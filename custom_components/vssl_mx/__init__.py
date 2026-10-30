"""VSSL MX integration for Home Assistant.

Controls VSSL MX-series amplifiers (MA.1, MS.1) over the NSDK API the device
exposes on port 80. No cloud, no IR, no extra services.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VsslMxApi
from .const import DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import VsslCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]

VsslConfigEntry = ConfigEntry[VsslCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: VsslConfigEntry) -> bool:
    """Set up the entry created by the config flow."""
    session = async_get_clientsession(hass)
    api = VsslMxApi(
        session,
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
    )
    coordinator = VsslCoordinator(
        hass,
        api,
        name=entry.title or entry.data[CONF_HOST],
        update_interval=DEFAULT_SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("VSSL MX listo en %s", entry.data[CONF_HOST])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VsslConfigEntry) -> bool:
    """Unload the platform when the entry is removed or reloaded."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
