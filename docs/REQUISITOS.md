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
- [x] Configurar YouTube por defecto para priorizar consumo bajo y fluidez,
  incluyendo calidad y códecs cuando sea técnicamente posible; medir el efecto,
  conservar la reproducción y permitir que el usuario cambie la calidad. La
  preferencia de resolución usa un método interno que YouTube puede cambiar; la
  selección de códec es tentativa y no se demostró una mejora general de CPU.
- [x] Intentar desactivar inicialmente la iluminación cinemática de YouTube
  para reducir el trabajo gráfico, manteniendo el ajuste manual y su persistencia.
  Los menús reconocidos son inglés y español; si YouTube cambia la interfaz o
  usa otro idioma, se mantiene su comportamiento normal.
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
