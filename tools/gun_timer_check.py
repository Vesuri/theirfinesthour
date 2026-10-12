#!/usr/bin/env python3
"""FR-07 elapsed reload and native ammunition/burst regression."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks

class GunChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,ai=False):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152))
        c.write(c.a4+23586,bytes(80));c.write(c.a4+23890,bytes(16))
        c.set(13394,1,'B');c.set(13318,1 if ai else 0);c.set(13546,1,'B')
        c.set(11384,0,'B');c.set(22946,1000);c.set(22786,1,'B')
        for off,val,fmt in [(14290,10000000,'i'),(14898,10000000,'i'),(15506,50000,'i'),
                            (18162,0,'h'),(18466,16384,'h'),(18830,16384,'h'),(19694,0,'h')]:c.set(off,val,fmt)
        return c.get(22946)
    def step(self,t,held=True,clear=True):
        c=self.c;c.set(11700,t)
        if clear:c.write(c.a4+13394+52,bytes(48))
        if held:c.run(c.bob+0x1c876,args=struct.pack('>H',0))
        c.run(c.bob+0x1c5dc)
        return c.get(22946)
    def run(self):
        c,a=self.c,self.a;totals=[]
        for ai in (False,True):
            for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
                start=self.setup(ai)
                if ai:c.set(23586,1,'B');c.set(23666,27,'B')
                elapsed=Fraction(0);events=0;previous=start
                for frame in range(2000):
                    t=schedule[frame%len(schedule)]
                    if elapsed+Fraction(1,t)>9:break
                    now=self.step(t,not ai);elapsed+=Fraction(1,t)
                    used=previous-now
                    if used:events+=used
                    previous=now
                # Exact expected number of events in [0, elapsed), not rounded frames.
                expected=(elapsed*3).__ceil__()
                totals.append((ai,schedule,events,expected))
                assert events==expected,(totals[-1],elapsed) # native type-20 ammo cost
                if ai and elapsed==9:assert c.get(23666,'B')==0 and c.get(23586,'B')==2
        print('equal-time native ammunition and burst cadence:',totals)
        damages=[]
        for t in (2,4,8,25,50,60):
            self.setup();c.set(13395,4,'B');c.set(22707,0,'B');c.set(22588,0)
            for off,value in ((14294,10000000),(14902,10005000),(15510,50000)):c.set(off,value,'i')
            for off,value in ((18164,0),(18468,16384),(18832,16384),(19696,0),(19472,0),(19504,0),(19536,0)):c.set(off,value)
            for frame in range(t*4):
                self.step(t,frame<t*2,clear=False)
                c.run(c.bob+0x154b2)
                for slot in range(52,68):
                    if c.get(13394+slot,'B'):c.run(c.bob+0x1e3d6,args=struct.pack('>H',slot))
            damages.append(c.get(22588))
            assert c.get(22946)==994
        assert len(set(damages))==1 and damages[0]>0,damages
        print('six native fire events, resolved target damage:',damages)
        self.setup();self.step(50)
        for _ in range(100):self.step(50,False)
        before=c.get(22946);self.step(2)
        assert before-c.get(22946)==2,'idle credit or missing slow-frame catch-up'
        before=c.get(22946);self.step(50,False);assert c.get(22946)==before
        self.setup();c.set(22946,0)
        for t in (2,50,4,60):self.step(t)
        assert c.get(22946)==0
        self.setup();c.write(c.a4+13394+52,bytes([20])*16)
        self.step(2,clear=False);assert c.get(22946)==1000
        c.write(a.sym('dt_gun_left'),b'\xff'*320);c.write(a.sym('dt_gun_requests'),b'\xff'*80)
        for plane in range(16):c.reg(13,plane);c.run(a.sym('dt_gun_reset'))
        assert c.read(a.sym('dt_gun_left'),400)==bytes(400)
        a.options();print('release/repress, empty ammo, full pool, all-slot reset and original gate passed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    GunChecks(p.parse_args()).run()
