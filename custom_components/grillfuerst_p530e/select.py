"""Knob light selects of the Grillfürst Independence P530E."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .const import DP_KNOB_COLOR, DP_KNOB_LIGHT, KNOB_COLORS, KNOB_LIGHT_MODES
from .entity import GrillEntity


@dataclass(frozen=True, kw_only=True)
class GrillSelectDescription(SelectEntityDescription):
    """Describes a select and how its options map to DP values."""

    dp: str
    values: dict[Any, str]  # DP value -> option


SELECTS: tuple[GrillSelectDescription, ...] = (
    GrillSelectDescription(
        key="knob_light_mode",
        translation_key="knob_light_mode",
        icon="mdi:knob",
        dp=DP_KNOB_LIGHT,
        values=KNOB_LIGHT_MODES,
        options=list(KNOB_LIGHT_MODES.values()),
    ),
    GrillSelectDescription(
        key="knob_color",
        translation_key="knob_color",
        icon="mdi:palette",
        dp=DP_KNOB_COLOR,
        values={color: color for color in KNOB_COLORS},
        options=list(KNOB_COLORS),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the selects."""
    coordinator = entry.runtime_data
    async_add_entities(GrillSelect(coordinator, description) for description in SELECTS)


class GrillSelect(GrillEntity, SelectEntity):
    """A select backed by one DP."""

    entity_description: GrillSelectDescription

    @property
    def current_option(self) -> str | None:
        value = (self.coordinator.data or {}).get(self.entity_description.dp)
        return self.entity_description.values.get(value)

    async def async_select_option(self, option: str) -> None:
        for value, name in self.entity_description.values.items():
            if name == option:
                await self.coordinator.async_set_dp(self.entity_description.dp, value)
                return
