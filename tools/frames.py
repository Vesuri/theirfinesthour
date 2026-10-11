#!/usr/bin/env python3
"""Whole-trace summary for a Their Finest Hour trace: frame rate, blitter waits, interrupts, bus use.

  python3 tools/frames.py TRACE.bin CODE.bin BASE

Frames are counted at the game's swap requests, the `move.w #1,-7962(a4)` stores that follow
setting the buffer to show (-7964(a4)); the level-3 VERTB handler (bob:28d4c) then loads
that buffer's copper list into COP1LC and clears the request.  Sites: bob:12f38 (the
end of a frame in flight), bob:14d78, bob:28f9e (a show-buffer-and-wait helper).  Blitter
waits are the cycles on `btst #14,$dff002` / `bne.s` polls (DMACONR BBUSY).  Interrupts are
counted at the autovectors read from the trace's chip snapshot ($64..$78) and at the
level-3 handler's VERTB, BLIT and COPER branches.  DMA slot types come from the per-field
DMA records.
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from tfh_report import regions

SWAPS = (0x12f38, 0x14d78, 0x28f9e)
LEVEL3 = {0x28d4c: 'level-3 handler (bob:28d4c)', 0x28d66: '  vertical blank',
          0x28e0e: '  blitter-finished', 0x28e1c: '  copper'}
POLL = bytes.fromhex('0839000e00dff002')  # btst #14,$dff002
DMA = {0: 'free', 1: 'refresh', 2: 'CPU', 3: 'copper', 4: 'audio', 5: 'blitter', 6: 'bitplane',
       7: 'sprite', 8: 'disk'}


def main():
    trace, code, base = barto.load(sys.argv[1]), open(sys.argv[2], 'rb').read(), int(sys.argv[3], 0)
    regs = {name: (lo, hi, origin) for lo, hi, name, origin in regions(code, base, trace.chip)}
    hb = regs['bob'][0]

    def raw(a, n):
        o = a - base
        if 0 <= o and o + n <= len(code):
            return code[o:o + n]
        return trace.chip[a:a + n] if a + n <= len(trace.chip) else b''

    swap_pcs = {hb + o for o in SWAPS}
    watch = {hb + o: name for o, name in LEVEL3.items()}
    for level in range(1, 7):
        vec = struct.unpack_from('>I', trace.chip, 0x60 + 4 * level)[0]
        watch.setdefault(vec, f'level-{level} vector {vec:#x}')
    total = wait = 0
    swaps = []
    hits = collections.Counter()
    slots = collections.Counter()
    for f in trace.fields:
        n = 0
        for pc, cost, r in trace.instructions(f):
            total += cost
            if pc is None:
                continue
            if pc in swap_pcs:
                n += 1
            if pc in watch:
                hits[watch[pc]] += 1
            if raw(pc, 8) == POLL or (raw(pc, 2) == b'\x66\xf6' and raw(pc - 8, 8) == POLL):
                wait += cost
        swaps.append(n)
        for i in range(0, len(f.dma), f.dma_size):
            slots[f.dma[i + 29]] += 1

    if not total:
        sys.exit('No CPU instruction records in this trace; use fixed_window.sh with SWAP_ONLY=1.')
    nf = len(trace.fields)
    first = next((i for i, n in enumerate(swaps) if n), None)
    last = max((i for i, n in enumerate(swaps) if n), default=None)
    print(f'\n## Frames ({nf} fields)')
    print('buffer swaps per field:', ''.join(str(min(n, 9)) for n in swaps))
    if first is not None and last > first:
        frames = sum(swaps[first + 1:last + 1])
        per = (last - first) / frames
        print(f'{frames} frames in {last - first} fields: {per:.2f} fields/frame, {50 / per:.1f} fps (PAL)')
    print(f'blitter busy-wait polling: {100 * wait / total:.1f}% of CPU cycles')
    for k in list(LEVEL3.values()) + sorted(set(watch.values()) - set(LEVEL3.values())):
        print(f'{k}: {hits[k]} ({hits[k] / nf:.1f} per field)')
    n = sum(slots.values())
    print('DMA slots:', ', '.join(f'{DMA.get(k, k)} {100 * v / n:.1f}%' for k, v in sorted(slots.items())))


if __name__ == '__main__':
    main()
