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
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GrillConfigEntry
from .const import (
    DOMAIN,
    DP_CYLINDER_SIZE,
    DP_CYLINDER_TARE,
    DP_GAS_LEVEL_STEP,
    DP_GAS_REMAINING,
    DP_SCALE_WEIGHT,
    MANUFACTURER,
    MODEL,
    WEIGHT_SCALE,
)
from .coordinator import GrillCoordinator


def _weight(dp: str) -> Callable[[dict[str, Any]], float | None]:
    def value(data: dict[str, Any]) -> float | None:
        raw = data.get(dp)
        if not isinstance(raw, (int, float)):
            return None
        return round(raw / WEIGHT_SCALE, 1)

    return value


def _gas_percent(data: dict[str, Any]) -> float | None:
    gas = data.get(DP_GAS_REMAINING)
    size = data.get(DP_CYLINDER_SIZE)
    if not isinstance(gas, (int, float)) or not isinstance(size, (int, float)) or size <= 0:
        return None
    return round(min(max(gas / size * 100, 0), 100))


def _level_step(data: dict[str, Any]) -> int | None:
    try:
        return int(data[DP_GAS_LEVEL_STEP])
    except (KeyError, TypeError, ValueError):
        return None


@dataclass(frozen=True, kw_only=True)
class GrillSensorDescription(SensorEntityDescription):
    """Describes a grill sensor."""

    value_fn: Callable[[dict[str, Any]], float | int | None]


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
        key="cylinder_size",
        translation_key="cylinder_size",
        icon="mdi:gas-cylinder",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_weight(DP_CYLINDER_SIZE),
    ),
    GrillSensorDescription(
        key="cylinder_tare",
        translation_key="cylinder_tare",
        icon="mdi:weight-kilogram",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_weight(DP_CYLINDER_TARE),
    ),
    GrillSensorDescription(
        key="gas_level_step",
        translation_key="gas_level_step",
        icon="mdi:stairs",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_level_step,
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


class GrillSensor(CoordinatorEntity[GrillCoordinator], RestoreSensor):
    """A grill sensor that keeps its last value while the grill sleeps."""

    _attr_has_entity_name = True
    entity_description: GrillSensorDescription

    def __init__(
        self, coordinator: GrillCoordinator, description: GrillSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"{MANUFACTURER} {MODEL}",
        )
        self._restored_value: float | int | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            value = last.native_value
            self._restored_value = value if isinstance(value, (int, float)) else None

    @property
    def native_value(self) -> float | int | None:
        value = self.entity_description.value_fn(self.coordinator.data or {})
        return self._restored_value if value is None else value
