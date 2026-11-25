"""Sensors for the Grillfürst Independence P530E."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import time
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import GrillConfigEntry
from .const import (
    DP_CHAMBER_TEMP,
    DP_CYLINDER_SIZE,
    DP_PROBE_TEMPS,
    DP_GAS_LEVEL_STEP,
    DP_GAS_REMAINING,
    DP_SCALE_WEIGHT,
    DP_TIMER_REMAINING,
    DP_TIMER_STATE,
    TIMER_STATES,
    WEIGHT_SCALE,
)
from .analytics import GrillAnalytics
from .entity import GrillEntity

type SensorValue = float | int | str | None


def _weight(dp: str) -> Callable[[dict[str, Any]], SensorValue]:
    def value(data: dict[str, Any]) -> SensorValue:
        raw = data.get(dp)
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            return None
        return round(raw / WEIGHT_SCALE, 1)

    return value


def _integer(dp: str) -> Callable[[dict[str, Any]], SensorValue]:
    def value(data: dict[str, Any]) -> SensorValue:
        raw = data.get(dp)
        if not isinstance(raw, int) or isinstance(raw, bool):
            return None
        return raw

    return value


def _gas_percent(data: dict[str, Any]) -> SensorValue:
    gas = data.get(DP_GAS_REMAINING)
    size = data.get(DP_CYLINDER_SIZE)
    if not isinstance(gas, (int, float)) or not isinstance(size, (int, float)) or size <= 0:
        return None
    return round(min(max(gas / size * 100, 0), 100))


def _level_step(data: dict[str, Any]) -> SensorValue:
    try:
        return int(data[DP_GAS_LEVEL_STEP])
    except (KeyError, TypeError, ValueError):
        return None



def _timer_state(data: dict[str, Any]) -> SensorValue:
    return TIMER_STATES.get(data.get(DP_TIMER_STATE))


@dataclass(frozen=True, kw_only=True)
class GrillSensorDescription(SensorEntityDescription):
    """Describes a grill sensor."""

    value_fn: Callable[[dict[str, Any]], SensorValue]
    # Keep showing the last known value while the grill is unreachable (gas scale)
    keep_last: bool = False



def _temperature_sensor(**kwargs: Any) -> GrillSensorDescription:
    return GrillSensorDescription(
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        **kwargs,
    )


TEMPERATURE_SENSORS: tuple[GrillSensorDescription, ...] = (
    _temperature_sensor(
        key="chamber_temperature",
        translation_key="chamber_temperature",
        icon="mdi:thermometer",
        value_fn=_integer(DP_CHAMBER_TEMP),
    ),
    *(
        _temperature_sensor(
            key=f"probe_{index}_temperature",
            translation_key="probe_temperature",
            translation_placeholders={"probe": str(index)},
            icon="mdi:thermometer-probe",
            value_fn=_integer(dp),
        )
        for index, dp in enumerate(DP_PROBE_TEMPS, start=1)
    ),
)

SENSORS: tuple[GrillSensorDescription, ...] = (
    *TEMPERATURE_SENSORS,
    GrillSensorDescription(
        key="gas_remaining",
        translation_key="gas_remaining",
        keep_last=True,
        icon="mdi:gas-cylinder",
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        suggested_display_precision=1,
        value_fn=_weight(DP_GAS_REMAINING),
    ),
    GrillSensorDescription(
        key="gas_level",
        translation_key="gas_level",
        keep_last=True,
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_gas_percent,
    ),
    GrillSensorDescription(
        key="scale_weight",
        translation_key="scale_weight",
        keep_last=True,
        icon="mdi:scale",
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_weight(DP_SCALE_WEIGHT),
    ),
    GrillSensorDescription(
        key="gas_level_step",
        translation_key="gas_level_step",
        keep_last=True,
        icon="mdi:stairs",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_level_step,
    ),
    GrillSensorDescription(
        key="timer_state",
        translation_key="timer_state",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.ENUM,
        options=list(TIMER_STATES.values()),
        value_fn=_timer_state,
    ),
    GrillSensorDescription(
        key="timer_remaining",
        translation_key="timer_remaining",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=_integer(DP_TIMER_REMAINING),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the grill sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            *(GrillSensor(coordinator, description) for description in SENSORS),
            *(GrillStatSensor(coordinator, description) for description in STATS),
        ]
    )


class GrillSensor(GrillEntity, RestoreSensor):
    """A grill sensor that keeps its last value while the grill sleeps."""

    entity_description: GrillSensorDescription
    _restored_value: SensorValue = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            value = last.native_value
            if isinstance(value, (int, float, str)):
                self._restored_value = value

    @property
    def available(self) -> bool:
        if self.entity_description.keep_last and self.native_value is not None:
            return True
        return super().available

    @property
    def native_value(self) -> SensorValue:
        value = self.entity_description.value_fn(self.coordinator.data or {})
        return self._restored_value if value is None else value


# ---------------- Derived values (gas consumption, sessions, time to target) ----------------

type StatValue = float | int | datetime | None


@dataclass(frozen=True, kw_only=True)
class GrillStatDescription(SensorEntityDescription):
    """A value computed by GrillAnalytics."""

    stat_fn: Callable[[GrillAnalytics, dict[str, Any], float], StatValue]


def _eta(seconds: float | None) -> datetime | None:
    if seconds is None or seconds <= 0:
        return None
    return dt_util.utcnow() + timedelta(seconds=seconds)


def _gas_kg(data: dict[str, Any]) -> float | None:
    raw = data.get(DP_GAS_REMAINING)
    return raw / WEIGHT_SCALE if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None


def _session(key: str, scale: float = 1, digits: int = 0) -> Callable[[GrillAnalytics, dict[str, Any], float], StatValue]:
    def value(a: GrillAnalytics, _data: dict[str, Any], now: float) -> StatValue:
        s = a.current_or_last(now)
        if not s or s.get(key) is None:
            return None
        return round(s[key] / scale, digits) if digits else round(s[key] / scale)

    return value


def _session_start(a: GrillAnalytics, _data: dict[str, Any], now: float) -> StatValue:
    s = a.current_or_last(now)
    return dt_util.utc_from_timestamp(s["start"]) if s else None


def _round(v: float | None, digits: int) -> float | None:
    return None if v is None else round(v, digits)


STATS: tuple[GrillStatDescription, ...] = (
    GrillStatDescription(key="gas_consumed", translation_key="gas_consumed", icon="mdi:gas-cylinder",
        device_class=SensorDeviceClass.WEIGHT, state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS, suggested_display_precision=1,
        stat_fn=lambda a, d, n: round(a.gas_consumed, 2)),
    GrillStatDescription(key="gas_energy", translation_key="gas_energy", icon="mdi:fire",
        device_class=SensorDeviceClass.ENERGY, state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR, suggested_display_precision=1,
        stat_fn=lambda a, d, n: round(a.gas_energy, 2)),
    GrillStatDescription(key="gas_rate", translation_key="gas_rate", icon="mdi:speedometer",
        state_class=SensorStateClass.MEASUREMENT, native_unit_of_measurement="kg/h", suggested_display_precision=2,
        stat_fn=lambda a, d, n: _round(a.gas_rate, 3)),
    GrillStatDescription(key="gas_runtime", translation_key="gas_runtime", icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.HOURS, suggested_display_precision=1,
        stat_fn=lambda a, d, n: _round(a.runtime_left(_gas_kg(d)), 2)),
    GrillStatDescription(key="session_start", translation_key="session_start", icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP, stat_fn=_session_start),
    GrillStatDescription(key="session_duration", translation_key="session_duration", icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.MINUTES,
        stat_fn=_session("duration", 60)),
    GrillStatDescription(key="session_gas", translation_key="session_gas", icon="mdi:gas-cylinder",
        device_class=SensorDeviceClass.WEIGHT, native_unit_of_measurement=UnitOfMass.KILOGRAMS, suggested_display_precision=1,
        stat_fn=_session("gas_used", 1, 2)),
    GrillStatDescription(key="session_max_temp", translation_key="session_max_temp", icon="mdi:thermometer-high",
        device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        stat_fn=_session("max_temp")),
    GrillStatDescription(key="preheat_eta", translation_key="preheat_eta", icon="mdi:fire-alert",
        device_class=SensorDeviceClass.TIMESTAMP, stat_fn=lambda a, d, n: _eta(a.preheat_eta(d))),
    *(
        GrillStatDescription(key=f"probe_{i + 1}_eta", translation_key="probe_eta", translation_placeholders={"probe": str(i + 1)},
            icon="mdi:clock-check-outline", device_class=SensorDeviceClass.TIMESTAMP,
            stat_fn=lambda a, d, n, i=i: _eta(a.probe_eta(i, d)))
        for i in range(len(DP_PROBE_TEMPS))
    ),
)


class GrillStatSensor(GrillEntity, SensorEntity):
    """Computed from the grill history; available even while the grill is offline."""

    entity_description: GrillStatDescription

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> StatValue:
        return self.entity_description.stat_fn(self.coordinator.analytics, self.coordinator.data or {}, time.time())
