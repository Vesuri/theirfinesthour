#!/usr/bin/env python3
"""Read bob's data hunk (chip RAM) at successive level-3 interrupt entries; never write game memory.
Run while tfh.py is stopped at the anchor. All dumps go through a space-free
private /tmp directory because the stub's gdb cannot quote dump file names.
  state_fields.py FIELDS OUTDIR CODE.bin BASE
The first snapshot precedes field 0; subsequent snapshots are at VBL-server entry.
"""
import argparse, json, os, shutil, socket, struct, tempfile
from pathlib import Path
from tfh import SOCK
from tfh_report import regions

def command(s):
    with socket.socket(socket.AF_UNIX) as c:
        c.connect(SOCK); c.sendall(('gdb '+s).encode()); out = b''
        while chunk := c.recv(65536): out += chunk
    reply = out.decode()
    if 'ERROR' in reply: raise RuntimeError(reply)
    return reply

def main():
    p = argparse.ArgumentParser(); p.add_argument('fields', type=int)
    p.add_argument('out'); p.add_argument('dump'); p.add_argument('base', type=lambda x:int(x,0))
    a = p.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    rr={n:lo for lo,hi,n,o in regions(Path(a.dump).read_bytes(),a.base)}
    hb, db=rr['bob'],rr['bob-data']; end=db+0xfa14
    # under tmp/, by a relative path: gdb runs in the repo root and its dump takes no spaces
    with tempfile.TemporaryDirectory(prefix='tfh-state-', dir='tmp') as temp:
        temp = os.path.relpath(temp)
        text=command(f"""dump binary memory {temp}/initial.bin {db:#x} {end:#x}
break *{hb+0x28d4c:#x}
set $tfh_sample = 0
while $tfh_sample < {a.fields}
continue
eval "dump binary memory {temp}/%04d.bin {db:#x} {end:#x}", $tfh_sample
set $tfh_sample = $tfh_sample + 1
end
delete
""")
        (out/'gdb.txt').write_text(text)
        files=sorted(Path(temp).glob('*.bin'))
        if len(files)!=a.fields+1: raise RuntimeError(f'{len(files)} snapshots, expected {a.fields+1}')
        for f in files: shutil.move(str(f),out/f.name)
    (out/'metadata.json').write_text(json.dumps(dict(code_base=hb,data_base=db,a4=db+0x7ffe,fields=a.fields,anchor='bob:28d4c entry (level-3 interrupt)'),indent=2)+'\n')
    print(f'{a.fields} field snapshots: {out}')
if __name__=='__main__': main()
