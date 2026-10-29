# Validación de Babinium Browser 0.4.3

29 de octubre de 2026. Babinium sigue siendo un prototipo experimental. Sus
mediciones describen una máquina y unas condiciones concretas, y no son una
comparación suficiente para afirmar que sea el navegador más liviano.

La compilación se realizó en Debian 13 amd64 con opciones x86-64 genéricas en
[GitHub Actions, ejecución 40972766686](https://github.com/babinium/babinium-browser/actions/runs/40972766686),
con las fuentes `ac0580636734ccf443de0c999848dbd0e81561c6`. La descarga se
verificó y el SHA-256 del `.deb` es
`0bdddc42ab4b793edb6b7db0652953077dfffe509a159c55703d7b321c445733`.
Actions aprobó seis pruebas Rust, seis Python y 35 JavaScript. El paquete no se
instaló automáticamente.

Esta versión intenta corregir una falla intermitente detectada en la prueba visible de
0.4.2: después de una tecla de Babinium, YouTube pudo volver de 1,1× a 1×.
Al cambiar la velocidad, Babinium escucha los cambios reales del medio y
reaplica la elegida cuando el sitio la modifica, incluso después de ocultar el
indicador. Limita los reintentos para evitar un ciclo si un sitio se opone
continuamente. No crea un proceso adicional ni mantiene sondeo para el control.

Una prueba visible posterior del paquete 0.4.3 volvió a observar un regreso
espontáneo de 1,1× a 1×. La corrección sí superó reversiones provocadas en las
pruebas, pero esa ejecución muestra que no basta para concluir que el fallo
intermitente haya desaparecido; es necesaria una investigación adicional.

## Pruebas de controles y ayuda

En una prueba visible con YouTube real y un perfil aislado se utilizó el
control de Babinium para ajustar 1,1×. Cuando una acción de la prueba obligó
al video a volver a 1× después de ocultarse el indicador, Babinium lo devolvió
a 1,1×. Se comprobaron las pulsaciones rápidas, los saltos y las marcas, y la
reproducción a 3× durante diez segundos y después de un salto. El medio avanzó
unos 28 segundos durante esos diez segundos; el menú de YouTube puede mostrar
2× mientras el medio reproduce a 3×.

En un video real incrustado de `youtube-nocookie.com`, con el bloqueo activo,
se midió el avance del video en vez de depender de la velocidad indicada por
YouTube: aproximadamente 1,75× al pedir 1,8× y 0,97× al volver a 1×. Son
estimaciones puntuales afectadas por el intervalo de muestreo y la carga.

También se probaron teclas reales con video, audio, sombra abierta e iframe de
otro origen, y con una página que restablece la velocidad. Las teclas no
interfirieron con un campo de texto. La pestaña de ayuda abierta desde
«Babinium» es GTK: desde una pestaña vacía no inició ningún proceso de WebKit.

Los iframes de otro origen necesitan recibir el foco mediante un clic. Algunos
reproductores, medios protegidos, componentes cerrados y velocidades no
admitidas por el medio pueden limitar el control. La búsqueda de componentes
abiertos tiene un límite de trabajo. Cambios futuros de YouTube o sitios que
restablezcan la velocidad continuamente pueden impedir que se conserve.

## Alcance pendiente

El filtrado de solicitudes, las excepciones, las reglas cosméticas y los
scriptlets pasaron las pruebas de integración de 0.4.2. No se demostró el
bloqueo de un anuncio real de video de YouTube frente a un control que sí lo
mostrara. Se verificó la persistencia local de cookies, `localStorage` e
IndexedDB en un perfil aislado, pero no una sesión real de Google tras reiniciar.
Las opciones de instrumentación seguirán disponibles durante el desarrollo y
se revisarán antes de una versión estable, como pidió Miguel.

## Consumo de la corrección en una página sin video

En el escritorio X11 visible de 1366 × 768 se comparó la misma página local
estática con el bloqueo desactivado y perfiles aislados. Se usó el mismo
ejecutable de la compilación 0.4.2 en ambos casos; solo se sustituyó el script
del control por el código corregido de 0.4.3. Cada ejecución duró 30 segundos,
con 15 de calentamiento y una muestra por segundo:

| Control | PSS mediana | RSS sumada mediana | CPU estable | Máx. procesos |
|---|---:|---:|---:|---:|
| 0.4.2 original | 240,1 MiB | 461,3 MiB | 0,07 % | 8 |
| Corrección 0.4.3 | 239,8 MiB | 461,1 MiB | 0,0 % | 8 |

La PSS reparte la memoria compartida; la RSS sumada la cuenta varias veces.
La CPU al 100 % equivale a un núcleo lógico. Se incluyen los procesos del
navegador y descendientes, pero no el servidor X ni toda la memoria de GPU o
del núcleo. Es una muestra por caso en una página sin video: las diferencias
son demasiado pequeñas para atribuirlas a la corrección o concluir que mejora
el consumo en general. Los resultados con Xvfb de la versión anterior están
en [validación 0.4.2](validation-0.4.2.md) y no se comparan directamente con
estas cifras de escritorio.
