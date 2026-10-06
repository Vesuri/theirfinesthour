#!/usr/bin/env python3
"""Count buffer swaps (the game's swap requests) over PAL fields with read-only debugger breakpoints.
Used by fixed_window.sh when a CPU backend provides no instruction trace.
Only debugger convenience variables change; target memory/registers are read-only.
"""
import argparse
from pathlib import Path
import re
from state_fields import command
from tfh_report import regions
from frames import SWAPS

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('fields', type=int)
p.add_argument('out', type=Path)
p.add_argument('dump', type=Path)
p.add_argument('base', type=lambda x: int(x, 0))
a = p.parse_args()
assert a.fields > 1
code = a.dump.read_bytes()
r = {name: (lo, hi) for lo, hi, name, origin in regions(code, a.base)}
# Breakpoints on the level-3 interrupt entry and the game's swap requests (frames.SWAPS).
hb = r['bob'][0]
vbl = hb+0x28d4c
swaps_bp = ''.join(f'break *{hb+o:#x}\n' for o in SWAPS)
reply = command(f'''break *{vbl:#x}
{swaps_bp}set $tfh_field = -1
while $tfh_field < {a.fields}
continue
if $pc == {vbl:#x}
set $tfh_field = $tfh_field + 1
else
printf "TFHSWAP %d\\n", $tfh_field
end
end
delete
''')
(a.out/'swaps-gdb.txt').write_text(reply)
swaps = [0]*a.fields
for field in re.findall(r'^TFHSWAP (-?\d+)$', reply, re.M):
    index = int(field)
    if 0 <= index < a.fields:
        swaps[index] += 1
assert 'ERROR' not in reply
first = next((i for i, n in enumerate(swaps) if n), None)
last = max((i for i, n in enumerate(swaps) if n), default=None)
assert first is not None and last > first, 'insufficient swaps for FPS'
frames = sum(swaps[first+1:last+1])
report = (f'Read-only swap counter ({a.fields} PAL fields)\n'
          f'buffer swaps per field: {"".join(str(n) for n in swaps)}\n'
          f'{frames} frames in {last-first} fields: {(last-first)/frames:.2f} fields/frame, '
          f'{50*frames/(last-first):.1f} fps (PAL)\n')
(a.out/'frames.txt').write_text(report)
print(report, end='')
