#!/usr/bin/env python3
"""FR-01 native constructors/movement checks; same inputs as bomb_check.py.

No rendering or world effect cadence is modelled. Compare complete trajectories
against fixed 64Hz motion, plus independent gravity, drag and lifetime checks.
"""
import argparse
import struct
from fractions import Fraction
from input_combat_check import Checks

class DebrisChecks:
    def __init__(self, args):
        self.a = Checks(args)
        self.c = self.a.c

    def setup(self, kind, altitude=100000, velocity=0, speed=100, slot=100):
        a,c=self.a,self.c
        a.reset()
        c.write(c.a4+13394, bytes(152))
        c.set(11700, 8)
        for off,val,fmt in [(13394,4,'B'),(13562,1,'B'),(15506,altitude,'i'),
                            (14290,10000000,'i'),(14898,10000000,'i'),
                            (19694,speed*2,'h'),(20030,velocity,'h')]:
            c.set(off,val,fmt)
        # Occupy preceding slots to exercise the entire pool and real allocator.
        for n in range(100,slot): c.set(13394+n,32,'B')
        c.write(a.sym('dt_debris_time'), b'\xff'*48)
        c.write(a.sym('dt_debris_grav'), b'\xff'*24)
        c.write(a.sym('dt_frac')+slot*6, b'\xff'*6)
        if kind==9:
            c.run(c.bob+0x1d670,args=struct.pack('>H',0))
        else:
            c.run(c.bob+0x1d588,args=struct.pack('>HHHHH',0,32,kind,0,0))
        assert c.get(13562+slot,'B')==kind
        assert c.read(a.sym('dt_debris_time')+(slot-100)*4,4)==bytes(4)
        assert c.read(a.sym('dt_debris_grav')+(slot-100)*2,2)==bytes(2)
        assert c.read(a.sym('dt_frac')+slot*6,6)==bytes(6)
        assert c.get(20798+slot*2)==(256 if kind==9 else 320)
        for n in range(12):
            if n!=slot-100:
                assert c.read(a.sym('dt_debris_time')+n*4,4)==b'\xff'*4
                assert c.read(a.sym('dt_debris_grav')+n*2,2)==b'\xff'*2
        c.write(c.a4+13394, bytes(100))
        for n in range(100,slot): c.set(13394+n,0,'B')
        # Controlled post-creation conditions; randomness is not under test.
        c.set(20030+slot*2,velocity)
        c.set(19694+slot*2,speed)
        c.set(18162+slot*2,8192)
        return slot

    def state(self,slot):
        c=self.c
        return tuple(c.get(off+slot*size,fmt) for off,size,fmt in
                     [(13394,1,'B'),(14290,4,'i'),(14898,4,'i'),(15506,4,'i'),
                      (19694,2,'h'),(20030,2,'h'),(20798,2,'h')])

    def step(self,rate):
        c=self.c
        c.set(11698,rate);c.set(11700,rate)
        c.run(c.bob+0x154b2)
        assert c.get(11700)==rate
        assert c.read(self.a.sym('dt_bomb_active'),2)==bytes(2)

    def run(self):
        schedules=[[n] for n in (2,4,8,25,50,60)]+[[8,50,25,60,4],[50,16,50,16]]
        for kind in (9,10,11):
            for scenario in (dict(),dict(altitude=1,velocity=-20),
                             dict(altitude=200,velocity=30),dict(speed=0)):
                slot=self.setup(kind,**scenario)
                reference=[self.state(slot)]
                for tick in range(1,897):
                    self.step(64)
                    reference.append(self.state(slot))
                    if reference[-1][0]==0 or reference[-1][3]==0: break
                terminal=len(reference)-1
                for schedule in schedules:
                    self.setup(kind,**scenario)
                    elapsed=Fraction(0)
                    for frame in range(2000):
                        rate=schedule[frame%len(schedule)]
                        self.step(rate);elapsed+=Fraction(1,rate)
                        tick=min(int(elapsed*64),terminal)
                        assert self.state(slot)==reference[tick], (kind,scenario,schedule,elapsed,self.state(slot),reference[tick])
                        if tick==terminal or elapsed>=12: break
                    else: raise AssertionError('never reached terminal state')
                print('trajectory/contact/expiry passed:',kind,scenario or 'level')
            slot=self.setup(kind)
            for _ in range(64): self.step(64)
            assert self.c.get(20030+slot*2)==-22
            if kind==9:
                for _ in range(191): self.step(64)
                assert self.c.get(13394+slot,'B')!=0
                self.step(64)
                assert self.c.get(13394+slot,'B')==0
            else:
                for _ in range(255): self.step(64)
                assert self.c.get(19694+slot*2)==100
                self.step(64)
                assert self.c.get(19694+slot*2)==99
                for _ in range(320): self.step(64)
                assert self.c.get(19694+slot*2)==98
            for slot in range(100,112): self.setup(kind,slot=slot)
        print('independent 22/s gravity, 4s expiry, 5s drag and all constructor slot resets passed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    DebrisChecks(p.parse_args()).run()
