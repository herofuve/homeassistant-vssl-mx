"""Config flow for VSSL MX: asks for the IP and validates it against the device."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VsslConnectionError, VsslError, VsslMxApi
from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class VsslMxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Amplifier setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            api = VsslMxApi(
                async_get_clientsession(self.hass), host, port
            )
            try:
                identity = await api.get_identity()
            except VsslConnectionError as err:
                _LOGGER.debug("Could not connect to %s: %s", host, err)
                errors["base"] = "cannot_connect"
            except VsslError as err:
                _LOGGER.debug("Unexpected response from %s: %s", host, err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating %s", host)
                errors["base"] = "unknown"
            else:
                if not identity.get("name"):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(
                        str(identity.get("mac") or f"{host}:{port}")
                    )
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: host, CONF_PORT: port}
                    )
                    return self.async_create_entry(
                        title=str(identity.get("name") or host),
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            "identity": identity,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )
