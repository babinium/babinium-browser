# Validación del prototipo 0.2.0

29 de octubre de 2026. Esta versión es experimental. **El bloqueo de anuncios
de vídeo de YouTube no quedó demostrado de forma concluyente**, y estas medidas
no constituyen una comparación entre navegadores.

El paquete se compiló en Debian 13 amd64 mediante [GitHub Actions, ejecución
40879039442](https://github.com/babinium/babinium-browser/actions/runs/40879039442),
con fuentes `9f642757ed8f2fc877736a73cae3f2340d8c44d3`. El SHA-256 del `.deb`
es `ee7098e10c028a5459882b59688ed2dfb6e01c0ad76ca8b34ab6801ab7dfd01f`.
La descarga y los hashes del artefacto se verificaron; el paquete no se instaló
automáticamente. Los cambios posteriores a ese commit son de pruebas o
documentación y no alteran el código del binario.
Actions aprobó cuatro pruebas Rust, seis Python y seis del selector de códec.

## Funciones y persistencia

En un perfil de prueba, cookies persistentes, `localStorage` e IndexedDB se
mantuvieron tras cierres completos y reinicios. Se guardó un favorito, se abrió
desde su panel y se quitó tras reiniciar. También pasaron las pruebas GTK de
pestañas diferidas, navegación, descarga y excepción de bloqueo. Una ventana
abierta con un gesto del usuario pudo comunicarse con su ventana de origen.

La captura de una pestaña vacía, al primer segundo, mostró el centro negro
`RGB(0,0,0)` y el rótulo «Babinium» a la derecha. No hubo navegación ni proceso
web para esa pestaña. Una búsqueda escrita en la barra inició una petición a
Google. En una página clara, Dark Reader transformó el fondo; al excluir el
sitio se recuperó el fondo original. Una página nativamente oscura quedó sin
transformar, mientras que otra con una zona central clara sí se transformó.

La pantalla inicial real de acceso de Google para YouTube se abrió sin ingresar
credenciales. **No se probó una cuenta real ni se confirmó una sesión de
Google/YouTube después de reiniciar.** [Google advierte](https://support.google.com/accounts/answer/7675428?hl=es)
que puede rechazar algunos navegadores integrados; la persistencia local no
garantiza su aceptación.

## Memoria y CPU

Misma máquina Debian 13.7, WebKitGTK 2.54.0 y GStreamer 1.26.2, pantalla X11;
Celeron B820 de dos núcleos usado exclusivamente para medir, con compilación
x86-64 genérica. Perfiles aislados, sin sesión de YouTube y sin actualización
de listas durante las mediciones estables. En YouTube el vídeo se silenció para
la medición; el audio se comprueba aparte. Se muestreó cada segundo la sesión
completa y sus descendientes. La RSS sumada cuenta páginas compartidas más de
una vez; la PSS las reparte. **100 % de CPU equivale a un núcleo lógico.**

| Carga | PSS mediana | RSS sumada mediana | CPU estable | Procesos máx. |
|---|---:|---:|---:|---:|
| Pestaña vacía, versión 0.2 | 41,0 MiB | 69,5 MiB | 0,0 % | 1 |
| GitHub con Dark Reader siempre aplicado, versión intermedia | 591,8 MiB | 822,7 MiB | 9,9 % | 8 |
| GitHub con detección del tema nativo, versión 0.2 | 444,8 MiB | 683,4 MiB | 0,7 % | 8 |
| YouTube real, bloqueo activado, 360p, versión 0.2 | 1.023,0 MiB | 1.270,2 MiB | 75,5 % | 14 |
| YouTube real, bloqueo desactivado, 360p, versión intermedia | 936,1 MiB | 1.186,2 MiB | 72,4 % | 13 |

Los casos de GitHub duraron 40 s, con 20 s de calentamiento. En el segundo se
observó fondo oscuro nativo y ninguna hoja de Dark Reader. El caso de YouTube
con bloqueo duró 110 s, con 55 s de calentamiento; el control duró 100 s, con
50 s de calentamiento. Son ejecuciones individuales y el contenido, red y
cachés pueden variar: muestran órdenes de magnitud, no una mejora garantizada
ni una comparación estadística. Los valores de CPU no incluyen Xorg ni otros
servicios compartidos, y la memoria no incluye toda la memoria de GPU o kernel.

La pestaña vacía se midió durante 25 s con 10 s de calentamiento. El primer
dibujado GTK tuvo una mediana de **0,624 s** en tres arranques, con rango de
0,530 a 1,167 s desde el lanzamiento; mide la ventana vacía, no la carga web.

## YouTube y anuncios

Con la versión 0.2, el vídeo `dQw4w9WgXcQ` avanzó 73,1 s a 640 × 360; se
observaron 1.829 fotogramas y cero perdidos en la última muestra. En esa
ejecución YouTube usó VP9 y Opus. En otra se observó H.264 y Opus a 360p. La
preferencia de calidad usa una función interna del reproductor; la [API pública
de YouTube ya no admite fijar la calidad](https://developers.google.com/youtube/iframe_api_revision_history).
El sitio puede cambiar o ignorar ese método interno. En una prueba con clics
reales se cambió de 360p a 720p y el vídeo continuó a 720p. La decisión de
códec depende de lo que informa el motor y de si se llega a tiempo; no se puede
afirmar una mejora general de CPU a partir de una sola ejecución por caso.

El audio se comprobó por separado con un clic real y volumen bajo: se capturaron
2,8 s de PCM estéreo a 48 kHz, con RMS 98,1 y pico 668 sobre muestras de 16
bits. La captura se limitó al flujo de WebKit de Babinium; no se grabaron el
micrófono ni la mezcla del escritorio. Las muestras se descartaron después del
cálculo.

El caso bloqueado registró hasta 34 solicitudes bloqueadas o sustituidas,
incluyendo seguimiento. Los datos del reproductor quedaron con cero
`adPlacements` y cero `playerAds`; el control sin bloqueo conservó dos y uno,
respectivamente. **Ninguna de las dos reproducciones mostró un anuncio de vídeo
en los intervalos observados.** No se puede concluir que se eliminaron prerolls,
midrolls ni anuncios insertados en el mismo flujo. La validación anterior y las
limitaciones de WebKitGTK están en [validation.md](validation.md) y
[feasibility.md](feasibility.md).

Las pruebas locales y los registros completos se conservan en `runs/`, que no se
publica en el repositorio; contienen URLs y datos de diagnóstico. Los resultados
pueden reproducirse con `tests/features.py`, `tests/integration.py`,
`tests/ui-smoke.py`, `tests/favorites-open.py`, `tests/popup-smoke.py`,
`tests/youtube-manual.py`, `tests/audio-smoke.py` y `scripts/measure.py`. Los
perfiles de prueba no usaron datos reales del usuario.
