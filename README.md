# Chat distribuido — Grupo g2

Proyecto final de Sistemas Distribuidos (UIS · EISI). Servidor de chat en contenedores
que se registra en el servidor central del curso y participa en la sala global `#general`.

## Levantar el sistema en un equipo limpio

Requisitos: Docker y Docker Compose.

```bash
cp .env.example .env
# editar .env con los valores de la sesion (GROUP_NAME, PUBLIC_URL, CENTRAL_URL)
docker compose up --build
```

El servidor del grupo queda en `http://localhost:${PORT}` (por defecto 8000).

### Pruebas locales sin el servidor central del profesor

El perfil `local` levanta un servidor central simulado y un segundo servidor (`g2b`)
para probar federación, caídas y recuperación en una sola máquina:

```bash
docker compose --profile local up --build
# servidor del grupo:  http://localhost:8000
# segundo servidor:    http://localhost:8001
# central simulado:    http://localhost:9000
```

## Cliente

```bash
python3 client/chat_client.py --server http://localhost:8000 --user ana
```

Crea el usuario si no existe, muestra el historial y envía mensajes. Los usuarios de
otros grupos aparecen con otro color y con la etiqueta `[otro grupo]`.

## Variables de entorno

| Variable | Por defecto | Significado |
| --- | --- | --- |
| `GROUP_NAME` | `g2` | Nombre corto del servidor (gN). |
| `PUBLIC_URL` | `http://localhost:8000` | URL con la que el servidor central debe alcanzar este servidor. |
| `CENTRAL_URL` | `http://localhost:9000` | URL del servidor central. Nunca está escrita en el código. |
| `PORT` | `8000` | Puerto del servidor del grupo. |
| `DB_PATH` | `/data/chat.db` | Ruta de la base SQLite (volumen). |
| `REGISTER_INTERVAL` | `30` | Segundos entre renovaciones de registro. |
| `HEARTBEAT_INTERVAL` | `5` | Segundos entre heartbeats a `GET /health` del central. |
| `HEARTBEAT_MAX_FAILS` | `3` | Fallos consecutivos antes de marcar el central como caído. |
| `RETRY_BASE_SECONDS` | `0.5` | Base de la espera exponencial de reintentos. |
| `RETRY_MAX_SECONDS` | `30` | Tope de la espera exponencial. |

## Decisiones de diseño

- **FastAPI + SQLite.** Un solo contenedor con el servidor; la base vive en el volumen
  `server-data`, por lo que usuarios e historial sobreviven a `docker compose restart`.
- **Reloj de Lamport en memoria, respaldado por la base.** Al arrancar se restaura con
  el máximo `lamport` conocido. Antes de enviar: `local + 1`. Al recibir:
  `max(local, recibido) + 1`.
- **Deduplicación por `id` (UUID v4).** La tabla `messages` usa `id` como clave primaria;
  un `id` repetido se descarta y responde `200` igualmente (idempotencia).
- **Cola de salida persistente (`pending`).** Todo mensaje local se guarda en la cola
  antes de enviarlo. El bucle de envío reintenta con backoff exponencial
  (`0.5s * 2^intentos`, tope 30s) ante 5xx o falta de respuesta; los 4xx no se
  reintentan y se registran como `DROP`.
- **Heartbeat.** Un bucle consulta `GET /health` del central. Tras
  `HEARTBEAT_MAX_FAILS` fallos lo marca caído (`CENTRAL_DOWN` en el log) y deja los
  mensajes pendientes en la cola. Al volver (`CENTRAL_UP`) recupera el historial con
  `GET /history?since={max_lamport}` y vacía la cola.
- **Orden.** El historial se sirve ordenado por `(lamport, origin)`.
- **Logs como fuente de datos.** Cada evento relevante deja rastro con `id`, `lamport`
  y origen: `LOCAL`, `SENT`, `RECV`, `RETRY`, `DROP`, `DUP`, `REGISTER`, `CENTRAL_UP`,
  `CENTRAL_DOWN`, `HISTORY`.

## Endpoints locales (API libre, para el cliente)

| Método y ruta | Propósito |
| --- | --- |
| `POST /users` | Crear usuario local `{"name": "ana"}` → `ana@g2`. |
| `GET /users` | Listar usuarios locales. |
| `POST /messages` | Enviar a `#general`: `{"from": "ana@g2", "body": "..."}`. |
| `GET /messages` | Historial ordenado por `(lamport, origin)`. |
| `GET /status` | Estado: reloj, central arriba/abajo, pendientes. |

## Endpoints de federación (los fija la especificación)

| Método y ruta | Propósito |
| --- | --- |
| `GET /fed/health` | `{"server": "g2", "lamport": N}`. |
| `POST /fed/messages` | Recibir reenvío del central; idempotente por `id`. |
| `POST /register`, `POST /messages`, `GET /history`, `GET /health` | Llamadas salientes al central. |

> **Importante:** la especificación OpenAPI oficial del curso manda sobre este README.
> Antes de la sesión de interoperabilidad, correr el script de conformidad y ajustar
> cualquier diferencia de campos o códigos de respuesta.

## Experimento: tiempo de recuperación

Pregunta: ¿cuánto tarda el servidor en ponerse al día después de reiniciarse?

```bash
docker compose --profile local up --build -d
python3 experiment/medir_recuperacion.py --repeats 3 --count 20 --rate 5 --outage 10
```

El script apaga el servidor principal, envía mensajes desde el segundo servidor a tasa
fija durante la caída, lo levanta y mide el tiempo hasta que su historial contiene todos
los mensajes. Escribe `experiment/datos/resultados.csv` e imprime un resumen estadístico.

## Documentación

- `docs/arquitectura.md` — diagrama de contenedores, redes y volúmenes.
- `docs/plan_trabajo.md` — reparto de roles y puntos de control.
- `docs/bitacora_interoperabilidad.md` — plantilla de la bitácora de la sesión.
