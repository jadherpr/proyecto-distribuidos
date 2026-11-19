# Arquitectura — Grupo g2

## Diagrama de contenedores, redes y volúmenes

```mermaid
flowchart TB
    subfilter=false
    subcurso["Sistema del curso (estrella)"]
    central["Servidor central del profesor\n(POST /register · POST /messages ·\nGET /history · GET /health)"]

    subgraph g2 ["docker compose del grupo g2"]
        server["server\nuvicorn · FastAPI\n:8000"]
        vol[("server-data\nSQLite: users, messages,\npending")]
        client["cliente CLI\n(puede correr en el host)"]
    end

    subgraph local ["perfil local (solo pruebas)"]
        mockcentral["central (simulado)\n:9000"]
        serverb["server-b (g2b)\n:8001"]
        volb[("server-b-data")]
    end

    client -->|HTTP API libre| server
    server --- vol
    serverb --- volb
    server -->|POST /register\nPOST /messages\nGET /history\nGET /health| central
    server -->|perfil local| mockcentral
    serverb --> mockcentral
    central -.->|POST /fed/messages\nGET /fed/health| server
    mockcentral -.-> server
    mockcentral -.-> serverb
```

- **Red:** cada `docker compose up` crea su red propia; en la sesión de
  interoperabilidad los servidores se alcanzan por la red de la sala usando la
  `PUBLIC_URL` declarada en `.env`.
- **Volúmenes:** `server-data` (y `server-b-data` en pruebas) guarda la base SQLite,
  de modo que `docker compose restart` no pierde usuarios, historial ni la cola de
  mensajes pendientes.

## Componentes del servidor

| Módulo | Responsabilidad |
| --- | --- |
| `app/config.py` | Toda la configuración por variables de entorno; ninguna URL escrita en el código. |
| `app/clock.py` | Reloj de Lamport con exclusión mutua: `tick()` antes de enviar, `observe(r)` al recibir. |
| `app/db.py` | SQLite: usuarios, mensajes (clave primaria `id` = deduplicación), cola `pending`, `meta`. |
| `app/federation.py` | Bucles de registro, heartbeat, envío con reintentos y recuperación de historial. |
| `app/main.py` | API local (libre) + API de federación (`/fed/*`), arranque de tareas en segundo plano. |

## Flujo de un mensaje local (ana@g2 escribe en #general)

1. El cliente hace `POST /messages` a su servidor.
2. El servidor incrementa el reloj (`lamport = tick()`), genera el UUID `id`, guarda el
   mensaje en `messages` y lo encola en `pending` (log `LOCAL`).
3. El bucle de envío hace `POST /messages` al central (log `SENT`); si falla con 5xx o
   timeout, reintenta con backoff exponencial (log `RETRY`); si responde 4xx, lo
   descarta con log `DROP`.
4. El central guarda el mensaje y lo reenvía a los demás servidores con
   `POST /fed/messages`; cada receptor aplica `max(local, recibido) + 1` y descarta
   `id` repetidos (log `DUP`).

## Flujo de caída y recuperación

1. El bucle de heartbeat acumula fallos de `GET /health`; al llegar a
   `HEARTBEAT_MAX_FAILS` marca el central caído (log `CENTRAL_DOWN`). Los mensajes
   locales siguen guardándose en la cola `pending`.
2. Cuando el central vuelve a responder, se marca arriba (log `CENTRAL_UP`).
3. Se pide `GET /history?since={max_lamport}` y se ingiere lo faltante
   (log `HISTORY`); luego se vacía la cola pendiente.

## Experimento: tiempo de recuperación

- **Pregunta:** ¿cuánto tarda el servidor en ponerse al día después de reiniciarse?
- **Hipótesis:** el tiempo de recuperación es del orden de los reintentos y el
  heartbeat (segundos), y crece poco con la cantidad de mensajes perdidos porque la
  recuperación es un solo `GET /history`.
- **Método:** `experiment/medir_recuperacion.py` apaga el servidor principal con
  `docker compose stop`, envía N mensajes a tasa fija desde el segundo servidor
  durante la caída, lo levanta con `docker compose up -d` y mide el tiempo hasta que
  `GET /messages` del servidor contiene todos los `id` enviados.
- **Parámetros:** `--repeats` (≥ 3), `--count`, `--rate`, `--outage`.
- **Salida:** `experiment/datos/resultados.csv` con una fila por repetición
  (`recuperacion_s`, en segundos) y resumen con media, mínimo, máximo y desviación.
