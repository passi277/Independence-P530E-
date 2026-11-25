"""Config flow for the Grillfürst Independence P530E integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    DEFAULT_PROTOCOL_VERSION,
    DOMAIN,
    MODEL,
    PROTOCOL_VERSIONS,
)
from .coordinator import CannotConnect, fetch_status

_LOGGER = logging.getLogger(__name__)

TUYA_LOCAL_DOMAIN = "tuya_local"


class GrillConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the local connection details of the grill."""

    VERSION = 1

    def _defaults_from_tuya_local(self) -> dict[str, Any]:
        """Prefill the form from an existing Tuya Local entry, if there is one."""
        for entry in self.hass.config_entries.async_entries(TUYA_LOCAL_DOMAIN):
            data = entry.data
            if data.get(CONF_DEVICE_ID) and data.get(CONF_LOCAL_KEY):
                version = str(data.get(CONF_PROTOCOL_VERSION, DEFAULT_PROTOCOL_VERSION))
                return {
                    CONF_HOST: data.get(CONF_HOST, ""),
                    CONF_DEVICE_ID: data[CONF_DEVICE_ID],
                    CONF_LOCAL_KEY: data[CONF_LOCAL_KEY],
                    CONF_PROTOCOL_VERSION: version
                    if version in PROTOCOL_VERSIONS
                    else DEFAULT_PROTOCOL_VERSION,
                }
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()
            try:
                await self.hass.async_add_executor_job(
                    fetch_status,
                    user_input[CONF_DEVICE_ID],
                    user_input[CONF_HOST],
                    user_input[CONF_LOCAL_KEY],
                    user_input[CONF_PROTOCOL_VERSION],
                )
            except (CannotConnect, OSError) as err:
                _LOGGER.debug("Connection test failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=MODEL, data=user_input)

        defaults = user_input or self._defaults_from_tuya_local()
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
                vol.Required(
                    CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, "")
                ): str,
                vol.Required(
                    CONF_LOCAL_KEY, default=defaults.get(CONF_LOCAL_KEY, "")
                ): str,
                vol.Required(
                    CONF_PROTOCOL_VERSION,
                    default=defaults.get(CONF_PROTOCOL_VERSION, DEFAULT_PROTOCOL_VERSION),
                ): vol.In(PROTOCOL_VERSIONS),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
