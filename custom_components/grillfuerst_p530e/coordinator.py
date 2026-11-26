"""Polling coordinator talking to the grill over the local Tuya protocol."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time
from typing import Any

import tinytuya

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .analytics import GrillAnalytics, control_temperature

from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    DEFAULT_PROTOCOL_VERSION,
    DOMAIN,
    DP_TIMER_ALARM,
    DP_TIMER_REMAINING,
    DP_PROBE_TEMPS,
    DP_TIMER_STATE,
    IDLE_SCAN_INTERVAL_SECONDS,
    IN_USE_TEMP,
    OFFLINE_SCAN_INTERVAL_SECONDS,
    SCAN_INTERVAL_SECONDS,
    TIMER_PAUSED,
    TIMER_IDLE,
    TIMER_RUNNING,
    TIMER_STOPPED,
)

_LOGGER = logging.getLogger(__name__)


# Measured values the controller only reports on request
REFRESH_DPS = [101, 102, 103, 104, 105, 119, 120, 121, 124, 126]
# Writing this DP (as the app does on open) makes the controller send its live values
LIVE_DP = 132


class CannotConnect(Exception):
    """Raised when the grill does not answer with a valid status."""


def fetch_status(
    device_id: str, host: str, local_key: str, protocol_version: str
) -> dict[str, Any]:
    """Read the current DPs from the grill (blocking, run in an executor)."""
    device = tinytuya.Device(device_id, host, local_key, version=float(protocol_version))
    device.set_socketPersistent(True)
    device.set_socketTimeout(5)
    device.set_socketRetryLimit(1)
    fresh: dict[str, Any] = {}
    try:
        # Read the full status first, on its own, so no other answer is mistaken for it.
        result = device.status()
        if not isinstance(result, dict) or "Error" in result or "dps" not in result:
            raise CannotConnect(str(result))
        # The Wi-Fi module answers status() from a cache; the controller only sends new
        # probe/chamber values when asked. DP 132 is the first thing the app sends when it
        # opens (it is always "on", so re-sending it changes nothing), then ask for a refresh
        # and collect whatever the grill pushes back.
        try:
            device.set_value(LIVE_DP, True, nowait=True)
            device.updatedps(index=REFRESH_DPS, nowait=True)
            device.set_socketTimeout(1.5)
            for _ in range(6):
                msg = device.receive()
                if not isinstance(msg, dict):
                    break
                _LOGGER.debug("Grill pushed %s", msg)
                if isinstance(msg.get("dps"), dict):
                    fresh.update(msg["dps"])
        except Exception as err:  # noqa: BLE001 - refresh is best effort
            _LOGGER.debug("DP refresh failed: %s", err)
    finally:
        device.close()
    if fresh:
        _LOGGER.debug("Refreshed DPs %s", fresh)
    return {**result["dps"], **fresh}


def send_value(
    device_id: str,
    host: str,
    local_key: str,
    protocol_version: str,
    dp: str,
    value: Any,
) -> None:
    """Write one DP to the grill (blocking, run in an executor)."""
    device = tinytuya.Device(device_id, host, local_key, version=float(protocol_version))
    device.set_socketPersistent(False)
    device.set_socketTimeout(5)
    device.set_socketRetryLimit(1)
    try:
        result = device.set_value(int(dp), value)
    finally:
        device.close()
    if isinstance(result, dict) and "Error" in result:
        raise CannotConnect(str(result))


def discover_host(device_id: str) -> str | None:
    """Listen for the grill's UDP broadcast and return its current IP (blocking, ~20 s)."""
    try:
        result = tinytuya.find_device(dev_id=device_id)
    except Exception as err:  # noqa: BLE001 - discovery is best effort
        _LOGGER.debug("Discovery failed: %s", err)
        return None
    ip = result.get("ip") if isinstance(result, dict) else None
    return ip if isinstance(ip, str) and ip else None


# After a failed poll, look for a changed IP at most this often
DISCOVERY_INTERVAL = 10 * 60


class GrillCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the grill and keeps the last known value of every DP.

    In standby the grill only reports DPs 101-107, so values of the other
    DPs are kept from the last time the grill was awake.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.device_id: str = entry.data[CONF_DEVICE_ID]
        self._host: str = entry.data[CONF_HOST]
        self._local_key: str = entry.data[CONF_LOCAL_KEY]
        self._protocol_version: str = entry.data.get(
            CONF_PROTOCOL_VERSION, DEFAULT_PROTOCOL_VERSION
        )
        self._dps: dict[str, Any] = {}
        self._last_discovery = 0.0
        # When the timer last ran out (None while it has not or after a restart)
        self.timer_finished_at: float | None = None
        self.analytics = GrillAnalytics()
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        # Tuya devices handle only one local connection well: serialise all access.
        self._lock = asyncio.Lock()

    async def async_set_dp(self, dp: str, value: Any) -> None:
        """Write a DP and update the cached state."""
        async with self._lock:
            try:
                await self.hass.async_add_executor_job(
                    send_value,
                    self.device_id,
                    self._host,
                    self._local_key,
                    self._protocol_version,
                    dp,
                    value,
                )
            except (CannotConnect, OSError) as err:
                raise HomeAssistantError(f"Could not send command to the grill: {err}") from err
        self._dps[dp] = value
        self._set_interval(SCAN_INTERVAL_SECONDS)
        # Update entities without restarting the poll interval
        # (async_set_updated_data would push the next poll back).
        self.data = dict(self._dps)
        self.async_update_listeners()

    def _track_timer(self, dps: dict[str, Any]) -> None:
        """Notice the end of the timer.

        The grill sets DP 125 only for a few seconds and then goes running -> stopped -> idle.
        A manual stop keeps the remaining minutes (rounded up, so >= 1), a finished timer has 0.
        """
        before, now = self._dps.get(DP_TIMER_STATE), dps.get(DP_TIMER_STATE)
        if now == TIMER_RUNNING:
            self.timer_finished_at = None
            return
        ran_out = before == TIMER_RUNNING and now in (TIMER_STOPPED, TIMER_IDLE) and dps.get(DP_TIMER_REMAINING) == 0
        if (dps.get(DP_TIMER_ALARM) is True or ran_out) and self.timer_finished_at is None:
            self.timer_finished_at = time.time()

    async def async_load(self) -> None:
        """Restore totals and the last session from storage."""
        self.analytics = GrillAnalytics.from_dict(await self._store.async_load())

    def _feed(self, dps: dict[str, Any] | None) -> None:
        self.analytics.update(time.time(), dps)
        self._store.async_delay_save(self.analytics.as_dict, 60)

    async def _fetch(self) -> dict[str, Any]:
        async with self._lock:
            return await self.hass.async_add_executor_job(
                fetch_status,
                self.device_id,
                self._host,
                self._local_key,
                self._protocol_version,
            )

    async def _rediscover(self) -> bool:
        """The grill may have a new IP (DHCP): find it via its broadcast and store it."""
        now = time.time()
        if now - self._last_discovery < DISCOVERY_INTERVAL:
            return False
        self._last_discovery = now
        ip = await self.hass.async_add_executor_job(discover_host, self.device_id)
        if not ip or ip == self._host:
            return False
        _LOGGER.warning("Grill found at new IP %s (was %s), updating the configuration", ip, self._host)
        self._host = ip
        self.hass.config_entries.async_update_entry(
            self.config_entry, data={**self.config_entry.data, CONF_HOST: ip}
        )
        return True

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            dps = await self._fetch()
        except (CannotConnect, OSError) as err:
            dps = None
            if await self._rediscover():
                try:
                    dps = await self._fetch()
                except (CannotConnect, OSError):
                    dps = None
            if dps is None:
                self._feed(None)
                self._set_interval(OFFLINE_SCAN_INTERVAL_SECONDS)
                raise UpdateFailed(f"Grill did not answer: {err}") from err

        _LOGGER.debug("Grill reported %s", dps)
        self._track_timer(dps)
        self._dps.update(dps)
        self._feed(self._dps)
        self._set_interval(SCAN_INTERVAL_SECONDS if self.in_use else IDLE_SCAN_INTERVAL_SECONDS)
        return dict(self._dps)

    @property
    def in_use(self) -> bool:
        """Grilling, a timer running/ringing, a probe plugged in or the grill warm: poll often."""
        d = self._dps
        temp = control_temperature(d)
        probes = any(isinstance(d.get(dp), int) and not isinstance(d.get(dp), bool) and d[dp] > 0 for dp in DP_PROBE_TEMPS)
        return (
            self.analytics.grilling
            or d.get(DP_TIMER_STATE) in (TIMER_RUNNING, TIMER_PAUSED)
            or d.get(DP_TIMER_ALARM) is True
            or self.timer_finished_at is not None and time.time() - self.timer_finished_at < 600
            or probes
            or (temp is not None and temp >= IN_USE_TEMP)
        )

    def _set_interval(self, seconds: int) -> None:
        interval = timedelta(seconds=seconds)
        if self.update_interval != interval:
            _LOGGER.debug("Polling every %s s", seconds)
            self.update_interval = interval
