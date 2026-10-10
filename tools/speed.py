#!/usr/bin/env python3
"""Ground speed of the player's plane per wall-clock second, from state_fields.py snapshots.
  speed.py [--window FIELDS] [--hz 50|60] STATE_DIR [STATE_DIR...]
Snapshots are bob's data hunk at successive level-3 entries (VERTB, and blitter-finished
when the blitter runs); a4 is the hunk + $7FFE. Time is the game's VERTB count -8010(a4),
one per field (--hz: 50 PAL, the default, or 60 NTSC). Speed = horizontal distance between the
first and last snapshot in which the position changed, over the fields between them (x hz for
units per second). With a correct time model it is the same on every machine for the same flight,
and equal to the nominal speed: the speed word 19694(a4) of the viewed object 30718(a4) times
4660/256 units per second (the step bob:154dc divides by T), averaged over the snapshots.
--window: also print the speed per window of that many fields, with the step divisor
11700(a4) seen in it (T, or less while the T key accelerates time).
--turn: also print the heading rate (degrees per second, from the heading word 11680(a4),
65536 = 360) per window, with the player's roll 19198(a4) (plane 0) at its end.
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

p = argparse.ArgumentParser(); p.add_argument('--window', type=int, default=0); p.add_argument('--hz', type=int, default=50); p.add_argument('--turn', action='store_true'); p.add_argument('dirs', nargs='+')
a = p.parse_args()
for d in a.dirs:
    snaps = [p.read_bytes() for p in sorted(Path(d).glob('[0-9]*.bin'))]
    rows = [(long(b, 11668), long(b, 11672), long(b, 11676), word(b, 11698), word(b, 11700), word(b, -8010),
             word(b, 11680) & 0xffff, word(b, 19198))
            for b in snaps]
    view = [struct.unpack_from('>H', b, A4+30718)[0] for b in snaps]
    nominal = sum(struct.unpack_from('>H', b, A4+19694+2*v)[0] for b, v in zip(snaps, view)) / len(snaps) * 4660 / 256
    moves = [i for i in range(1, len(rows)) if rows[i][:2] != rows[i-1][:2]]
    if len(moves) < 2:
        print(f'{d}: position changed in {len(moves)} fields, no speed'); continue
    # Steps land on the field after a frame; measure between the first and last step.
    i, j = moves[0], moves[-1]
    dist, fields = speed(rows, i, j)
    ts = sorted({r[3] for r in rows[i:j+1]})
    print(f'{d}: {len(moves)-1} steps in {fields} fields, {dist:.0f} units, '
          f'{a.hz*dist/fields:.0f} units/s (nominal {nominal:.0f}), T {ts[0]}..{ts[-1]}, altitude {rows[i][2]}..{rows[j][2]}')
    if a.window:
        start = i
        while start < j:
            ends = [m for m in moves if m > start and (rows[m][5]-rows[start][5]) & 0xffff <= a.window]
            if not ends: break
            end = ends[-1]
            dist, fields = speed(rows, start, end)
            div = sorted({r[4] for r in rows[start:end+1]})
            turn = ''
            if a.turn:
                dh = (rows[end][6] - rows[start][6] + 0x8000) % 0x10000 - 0x8000
                turn = f', heading {a.hz*dh*360/65536/fields:+6.2f} deg/s, roll {rows[end][7]*360/65536:+6.1f} deg'
            print(f'  fields {rows[start][5]}..{rows[end][5]}: {a.hz*dist/fields:6.0f} units/s, '
                  f'step divisor {div[0]}..{div[-1]}{turn}')
            start = end
