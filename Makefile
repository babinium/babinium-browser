PREFIX ?= /usr
CFLAGS ?= -O2 -march=x86-64 -mtune=generic
CFLAGS += -std=c11 -D_DEFAULT_SOURCE -Wall -Wextra -Wno-deprecated-declarations -ffunction-sections -fdata-sections
UI_PKGS = webkit2gtk-4.1 gtk+-3.0 json-glib-1.0
EXT_PKGS = webkit2gtk-web-extension-4.1 json-glib-1.0
RUSTLIB = blocker/target/release/libbabinium_blocker.a

.PHONY: all resources test package clean
all: build/bin/babinium-browser build/lib/babinium-browser/libbabinium-adblock.so build/bin/babinium-filter build/bin/babinium-filter-update

$(RUSTLIB): blocker/src/lib.rs blocker/src/main.rs blocker/Cargo.toml
	cd blocker && cargo build --release

build/bin/babinium-filter: $(RUSTLIB)
	mkdir -p $(@D)
	cp blocker/target/release/babinium-filter $@

build/bin/babinium-browser: src/browser.c
	mkdir -p $(@D)
	$(CC) $(CFLAGS) $< -o $@ $$(pkg-config --cflags --libs $(UI_PKGS)) -Wl,--gc-sections

build/lib/babinium-browser/libbabinium-adblock.so: src/extension.c src/blocker.h $(RUSTLIB)
	mkdir -p $(@D)
	$(CC) $(CFLAGS) -fPIC -shared src/extension.c $(RUSTLIB) -o $@ $$(pkg-config --cflags --libs $(EXT_PKGS)) -Wl,--gc-sections -ldl -lpthread -lm

build/bin/babinium-filter-update: scripts/filter-update.py
	mkdir -p $(@D)
	install -m755 $< $@

resources: all
	python3 scripts/prepare-resources.py
	cp data/cosmetic.js data/sources.json data/upstream.json build/share/babinium-browser/

test: all
	cd blocker && cargo test --release
	python3 -m unittest discover -s tests -p 'test_*.py' -v

package:
	bash packaging/package.sh

clean:
	rm -rf build
