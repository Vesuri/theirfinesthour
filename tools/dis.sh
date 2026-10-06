#!/usr/bin/env bash
# dis.sh DUMP BASE START END  -- disassemble [START,END) of a memory dump taken at BASE
. "$(dirname "$0")/../amiga/env.sh"
m68k-amiga-elf-objdump -D -b binary -m m68k:68000 --adjust-vma="$2" --start-address="$3" --stop-address="$4" "$1" | sed -n '/>:$/,$p' | tail -n +2
