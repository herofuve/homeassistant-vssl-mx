"""Async client for the VSSL MX NSDK API.

Only depends on aiohttp (shipped with Home Assistant) and imports nothing from
Home Assistant, so it can be tested against the device from a plain script.

Device endpoints (port 80, plain HTTP, no authentication):

    GET  /api/getData?path=<module:/path>&roles=<role[,role]>|@all
    GET  /api/getRows?path=<container>&roles=@all&from=0&to=N
    POST /api/setData  {"path":..,"role":..,"value":..}
    POST /api/event/modifyQueue   -> queueId
    GET  /api/event/pollQueue     -> long-poll de eventos
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import aiohttp

from .const import (
    BT_DEVICE_PREFIX,
    DEFAULT_PORT,
    INPUTS,
    NETWORK_SOURCES,
    PATH_BLUETOOTH_UI,
    PATH_DEVICE_NAME,
    PATH_MUTE,
    PATH_PLAYER_CONTROL,
    PATH_PLAYER_DATA,
    PATH_POWER_ONLINE,
    PATH_POWER_STANDBY,
    PATH_VOLUME,
    REQUEST_TIMEOUT,
    RESOURCE_MIME,
    RESOURCE_URI,
    TRANSPORT_NEXT,
    TRANSPORT_PAUSE,
    TRANSPORT_PLAY,
    TRANSPORT_PREVIOUS,
    TRANSPORT_STOP,
)

_LOGGER = logging.getLogger(__name__)

_MAC_RE = re.compile(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})")


class VsslError(Exception):
    """Generic NSDK API error."""


class VsslConnectionError(VsslError):
    """Could not talk to the device."""


class VsslApiError(VsslError):
    """The device answered with an application-level error."""


def unwrap(values: Any) -> Any:
    """Convierte [{"type":"i32_","i32_":45}] -> 45.

    NSDK returns typed values; this returns the plain Python value.
    Also accepts a bare dict or a scalar.
    """
    if isinstance(values, list):
        if not values:
            return None
        values = values[0]
    if isinstance(values, dict):
        vtype = values.get("type")
        if vtype in ("i16_", "i32_", "i64_", "bool_", "double_", "string_"):
            return values.get(vtype)
        if vtype:
            return values.get(vtype)
        return values
    return values


class VsslMxApi:
    """Minimal device client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._session = session
        self.host = host
        self.port = port

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    # ------------------------------------------------------------------ HTTP
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                params=params,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                text = await resp.text()
                if resp.status >= 500 and text.lstrip().startswith("{"):
                    raise VsslApiError(self._error_message(text))
                if resp.status >= 400:
                    raise VsslApiError(f"HTTP {resp.status} en {path}")
                if not text:
                    return None
                try:
                    return json.loads(text)
                except json.JSONDecodeError as err:
                    raise VsslApiError(f"Respuesta no JSON en {path}") from err
        except asyncio.TimeoutError as err:
            raise VsslConnectionError(f"Timeout talking to {self.host}") from err
        except aiohttp.ClientError as err:
            raise VsslConnectionError(f"Network error with {self.host}: {err}") from err

    @staticmethod
    def _error_message(text: str) -> str:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return text[:120]
        error = data.get("error") or {}
        return error.get("message") or error.get("name") or str(data)[:120]

    # --------------------------------------------------------------- Reading
    async def get_data(self, nspath: str, roles: str = "value") -> Any:
        """Returns the requested list of roles (typed NSDK values)."""
        return await self._request(
            "GET",
            "/api/getData",
            params={"path": nspath, "roles": roles, "_nocache": "1"},
        )

    async def get_value(self, nspath: str) -> Any:
        """Returns the already unwrapped value."""
        return unwrap(await self.get_data(nspath, "value"))

    async def get_rows(self, nspath: str, start: int = 0, end: int = 100) -> list[dict]:
        data = await self._request(
            "GET",
            "/api/getRows",
            params={
                "path": nspath,
                "roles": "@all",
                "from": str(start),
                "to": str(end),
                "_nocache": "1",
            },
        )
        if isinstance(data, dict):
            return data.get("rows", [])
        return []

    async def get_identity(self) -> dict[str, Any]:
        """Name, version, model and MAC (for the device registry)."""
        name, version, board, mac = await asyncio.gather(
            self.get_value(PATH_DEVICE_NAME),
            self.get_value("settings:/version"),
            self.get_value("settings:/system/boardName"),
            self.get_mac(),
            return_exceptions=True,
        )
        def _clean(value: Any) -> Any:
            return None if isinstance(value, BaseException) else value
        return {
            "name": _clean(name),
            "version": _clean(version),
            "model": _clean(board),
            "mac": _clean(mac),
        }

    async def get_mac(self) -> str | None:
        """The real MAC lives in the device web UI (/index.fcgi -> networkInfo).

        The JSON is escaped inside a <script>, so searching for a literal
        '"mac":"' does not work: the "wired" block is located and the first
        MAC after it (eth0) is taken, falling back to any valid MAC.
        """
        try:
            async with self._session.get(
                f"{self.base_url}/index.fcgi",
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                html = await resp.text()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return None

        wired = html.find("wired")
        if wired >= 0:
            match = _MAC_RE.search(html, wired)
            if match:
                return match.group(1).upper()
        for match in _MAC_RE.finditer(html):
            mac = match.group(1).upper()
            if mac != "00:00:00:00:00:00":
                return mac
        return None

    async def get_player_state(self) -> dict[str, Any]:
        """Extracts state/input/track from player:player/data/value."""
        raw = await self.get_data(PATH_PLAYER_DATA, "value")
        return parse_player_value(raw)

    # --------------------------------------------------------------- Writing
    async def set_value(
        self, nspath: str, value: Any, role: str = "value", vtype: str | None = None
    ) -> Any:
        if isinstance(value, bool):
            vtype = vtype or "bool_"
        elif isinstance(value, int):
            vtype = vtype or "i32_"
        elif isinstance(value, float):
            vtype = vtype or "double_"
        elif isinstance(value, str):
            vtype = vtype or "string_"
        nsdk_value = value if vtype is None else {"type": vtype, vtype: value}
        return await self._request(
            "POST",
            "/api/setData",
            payload={"path": nspath, "role": role, "value": nsdk_value},
        )

    async def activate(self, nspath: str, value: dict[str, Any] | None = None) -> Any:
        return await self._request(
            "POST",
            "/api/setData",
            payload={"path": nspath, "role": "activate", "value": value or {}},
        )

    async def set_volume(self, volume: int) -> None:
        await self.set_value(PATH_VOLUME, max(0, min(100, int(volume))))

    async def set_mute(self, muted: bool) -> None:
        await self.set_value(PATH_MUTE, bool(muted))

    async def set_power(self, on: bool) -> None:
        await self.activate(PATH_POWER_ONLINE if on else PATH_POWER_STANDBY)

    async def set_find_me(self, enabled: bool) -> None:
        await self.set_value(PATH_FIND_ME, bool(enabled))

    async def select_input(self, key: str) -> None:
        """Activates a physical input: aux|spdif|coax|hdmi|usb."""
        spec = INPUTS.get(key.lower())
        if spec is None:
            raise VsslApiError(f"Unknown input: {key}")
        await self._player_command(
            {
                "control": TRANSPORT_PLAY,
                "mediaRoles": {
                    "type": "audio",
                    "path": spec["path"],
                    "icon": spec["icon"],
                    "mediaData": {
                        "metaData": {"serviceID": spec["service"]},
                        "resources": [
                            {"uri": RESOURCE_URI, "mimeType": RESOURCE_MIME}
                        ],
                    },
                },
            }
        )

    async def transport(self, command: str) -> None:
        """play|pause|stop|next|previous on player:player/control."""
        await self._player_command({"control": command})

    async def get_network_sources(self) -> dict[str, str]:
        """Network sources usable *right now*, as {name shown in HA: action path}.

        Physical inputs are not included: those go through select_input(). A
        service is offered only when its action node is not ``disabled``.
        """
        sources: dict[str, str] = {}
        for spec in NETWORK_SOURCES.values():
            try:
                data = await self.get_data(spec["path"], "@all")
            except VsslError:
                continue
            node = data[0] if isinstance(data, list) else data
            if not isinstance(node, dict) or node.get("disabled"):
                continue
            sources[spec["name"]] = spec["path"]

        for name, path in await self._bluetooth_sources():
            sources.setdefault(name, path)
        return sources

    async def _bluetooth_sources(self) -> list[tuple[str, str]]:
        """Paired Bluetooth devices that can be connected right now."""
        try:
            rows = await self.get_rows(PATH_BLUETOOTH_UI, 0, 40)
        except VsslError:
            return []

        found: list[tuple[str, str]] = []
        for row in rows:
            path = str(row.get("path") or "")
            if not path.startswith(BT_DEVICE_PREFIX):
                continue
            base = path.split("/section")[0]
            label = row.get("title") or base.rsplit("/", 1)[-1]
            play_path = f"{base}/play"
            try:
                data = await self.get_data(play_path, "@all")
            except VsslError:
                continue
            node = data[0] if isinstance(data, list) else data
            if not isinstance(node, dict) or node.get("disabled"):
                continue
            found.append((f"Bluetooth {label}", play_path))
        return found

    async def _player_command(self, value: dict[str, Any]) -> Any:
        # The payload goes as-is in "value": it must NOT be wrapped in an NSDK type.
        return await self.activate(PATH_PLAYER_CONTROL, value)

    # Semantic aliases for the media player
    async def play_pause(self) -> None:
        await self.transport(TRANSPORT_PAUSE)  # the device treats it as a toggle

    async def media_stop(self) -> None:
        await self.transport(TRANSPORT_STOP)

    async def media_next(self) -> None:
        await self.transport(TRANSPORT_NEXT)

    async def media_previous(self) -> None:
        await self.transport(TRANSPORT_PREVIOUS)


def parse_player_value(raw: Any) -> dict[str, Any]:
    """Normaliza la respuesta de player:player/data/value.

    Acepta tanto [{"type":"playLogicData","playLogicData":{...}}] como
    {"value":{"playLogicData":{...}}}.
    """
    node = unwrap(raw)
    if isinstance(node, dict):
        # unwrap returns the type dict because "playLogicData" is not a simple type
        play = node.get("playLogicData", node)
    else:
        play = {}
    if not isinstance(play, dict):
        play = {}

    roles = play.get("trackRoles") or {}
    if not isinstance(roles, dict):
        roles = {}
    media = (roles.get("mediaData") or {}).get("metaData") or {}
    if not isinstance(media, dict):
        media = {}

    def _text(node_value: Any) -> str | None:
        if isinstance(node_value, dict):
            return node_value.get("text")
        if isinstance(node_value, str):
            return node_value
        return None

    return {
        "state": play.get("state"),
        "service_id": media.get("serviceID") or media.get("serviceName"),
        "service_name": media.get("serviceName"),
        "title": _text(roles.get("title")),
        "artist": _text(roles.get("artist")),
        "album": _text(roles.get("album")),
        "duration": roles.get("duration"),
        "progress": play.get("progress"),
    }
