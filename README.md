# VSSL MX — Home Assistant integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/herofuve/homeassistant-vssl-mx)](https://github.com/herofuve/homeassistant-vssl-mx/releases)
[![Validate](https://github.com/herofuve/homeassistant-vssl-mx/actions/workflows/validate.yml/badge.svg)](https://github.com/herofuve/homeassistant-vssl-mx/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/herofuve/homeassistant-vssl-mx)](LICENSE)

Local control of **VSSL MX-series** amplifiers (`MA.1`, `MS.1`) from Home Assistant, using the
**NSDK (StreamSDK)** API the device exposes on its own LAN port 80. No cloud, no IR blaster,
no extra services.

> **X series** (`A.1`, `A.1x`, `A.3`, `A.3x`, `A.6x`): that generation speaks a different
> protocol (TCP 50002/7777) and is **not** covered here — use the community integration
> [`vsslctrl`](https://github.com/vsslctrl/integration.home-assistant) for those units.
> **SX series** (speaker/subwoofer): same StreamSDK platform, not verified yet.

> ⚠️ Independent project. **Not affiliated with or endorsed by VSSL / Soundvision
> Technologies.** "VSSL" is a trademark of its respective owners.

## Status

| Tested firmware | Home Assistant | Version |
|---|---|---|
| MA.1 · `rc20` / `0.0.161.0xff2d7c5` | 2026.2.3 | 0.1.0 |

## What it does

A single `media_player` entity for the amplifier:

| Function | NSDK implementation |
|---|---|
| Absolute volume (0-100) and step up/down | `player:volume` |
| Mute | `settings:/mediaPlayer/mute` |
| Power on / network standby | `ui:/poweronline` · `ui:/powernetworkstandby` |
| Play/Pause, Stop, Next, Previous | `player:player/control` (`PlayerCommand`) |
| **Input selection**: AUX, SPDIF, COAX, HDMI, USB | `player:player/control` + `mediaRoles` payload |
| State, title, artist, album | `player:player/data/value` |

Network sources (Spotify, Google Cast, AirPlay, UPnP) show up as the current `source` when
active, but cannot be started from Home Assistant — they are started from their own app.

## Installation

### HACS (recommended)

1. HACS → three-dot menu → **Custom repositories**.
2. URL: `https://github.com/herofuve/homeassistant-vssl-mx` · Category: **Integration**.
3. Install **VSSL MX** and restart Home Assistant.
4. *Settings → Devices & services → Add integration → VSSL MX*.
5. Enter the amplifier IP address (port 80 by default).

### Manual

Copy `custom_components/vssl_mx/` into your `config/custom_components/` folder and restart.

## Requirements

- The amplifier must be reachable from Home Assistant on **port 80**.
  Quick check: `http://<ip>/index.fcgi` returns the "StreamSDK" page.
- For the power button to wake the unit from off, it must be in **network standby**
  (not unplugged).

## Known limitations

- Polling every 5 s (4 parallel HTTP requests); the NSDK event queue is not used yet, so a
  change made from another app can take up to 5 s to show up.
- `play/pause` is sent as the `pause` command, which the firmware treats as a *toggle*.
- `next/prev/stop/seek` only have an effect with an active network source; physical inputs
  have no transport.
- EQ, BLAST LED, presets and the standby timer are not exposed yet (planned for 0.2).

## Troubleshooting

```bash
curl "http://<ip>/api/getData?path=settings:/deviceName&roles=value"
# -> [{"type":"string_","string_":"Ampli Medusa"}]
```

Debug logging in Home Assistant:

```yaml
logger:
  logs:
    custom_components.vssl_mx: debug
```

## How it works (technical summary)

The unit is a StreamSDK device from StreamUnlimited. Its web UI (`/index.fcgi`) loads
`/jsapi/nsdk-api.js`, which documents the API:

```
GET  /api/getData?path=<module:/path>&roles=<role[@all]>
GET  /api/getRows?path=<container>&roles=@all&from=0&to=N
POST /api/setData {"path":..,"role":..,"value":..}
POST /api/event/modifyQueue    GET /api/event/pollQueue
```

The control paths (`player:player/control`, `powermanager:target`, `ui:/poweronline`, ...)
and the exact command payloads were extracted from the official VSSL CNCT app APK
(`com.vssl.app.sx`). Full details in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## License

MIT — see [LICENSE](LICENSE).
