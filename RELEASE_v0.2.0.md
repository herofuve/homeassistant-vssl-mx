Streaming sources and an editable endpoint.

- Source list includes the streaming services the amplifier can start right now: Spotify,
  AirPlay and each paired Bluetooth device.
- Google Cast and UPnP cannot be selected: they expose no command to activate and take over
  when a stream arrives. They still show as the current source while active.
- New repair issue when the `entity_id` collides with another integration (Google Cast),
  naming the integration holding the natural name instead of silently keeping a `_2`.
- Entity name carries the model (`Living room (MA1)`), so a clean install does not collide.
- Options flow: change the IP/port and the entity name without deleting the entry.
