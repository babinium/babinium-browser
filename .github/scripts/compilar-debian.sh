#!/bin/bash
set -euo pipefail
make build/bin/babinium-browser
make -j2
make resources
make test
make package
mkdir -p artifacts/bundle
cp -r build/bin build/lib build/share artifacts/bundle/
cp blocker/Cargo.lock artifacts/Cargo.lock
{
  printf 'Debian 13 amd64; arquitectura genérica x86-64\n'
  printf 'Commit: %s\nRun: %s\nCFLAGS: %s\nRUSTFLAGS: %s\n' "$GITHUB_SHA" "$GITHUB_RUN_ID" "$CFLAGS" "$RUSTFLAGS"
  getconf GNU_LIBC_VERSION
  rustc --version
  pkg-config --modversion webkit2gtk-4.1
  file build/bin/babinium-browser build/lib/babinium-browser/libbabinium-adblock.so
  ldd build/bin/babinium-browser
  ldd build/lib/babinium-browser/libbabinium-adblock.so
} > artifacts/entorno.txt
readelf --version-info build/bin/babinium-browser > artifacts/glibc.txt
readelf --version-info build/lib/babinium-browser/libbabinium-adblock.so >> artifacts/glibc.txt
