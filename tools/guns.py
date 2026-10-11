#!/usr/bin/env python3
"""The player's rate of fire, from state_fields.py snapshots (tape 8 holds the fire button).
  guns.py STATE_DIR [STATE_DIR...]
Snapshots are bob's data hunk at successive level-3 entries; a4 is the hunk + $7FFE. A shot is
a snapshot in which the first gun's ammunition 22946(a4)[plane*5] changed (plane 13318(a4));
time is the game's VERTB count -8010(a4). Prints each shot with T 11698(a4) and the reload
23106(a4)[plane*5] the shot set (frames), then the gaps between shots in fields. The reload is
T/3 frames, so the gaps are a third of a second only while T matches the frames that follow.
"""
import struct, sys
from pathlib import Path

def word(b, off): return struct.unpack_from('>H', b, off + 0x7ffe)[0]

def main():
    for d in map(Path, sys.argv[1:]):
        shots, last = [], None
        for f in sorted(d.glob('[0-9]*.bin')):
            b = f.read_bytes(); plane = word(b, 13318)
            ammo = word(b, 22946 + plane * 10)
            if last is not None and ammo != last:
                vbl = word(b, -8010); shots.append(vbl)
                print(f'{d}: field {vbl} T {word(b, 11698)} reload {b[23106 + plane * 5 + 0x7ffe]}'
                      f' ammunition {ammo}')
            last = ammo
        gaps = [b - a for a, b in zip(shots, shots[1:])]
        mean = f', mean {sum(gaps) / len(gaps):.1f}' if gaps else ''
        print(f'{d}: {len(shots)} shots, gaps {min(gaps, default=0)}..{max(gaps, default=0)} fields'
              f'{mean}: {gaps}')

if __name__ == '__main__':
    main()
