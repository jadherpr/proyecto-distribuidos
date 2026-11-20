# Bitácora — Sesión de interoperabilidad

- **Fecha:** ____
- **Grupo:** g2
- **Integrantes presentes:** Jadher Prada, ____, ____

## Antes de la sesión

- [x] `.env` con `GROUP_NAME=g2` y `PUBLIC_URL` configurables (probado en local).
- [x] `CENTRAL_URL` por variable de entorno, nunca escrita en el código.
- [x] `docker compose up --build` funciona en equipo limpio (perfil local: central simulado + g2b).
- [ ] Salida del script de conformidad guardada en el repositorio.

## Pruebas previas en local (g2 vs g2b con central simulado)

| Qué verificamos | Resultado | Evidencia |
| --- | --- | --- |
| Conversación entre servidores (ana@g2 ↔ bob@g2b) | OK | Capturas; los mensajes cruzan por el central con marca Lamport |
| Recepción sin necesidad de escribir (polling del cliente) | OK | El cliente consulta cada 1,5 s (fix: antes solo consultaba al enviar) |
| Deduplicación por id | OK | Reenvío de mensaje repetido responde `duplicate` y no se agrega (log DUP) |
| Recuperación de historial tras reinicio | OK | Log `HISTORY since=12 recovered=5`; 6 repeticiones con 20/20 mensajes entregados |
| Persistencia (volumen SQLite) | OK por diseño | Usuarios e historial en volumen `server-data` |
| Orden por Lamport | OK | Historial ordenado por (lamport, origin); ambos servidores muestran el mismo orden |

**Mediciones del experimento:** caída 10 s → 0,89 / 0,45 / 0,45 s; caída 30 s → 0,91 / 0,43 / 0,45 s.
Media 0,60 ± 0,25 s y 0,60 ± 0,27 s. El tiempo de recuperación no depende de la duración
de la caída. La primera repetición de cada serie tarda el doble (~0,9 s): arranque en frío
del contenedor.

## Prueba 1: conversación global (sesión del curso)

| Qué verificamos | Resultado | Evidencia (log / captura) |
| --- | --- | --- |
| Un usuario de cada grupo escribió en #general | | |
| Todos los grupos vimos los mensajes de todos | | |
| El orden mostrado coincide entre servidores (lamport, origin) | | |

Observaciones:

## Prueba 2: caída y recuperación (sesión del curso)

| Qué verificamos | Resultado | Evidencia (log / captura) |
| --- | --- | --- |
| Apagamos nuestro servidor mientras otros escribían | | |
| Al volver, recuperamos lo perdido (`HISTORY` en el log) | | |
| No aparecieron mensajes duplicados (`DUP` en el log) | | |

Observaciones:

## Hallazgos

### Fallas propias encontradas y su causa

1. `KeyError: 'from'` en el cliente: el servidor devolvía el campo como `from_user` y el cliente esperaba `from`. Corregido (commit 4937251): el servidor ahora responde `from`, formato del protocolo.
2. Los mensajes de bob solo llegaban a ana cuando ana escribía: el `input()` del cliente bloqueaba el bucle y no había polling. Corregido (commit 06eb6f8) con un hilo que consulta cada 1,5 s.
3. Hipótesis inicial (~15 s por heartbeat) incorrecta: aplicaba a la caída del central, no del servidor propio. El experimento la corrigió.

### Fallas ajenas encontradas (otros grupos / central) y su explicación

1. [COMPLETAR tras la sesión]

### Incompatibilidades de protocolo detectadas

1. [COMPLETAR tras la sesión]

## Conclusiones para el póster
