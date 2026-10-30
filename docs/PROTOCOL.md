# Protocolo NSDK de VSSL (serie MX) — referencia

Todo lo aquí descrito se verificó contra un **VSSL MA.1** con firmware `rc20` /
`0.0.161.0xff2d7c5`. El equipo es un dispositivo **StreamSDK** de StreamUnlimited:
su web (`/index.fcgi`) se titula "StreamSDK Main Page" y carga `/jsapi/nsdk-api.js`,
que documenta la API que usa esta integración.

## Transporte

HTTP en claro, puerto **80**, sin autenticación.

```
GET  /api/getData?path=<modulo:/ruta>&roles=<rol[,rol]>|@all&_nocache=1
GET  /api/getRows?path=<container>&roles=@all&from=0&to=N
POST /api/setData    {"path": "...", "role": "...", "value": ...}
POST /api/event/modifyQueue {"queueId":"","subscribe":[{"path":..,"type":"itemWithValue"}],"unsubscribe":[]}
GET  /api/event/pollQueue?queueId=...
```

- Las rutas usan el formato `modulo:/ruta` (`settings:/deviceName`, `player:volume`).
- Los valores son objetos tipados: `{"type":"i32_","i32_":45}`, `bool_`, `string_`, `double_`.
- Ruta inexistente → HTTP 500 con `{"error":{"name":"CMAbstractWorker::invalidPath",...}}`.
- `getRows` sobre un **container** lista sus hijos: es la única forma de descubrir el árbol
  (no hay listado global de módulos).
- `pollQueue` es un long-poll real: bloquea hasta que hay evento; el parámetro `timeout`
  no corta la espera en esta build.

## Rutas relevantes

| Uso | Ruta | Tipo |
|---|---|---|
| Nombre | `settings:/deviceName` | value (string, escribible) |
| Versión | `settings:/version`, `settings:/versionSDK`, `settings:/releasetext` | value |
| Modelo | `settings:/system/boardName` (`VSSL MA1`), `productName` (`Mx series 2025`) | value |
| Volumen | `player:volume` | value (i32 0-100) |
| Mute | `settings:/mediaPlayer/mute` | value (bool) |
| Volumen máx. | `settings:/mediaPlayer/maxVolume`, `settings:/dsp/maxVolumeLimit` | value |
| EQ | `settings:/mediaPlayer/{bass,treble,balance,loudness,equalizerOnOff,subCrossoverFreq,subwooferLevel}` | value |
| LED BLAST | `settings:/leds/*` | value |
| **Control de reproducción** | **`player:player/control`** | action |
| Estado / pista | `player:player/data/value` | value (`playLogicData`) |
| Energía (objetivo) | `powermanager:target` (`online` / `networkStandby`) | value |
| Encender / standby | `ui:/poweronline`, `ui:/powernetworkstandby` | action |
| Find me | `vssl:/findMeEnabled` | value (bool) |
| Temporizador standby | `vssl:/standbyTimer/stop`, `vssl:/standbyTimer/remainingTime` | action/value |
| Aprender IR | `vssl:/learn/trigger`, `vssl:/learn/cancel` | action |

## Comandos de reproducción

Se envían al nodo de acción `player:player/control` con `role: "activate"`. La clase
`PlayerCommand` del APK oficial tiene un campo `control`:

```json
{"control": "pause"}          // play/pausa (el firmware lo trata como toggle)
{"control": "next"}
{"control": "previous"}
{"control": "stop"}
{"control": "seekTime", "time": 42000}
{"control": "changePlayMode", "playMode": {...}}
```

## Cambio de entrada

Mismo nodo, con payload `mediaRoles`. **El array `resources` es obligatorio**: sin él el
equipo responde `500 Failed to start playback, internal streamer error`.

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

| Entrada | `path` | `serviceID` | icono |
|---|---|---|---|
| Line in (AUX) | `ui:/auxaux_plug` | `AUX` | `skin:iconAUX` |
| SPDIF in | `ui:/spdifinaux_plug` | `SPDIFIN` | `skin:iconOptics` |
| COAX in | `ui:/coaxinaux_plug` | `COAXIN` | `skin:iconOptics` |
| HDMI in | `ui:/hdmiaux_plug` | `HDMI` | `skin:iconHdmi` |
| USB Memory | `ui:/usbMemaux_plug` | `Storage` | `skin:iconUsb` |

Respuesta correcta: HTTP 200 con un entero (id interno de la transición). El cambio se
confirma leyendo `player:player/data/value` → `playLogicData.trackRoles.mediaData.metaData.serviceID`.

## Estado de reproducción

`player:player/data/value` devuelve un objeto `playLogicData` con `state`
(`playing`/`paused`/`stopped`/`transitioning`) y `trackRoles` (título, artista, álbum,
`mediaData.metaData.serviceID`). El puerto TCP **4545** emite además el mismo JSON en
streaming continuo (útil para *now playing* sin sondeo).

## Puertos del MA.1

`80` API web + NSDK · `443` misma web por HTTPS · `4545` stream JSON de estado ·
`7000` AirPlay · `8008`/`8009` Google Cast · `1883`-no, `16300`/`16500` artefactos del
firmware `rc` de desarrollo (16500 = Syncthing) · `10001` TLS con certificado de cliente
(canal de la app CNCT, no usable sin ella).

**No existen** los puertos `50002` ni `7777` del protocolo legacy de la serie X: por eso la
integración `vsslctrl` de HACS falla con `Error fetching zone info, is the zone connected?`.

## Cómo se obtuvo

La API web no expone transporte ni selección de fuente: el árbol de navegación (`ui:`) se
puede listar pero sus filas no son direccionables. Las rutas y payloads de control salieron
de analizar el APK oficial **`com.vssl.app.sx` v2.1.5** (clases
`com.example.streamkit.data.network.ApiService` → `activateValue(path, role)` y el paquete
`model/valueactivator/PlayerCommand`), extrayendo las constantes de los DEX con `androguard`.
