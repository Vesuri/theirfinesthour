#!/usr/bin/env python3
"""FR-22 recording capacity, native snapshots and deterministic timestep history."""
import argparse,random,re,struct
from fractions import Fraction
from pathlib import Path
from input_combat_check import Checks,u,Q,P,I,C
class ReplayChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def manifest(self):
        a,c=self.a,self.c;out=[];p=a.sym('replay_state_table')
        while True:
            offset=int.from_bytes(c.read(p,2),'big',signed=True);p+=2
            if not offset:break
            size=int.from_bytes(c.read(p,2),'big');p+=2;out.append((a.sym('replay_state_table')+offset,size))
        p=a.sym('replay_extra_table')
        while True:
            offset=int.from_bytes(c.read(p,2),'big',signed=True);p+=2
            if not offset:break
            size=int.from_bytes(c.read(p,2),'big');p+=2;out.append((c.a4+offset,size))
        return out
    def state(self):return b''.join(self.c.read(addr,size) for addr,size in self.manifest())
    def snapshots(self):
        a,c=self.a,self.c;a.reset();r=random.Random(22);manifest=self.manifest()
        assert sum(n for _,n in manifest)==a.syms['REPLAY_SNAPSHOT_BYTES']
        names=set(re.findall(r'^(dt_\w+)\s+dcb?\.',Path('whdload/timing.s').read_text(),re.M))
        names-={'dt_contact_angle_offsets','dt_contact_bounds'}
        declared=set(re.findall(r'dc.w (dt_\w+)-replay_state_table',Path('whdload/replay.s').read_text()))
        assert names==declared,('snapshot manifest missing state',names-declared,declared-names)
        for addr,size in manifest:c.write(addr,r.randbytes(size))
        saved=self.state();c.reg(1,0x10000);c.reg(9,0);c.run(a.sym('replay_state_copy'))
        assert c.read(0x10000,len(saved))==saved
        for addr,size in manifest:c.write(addr,bytes(size))
        c.reg(1,0x10000);c.reg(9,1);c.run(a.sym('replay_state_copy'));assert self.state()==saved
        # Native 195-field snapshot and our two independent companions.
        a.reset();c.set(13016,0x10000,'I');c.set(13020,0x20000,'I')
        for slot,tag in ((13016,0x11),(13020,0x22)):
            for addr,size in manifest:c.write(addr,bytes([tag])*size)
            # Keep native arrays valid; copying itself never executes their values.
            c.set(13016,0x10000,'I');c.set(13020,0x20000,'I')
            c.run(c.bob+0x1996,args=struct.pack('>IH',c.get(slot,'I'),1))
        for slot,tag in ((13016,0x11),(13020,0x22),(13016,0x11)):
            c.run(c.bob+0x19f6,args=struct.pack('>IH',c.get(slot,'I'),1))
            for addr,size in manifest:
                expected=bytes(size) if addr==a.sym('dt_live') else bytes([0x22 if addr in (a.sym('dt_hz'),a.sym('dt_boot'),a.sym('dt_mouse_shift')) else tag])*size
                assert c.read(addr,size)==expected,(slot,hex(addr),size)
        print('FR-22 complete private manifest, native snapshots, rewind and live-return isolation pass')
    def record(self):
        c=self.c;c.reg(6,0x1e00000);c.write(0x1e00000,struct.pack('>II',0,0x1000))
        c.run(c.bob+0x13bf8)
    def capacity(self):
        a,c=self.a,self.c
        for schedule in ([8],[25],[50],[60],[8,50,25,60,4]):
            a.reset();c.set(25850,0);c.set(30696,1);c.write(c.a4-32244,b'\x4e\x75');elapsed=Fraction(0)
            frames=[]
            for i in range(7681):
                t=schedule[i%len(schedule)];sim=max(2,t//3) if i%3==0 else t
                c.set(11698,t);c.set(11700,sim);c.set(11702,(sim>>3)+1);c.set(-7828,i,'H')
                inputs=struct.pack('>4H',i&127,i&255,(i*7)&65535,i&1);c.write(c.a4+11966,inputs)
                self.record();elapsed+=Fraction(1,t);frames.append((inputs,t,sim,i))
                if not c.get(30696):break
            assert 128-Fraction(1,1000)<=elapsed<=128+max(Fraction(1,t) for t in schedule),(schedule,elapsed)
            assert c.get(25850)==len(frames)<=7680
            c.run(a.sym('replay_rewind'))
            for inputs,t,sim,seed in frames:
                # Rendering/current host divisors and RNG must not replace recorded ones.
                c.set(11698,17);c.set(11700,5);c.set(-7828,999)
                c.run(a.sym('replay_read'))
                assert c.read(c.a4+11966,8)==inputs
                assert (c.get(11698),c.get(11700),c.get(11702),c.get(-7828,'H'))==(t,sim,(sim>>3)+1,seed)
            assert c.get(13012,'I')==a.sym('replay_storage')+8*len(frames)
        a.options();print('FR-22 128-second recording capacity, varying timesteps, acceleration and RNG history pass')
    def world_replay(self,manual=0,steps=600):
        a,c=self.a,self.c;a.reset();c.set(13016,0x10000,'I');c.set(13020,0x20000,'I')
        c.set(25850,0);c.set(30696,1);c.set(26004,0);c.set(13322,manual,'B')
        c.set(11966,0);c.set(11972,0);c.write(c.a4-32244,b'\x4e\x75')
        c.write(c.a4-32448,b'\x4e\x75')  # isolate transition UI
        regions=[]
        for i in range(195):
            addr=c.get(-27322+4*i,'I');size=c.get(-26542+2*i,'H')
            # Exclude hardware field count, which is not a simulation clock.
            if addr!=c.a4-8010:regions.append((addr,size))
        expected=[]
        for i in range(steps):
            t=(8,50,25,60)[i%4];c.set(11698,t);c.set(11700,2);c.set(11702,1)
            c.set(11968,64 if i<60 else -64);c.set(11970,0);c.set(11972,1 if i%10==0 else 0)
            if manual:c.set(11966,(0,1,2,3,4,32)[i%6])
            c.run(c.bob+0x12984,args=b'\x00\x01');c.run(c.bob+0x12dba)
            if i==0:c.run(c.bob+0x1996,args=struct.pack('>IH',0x10000,1))
            self.record();c.run(c.bob+0x12eaa)
            expected.append([c.read(addr,size) for addr,size in regions])
        c.run(c.bob+0x19f6,args=struct.pack('>IH',0x10000,1));c.run(a.sym('replay_rewind'))
        c.set(30728,len(expected));c.set(26004,1);c.set(30656,1)
        for i,frame in enumerate(expected):
            c.set(11698,17);c.set(11700,3)
            c.run(c.bob+0x16a3a) if i%2 else c.run(a.sym('replay_step'))
            got=[c.read(addr,size) for addr,size in regions]
            differences=[(addr-c.a4,size) for (addr,size),old,new in zip(regions,frame,got) if old!=new]
            assert not differences,('world replay diverged',i,differences)
        assert c.get(30728)==0 and c.get(30656)==0
        print('FR-22 full native world trajectory and last-step playback match recorded states')
    def pacing(self):
        a,c=self.a,self.c
        schedules=((8,), (50,), (60,), (8,50,25,60))
        for hz in (50,60):
            for rates in schedules:
                for draw_fields in (1,2,5):
                    a.reset();c.write(c.a4-32244,b'\x4e\x75');c.write(c.a4-32448,b'\x4e\x75')
                    c.set(26004,1);c.set(30656,1);c.set(30728,300);c.set(25850,300)
                    c.write(a.sym('dt_hz'),struct.pack('>H',hz));c.write(a.sym('replay_storage'),bytes(2400))
                    c.write(a.sym('replay_storage')+a.syms['REPLAY_INPUT_BYTES'],b''.join(struct.pack('>4H',rates[i%len(rates)],rates[i%len(rates)],1,1234) for i in range(300)))
                    c.run(a.sym('replay_rewind'));c.set(-8010,0);c.run(a.sym('replay_read_continuous'),stop=c.bob+0x15fba)
                    for field in range(draw_fields,hz*2+1,draw_fields):
                        c.set(-8010,field);c.run(a.sym('replay_read_continuous'),stop=c.bob+0x15fba)
                    count=300-c.get(30728);used=sum((Fraction(1,rates[i%len(rates)]) for i in range(count)),Fraction())
                    assert abs(used-Fraction(field,hz))<=max(Fraction(1,t) for t in rates)+Fraction(1,1000),(hz,rates,draw_fields,count,used)
                    c.set(30656,0);c.run(a.sym('replay_read_continuous'),stop=c.bob+0x15fba)
                    c.set(-8010,field+10);c.set(30656,1);c.run(a.sym('replay_read_continuous'),stop=c.bob+0x15fba)
                    assert 300-c.get(30728)==count
        # Fast-forward follows actual recorded world time rather than T records.
        a.reset();c.write(c.a4-32244,b'\x4e\x75');c.write(c.a4-32448,b'\x4e\x75')
        c.set(26004,1);c.set(30728,30);c.set(25850,30);c.set(12058,0x1203)
        c.write(a.sym('replay_storage'),bytes(240));c.write(a.sym('replay_storage')+a.syms['REPLAY_INPUT_BYTES'],struct.pack('>4H',50,2,1,1234)*30)
        c.run(a.sym('replay_rewind'));c.run(a.sym('replay_skip_second'),stop=c.bob+0x167aa)
        assert c.get(30728)==28 and c.get(12058)==0x1203
        print('FR-22 PAL/NTSC playback pacing, different render rates, pause/resume and elapsed-time fast-forward pass')
    def file_roundtrip(self):
        a,c=self.a,self.c;a.reset();c.set(13016,0x10000,'I');c.set(25560,1,'I')
        self.file=bytearray();self.readpos=0;self.file_error=False;self.deleted=False
        def io(h,addr,size,user):
            off=addr-c.bob
            if off==0x3418:
                if self.file_error:c.reg(9,0xffffffff)
                else:
                    value=int.from_bytes(c.read(c.reg(8)+4,2),'big')&255
                    self.file.append(value);c.reg(9,value)
            elif off==0x33f8:
                if self.readpos<len(self.file):c.reg(9,self.file[self.readpos]);self.readpos+=1
                else:c.reg(9,0xffffffff)
            elif off==0x1cb2:c.set(25560,1,'I');c.reg(9,1)
            elif off==0x9ea:self.deleted=True;c.reg(9,0)
            else:c.reg(9,0)
        self.io_callback=C.CFUNCTYPE(None,P,Q,I,P)(io);self.io_hooks=[]
        u.uc_hook_add.argtypes=[P,C.POINTER(Q),I,P,P,Q,Q];u.uc_hook_add.restype=I
        for off in (0x3418,0x33f8,0x33c8,0x357a,0x1cb2,0x1d54,0x9ea):
            c.write(c.bob+off,b'\x4e\x75');hook=Q()
            c.ck(u.uc_hook_add(c.h,C.byref(hook),4,self.io_callback,None,c.bob+off,c.bob+off));self.io_hooks.append(hook)
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        def file_call(off):
            c.reg(8,0x1f00000);c.write(0x1f00000,struct.pack('>II',0x1000,0x1200))
            c.ck(u.uc_emu_start(c.h,c.bob+off,0x1000,30000000,20000000))
            assert c.reg(18)==0x1000,hex(c.reg(18))
            return c.reg(9)
        r=random.Random(220);size=a.syms['REPLAY_SNAPSHOT_BYTES'];prefix=4+8192+12213
        for count in (0,2,1023,7680):
            inputs=r.randbytes(count*8);meta=b''.join(struct.pack('>4H',50,16,3,i) for i in range(count))
            private=r.randbytes(size);native=r.randbytes(12213)
            c.write(a.sym('replay_storage'),inputs);c.write(a.sym('replay_storage')+a.syms['REPLAY_INPUT_BYTES'],meta)
            c.write(a.sym('replay_movie_state'),private);c.write(0x10000,native)
            c.set(25850,count);c.set(25852,1234);c.write(a.sym('replay_legacy'),bytes(2))
            self.file=bytearray();assert file_call(0x1a4e)==1
            assert self.file[:2]==bytes(2) and self.file[prefix:prefix+4]==b'TFH3'
            assert len(self.file)==prefix+16+size+16*count
            saved=bytes(self.file);c.write(a.sym('replay_movie_state'),bytes(size));c.write(0x10000,bytes(12213))
            c.write(a.sym('replay_storage'),bytes(count*8));self.readpos=0
            assert file_call(0x1bc4)==1
            assert c.get(25850)==count and c.get(25852)==1234
            assert c.read(a.sym('replay_movie_state'),size)==private and c.read(0x10000,12213)==native
            assert c.read(a.sym('replay_storage'),count*8)==inputs
            assert c.read(a.sym('replay_storage')+a.syms['REPLAY_INPUT_BYTES'],count*8)==meta
        # Reject truncation, unsupported format, oversized count, layout mismatch and zero divisor.
        malformed=[saved[:prefix+8],saved[:-1]]
        for off,value in ((prefix+4,b'\x00\x02'),(prefix+6,b'\xff\xff'),(prefix+12,b'\x00\x01'),(prefix+16+size+7680*8,b'\x00\x00')):
            blob=bytearray(saved);blob[off:off+2]=value;malformed.append(blob)
        for blob in malformed:
            self.file=bytearray(blob);self.readpos=0
            assert file_call(0x1bc4)==0 and c.get(25850)==0
        # Legacy prefix remains readable with the original 1,023-sample policy.
        self.file=bytearray(saved[:prefix]);self.file[:2]=struct.pack('<H',20);self.readpos=0
        assert file_call(0x1bc4)==1 and c.get(25850)==20
        assert c.read(a.sym('replay_legacy'),2)==b'\x00\x01'
        # A write failure follows native close/delete failure handling.
        self.file_error=True;self.file=bytearray()
        assert file_call(0x1a4e)==0 and self.deleted
        print('FR-22 native file round trips, maximum capacity, legacy prefix, malformed reads and write failures pass')
    def run(self):self.snapshots();self.capacity();self.world_replay();self.world_replay(manual=1,steps=120);self.pacing();self.file_roundtrip()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');ReplayChecks(p.parse_args()).run()
