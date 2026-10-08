#!/usr/bin/env python3
"""Check the point transform (bob:2f4ae, or the slave's replacement) against a model of the original.
Run while tfh.py is stopped at the anchor; never writes game memory.
  xform_check.py CALLS CODE.bin BASE
For each of CALLS calls: stop at bob:2f4ae, read D0-D2 and the data hunk's camera and matrix,
run to the return and read the three results (4236, 4228, 4232(a4)) and the registers. The
model is the original routine: each coordinate minus the camera as sign and magnitude, each
term (magnitude * m) >> 16 from two 16x16 halves, negated by the sign rule; only D0-D2 change.
"""
import argparse, re, struct, tempfile
from pathlib import Path
from state_fields import command
from tfh_report import regions

M32 = 0xffffffff
CAM = (4154, 4158, 4162)
# result: [(axis, matrix magnitude, matrix sign, negate when the signs are equal)]
ROWS = {4236: [(0, 4122, 4138, False), (1, 4128, 4144, False), (2, 4120, 4136, False)],
        4228: [(0, 4114, 4130, False), (1, 4116, 4132, True)],
        4232: [(0, 4124, 4140, True), (1, 4126, 4142, True), (2, 4118, 4134, False)]}

def model(p, w16, l32):
    mag, sgn = [], []
    for v, c in zip(p, CAM):
        d = (v - l32(c)) & M32
        if d & 0x80000000: mag.append(-d & M32); sgn.append(0x8000)
        else: mag.append(d); sgn.append(0)
    out = {}
    for r, terms in ROWS.items():
        acc = 0
        for ax, m, s, eq in terms:
            mm = w16(m)
            t = (((mag[ax] & 0xffff) * mm >> 16) + (mag[ax] >> 16) * mm) & M32
            differ = (sgn[ax] ^ w16(s)) != 0
            if differ != eq: t = -t & M32
            acc = (acc + t) & M32
        out[r] = acc
    return out

def regs(text):
    return {m.group(1): int(m.group(2), 16) for m in re.finditer(r'^(\w+)\s+0x([0-9a-f]+)', text, re.M)}

def main():
    p = argparse.ArgumentParser(); p.add_argument('calls', type=int)
    p.add_argument('dump'); p.add_argument('base', type=lambda x: int(x, 0))
    a = p.parse_args()
    rr = {n: lo for lo, hi, n, o in regions(Path(a.dump).read_bytes(), a.base)}
    hb, db = rr['bob'], rr['bob-data']
    keep = ['d3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'sp']
    bad = negs = 0
    with tempfile.TemporaryDirectory(prefix='tfh-xform-') as t:
        command(f'break *{hb + 0x2f4ae:#x}')
        for n in range(a.calls):
            r0 = regs(command('continue\ninfo registers'))
            command(f'dump binary memory {t}/in.bin {db:#x} {db + 0xfa14:#x}\n'
                    f'dump binary memory {t}/ret.bin {r0["sp"]:#x} {r0["sp"] + 4:#x}')
            d = Path(f'{t}/in.bin').read_bytes()
            w16 = lambda o: struct.unpack_from('>H', d, o + 0x7ffe)[0]
            l32 = lambda o: struct.unpack_from('>I', d, o + 0x7ffe)[0]
            want = model([r0['d0'], r0['d1'], r0['d2']], w16, l32)
            ret = struct.unpack('>I', Path(f'{t}/ret.bin').read_bytes())[0]
            r1 = regs(command(f'tbreak *{ret:#x}\ncontinue\ninfo registers\n'
                              f'dump binary memory {t}/out.bin {db:#x} {db + 0xfa14:#x}'))
            o = Path(f'{t}/out.bin').read_bytes()
            got = {k: struct.unpack_from('>I', o, k + 0x7ffe)[0] for k in ROWS}
            moved = [k for k in keep if r0[k] != r1[k] - (4 if k == 'sp' else 0)]
            negs += any(w & 0x80000000 for w in want.values())
            if got != want or moved:
                bad += 1
                print(f'call {n}: in {r0["d0"]:#x},{r0["d1"]:#x},{r0["d2"]:#x} want '
                      f'{ {k: hex(v) for k, v in want.items()} } got { {k: hex(v) for k, v in got.items()} }'
                      f' registers changed {moved}')
        command('delete')
    print(f'{a.calls} calls ({negs} with a negative result): ' +
          ('transform matches the model' if not bad else f'{bad} differ from the model'))

if __name__ == '__main__': main()
