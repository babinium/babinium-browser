# Validación de Babinium 0.4.12

Fecha: 30 de octubre de 2026. La compilación de prueba se hizo en Debian 13
amd64 en GitHub Actions, ejecución 41137737437, commit `45603d9f2eadc51a97fc17d0abc258b1a5fe64d6`.
La batería completa pasó: pruebas C y Rust, 19 de Python y 31 de JavaScript.
Las pruebas gráficas se realizaron en la pantalla X11 visible, con perfiles
aislados, sin usar la cuenta ni los datos de navegación de Miguel.

## Resultados funcionales

- Las llaves modificaron velocidad en pasos de 0,5× en video, audio, un iframe y
  un componente abierto; los atajos anteriores no interfirieron. Se comprobó el
  campo de texto y la recuperación ante cambios de velocidad del reproductor.
  Miguel confirmó que sus teclas físicas funcionan.
- La ayuda mostró las llaves para videos fuera de YouTube y los controles de
  MPV. La casilla de subtítulos comenzó desactivada; al activarla y elegir 360p,
  ambas preferencias se guardaron.
- El video real `hd1kyFrchBw` abrió MPV a 720p sin subtítulos por defecto y MPV
  siguió reproduciendo tras cerrar Babinium. Al reiniciar con las opciones
  activadas, el mismo MPV reprodujo a 360p con una pista española automática
  procesada y texto de subtítulos visible. Se comprobaron { y } en MPV y el
  botón «Abrir MPV» volvió a iniciar el video con esas opciones guardadas. En los
  562 fragmentos procesados no se encontraron solapamientos ni fragmentos con
  una línea anterior junto a otra nueva.
- En una página local, el bloqueo de solicitudes, filtros cosméticos y
  scriptlets funcionó y la excepción por sitio los desactivó.
- Se comprobaron pestañas, navegación, recarga, una descarga, favoritos,
  búsqueda Google, fondo negro inicial, tema oscuro, y persistencia de cookies,
  almacenamiento local e IndexedDB entre reinicios.

## Medición orientativa

Una muestra en esta PC, con pantalla visible, perfil aislado y actualizaciones
de listas desactivadas durante la medición. No es una comparación con otros
navegadores ni una garantía para otras páginas o equipos. PSS reparte la memoria
compartida y CPU 100 % equivale a un núcleo lógico completo.

| Caso | Duración y ventana estable | RAM PSS mediana | RAM RSS sumada mediana | CPU estable | Primer dibujo |
| --- | --- | ---: | ---: | ---: | ---: |
| Pestaña vacía | 16 s, últimos 11 s | 45 MiB | 70 MiB | 0,1 % de un núcleo | 0,65 s |
| YouTube y MPV a 720p, MPV silenciado | 40 s, últimos 25 s | 969 MiB | 1.260 MiB | 117 % de un núcleo | 1,02 s |

En esa muestra de YouTube la mediana proporcional fue aproximadamente 697 MiB
para el proceso web y 129 MiB para MPV; el resto corresponde a Babinium y sus
otros procesos. La señal de carga terminada de la página llegó a los 15,45 s.
Las cifras incluyen procesos descendientes observados, pero no el servidor X ni
otras aplicaciones del escritorio; procesos muy breves pueden quedar fuera.
RSS suma memoria compartida más de una vez.

## Límites de la comprobación

El bloqueo se verificó con una página controlada, no con un anuncio real de
video de YouTube en una reproducción de control. Tampoco se inició sesión en una
cuenta Google real ni se validaron todas las páginas, transmisiones en vivo,
formatos de subtítulos o distribuciones de teclado. Los subtítulos generados
automáticamente pueden contener errores. Se trata de un prototipo experimental.
