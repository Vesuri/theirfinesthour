#!/usr/bin/env python3
"""compare_traces.py A.bin B.bin: per-field identity of two traces ('.' same, 'X' differs).
Compares each field's raw instruction records (PCs, cycles, registers), DMA records and
screenshot bytes; the slow-RAM snapshot is ignored (it holds WHDLoad/host bytes)."""
import hashlib, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
import barto
a, b = barto.load(sys.argv[1]), barto.load(sys.argv[2])
def h(t, f):
    return (hashlib.sha1(t.data[f.insn_off:f.insn_end]).digest(), hashlib.sha1(f.dma).digest(),
            hashlib.sha1(f.shot).digest())
out = []
for fa, fb in zip(a.fields, b.fields):
    ha, hb = h(a, fa), h(b, fb)
    out.append('.' if ha == hb else 'i' if ha[0] != hb[0] else 'X')
print(''.join(out))
print('identical' if set(out) == {'.'} and len(a.fields) == len(b.fields) else 'DIFFERENT')
