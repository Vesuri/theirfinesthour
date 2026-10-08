#!/usr/bin/env python3
"""Compare two state_fields.py captures snapshot by snapshot: bob's whole data hunk, byte for byte.
  compare_state.py A/state B/state
Snapshot n of each is the data hunk at the n-th level-3 entry after the anchor. The hunk holds
absolute pointers, and another slave build can load bob elsewhere: a longword that points into
bob's code or data hunk at the same offset in both (metadata.json bases) counts as equal.
Prints how many snapshots are equal and, for the first that differs, the differing a4 offsets.
"""
import argparse, json, struct
from pathlib import Path

A4 = 0x7ffe
CODE, DATA = 0x31e40, 0xfa14  # bob's hunk sizes

def relocated(x, y, i, ma, mb):
    """offsets of x[i:i+4] and y[i:i+4] relative to bob's hunks, if both point into the same one"""
    if i + 4 > min(len(x), len(y)): return False
    u, v = struct.unpack_from('>I', x, i)[0], struct.unpack_from('>I', y, i)[0]
    for base, size in (('code_base', CODE), ('data_base', DATA)):
        if 0 <= u - ma[base] < size and u - ma[base] == v - mb[base]: return True
    return False

def differences(x, y, ma, mb):
    out, i = [], 0
    while i < min(len(x), len(y)):
        if x[i] == y[i]: i += 1; continue
        for j in range(max(0, i - 3), i + 1):  # a relocated longword containing byte i
            if relocated(x, y, j, ma, mb) and x[j:i] == y[j:i]:
                i = j + 4; break
        else:
            out.append(i - A4); i += 1
    return out

def main():
    p = argparse.ArgumentParser(); p.add_argument('a', type=Path); p.add_argument('b', type=Path)
    a = p.parse_args()
    names = sorted(f.name for f in a.a.glob('[0-9]*.bin'))
    assert names and names == sorted(f.name for f in a.b.glob('[0-9]*.bin')), 'different snapshot sets'
    ma, mb = (json.loads((d / 'metadata.json').read_text()) for d in (a.a, a.b))
    same, first = 0, None
    for n in names:
        x, y = (a.a / n).read_bytes(), (a.b / n).read_bytes()
        d = [] if x == y else differences(x, y, ma, mb)
        if not d: same += 1
        elif first is None: first = (n, d)
    print(f'{same}/{len(names)} snapshots equal')
    if first:
        n, offs = first
        print(f'first difference in {n}: {len(offs)} bytes at a4 offsets {offs[:12]}')

if __name__ == '__main__': main()
