# Validación de Babinium Browser 0.4.4

29 de octubre de 2026. Babinium sigue siendo experimental. Las cifras de una
prueba describen esa máquina y esas condiciones; no bastan para afirmar que
Babinium sea el navegador más liviano.

La compilación se realizó en Debian 13 amd64 con opciones x86-64 genéricas en
[GitHub Actions, ejecución 40974591903](https://github.com/babinium/babinium-browser/actions/runs/40974591903),
con las fuentes `10df4424778a6f120b40dda8c59dc2055e9b1d3d`. La descarga se
verificó y el SHA-256 del `.deb` es
`cfdb1801cb2211259cd9af226e8b2f05132883afb838746f75b299905c5c8015`.
Actions aprobó seis pruebas Rust, seis Python y 36 JavaScript. El paquete no se
instaló automáticamente.

La prioridad de los controles propios motivó dos correcciones. En pruebas
visibles de 0.4.2 y 0.4.3 se observó una reversión espontánea de 1,1× a 1× en
YouTube, aunque otras ejecuciones sí mantuvieron la velocidad. Además se
reprodujo con una página local un caso concreto: una página puede detener el
evento de cambio de velocidad antes de que llegue al control del medio.

Babinium ahora escucha ese evento durante su captura en el documento y también
en el medio, para cubrir componentes de sombra. Tras un cambio de velocidad
intenta restaurar la elegida si el sitio la modifica, incluso cuando el
indicador ya se ocultó; limita los reintentos para evitar ciclos. Este mecanismo
es por eventos: no crea un proceso ni mantiene un sondeo continuo.

## Pruebas visibles

La página local que restablecía 1× y detenía el evento falló con 0.4.3 y pasó
con el código corregido: el video volvió a 1,1× y siguió reproduciéndose.
También se probaron video, audio, componentes con sombra abierta e iframe de
otro origen, escritura en un campo de texto, todos los atajos y los botones
del indicador.

En YouTube real, con un perfil aislado y el bloqueo activado, la prueba cambió
el video a 1,1× y obligó tanto al reproductor como al medio a volver a 1×,
primero inmediatamente y luego con el indicador oculto. Babinium recuperó
1,1×. Se probaron pulsaciones rápidas, Z/X y M/J, y el video avanzó durante
diez segundos a 3× y conservó esa velocidad después de un salto. Por encima
del límite de su menú, YouTube puede mostrar 2× mientras el medio va a 3×.

En un video real incrustado de `youtube-nocookie.com`, con bloqueo activo,
se midió el avance real: aproximadamente 1,75× al pedir 1,8× y 0,96× al volver
a 1×. Son estimaciones puntuales influidas por el muestreo y la carga.

Las dos reversiones espontáneas observadas en versiones anteriores no tuvieron
una causa concluyente; la prueba de eventos detenidos demuestra y cubre una
limitación concreta, pero no prueba que esa haya sido la causa de ambas. Los
reproductores que fuerzan cambios repetidamente, medios protegidos, componentes
cerrados o velocidades no admitidas pueden limitar el control. Para un iframe
de otro origen hay que hacer clic en el reproductor para darle el foco; el
recorrido de componentes abiertos tiene un límite de trabajo.

## Funciones pendientes de validación

El paquete final pasó las pruebas de solicitudes bloqueadas y permitidas,
reglas cosméticas y procedurales, scriptlets y control por sitio, con el
bloqueo activado y desactivado. La pestaña de ayuda se abrió desde «Babinium»
sin iniciar un proceso WebKit desde una pestaña vacía.

No se ha demostrado el bloqueo de un anuncio real de video de YouTube frente a
un control que sí lo muestre. Se comprobó la persistencia local de cookies,
`localStorage` e IndexedDB en un perfil aislado, pero no una sesión real de
Google tras reiniciar. Las opciones de instrumentación seguirán disponibles
durante el desarrollo y se revisarán antes de una versión estable, como pidió
Miguel. La [lista de requisitos](REQUISITOS.md) conserva lo terminado y pendiente.

## Consumo del control en una página sin video

En el escritorio X11 visible, de 1366 × 768, se midió la misma página local
estática sin bloqueo, durante 30 segundos por caso con 15 de calentamiento.
Para aislar el cambio se usó el mismo ejecutable 0.4.3: solo se sustituyó el
script del control por el de 0.4.4. Cada fila representa una sola ejecución.

| Control | PSS mediana | RSS sumada mediana | CPU estable | Máx. procesos |
|---|---:|---:|---:|---:|
| 0.4.3 | 240,5 MiB | 461,7 MiB | 0,14 % | 8 |
| 0.4.4 | 240,7 MiB | 461,4 MiB | 0,07 % | 8 |

La CPU al 100 % equivale a un núcleo lógico. La PSS reparte la memoria
compartida y la RSS sumada la cuenta varias veces. Las muestras incluyen los
procesos del navegador y sus descendientes, pero no el servidor X ni toda la
memoria de GPU o del núcleo. La diferencia pequeña no demuestra una mejora ni
predice el consumo de otras páginas.

En una pestaña vacía del paquete final, una ejecución de 25 segundos con 10
de calentamiento dio **41,1 MiB de PSS**, **69,8 MiB de RSS sumada**, **0,0 %
de CPU estable** y un proceso. El primer dibujado de GTK tardó 0,642, 1,013
y 0,650 segundos en tres arranques: mediana **0,650 segundos**. Se mide la
ventana vacía, no el tiempo necesario para cargar una página.

Con el paquete final y el bloqueo activado se midió YouTube real en el mismo
escritorio, a velocidad normal y 640 × 360 con H.264 y Opus. La ejecución duró
100 segundos, con 50 de calentamiento. La mediana fue **958,3 MiB de PSS** y
**1.205,4 MiB de RSS sumada**; la CPU estable fue **37,9 % de un núcleo**, con
hasta ocho procesos. En la última muestra el video había avanzado 64,9 segundos
y el reproductor registró 1.624 fotogramas y ninguno perdido. Se utilizó un
perfil aislado, el video se inició silenciado y se consultó su estado cada
cinco segundos. No se incluyó el servidor X ni toda la memoria de GPU o del
núcleo. Es una sola ejecución y depende de red, contenido y carga del equipo.

Durante esta medición no se observó un anuncio de video; no valida el bloqueo
de prerolls. Las muestras y perfiles de prueba quedan en `runs/`, fuera del
repositorio. Para el método y resultados anteriores véase
[validación 0.4.3](validation-0.4.3.md).
