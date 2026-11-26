"""Derived values: gas consumption, grill sessions and time-to-target estimates.

Pure Python (no Home Assistant imports) so the logic can be unit tested.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .const import (
    DP_CHAMBER_TEMP,
    DP_GAS_REMAINING,
    DP_GRILL_MODE,
    DP_PROBE_TARGETS,
    DP_PROBE_TEMPS,
    DP_TARGET_DIRECT,
    DP_TARGET_INDIRECT,
    DP_TARGET_LOW_SLOW,
    WEIGHT_SCALE,
)

# Propane: lower heating value ≈ 46.4 MJ/kg ≈ 12.8 kWh/kg
GAS_KWH_PER_KG = 12.8
# The grill counts as "grilling" from this chamber temperature on
ACTIVE_TEMP = 60
# A session ends after this many seconds without heat and without gas use
SESSION_END_AFTER = 10 * 60
# Gas use only counts in steps of the scale resolution (0.1 kg)
GAS_STEP = 0.1
# A jump up of at least this much means a new/refilled cylinder
GAS_REFILL = 0.5
# A sudden drop of more than this within one poll means the cylinder was taken off
GAS_REMOVED = 1.0
# Rate estimate needs at least this much grilling time
MIN_RATE_SECONDS = 30 * 60
# Time-to-target uses the temperature rise over this window
SLOPE_WINDOW = 10 * 60
MIN_SLOPE_SPAN = 2 * 60

MODE_TARGET_DP = {0: DP_TARGET_DIRECT, 4: DP_TARGET_INDIRECT, 3: DP_TARGET_LOW_SLOW}
# Manual: in indirect and low & slow the grill regulates with probe F4 placed above burner 3,
# in direct and stage mode with the built-in sensor below the grate (DP 101).
MODE_CONTROL_DP = {3: DP_PROBE_TEMPS[3], 4: DP_PROBE_TEMPS[3]}
CONTROL = "control"


def _num(data: dict[str, Any], dp: str) -> float | None:
    v = data.get(dp)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def control_temperature(data: dict[str, Any] | None) -> float | None:
    """The temperature the grill regulates with in the current mode (display "Ist-Temperatur")."""
    if not data:
        return None
    mode = data.get(DP_GRILL_MODE)
    dp = MODE_CONTROL_DP.get(mode, DP_CHAMBER_TEMP) if isinstance(mode, int) else DP_CHAMBER_TEMP
    return _num(data, dp)


def eta_seconds(samples: deque[tuple[float, float]], target: float | None) -> float | None:
    """Seconds until `target` is reached from the recent rise, None if not rising."""
    if target is None or target <= 0 or len(samples) < 2:
        return None
    (t0, v0), (t1, v1) = samples[0], samples[-1]
    if v1 >= target:
        return 0.0
    if t1 - t0 < MIN_SLOPE_SPAN or v1 <= v0:
        return None
    slope = (v1 - v0) / (t1 - t0)
    return (target - v1) / slope


@dataclass
class Session:
    start: float
    start_gas: float | None
    last_active: float
    gas_used: float = 0.0
    max_temp: float = 0.0

    def as_dict(self, end: float | None = None) -> dict[str, Any]:
        return {"start": self.start, "end": end, "gas_used": round(self.gas_used, 2), "max_temp": self.max_temp,
                "duration": round((end or self.last_active) - self.start)}


@dataclass
class GrillAnalytics:
    """State that survives restarts: totals and the last finished session."""

    gas_consumed: float = 0.0
    active_seconds: float = 0.0
    active_gas: float = 0.0
    last_session: dict[str, Any] | None = None
    session: Session | None = None
    _gas_ref: float | None = None
    _last_tick: float | None = None
    _last_gas_drop: float | None = None
    _samples: dict[str, deque] = field(default_factory=dict)

    # ---------- persistence ----------
    def as_dict(self) -> dict[str, Any]:
        return {"gas_consumed": round(self.gas_consumed, 3), "active_seconds": round(self.active_seconds),
                "active_gas": round(self.active_gas, 3), "last_session": self.last_session, "gas_ref": self._gas_ref}

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> GrillAnalytics:
        d = d or {}
        a = cls(gas_consumed=float(d.get("gas_consumed", 0)), active_seconds=float(d.get("active_seconds", 0)),
                active_gas=float(d.get("active_gas", 0)), last_session=d.get("last_session"))
        a._gas_ref = d.get("gas_ref")
        return a

    # ---------- update ----------
    def update(self, now: float, data: dict[str, Any] | None) -> None:
        """Feed a poll result (None = grill not reachable)."""
        dt = 0.0 if self._last_tick is None else min(now - self._last_tick, 120.0)
        self._last_tick = now
        chamber = _num(data, DP_CHAMBER_TEMP) if data else None
        control = control_temperature(data)
        used = self._track_gas(now, _num(data, DP_GAS_REMAINING) if data else None)

        if data:
            self._sample(DP_CHAMBER_TEMP, now, chamber)
            self._sample(CONTROL, now, control)
            for dp in DP_PROBE_TEMPS:
                self._sample(dp, now, _num(data, dp))

        hottest = max((t for t in (chamber, control) if t is not None), default=None)
        hot = hottest is not None and hottest >= ACTIVE_TEMP
        burning = self._last_gas_drop is not None and now - self._last_gas_drop < SESSION_END_AFTER
        if hot or (data and burning):
            if self.session is None:
                gas = _num(data, DP_GAS_REMAINING) if data else None
                self.session = Session(start=now, start_gas=gas / WEIGHT_SCALE if gas is not None else None, last_active=now)
            self.session.last_active = now
            self.active_seconds += dt
            self.active_gas += used
            self.session.gas_used += used
            if hottest is not None:
                self.session.max_temp = max(self.session.max_temp, hottest)
        elif self.session is not None and now - self.session.last_active >= SESSION_END_AFTER:
            self.last_session = self.session.as_dict(self.session.last_active)
            self.session = None

    def _track_gas(self, now: float, raw: float | None) -> float:
        if raw is None:
            return 0.0
        gas = raw / WEIGHT_SCALE
        ref = self._gas_ref
        if ref is None or gas >= ref + GAS_REFILL or ref - gas > GAS_REMOVED:
            self._gas_ref = gas
            return 0.0
        if gas <= ref - GAS_STEP + 1e-9:
            used = ref - gas
            self._gas_ref = gas
            self.gas_consumed += used
            self._last_gas_drop = now
            return used
        return 0.0

    def _sample(self, key: str, now: float, value: float | None) -> None:
        q = self._samples.setdefault(key, deque())
        if value is None or value <= 0:
            q.clear()
            return
        q.append((now, value))
        while q and now - q[0][0] > SLOPE_WINDOW:
            q.popleft()

    # ---------- derived values ----------
    @property
    def gas_rate(self) -> float | None:
        """Average gas use while grilling in kg/h."""
        if self.active_seconds < MIN_RATE_SECONDS or self.active_gas <= 0:
            return None
        return self.active_gas / (self.active_seconds / 3600)

    def runtime_left(self, gas_kg: float | None) -> float | None:
        rate = self.gas_rate
        if gas_kg is None or rate is None or rate <= 0:
            return None
        return gas_kg / rate

    @property
    def gas_energy(self) -> float:
        return self.gas_consumed * GAS_KWH_PER_KG

    @property
    def grilling(self) -> bool:
        return self.session is not None

    def current_or_last(self, now: float) -> dict[str, Any] | None:
        if self.session is not None:
            d = self.session.as_dict()
            d["duration"] = round(now - self.session.start)
            return d
        return self.last_session

    def preheat_target(self, data: dict[str, Any]) -> float | None:
        mode = data.get(DP_GRILL_MODE)
        dp = MODE_TARGET_DP.get(mode) if isinstance(mode, int) else None
        return _num(data, dp) if dp else None

    def preheat_eta(self, data: dict[str, Any]) -> float | None:
        return eta_seconds(self._samples.get(CONTROL, deque()), self.preheat_target(data))

    def probe_eta(self, index: int, data: dict[str, Any]) -> float | None:
        return eta_seconds(self._samples.get(DP_PROBE_TEMPS[index], deque()), _num(data, DP_PROBE_TARGETS[index]))
