#!/usr/bin/env python3
"""Check the C2P (bob:283a0, or the slave's replacement) against a model of the original.
Run while tfh.py is stopped at the anchor; never writes game memory.
  c2p_check.py CALLS OUTDIR CODE.bin BASE
For each of CALLS frames: stop at bob:283a6 (the C2P body, after its prologue), dump its
inputs (new and previous chunky frame, window mask, the four planes), run to its return and
dump the planes again. The model is the original routine: each longword of the new frame
that differs from the old one is converted (pixel i of the longword in bits 31-4i..28-4i,
plane 0 the lowest) into a byte of each plane, merged through the mask byte.
"""
import argparse, os, re, struct, tempfile
from pathlib import Path
from state_fields import command
from tfh_report import regions

PLANE, ROW = 8000, 40

def model(new, old, mask, planes, w, rows, off):
    out = bytearray(planes)
    for r in range(rows):
        for j in range(w):
            i = (r * w + j) * 4
            if new[i:i+4] == old[i:i+4]: continue
            v = struct.unpack_from('>I', new, i)[0]
            m = mask[r * w + j]
            for k in range(4):
                b = 0
                for p in range(8): b = (b << 1) | (v >> (28 - 4 * p + k)) & 1
                a = k * PLANE + off + r * ROW + j
                out[a] = (out[a] & ~m & 0xff) | (b & m)
    return bytes(out)

def reg(text, name):
    return int(re.search(rf'^{name}\s+0x([0-9a-f]+)', text, re.M).group(1), 16)

def main():
    p = argparse.ArgumentParser(); p.add_argument('calls', type=int)
    p.add_argument('out'); p.add_argument('dump'); p.add_argument('base', type=lambda x: int(x, 0))
    a = p.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rr = {n: lo for lo, hi, n, o in regions(Path(a.dump).read_bytes(), a.base)}
    hb, db = rr['bob'], rr['bob-data']; a4 = db + 0x7ffe
    w16 = lambda d, o: struct.unpack_from('>h', d, o + 0x7ffe)[0]
    l32 = lambda d, o: struct.unpack_from('>I', d, o + 0x7ffe)[0]
    bad = 0
    # under tmp/, by a relative path: gdb runs in the repo root and its dump takes no spaces
    with tempfile.TemporaryDirectory(prefix='tfh-c2p-', dir='tmp') as t:
        t = os.path.relpath(t)
        command(f'break *{hb + 0x283a6:#x}')
        for n in range(a.calls):
            regs = command('continue\ninfo registers')
            a5 = reg(regs, 'a5'); sp = reg(regs, 'sp')
            command(f'dump binary memory {t}/data.bin {db:#x} {db + 0xfa14:#x}\n'
                    f'dump binary memory {t}/args.bin {a5:#x} {a5 + 12:#x}\n'
                    f'dump binary memory {t}/ret.bin {sp:#x} {sp + 4:#x}')
            d = Path(f'{t}/data.bin').read_bytes()
            newp, oldp = struct.unpack_from('>II', Path(f'{t}/args.bin').read_bytes(), 4)
            ret = struct.unpack('>I', Path(f'{t}/ret.bin').read_bytes())[0]
            w, rows, off = w16(d, -7796), w16(d, -7792), w16(d, -7808)
            p0, maskp = l32(d, 25530), l32(d, -9778)
            assert [l32(d, 25530 + 4 * k) - p0 for k in range(4)] == [0, PLANE, 2 * PLANE, 3 * PLANE]
            size = w * rows * 4
            command(f'dump binary memory {t}/new.bin {newp:#x} {newp + size:#x}\n'
                    f'dump binary memory {t}/old.bin {oldp:#x} {oldp + size:#x}\n'
                    f'dump binary memory {t}/mask.bin {maskp:#x} {maskp + w * rows:#x}\n'
                    f'dump binary memory {t}/before.bin {p0:#x} {p0 + 4 * PLANE:#x}\n'
                    f'tbreak *{ret:#x}\ncontinue\n'
                    f'dump binary memory {t}/after.bin {p0:#x} {p0 + 4 * PLANE:#x}')
            new, old, mask, before, after = (Path(f'{t}/{x}.bin').read_bytes() for x in ('new', 'old', 'mask', 'before', 'after'))
            want = model(new, old, mask, before, w, rows, off)
            changed = sum(new[i:i+4] != old[i:i+4] for i in range(0, size, 4))
            diff = sum(x != y for x, y in zip(want, after))
            bad += diff != 0
            print(f'call {n}: {w}x{rows} longwords at plane offset {off}, {changed} changed, '
                  f'{sum(x != y for x, y in zip(before, after))} plane bytes written, {diff} differ from the model')
            if n == 0:
                for x in ('new', 'old', 'mask', 'before', 'after'):
                    os.replace(f'{t}/{x}.bin', out / f'{x}.bin')
        command('delete')
    print('C2P matches the model' if not bad else f'C2P differs from the model in {bad} of {a.calls} calls')

if __name__ == '__main__': main()
