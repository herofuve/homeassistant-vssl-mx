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


def endpoint(entry: ConfigEntry) -> tuple[str, int]:
    """Effective host/port: the options flow wins over the original entry data.

    The amplifier can move (DHCP, VLAN change, Tailscale address), so the
    endpoint has to be editable without deleting and re-adding the entry —
    otherwise every entity gets a new suffix and automations break.
    """
    host = str(entry.options.get(CONF_HOST, entry.data[CONF_HOST]))
    port = int(entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT)))
    return host, port


async def async_setup_entry(hass: HomeAssistant, entry: VsslConfigEntry) -> bool:
    """Set up the entry created by the config flow."""
    session = async_get_clientsession(hass)
    host, port = endpoint(entry)
    api = VsslMxApi(session, host, port)
    coordinator = VsslCoordinator(
        hass,
        api,
        name=entry.title or host,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("VSSL MX ready at %s:%s", host, port)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload after an options change (new IP, new entity name...)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: VsslConfigEntry) -> bool:
    """Unload the platform when the entry is removed or reloaded."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
