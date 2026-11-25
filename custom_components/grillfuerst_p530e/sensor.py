"""Sensors for the Grillfürst Independence P530E."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfMass,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .const import (
    DP_CYLINDER_SIZE,
    DP_GAS_LEVEL_STEP,
    DP_GAS_REMAINING,
    DP_SCALE_WEIGHT,
    DP_TIMER_REMAINING,
    DP_TIMER_STATE,
    TIMER_STATES,
    WEIGHT_SCALE,
)
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



SENSORS: tuple[GrillSensorDescription, ...] = (
    GrillSensorDescription(
        key="gas_remaining",
        translation_key="gas_remaining",
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
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_gas_percent,
    ),
    GrillSensorDescription(
        key="scale_weight",
        translation_key="scale_weight",
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
    async_add_entities(GrillSensor(coordinator, description) for description in SENSORS)


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
    def native_value(self) -> SensorValue:
        value = self.entity_description.value_fn(self.coordinator.data or {})
        return self._restored_value if value is None else value
