"""Polling coordinator talking to the grill over the local Tuya protocol."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time
from typing import Any

import tinytuya

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .analytics import GrillAnalytics

from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    DEFAULT_PROTOCOL_VERSION,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


# Measured values the controller only reports on request
REFRESH_DPS = [101, 102, 103, 104, 105, 119, 120, 121, 124, 126]


class CannotConnect(Exception):
    """Raised when the grill does not answer with a valid status."""


def fetch_status(
    device_id: str, host: str, local_key: str, protocol_version: str
) -> dict[str, Any]:
    """Read the current DPs from the grill (blocking, run in an executor)."""
    device = tinytuya.Device(device_id, host, local_key, version=float(protocol_version))
    device.set_socketPersistent(True)
    device.set_socketTimeout(5)
    device.set_socketRetryLimit(1)
    fresh: dict[str, Any] = {}
    try:
        # The Wi-Fi module answers status() from a cache; the grill's controller only
        # reports new probe/chamber values when asked to refresh them (the app does this).
        try:
            device.updatedps(index=REFRESH_DPS, nowait=True)
            device.set_socketTimeout(1.5)
            for _ in range(4):
                msg = device.receive()
                if not isinstance(msg, dict):
                    break
                if isinstance(msg.get("dps"), dict):
                    fresh.update(msg["dps"])
            device.set_socketTimeout(5)
        except Exception as err:  # noqa: BLE001 - refresh is best effort
            _LOGGER.debug("DP refresh failed: %s", err)
        result = device.status()
    finally:
        device.close()
    if not isinstance(result, dict) or "Error" in result or "dps" not in result:
        raise CannotConnect(str(result))
    if fresh:
        _LOGGER.debug("Refreshed DPs %s", fresh)
    return {**result["dps"], **fresh}


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


def discover_host(device_id: str) -> str | None:
    """Listen for the grill's UDP broadcast and return its current IP (blocking, ~20 s)."""
    try:
        result = tinytuya.find_device(dev_id=device_id)
    except Exception as err:  # noqa: BLE001 - discovery is best effort
        _LOGGER.debug("Discovery failed: %s", err)
        return None
    ip = result.get("ip") if isinstance(result, dict) else None
    return ip if isinstance(ip, str) and ip else None


# After a failed poll, look for a changed IP at most this often
DISCOVERY_INTERVAL = 10 * 60


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
        self._last_discovery = 0.0
        self.analytics = GrillAnalytics()
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
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
        # Update entities without restarting the poll interval
        # (async_set_updated_data would push the next poll back).
        self.data = dict(self._dps)
        self.async_update_listeners()

    async def async_load(self) -> None:
        """Restore totals and the last session from storage."""
        self.analytics = GrillAnalytics.from_dict(await self._store.async_load())

    def _feed(self, dps: dict[str, Any] | None) -> None:
        self.analytics.update(time.time(), dps)
        self._store.async_delay_save(self.analytics.as_dict, 60)

    async def _fetch(self) -> dict[str, Any]:
        async with self._lock:
            return await self.hass.async_add_executor_job(
                fetch_status,
                self.device_id,
                self._host,
                self._local_key,
                self._protocol_version,
            )

    async def _rediscover(self) -> bool:
        """The grill may have a new IP (DHCP): find it via its broadcast and store it."""
        now = time.time()
        if now - self._last_discovery < DISCOVERY_INTERVAL:
            return False
        self._last_discovery = now
        ip = await self.hass.async_add_executor_job(discover_host, self.device_id)
        if not ip or ip == self._host:
            return False
        _LOGGER.warning("Grill found at new IP %s (was %s), updating the configuration", ip, self._host)
        self._host = ip
        self.hass.config_entries.async_update_entry(
            self.config_entry, data={**self.config_entry.data, CONF_HOST: ip}
        )
        return True

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            dps = await self._fetch()
        except (CannotConnect, OSError) as err:
            dps = None
            if await self._rediscover():
                try:
                    dps = await self._fetch()
                except (CannotConnect, OSError):
                    dps = None
            if dps is None:
                self._feed(None)
                raise UpdateFailed(f"Grill did not answer: {err}") from err

        _LOGGER.debug("Grill reported %s", dps)
        self._dps.update(dps)
        self._feed(self._dps)
        return dict(self._dps)
