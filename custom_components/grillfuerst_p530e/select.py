"""Knob light selects of the Grillfürst Independence P530E."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import GrillConfigEntry
from .const import (
    DP_GRILL_MODE,
    DP_KNOB_COLOR,
    DP_KNOB_LIGHT,
    DP_PROBE_TARGETS,
    GRILL_MODES,
    KNOB_COLORS,
    KNOB_LIGHT_MODES,
    PROBE_PRESETS,
)
from .entity import GrillEntity


@dataclass(frozen=True, kw_only=True)
class GrillSelectDescription(SelectEntityDescription):
    """Describes a select and how its options map to DP values."""

    dp: str
    values: dict[Any, str]  # DP value -> option


SELECTS: tuple[GrillSelectDescription, ...] = (
    GrillSelectDescription(
        key="grill_mode",
        translation_key="grill_mode",
        icon="mdi:grill",
        dp=DP_GRILL_MODE,
        values=GRILL_MODES,
        options=list(GRILL_MODES.values()),
    ),
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


PRESET_SELECTS: tuple[GrillSelectDescription, ...] = tuple(
    GrillSelectDescription(
        key=f"probe_{index}_preset",
        translation_key="probe_preset",
        translation_placeholders={"probe": str(index)},
        icon="mdi:food-steak",
        dp=dp,
        values={},
        options=list(PROBE_PRESETS),
    )
    for index, dp in enumerate(DP_PROBE_TARGETS, start=1)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the selects."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            *(GrillSelect(coordinator, description) for description in SELECTS),
            *(GrillPresetSelect(coordinator, description) for description in PRESET_SELECTS),
        ]
    )


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


class GrillPresetSelect(GrillEntity, SelectEntity, RestoreEntity):
    """Doneness preset for a probe: writes the matching target temperature.

    Several presets share a temperature, so the chosen preset is remembered and
    shown only while the probe target still equals the preset's temperature.
    """

    entity_description: GrillSelectDescription
    _selected: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state in PROBE_PRESETS:
            self._selected = last.state

    @property
    def current_option(self) -> str | None:
        target = (self.coordinator.data or {}).get(self.entity_description.dp)
        if self._selected is not None and PROBE_PRESETS[self._selected] == target:
            return self._selected
        return None

    async def async_select_option(self, option: str) -> None:
        self._selected = option
        await self.coordinator.async_set_dp(self.entity_description.dp, PROBE_PRESETS[option])
