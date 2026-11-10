Adds the **Streaming** input, plus everything from 0.2.0.

## New in 0.2.1 — the Streaming input
The VSSL app lists a fifth input called *Streaming* next to the physical ones. Home Assistant
now offers it too: it hands the output to the internal streamer, so whichever service is
playing (Spotify Connect, AirPlay, Cast) takes over instead of a cable.

It has no readable node in the device API, so it was captured by watching the amplifier
while the app switched to it: `ui:/streamaux_plug` with `skin:iconStream`, reusing the same
ALSA resource as AUX.

`source_list` is now `Streaming, AUX, SPDIF, COAX, HDMI, USB, Spotify, Bluetooth <device>`.
Service name lookups became case-insensitive, because the device reports `Spotify` when the
streamer drives playback and `spotify` for a Connect session.

## 0.2.0 — streaming sources and an editable endpoint
- Source list includes the streaming services the amplifier can start right now: Spotify,
  AirPlay and each paired Bluetooth device.
- Google Cast and UPnP cannot be selected: the amplifier exposes no command for them, they
  take over when a stream arrives (they still show as the current source while active).
- Selecting a source that is not available raises an error instead of failing silently.
- New repair issue when the `entity_id` collides with another integration (Google Cast):
  it names the integration holding the natural name instead of silently keeping a `_2`
  suffix. Nothing is renamed automatically.
- Entity name carries the model (`Living room (MA1)`), so a clean install does not collide.
- Options flow: change the IP/port (DHCP, VLAN, Tailscale) and the entity name without
  deleting the entry.

## Verified on hardware
VSSL MA1, firmware rc20, reached over Tailscale:
- `source_list` = `Streaming, AUX, SPDIF, COAX, HDMI, USB, Spotify, Bluetooth QT68D`
- selecting Spotify switched `serviceID` from `SPDIFIN` to `spotify` in under 3 s
- selecting Streaming switched the path to `ui:/streamaux_plug` (reply 17)
- the amplifier was restored to SPDIF after every test
