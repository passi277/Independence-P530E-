"""Timer buttons of the Grillfürst Independence P530E."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GrillConfigEntry
from .const import DP_TIMER_STATE, TIMER_PAUSED, TIMER_RUNNING, TIMER_STOPPED
from .entity import GrillEntity


@dataclass(frozen=True, kw_only=True)
class GrillButtonDescription(ButtonEntityDescription):
    """Describes a button writing a fixed value to a DP."""

    dp: str
    value: int


BUTTONS: tuple[GrillButtonDescription, ...] = (
    GrillButtonDescription(
        key="timer_start",
        translation_key="timer_start",
        icon="mdi:play",
        dp=DP_TIMER_STATE,
        value=TIMER_RUNNING,
    ),
    GrillButtonDescription(
        key="timer_pause",
        translation_key="timer_pause",
        icon="mdi:pause",
        dp=DP_TIMER_STATE,
        value=TIMER_PAUSED,
    ),
    GrillButtonDescription(
        key="timer_stop",
        translation_key="timer_stop",
        icon="mdi:stop",
        dp=DP_TIMER_STATE,
        value=TIMER_STOPPED,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrillConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the timer buttons."""
    coordinator = entry.runtime_data
    async_add_entities(GrillButton(coordinator, description) for description in BUTTONS)


class GrillButton(GrillEntity, ButtonEntity):
    """A timer control button."""

    entity_description: GrillButtonDescription

    async def async_press(self) -> None:
        await self.coordinator.async_set_dp(
            self.entity_description.dp, self.entity_description.value
        )
