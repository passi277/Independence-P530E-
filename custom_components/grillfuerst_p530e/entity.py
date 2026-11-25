"""Base entity for the Grillfürst Independence P530E."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import GrillCoordinator


class GrillEntity(CoordinatorEntity[GrillCoordinator]):
    """Common device info and unique id handling."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GrillCoordinator, description: EntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"{MANUFACTURER} {MODEL}",
        )
