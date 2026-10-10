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
  scen   bob:11604 (bob:1142c's vertex loops for one polygon) to its exit, bob:11b2a, 11b34
         or 11c70: the calls to bob:2f48c (transform) and bob:3041c (projection) with their
         arguments, the frame arrays -118..-24(a5), -378/-458(a5), the screen points at
         9126(a4), 26372/26382/26384(a4) and the exit, against a model of the original
         loops given the results of those calls.
  pnorm  bob:3041c (the projection's C entry) to bob:2f160: 4240/4242/4244 (words), 8860/8856
         and -10352(a4) = A5 from the stack arguments x, y, z, with x and y as magnitudes all
         shifted right one bit at a time until x | y | z < $8000, and on return D1-A6 and
         SP as at the call.
  aiturn bob:210de and 21170 (an AI plane's turn, CALLS of either) to bob:21116 and 211a8:
         v in -42(a5) from the folded bank a there, plane D4. The original truncates,
         ((a / 3) / 11700 * 22346[D4]) >> 16; CUSTOM4 carries the fraction, so per plane
         the sum of v stays within 1 of the exact a * 22346[D4] / (3 * 11700) / 65536.
"""
import argparse, collections, os, re, struct, tempfile
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
    p = argparse.ArgumentParser(); p.add_argument('--routine', default='xform', choices=['xform', 'proj', 'div', 'clear', 'tile', 'aiturn', 'scen', 'pnorm'])
    p.add_argument('calls', type=int)
    p.add_argument('dump'); p.add_argument('base', type=lambda x: int(x, 0))
    a = p.parse_args()
    rr = {n: lo for lo, hi, n, o in regions(Path(a.dump).read_bytes(), a.base)}
    hb, db = rr['bob'], rr['bob-data']
    keep = ['d3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'sp']
    bad = negs = 0
    if a.routine == 'clear': return check_clear(a.calls, hb)
    if a.routine == 'tile': return check_tile(a.calls, hb, db)
    if a.routine == 'aiturn': return check_aiturn(a.calls, hb, db)
    if a.routine == 'scen': return check_scen(a.calls, hb, db)
    if a.routine == 'pnorm': return check_pnorm(a.calls, hb, db)
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

def half(v):
    v = v - (1 << 32) if v & 0x80000000 else v
    return int(v / 2) & M32

def model_scen(f, g, verts, nums, results):
    """bob:11604..11b34: (calls, frame changes {offset: (size, value)}, globals, exit)"""
    F = lambda o, k: int.from_bytes(f[o:o + k], 'big')  # o: offset from a5 (negative)
    fr = {}
    def get(o, k): return fr[o][1] if o in fr else F(o, k)
    def put(o, k, v): fr[o] = (k, v & ((1 << 8 * k) - 1))
    n = F(-26, 2); calls = []; res = iter(results)
    sx = lambda v: v - 0x10000 if v & 0x8000 else v
    behind = F(-499, 1)
    for j in range(n):
        v = nums[j]
        if not get(-298 + v, 1):
            w = [struct.unpack_from('>H', verts, 6 * v + 2 * i)[0] for i in range(3)]
            if w[0] != 0x8000:
                arg = tuple(((sx(w[i]) << 6) + g[26360 + 4 * i]) & M32 for i in range(3))
                calls.append(('xform', arg)); r = next(res)
                for o, i in ((-118, 0), (-198, 1), (-278, 2)): put(o + 4 * v, 4, r[i])
                put(-298 + v, 1, 1)
            else:
                a, b = w[1], w[2]
                for o in (-118, -198, -278):
                    put(o + 4 * v, 4, half((get(o + 4 * a, 4) + get(o + 4 * b, 4)) & M32))
                put(-298 + v, 1, 1); put(-498 + v, 1, 1)
        if get(-278 + 4 * v, 4) & 0x80000000: behind = (behind + 1) & 0xff
    put(-24, 2, n); put(-499, 1, behind)
    gl = {}
    if behind == n:
        gl[26372] = (g[26372] + n) & M32; return calls, fr, gl, 0x11c70, []
    gl[26382] = gl[26384] = 0
    if behind: return calls, fr, gl, 0x11b34, []
    pts = []
    for j in range(n):
        v = nums[j]
        if get(-478 + v, 1):
            pts += [get(-378 + 4 * v, 4), get(-458 + 4 * v, 4)]; continue
        mid = False
        if get(-498 + v, 1):
            a, b = (struct.unpack_from('>H', verts, 6 * v + 2 * i)[0] for i in (1, 2))
            z = lambda u: (lambda x: x - (1 << 32) if x & 0x80000000 else x)(get(-278 + 4 * u, 4))
            mid = get(-478 + a, 1) and get(-478 + b, 1) and z(a) > 20000 and z(b) > 20000
        if mid:
            p = [(half(get(o + 4 * a, 4)) + half(get(o + 4 * b, 4))) & M32 for o in (-378, -458)]
        else:
            calls.append(('proj', tuple(get(o + 4 * v, 4) for o in (-118, -198, -278))))
            p = list(next(res))
        put(-378 + 4 * v, 4, p[0]); put(-458 + 4 * v, 4, p[1]); put(-478 + v, 1, 1)
        pts += p
    gl[26382] = 2 * n
    return calls, fr, gl, 0x11b2a, pts

def check_scen(calls, hb, db):
    bad = total = 0
    exits = (0x11b2a, 0x11b34, 0x11c70)
    seen = collections.Counter()
    with tempfile.TemporaryDirectory(prefix='tfh-scen-', dir='tmp') as t:
        t = os.path.relpath(t)
        def mem(addr, k):
            command(f'dump binary memory {t}/m.bin {addr:#x} {addr + k:#x}')
            return Path(f'{t}/m.bin').read_bytes()
        a4 = db + 0x7ffe
        L = lambda o: int.from_bytes(mem(a4 + o, 4), 'big')
        command(f'break *{hb + 0x11604:#x}')
        for n in range(calls):
            r0 = regs(command('continue\ninfo registers'))
            a5 = r0['a5']
            fb = mem(a5 - 512, 512)
            fbytes = lambda o, k: fb[512 + o:512 + o + k]
            class Fr:  # frame bytes indexed by a5 offset
                def __getitem__(self, s): return fbytes(s.start, s.stop - s.start)
            g = {o: L(o) for o in (26360, 26364, 26368, 26372)}
            cnt = int.from_bytes(fbytes(-26, 2), 'big')
            nums = mem(g[26372], max(cnt, 1))
            verts = mem(int.from_bytes(fbytes(-8, 4), 'big'), 6 * 256)
            command('delete\n' + ''.join(f'break *{hb + e:#x}\n' for e in (0x2f48c, 0x3041c) + exits))
            got_calls, results = [], []
            while True:
                r = regs(command('continue\ninfo registers'))
                pc = r['pc'] - hb
                if pc in exits: break
                args = struct.unpack('>4I', mem(r['sp'], 16))
                command(f'tbreak *{args[0]:#x}\ncontinue')
                kind = 'xform' if pc == 0x2f48c else 'proj'
                got_calls.append((kind, args[1:]))
                results.append(tuple(L(o) for o in ((4228, 4232, 4236) if kind == 'xform' else (4268, 4272))))
            want_calls, fr, gl, want_exit, pts = model_scen(Fr(), g, verts, nums, results)
            seen[{0x11b2a: 'drawn', 0x11b34: 'clipped', 0x11c70: 'behind'}[want_exit]] += 1
            seen['midpoints'] += sum(1 for o, (k, v) in fr.items() if -498 <= o < -478)
            seen['reused screen points'] += len(pts) // 2 - sum(1 for c in want_calls if c[0] == 'proj')
            fa = mem(a5 - 512, 512)
            errs = []
            if want_calls != got_calls: errs.append(f'calls {want_calls} got {got_calls}')
            if pc != want_exit: errs.append(f'exit {pc:#x} want {want_exit:#x}')
            for o, (k, v) in fr.items():
                if int.from_bytes(fa[512 + o:512 + o + k], 'big') != v: errs.append(f'frame {o}')
            for o in (-118, -198, -278, -378, -458):  # unchanged entries too
                for i in range(20):
                    if o + 4 * i not in fr and fa[512 + o + 4 * i:516 + o + 4 * i] != fbytes(o + 4 * i, 4):
                        errs.append(f'frame {o + 4 * i} changed')
            for o, v in gl.items():
                got = L(o) if o == 26372 else int.from_bytes(mem(a4 + o, 2), 'big')
                if got != v: errs.append(f'{o} = {got:#x} want {v:#x}')
            if pts and list(struct.unpack(f'>{len(pts)}I', mem(a4 + 9126, 4 * len(pts)))) != pts:
                errs.append('screen points')
            total += len(got_calls)
            if errs: bad += 1; print(f'call {n} ({cnt} vertices, exit {pc:#x}): ' + '; '.join(errs[:6]))
            command(f'delete\nbreak *{hb + 0x11604:#x}')
        command('delete')
    print(f'{calls} polygons ({total} transform and projection calls; ' +
          ', '.join(f'{k} {v}' for k, v in seen.items()) + '): ' +
          ('scen matches the model' if not bad else f'{bad} differ from the model'))

def model_pnorm(x, y, z):
    ax = (-x) & M32 if x & 0x80000000 else x
    ay = (-y) & M32 if y & 0x80000000 else y
    k = 0
    while (ax | ay | z) >> 15: ax >>= 1; ay >>= 1; z >>= 1; k += 1
    w = lambda v, neg: (-v if neg else v) & 0xffff
    return {4240: w(ax, x & 0x80000000), 4242: w(ay, y & 0x80000000), 4244: z & 0xffff}, k

def check_pnorm(calls, hb, db):
    bad = 0; shifts = collections.Counter()
    keep = ['d1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6']
    with tempfile.TemporaryDirectory(prefix='tfh-pnorm-', dir='tmp') as t:
        t = os.path.relpath(t)
        def mem(addr, k):
            command(f'dump binary memory {t}/m.bin {addr:#x} {addr + k:#x}')
            return Path(f'{t}/m.bin').read_bytes()
        a4 = db + 0x7ffe
        command(f'break *{hb + 0x3041c:#x}')
        for n in range(calls):
            r0 = regs(command('continue\ninfo registers'))
            ret, x, y, z = struct.unpack('>4I', mem(r0['sp'], 16))
            want, k = model_pnorm(x, y, z); shifts[k] += 1
            command(f'tbreak *{hb + 0x2f160:#x}\ncontinue')
            got = {o: int.from_bytes(mem(a4 + o, 2), 'big') for o in want}
            errs = [f'{o} = {got[o]:#x} want {want[o]:#x}' for o in want if got[o] != want[o]]
            for o, v in ((8860, x), (8856, y), (-10352, r0['a5'])):
                g = int.from_bytes(mem(a4 + o, 4), 'big')
                if g != v: errs.append(f'{o} = {g:#x} want {v:#x}')
            r1 = regs(command(f'tbreak *{ret:#x}\ncontinue\ninfo registers'))
            errs += [f'{k2} changed' for k2 in keep if r1[k2] != r0[k2]]
            if r1['sp'] != r0['sp'] + 4: errs.append('sp')
            if errs: bad += 1; print(f'call {n} ({x:#x},{y:#x},{z:#x}): ' + '; '.join(errs))
        command('delete')
    print(f'{calls} calls (shifts: ' + ', '.join(f'{k}: {v}' for k, v in sorted(shifts.items())) + '): ' +
          ('pnorm matches the model' if not bad else f'{bad} differ from the model'))

def check_aiturn(calls, hb, db):
    trunc = carry = 0
    sums = {}  # plane: [sum of v, exact sum, sign changes]
    exits = {0x210de: (0x21116, 1), 0x21170: (0x211a8, -1)}
    with tempfile.TemporaryDirectory(prefix='tfh-aiturn-', dir='tmp') as t:
        t = os.path.relpath(t)
        def w16(addr):
            command(f'dump binary memory {t}/w.bin {addr:#x} {addr + 2:#x}')
            return struct.unpack('>H', Path(f'{t}/w.bin').read_bytes())[0]
        a4 = db + 0x7ffe
        for e in exits: command(f'break *{hb + e:#x}')
        for n in range(calls):
            r = regs(command('continue\ninfo registers'))
            out, sign = exits[r['pc'] - hb]
            plane = r['d4'] & 0xffff
            ang, f, dv = w16(r['a5'] - 42), w16(a4 + 22346 + 2 * plane), w16(a4 + 11700)
            command(f'tbreak *{hb + out:#x}\ncontinue')
            v = w16(r['a5'] - 42)
            trunc += v == ((ang // 3) // dv * f) >> 16
            s = sums.setdefault(plane, [0, 0.0])
            s[0] += sign * v; s[1] += sign * ang * f / (3 * dv) / 65536
            carry += abs(s[0] - s[1]) < 1
        command('delete')
    print(f'{calls} calls, {len(sums)} planes: {trunc} as the truncating original, {carry} with the sum '
          'within 1 of exact; per plane sum of v / exact: ' +
          ', '.join(f'{p}: {s[0]}/{s[1]:.1f}' for p, s in sorted(sums.items())))
    print('aiturn matches the original' if trunc == calls else
          'aiturn carries its fraction' if carry == calls else 'aiturn differs from both models')

if __name__ == '__main__': main()
