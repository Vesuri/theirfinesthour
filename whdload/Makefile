# Host cross-build of the reconstructed Their Finest Hour slave (Psygore's 1.1 ships without
# source; TheirFinestHour.s is rebuilt from its disassembly).  Not byte-identical to the
# shipped slave: kick13.s is the WHDLoad 20.0 one (see README.md).
# The shared environment (as amiga/env.sh): WHDLoad 20.0's API headers and KickEmu sources,
# the NDK and vasm.  Override from the environment or make arguments.
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad-20.0
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
VASM ?= $(HOME)/.local/vasmm68k_mot
VASMFLAGS ?=

.PHONY: all verify clean FORCE
all: TheirFinestHour.slave

# Always assemble: options must not leave a stale variant.
TheirFinestHour.slave: TheirFinestHour.s $(wildcard include/lvo/*.i) FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I"$(WHDLOAD)/Include" -I"$(WHDLOAD)/Src/sources" -I"$(NDK)" -o $@ $<

verify:
	$(MAKE) TheirFinestHour.slave VASMFLAGS="$(VASMFLAGS) -DVERIFY=1 -L TheirFinestHour.lst"

clean:
	rm -f TheirFinestHour.slave
