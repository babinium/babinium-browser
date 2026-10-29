# Babinium Browser

Prototipo de navegador libre para Debian 13, escrito en C/GTK 3, con WebKitGTK
4.1 del sistema y bloqueo nativo mediante adblock-rust de Brave. Inspirado por
la simplicidad de surf; la interfaz es nueva. Licencia GPL-3.0-o-posterior.

**Estado: experimental.** No se presenta como el navegador de menor consumo.
Se validaron reproducción real de YouTube, bloqueo de solicitudes publicitarias
y modificación de datos del reproductor. La eliminación de preroll/midroll no
quedó demostrada porque el control tampoco mostró anuncios de vídeo.
Véase el [informe de validación y consumo](docs/validation.md).

- Barra de direcciones y búsqueda, atrás/adelante, pestañas y descargas.
- Bloqueo de solicitudes, CSS específico y genérico, scriptlets uBO/Brave.
- Bloqueo activado por defecto y excepciones por hostname exacto con Ctrl+B.
- EasyList, EasyPrivacy y filtros de uAssets incluidos; actualizaciones HTTPS
  en segundo plano, con validación y cambio atómico. Un fallo conserva la versión
  anterior. Sin servicio residente para actualizar ni intérprete para navegar.
- Sandbox multiproceso de WebKit habilitado, TLS del sistema y cookies sin
  terceros. El motor se actualiza con las actualizaciones de seguridad de Debian.

## Ejecutar

El artefacto de GitHub Actions contiene un `.deb` y `bundle/` ejecutable sin
instalar. Para el bundle se necesitan las dependencias de ejecución del paquete.

```sh
./bundle/bin/babinium-browser https://www.youtube.com/
# Instalación opcional:
sudo apt install ./babinium-browser_0.1.0_amd64.deb
```

Perfil predeterminado: `~/.local/share/babinium-browser`. `--profile DIR` permite
perfiles de prueba independientes. No abrir simultáneamente dos instancias sobre
el mismo perfil. Descargas en la carpeta Descargas del usuario, sin sobrescribir.

Atajos: Ctrl+L dirección, Ctrl+T pestaña, Ctrl+W cerrar, Ctrl+Tab cambiar,
Ctrl+1…9 seleccionar, Ctrl+R recargar, Ctrl+Shift+R sin caché, Alt+flechas navegar,
Ctrl+B bloqueo por sitio, Ctrl+D descargas. El panel de descargas permite forzar
la actualización de listas. Cambiar el bloqueo recarga la pestaña; otras pestañas
del mismo hostname aplican la decisión de red inmediatamente y necesitan recarga
para retirar los scriptlets ya ejecutados.
El contador muestra solicitudes bloqueadas acumuladas en la pestaña, incluyendo
seguimiento; no es un contador de anuncios de vídeo.

## Arquitectura y límites

La extensión de WebKit ejecuta el matcher Rust en su hilo principal, sin IPC por
solicitud. Un motor por proceso web, compartido por las páginas de ese proceso.
Las pestañas vacías son widgets GTK: el contexto WebKit y las vistas se crean
sólo al navegar. Abrir pestañas vacías no inicia procesos web ni carga el índice.
Se carga un índice serializado; no se parsean listas al arrancar la interfaz.
Los scriptlets se inyectan al crear el contexto JavaScript antes de los scripts
del sitio; la consulta cosmética nativa está en un mundo aislado. Los cambios del
DOM se agrupan, sin sondeo permanente. La política de caché reduce retención a
cambio de volver a cargar páginas al retroceder; no se desactivan JIT ni sandbox.

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
  libgtk-3-dev libjson-glib-dev python3 nodejs ca-certificates
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
