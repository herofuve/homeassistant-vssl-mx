# VSSL MX

Control local de amplificadores **VSSL serie MX** (MA.1, MS.1) desde Home Assistant mediante
la API **NSDK** del propio equipo. Sin nube, sin infrarrojos.

Un `media_player` con volumen, mute, encendido/standby, play/pausa, siguiente/anterior y
**selección de entrada** (AUX, SPDIF, COAX, HDMI, USB), más título/artista/álbum cuando la
fuente los publica.

Instalación: añade `https://github.com/herofuve/homeassistant-vssl-mx` como repositorio
personalizado de tipo **Integración** en HACS, descarga, reinicia y añade la integración
indicando la IP del amplificador.
