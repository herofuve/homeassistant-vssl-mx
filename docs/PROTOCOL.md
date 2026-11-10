---
title: "NSDK protocol reference"
description: "Reverse-engineered reference for the VSSL MX-series (MA.1, MS.1) local NSDK/StreamSDK API — endpoints, paths, playback commands, discrete input switching and ports."
keywords: "VSSL NSDK, StreamSDK API, VSSL MA.1 API, Home Assistant integration, reverse engineering"
---

# VSSL (MX series) NSDK protocol — reference

Everything below was verified against a **VSSL MA.1** running firmware `rc20` /
`0.0.161.0xff2d7c5`. The unit is a **StreamSDK** device from StreamUnlimited: its web UI
(`/index.fcgi`) is titled "StreamSDK Main Page" and loads `/jsapi/nsdk-api.js`, which
documents the API this integration uses.

## Transport

Plain HTTP, port **80**, no authentication.

```
GET  /api/getData?path=<module:/path>&roles=<role[,role]>|@all&_nocache=1
GET  /api/getRows?path=<container>&roles=@all&from=0&to=N
POST /api/setData    {"path": "...", "role": "...", "value": ...}
POST /api/event/modifyQueue {"queueId":"","subscribe":[{"path":..,"type":"itemWithValue"}],"unsubscribe":[]}
GET  /api/event/pollQueue?queueId=...
```

- Paths use the `module:/path` form (`settings:/deviceName`, `player:volume`).
- Values are typed objects: `{"type":"i32_","i32_":45}`, `bool_`, `string_`, `double_`.
- Unknown path -> HTTP 500 with `{"error":{"name":"CMAbstractWorker::invalidPath",...}}`.
- `getRows` on a **container** lists its children: the only way to discover the tree
  (there is no global module listing).
- `pollQueue` is a true long-poll: it blocks until an event arrives; the `timeout`
  parameter does not cut the wait short on this build.

## Relevant paths

| Purpose | Path | Type |
|---|---|---|
| Name | `settings:/deviceName` | value (string, writable) |
| Version | `settings:/version`, `settings:/versionSDK`, `settings:/releasetext` | value |
| Model | `settings:/system/boardName` (`VSSL MA1`), `productName` (`Mx series 2025`) | value |
| Volume | `player:volume` | value (i32 0-100) |
| Mute | `settings:/mediaPlayer/mute` | value (bool) |
| Max volume | `settings:/mediaPlayer/maxVolume`, `settings:/dsp/maxVolumeLimit` | value |
| EQ | `settings:/mediaPlayer/{bass,treble,balance,loudness,equalizerOnOff,subCrossoverFreq,subwooferLevel}` | value |
| BLAST LED | `settings:/leds/*` | value |
| **Playback control** | **`player:player/control`** | action |
| State / track | `player:player/data/value` | value (`playLogicData`) |
| Power target | `powermanager:target` (`online` / `networkStandby`) | value |
| Power on / standby | `ui:/poweronline`, `ui:/powernetworkstandby` | action |
| Find me | `vssl:/findMeEnabled` | value (bool) |
| Standby timer | `vssl:/standbyTimer/stop`, `vssl:/standbyTimer/remainingTime` | action/value |
| IR learning | `vssl:/learn/trigger`, `vssl:/learn/cancel` | action |

## Playback commands

Sent to the action node `player:player/control` with `role: "activate"`. The `PlayerCommand`
class in the official APK carries a `control` field:

```json
{"control": "pause"}          // play/pause (the firmware treats it as a toggle)
{"control": "next"}
{"control": "previous"}
{"control": "stop"}
{"control": "seekTime", "time": 42000}
{"control": "changePlayMode", "playMode": {...}}
```

## Input selection

Same node, with a `mediaRoles` payload. **The `resources` array is mandatory**: without it
the device answers `500 Failed to start playback, internal streamer error`.

```json
{
  "control": "play",
  "mediaRoles": {
    "type": "audio",
    "path": "ui:/auxaux_plug",
    "icon": "skin:iconAUX",
    "mediaData": {
      "metaData": {"serviceID": "AUX"},
      "resources": [{
        "uri": "alsa://aux_plug?rate=48000?channels=2?format=S16LE?latency-time=5000?buffer-time=50000?ts-offset=20000",
        "mimeType": "audio/unknown"
      }]
    }
  }
}
```

| Input | `path` | `serviceID` | icon |
|---|---|---|---|
| Line in (AUX) | `ui:/auxaux_plug` | `AUX` | `skin:iconAUX` |
| SPDIF in | `ui:/spdifinaux_plug` | `SPDIFIN` | `skin:iconOptics` |
| COAX in | `ui:/coaxinaux_plug` | `COAXIN` | `skin:iconOptics` |
| HDMI in | `ui:/hdmiaux_plug` | `HDMI` | `skin:iconHdmi` |
| USB Memory | `ui:/usbMemaux_plug` | `Storage` | `skin:iconUsb` |

A successful switch returns HTTP 200 with an integer (internal transition id) and is
confirmed by reading `player:player/data/value` ->
`playLogicData.trackRoles.mediaData.metaData.serviceID`.

## Playback state

`player:player/data/value` returns a `playLogicData` object with `state`
(`playing`/`paused`/`stopped`/`transitioning`) and `trackRoles` (title, artist, album,
`mediaData.metaData.serviceID`). TCP port **4545** additionally streams the same JSON
continuously (useful for *now playing* without polling).

## Ports on the MA.1

`80` web UI + NSDK API · `443` same UI over HTTPS · `4545` JSON state stream ·
`7000` AirPlay · `8008`/`8009` Google Cast · `16300`/`16500` development-`rc` firmware
artifacts (16500 is Syncthing) · `10001` TLS requiring a client certificate (the CNCT app
channel, unusable without the app).

The legacy X-series ports `50002` and `7777` **do not exist** on this hardware — which is
why the `vsslctrl` HACS integration fails with
`Error fetching zone info, is the zone connected?`.

## How this was found

The local web API exposes no transport control and no input selection: the browse tree
(`ui:`) can be listed but its rows are not addressable. The control paths and payloads came
from analysing the official **`com.vssl.app.sx` v2.1.5** APK (classes
`com.example.streamkit.data.network.ApiService` -> `activateValue(path, role)` and the
`model/valueactivator/PlayerCommand` package), extracting the DEX string constants with
`androguard`.

## Network sources: no "select input" command

Physical inputs are switched by sending a `mediaRoles` payload to
`player:player/control`. Streaming services work differently: they appear as **action
nodes** under the `ui:` tree and the amplifier marks them `"disabled": true` when they
cannot be used.

| Node | Meaning | Observed when |
|---|---|---|
| `spotify:/ui/resume` | Resume the Spotify Connect session | enabled (Spotify account linked) |
| `airplay:resumePlayback` | Resume AirPlay | `disabled`, title "No active session" |
| `bluetooth:devices/<MAC>/play` | Connect and play that paired speaker | enabled, title "Connect and play" |
| `bluetooth:devices/<MAC>/disconnect` | Disconnect | `disabled`, title "Not connected" |
| `bluetooth:deviceList/scan` | Start a scan | always enabled |

```http
POST /api/setData
{"path":"spotify:/ui/resume","role":"activate","value":{}}
```

Responds `null` and the player state flips to `serviceID: spotify` within one poll — this
is what `select_source` does for a network source.

**Google Cast and UPnP expose nothing to activate** (`ui:/googlecastlite` only offers
`openHomeApp` and "Learn More"; `ui:/upnp` has zero rows). They take over the amplifier
when a stream is pushed to it, so they can only be observed as the current `source`, never
selected.

The rows of the `ui:` tree for these services are *containers* (navigation only): requesting
`ui:/spotify` directly answers `invalidPath`. Only the action nodes above are addressable.

### The "Streaming" input

The VSSL app offers a fifth input called **Streaming** next to the physical ones. It is not
a readable node (`getData` on any `ui:/*_plug` path answers `invalidPath`, even for AUX), but
it *is* a valid `mediaRoles` target:

```json
{"path":"player:player/control","role":"activate","value":{
  "control":"play",
  "mediaRoles":{"type":"audio","path":"ui:/streamaux_plug","icon":"skin:iconStream",
    "mediaData":{"metaData":{"serviceID":"Stream"},
      "resources":[{"uri":"alsa://aux_plug?rate=48000?...","mimeType":"audio/unknown"}]}}}}
```

Verified on hardware: the reply is a new stream id and `playLogicData.trackRoles.path`
becomes `ui:/streamaux_plug`. It reuses the **same ALSA resource as AUX**
(`alsa://aux_plug`), which is why the play history labels it "VSSL Audio".

Note the `serviceID` the device reports afterwards is whatever the streamer is playing —
`"Spotify"` (capital S) when the streamer reports itself, `"spotify"` when the Connect
session drives it — so name lookups must be case-insensitive.
