# Guion de sustentación y demo — Grupo g2 (máx. 10 min)

## Parte 1 — Explicación del póster (≈3 min, palabra por palabra)

**Título/pregunta (0:00–0:45)**
> "Somos el grupo g2. Nuestro sistema conecta el servidor de nuestro grupo con el
> servidor central del curso, como pide el proyecto: una sala global #general donde
> todos los grupos conversan. Nuestra pregunta fue: ¿cuánto tarda el servidor de un
> grupo en ponerse al día después de reiniciarse en plena operación, sin perder ni
> duplicar mensajes?"

**Arquitectura (0:45–1:45)**
> "La arquitectura es una estrella: g2 y g2b nunca se hablan directamente; todo pasa
> por el central. Cada servidor mantiene un reloj de Lamport: antes de enviar suma 1,
> al recibir toma el máximo entre su reloj y el recibido, más 1. El historial se ordena
> por marca de Lamport, no por relojes físicos. Para la entrega usamos al menos una
> vez: cada mensaje queda en una cola persistente en SQLite y se reintenta con backoff
> exponencial. Y como reintentar no puede distinguir 'no llegó' de 'llegó y se perdió
> la respuesta', el receptor deduplica por el UUID del mensaje."

**Método (1:45–2:30)**
> "El experimento apaga el servidor de g2 con docker compose stop mientras g2b envía
> 20 mensajes a 5 por segundo. Al levantar de nuevo, medimos cuánto tarda el historial
> de g2 en contener los 20 ids. Tres repeticiones por serie, con caídas de 10 y de 30
> segundos."

**Resultados (2:30–3:30)**
> "Resultado: 0,60 segundos de media en ambas series, con desviación de 0,25 y 0,27.
> Es decir: la recuperación NO depende de cuánto estuvo caído el servidor, porque
> arranca, confirma el central en el primer heartbeat y trae lo perdido con UNA
> petición GET /history. En las 6 repeticiones llegó el 100 % de los mensajes, sin
> duplicados. Observamos además que la primera repetición de cada serie siempre tardó
> el doble, cerca de 0,9 segundos: es el arranque en frío del contenedor."

**Cierre (3:30–3:45)**
> "Conclusión: reintentos con backoff, deduplicación por id y recuperación desde la
> marca de Lamport hacen que una caída real sea prácticamente invisible para el
> usuario. Ahora la demo."

## Parte 2 — Demo A: caída del servidor del grupo (≈2,5 min)

Preparar: 3 ventanas visibles — (1) cliente ana `python client/chat_client.py --server http://localhost:8000 --user ana`, (2) cliente bob `python client/chat_client.py --server http://localhost:8001 --user bob`, (3) PowerShell con `docker compose logs -f server`.

1. Ana escribe "hola desde g2" → aparece en bob. Decir: "el mensaje va al central y el central lo reenvía".
2. Bob escribe "hola desde g2b" → aparece en ana con etiqueta [otro grupo].
3. `docker compose stop server` (el cursor de ana se queda sin respuesta).
4. En logs (ventana 3): señalar CENTRAL_DOWN. Decir: "el heartbeat detectó la caída".
5. Bob escribe "mensaje 1", "mensaje 2", "mensaje 3".
6. `docker compose start server`.
7. En logs: señalar CENTRAL_UP y luego HISTORY since=… recovered=N. Decir: "recuperó lo perdido con una petición".
8. Los 3 mensajes aparecen en ana UNA vez cada uno. Decir: "sin duplicados: el id es la clave de deduplicación".

## Parte 3 — Demo B: caída del central (≈2 min)

1. Ana escribe dos mensajes. Nada especial.
2. `docker compose stop central` → en logs aparece CENTRAL_DOWN tras 3 heartbeats (~15 s; mencionar que es configurable).
3. Ana escribe "esto quedó en cola" → no sale en bob.
4. `docker compose start central` → CENTRAL_UP, la cola se vacía y bob recibe todo. Decir: "la cola de salida es persistente y el flujo se restablece solo".

## Parte 4 — Cierre (≈1 min)

> "En resumen: el sistema entrega al menos una vez sin duplicar, detecta fallos por
> heartbeat, y ambos casos — caída del servidor de grupo y caída del central — se
> recuperan automáticamente."

## Preguntas probables del profesor (respuestas cortas)

- **¿Por qué 0,6 s y no ~15 s como una hipótesis ingenua?** Los 3 fallos de heartbeat aplican a un central caído; si el que se reinicia es el propio servidor, su primer heartbeat ya entra y todo llega en un GET /history.
- **¿Por qué no usan sent_at para ordenar?** El reloj físico de cada máquina no está sincronizado; Lamport da un orden lógico consistente.
- **¿Qué pasa si un 4xx rechaza el mensaje?** No se reintenta: se descarta y se registra en el log (DROP), porque un 5xx puede ser transitorio pero un 4xx es un problema del mensaje.
- **¿Dónde queda la cola pendiente?** En SQLite (tabla pending), sobrevive a restarts.
- **¿Y si la red de la sala no deja que el central conecte a nuestro servidor?** La especificación define un modo alternativo; pendiente del aviso del profesor.

## Para el video (si es grabado)

1. Grabar primero las demos A y B (Windows: Win+G u OBS), con las 3 ventanas abiertas.
2. Grabar la explicación del póster a pantalla completa siguiendo la Parte 1.
3. Unir en Clipchamp en ese orden: póster → demo A → demo B → cierre. Exportar MP4 1080p, revisar que dure < 10 min.
