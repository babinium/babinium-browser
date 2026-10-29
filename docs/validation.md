# Validación del prototipo 0.1.0

29 de octubre de 2026. **La integración funciona; el bloqueo de anuncios de vídeo
de YouTube todavía no tiene una validación concluyente.** No se presenta este
prototipo como el navegador de menor consumo.

## Artefacto y pruebas

Compilación Debian 13 amd64 en [Actions, ejecución 40816193802](https://github.com/babinium/babinium-browser/actions/runs/40816193802),
fuentes `6d93a861f50ed73f579aa7870dd8d62aa14a1c15`. El paquete es
`babinium-browser_0.1.0_amd64.deb`, SHA-256:

```text
b2f806162cb421e01ba026429bfc8b00a81e0409048da27ce5bd10a47f1c25d4
```

C y Rust se compilaron remotamente. Las actualizaciones locales recompilan
índices de filtros, sin compilar código fuente. Pasaron 4 pruebas Rust y 6 Python
en Actions. La integración gráfica se comprobó como usuario normal en Debian,
con sandbox activado: Docker introduce restricciones distintas sobre los
namespaces de bubblewrap. Los cambios posteriores en documentación y controladores
de pruebas no alteran las fuentes de los binarios entregados.

Un servidor HTTP local confirmó que los scripts bloqueados no llegaron a red,
que las excepciones sí llegaron y que el sustituto `noop.js` cargó localmente.
Se verificaron scriptlets antes del JavaScript del sitio, CSS específico y
dinámico, excepciones genéricas y filtros procedurales. La excepción por sitio
restauró las solicitudes, los elementos y el comportamiento originales.

Las pruebas GTK ejercitan pestañas, cambio en ambos sentidos, cierre,
atrás/adelante, recarga, bloqueo por sitio y una descarga HTTP cuyos bytes se
comprobaron. Abrir una pestaña vacía no genera una carga web.

## Medición

Debian 13.7, kernel `6.12.113+deb13-amd64`, WebKitGTK 2.54.0 y GStreamer 1.26.2.
Equipo de prueba: Celeron B820 de dos núcleos; compilación x86-64 genérica, sin
ajuste al procesador ni a su RAM. Pantalla X11 real, ventana de 1366 × 721.
Perfiles nuevos, sin iniciar sesión en YouTube; cachés del sistema sin vaciar.

Cada segundo se muestreó toda la sesión y sus descendientes, incluidos los
procesos WebKit, bubblewrap y xdg-dbus-proxy. PSS estuvo disponible en todas las
muestras de estos casos; no se observó SwapPSS del navegador. RSS cuenta páginas
compartidas varias veces; PSS las reparte. **100 % de CPU equivale a un núcleo
lógico completo.** La CPU estable excluye el calentamiento.

| Carga | PSS mediana, MiB | RSS sumada mediana, MiB | CPU estable | Procesos máximos |
|---|---:|---:|---:|---:|
| Pestaña vacía, sin actualización | 43,3 | 68,1 | 0,0 % | 1 |
| YouTube: Rick Astley, bloqueo, 360p | 1015,6 | 1260,1 | 73,7 % | 8 |
| Mismo vídeo, sin bloqueo, 360p | 1022,3 | 1267,8 | 61,6 % | 14 |
| YouTube: Big Buck Bunny, bloqueo, 360p | 1021,9 | 1266,5 | 68,3 % | 8 |
| Repositorio de GitHub cargado | 458,5 | 688,2 | 0,8 % | 8 |
| Pestaña vacía con actualización automática | 43,3 | 68,1 | 1,3 % | 2 |

El pico muestreado de YouTube con bloqueo fue 1133,2 MiB PSS y 1375,2 MiB RSS.
El bloqueo añadió trabajo de CPU en esta carga; no se deduce una mejora de
rendimiento de la pequeña diferencia de memoria entre ambas sesiones. El control
no recibió anuncios de vídeo, por lo que tampoco permite estimar su ahorro.

La actualización automática completó las 16 listas a los 46,5 s del lanzamiento,
programada para empezar después de 30 s. Su pico muestreado con la interfaz fue
65,8 MiB PSS y 100,7 MiB RSS; después volvió al reposo. Una prueba separada del
actualizador tardó 13,4 s, con 1,07 s de CPU y 61,5 MiB RSS de pico, muestreada
cada 100 ms.

## Arranque

La primera representación de la ventana tardó **0,692 s de mediana** en tres
arranques con perfil nuevo; rango 0,450–0,821 s desde el lanzamiento. Esto mide
la interfaz vacía lista para recibir una dirección. WebKit se crea al navegar,
con su coste correspondiente: al lanzar directamente Rick Astley la ventana se
representó a los 0,997 s y la carga terminó a los 15,2 s. El controlador de prueba
espera 30 s antes de fijar calidad y reproducir.

La implementación inicial también iniciaba WebKit para una pestaña vacía:
245,4 MiB PSS y ocho procesos. La creación diferida redujo esa carga a 43,3 MiB y
un proceso. YouTube siguió alrededor de 1 GiB: el motor, el sitio y el vídeo
dominan esa carga. Un ejecutable pequeño no demuestra bajo consumo.

## YouTube real

Se usaron las páginas completas, sin reproductor externo ni descarga previa:

- `dQw4w9WgXcQ`: avanzó 70,86 s; 1772 fotogramas sin pérdidas, a 640 × 360.
- `aqz-KE-bpKQ`: avanzó 40,83 s en la repetición válida; 1225 fotogramas sin
  pérdidas, a 640 × 360.
- El control sin bloqueo avanzó 71,54 s; 1789 fotogramas sin pérdidas a la misma
  resolución.

Se registraron 22 solicitudes bloqueadas o sustituidas en el primer vídeo y 29
en el segundo. El contador incluye seguimiento, no sólo publicidad. Entre los
recursos publicitarios reales estuvieron `static.doubleclick.net/instream/ad_status.js`
y `googleads.g.doubleclick.net/pagead/id`.

El control conservaba **dos `adPlacements` y un `playerAds`** en la respuesta del
reproductor; con bloqueo quedaron vacíos. Esto valida el filtrado de datos reales
mediante scriptlets, además del bloqueo de solicitudes publicitarias.

**El control tampoco mostró un anuncio de vídeo durante la ventana observada.**
No se puede dar por demostrada la eliminación de preroll y midroll. Tampoco se
validaron anuncios insertados en el mismo flujo del contenido, sesiones
autenticadas, otras regiones, directos ni 1080p/4K. Esta versión sigue siendo
experimental para ese requisito central.

Un intento de Big Buck Bunny quedó pausado después del cambio de calidad. Se
conserva como `youtube-bunny-paused-attempt`, excluido de las cifras de reproducción.
Se repitió usando `playVideo()` del controlador del sitio además de
`HTMLMediaElement.play()`, sin cambiar el navegador ni saltar anuncios.

## Límites y alternativa

La API pública WebKitGTK no expone el tipo exacto ni todo el contexto iniciador
de cada solicitud; se usan metadatos y heurísticas. Tampoco permite reescribir
nativamente el cuerpo de respuestas. Véase [viabilidad](feasibility.md).

Para conservar la interfaz C/GTK, el siguiente experimento sería complementar
la red con reglas traducibles de `WebKitUserContentFilter`, verificando sus
excepciones y consumo. No resolvería por sí solo todos los anuncios de YouTube.
Si se necesitan más capacidades de modificación de respuestas, la alternativa
a evaluar es Firefox ESR del sistema con uBlock Origin completo: Firefox ofrece
[filtrado del flujo de respuestas](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webRequest/filterResponseData).
No se afirma que consuma menos; requiere una comparación con la misma carga.
Mantener un fork propio de WebKit elevaría el coste de mantenimiento y seguridad.

## Evidencia y reproducción

`tests/run-real.py` guarda perfiles aislados, muestras, eventos y capturas por
caso. `tests/integration.py` y `tests/ui-smoke.py` prueban WebKit/GTK bajo Xvfb
como usuario normal. `scripts/measure.py` conserva PIDs, RSS, PSS y CPU.
Los resultados sanitizados están en [validation-results.json](validation-results.json).

Los registros completos permanecen localmente en `runs/final-validation/`,
`runs/final-bunny-retry/`, `runs/final-integration/` y `runs/final-ui-navigation/`.
El artefacto contiene metadatos del commit, ejecución y compatibilidad.

El muestreo puede omitir procesos muy breves y no atribuye los servicios
compartidos Xorg/PipeWire ni toda la memoria del kernel/GPU. El resto del
escritorio no estuvo aislado. Sólo el arranque se repitió tres veces. Estos
números no forman un ranking frente a otros navegadores.
