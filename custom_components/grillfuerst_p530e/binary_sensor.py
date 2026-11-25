"""Connection state of the Grillfürst Independence P530E."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .entity import GrillEntity

CONNECTION = BinarySensorEntityDescription(
    key="connection",
    translation_key="connection",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the connection sensor."""
    async_add_entities([GrillConnection(entry.runtime_data, CONNECTION)])


class GrillConnection(GrillEntity, BinarySensorEntity):
    """On while the grill answers on the local network."""

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success
