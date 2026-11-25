"""Light switches of the Grillfürst Independence P530E."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .const import (
    DP_CHAMBER_LIGHT,
    DP_KNOB_LIGHT,
    DP_LOGO_LIGHT,
    KNOB_LIGHT_OFF,
    KNOB_LIGHT_ON,
)
from .entity import GrillEntity


@dataclass(frozen=True, kw_only=True)
class GrillSwitchDescription(SwitchEntityDescription):
    """Describes a grill switch and the DP values it writes."""

    dp: str
    on_value: Any = True
    off_value: Any = False


SWITCHES: tuple[GrillSwitchDescription, ...] = (
    GrillSwitchDescription(
        key="chamber_light",
        translation_key="chamber_light",
        icon="mdi:lightbulb",
        dp=DP_CHAMBER_LIGHT,
    ),
    GrillSwitchDescription(
        key="logo_light",
        translation_key="logo_light",
        icon="mdi:lightbulb-on-outline",
        dp=DP_LOGO_LIGHT,
    ),
    GrillSwitchDescription(
        key="knob_light",
        translation_key="knob_light",
        icon="mdi:knob",
        dp=DP_KNOB_LIGHT,
        on_value=KNOB_LIGHT_ON,
        off_value=KNOB_LIGHT_OFF,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the grill switches."""
    coordinator = entry.runtime_data
    async_add_entities(GrillSwitch(coordinator, description) for description in SWITCHES)


class GrillSwitch(GrillEntity, SwitchEntity):
    """A light on the grill."""

    entity_description: GrillSwitchDescription

    @property
    def is_on(self) -> bool | None:
        value = (self.coordinator.data or {}).get(self.entity_description.dp)
        if value is None:
            return None
        # The knob light reports intermediate values (e.g. 1) while switching on.
        return value != self.entity_description.off_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_dp(
            self.entity_description.dp, self.entity_description.on_value
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_dp(
            self.entity_description.dp, self.entity_description.off_value
        )
