#!/usr/bin/env python3
"""hotspots.py TRACE DUMP BASE HUNKBASE OFF[,OFF...] [SPAN]: hottest instructions of bob
routines (hunk offsets), with disassembly, as % of all traced cycles."""
import collections, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import barto
trace, dump, base, hb = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), int(sys.argv[4], 0)
offs = [int(x, 16) for x in sys.argv[5].split(',')]
span = int(sys.argv[6], 0) if len(sys.argv) > 6 else 0x400
t = barto.load(trace)
pcs = collections.Counter(); tot = 0
for f in t.fields:
    for pc, c, r in t.instructions(f):
        tot += c
        if pc is not None: pcs[pc - hb] += c
dis = {}
od = os.path.join(os.environ.get('AMIGA_TOOLCHAIN') or os.path.expanduser('~/.local/opt'), 'bin', 'm68k-amiga-elf-objdump')
for o in offs:
    out = subprocess.run([od, '-D', '-b', 'binary', '-m', 'm68k:68000', f'--adjust-vma={base:#x}',
                          f'--start-address={hb + o:#x}', f'--stop-address={hb + o + span:#x}', dump],
                         capture_output=True, text=True).stdout
    for l in out.split('\n'):
        if ':\t' in l and l.strip()[0] in '0123456789abcdef':
            a, rest = l.split(':', 1)
            dis[int(a, 16) - hb] = ' '.join(rest.split('\t')[2:])
    tot_fn = sum(c for p, c in pcs.items() if o <= p < o + span)
    print(f'\n== bob:{o:05x} (+{span:#x}): {100 * tot_fn / tot:.2f}%')
    for p, c in sorted(((p, c) for p, c in pcs.items() if o <= p < o + span), key=lambda x: -x[1])[:14]:
        print(f'  {100 * c / tot:5.2f}  {p:05x}  {dis.get(p, "?")}')
