"""media_player for the VSSL MA.1 / MX series over NSDK."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import VsslError
from .const import (
    CONF_ENTITY_NAME,
    DOMAIN,
    INPUT_KEY_BY_NAME,
    SOURCE_LIST,
    TRANSPORT_NEXT,
    TRANSPORT_PAUSE,
    TRANSPORT_PLAY,
    TRANSPORT_PREVIOUS,
    TRANSPORT_STOP,
)
from .coordinator import VsslCoordinator, VsslState
from .naming import build_device_name

_LOGGER = logging.getLogger(__name__)

STATE_MAP: dict[str, MediaPlayerState] = {
    "playing": MediaPlayerState.PLAYING,
    "paused": MediaPlayerState.PAUSED,
    "stopped": MediaPlayerState.IDLE,
    "transitioning": MediaPlayerState.IDLE,
    "buffering": MediaPlayerState.BUFFERING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Creates the player entity."""
    coordinator: VsslCoordinator = entry.runtime_data
    async_add_entities([VsslMediaPlayer(coordinator, entry)])


class VsslMediaPlayer(CoordinatorEntity[VsslCoordinator], MediaPlayerEntity):
    """Representa el amplificador VSSL."""

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_has_entity_name = True
    _attr_name = None
    _attr_source_list = SOURCE_LIST
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
    )

    def __init__(self, coordinator: VsslCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        identity = entry.data.get("identity") or {}
        mac = identity.get("mac")
        model = identity.get("model") or "MA1"
        # The device name decides the entity_id (has_entity_name), and Google
        # Cast registers the same amplifier with the same vendor name, so the
        # model is appended to keep both apart: "Ampli Medusa (MA1)".
        device_name = build_device_name(
            identity.get("name") or entry.title,
            model,
            entry.options.get(CONF_ENTITY_NAME),
        )
        host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
        self._attr_unique_id = f"{mac or entry.entry_id}-media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac or entry.entry_id)},
            manufacturer="VSSL",
            model=str(model),
            name=device_name,
            sw_version=identity.get("version"),
            configuration_url=f"http://{host}/",
        )

    # ----------------------------------------------------------------- State
    @property
    def _state(self) -> VsslState:
        return self.coordinator.data

    @property
    def state(self) -> MediaPlayerState | None:
        if not self._state.is_on:
            return MediaPlayerState.OFF
        return STATE_MAP.get(self._state.player_state, MediaPlayerState.IDLE)

    @property
    def volume_level(self) -> float | None:
        return self._state.volume / 100

    @property
    def is_volume_muted(self) -> bool | None:
        return self._state.muted

    @property
    def source(self) -> str | None:
        return self._state.source_name

    @property
    def source_list(self) -> list[str]:
        """Physical inputs plus the streaming services usable right now."""
        return self._state.source_list

    @property
    def media_title(self) -> str | None:
        return self._state.title

    @property
    def media_artist(self) -> str | None:
        return self._state.artist

    @property
    def media_album_name(self) -> str | None:
        return self._state.album

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "vssl_power": self._state.power,
            "vssl_source_id": self._state.source_id,
            "vssl_player_state": self._state.player_state,
        }

    # -------------------------------------------------------------- Commands
    async def async_set_volume_level(self, volume: float) -> None:
        await self.coordinator.api.set_volume(round(volume * 100))
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        current = self._state.volume
        await self.coordinator.api.set_volume(min(100, current + 1))
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        current = self._state.volume
        await self.coordinator.api.set_volume(max(0, current - 1))
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.api.set_mute(mute)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        """Switch to a physical input or start a network source.

        Physical inputs go through the mediaRoles payload of
        player:player/control; network sources (Spotify, AirPlay, a paired
        Bluetooth device) are "action" nodes the device must activate. Anything
        else is rejected loudly instead of being ignored.
        """
        key = INPUT_KEY_BY_NAME.get(source)
        path = self._state.network_sources.get(source)
        try:
            if key is not None:
                await self.coordinator.api.select_input(key)
            elif path is not None:
                await self.coordinator.api.activate(path)
            else:
                raise HomeAssistantError(
                    f"Source '{source}' cannot be selected right now. "
                    f"Available: {', '.join(self._state.source_list)}"
                )
        except VsslError as err:
            raise HomeAssistantError(
                f"Could not select source '{source}': {err}"
            ) from err
        self.coordinator.invalidate_network_sources()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self.coordinator.api.set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.api.set_power(False)
        await self.coordinator.async_request_refresh()

    async def async_media_play_pause(self) -> None:
        await self.coordinator.api.transport(TRANSPORT_PAUSE)
        await self.coordinator.async_request_refresh()

    async def async_media_play(self) -> None:
        await self.coordinator.api.transport(TRANSPORT_PLAY)
        await self.coordinator.async_request_refresh()

    async def async_media_pause(self) -> None:
        await self.coordinator.api.transport(TRANSPORT_PAUSE)
        await self.coordinator.async_request_refresh()

    async def async_media_stop(self) -> None:
        await self.coordinator.api.transport(TRANSPORT_STOP)
        await self.coordinator.async_request_refresh()

    async def async_media_next_track(self) -> None:
        await self.coordinator.api.transport(TRANSPORT_NEXT)
        await self.coordinator.async_request_refresh()

    async def async_media_previous_track(self) -> None:
        await self.coordinator.api.transport(TRANSPORT_PREVIOUS)
        await self.coordinator.async_request_refresh()
