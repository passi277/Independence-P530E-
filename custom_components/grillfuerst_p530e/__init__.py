"""Local integration for the Grillfürst Independence P530E gas grill."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import GrillCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type GrillConfigEntry = ConfigEntry[GrillCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: GrillConfigEntry) -> bool:
    """Set up the grill from a config entry."""
    coordinator = GrillCoordinator(hass, entry)
    await coordinator.async_load()
    # Do not fail setup while the grill is switched off: the gas values are
    # restored from the last run and the connection sensor shows "offline".
    await coordinator.async_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GrillConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
