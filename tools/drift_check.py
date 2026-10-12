#!/usr/bin/env python3
"""FR-18 native auxiliary aircraft movement and formation-rate regression."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,u,Q

class DriftChecks:
    origins=(10000000,10000000,50000)
    positions=(14290,14898,15506)
    rates=(19470,19502,19534)
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def patch(self,on):
        a,c=self.a,self.c
        for off,axis in ((0x155d6,'x'),(0x1563a,'y'),(0x1569e,'z')):
            c.write(c.bob+off,b'\x4e\xb9'+struct.pack('>I',a.sym('dt_drift_'+axis)) if on else a.orig[off:off+6])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob+0x154b2),Q(c.bob+0x15b70)))
    def setup(self,values,slot=1):
        a,c=self.a,self.c;a.reset();self.slot=slot
        c.write(c.a4+13394,bytes(152));c.set(13394+slot,4,'B');c.set(13562+slot,1,'B')
        c.set(19694+slot*2,0);c.set(18162+slot*2,0);c.set(18466+slot*2,16384)
        for off,v in zip(self.rates,values):c.set(off+slot*2,v)
        for off,v in zip(self.positions,self.origins):c.set(off+slot*4,v,'i')
    def step(self,t,values=None):
        c=self.c;c.set(11700,t)
        if values is not None:
            for off,v in zip(self.rates,values):c.set(off+self.slot*2,v)
        c.run(c.bob+0x154b2)
        return tuple(c.get(off+self.slot*4,'i')-v for off,v in zip(self.positions,self.origins))
    def baseline(self):
        self.patch(False);out=[]
        for t in (8,50):
            self.setup((399,-399,7))
            for _ in range(t):p=self.step(t)
            out.append(p)
        assert out==[(392,-392,0),(350,-350,0)],out
        self.patch(True)
        print('FR-18 native signed drift loss reproduced:',out)
    def motion(self):
        seqs=[[t]*t for t in (2,4,8,25,50,60)]+[[2]+[50]*25,[8]*4+[60]*30]
        fixtures=[(7,-7,1),(399,-399,-100),(400,-400,400),(1000,-1000,32767),
                  (-32768,1,-1),(0,0,0)]
        for values in fixtures:
            for seq in seqs:
                self.setup(values);elapsed=Fraction(0)
                rate=tuple(max(-400,min(400,v)) for v in values)
                for t in seq:
                    p=self.step(t);elapsed+=Fraction(1,t)
                    assert all(abs(x-elapsed*v)<=1 for x,v in zip(p,rate)),(values,t,p,elapsed)
                before=p;fracs=self.c.read(self.a.sym('dt_drift_frac'),96)
                for t in seq:assert self.step(t,(0,0,0))==before
                assert self.c.read(self.a.sym('dt_drift_frac'),96)==fracs
                for t in seq:p=self.step(t,tuple(-v for v in rate))
                assert p==(0,0,0),(values,seq[0],p)
        # A normal polar trajectory plus drift equals their separately integrated
        # components within the one-unit carry bound on each axis.
        for t in (8,25,50,60):
            results=[]
            for values in ((0,0,0),(7,-7,-100)):
                self.setup(values);self.c.set(19696,300);self.c.set(18164,8192)
                for _ in range(t):p=self.step(t)
                results.append(p)
            assert all(abs(b-a-v)<=1 for a,b,v in zip(*results,(7,-7,-100))),results
        print('FR-18 all axes, clamp boundaries, tiny signed rates, zero/reversal, variable T and polar superposition pass')
    def writers(self):
        c=self.c
        for heading in (0,16384,32768):
            for formation in range(4):
                out=[]
                for t in (2,8,25,50,60):
                    self.setup((0,0,0));c.set(11700,t);c.set(11710,1)
                    c.set(19423,0,'B');c.set(19439,0,'B')
                    c.set(19454,formation,'B');c.set(19455,formation,'B');c.set(18162,heading,'H')
                    for off,origin,delta in zip(self.positions,self.origins,(1600,-3200,800)):
                        c.set(off,origin+delta,'i')
                    c.run(c.bob+0x270ec)
                    out.append(tuple(c.get(off+2) for off in self.rates))
                assert all(v==out[0] for v in out),out
        # Perturbing leader coordinates by the native correction scales changes
        # precisely one component; this identifies these terms as formation error.
        base=out[-1]
        for axis,scale in enumerate((16,16,8)):
            for off,origin,delta in zip(self.positions,self.origins,(1600,-3200,800)):
                c.set(off,origin+delta,'i')
            c.set(self.positions[axis],c.get(self.positions[axis],'i')+scale,'i')
            c.run(c.bob+0x270ec)
            v=tuple(c.get(off+2) for off in self.rates)
            assert v==tuple(x+(i==axis) for i,x in enumerate(base)),(axis,base,v)
        print('FR-18 native formation writer agrees across T; XYZ position-error scales verified')
    def resets(self):
        a,c=self.a,self.c
        for slot in range(16):
            self.setup((7,-7,-100),slot)
            for _ in range(50):p=self.step(50)
            assert all(abs(x-y)<=1 for x,y in zip(p,(7,-7,-100)))
            c.write(a.sym('dt_drift_frac'),b'\xff'*96)
            c.reg(13,slot);c.run(a.sym('dt_plane_generation'))
            for axis in range(3):
                b=c.read(a.sym('dt_drift_frac')+axis*32,32)
                assert b==b'\xff'*(slot*2)+bytes(2)+b'\xff'*(30-slot*2)
        c.run(a.sym('dt_effect_init'));assert c.read(a.sym('dt_drift_frac'),96)==bytes(96)
        a.options()
        print('FR-18 all aircraft slots, reuse, flight reset and original gate pass')
    def run(self):self.baseline();self.motion();self.writers();self.resets()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    DriftChecks(p.parse_args()).run()
