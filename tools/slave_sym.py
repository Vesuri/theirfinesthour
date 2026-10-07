#!/usr/bin/env python3
"""Absolute addresses of slave symbols in a running capture.

  python3 tools/slave_sym.py CODE.bin BASE SYMBOL [SYMBOL...]

Symbol offsets come from the vasm listing of the verify build (whdload/TheirFinestHour.lst,
written by `make -C whdload verify`); the slave base comes from tfh_report.regions(), which
needs SLAVE= naming the slave that is running.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from tfh_report import ROOT, regions


def offsets(lst=os.path.join(ROOT, 'whdload/TheirFinestHour.lst')):
    out = {}
    for line in open(lst, encoding='latin1'):
        m = re.match(r'^([0-9A-F]{8}) (\S+)$', line.rstrip('\n'))
        if m:
            out[m.group(2)] = int(m.group(1), 16)
    return out


def addresses(dump, base, names):
    slave = next(lo for lo, hi, n, o in regions(dump, base) if n == 'slave')
    off = offsets()
    return {n: slave + off[n] for n in names}


if __name__ == '__main__':
    dump = open(sys.argv[1], 'rb').read()
    for n, a in addresses(dump, int(sys.argv[2], 0), sys.argv[3:]).items():
        print(f'{n} {a:#x}')
