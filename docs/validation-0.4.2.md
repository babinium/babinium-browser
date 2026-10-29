# Validación de Babinium Browser 0.4.2

29 de octubre de 2026. Babinium continúa siendo un prototipo experimental.
Las mediciones corresponden a una máquina y unas condiciones concretas; no
demuestran que sea el navegador más liviano ni que sus resultados se repitan en
otros equipos.

En una prueba posterior visible en X11, YouTube restableció 1× poco después
de pedir 1,1× en una ejecución; otra ejecución sí mantuvo la velocidad. Por
esta falla intermitente se preparó una corrección posterior para dar prioridad
a la velocidad de Babinium. Las pruebas satisfactorias citadas abajo no
demuestran que la versión 0.4.2 sea confiable ante ese restablecimiento.

El paquete se compiló para Debian 13 amd64 con opciones x86-64 genéricas en
[GitHub Actions, ejecución 40937476251](https://github.com/babinium/babinium-browser/actions/runs/40937476251),
con las fuentes `df86a442ff2ec226fbd719033d0f7b99e0cc9cf0`. Su SHA-256 es
`e2a0bc36463a50cace16cc896a4d4827fe9115119174baf293ba188388851536`.
Se verificó la descarga y no se instaló automáticamente. Actions aprobó seis
pruebas Rust, seis Python y 33 JavaScript.

## Controles y ayuda

Los controles de medios HTML5 están integrados y activados; no requieren una
extensión, un proceso adicional ni sondeo continuo. Solo buscan un reproductor
al pulsar un atajo. Los componentes con sombra abierta se recorren con un
límite de 4.096 elementos. El indicador se crea al usarlos y se oculta después,
salvo que se fije con V. Sus botones permiten ajustar la velocidad con el ratón.

Se comprobaron todos los atajos con teclas reales en videos y audio HTML5,
un componente con sombra abierta y un iframe de otro origen, y ante un
reproductor que intenta restablecer la velocidad. Las teclas no interfirieron
con la escritura en un campo de texto. Al pulsar «Babinium» desde una pestaña
vacía se abrió la ayuda GTK sin iniciar un proceso de WebKit; se pudo navegar
desde ella y cerrarla.

En YouTube real, sin sesión iniciada, la tecla D ajustó el video de 1× a 1,1×,
que se mantuvo durante cuatro segundos; R volvió a 1×. Se probaron pulsaciones
rápidas, Z/X y M/J, y el video siguió reproduciéndose a 3× durante diez
segundos y después de un salto. Babinium prioriza su velocidad en el medio: por
encima del límite del menú de YouTube, este puede mostrar 2× aunque el medio esté
a 3×. También se probó 1,1× y el regreso a 1× durante la reproducción de un
iframe real de `youtube-nocookie.com`, con bloqueo activado y el video de
ejemplo de la API oficial.

Para un iframe de otro origen hay que hacer clic en el reproductor para darle
el foco. Los reproductores que usen medios protegidos, componentes cerrados o
restricciones propias pueden no admitir los cambios; algunas páginas pueden
contener más elementos que el límite del recorrido de componentes. No es una
garantía de compatibilidad con todos los videos ni de que YouTube conserve su
interfaz interna.

## Regresiones

En el paquete final se probaron bloqueo de solicitudes y excepciones, filtros
cosméticos y scriptlets, control por sitio, navegación, pestañas y descargas.
También pasaron las pruebas de favoritos, búsqueda con Google, fondo negro de
pestañas vacías, modo oscuro y persistencia de cookies, `localStorage` e
IndexedDB con un perfil aislado. No se usó una cuenta de Google: la persistencia
de una sesión real de YouTube después de reiniciar sigue sin verificar.

El bloqueo de anuncios de video de YouTube permanece pendiente de una prueba
comparativa en la que el control muestre efectivamente un anuncio. Bloquear
solicitudes o eliminar datos publicitarios no demuestra por sí solo que se
hayan bloqueado prerolls o anuncios insertados en el flujo.

## Recursos

Las mediciones se hicieron en Debian 13 con WebKitGTK 2.54.0, GStreamer 1.26.2,
una pantalla Xvfb de 1360 × 768 y perfiles aislados, sin actualizaciones de
listas durante la medición. Se muestrearon los procesos del navegador y sus
descendientes cada segundo. La PSS reparte la memoria compartida; la RSS sumada
la cuenta más de una vez. La CPU se expresa respecto de un núcleo lógico. No
se incluye el servidor Xvfb ni toda la memoria de GPU o del núcleo; procesos
que comienzan y terminan entre muestras pueden no registrarse.

Para estimar el costo en una página sin video se abrió la misma página local
estática, sin bloqueo, durante 30 segundos por versión con 15 de calentamiento.
Cada fila es una única ejecución, no una comparación estadística:

| Versión | PSS mediana | RSS sumada mediana | CPU estable | Máx. procesos |
|---|---:|---:|---:|---:|
| 0.3.1 | 261,8 MiB | 493,4 MiB | 0,0 % | 8 |
| 0.4.2 | 260,6 MiB | 492,5 MiB | 0,07 % | 8 |

Estos datos indican un consumo similar en esta prueba; no permiten atribuir la
diferencia pequeña a la función nueva ni predecir el consumo en otras páginas.

En una pestaña vacía, una ejecución de 25 segundos con 10 de calentamiento
dio **59,5 MiB de PSS**, **118,3 MiB de RSS sumada**, **0,0 % de CPU estable**
y un proceso. El primer dibujado de GTK tardó 0,602, 0,633 y 0,661 segundos
en tres arranques: mediana **0,633 segundos**. Se trata del primer dibujado de
la ventana vacía, no del tiempo hasta cargar una página web.

Con bloqueo activado se midió YouTube real a velocidad normal y a 640 × 360,
con H.264 y Opus. La medición duró 100 segundos. La reproducción empezó tarde;
para informar únicamente un tramo en reproducción se analizaron los segundos
60,2 a 99,2: **997,2 MiB de PSS**, **1.257,2 MiB de RSS sumada**, **51,8 % de
un núcleo** y hasta ocho procesos. En la última muestra el video había avanzado
42,4 segundos, con 1.012 fotogramas y uno perdido. La prueba automatizada inició
el video silenciado; la auditoría y el muestreo de estado cada cinco segundos
también estuvieron activos. La variación de red, carga y contenido impide
atribuir diferencias respecto de mediciones anteriores a los controles.

Se registraron hasta 22 solicitudes bloqueadas en un proceso, incluidas
solicitudes de seguimiento: no es un número de anuncios de video. Durante
esta medición no se observó un anuncio de video. Los registros locales quedan
en `runs/`; las pruebas externas y `scripts/measure.py` permiten repetirlos.
Antes de una versión estable se revisarán las opciones de diagnóstico del
producto para retirar las que no sean fundamentales, como pidió Miguel.
