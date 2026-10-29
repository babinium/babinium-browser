# Componentes y procedencia

- WebKitGTK, GTK, GLib, libsoup, JavaScriptCore y GStreamer: bibliotecas del
  sistema Debian, conservan sus licencias. No se incluye un motor web propio.
- [adblock-rust](https://github.com/brave/adblock-rust), versión 0.13.3, MPL-2.0,
  biblioteca sin modificaciones enlazada a la extensión y al compilador de
  índices. Las dependencias exactas se fijan en `blocker/Cargo.lock`.
- [uBlock Origin](https://github.com/gorhill/uBlock), GPL-3.0-o-posterior,
  scriptlets y recursos. Revisión fija en `data/upstream.json`. Se transforman
  funciones y metadatos al formato Resource de adblock-rust. El archivo original
  y sus avisos se conservan en `upstream-sources.tar.gz` del artefacto.
- [Brave adblock-resources](https://github.com/brave/adblock-resources),
  MPL-2.0, revisión fija en `data/upstream.json`; recursos sin modificación.
- [Dark Reader](https://github.com/darkreader/darkreader), versión 4.9.134,
  licencia MIT: API integrada como script local, con archivo original y licencia
  incluidos. SHA-256 del paquete npm: `e3da6d984ffa830229c31f531fc9f0666910549ff74655c022bb411c70d47745`.
- [EasyList/EasyPrivacy](https://easylist.to/) y
  [uAssets](https://github.com/uBlockOrigin/uAssets): se conservan las cabeceras
  con autoría/licencia en cada lista de `share/babinium-browser/lists/`.
  EasyList permite GPL-3.0-o-posterior o CC BY-SA 3.0; uAssets usa GPL-3.0.
  Se elige la opción GPL para esta distribución. Sólo se resuelven directivas
  condicionales de plataforma para WebKit; no se atribuyen las listas al proyecto.
- [surf](https://surf.suckless.org/), MIT: referencia arquitectónica de interfaz
  mínima en C/WebKitGTK. No se ha copiado código de surf.

Los hashes de las listas descargadas están en `seed-provenance.json` y en
`filters/current/state.json` después de las actualizaciones. Los scriptlets son
código privilegiado de los recursos incluidos; sólo las listas uAssets de la
selección fija reciben el permiso uBO de scriptlets `trusted-*`. No se descarga
código de recursos nuevo durante la navegación. Al actualizar recursos deben
revisarse revisiones, dependencias y licencias y reconstruir el paquete.
