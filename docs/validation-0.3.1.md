# Validación de Babinium Browser 0.3.1

29 de octubre de 2026. Este navegador sigue siendo experimental. Las medidas
son de una máquina y circunstancias concretas y no son una comparación entre
navegadores. El bloqueo de anuncios de vídeo de YouTube todavía necesita un
control en el que se muestre un anuncio real.

La compilación se realizó en Debian 13 amd64 con opciones x86-64 genéricas en
[GitHub Actions, ejecución 40930228881](https://github.com/babinium/babinium-browser/actions/runs/40930228881),
a partir de las fuentes `46239ef2325e9b3597c4b073058b7ac23bd82e5e`.
El SHA-256 del `.deb` es
`7dc3a6ed7fe478479c05bbcba290c0ce37fb34b177d4f36c3c795a96565a5a3c`.
La descarga se verificó y el paquete no se instaló automáticamente. Actions
aprobó seis pruebas Rust, seis Python y quince JavaScript.

## Cambios y prueba controlada

El ajuste inicial de YouTube intenta desactivar una vez la iluminación
cinemática mediante el propio menú del reproductor. Se respetan los clics del
usuario aun si llegan mientras el menú se está abriendo; un ajuste manual
posterior se conserva tras reiniciar. También se intenta una vez en perfiles
preexistentes que todavía no tengan la marca de inicialización. El reconocimiento se probó en inglés y
español y depende de una interfaz interna de YouTube. En otros idiomas o ante
cambios del sitio el ajuste puede no aplicarse. La selección de calidad se
puede modificar desde el reproductor.

Antes de integrar el cambio se alternó la iluminación activada, desactivada y
reactivada en una sola reproducción real de YouTube, usando la versión 0.2 a
360p con H.264 y Opus. La CPU de la sesión fue respectivamente **76,8 %**,
**39,6 %** y **74,9 % de un núcleo**; la PSS fue 1.116,5, 1.149,3 y 1.118,8
MiB. Las escenas eran distintas y son tres intervalos de un único vídeo en una
sola máquina. Esta observación no demuestra una reducción de RAM ni garantiza
la misma mejora en otros equipos. El método y la comparación de la caché
cosmética están en [validación 0.3.0](validation-0.3.md).

El matcher conserva hasta ocho contextos pequeños de excepciones por URL, y los
invalida al cambiar el motor. El beneficio aislado sobre consultas sintéticas no
se tradujo en una mejora significativa demostrada en la página real probada.

## Funciones probadas

En el paquete 0.3.1 se comprobaron las solicitudes bloqueadas, excepciones,
filtros cosméticos específicos y genéricos, reglas procedurales y scriptlets,
con y sin bloqueo. También pasaron cookies, `localStorage` e IndexedDB entre
reinicios, favoritos, modo oscuro, búsqueda con Google y pestaña vacía negra
con la marca en el extremo derecho. Las pruebas anteriores de navegación,
descargas y comunicación con ventanas abiertas por el usuario usaron el mismo
código de interfaz salvo el número de versión.

El script definitivo de iluminación, idéntico al del paquete 0.3.1, se probó
con YouTube real en inglés y español usando el ejecutable 0.3.0 y una copia
independiente de datos: el efecto se desactivó inicialmente y, tras reactivarlo
manualmente, permaneció activado al reiniciar. Con el paquete 0.3.1 completo se
cambió un vídeo real de 360p a 720p mediante clics, y el vídeo continuó a 720p.
También se comprobó audio capturando únicamente 2,8 s del flujo nuevo de WebKit:
estéreo a 48 kHz, RMS 111,7 y pico 748 en muestras de 16 bits. No se grabaron
micrófono ni mezcla del escritorio.

No se usó una cuenta real de Google. Aunque se verificó la persistencia local,
Google puede rechazar el inicio de sesión en navegadores integrados; todavía no
se confirmó una sesión autenticada tras reiniciar.

## Medición del paquete 0.3.1

Debian 13, WebKitGTK 2.54.0, GStreamer 1.26.2, pantalla Xvfb de 1360 × 768,
perfiles aislados y actualizaciones de listas desactivadas durante la medición.
El muestreo se hizo cada segundo e incluyó todos los procesos del navegador y
sus descendientes. La RSS sumada cuenta memoria compartida más de una vez; la
PSS la reparte. La CPU al 100 % equivale a un núcleo lógico. No se incluyeron el
servidor Xvfb, servicios externos ni toda la memoria de GPU o del núcleo.

| Carga | PSS mediana | RSS sumada mediana | CPU estable | Máx. procesos |
|---|---:|---:|---:|---:|
| Pestaña vacía | 61,0 MiB | 118,4 MiB | 0,0 % | 1 |
| YouTube con bloqueo, 360p | 1.046,3 MiB | 1.303,7 MiB | 62,2 % | 14 |
| YouTube sin bloqueo, 360p | 1.022,2 MiB | 1.278,8 MiB | 47,7 % | 14 |

La pestaña vacía se midió durante 25 s con 10 s de calentamiento. El primer
dibujado GTK ocurrió a los 0,665, 0,616 y 0,603 s en tres arranques, con mediana
de **0,616 s**. YouTube con bloqueo se midió durante 110 s con 55 s de
calentamiento; el control, 100 s con 50 s de calentamiento. Son ejecuciones
individuales, no una estimación estadística del efecto del bloqueo. Xvfb puede
usar una vía gráfica distinta de Xorg: no se comparan directamente estas cifras
con las obtenidas en el escritorio real para la versión anterior.

En ambos casos se reprodujo `dQw4w9WgXcQ` a 640 × 360 con H.264 y Opus. La
última muestra del caso bloqueado mostró 56,7 s de vídeo, 1.412 fotogramas y
cero perdidos; el control mostró 63,4 s, 1.585 y cero perdidos. El caso
bloqueado registró hasta 29 solicitudes bloqueadas en un proceso, incluyendo
seguimiento; no es un número de anuncios de vídeo. Los datos del reproductor
tenían cero `adPlacements` y cero `playerAds` con bloqueo, frente a dos y uno en
el control. **Ninguno mostró un anuncio de vídeo**, por lo que esta prueba no
confirma la eliminación de prerolls, midrolls o anuncios insertados en el flujo.

Los registros quedan en `runs/`, fuera del repositorio. Las pruebas externas se
pueden reproducir con los programas de `tests/` y `scripts/measure.py`. Antes de
una versión estable se revisarán las opciones de diagnóstico incorporadas para
retirar las que no sean fundamentales, como pidió Miguel.
