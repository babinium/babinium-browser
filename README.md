# Babinium Browser

Prototipo de navegador libre para Debian 13, escrito en C/GTK 3, con WebKitGTK
4.1 del sistema y bloqueo nativo mediante adblock-rust de Brave. Inspirado por
la simplicidad de surf; la interfaz es nueva. Licencia GPL-3.0-o-posterior.

**Estado: experimental.** No se presenta como el navegador de menor consumo.
En versiones anteriores se validaron reproducción real de YouTube, bloqueo de
solicitudes publicitarias y modificación de datos del reproductor. La eliminación
de preroll/midroll no quedó demostrada porque el control tampoco mostró anuncios
de vídeo. Miguel informó que la apertura automática de MPV de la versión 0.4.7
funciona; el selector de resolución y la opción de subtítulos quedan pendientes
de prueba manual.
Véanse los informes de [validación 0.4.5](docs/validation-0.4.5.md), [validación 0.4.4](docs/validation-0.4.4.md), [validación 0.4.3](docs/validation-0.4.3.md),
[validación 0.4.2](docs/validation-0.4.2.md), [validación 0.3.1](docs/validation-0.3.1.md),
[validación 0.3.0](docs/validation-0.3.md), [validación 0.2](docs/validation-0.2.md) y del
[prototipo inicial 0.1](docs/validation.md).
La [lista de requisitos y su estado](docs/REQUISITOS.md) conserva todos los
pedidos y los puntos que todavía requieren pruebas.

- Barra de direcciones con búsqueda Google, atrás/adelante, pestañas y descargas.
- Pestañas vacías negras y «Babinium ⚙» en el extremo derecho de la barra.
- Favoritos en el perfil, con estrella y panel amplio de títulos y nombres de
  sitio; cookies y datos de sitios persistentes entre reinicios.
- Control integrado de velocidad para medios HTML5, con indicador y los atajos de
  [Video Speed Controller](https://github.com/igrigorik/videospeed). Al pulsar
  «Babinium» se abre una pestaña de ayuda GTK.
- Al abrir un video de YouTube, Babinium mantiene la página abierta, deshabilita
  su reproducción y abre el video automáticamente en MPV. Otro video reemplaza
  al anterior en el mismo MPV. «Abrir MPV» permite volver a abrir el video tras
  cerrar el reproductor; MPV puede seguir funcionando al cerrar el navegador.
  La resolución se elige entre 144p y 1080p en la pestaña «Babinium»; el valor
  inicial es 720p y la elección se guarda. Prefiere H.264 y audio en español
  cuando están disponibles. Los subtítulos son opcionales, están desactivados por
  defecto y la elección se guarda: se prefiere el español y, si falta, otro
  idioma disponible. Requiere MPV y yt-dlp.
- Para reducir CPU, las animaciones CSS infinitas muy alejadas de la pantalla
  se pausan y vuelven a moverse antes de entrar en la vista. La opción se puede
  desactivar desde la ayuda al pulsar «Babinium»; recargá luego la página.
- Modo oscuro predeterminado con la API local de Dark Reader; el botón Oscuro
  permite excluir un sitio. YouTube usa su propio tema oscuro cuando está
  disponible. Cuando el fondo y varios puntos visibles ya son oscuros se evita
  transformar la página; es una heurística inicial, no detección perfecta. La
  integración API no incluye todas las correcciones de la extensión de
  escritorio y respeta las restricciones CORS de la página.
- Bloqueo de solicitudes, CSS específico y genérico, scriptlets uBO/Brave.
- Bloqueo activado por defecto y excepciones por hostname exacto con Ctrl+B.
- EasyList, EasyPrivacy y filtros de uAssets incluidos; actualizaciones HTTPS
  en segundo plano, con validación y cambio atómico. Un fallo conserva la versión
  anterior. Sin servicio residente para actualizar ni intérprete para navegar.
- Sandbox multiproceso de WebKit habilitado, TLS del sistema y cookies sin
  terceros. El motor se actualiza con las actualizaciones de seguridad de Debian.

## Ejecutar

Descargá el paquete para Debian 13 amd64 desde la [última versión publicada](https://github.com/babinium/babinium-browser/releases/latest).
El artefacto de GitHub Actions también contiene un `.deb` y `bundle/` ejecutable
sin instalar. Para el bundle se necesitan las dependencias de ejecución del paquete.

```sh
./bundle/bin/babinium-browser https://www.youtube.com/
# Instalación opcional:
sudo apt install ./babinium-browser_0.4.10_amd64.deb
```

«Abrir MPV» necesita una versión reciente de `yt-dlp`: la versión de abril de
2025 de Debian 13 falló con un video real de YouTube, mientras que la de
trixie-backports 2026.10.21 funcionó en esa prueba. El paquete recomienda esta
última o una más reciente, sin obligar a instalar MPV para usar el navegador.
Después de activar el repositorio oficial siguiendo las [instrucciones de Debian
Backports](https://backports.debian.org/Instructions/), se puede actualizar solo
el extractor con `sudo apt update` y `sudo apt install yt-dlp/trixie-backports`.
YouTube cambia con el tiempo, por lo que ninguna versión garantiza reproducir
todos los videos; MPV no recibe automáticamente la sesión de Babinium. Algunos
videos pueden requerir además la [configuración de JavaScript de yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/EJS).
La selección se aplica al abrir o volver a abrir un video. Si la calidad elegida
no existe, se busca una inferior; si no hay un formato compatible a esa altura o
menor, MPV informará un error. El español se aplica solo a las pistas disponibles
en el video. La opción de subtítulos también se aplica al abrir o volver a abrir
un video; las pistas generadas automáticamente pueden contener errores.

Perfil predeterminado: `~/.local/share/babinium-browser`. `--profile DIR` permite
perfiles de prueba independientes. No abrir simultáneamente dos instancias sobre
el mismo perfil. Descargas en la carpeta Descargas del usuario, sin sobrescribir.

Atajos: Ctrl+L dirección, Ctrl+T pestaña, Ctrl+W cerrar, Ctrl+Tab cambiar,
Ctrl+1…9 seleccionar, Ctrl+R recargar, Ctrl+Shift+R sin caché, Alt+flechas navegar,
Ctrl+B bloqueo por sitio, Ctrl+D guardar/quitar favorito, Ctrl+Shift+D favoritos,
Ctrl+Shift+M modo oscuro por sitio, Ctrl+J descargas. El panel de descargas permite forzar
la actualización de listas. Cambiar el bloqueo recarga la pestaña; otras pestañas
del mismo hostname aplican la decisión de red inmediatamente y necesitan recarga
para retirar los scriptlets ya ejecutados.
El contador muestra solicitudes bloqueadas acumuladas en la pestaña, incluyendo
seguimiento; no es un contador de anuncios de vídeo.

Con un video o audio presente: S/D disminuyen/aumentan 0,1×; R vuelve a 1×;
G alterna entre 1,8× y la velocidad anterior; Z/X retroceden/avanzan 10 s;
M guarda una marca, J vuelve a ella y V fija u oculta el indicador. El indicador
también ofrece botones −/+. Los atajos no se activan mientras se escribe ni con
Ctrl, Alt, Super o Mayúsculas. Para medios en un iframe de otro origen, hacé
clic en el reproductor para enfocarlo. Algunos reproductores, medios protegidos,
elementos en componentes cerrados o transmisiones pueden limitar estos controles.
En videos de YouTube incrustados en otros sitios, Babinium prioriza la velocidad
pedida; su indicador muestra la velocidad real, aunque el menú propio de YouTube
no coincida por encima de 2×. En la ventana de MPV se usan sus propios controles:
espacio o p pausa; las flechas izquierda y derecha retroceden o avanzan; [ y ]
cambian la velocidad; Retroceso vuelve a 1×; 9 y 0 cambian el volumen; m silencia;
f y Esc controlan la pantalla completa; v muestra u oculta subtítulos y q cierra
MPV. Estos atajos pueden variar si se personalizó la configuración de MPV.
Después de cambiar la velocidad, el navegador escucha cambios del medio y
reaplica la elegida si el sitio la restablece, con reintentos limitados y sin
sondeo continuo. Tras cada cambio manual hace además una sola comprobación
breve para cubrir avisos de cambio perdidos. Si un reproductor la fuerza
repetidamente, puede prevalecer su límite.

En páginas de YouTube se deshabilita la reproducción multimedia de WebKit y se
bloquean las solicitudes de video conocidas hacia Googlevideo y los manifiestos
de YouTube. Esto no bloquea el tráfico independiente de MPV ni los videos de
otros sitios. YouTube puede cambiar su implementación: la carga de sus
recomendaciones y la ausencia de solicitudes de video necesitan prueba manual.
La persistencia del perfil no garantiza que Google acepte iniciar sesión en
todos los navegadores integrados.

## Arquitectura y límites

La extensión de WebKit ejecuta el matcher Rust en su hilo principal, sin IPC por
solicitud. Un motor por proceso web, compartido por las páginas de ese proceso.
Las pestañas vacías son widgets GTK: el contexto WebKit y las vistas se crean
sólo al navegar. Abrir pestañas vacías no inicia procesos web ni carga el índice.
Se carga un índice serializado; no se parsean listas al arrancar la interfaz.
Los scriptlets se inyectan al crear el contexto JavaScript antes de los scripts
del sitio; la consulta cosmética nativa está en un mundo aislado. Los cambios del
DOM se agrupan, sin sondeo permanente. El filtrado cosmético conserva un máximo
de ocho conjuntos pequeños de excepciones por URL para evitar volver a calcular
los recursos completos al aparecer clases nuevas; se limpia al cambiar el motor.
La política de caché reduce retención a
cambio de volver a cargar páginas al retroceder; no se desactivan JIT ni sandbox.
La optimización de animaciones usa `IntersectionObserver`, sin sondeo continuo,
y deja intactas las animaciones finitas y los elementos que las combinan con
otras infinitas. Tiene un límite de 256 elementos observados por documento.
Pausar animaciones lejanas puede afectar páginas que dependan de sus eventos;
si ocurre, desactivá la opción en la ayuda y recargá. El cambio afecta a páginas
posteriores o recargadas y no modifica la preferencia de JavaScript.

`WebPage::send-request` permite cancelar y cambiar URLs, pero la API pública no
expone el tipo exacto de recurso ni su frame iniciador. Se usa Sec-Fetch-Dest si
está disponible, Referer, Accept y finalmente sufijos de URL. Las solicitudes
desconocidas se clasifican como `other`. Esto limita reglas con tipos específicos,
algunos iframes, workers y WebSockets. No hay filtrado HTML ni reescritura nativa
del cuerpo de respuestas. Los scriptlets compensan parte de esta carencia;
**no equivalen a integrar todo Brave ni todo uBlock Origin**.

La ejecución cosmética tiene límites de trabajo para no monopolizar CPU; una
cola muy grande puede omitir elementos y algunos operadores complejos. El
bloqueo de vídeo de YouTube cambia por región, sesión y experimento. Los filtros
actuales y los recursos uBO/Brave son necesarios, pero no garantizan eliminar
anuncios integrados en el mismo flujo del contenido. Véase `docs/feasibility.md`
y la evidencia de pruebas para el alcance comprobado.

## Construir en Debian 13

```sh
sudo apt install build-essential pkg-config libwebkit2gtk-4.1-dev \
  libgtk-3-dev libjson-glib-dev libsoup-3.0-dev python3 nodejs ca-certificates
# Con trixie-backports configurado (Rust >= 1.88):
sudo apt install -t trixie-backports cargo rustc
make -j2
make resources
make test
make package
```

El workflow manual `Compilar Debian 13 amd64` realiza estos pasos en un contenedor
Debian 13. Opciones genéricas x86-64, sin `-march=native` ni adaptación al equipo.
Actions compila, empaqueta y ejecuta pruebas unitarias. Las pruebas gráficas con
sandbox y YouTube real se ejecutan como usuario normal en Debian; Docker introduce
restricciones distintas sobre los namespaces de bubblewrap.
Las listas se descargan al construir; los recursos de código tienen revisiones
fijas en `data/upstream.json`. Cada descarga incluye procedencia y hash; las
fuentes originales de los recursos se entregan con el artefacto. `Cargo.lock`
fija las dependencias después de la primera compilación.

## Diagnóstico y medición

No se recopila telemetría en uso normal. `--telemetry FILE` escribe localmente
eventos JSONL con URLs y tiempos. `--audit` añade URLs bloqueadas. `--eval FILE`,
`--probe-interval N`, `--screenshot PNG` y `--quit-after N` son opciones explícitas
para reproducir pruebas. `--no-block` sirve para comparaciones; `--no-update`
separa las mediciones estables del trabajo de actualización.

La medición debe sumar todos los procesos: RSS suma memoria compartida varias
veces, PSS la reparte. Deben publicarse ambas, cantidad de procesos, CPU acumulada
y por intervalo, tiempo hasta mostrar interfaz y hasta contenido útil. Comparar
con otros navegadores exige misma URL, resolución de vídeo, perfil, caché,
sesión, aceleración y duración. El tamaño del binario no mide el consumo.
