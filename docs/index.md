---
title: "VSSL MX — Home Assistant integration"
description: "Control VSSL MA.1 and MS.1 amplifiers from Home Assistant over the local StreamSDK/NSDK API — volume, mute, power, play/pause and input selection (AUX, SPDIF, COAX, HDMI, USB), with no cloud and no IR blaster."
keywords: "VSSL MA.1, VSSL MS.1, VSSL Home Assistant, VSSL integration, HA custom integration, StreamSDK, NSDK, multi-room amplifier, HACS"
---

# VSSL MX — Home Assistant integration

Custom integration for Home Assistant that controls **VSSL MX-series** amplifiers
(`MA.1`, `MS.1`) over the **NSDK / StreamSDK** API the device exposes on its own network
(port 80). No cloud account, no IR blaster, no extra hardware.

**[View the code and install instructions on GitHub →](https://github.com/herofuve/homeassistant-vssl-mx)**

## What you get

| Feature | Detail |
|---|---|
| Volume | Absolute 0-100 plus step up/down |
| Mute | Independent of volume |
| Power | On and network standby, works while the unit is asleep |
| Transport | Play/pause, stop, next, previous |
| **Input selection** | AUX, SPDIF, COAX, HDMI, USB — real discrete switching |
| Now playing | Title, artist and album when the source publishes them |

The integration creates one `media_player` entity and one device, with the amplifier name,
model and firmware version pulled from the unit itself.

## Install (HACS)

1. HACS → three-dot menu → **Custom repositories**
2. Add `https://github.com/herofuve/homeassistant-vssl-mx`, category **Integration**
3. Install **VSSL MX**, restart Home Assistant
4. *Settings → Devices & services → Add integration → VSSL MX* → enter the amplifier IP

Manual install and full documentation: see the
[README](https://github.com/herofuve/homeassistant-vssl-mx#readme).

## Which VSSL models does this work with?

- **MX series (supported):** `MA.1` single-zone streaming amplifier, `MS.1` streamer.
  Tested on `MA.1` firmware `rc20` / `0.0.161.0xff2d7c5`.
- **X series (`A.1`, `A.1x`, `A.3`, `A.3x`, `A.6x`): not supported.** Those speak a different
  protocol; use [`vsslctrl`](https://github.com/vsslctrl/integration.home-assistant) instead.
- **SX series (speaker/subwoofer): unverified.** Same StreamSDK platform, no hardware tested.

## Technical notes

The amplifier is a StreamSDK device: its web UI (`/index.fcgi`) loads `/jsapi/nsdk-api.js`,
which documents the JSON API used here (`/api/getData`, `/api/setData`, `/api/getRows`,
`/api/event/*`). The control paths and payloads were extracted from the official VSSL CNCT
app and then verified against real hardware — see
[PROTOCOL.md](PROTOCOL.html) for the full write-up.

## Roadmap

Multi-room / grouped playback is **not implemented yet**; the device supports it natively
(RTP distribution synchronised with PTP). Details and interim options are in the
[roadmap section](https://github.com/herofuve/homeassistant-vssl-mx#roadmap).

## Disclaimer

Independent project. Not affiliated with or endorsed by VSSL / Soundvision Technologies.
MIT licensed.
