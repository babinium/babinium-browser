PREFIX ?= /usr
CFLAGS ?= -O2
CFLAGS += -std=c11 -D_DEFAULT_SOURCE -Wall -Wextra -Wno-deprecated-declarations -ffunction-sections -fdata-sections
UI_PKGS = webkit2gtk-4.1 gtk+-3.0 json-glib-1.0 libsoup-3.0
EXT_PKGS = webkit2gtk-web-extension-4.1 json-glib-1.0
RUSTLIB = blocker/target/release/libbabinium_blocker.a

.PHONY: all resources test package clean
all: build/bin/babinium-browser build/lib/babinium-browser/libbabinium-adblock.so build/bin/babinium-filter build/bin/babinium-filter-update

$(RUSTLIB): blocker/src/lib.rs blocker/src/main.rs blocker/Cargo.toml
	cd blocker && cargo build --release --locked

build/bin/babinium-filter: $(RUSTLIB)
	mkdir -p $(@D)
	cp blocker/target/release/babinium-filter $@

build/bin/babinium-browser: src/browser.c src/site-name.c src/site-name.h src/youtube-url.c src/youtube-url.h
	mkdir -p $(@D)
	$(CC) $(CFLAGS) src/browser.c src/site-name.c src/youtube-url.c -o $@ $$(pkg-config --cflags --libs $(UI_PKGS)) -Wl,--gc-sections

build/lib/babinium-browser/libbabinium-adblock.so: src/extension.c src/blocker.h $(RUSTLIB)
	mkdir -p $(@D)
	$(CC) $(CFLAGS) -fPIC -shared src/extension.c $(RUSTLIB) -o $@ $$(pkg-config --cflags --libs $(EXT_PKGS)) -Wl,--gc-sections -ldl -lpthread -lm

build/bin/babinium-filter-update: scripts/filter-update.py
	mkdir -p $(@D)
	install -m755 $< $@

resources: all
	python3 scripts/prepare-resources.py
	python3 scripts/license-notices.py
	cp data/cosmetic.js data/youtube.js data/youtube-ambient.js data/video-speed.js data/video-speed-youtube.js data/sources.json data/upstream.json build/share/babinium-browser/

build/tests/test-site-name: tests/test-site-name.c src/site-name.c src/site-name.h
	mkdir -p $(@D)
	$(CC) $(CFLAGS) tests/test-site-name.c src/site-name.c -o $@ $$(pkg-config --cflags --libs gio-2.0 libsoup-3.0)

build/tests/test-youtube-url: tests/test-youtube-url.c src/youtube-url.c src/youtube-url.h
	mkdir -p $(@D)
	$(CC) $(CFLAGS) tests/test-youtube-url.c src/youtube-url.c -o $@ $$(pkg-config --cflags --libs glib-2.0)

test: all build/tests/test-site-name build/tests/test-youtube-url
	build/tests/test-site-name
	build/tests/test-youtube-url
	cd blocker && cargo test --release --locked
	python3 -m unittest discover -s tests -p 'test_*.py' -v
	node --test tests/test-youtube.js tests/test-ambient.js tests/test-video-speed.js tests/test-video-speed-youtube.js

package:
	bash packaging/package.sh

clean:
	rm -rf build
