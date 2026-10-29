# Viabilidad comprobada y decisiones

Consulta de APIs y fuentes: 29 de octubre de 2026.

La combinación es viable para un navegador de propósito general y un bloqueador
nativo, con limitaciones respecto a Chromium/Gecko. Se usa GTK 3 + WebKitGTK 4.1
para conservar una interfaz pequeña y el motor actualizado de Debian 13. surf
sirve de referencia; incorporar barra, pestañas y descargas resulta más directo
con una interfaz propia que añadiendo parches a su manejo por XProperties.

1. [WebPage::send-request](https://webkitgtk.org/reference/webkit2gtk-web-extension/2.42.4/signal.WebPage.send-request.html)
   puede cancelar cargas antes de red, incluidas redirecciones. Se conecta en
   la extensión del proceso web; `resource-load-started` de la interfaz no es un
   interceptor equivalente.
2. [WebKitURIRequest](https://webkitgtk.org/reference/webkit2gtk-web-extension/2.42.4/class.URIRequest.html)
   sólo expone URL, método y cabeceras. No ofrece el contexto completo de cada
   solicitud. El prototipo identifica tipos por metadatos y heurísticas; por
   eso no promete paridad con Brave.
3. [Engine de adblock-rust](https://docs.rs/adblock/0.13.3/adblock/engine/struct.Engine.html)
   compila reglas, consulta red, devuelve CSS, acciones y scripts; la aplicación
   debe ejecutar los recursos, observar clases/IDs y respetar excepciones.
4. [Recursos de Brave](https://github.com/brave/adblock-resources) contienen sólo
   sus recursos adicionales. Se necesitan también los scriptlets y sustitutos
   de uBlock Origin; el prototipo transforma el registro ESM de uBO y verifica
   dependencias antes de crear el paquete.
5. uAssets emplea condicionales como `cap_html_filtering`. Al no ofrecer WebKitGTK
   reescritura de respuesta, hay que seleccionar las ramas de scriptlets para
   WebKit, no ignorar comentarios y aplicar las dos ramas simultáneamente.

## YouTube

Se incluyen filtros uAssets de YouTube y quick-fixes. Se inyectan en el contexto
de página al limpiarse el objeto window, antes de sus scripts. Los filtros
cosméticos, de red y los scripts cubren mecanismos distintos. No se usa un
reproductor externo ni se descarga el vídeo para aparentar reproducción interna.

Una prueba positiva debe mostrar que currentTime avanza, se decodifican frames
y no existe un error de reproducción, junto con evidencia de anuncios filtrados.
Un contador de solicitudes a rastreadores no demuestra por sí solo bloqueo de
preroll/midroll. Un vídeo que no recibió publicidad en el control sin bloqueo
tampoco permite concluir que el bloqueador eliminó sus anuncios.

## Alternativas conservando las prioridades

Primero conviene mantener la interfaz C/GTK y añadir reglas compiladas
`WebKitUserContentFilter` para las reglas traducibles: el motor conoce los tipos
exactos y puede bloquear antes de IPC, pero su formato pierde semántica de uBO;
hay que verificar excepciones y evitar duplicar todos los índices. No resuelve
por sí solo la modificación de respuestas ni todas las variantes de YouTube.

Si el requisito pasa a ser bloqueo robusto de YouTube ante todos los experimentos,
la alternativa práctica es Firefox ESR del sistema con uBlock Origin completo.
Introduce una interfaz y motor distintos, pero aporta APIs probadas de bloqueo,
reescritura y mantenimiento de filtros. Debe medirse con la misma carga antes de
comparar consumo. Mantener un fork de WebKit con APIs privadas para lograr
paridad elevaría mucho el coste de seguridad y mantenimiento; no se recomienda
como primer prototipo ligero. Ningún bloqueador puede garantizar permanentemente
todos los anuncios de una plataforma que cambia el protocolo.
