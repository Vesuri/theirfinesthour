#!/usr/bin/env python3
"""FR-24 native gunner/free-look input and replay-safe processing."""
import argparse, struct
from fractions import Fraction
from input_combat_check import Checks, u, Q
class GunnerChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,t=50):
        a,c=self.a,self.c;a.reset()
        for o,v in ((11698,t),(11700,t),(11940,0),(11966,0),(11968,0),(11970,0),(11972,0),(11686,16384),(11688,0)):c.set(o,v)
        c.set(13322,1,'B');c.set(13390,0,'B')
    def step(self):self.c.run(self.c.bob+0x139d2)
    def baseline(self):
        a,c=self.a,self.c
        c.write(c.bob+0x139d2,a.orig[0x139d2:0x139d8]);self.flush();out=[]
        for t in (8,25,50,60):
            self.setup(t);c.set(11968,1024)
            for _ in range(t):self.step()
            out.append(c.get(11688,'H'))
        assert out==[1024,0,0,0],out
        c.write(c.bob+0x139d2,b'\x4e\xf9'+struct.pack('>I',a.sym('dt_gunner')));self.flush()
        print('FR-24 native gunner yaw dead-zone failure reproduced at 8/25/50/60 Hz')
    def flush(self):
        c=self.c;c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def rates(self):
        a,c=self.a,self.c
        for rate in (-10240,-1025,-65,-1,0,1,25,65,1025,10240):
            for schedule in ((8,),(25,),(50,),(60,),(8,50,25,60)):
                self.setup();elapsed=Fraction(0)
                for i in range(120):
                    t=schedule[i%len(schedule)];c.set(11698,t);c.set(11700,2);c.set(11968,rate);c.set(11970,rate)
                    self.step();elapsed+=Fraction(1,t)
                    expected=rate*elapsed
                    error=((c.get(11688,'H')-int(expected)+32768)%65536)-32768
                    assert abs(error)<=1,(rate,schedule,i,error)
                    assert abs(c.get(11686,'H')-max(0,min(32768,16384-expected)))<=1
        print('FR-24 signed fractional aiming, small inputs, changing rates and accelerated world time pass')
    def inputs(self):
        a,c=self.a,self.c
        for axis in (0,1):
            for total in (-100,-2,2,100):
                for shift in range(4):
                    out=[]
                    for t in (8,25,50,60):
                        self.setup(t);c.write(a.sym('dt_mouse_shift'),struct.pack('>H',shift))
                        for i in range(t):
                            delta=(i+1)*total//t-i*total//t
                            for o,v in ((11958,delta if axis==0 else 0),(11960,delta if axis else 0),(-4696,0),(-4694,0)):c.set(o,v)
                            c.run(c.bob+0x112);self.step()
                        out.append(c.get(11686,'H') if axis else c.get(11688,'H'))
                    assert len(set(out))==1,(axis,total,shift,out)
        for key in (1,2,3,4,32):
            self.setup();c.set(11940,99);c.set(11966,key)
            for _ in range(50):self.step()
            assert abs(c.get(11688,'H')-({1:65536-10240,2:10240}.get(key,0)))<=1
            assert abs(c.get(11686,'H')-({3:16384+10240,4:16384-10240}.get(key,16384)))<=1
            if key==32:assert c.get(30690)&2
        # Physical controller dead zones are applied once, before recording.
        self.setup();c.set(11968,64);c.set(11970,24);c.write(a.sym('dt_mouse_axes'),bytes(4))
        c.run(a.sym('dt_input_filter'));assert (c.get(11968),c.get(11970))==(0,0)
        c.set(11968,64);c.set(11970,24);c.write(a.sym('dt_mouse_axes'),struct.pack('>HH',1,1))
        c.run(a.sym('dt_input_filter'));assert (c.get(11968),c.get(11970))==(64,24)
        c.write(a.sym('dt_mouse_axes'),bytes(4));c.run(c.bob+0x304)
        assert (c.get(11968),c.get(11970))==(64,24)
        print('FR-24 mouse count/gain equivalence, recorded keyboard overrides and once-only controller filtering pass')
    def transitions(self):
        a,c=self.a,self.c;self.setup(60);c.set(11968,1);self.step()
        assert c.read(a.sym('dt_gunner_state'),2)!=bytes(2)
        c.set(13322,0,'B');c.set(13390,0,'B');c.run(c.bob+0x304)
        assert c.read(a.sym('dt_gunner_state'),10)==bytes(10)
        c.set(13390,4,'B');c.set(11688,1234);self.step();assert c.get(11688)==1234
        c.set(11968,0);c.set(11970,-10240);c.set(11686,32767);self.step();assert c.get(11686,'H')==32768
        assert c.read(a.sym('dt_gunner_state')+2,2)==bytes(2)
        c.set(11970,10240);self.step();assert c.get(11686,'H')<32768
        c.run(a.sym('dt_gunner_reset'));assert c.read(a.sym('dt_gunner_state'),10)==bytes(10)
        a.options();print('FR-24 station/free-look transitions, pose changes, aim limits/reset and original-mode gate pass')
    def run(self):self.baseline();self.rates();self.inputs();self.transitions()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');GunnerChecks(p.parse_args()).run()
