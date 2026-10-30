"""Integración VSSL MX para Home Assistant.

Controla amplificadores VSSL de la serie MX (MA.1, MS.1) hablando la API
NSDK que el equipo expone en su puerto 80. No requiere HACS, ni IR, ni
nubes intermedias.
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
    """Configura la entrada creada por el config flow."""
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
    """Descarga la plataforma al eliminar o recargar la entrada."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
