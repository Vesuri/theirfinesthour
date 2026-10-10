#!/usr/bin/env python3
"""Check the point transform and projection (or the slave's replacements) against models of the
original routines. Run while tfh.py is stopped at the anchor; never writes game memory.
  xform_check.py [--routine xform|proj|div|clear|tile] CALLS CODE.bin BASE
For each of CALLS calls: stop at the routine, read its register and data-hunk inputs, run to
the return and compare its results with the model.
  xform  bob:2f4ae: 4236, 4228, 4232(a4); registers other than D0-D2 unchanged. Each
         coordinate minus the camera as sign and magnitude, each term (magnitude * m) >> 16
         from two 16x16 halves, negated by the sign rule.
  proj   bob:2f28a (bob:2f160's 32-bit path): 4268, 4272(a4) and D0. Terms
         (magnitude * m + $8000) >> 16 from two halves.
  div    bob:2f374: D0 and D2. |D0.w| / 4244(a4) as a 32-bit quotient from two divu.w,
         times 4264(a4), rounded >> 16, negated with D0.w.
  clear  bob:1148e, after bob:1142c's clear loop: -498..-459(a5) and -298..-279(a5) zero,
         the counter -24(a5) = 20.
  tile   bob:11138 (map scenery): every call it makes to bob:1133a, in order, with its
         argument and 26360, 26364, 26372(a4) (long) and 26376, 26377(a4) (byte), against a
         model of the original from the data hunk, the map at 12132(a4), the ring offsets
         at 12136(a4) and the scenery records at 12140(a4).
"""
import argparse, os, re, struct, tempfile
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

def t16(mag, m):
    """the original's rounded product: low half rounded, plus the high half"""
    return ((((mag & 0xffff) * m + 0x8000) & M32) >> 16) + (mag >> 16) * m & M32

def model_proj(w16, l32):
    X, Y, sx, sy = l32(4282), l32(4286), w16(4316), w16(4318)
    sneg = lambda t, a, b, neg_if_set: (-t & M32) if bool((a ^ b) & 0x8000) == neg_if_set else t
    r1 = (sneg(t16(X, w16(4148)), sx, w16(4152), True) +
          sneg(t16(Y, w16(4146)), sy, w16(4150), False) + w16(-7802)) & M32
    r = (sneg(t16(X, w16(4146)), sx, w16(4150), True) +
         sneg(t16(Y, w16(4148)), sy, w16(4152), True)) & M32
    t = t16(r if r < 0x80000000 else -r & M32, 0xe8ba)
    if r & 0x80000000: t = -t & M32
    r2 = (t - l32(4312) + w16(-7788)) & M32
    return {4268: r1, 4272: r2}, X & 0xffff0000

def model_div(d0, w16):
    a = d0 & 0xffff
    mag = (-a & 0xffff) if a & 0x8000 else a
    z, m = w16(4244), w16(4264)
    if z == 0: qh, ql = mag, 0
    else: qh, ql = mag // z, ((mag % z) << 16) // z
    res = (qh * m + ((ql * m + 0x8000) >> 16)) & M32
    return (-res & M32) if a & 0x8000 else res, res

def regs(text):
    return {m.group(1): int(m.group(2), 16) for m in re.finditer(r'^(\w+)\s+0x([0-9a-f]+)', text, re.M)}

def main():
    p = argparse.ArgumentParser(); p.add_argument('--routine', default='xform', choices=['xform', 'proj', 'div', 'clear', 'tile'])
    p.add_argument('calls', type=int)
    p.add_argument('dump'); p.add_argument('base', type=lambda x: int(x, 0))
    a = p.parse_args()
    rr = {n: lo for lo, hi, n, o in regions(Path(a.dump).read_bytes(), a.base)}
    hb, db = rr['bob'], rr['bob-data']
    keep = ['d3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'sp']
    bad = negs = 0
    if a.routine == 'clear': return check_clear(a.calls, hb)
    if a.routine == 'tile': return check_tile(a.calls, hb, db)
    # under tmp/, by a relative path: gdb runs in the repo root and its dump takes no spaces
    with tempfile.TemporaryDirectory(prefix='tfh-xform-', dir='tmp') as t:
        t = os.path.relpath(t)
        entry = {'xform': 0x2f4ae, 'proj': 0x2f28a, 'div': 0x2f374}[a.routine]
        command(f'break *{hb + entry:#x}')
        for n in range(a.calls):
            r0 = regs(command('continue\ninfo registers'))
            command(f'dump binary memory {t}/in.bin {db:#x} {db + 0xfa14:#x}\n'
                    f'dump binary memory {t}/ret.bin {r0["sp"]:#x} {r0["sp"] + 4:#x}')
            d = Path(f'{t}/in.bin').read_bytes()
            w16 = lambda o: struct.unpack_from('>H', d, o + 0x7ffe)[0]
            l32 = lambda o: struct.unpack_from('>I', d, o + 0x7ffe)[0]
            if a.routine == 'xform': want = model([r0['d0'], r0['d1'], r0['d2']], w16, l32)
            elif a.routine == 'proj': want, want_d0 = model_proj(w16, l32)
            else: want_d0, want_d2 = model_div(r0['d0'], w16); want = {}
            ret = struct.unpack('>I', Path(f'{t}/ret.bin').read_bytes())[0]
            r1 = regs(command(f'tbreak *{ret:#x}\ncontinue\ninfo registers\n'
                              f'dump binary memory {t}/out.bin {db:#x} {db + 0xfa14:#x}'))
            o = Path(f'{t}/out.bin').read_bytes()
            got = {k: struct.unpack_from('>I', o, k + 0x7ffe)[0] for k in want}
            if a.routine == 'xform':
                moved = [k for k in keep if r0[k] != r1[k] - (4 if k == 'sp' else 0)]
            else:
                moved = [] if r1['d0'] == want_d0 else [f'd0 {r1["d0"]:#x} want {want_d0:#x}']
                if a.routine == 'div' and r1['d2'] != want_d2: moved.append(f'd2 {r1["d2"]:#x} want {want_d2:#x}')
            negs += any(w & 0x80000000 for w in want.values()) or (a.routine == 'div' and bool(want_d0 & 0x80000000))
            if got != want or moved:
                bad += 1
                print(f'call {n}: in {r0["d0"]:#x},{r0["d1"]:#x},{r0["d2"]:#x} want '
                      f'{ {k: hex(v) for k, v in want.items()} } got { {k: hex(v) for k, v in got.items()} }'
                      f' registers changed {moved}')
        command('delete')
    print(f'{a.calls} calls ({negs} with a negative result): ' +
          (f'{a.routine} matches the model' if not bad else f'{bad} differ from the model'))

def check_clear(calls, hb):
    bad = 0
    with tempfile.TemporaryDirectory(prefix='tfh-clear-', dir='tmp') as t:
        t = os.path.relpath(t)
        command(f'break *{hb + 0x1148e:#x}')
        for n in range(calls):
            a5 = regs(command('continue\ninfo registers'))['a5']
            command(f'dump binary memory {t}/f.bin {a5 - 498:#x} {a5:#x}')
            f = Path(f'{t}/f.bin').read_bytes()
            at = lambda off, k: f[498 + off:498 + off + k]
            ok = at(-498, 40) == bytes(40) and at(-298, 20) == bytes(20) and at(-24, 2) == b'\0\x14'
            if not ok: bad += 1; print(f'call {n}: frame at {a5:#x} not as the loop leaves it')
        command('delete')
    print(f'{calls} calls: ' + ('clear matches the model' if not bad else f'{bad} differ from the model'))

def model_tile(d, mem):
    """bob:11138 as compiled: the bob:1133a calls as (argument, 26360, 26364, 26372, 26376, 26377)"""
    w16 = lambda o: struct.unpack_from('>H', d, o + 0x7ffe)[0]
    l32 = lambda o: struct.unpack_from('>I', d, o + 0x7ffe)[0]
    b8 = lambda o: d[o + 0x7ffe]
    sb = lambda v: v - 256 if v & 0x80 else v
    def pos(o, k):
        v = l32(o); v = v - (1 << 32) if v & 0x80000000 else v
        return (((v >> 16) - k) >> 2) & 0xffff
    x0, y0 = pos(11668, 96), pos(11672, 64)
    calls = []
    for ring in range(11):
        step = w16(-21692 + 2 * ring)
        q = ((step >> 1) + w16(11680)) & 0xffff
        q = q // step if q // step < 0x10000 else None
        c = (q - sb(b8(-21704 + ring))) & 0xff
        length = b8(-21726 + ring)
        if c >= 128: c = (c + length) & 0xff
        limit = sb(length) & 0xffff
        n = b8(-21715 + ring)
        detail = 0 if ring == 0 else ((ring - 1) * 4 + 1) & 0xff
        offs = (w16(-21670 + 2 * ring) + l32(12136)) & M32
        while n:
            n -= 1
            if c >= limit: c = 0
            x = (sb(mem(offs + 2 * c, 1)[0]) + x0) & 0xffff
            y = (sb(mem(offs + 2 * c + 1, 1)[0]) + y0) & 0xffff
            if x < 64 and y < 64:
                v = mem(l32(12132) + (y << 5) + (x >> 1), 1)[0]
                v = v & 15 if x & 1 else v >> 4
                if v:
                    rec = (w16(-23016 + 2 * v) + l32(12140)) & M32
                    if detail < mem(rec + 1, 1)[0]:
                        calls.append((detail << 16, ((x * 4 + 98) & 0xffff) << 16,
                                      ((y * 4 + 66) & 0xffff) << 16, rec, v, 0))
            c = (c + 1) & 0xff
    return calls

def check_tile(calls, hb, db):
    bad = total = 0
    cache = {}
    with tempfile.TemporaryDirectory(prefix='tfh-tile-', dir='tmp') as t:
        t = os.path.relpath(t)
        def mem(addr, k):
            page = addr & ~0xfff
            if page not in cache:
                command(f'dump binary memory {t}/m.bin {page:#x} {page + 0x2000:#x}')
                cache[page] = Path(f'{t}/m.bin').read_bytes()
            return cache[page][addr - page:addr - page + k]
        command(f'break *{hb + 0x11138:#x}')
        for n in range(calls):
            r0 = regs(command('continue\ninfo registers'))
            command(f'dump binary memory {t}/in.bin {db:#x} {db + 0xfa14:#x}\n'
                    f'dump binary memory {t}/ret.bin {r0["sp"]:#x} {r0["sp"] + 4:#x}')
            d = Path(f'{t}/in.bin').read_bytes()
            cache.clear()
            want = model_tile(d, mem)
            ret = struct.unpack('>I', Path(f'{t}/ret.bin').read_bytes())[0]
            command(f'break *{hb + 0x1133a:#x}\ntbreak *{ret:#x}')
            got = []
            while True:
                r = regs(command('continue\ninfo registers'))
                if r['pc'] == ret: break
                command(f'dump binary memory {t}/g.bin {db + 0x7ffe + 26360:#x} {db + 0x7ffe + 26378:#x}\n'
                        f'dump binary memory {t}/a.bin {r["sp"] + 4:#x} {r["sp"] + 8:#x}')
                g = Path(f'{t}/g.bin').read_bytes()
                arg = struct.unpack('>I', Path(f'{t}/a.bin').read_bytes())[0]
                got.append((arg, struct.unpack_from('>I', g, 0)[0], struct.unpack_from('>I', g, 4)[0],
                            struct.unpack_from('>I', g, 12)[0], g[16], g[17]))
            command(f'delete\nbreak *{hb + 0x11138:#x}')
            total += len(want)
            if got != want:
                bad += 1
                print(f'call {n}: {len(want)} scenery adds in the model, {len(got)} made; first difference '
                      f'{next(((i, w, g) for i, (w, g) in enumerate(zip(want, got)) if w != g), "in length")}')
        command('delete')
    print(f'{calls} calls ({total} scenery adds): ' + ('tile matches the model' if not bad else f'{bad} differ from the model'))

if __name__ == '__main__': main()
