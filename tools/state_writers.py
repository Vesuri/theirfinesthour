#!/usr/bin/env python3
"""Locate executed simple memory stores to selected globals from a trace.
This reports executed destination EAs, task stacks and fields, not reconstructed
memory values. The independent gdb field snapshots remain the state oracle.
Unknown/complex destinations are skipped; do not use absence here as proof of no writes.
  state_writers.py TRACE DUMP BASE
"""
import argparse,collections,re,subprocess,os
from pathlib import Path
import barto
from tfh_report import regions
from state_report import VARIABLES

def main():
    p=argparse.ArgumentParser();p.add_argument('trace');p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));a=p.parse_args()
    dump=Path(a.dump).read_bytes();rr={n:lo for lo,hi,n,o in regions(dump,a.base)};hb=rr['bob'];a4=rr['bob-data']+0x7ffe
    dis=subprocess.run([os.path.expanduser('~/.local/opt/bin/m68k-amiga-elf-objdump'),'-D','-b','binary','-m','m68k:68000',f'--adjust-vma={a.base}',f'--start-address={hb}',f'--stop-address={hb+0x1156c}',a.dump],capture_output=True,text=True,check=True).stdout
    stores={}
    for line in dis.splitlines():
        parts=line.split('\t')
        if len(parts)<3:continue
        try:pc=int(parts[0].strip().rstrip(':'),16)
        except ValueError:continue
        ins=' '.join(parts[2:]);m=re.match(r'(move|addq|subq|addi|subi|add|sub|clr|and|or|eor|neg|not)\.([bwl]) (.*)',ins)
        if not m:continue
        dest=m[3].rsplit(',',1)[-1];ea=re.fullmatch(r'(-?\d+)?\(a([0-6])\)',dest)
        if ea:stores[pc]=(int(ea[1] or 0),8+int(ea[2]),{'b':1,'w':2,'l':4}[m[2]],ins)
    events=collections.defaultdict(list);t=barto.load(a.trace)
    for f in t.fields:
        for pc,c,r in t.instructions(f):
            if pc not in stores or r[12]!=a4:continue
            disp,reg,size,ins=stores[pc];addr=r[reg]+disp
            for name,(off,n) in VARIABLES.items():
                if addr<a4+off+n and a4+off<addr+size:
                    events[(name,pc-hb,r[15]>>12,ins)].append(f.index)
    for (name,pc,stack,ins),fields in sorted(events.items()):
        print(f'{name}: bob:{pc:05x} sp-page={stack:x} {ins}; stores={len(fields)} fields={sorted(set(fields))}')
if __name__=='__main__':main()
