"""Repair issues for VSSL MX.

The amplifier is also a Google Cast target. Home Assistant derives the
``entity_id`` from the device name for entities with ``has_entity_name``, so
when both integrations use the vendor name the second one to register silently
gets a ``_2`` suffix. That happened in the field: ``media_player.ampli_medusa``
ended up being the *Cast* entity, the VSSL one became
``media_player.ampli_medusa_2`` and automations (plus the ESP32 dashboard of
this project) addressed the wrong device.

Since 0.2.0 the device name carries the model, so fresh installs do not
collide. For installs created before that, this module raises a repair issue
that names the integration holding the natural ``entity_id`` and explains how
to rename ours — deliberately *without* renaming anything automatically: the
old ``entity_id`` may be referenced by automations and by an ESP32 flashed with
it.
"""

from __future__ import annotations

import logging
import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_PREFIX = "entity_id_collision"
_SUFFIX_RE = re.compile(r"^(?P<base>media_player\..+?)_(?P<num>\d+)$")


def _issue_id(entry: ConfigEntry) -> str:
    return f"{ISSUE_PREFIX}_{entry.entry_id}"


async def async_check_entity_id_collision(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Create (or clear) the repair issue for a suffixed media_player entity."""
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)

    for item in entities:
        if item.domain != Platform.MEDIA_PLAYER:
            continue
        match = _SUFFIX_RE.match(item.entity_id)
        if not match:
            continue
        base_id = match.group("base")
        owner = registry.async_get(base_id)
        if owner is None or owner.config_entry_id == entry.entry_id:
            continue

        _LOGGER.debug(
            "Entity id collision for %s: %s is owned by %s",
            item.entity_id,
            base_id,
            owner.platform,
        )
        async_create_issue(
            hass,
            DOMAIN,
            _issue_id(entry),
            is_fixable=False,
            severity=IssueSeverity.WARNING,
            translation_key="entity_id_collision",
            translation_placeholders={
                "entity_id": item.entity_id,
                "base_id": base_id,
                "platform": owner.platform or "another integration",
            },
        )
        return

    # Nothing wrong (any more): drop a stale issue, if present.
    async_delete_issue(hass, DOMAIN, _issue_id(entry))
