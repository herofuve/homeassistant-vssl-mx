"""media_player para VSSL MA.1 / serie MX vía NSDK."""

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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
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
    """Crea el reproductor."""
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
        model = identity.get("model") or "MA.1"
        self._attr_unique_id = f"{mac or entry.entry_id}-media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac or entry.entry_id)},
            manufacturer="VSSL",
            model=str(model),
            name=identity.get("name") or entry.title,
            sw_version=identity.get("version"),
            configuration_url=f"http://{entry.data.get('host')}/",
        )

    # ------------------------------------------------------------- Estado
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

    # ----------------------------------------------------------- Comandos
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
        key = INPUT_KEY_BY_NAME.get(source)
        if key is None:
            _LOGGER.warning("Fuente no soportada por NSDK: %s", source)
            return
        await self.coordinator.api.select_input(key)
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
