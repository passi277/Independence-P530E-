"""Polling coordinator talking to the grill over the local Tuya protocol."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

import tinytuya

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    DEFAULT_PROTOCOL_VERSION,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """Raised when the grill does not answer with a valid status."""


def fetch_status(
    device_id: str, host: str, local_key: str, protocol_version: str
) -> dict[str, Any]:
    """Read the current DPs from the grill (blocking, run in an executor)."""
    device = tinytuya.Device(device_id, host, local_key, version=float(protocol_version))
    device.set_socketPersistent(False)
    device.set_socketTimeout(5)
    device.set_socketRetryLimit(1)
    try:
        result = device.status()
    finally:
        device.close()
    if not isinstance(result, dict) or "Error" in result or "dps" not in result:
        raise CannotConnect(str(result))
    return result["dps"]


def send_value(
    device_id: str,
    host: str,
    local_key: str,
    protocol_version: str,
    dp: str,
    value: Any,
) -> None:
    """Write one DP to the grill (blocking, run in an executor)."""
    device = tinytuya.Device(device_id, host, local_key, version=float(protocol_version))
    device.set_socketPersistent(False)
    device.set_socketTimeout(5)
    device.set_socketRetryLimit(1)
    try:
        result = device.set_value(int(dp), value)
    finally:
        device.close()
    if isinstance(result, dict) and "Error" in result:
        raise CannotConnect(str(result))


class GrillCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the grill and keeps the last known value of every DP.

    In standby the grill only reports DPs 101-107, so values of the other
    DPs are kept from the last time the grill was awake.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.device_id: str = entry.data[CONF_DEVICE_ID]
        self._host: str = entry.data[CONF_HOST]
        self._local_key: str = entry.data[CONF_LOCAL_KEY]
        self._protocol_version: str = entry.data.get(
            CONF_PROTOCOL_VERSION, DEFAULT_PROTOCOL_VERSION
        )
        self._dps: dict[str, Any] = {}
        # Tuya devices handle only one local connection well: serialise all access.
        self._lock = asyncio.Lock()

    async def async_set_dp(self, dp: str, value: Any) -> None:
        """Write a DP and update the cached state."""
        async with self._lock:
            try:
                await self.hass.async_add_executor_job(
                    send_value,
                    self.device_id,
                    self._host,
                    self._local_key,
                    self._protocol_version,
                    dp,
                    value,
                )
            except (CannotConnect, OSError) as err:
                raise HomeAssistantError(f"Could not send command to the grill: {err}") from err
        self._dps[dp] = value
        self.async_set_updated_data(dict(self._dps))

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            async with self._lock:
                dps = await self.hass.async_add_executor_job(
                    fetch_status,
                    self.device_id,
                    self._host,
                    self._local_key,
                    self._protocol_version,
                )
        except CannotConnect as err:
            raise UpdateFailed(f"Grill did not answer: {err}") from err
        except OSError as err:
            raise UpdateFailed(f"Connection error: {err}") from err

        _LOGGER.debug("Grill reported %s", dps)
        self._dps.update(dps)
        return dict(self._dps)
