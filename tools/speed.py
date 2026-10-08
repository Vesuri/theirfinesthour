#!/usr/bin/env python3
"""Ground speed of the player's plane per wall-clock second, from state_fields.py snapshots.
  speed.py [--window FIELDS] [--hz 50|60] STATE_DIR [STATE_DIR...]
Snapshots are bob's data hunk at successive level-3 entries (VERTB, and blitter-finished
when the blitter runs); a4 is the hunk + $7FFE. Time is the game's VERTB count -8010(a4),
one per field (--hz: 50 PAL, the default, or 60 NTSC). Speed = horizontal distance between the
first and last snapshot in which the position changed, over the fields between them (x hz for
units per second). With a correct time model it is the same on every machine for the same flight.
--window: also print the speed per window of that many fields, with the step divisor
11700(a4) seen in it (T, or less while the T key accelerates time).
"""
import argparse, math, struct
from pathlib import Path

A4 = 0x7ffe
def word(b, off): return struct.unpack_from('>h', b, A4+off)[0]
def long(b, off): return struct.unpack_from('>l', b, A4+off)[0]

def speed(rows, i, j):
    dist = math.hypot(rows[j][0]-rows[i][0], rows[j][1]-rows[i][1])
    fields = (rows[j][5]-rows[i][5]) & 0xffff
    return dist, fields

p = argparse.ArgumentParser(); p.add_argument('--window', type=int, default=0); p.add_argument('--hz', type=int, default=50); p.add_argument('dirs', nargs='+')
a = p.parse_args()
for d in a.dirs:
    snaps = [p.read_bytes() for p in sorted(Path(d).glob('[0-9]*.bin'))]
    rows = [(long(b, 11668), long(b, 11672), long(b, 11676), word(b, 11698), word(b, 11700), word(b, -8010))
            for b in snaps]
    moves = [i for i in range(1, len(rows)) if rows[i][:2] != rows[i-1][:2]]
    if len(moves) < 2:
        print(f'{d}: position changed in {len(moves)} fields, no speed'); continue
    # Steps land on the field after a frame; measure between the first and last step.
    i, j = moves[0], moves[-1]
    dist, fields = speed(rows, i, j)
    ts = sorted({r[3] for r in rows[i:j+1]})
    print(f'{d}: {len(moves)-1} steps in {fields} fields, {dist:.0f} units, '
          f'{a.hz*dist/fields:.0f} units/s, T {ts[0]}..{ts[-1]}, altitude {rows[i][2]}..{rows[j][2]}')
    if a.window:
        start = i
        while start < j:
            ends = [m for m in moves if m > start and (rows[m][5]-rows[start][5]) & 0xffff <= a.window]
            if not ends: break
            end = ends[-1]
            dist, fields = speed(rows, start, end)
            div = sorted({r[4] for r in rows[start:end+1]})
            print(f'  fields {rows[start][5]}..{rows[end][5]}: {a.hz*dist/fields:6.0f} units/s, '
                  f'step divisor {div[0]}..{div[-1]}')
            start = end
