#!/usr/bin/env python3
"""FR-17 native player ground steering and airborne isolation regression."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,u,Q

class SteeringChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def patch(self,on):
        a,c=self.a,self.c
        c.write(c.bob+0x1467a,b'\x4e\xb9'+struct.pack('>I',a.sym('dt_ground_steer'))+b'\x4e\x71' if on else a.orig[0x1467a:0x14682])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob+0x13c6e),Q(c.bob+0x14ac6)))
    def setup(self,state=2,throttle=1,slot=1):
        a,c=self.a,self.c;a.reset();self.slot=slot
        c.set(13318,slot);c.set(13326,0,'B');c.set(22386+slot,state,'B')
        c.set(22402+slot*2,throttle);c.set(19694+slot*2,0);c.set(18162+slot*2,0)
        for off in (11966,11970,11972):c.set(off,0)
        for off in (13322,13390,13324):c.set(off,0,'B')
    def step(self,t,stick,world=None):
        c=self.c;c.set(11698,t);c.set(11700,world or t);c.set(11968,stick)
        c.reg(6,0x1e00000);c.write(0x1e00000,struct.pack('>II',0,0x1000))
        c.run(c.bob+0x13c76)
        return c.get(18162+self.slot*2)
    def baseline(self):
        self.patch(False);out=[]
        for t in (8,50):
            self.setup()
            for _ in range(t):angle=self.step(t,256)
            out.append(angle)
        assert out==[64,50],out
        self.setup()
        for _ in range(100):assert self.step(50,7)==0
        self.patch(True)
        print('FR-17 native steering loss and dead small inputs reproduced:',out)
    def motion(self):
        seqs=[[t]*t for t in (2,4,8,25,50,60)]+[[2]+[50]*25,[8]*4+[60]*30]
        for stick in (0,1,-1,7,-7,256,-256,16384,-16384,32767,-32768):
            for seq in seqs:
                self.setup();elapsed=Fraction(0)
                for t in seq:
                    angle=self.step(t,stick,max(2,t//3));elapsed+=Fraction(1,t)
                    assert abs(angle-elapsed*Fraction(stick,4))<=1,(stick,t,angle,elapsed)
                # Identical elapsed reverse input cancels the signed carry exactly.
                if stick!=-32768:
                    for t in seq:angle=self.step(t,-stick)
                    assert angle==0,(stick,seq[0],angle)
        # Neutral samples do not consume a residual or invent extra movement.
        self.setup();angle=self.step(50,-1)
        frac=self.c.read(self.a.sym('dt_ground_frac')+2,2)
        for _ in range(50):assert self.step(50,0)==angle
        assert self.c.read(self.a.sym('dt_ground_frac')+2,2)==frac
        print('FR-17 tiny/full signed input, changing rates, acceleration, reversal and neutral carry pass')
    def gates(self):
        a,c=self.a,self.c
        for state,throttle in ((2,0),(0,1),(1,1),(3,1),(7,1)):
            snapshots=[]
            for on in (False,True):
                self.patch(on);self.setup(state,throttle)
                for t in (8,50,60,2):self.step(t,-256)
                snapshots.append(c.read(c.a4-0x7ffe,0xfa14))
            assert snapshots[0]==snapshots[1],(state,throttle)
        for slot in range(16):
            self.setup(slot=slot)
            for _ in range(50):angle=self.step(50,256)
            assert abs(angle-64)<=1
            c.write(a.sym('dt_ground_frac'),b'\xff'*32)
            c.reg(13,slot);c.run(a.sym('dt_plane_generation'))
            assert c.read(a.sym('dt_ground_frac'),32)==b'\xff'*(slot*2)+bytes(2)+b'\xff'*(30-slot*2)
        c.run(a.sym('dt_effect_init'))
        assert c.read(a.sym('dt_ground_frac'),32)==bytes(32)
        a.options()
        print('FR-17 unchanged airborne/non-taxi/zero-throttle native state, all slots, resets and original gate pass')
    def run(self):self.baseline();self.motion();self.gates()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    SteeringChecks(p.parse_args()).run()
