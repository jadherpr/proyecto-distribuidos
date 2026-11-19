# Bitácora — Sesión de interoperabilidad

- **Fecha:** ____
- **Grupo:** g2
- **Integrantes presentes:** ____

## Antes de la sesión

- [ ] `.env` con `GROUP_NAME=g2` y la `PUBLIC_URL` visible en la red de la sala.
- [ ] `CENTRAL_URL` apuntando al servidor central del profesor.
- [ ] `docker compose up --build` funciona en un equipo limpio.
- [ ] Salida del script de conformidad guardada en el repositorio.

## Prueba 1: conversación global

| Qué verificamos | Resultado | Evidencia (log / captura) |
| --- | --- | --- |
| Un usuario de cada grupo escribió en #general | | |
| Todos los grupos vimos los mensajes de todos | | |
| El orden mostrado coincide entre servidores (lamport, origin) | | |

Observaciones:

## Prueba 2: caída y recuperación

| Qué verificamos | Resultado | Evidencia (log / captura) |
| --- | --- | --- |
| Apagamos nuestro servidor mientras otros escribían | | |
| Al volver, recuperamos lo perdido (`HISTORY` en el log) | | |
| No aparecieron mensajes duplicados (`DUP` en el log) | | |

Observaciones:

## Hallazgos

### Fallas propias encontradas y su causa

1.

### Fallas ajenas encontradas (otros grupos / central) y su explicación

1.

### Incompatibilidades de protocolo detectadas

1.

## Conclusiones para el póster
