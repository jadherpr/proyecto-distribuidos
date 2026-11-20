# Bitácora — Sesión de interoperabilidad

- **Grupo:** g2
- **Integrantes:** Jadher Prada · [Compañera 1] · [Compañera 2]
- **Repositorio:** github.com/jadherpr/proyecto-distribuidos

## Antes de la sesión

- [x] `.env` con `GROUP_NAME=g2` y `PUBLIC_URL`/`CENTRAL_URL` configurables por variable de entorno (nunca escritas en el código).
- [x] `docker compose --profile local up --build` probado en equipo limpio (Windows + Docker Desktop): levanta `g2-server` (:8000), `g2-server-b` (:8001) y `mock-central` (:9000).
- [ ] Salida del script de conformidad guardada en el repositorio *(pendiente: script publicado por el profesor)*.

## Pruebas previas en local (g2 vs g2b con central simulado — 2026-11-19/20)

| Qué verificamos | Resultado | Evidencia |
| --- | --- | --- |
| Conversación entre servidores (ana@g2 ↔ bob@g2b) | ✅ OK | Capturas; los mensajes cruzan por el central con marca de Lamport |
| Recepción sin necesidad de escribir (polling del cliente, 1,5 s) | ✅ OK | El cliente de ana recibe los mensajes de bob sin que ella escriba |
| Deduplicación por id | ✅ OK | Reenvío de un mensaje conocido responde `duplicate` y no se agrega (log `DUP`) |
| Recuperación de historial tras reinicio | ✅ OK | Logs: `CENTRAL_UP` → `HISTORY since=12 recovered=5`; después 20/20 en las 6 repeticiones del experimento |
| Detección de caída del central por heartbeat | ✅ OK | `docker compose stop central` → `CENTRAL_DOWN fails=3` (~15 s); `start central` → `CENTRAL_UP` + vaciado de la cola pendiente |
| Orden por Lamport | ✅ OK | Ambos servidores muestran el mismo orden por `(lamport, origin)` |
| Persistencia en volumen SQLite | ✅ por diseño | `users` e historial en volumen `server-data` |

## Experimento (datos reales, 6 mediciones)

| Serie | Rep. 1 | Rep. 2 | Rep. 3 | Media ± desv. |
| --- | --- | --- | --- | --- |
| Caída 10 s (20 msg @ 5 msg/s) | 0,887 s | 0,450 s | 0,450 s | **0,60 ± 0,25 s** |
| Caída 30 s (20 msg @ 5 msg/s) | 0,907 s | 0,433 s | 0,450 s | **0,60 ± 0,27 s** |

- En las **6 repeticiones** llegaron **20/20 mensajes**: sin pérdidas ni duplicados.
- El tiempo de recuperación **no depende** de la duración de la caída: al reiniciar, el primer heartbeat confirma el central y todo lo perdido llega en una sola petición `GET /history`.
- La 1ª repetición de cada serie tarda el doble (~0,9 s): **arranque en frío del contenedor**.

## Prueba 1: conversación global (sesión del curso)

| Qué verificamos | Resultado | Evidencia (log / captura) |
| --- | --- | --- |
| Un usuario de cada grupo escribió en #general | [PENDIENTE SESIÓN] | |
| Todos los grupos vimos los mensajes de todos | | |
| El orden mostrado coincide entre servidores (lamport, origin) | | |

Observaciones:

## Prueba 2: caída y recuperación (sesión del curso)

| Qué verificamos | Resultado | Evidencia (log / captura) |
| --- | --- | --- |
| Apagamos nuestro servidor mientras otros escribían | [PENDIENTE SESIÓN] | |
| Al volver, recuperamos lo perdido (`HISTORY` en el log) | | |
| No aparecieron mensajes duplicados (`DUP` en el log) | | |

Observaciones:

## Hallazgos

### Fallas propias encontradas y su causa

1. **`KeyError: 'from'` en el cliente** (commit `4937251`): el servidor devolvía el campo del remitente como `from_user` y el cliente esperaba `from` (formato del protocolo). Corregido en `db.py`: el historial ahora responde `from`.
2. **Mensajes que solo llegaban al escribir** (commit `06eb6f8`): el `input()` del cliente bloqueaba el bucle, así que ana solo veía mensajes de bob cuando ella enviaba algo. Corregido con un hilo de polling que consulta el servidor cada 1,5 s.
3. **Hipótesis inicial incorrecta** (corregida por el experimento): se esperaba una recuperación de ~15 s (3 fallos de heartbeat × 5 s), pero eso aplica solo cuando se cae el **central**. Si el que se reinicia es el propio servidor, su primer heartbeat ya entra y todo llega en un `GET /history` → 0,60 s medidos.

### Fallas ajenas encontradas (otros grupos / central) y su explicación

1. [COMPLETAR tras la sesión: qué falló en otros grupos y por qué — una incompatibilidad bien explicada vale como hallazgo para el póster]

### Incompatibilidades de protocolo detectadas

1. [COMPLETAR tras la sesión: diferencias de nombres de campos, códigos de respuesta o formato de tiempo entre grupos]

## Conclusiones para el póster

- La combinación de **reintentos con backoff exponencial + deduplicación por UUID + recuperación desde marca de Lamport** logra puesta al día en **< 1 s**, sin pérdidas ni duplicados, ante fallos reales.
- El tiempo de recuperación es **independiente de la duración de la caída** (confirmado con 2 series × 3 repeticiones).
- Los logs (`SENT/RECV/RETRY/DUP/DROP/CENTRAL_*`) demostraron ser la herramienta principal de depuración y la fuente de evidencia de la bitácora.
