"""Data coordinator for the VSSL MX integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    VsslApiError,
    VsslConnectionError,
    VsslMxApi,
    parse_player_value,
    unwrap,
)
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PATH_MUTE,
    PATH_PLAYER_DATA,
    PATH_POWER_TARGET,
    PATH_VOLUME,
    SOURCE_NAME_BY_SERVICE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class VsslState:
    """Amplifier state snapshot."""

    power: str = "unknown"
    volume: int = 0
    muted: bool = False
    player_state: str = "stopped"
    source_id: str | None = None
    source_name: str | None = None
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    duration: int | None = None
    progress: int | None = None

    @property
    def is_on(self) -> bool:
        return self.power == "online"


class VsslCoordinator(DataUpdateCoordinator[VsslState]):
    """Polls the device every few seconds."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: VsslMxApi,
        name: str,
        update_interval=DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{name}",
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> VsslState:
        try:
            power, volume, muted, raw_player = await asyncio.gather(
                self.api.get_value(PATH_POWER_TARGET),
                self.api.get_data(PATH_VOLUME, "value"),
                self.api.get_value(PATH_MUTE),
                self.api.get_data(PATH_PLAYER_DATA, "value"),
            )
        except VsslConnectionError as err:
            raise UpdateFailed(f"Cannot reach the VSSL device: {err}") from err
        except VsslApiError as err:
            raise UpdateFailed(f"VSSL API error: {err}") from err

        player = parse_player_value(raw_player)
        source_id = player.get("service_id")
        state = VsslState(
            power=_power_string(power),
            volume=_as_int(unwrap(volume)),
            muted=bool(unwrap(muted)),
            player_state=player.get("state") or "stopped",
            source_id=source_id,
            source_name=SOURCE_NAME_BY_SERVICE.get(str(source_id), source_id),
            title=player.get("title"),
            artist=player.get("artist"),
            album=player.get("album"),
            duration=_as_int(player.get("duration")),
            progress=_as_int(player.get("progress")),
        )
        _LOGGER.debug("VSSL state: %s", state)
        return state


def _power_string(value: Any) -> str:
    """powermanager:target devuelve {'powerTarget': {'target': 'online'}}."""
    if isinstance(value, dict):
        target = value.get("powerTarget") or value
        if isinstance(target, dict):
            return str(target.get("target") or "unknown")
    if isinstance(value, str):
        return value
    return "unknown"


def _as_int(value: Any) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
