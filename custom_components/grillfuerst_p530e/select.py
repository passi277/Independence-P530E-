"""Knob light colour of the Grillfürst Independence P530E."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .const import DP_KNOB_COLOR, KNOB_COLORS
from .entity import GrillEntity

KNOB_COLOR = SelectEntityDescription(
    key="knob_color",
    translation_key="knob_color",
    icon="mdi:palette",
    options=KNOB_COLORS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the colour select."""
    async_add_entities([GrillKnobColor(entry.runtime_data, KNOB_COLOR)])


class GrillKnobColor(GrillEntity, SelectEntity):
    """Colour of the illuminated control knobs."""

    @property
    def current_option(self) -> str | None:
        value = (self.coordinator.data or {}).get(DP_KNOB_COLOR)
        return value if value in KNOB_COLORS else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_dp(DP_KNOB_COLOR, option)
