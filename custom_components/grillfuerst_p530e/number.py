"""Writable values of the Grillfürst Independence P530E."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfMass, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .const import (
    DP_CYLINDER_SIZE,
    DP_CYLINDER_TARE,
    DP_PROBE_TARGETS,
    DP_STAGE_LEVEL,
    DP_TARGET_DIRECT,
    DP_TARGET_INDIRECT,
    DP_TARGET_LOW_SLOW,
    DP_TIMER_REMAINING,
    PROBE_TARGET_MAX,
    PROBE_TARGET_MIN,
    STAGE_LEVEL_MAX,
    STAGE_LEVEL_MIN,
    TIMER_MAX_MINUTES,
    WEIGHT_SCALE,
)
from .entity import GrillEntity


@dataclass(frozen=True, kw_only=True)
class GrillNumberDescription(NumberEntityDescription):
    """Describes a writable DP; limits are the ones the app allows."""

    dp: str
    scale: int = 1  # raw DP value = displayed value * scale


def _temperature(key: str, dp: str, low: int, high: int) -> GrillNumberDescription:
    return GrillNumberDescription(
        key=key,
        translation_key=key,
        icon="mdi:thermometer-chevron-up",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=low,
        native_max_value=high,
        native_step=1,
        mode=NumberMode.BOX,
        dp=dp,
    )


PROBE_TARGETS = tuple(
    GrillNumberDescription(
        key=f"probe_{index}_target",
        translation_key="probe_target",
        translation_placeholders={"probe": str(index)},
        icon="mdi:thermometer-probe",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=PROBE_TARGET_MIN,
        native_max_value=PROBE_TARGET_MAX,
        native_step=1,
        mode=NumberMode.BOX,
        dp=dp,
    )
    for index, dp in enumerate(DP_PROBE_TARGETS, start=1)
)

NUMBERS: tuple[GrillNumberDescription, ...] = (
    *PROBE_TARGETS,
    GrillNumberDescription(
        key="timer_duration",
        translation_key="timer_duration",
        icon="mdi:timer-cog-outline",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=0,
        native_max_value=TIMER_MAX_MINUTES,
        native_step=1,
        mode=NumberMode.BOX,
        dp=DP_TIMER_REMAINING,
    ),
    _temperature("target_direct", DP_TARGET_DIRECT, 200, 360),
    _temperature("target_indirect", DP_TARGET_INDIRECT, 120, 200),
    _temperature("target_low_slow", DP_TARGET_LOW_SLOW, 95, 115),
    GrillNumberDescription(
        key="stage_level",
        translation_key="stage_level",
        icon="mdi:fire",
        native_min_value=STAGE_LEVEL_MIN,
        native_max_value=STAGE_LEVEL_MAX,
        native_step=1,
        mode=NumberMode.SLIDER,
        dp=DP_STAGE_LEVEL,
    ),
    GrillNumberDescription(
        key="cylinder_tare",
        translation_key="cylinder_tare",
        icon="mdi:weight-kilogram",
        device_class=NumberDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        native_min_value=4.0,
        native_max_value=15.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        dp=DP_CYLINDER_TARE,
        scale=WEIGHT_SCALE,
    ),
    GrillNumberDescription(
        key="cylinder_size",
        translation_key="cylinder_size",
        icon="mdi:gas-cylinder",
        device_class=NumberDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        native_min_value=3.0,
        native_max_value=12.0,
        native_step=0.5,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        dp=DP_CYLINDER_SIZE,
        scale=WEIGHT_SCALE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the numbers."""
    coordinator = entry.runtime_data
    async_add_entities(GrillNumber(coordinator, description) for description in NUMBERS)


class GrillNumber(GrillEntity, NumberEntity):
    """A writable grill setting."""

    entity_description: GrillNumberDescription

    @property
    def native_value(self) -> float | None:
        raw = (self.coordinator.data or {}).get(self.entity_description.dp)
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            return None
        value = raw / self.entity_description.scale
        return round(value, 1) if self.entity_description.scale != 1 else value

    async def async_set_native_value(self, value: float) -> None:
        description = self.entity_description
        # Clamp to the range the app allows; the grill never gets anything else.
        value = min(max(value, description.native_min_value), description.native_max_value)
        await self.coordinator.async_set_dp(description.dp, int(round(value * description.scale)))
