# Plan de trabajo — 3 integrantes

Una semana de trabajo. Cada etapa termina en un punto de control verificable; no
avanzar a la siguiente sin haberlo alcanzado. Todos pasan por el código: el enunciado
exige que cualquier integrante pueda explicar cualquier línea en la sustentación.

## Roles

| Rol | Responsabilidad principal | También participa en |
| --- | --- | --- |
| **Servidor** | Servidor local: usuarios, mensajes, persistencia, cliente CLI. | Revisión del código de federación. |
| **Federación** | Registro, envío/recepción, Lamport, deduplicación, reintentos, heartbeat, historial. | Script de conformidad y sesión de interoperabilidad. |
| **Experimento y póster** | Script de medición, repeticiones, gráfica, diseño del póster. | Demo en vivo y bitácora. |

## Etapas y puntos de control

### 1. Arranque (día 1)
- Leer la especificación OpenAPI oficial completa y las dudas al foro del curso.
- Crear el repositorio, subir este código y correr
  `docker compose --profile local up --build`.
- **Control:** los tres tienen el sistema corriendo en su máquina.

### 2. Servidor local (días 1–2)
- Verificar `POST /users`, `POST /messages`, `GET /messages` y el cliente CLI.
- Verificar persistencia: `docker compose restart` y comprobar que usuarios y
  historial siguen ahí.
- **Control:** dos clientes conversan entre sí y el historial sobrevive al reinicio.

### 3. Conexión con el servidor central (días 2–4)
- Probar contra el central simulado: registro, envío, recepción en `g2b`, orden por
  `(lamport, origin)`, deduplicación (`DUP` en el log) y reintentos (apagar el central
  y ver `RETRY` / `CENTRAL_DOWN` / `CENTRAL_UP`).
- Correr el script de conformidad oficial contra el servidor.
- **Control:** script de conformidad pasa completo; guardar su salida en el repo.

### 4. Experimento (días 4–5)
- Correr `experiment/medir_recuperacion.py` con al menos 3 repeticiones.
- Variar un parámetro (duración de la caída o tasa de envío) para la nota extra.
- Generar la gráfica o tabla con unidades para el póster.
- **Control:** CSV de resultados + gráfica en el repositorio.

### 5. Interoperabilidad, póster y sustentación (días 5–7)
- Ensayar la sesión: apagar el servidor mientras el otro escribe y verificar
  recuperación sin duplicados.
- Llenar `docs/bitacora_interoperabilidad.md` durante la sesión.
- Armar el póster con las secciones del enunciado (figuras > texto) y ensayar la
  demo de fallo + recuperación de 10 minutos.
- **Control:** póster en PDF, demo ensayada y bitácora completa.

## Reglas del grupo

- Commits pequeños y frecuentes con nombre de quien los hace (el historial de commits
  es parte de la evaluación).
- Antes de cada clase: `git pull` y correr la prueba de humo del README.
- Las dudas de protocolo se resuelven solo en el foro del curso, nunca negociando con
  otros grupos.
