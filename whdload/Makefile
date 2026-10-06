# Host cross-build of the reconstructed Their Finest Hour slave (Psygore's 1.1 ships without
# source; TheirFinestHour.s is rebuilt from its disassembly).  Not byte-identical to the
# shipped slave: kick13.s is the vendored WHDLoad 20.0 one (see whdload/README.md).
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
VASM ?= $(HOME)/.local/vasmm68k_mot
VASMFLAGS ?=

.PHONY: all verify clean FORCE
all: TheirFinestHour.slave

# Always assemble: options must not leave a stale variant.
TheirFinestHour.slave: TheirFinestHour.s $(wildcard whdload/* include/*.i include/lvo/*.i) FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I"$(WHDLOAD)/Include" -I"$(NDK)" -o $@ $<

verify:
	$(MAKE) TheirFinestHour.slave VASMFLAGS="$(VASMFLAGS) -DVERIFY=1"

clean:
	rm -f TheirFinestHour.slave
