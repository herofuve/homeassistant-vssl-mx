"""Config and options flow for VSSL MX."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VsslConnectionError, VsslError, VsslMxApi
from .const import CONF_ENTITY_NAME, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class VsslMxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Amplifier setup."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> "VsslMxOptionsFlow":
        """Return the options flow (endpoint and entity name)."""
        return VsslMxOptionsFlow()

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


class VsslMxOptionsFlow(OptionsFlow):
    """Change the endpoint and the entity name without re-adding the entry.

    Two reasons this exists:

    * The amplifier's address changes (DHCP, VLAN move, Tailscale). Re-adding
      the entry would create new entities and break every automation, so the
      host lives here instead.
    * The entity name decides the ``entity_id`` (``has_entity_name``), and the
      Google Cast integration usually takes ``media_player.<device name>``
      first. Appending the model avoids that collision; this field lets the
      user override it deliberately.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self.config_entry
        current_host = str(entry.options.get(CONF_HOST, entry.data.get(CONF_HOST, "")))
        current_port = int(
            entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT))
        )
        current_name = str(entry.options.get(CONF_ENTITY_NAME, "") or "")

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            entity_name = str(user_input.get(CONF_ENTITY_NAME, "") or "").strip()
            api = VsslMxApi(async_get_clientsession(self.hass), host, port)
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
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_HOST: host,
                            CONF_PORT: port,
                            "identity": identity,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_create_entry(
                        title="",
                        data={CONF_ENTITY_NAME: entity_name},
                    )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_host): str,
                    vol.Optional(CONF_PORT, default=current_port): int,
                    vol.Optional(CONF_ENTITY_NAME, default=current_name): str,
                }
            ),
            errors=errors,
        )
