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
- [ ] Repetir las mediciones con las nuevas funciones y con YouTube real.
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
- [ ] Configurar YouTube por defecto para priorizar consumo bajo y fluidez,
  incluyendo calidad y códecs cuando sea técnicamente posible; medir el efecto,
  conservar la reproducción y permitir que el usuario cambie la calidad.

## Interfaz y datos

- [x] Barra de direcciones, navegación, pestañas y descargas.
- [ ] Usar Google como buscador predeterminado.
- [ ] Modo oscuro de páginas activado por defecto, similar a Dark Reader, con
  un control por sitio cuando un diseño resulte incompatible.
- [ ] Mostrar «Babinium» al extremo derecho de la barra de pestañas.
- [ ] Mostrar negro desde el primer instante en una pestaña nueva vacía.
- [ ] Permitir guardar, consultar y quitar favoritos y conservarlos al cerrar.
- [ ] Conservar sesiones, cookies y datos de sitios entre reinicios; comprobar
  persistencia y documentar cualquier límite específico del inicio de sesión
  de Google/YouTube sin pedir ni almacenar contraseñas en el proyecto.

## Entrega

- [x] Compilar en GitHub Actions y generar un paquete Debian verificable.
- [x] Documentar límites técnicos del bloqueo y alternativas que conserven, en
  lo posible, ligereza y eficacia, sin prometer que todos los anuncios de
  YouTube siempre se bloquearán.
