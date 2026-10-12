#!/usr/bin/env python3
"""FR-26 native sound envelopes, sample queueing and display-time waits."""
import argparse,struct
from input_combat_check import Checks,u,Q
class AudioChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,hz):
        a,c=self.a,self.c;a.reset();c.write(a.sym('dt_hz'),struct.pack('>H',hz));c.set(30982,0xdff096,'I')
        c.write(c.a4+30998,bytes([1]*4));c.write(c.a4+31006,bytes([2]*4))
        c.write(c.a4-10420,bytes((1,255,255,0)))
        for channel in range(4):
            for seg in range(2):
                c.set(31010+channel*8+seg*4,0x10000+channel*4096+seg*512,'I');c.set(31042+channel*4+seg*2,256)
            c.set(31058+channel*2,200);c.set(31066+channel*2,0);c.set(31110+channel*2,120 if channel<3 else -1)
            c.set(31118+channel,0,'B');c.set(31122+channel*2,0)
            c.write(c.a4+31074+channel*3,bytes((255,128,192)));c.write(c.a4+31086+channel*3,bytes((2,1,1)))
            c.write(c.a4+31098+channel*3,bytes((20,12,0)))
    def tick(self):self.c.run(self.c.bob+0x29a76,stop=self.c.bob+0x29a80)
    def envelope(self):
        c=self.c;return (c.read(c.a4+30998,4),c.read(c.a4+31066,8),c.read(c.a4+31110,20))
    def gate(self,on):
        a,c=self.a,self.c;c.write(c.bob+0x2b6f4,b'\x4e\xb9'+struct.pack('>I',a.sym('dt_audio_tick')) if on else a.orig[0x2b6f4:0x2b6fa])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def audio(self):
        a,c=self.a,self.c;self.gate(False);baseline=[]
        for hz in (50,60):
            self.setup(hz)
            for _ in range(hz*2):c.run(c.bob+0x2b66c)
            baseline.append(self.envelope())
        assert baseline[0]!=baseline[1]
        self.setup(50);reference=[]
        for _ in range(300):c.run(c.bob+0x2b66c);reference.append(self.envelope())
        self.gate(True)
        for hz in (50,60):
            self.setup(hz);ticks=0
            for field in range(hz*6):
                self.tick();c.run(c.bob+0x2b66c)
                ticks+=int.from_bytes(c.read(a.sym('dt_field_due'),2),'big')
                if ticks:assert self.envelope()==reference[ticks-1],(hz,field,ticks)
                # Queue both sample segments on consecutive physical fields.
                if field<2:
                    for channel in range(4):
                        addr=int.from_bytes(c.read(0xdff0a0+channel*16,4),'big')
                        assert addr==0x10000+channel*4096+(512 if field==0 else 0),(hz,field,channel,addr)
            assert c.read(c.a4+30998,4)==bytes((0,0,0,1))
        print('FR-26 native four-channel attack/decay/sustain/release agree on PAL/NTSC; sample queueing still runs each physical field')
    def waits(self):
        a,c=self.a,self.c
        for hz in (50,60):
            self.setup(hz)
            for helper,threshold in (('dt_wait15',15 if hz==50 else 19),('dt_wait30',30 if hz==50 else 36),('dt_wait32',32 if hz==50 else 39)):
                for field in (0,threshold-1,threshold,threshold+1):
                    c.set(-8010,field);c.reg(9,123456);c.reg(10,654321)
                    c.write(0x8000,b'\x4e\xb9'+struct.pack('>I',a.sym(helper))+bytes.fromhex('55c257c34e75'))
                    c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(0x8000),Q(0x8010)))
                    c.run(0x8000)
                    assert bool(c.reg(11)&255)==(field<threshold) and bool(c.reg(12)&255)==(field==threshold),(helper,field)
                    assert c.reg(9)==123456 and c.reg(10)==654321
            for polls in (1,3,17):
                self.setup(hz);c.set(11980,0);c.set(11956,0);c.set(11950,0);c.set(11940,32)
                c.run(c.bob+0x35fc);assert c.get(11840)&2
                for field in range(1,hz*2//5+1):
                    self.tick()
                    for _ in range(polls):
                        c.set(11940,32);c.run(c.bob+0x35fc)
                        # Only the first poll after the elapsed deadline accepts it.
                        accepted=field==hz*2//5 and _==0
                        assert bool(c.get(11840)&2)==accepted,(hz,polls,field,_)
                c.set(11956,3);c.set(11940,0);c.run(c.bob+0x35fc);assert c.get(11840)==3
            self.setup(hz);c.set(11940,1);c.set(11958,0);c.set(11960,0);c.run(c.bob+0x112)
            c.set(11940,0)
            for field in range(1,hz//2+1):
                self.tick();c.run(c.bob+0x112)
                assert bool(c.get(11974))==(field<hz//2),(hz,field,c.get(11974))
        a.options();print('FR-26 native wait comparisons, 0.4s UI suppression, buttons and 0.5s flight key memory pass across polling rates')
    def run(self):self.audio();self.waits()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');AudioChecks(p.parse_args()).run()
