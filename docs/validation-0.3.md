# Validación del prototipo 0.3.0

29 de octubre de 2026. Este prototipo es experimental. Las cifras son de una
máquina y una situación concreta; no permiten afirmar que Babinium sea el
navegador de menor consumo. El bloqueo de anuncios de vídeo de YouTube todavía
requiere una prueba donde el control muestre un anuncio real.

Después de estas pruebas se detectó una interacción entre la inicialización de
la iluminación y un clic temprano en el menú de YouTube. La versión 0.3.1
incluye una corrección y tiene sus propias pruebas; este informe conserva la
procedencia de las mediciones de 0.3.0.

La compilación se realizó en Debian 13 amd64, con opciones x86-64 genéricas,
mediante [GitHub Actions, ejecución 40926556064](https://github.com/babinium/babinium-browser/actions/runs/40926556064),
para las fuentes `c392a74d23fa0e1bc3dc418f5c2b1c5c94703914`. El SHA-256 del
`.deb` es `e7feacbf19173ae9d81c3e6438763af3d39aab2e1798ab3ef5fa87b916015992`.
La descarga y sus hashes se verificaron; el paquete no se instaló automáticamente.
Actions aprobó seis pruebas Rust, seis Python y doce JavaScript. El ejecutable y
la biblioteca nativa eran idénticos a los de la compilación inmediatamente
anterior, utilizada también en pruebas gráficas; el índice de filtros y el nuevo
script de YouTube del paquete final se verificaron por separado.

## Cambio de CPU en YouTube

Se investigó en la misma reproducción real de YouTube el efecto del ajuste propio
[«Iluminación cinemática»](https://support.google.com/youtube/answer/12827017?co=GENIE.Platform%3DDesktop&hl=es-419).
Con el prototipo 0.2 se alternó activado → desactivado → activado en el menú del
sitio. El vídeo `dQw4w9WgXcQ` se mantuvo a 640 × 360, H.264 y Opus, sin sonido
para la medición. Se muestrearon una vez por segundo la sesión y todos sus
procesos descendientes, incluido el controlador de prueba. Cada fase duró 20 s;
se descartaron los segundos de los extremos. CPU al 100 % equivale a un núcleo
lógico; la PSS reparte memoria compartida y la RSS sumada la cuenta varias veces.

| Iluminación | CPU estable | PSS mediana | RSS sumada mediana |
|---|---:|---:|---:|
| Activada | 76,8 % | 1.116,5 MiB | 1.372,7 MiB |
| Desactivada | 39,6 % | 1.149,3 MiB | 1.405,1 MiB |
| Reactivada | 74,9 % | 1.118,8 MiB | 1.374,7 MiB |

Son tres intervalos de una sola reproducción, con escenas distintas, no una
comparación estadística entre equipos o navegadores. El resultado apoya reducir
el trabajo del compositor en este caso; **no demuestra una reducción de RAM**.
Los fotogramas perdidos permanecieron en cero en las muestras de la prueba.
La CPU excluye Xorg y los servicios compartidos; la memoria no incluye toda la
memoria de GPU ni del núcleo. WebKit puede adoptar otro códec o comportamiento.

En 0.3 el navegador intenta desactivar ese efecto una sola vez mediante el menú
de YouTube reconocido en inglés o español. Deja intactos idiomas o menús que no
reconozca, espera hasta 90 s cuando detecta un anuncio y permite volverlo a activar en el
menú; la elección manual se conserva. La integración depende de detalles
internos de la interfaz de YouTube que podrían cambiar.

## Filtrado cosmético

El matcher nativo mantiene hasta ocho contextos de excepciones por URL, en vez
de recalcular todos los recursos específicos al consultar clases nuevas. Cambiar
o liberar el motor invalida la caché; se probaron `generichide`, las excepciones
y el límite. Con el mismo índice de filtros y 1.000 consultas sintéticas, la
mediana de consulta para la URL de BBC fue de 0,333 ms en 0.2 y 0,048 ms en 0.3.
Esto mide un componente aislado, no el tiempo total de carga.

En una página real de BBC con instrumentación de desarrollo, el caso 0.2 hizo
seis consultas cosméticas en unos 4 ms acumulados; el 0.3 hizo siete en unos
10 ms. Las páginas cambiaron dinámicamente y el cronómetro mide bloques muy
breves, por lo que no hay evidencia de una mejora apreciable de CPU total en
esa navegación. En la muestra de YouTube el filtro `generichide` evitó las
consultas genéricas; no se atribuye el cambio de CPU del vídeo a esta caché.

## Pestaña vacía y funciones generales

En una ventana real de X11 se midió la pestaña vacía durante 25 s, con 10 s de
calentamiento: PSS mediana de **42,2 MiB**, RSS sumada de **69,5 MiB**, CPU
estable de **0,0 %** y un único proceso. En tres arranques el primer dibujado
GTK ocurrió a los 0,593, 1,228 y 0,700 s; la mediana fue de **0,700 s**. La
versión 0.2 había dado 41,0 MiB de PSS y 0,624 s de mediana: la variación entre
muestras no demuestra una mejora de arranque ni de memoria.

En pruebas gráficas se verificaron cookies, `localStorage` e IndexedDB entre
reinicios, modo oscuro y sus excepciones, pestaña vacía negra y rótulo, Google
como buscador, favoritos, descarga, navegación y comunicación con una ventana
abierta por el usuario. El ejecutable y biblioteca empleados en esas pruebas
son idénticos a los del paquete final. Con el paquete final se probaron además
las solicitudes bloqueadas, excepciones, CSS específico y genérico, filtros
procedurales y scriptlets, tanto con bloqueo activo como desactivado.
No se probó una cuenta de Google autenticada; conservar los datos del perfil no
garantiza que Google acepte todos los navegadores integrados.

## YouTube real y recursos del paquete final

Las pruebas siguientes se realizaron con perfiles nuevos y sin cuenta, en una
pantalla Xvfb aislada para no interferir con el escritorio. Se sumaron las RSS y
PSS de todos los procesos del navegador y sus descendientes; los valores no
incluyen el servidor Xvfb ni servicios externos. El caso con bloqueo duró 110 s
con 55 s de calentamiento; el control sin bloqueo duró 100 s con 50 s de
calentamiento. Se desactivaron solo las actualizaciones durante la medición.
No se deben comparar directamente con los valores tomados bajo Xorg: el servidor
gráfico y la aceleración pueden diferir.

| YouTube a 360p | PSS mediana | RSS sumada mediana | CPU estable | Máx. procesos |
|---|---:|---:|---:|---:|
| Bloqueo activado | 1.106,7 MiB | 1.363,9 MiB | 54,0 % | 14 |
| Control sin bloqueo | 1.042,6 MiB | 1.299,5 MiB | 48,8 % | 14 |

En ambos casos el vídeo avanzó más de 63 s a 640 × 360, H.264 y Opus, con más
de 1.580 fotogramas y ninguno perdido en la última muestra. El caso bloqueado
registró hasta 27 solicitudes bloqueadas en un proceso, incluyendo seguimiento;
no es un número de anuncios de vídeo. Los datos del reproductor contenían cero
`adPlacements` y cero `playerAds` con bloqueo, frente a dos y uno en el control.
**No se vio un anuncio de vídeo en ninguna de las dos reproducciones**, por lo
que no se demuestra la eliminación de prerolls, midrolls o anuncios insertados
en el propio flujo. Una sola ejecución por caso no cuantifica el costo general
del bloqueo ni el consumo en todos los vídeos.

Se probó por separado el ajuste inicial de iluminación cinemática con YouTube
real en inglés y español, y en ambos casos se pudo reactivar y conservar el
ajuste tras reiniciar. No se utilizaron credenciales del usuario.

Los registros detallados quedan en `runs/`, que no se publica en el repositorio.
Los análisis de desarrollo se reproducen con `tests/bench-blocker.py`,
`tests/youtube-ambient.py`, `tests/ambient-default-live.py`, las pruebas gráficas
en `tests/` y `scripts/measure.py`. El plan es revisar la instrumentación del
producto antes de una versión estable, sin eliminar los métodos externos de
validación.
