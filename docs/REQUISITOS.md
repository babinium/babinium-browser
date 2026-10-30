# Requisitos de Babinium Browser

Esta lista conserva los pedidos de Miguel y distingue lo terminado de lo que
todavía necesita implementación o validación. Un prototipo no es una versión
estable; los resultados de consumo pertenecen a la máquina y pruebas indicadas.

## Base y objetivos

- [x] Proyecto de código abierto en un repositorio público de GitHub.
- [x] Navegador para Debian con interfaz mínima en C y GTK, tomando a surf como
  referencia, y usando el WebKitGTK actualizado del sistema.
- [x] Integrar de forma nativa la biblioteca `adblock-rust` de Brave.
- [x] Buscar bajo consumo de RAM y CPU, arranque rápido y fluidez por diseño,
  sin optimizar para un modelo de procesador ni una cantidad de memoria.
- [x] Medir RAM de todos los procesos, CPU y arranque durante el desarrollo;
  conservar el método y las condiciones de las pruebas.
- [x] Repetir las mediciones con las nuevas funciones y con YouTube real; el
  informe identifica qué binario y condiciones se usaron para cada muestra.
- [x] Seguir mejorando la rapidez y la fluidez, y buscar menor CPU y RAM sin
  quitar el bloqueo ni las funciones pedidas; medir cada mejora y señalar
  expresamente cuando una reducción de memoria no esté demostrada.
- [ ] Antes de una versión estable, revisar y quitar del producto las opciones
  de instrumentación que no sean fundamentales; mantener las pruebas externas.
- [x] Evitar afirmaciones de ser el navegador más liviano sin una comparación
  válida y no confundir tamaño del ejecutable con uso de memoria.

## Bloqueo y compatibilidad

- [x] Bloqueo activado por defecto y actualización automática de listas.
- [x] Bloquear solicitudes, aplicar filtros cosméticos y scriptlets, y ofrecer
  control de bloqueo por sitio.
- [x] Probar sitios actuales y reproducir vídeo y audio de YouTube real.
- [ ] Validar bloqueo de anuncios de vídeo de YouTube frente a una reproducción
  de control donde efectivamente aparezca un anuncio; la prueba anterior observó
  eliminación de datos publicitarios, pero no pudo confirmar un preroll real.
- [x] Priorizar consumo bajo y fluidez en YouTube, con resolución y códec
  preferidos en MPV. Las anteriores preferencias del reproductor de YouTube
  dejaron de aplicarse cuando se deshabilitó su reproducción en la página.
- [x] En videos de YouTube, ofrecer «Abrir MPV» y permitir que MPV continúe
  reproduciendo después de cerrar Babinium. Priorizar audio en español cuando
  exista, sin cargar subtítulos; no adaptar la elección a un modelo de equipo.
  La versión de yt-dlp de Debian 13 de abril de 2025 falló con un video real; la de
  trixie-backports de octubre de 2026 funcionó y se documentó cómo actualizarla.
- [ ] Abrir MPV automáticamente una vez al entrar en cada video de YouTube;
  dejar la página y sus recomendaciones abiertas, impedir su reproducción y
  reemplazar el video actual en MPV al elegir otro. Tras cerrar MPV, el botón
  lo vuelve a abrir. Solo aplica a YouTube. Miguel informó que funciona; falta
  comprobar si la página descarga datos del video.
- [ ] Ofrecer en la pestaña «Babinium» un selector persistente de resolución de
  MPV entre 144p y 1080p, con 720p por defecto. Pendiente de prueba por Miguel.
- [x] Investigar y reducir cuando sea posible el consumo de CPU en Infobae y
  YouTube, midiendo sin quitar por defecto las funciones solicitadas.
- [x] Evaluar si un control de JavaScript por sitio merece incorporarse, tras
  medir consumo y compatibilidad en Infobae y YouTube.
- [x] Conservar el control del usuario cuando abra el menú durante la
  configuración inicial; la versión 0.3.1 se probó con selección real de 720p.

## Interfaz y datos

- [x] Barra de direcciones, navegación, pestañas y descargas.
- [x] Usar Google como buscador predeterminado.
- [x] Modo oscuro de páginas activado por defecto, con la API de Dark Reader y
  un control por sitio cuando un diseño resulte incompatible.
- [x] Mostrar «Babinium» al extremo derecho de la barra de pestañas.
- [x] Mostrar negro desde el primer instante en una pestaña nueva vacía.
- [x] Permitir guardar, consultar y quitar favoritos y conservarlos al cerrar.
- [x] Ampliar el panel de favoritos y permitir leer los títulos en varias
  líneas; mostrar solo el nombre principal del sitio (por ejemplo, «youtube»),
  conservando internamente la dirección completa para abrir cada favorito.
- [x] Integrar controles de velocidad para video y audio HTML5 con los atajos
  predeterminados de Video Speed Controller, sin instalar una extensión ni
  habilitar procesos o sondeo continuos adicionales. Priorizar la velocidad
  elegida con Babinium si YouTube intenta volver a su propio ajuste; las
  restricciones de cada medio o reproductor pueden impedir algunos cambios.
- [x] Abrir una pestaña de ayuda al pulsar «Babinium» en la barra de pestañas;
  incluir los controles de velocidad y permitir agregar información más adelante.
- [x] Conservar cookies, almacenamiento local e IndexedDB entre reinicios; se
  verificó con un perfil de prueba independiente.
- [ ] Verificar una sesión real de Google/YouTube al reiniciar. La página de
  acceso carga, pero todavía no se probó una cuenta autenticada; Google puede
  limitar los navegadores integrados. No pedir ni guardar contraseñas en el
  proyecto ni usar el perfil real del usuario para las pruebas automáticas.

## Entrega

- [x] Compilar en GitHub Actions y generar un paquete Debian verificable.
- [x] Documentar límites técnicos del bloqueo y alternativas que conserven, en
  lo posible, ligereza y eficacia, sin prometer que todos los anuncios de
  YouTube siempre se bloquearán.
