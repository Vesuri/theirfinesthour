#!/usr/bin/env python3
"""Attribute a cycle-exact FS-UAE trace of the original Their Finest Hour to its routines.

  python3 tools/tfh_report.py TRACE.bin MEMDUMP.bin [--base=0xc00000] [--top=40]

TRACE is `tfh.py profile` output (Barto format, all PCs recorded); MEMDUMP is a gdb
`dump binary memory` of the region holding the code (base address --base), taken in the
same session so the loaded addresses match.  Code regions are identified by matching the
dump against the installed files: `bob` code hunk, the Kickstart 1.3 image kickemu
copies into RAM, and the WHDLoad slave.  `bob`'s data hunk is MEMF_CHIP, so it is found by
following LoadSeg's BPTR chain into chip RAM (read from the trace's chip snapshot).

Calls are rebuilt from the instruction stream: a jsr/bsr pushes a frame (callee = the next
traced PC), the frame pops once SP climbs back above its return slot.  `jsr d16(a6)` is
named after the library node at a6 and the LVO.  User and supervisor execution keep
separate stacks.  Cycles are 7.09 MHz CPU clocks; a PAL field is 142,102.
"""
import argparse, collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import barto

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELD = 142102


class Memory:
    def __init__(self, trace, dump, base):
        self.chip, self.dump, self.base = trace.chip, dump, base

    def read(self, a, n):
        if self.base <= a and a + n <= self.base + len(self.dump):
            return self.dump[a - self.base:a - self.base + n]
        if a + n <= len(self.chip):
            return self.chip[a:a + n]
        return None

    def word(self, a):
        b = self.read(a, 2)
        return struct.unpack('>H', b)[0] if b else None

    def long(self, a):
        b = self.read(a, 4)
        return struct.unpack('>I', b)[0] if b else None

    def cstr(self, a):
        out = b''
        while a and len(out) < 40:
            b = self.read(a, 1)
            if not b or b == b'\0':
                break
            out += b
            a += 1
        return out.decode('latin1')


def locate(mem, blob, base, step=64):
    votes = collections.Counter()
    for off in range(0, len(blob) - 16, step):
        w = blob[off:off + 16]
        if w.count(0) > 8:
            continue
        # Vote for every occurrence (up to 4): WHDLoad's PRELOAD cache can hold a second copy.
        i, seen = mem.find(w), 0
        while i >= 0 and seen < 4:
            votes[base + i - off] += 1
            i, seen = mem.find(w, i + 1), seen + 1
    # WHDLoad's PRELOAD caches whole files in memory: a copy preceded by its own hunk header
    # ($3F3 at file offset 0) is the cached file, not the loaded program.
    for a, n in votes.most_common():
        hdr = a - base - 0x28
        if n >= 4 and not (hdr >= 0 and mem[hdr:hdr + 4] == b'\0\0\x03\xf3'):
            return a
    return None


# data/bob v1.1 (CRC16 $274F, the slave's only "bob" list for this version): Aztec C,
# hunk 0 code at file $28 ($31E40 bytes), hunk 1 data MEMF_CHIP ($AB70 in the file, $FA14
# allocated), hunk 2 BSS (4 bytes).
BOB = 'tmp/game/TheirFinestHour/data/bob'
CODE_FILE, CODE_SIZE = 0x28, 0x31e40
DATA_SIZE = 0xfa14


def regions(dump, base, chip=None):
    """[(lo, hi, name, origin)] for the code regions found in the dump.  The data hunk is
    usually in chip RAM; pass the trace's chip snapshot as `chip` to bound-check it."""
    bob = open(os.path.join(ROOT, BOB), 'rb').read()
    kick = open(os.path.expanduser('~/Documents/RetroPie/BIOS/kick34005.A500'), 'rb').read()
    slave_path = os.environ.get('SLAVE') or os.path.join(ROOT, 'tmp/game/TheirFinestHour/TheirFinestHour.Slave')
    slave = open(slave_path, 'rb').read()
    out = []
    code = bob[CODE_FILE:CODE_FILE + CODE_SIZE]
    a = locate(dump, code, base)
    if a:
        out.append((a, a + len(code), 'bob', a))
        # Follow LoadSeg's BPTR chain; a byte search can select the PRELOAD data copy.
        next_bptr = struct.unpack_from('>I', dump, a - base - 4)[0]
        data_base = next_bptr * 4 + 4
        in_dump = base <= data_base and data_base + DATA_SIZE <= base + len(dump)
        in_chip = data_base + DATA_SIZE <= (len(chip) if chip is not None else 0x200000)
        if next_bptr and (in_dump or in_chip):
            out.append((data_base, data_base + DATA_SIZE, 'bob-data', data_base))
    a = locate(dump, kick[:0x40000], base, 256)
    if a: out.append((a, a + 0x40000, 'kick', a - 0xfc0000))  # name by ROM address
    # Match the slave's code hunk only (the file's header and HUNK_END are not in memory).
    shunk = slave[0x20:0x20 + struct.unpack_from('>I', slave, 0x18)[0] * 4]
    a = locate(dump, shunk, base, 16)
    if a: out.append((a, a + len(shunk), 'slave', a))
    return out


class Namer:
    def __init__(self, regs, mem):
        self.regs, self.mem = regs, mem
        self.libs = {}
        self.starts = set()
        for lo, hi, name, origin in regs:
            if name == 'bob':
                for a in range(lo, hi, 2):
                    if mem.word(a) == 0x4e55:  # link a5,#n: Aztec C prologue
                        self.starts.add(a)

    def addr(self, pc):
        if pc is None:
            return '[stopped]'
        if pc == 0x7fffffff:
            return '[irq entry]'
        for lo, hi, name, origin in self.regs:
            if lo <= pc < hi:
                return f'{name}:{pc - origin:05x}' if name != 'kick' else f'kick:{pc - origin:06x}'
        if pc >= 0xf80000:
            return f'rom:{pc:06x}'
        return f'?{pc:06x}'

    def lib(self, base):
        if base not in self.libs:
            name = self.mem.cstr(self.mem.long(base + 10) or 0)
            self.libs[base] = name.replace('.library', '').replace('.resource', '') or f'lib@{base:x}'
        return self.libs[base]


def contexts(trace, fields):
    """Group stack pointers into stacks: pages closer than 8 KB belong to one stack.
    UAE's recorded SR is stale (rebuilt lazily), so SP is the only mode signal."""
    pages = collections.Counter()
    for f in fields[:10]:
        for pc, cost, r in trace.instructions(f):
            pages[r[15] >> 12] += cost
    groups, cur = [], []
    for p in sorted(pages):
        if cur and p - cur[-1] > 2:
            groups.append(cur); cur = []
        cur.append(p)
    if cur: groups.append(cur)
    groups.sort(key=lambda g: -sum(pages[p] for p in g))
    return [(g[0] << 12, (g[-1] + 1) << 12) for g in groups]


def analyse(trace, mem, namer, fields):
    ranges = contexts(trace, fields)
    labels = ['main'] + [f'ctx{i}' for i in range(1, len(ranges))]
    def ctx_of(sp):
        for (lo, hi), name in zip(ranges, labels):
            if lo <= sp < hi + 0x1000:
                return f'{name}@{lo:x}'
        return f'sp@{sp >> 12:x}000'
    self_c = collections.Counter()
    incl = collections.Counter()
    calls = collections.Counter()
    edges = collections.Counter()  # (caller, callee) -> inclusive cycles
    pcs = collections.Counter()
    leafpcs = collections.Counter()
    kinds = collections.Counter()
    stacks = collections.defaultdict(list)  # context -> [(sp_before, name)]
    pending = None  # (sp_before, label or None) for the call just executed
    starts = set(namer.starts)
    for f in fields:
        for pc, cost, r in trace.instructions(f):
            sp = r[15]
            sup = ctx_of(sp)  # execution context = which stack SP lies in
            if pc is None or pc == 0x7fffffff:
                kinds['stopped' if pc is None else 'irq-entry'] += cost
                self_c[namer.addr(pc)] += cost
                incl[namer.addr(pc)] += cost
                pending = None
                continue
            st = stacks[sup]
            if pending is not None:
                psp, plabel, psup = pending
                if psup == sup and sp == psp - 4:
                    target = pc
                    if mem.word(pc) == 0x4ef9:  # jmp abs.l trampoline (jump table)
                        target = mem.long(pc + 2)
                    starts.add(target)
                    st.append((psp, plabel or namer.addr(target)))
                    calls[st[-1][1]] += 1
                pending = None
            while st and sp >= st[-1][0]:
                st.pop()
            if len(st) > 200:
                del st[:100]
            leafpcs[(sup, pc)] += cost
            seen = set()
            prev = '[top]'
            for _, name in st:
                if name not in seen:
                    incl[name] += cost
                    seen.add(name)
                edges[(prev, name)] += cost
                prev = name
            pcs[pc] += cost
            kinds[sup] += cost
            op = mem.word(pc)
            if op is None:
                continue
            if (op & 0xff00) == 0x6100 or (op & 0xffc0) == 0x4e80:
                label = None
                if op == 0x4eae:  # jsr d16(a6)
                    disp = struct.unpack('>h', mem.read(pc + 2, 2))[0]
                    label = f'{namer.lib(r[14])}{disp}'
                pending = (sp, label, sup)
    ordered = sorted(starts)
    import bisect
    by_ctx = collections.defaultdict(collections.Counter)
    for (ctx, pc), c in leafpcs.items():
        i = bisect.bisect_right(ordered, pc) - 1
        fn = ordered[i] if i >= 0 else None
        name = namer.addr(fn) if fn is not None and namer.addr(fn).split(':')[0] == namer.addr(pc).split(':')[0] else namer.addr(pc)
        self_c[name] += c
        by_ctx[ctx][name] += c
    return self_c, incl, calls, edges, pcs, kinds, by_ctx


def main():
    p = argparse.ArgumentParser()
    p.add_argument('trace')
    p.add_argument('dump')
    p.add_argument('--base', type=lambda s: int(s, 0), default=0x330000)
    p.add_argument('--top', type=int, default=40)
    p.add_argument('--fields', default=None, help='a-b (0-based, inclusive)')
    a = p.parse_args()
    trace = barto.load(a.trace)
    dump = open(a.dump, 'rb').read()
    mem = Memory(trace, dump, a.base)
    regs = regions(dump, a.base, trace.chip)
    namer = Namer(regs, mem)
    fields = trace.fields
    if a.fields:
        lo, hi = map(int, a.fields.split('-'))
        fields = fields[lo:hi + 1]
    self_c, incl, calls, edges, pcs, kinds, by_ctx = analyse(trace, mem, namer, fields)
    total = sum(kinds.values())
    nf = len(fields)
    print(f'# {a.trace}: {nf} fields, {total} cycles ({total / nf / FIELD:.3f} of each field)')
    print('regions:', ', '.join(f'{n} {lo:#x}-{hi:#x}' for lo, hi, n, _ in regs))
    print('by mode:', ', '.join(f'{k} {100 * v / total:.1f}%' for k, v in kinds.most_common()))
    reg = collections.Counter()
    for pc, c in pcs.items():
        reg[namer.addr(pc).split(':')[0]] += c
    print('by region:', ', '.join(f'{k} {100 * v / total:.1f}%' for k, v in reg.most_common()))
    for ctx, cnt in sorted(by_ctx.items(), key=lambda kv: -sum(kv[1].values())):
        ct = sum(cnt.values())
        print(f'\n## Context {ctx}: {100 * ct / total:.1f}% ({ct / nf:.0f} cycles/field), self time')
        for name, c in cnt.most_common(12):
            print(f'{100 * c / total:6.2f} {c / nf:9.0f}  {name}')
    print(f'\n## Self time (top {a.top})')
    print(f'{"%":>6} {"cyc/field":>9} {"calls":>7}  routine')
    for name, c in self_c.most_common(a.top):
        print(f'{100 * c / total:6.2f} {c / nf:9.0f} {calls[name]:7d}  {name}')
    print(f'\n## Inclusive time (top {a.top})')
    print(f'{"%":>6} {"cyc/field":>9} {"calls":>7} {"cyc/call":>8}  routine')
    for name, c in incl.most_common(a.top):
        n = calls[name]
        print(f'{100 * c / total:6.2f} {c / nf:9.0f} {n:7d} {c / n if n else 0:8.0f}  {name}')
    print(f'\n## Hottest instructions')
    for pc, c in pcs.most_common(25):
        op = mem.read(pc, 6)
        print(f'{100 * c / total:6.2f}  {pc:06x} {namer.addr(pc):16s} {op.hex() if op else ""}')
    print(f'\n## Call edges (inclusive cycles, top 40)')
    for (x, y), c in edges.most_common(40):
        print(f'{100 * c / total:6.2f}  {x} -> {y}')


if __name__ == '__main__':
    main()
