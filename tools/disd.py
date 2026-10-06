#!/usr/bin/env python3
"""disd.py DUMP BASE HUNKBASE START END: disassemble bob code by hunk offset."""
import subprocess, sys, os
dump, base, hb, s, e = sys.argv[1], *[int(x, 0) for x in sys.argv[2:]]
out = subprocess.run([os.path.expanduser('~/.local/opt/bin/m68k-amiga-elf-objdump'), '-D', '-b', 'binary', '-m', 'm68k:68000',
                      f'--adjust-vma={base:#x}', f'--start-address={hb + s:#x}', f'--stop-address={hb + e:#x}', dump],
                     capture_output=True, text=True).stdout.split('\n')
for l in out:
    if ':\t' in l and l.strip()[0] in '0123456789abcdef':
        a, rest = l.split(':', 1)
        parts = rest.split('\t')
        print(f'{int(a, 16) - hb:05x}  {parts[1]:<22} {" ".join(parts[2:])}')
