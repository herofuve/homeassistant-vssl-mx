# VSSL MX

Local control of **VSSL MX-series** amplifiers (MA.1, MS.1) from Home Assistant using the
**NSDK** API the device exposes on the LAN. No cloud, no IR blaster.

A `media_player` with volume, mute, power on/network standby, play/pause, next/previous and
**real input selection** (AUX, SPDIF, COAX, HDMI, USB), plus title/artist/album when the
source publishes them.

Install: add `https://github.com/herofuve/homeassistant-vssl-mx` as a custom repository of
type **Integration** in HACS, download it, restart, then add the integration with the
amplifier IP address.
