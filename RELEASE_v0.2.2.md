Fixes the playback state on cabled inputs.

## Fixed
- With audio coming in through **AUX, SPDIF, COAX, HDMI or Streaming**, the amplifier reports
  `state: transitioning` permanently — not just while it starts. The integration mapped that
  to *idle*, so Home Assistant showed **idle while music was playing**. A transitioning
  stream that carries a live input path is now reported as playing; services that report
  their own state (Spotify, AirPlay) are untouched.
- `trackRoles.path` is now read from the device, so the decision is based on what the
  amplifier reports rather than on the input name.

## Verified on hardware
SPDIF reads `state=transitioning`, `path=ui:/spdifinaux_plug` and normalises to `playing`;
nine mapping cases covered (live inputs, playing, paused, stopped, buffering, no state).
