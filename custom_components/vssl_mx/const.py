"""Constants for the VSSL MX integration.

Todo lo de este fichero está verificado contra un VSSL MA.1 con firmware
rc20 / 0.0.161.0xff2d7c5. Las rutas provienen de la API NSDK que expone el
propio equipo en el puerto 80 y del APK oficial (com.vssl.app.sx v2.1.5).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "vssl_mx"

DEFAULT_PORT: Final = 80
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=5)
REQUEST_TIMEOUT: Final = 10

# --- Rutas NSDK -------------------------------------------------------------
PATH_DEVICE_NAME: Final = "settings:/deviceName"
PATH_VERSION: Final = "settings:/version"
PATH_BOARD_NAME: Final = "settings:/system/boardName"
PATH_MANUFACTURER: Final = "settings:/system/manufacturer"

PATH_VOLUME: Final = "player:volume"
PATH_MUTE: Final = "settings:/mediaPlayer/mute"
PATH_MAX_VOLUME: Final = "settings:/mediaPlayer/maxVolume"

PATH_PLAYER_DATA: Final = "player:player/data/value"
PATH_PLAYER_CONTROL: Final = "player:player/control"

PATH_POWER_TARGET: Final = "powermanager:target"
PATH_POWER_ONLINE: Final = "ui:/poweronline"
PATH_POWER_STANDBY: Final = "ui:/powernetworkstandby"

PATH_FIND_ME: Final = "vssl:/findMeEnabled"

# URI de recurso que espera el equipo al activar una entrada local.
# Sin este bloque (y sin la lista "resources") responde
# "Failed to start playback, internal streamer error".
RESOURCE_URI: Final = (
    "alsa://aux_plug?rate=48000?channels=2?format=S16LE"
    "?latency-time=5000?buffer-time=50000?ts-offset=20000"
)
RESOURCE_MIME: Final = "audio/unknown"

# --- Entradas físicas -------------------------------------------------------
# key -> (path NSDK, serviceID del equipo, icono, nombre visible en HA)
INPUTS: Final[dict[str, dict[str, str]]] = {
    "aux": {
        "path": "ui:/auxaux_plug",
        "service": "AUX",
        "icon": "skin:iconAUX",
        "name": "AUX",
    },
    "spdif": {
        "path": "ui:/spdifinaux_plug",
        "service": "SPDIFIN",
        "icon": "skin:iconOptics",
        "name": "SPDIF",
    },
    "coax": {
        "path": "ui:/coaxinaux_plug",
        "service": "COAXIN",
        "icon": "skin:iconOptics",
        "name": "COAX",
    },
    "hdmi": {
        "path": "ui:/hdmiaux_plug",
        "service": "HDMI",
        "icon": "skin:iconHdmi",
        "name": "HDMI",
    },
    "usb": {
        "path": "ui:/usbMemaux_plug",
        "service": "Storage",
        "icon": "skin:iconUsb",
        "name": "USB",
    },
}

SOURCE_LIST: Final[list[str]] = [spec["name"] for spec in INPUTS.values()]

# serviceID que reporta el equipo -> nombre visible (incluye fuentes de red)
SOURCE_NAME_BY_SERVICE: Final[dict[str, str]] = {
    **{spec["service"]: spec["name"] for spec in INPUTS.values()},
    "googlecast": "Google Cast",
    "airplay": "AirPlay",
    "bluetooth": "Bluetooth",
    "spotify": "Spotify",
    "tidalconnect": "TIDAL",
    "upnp": "UPnP",
    "roon": "Roon",
}

# Nombre visible -> key de INPUTS (para async_select_source)
INPUT_KEY_BY_NAME: Final[dict[str, str]] = {
    spec["name"]: key for key, spec in INPUTS.items()
}

# --- Comandos de transporte (PlayerCommand.control) -------------------------
TRANSPORT_PLAY: Final = "play"
TRANSPORT_PAUSE: Final = "pause"
TRANSPORT_STOP: Final = "stop"
TRANSPORT_NEXT: Final = "next"
TRANSPORT_PREVIOUS: Final = "previous"

PLAYER_STATE_MAP: Final[dict[str, str]] = {
    "playing": "playing",
    "paused": "paused",
    "stopped": "stopped",
    "transitioning": "transitioning",
    "buffering": "buffering",
}
