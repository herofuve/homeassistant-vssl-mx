"""Data coordinator for the VSSL MX integration."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    VsslApiError,
    VsslConnectionError,
    VsslError,
    VsslMxApi,
    parse_player_value,
    unwrap,
)
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    NETWORK_SOURCE_REFRESH,
    PATH_MUTE,
    PATH_PLAYER_DATA,
    PATH_POWER_TARGET,
    PATH_VOLUME,
    SOURCE_LIST,
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
    # name shown in HA -> action path to activate it
    network_sources: dict[str, str] = field(default_factory=dict)

    @property
    def is_on(self) -> bool:
        return self.power == "online"

    @property
    def source_list(self) -> list[str]:
        """Physical inputs first, then the network sources that work right now."""
        return [*SOURCE_LIST, *self.network_sources]


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
        self._sources: dict[str, str] = {}
        self._sources_at: float = 0.0

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
            player_state=_player_state(player.get("state"), player.get("path")),
            source_id=source_id,
            source_name=_source_name(source_id),
            title=player.get("title"),
            artist=player.get("artist"),
            album=player.get("album"),
            duration=_as_int(player.get("duration")),
            progress=_as_int(player.get("progress")),
            network_sources=await self._async_network_sources(),
        )
        _LOGGER.debug("VSSL state: %s", state)
        return state

    async def _async_network_sources(self) -> dict[str, str]:
        """Which streaming sources can be activated right now.

        Probing them costs one request per service, so the result is cached:
        availability changes when a session starts or a device pairs, not on
        every poll. Never raises: a failure here must not take the poll down.
        """
        if (
            self._sources
            and time.monotonic() - self._sources_at < NETWORK_SOURCE_REFRESH
        ):
            return self._sources
        try:
            sources = await self.api.get_network_sources()
        except (VsslError, VsslConnectionError) as err:
            _LOGGER.debug("Could not probe network sources: %s", err)
            return self._sources
        self._sources = sources
        self._sources_at = time.monotonic()
        return sources

    def invalidate_network_sources(self) -> None:
        """Force a re-probe on the next poll (after selecting a source)."""
        self._sources_at = 0.0


LIVE_INPUT_PATH_SUFFIX = "_plug"


def _player_state(state: Any, path: Any) -> str:
    """Normalises the device's playLogicData.state.

    The amplifier never leaves ``transitioning`` on a live input (AUX, SPDIF,
    COAX, HDMI, Streaming): audio flows while the state stays there, so mapping
    it to IDLE made Home Assistant show *idle* with music playing. A live input
    with an active stream is PLAYING; a transitioning stream without a live path
    (a track that is still starting) stays transitioning, which HA shows as idle
    for a few seconds.

    Verified on hardware: SPDIF reports state=transitioning indefinitely while
    streaming audio; Spotify playback reports state=playing.
    """
    if not state:
        return "stopped"
    state = str(state)
    if state == "transitioning" and str(path or "").endswith(LIVE_INPUT_PATH_SUFFIX):
        return "playing"
    return state


def _source_name(source_id: Any) -> str | None:
    """Maps the reported serviceID to the name shown in Home Assistant.

    The device is inconsistent about capitalisation ("spotify" while playing
    from Spotify Connect, "Spotify" when the streamer reports itself), so the
    lookup is case-insensitive and falls back to whatever it reported.
    """
    if source_id in (None, ""):
        return None
    key = str(source_id)
    return (
        SOURCE_NAME_BY_SERVICE.get(key)
        or SOURCE_NAME_BY_SERVICE.get(key.lower())
        or key
    )


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
