# Validación de Babinium Browser 0.4.5

30 de octubre de 2026. Babinium sigue siendo experimental. Estas mediciones
describen una página, un momento y una máquina; no demuestran que sea el
navegador más liviano ni permiten generalizar a todos los sitios.

La compilación para Debian 13 amd64 usó opciones genéricas x86-64 en
[GitHub Actions, ejecución 41071846249](https://github.com/babinium/babinium-browser/actions/runs/41071846249),
con el código `82802ec336a51a60929ea44c0b0f7f20bac951bf`. El paquete Debian
tiene SHA-256 `655271e717464ce2a6419eb9c6f1da2b4af247c73fbb853cdffa3157e72f953c`.
Actions aprobó seis pruebas Rust, seis Python, pruebas C y 41 JavaScript. El
paquete se instaló y sus ejecutables, biblioteca y recursos se compararon con
los descargados. Las ventanas gráficas se mostraron en el escritorio X11 real;
se utilizaron perfiles aislados sin credenciales.

## Favoritos, MPV y velocidad

El panel de favoritos se probó con títulos largos, dominios públicos, direcciones
de prueba y suficientes entradas para desplazar la lista. Se abrieron y quitaron
favoritos y se comprobó que el archivo conservara las URL completas. El nombre
visible utiliza la lista de sufijos públicos del sistema, por ejemplo `youtube`
o `bbc` en lugar de la dirección entera.

El botón aparece para direcciones válidas de videos de YouTube. En una prueba
visible se abrió el video `dQw4w9WgXcQ` en MPV, se cerró Babinium y el tiempo
del video continuó avanzando de 2,96 a 6,36 s. La prueba aislada silenció MPV y
limitó el video a 720p para medirlo; el botón del producto no impone ese límite.
MPV y yt-dlp se recomiendan como dependencias y la disponibilidad de resoluciones
depende de YouTube, la red y la configuración de MPV. Las pruebas no copiaron
cookies de una cuenta a MPV.

Durante una prueba real apareció una reversión a 1× justo después de elegir
1,1×. El control dependía de recibir el evento de cambio para corregirla; una
prueba aislada también reprodujo el caso en que ese aviso no llega al control.
La causa exacta de todas las reversiones observadas en YouTube no quedó probada.
Ahora se agrega una comprobación única 500 ms después de un cambio del usuario,
además de los reintentos por eventos. No hay sondeo continuo. Con el ejecutable
verificado y el script corregido se probó YouTube real: el medio conservó 1,1×
tras dos restablecimientos simulados, avanzó unos 28,8 s en diez segundos a 3×
y conservó 3× después de un salto. También se probaron los atajos de salto y
marca. La repetición con el paquete instalado y sus listas actuales mantuvo
1,1× tras dos restablecimientos, mantuvo el ajuste de 3× después de un salto y
avanzó 24,5 s durante diez segundos de esa fase; la velocidad efectiva puede
variar con la carga y la red. En la instalación se probaron además video, audio, un componente con
sombra, un iframe y dos páginas que restablecían la velocidad; escribir en un
campo no activó los atajos. Algunos reproductores pueden seguir imponiendo sus
propias restricciones.

## CPU y memoria

Las muestras se tomaron con ventanas visibles, perfiles independientes, bloqueo
y modo oscuro activados, y actualización de listas detenida solo durante la
medición. Cada caso de Infobae duró 100 s, con 50 s de calentamiento. La CPU
incluye el navegador y sus procesos descendientes: **100 % equivale a un núcleo
lógico completo**. La PSS reparte memoria compartida; la RSS sumada puede contarla
más de una vez. No se incluye el servidor X ni toda la memoria de GPU o del núcleo.

| Infobae, muestra | Animaciones lejanas | CPU estable | PSS mediana | RSS sumada mediana |
|---|---|---:|---:|---:|
| Primera carga | Normales | 71,1 % | 551,4 MiB | 796,8 MiB |
| Primera carga comparable | Pausadas | 0,82 % | 551,8 MiB | 794,8 MiB |
| Repetición de control | Normales | 75,6 % | 552,9 MiB | 797,2 MiB |
| Página actualizada | Normales | 74,5 % | 616,3 MiB | 858,5 MiB |
| Página actualizada | Pausadas | 15,4 % | 647,8 MiB | 887,6 MiB |

La primera serie usó el ejecutable 0.4.4 y cambió solo el script experimental
de animaciones. La segunda usó el mismo ejecutable y los mismos recursos en ambos
casos, activando o desactivando la preferencia en perfiles separados; ese
ejecutable es idéntico al del paquete final. En la segunda pareja el contenido
textual medido coincidía y se observaron cinco animaciones infinitas muy por
debajo de la pantalla en el control. Las páginas y la red pueden cambiar entre
cargas. Las diferencias de PSS no demuestran una reducción de memoria.

Con el paquete instalado y sus listas incluidas, una medición adicional de la
página actual dio 14,3 % de un núcleo, 614,3 MiB de PSS y 856,1 MiB de RSS
sumada, con hasta ocho procesos. El índice de listas de esa compilación era
distinto del usado en la pareja anterior, por lo que no se usa como control
directo de esa comparación.

Con esa misma instalación y la optimización activa, una segunda carga en modo
claro dio también aproximadamente 14,3 % de un núcleo; el contenido textual
medido coincidía. Es una muestra por modo, no una comparación estadística.
No se encontró una razón para desactivar el modo oscuro predeterminado.

La optimización pausa animaciones CSS infinitas alejadas de la vista y las
reanuda al acercarse; no pausa animaciones finitas ni elementos que combinan
ambos tipos. Usa eventos e `IntersectionObserver`, con un máximo de 256
elementos observados por documento. En la ayuda puede desactivarse si un sitio
depende de los eventos de esas animaciones; el cambio se aplica al recargar.
En WebKit real se verificaron animaciones visibles, lejanas, finitas, mezcladas,
agregadas dinámicamente y pausadas por la propia página.

En YouTube se compararon dos intervalos de 20 s del mismo video a 640 × 360,
H.264 y Opus, con bloqueo activo y reproducción silenciada: 34,2 % de un núcleo
sin el script de animaciones y 35,5 % con él. Son muestras únicas y no muestran
una mejora de CPU en ese video. No se observó un anuncio de video en esas
reproducciones; las solicitudes bloqueadas no son un conteo de prerolls.

La pestaña vacía tuvo una mediana de 45,3 MiB de PSS, 69,2 MiB de RSS sumada,
0 % de CPU estable y un proceso en una medición de 25 s. El primer dibujo de
GTK tardó 0,611, 0,732 y 0,767 s en tres arranques, con mediana de 0,732 s.
Esto mide la ventana vacía, no la carga de una página.

## Evaluación de JavaScript y límites pendientes

En una compilación temporal de diagnóstico se desactivó JavaScript sin agregar
un control al producto. Infobae quedó prácticamente ilegible en modo oscuro y
todavía utilizó 34,9 % de un núcleo en una muestra; YouTube mostró una miniatura
y una interfaz incompleta. Por ello no se agregó un interruptor general de
JavaScript: la optimización de animaciones conserva los scripts de los sitios.

Las pruebas de bloqueo comprobaron solicitudes, excepciones, CSS específico y
genérico, reglas procedurales y scriptlets con una página controlada. El bloqueo
de un anuncio real de video de YouTube frente a un control que sí lo muestre
sigue sin demostrarse; YouTube cambia por región, sesión y experimento. Se
verificó persistencia de cookies, `localStorage` e IndexedDB en un perfil de
prueba, pero no se inició sesión en una cuenta real de Google. Antes de una
versión estable se revisarán las opciones de instrumentación de desarrollo.
