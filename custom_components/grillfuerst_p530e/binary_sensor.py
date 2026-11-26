"""Binary sensors of the Grillfürst Independence P530E: connection, grilling, timer finished, preheated, probe done."""

from __future__ import annotations

from collections.abc import Callable
import time
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .analytics import control_temperature
from .const import DP_PROBE_TARGETS, DP_PROBE_TEMPS, TIMER_FINISHED_HOLD_SECONDS
from .coordinator import GrillCoordinator
from .entity import GrillEntity

# The chamber counts as preheated this close to the target
PREHEAT_MARGIN = 5


def _num(data: dict[str, Any], dp: str) -> float | None:
    v = data.get(dp)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _preheated(c: GrillCoordinator) -> bool | None:
    data = c.data or {}
    chamber, target = control_temperature(data), c.analytics.preheat_target(data)
    if chamber is None or target is None:
        return None
    return chamber >= target - PREHEAT_MARGIN


def _timer_finished(c: GrillCoordinator) -> bool:
    at = c.timer_finished_at
    return at is not None and time.time() - at < TIMER_FINISHED_HOLD_SECONDS


def _probe_done(index: int) -> Callable[[GrillCoordinator], bool | None]:
    def value(c: GrillCoordinator) -> bool | None:
        data = c.data or {}
        temp, target = _num(data, DP_PROBE_TEMPS[index]), _num(data, DP_PROBE_TARGETS[index])
        if temp is None or target is None:
            return None
        return temp > 0 and target > 0 and temp >= target

    return value


@dataclass(frozen=True, kw_only=True)
class GrillBinaryDescription(BinarySensorEntityDescription):
    """Describes a binary sensor."""

    is_on_fn: Callable[[GrillCoordinator], bool | None]
    always_available: bool = False


BINARY_SENSORS: tuple[GrillBinaryDescription, ...] = (
    GrillBinaryDescription(key="connection", translation_key="connection", device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC, always_available=True, is_on_fn=lambda c: c.last_update_success),
    GrillBinaryDescription(key="grilling", translation_key="grilling", device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:grill", always_available=True, is_on_fn=lambda c: c.analytics.grilling),
    GrillBinaryDescription(key="timer_finished", translation_key="timer_finished", icon="mdi:timer-alert-outline",
        is_on_fn=_timer_finished),
    GrillBinaryDescription(key="preheated", translation_key="preheated", icon="mdi:thermometer-check", is_on_fn=_preheated),
    *(
        GrillBinaryDescription(key=f"probe_{i + 1}_done", translation_key="probe_done", translation_placeholders={"probe": str(i + 1)},
            icon="mdi:food-steak", is_on_fn=_probe_done(i))
        for i in range(len(DP_PROBE_TEMPS))
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(GrillBinarySensor(coordinator, description) for description in BINARY_SENSORS)


class GrillBinarySensor(GrillEntity, BinarySensorEntity):
    """A derived on/off state."""

    entity_description: GrillBinaryDescription

    @property
    def available(self) -> bool:
        return self.entity_description.always_available or super().available

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.coordinator)
