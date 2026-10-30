#!/bin/bash
set -euo pipefail
stage=build/package
mkdir -p "$stage/DEBIAN" "$stage/usr/bin" "$stage/usr/lib/babinium-browser" "$stage/usr/share/babinium-browser" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps" "$stage/usr/share/doc/babinium-browser" artifacts
cp build/bin/* "$stage/usr/bin/"
cp build/lib/babinium-browser/* "$stage/usr/lib/babinium-browser/"
cp -r build/share/babinium-browser/* "$stage/usr/share/babinium-browser/"
cp packaging/babinium-browser.desktop "$stage/usr/share/applications/"
cp packaging/babinium-browser.svg "$stage/usr/share/icons/hicolor/scalable/apps/"
cp LICENSE THIRD_PARTY.md README.md "$stage/usr/share/doc/babinium-browser/"
cp build/share/babinium-browser/THIRD_PARTY_NOTICES.txt "$stage/usr/share/doc/babinium-browser/"
cat > "$stage/DEBIAN/control" <<'EOF'
Package: babinium-browser
Version: 0.4.8
Architecture: amd64
Maintainer: babinium <miguel_babini@outlook.com>
Section: web
Priority: optional
Depends: libc6 (>= 2.41), libgtk-3-0t64 (>= 3.24), libwebkit2gtk-4.1-0 (>= 2.48), libjavascriptcoregtk-4.1-0, libjson-glib-1.0-0, libsoup-3.0-0, python3, ca-certificates, gstreamer1.0-plugins-good, gstreamer1.0-plugins-bad, gstreamer1.0-gl, gstreamer1.0-pulseaudio, gstreamer1.0-libav
Recommends: mpv, yt-dlp (>= 2026.10.21)
Homepage: https://github.com/babinium/babinium-browser
Description: Experimental minimal WebKitGTK browser with native adblock-rust
 C/GTK shell, tabs, downloads, native request blocking, cosmetic filtering,
 scriptlets and automatically updated lists. YouTube compatibility is experimental.
EOF
dpkg-deb --root-owner-group --build "$stage" artifacts/babinium-browser_0.4.8_amd64.deb
tar -czf artifacts/upstream-sources.tar.gz -C build/upstream ubo.tar.gz brave.tar.gz darkreader.tar.gz
