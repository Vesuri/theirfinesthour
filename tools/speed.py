#!/usr/bin/env python3
"""Ground speed of the player's plane per wall-clock second, from state_fields.py snapshots.
  speed.py STATE_DIR [STATE_DIR...]
Snapshots are bob's data hunk at successive level-3 entries (VERTB, and blitter-finished
when the blitter runs); a4 is the hunk + $7FFE. Time is the game's VERTB count -8010(a4),
one per PAL field. Speed = horizontal distance between the first and last snapshot in
which the position changed, over the fields between them (x 50 for units per second). With a correct
time model it is the same on every machine for the same flight.
"""
import math, struct, sys
from pathlib import Path

A4 = 0x7ffe
def word(b, off): return struct.unpack_from('>h', b, A4+off)[0]
def long(b, off): return struct.unpack_from('>l', b, A4+off)[0]

for d in sys.argv[1:]:
    snaps = [p.read_bytes() for p in sorted(Path(d).glob('[0-9]*.bin'))]
    rows = [(long(b, 11668), long(b, 11672), long(b, 11676), word(b, 11698), word(b, 11700), word(b, -8010))
            for b in snaps]
    moves = [i for i in range(1, len(rows)) if rows[i][:2] != rows[i-1][:2]]
    if len(moves) < 2:
        print(f'{d}: position changed in {len(moves)} fields, no speed'); continue
    # Steps land on the field after a frame; measure between the first and last step.
    i, j = moves[0], moves[-1]
    dist = math.hypot(rows[j][0]-rows[i][0], rows[j][1]-rows[i][1])
    ts = sorted({r[3] for r in rows[i:j+1]})
    fields = (rows[j][5]-rows[i][5]) & 0xffff
    print(f'{d}: {len(moves)-1} steps in {fields} fields, {dist:.0f} units, '
          f'{50*dist/fields:.0f} units/s, T {ts[0]}..{ts[-1]}, altitude {rows[i][2]}..{rows[j][2]}')
