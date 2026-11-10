"""Naming helpers for the VSSL MX integration.

Why this file exists
--------------------
With ``has_entity_name`` enabled, Home Assistant derives an entity's
``entity_id`` from the *device* name. The amplifier is also a Google Cast
target, and the Cast integration uses the same device name (whatever the user
typed in the VSSL app), so a plain "<device name>" collides: whoever registers
first keeps ``media_player.<name>`` and the other integration silently ends up
with ``_2``. That is how ``media_player.ampli_medusa`` became the Cast entity
and the VSSL one became ``media_player.ampli_medusa_2``, with automations
(HACS and the ESP32 dashboard of this project) pointing at the wrong device.

Appending the model keeps both names distinct without depending on what the
user typed, and survives a rename in the vendor app.
"""

from __future__ import annotations


def short_model(model: str | None) -> str:
    """Turn a firmware model string into a short one: "VSSL MA1" -> "MA1".

    No dot is inserted on purpose: this string ends up in the entity_id, and
    ``media_player.ampli_medusa_ma1`` is friendlier in YAML than
    ``…_ma_1``. The firmware itself reports ``MA1`` / ``MS1``.
    """
    if not model:
        return ""
    return str(model).replace("VSSL", "").strip()


def build_device_name(
    device_name: str | None,
    model: str | None,
    override: str | None = None,
) -> str:
    """Return the device name used by Home Assistant.

    An explicit user override (options flow) always wins; otherwise the vendor
    name is suffixed with the model, e.g. ``Ampli Medusa (MA.1)``.
    """
    if override and str(override).strip():
        return str(override).strip()
    base = (device_name or "VSSL").strip() or "VSSL"
    model_short = short_model(model)
    return f"{base} ({model_short})" if model_short else base
