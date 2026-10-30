# VSSL MX — Home Assistant integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/herofuve/homeassistant-vssl-mx)](https://github.com/herofuve/homeassistant-vssl-mx/releases)
[![Validate](https://github.com/herofuve/homeassistant-vssl-mx/actions/workflows/validate.yml/badge.svg)](https://github.com/herofuve/homeassistant-vssl-mx/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/herofuve/homeassistant-vssl-mx)](LICENSE)

Control local de amplificadores **VSSL serie MX** (`MA.1`, `MS.1`) desde Home Assistant,
hablando la API **NSDK (StreamSDK)** que el propio equipo expone en el puerto 80.
Sin nube, sin HACS-dependencias, sin infrarrojos.

> Serie **X** (A.1, A.1x, A.3, A.3x, A.6x): esa generación usa otro protocolo (TCP 50002/7777)
> y **no** la cubre esta integración — para esos equipos está la integración de la comunidad
> [`vsslctrl`](https://github.com/vsslctrl/integration.home-assistant).
> Serie **SX** (altavoz/subwoofer): comparten plataforma StreamSDK, sin verificar todavía.

> ⚠️ Proyecto independiente. **No está afiliado ni respaldado por VSSL / Soundvision
> Technologies.** "VSSL" es marca de sus propietarios.

## Estado

| Firmware probado | Home Assistant | Versión |
|---|---|---|
| MA.1 · `rc20` / `0.0.161.0xff2d7c5` | 2026.2.3 | 0.1.0 |

## Qué hace

Un `media_player` completo para el amplificador:

| Función | Implementación NSDK |
|---|---|
| Volumen absoluto (0-100) y ± paso | `player:volume` |
| Mute | `settings:/mediaPlayer/mute` |
| Encendido / standby de red | `ui:/poweronline` · `ui:/powernetworkstandby` |
| Play/Pausa, Stop, Siguiente, Anterior | `player:player/control` (`PlayerCommand`) |
| **Selección de entrada**: AUX, SPDIF, COAX, HDMI, USB | `player:player/control` + payload `mediaRoles` |
| Estado, título, artista, álbum | `player:player/data/value` |

Las fuentes de red (Spotify, Google Cast, AirPlay, UPnP) aparecen como `source` cuando
están activas, pero no se pueden arrancar desde Home Assistant: se inician desde su app.

## Instalación

### HACS (recomendado)

1. HACS → menú de tres puntos → **Repositorios personalizados**.
2. URL: `https://github.com/herofuve/homeassistant-vssl-mx` · Categoría: **Integración**.
3. Instala **VSSL MX** y reinicia Home Assistant.
4. *Ajustes → Dispositivos y servicios → Añadir integración → VSSL MX*.
5. Introduce la IP del amplificador (el puerto es 80 por defecto).

### Manual

Copia `custom_components.vssl_mx/` a tu carpeta `config/custom_components/` y reinicia.

## Requisitos

- El amplificador debe ser alcanzable desde Home Assistant en el **puerto 80**.
  Comprobación: `http://<ip>/index.fcgi` muestra la página "StreamSDK".
- Para el botón de encendido desde apagado, el equipo debe estar en **standby de red**
  (no desenchufado).

## Limitaciones conocidas

- Sondeo cada 5 s (4 peticiones HTTP en paralelo); no usa todavía la cola de eventos NSDK,
  así que un cambio hecho desde otra app puede tardar hasta 5 s en reflejarse.
- `play/pause` se envía como comando `pause`, que el firmware interpreta como *toggle*.
- `next/prev/stop/seek` solo tienen efecto con una fuente de red activa; las entradas
  físicas no tienen transporte.
- No expone EQ, LED BLAST, presets ni temporizador de standby (previsto para 0.2).

## Diagnóstico

```bash
curl "http://<ip>/api/getData?path=settings:/deviceName&roles=value"
# -> [{"type":"string_","string_":"Ampli Medusa"}]
```

Log de depuración en Home Assistant:

```yaml
logger:
  logs:
    custom_components.vssl_mx: debug
```

## Cómo funciona (resumen técnico)

El equipo es un dispositivo StreamSDK de StreamUnlimited. Su web (`/index.fcgi`) carga
`/jsapi/nsdk-api.js`, que documenta la API:

```
GET  /api/getData?path=<modulo:/ruta>&roles=<rol[@all]>
GET  /api/getRows?path=<container>&roles=@all&from=0&to=N
POST /api/setData {"path":..,"role":..,"value":..}
POST /api/event/modifyQueue    GET /api/event/pollQueue
```

Las rutas de control (`player:player/control`, `powermanager:target`, `ui:/poweronline`…)
y el formato exacto de los comandos se obtuvieron analizando el APK oficial de la app
VSSL CNCT (`com.vssl.app.sx`). Detalle completo en `docs/PROTOCOL.md`.

## Licencia

MIT — ver [LICENSE](LICENSE).
