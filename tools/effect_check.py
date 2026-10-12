#!/usr/bin/env python3
"""FR-03: native effect transitions versus one native update per 1/8 second.

Same local dump/base/slave/listing inputs as input_combat_check.py. Restores the
native fragment emission routine stubbed by the combat harness. Sound stays
stubbed; animation tables, constructors, RNG and cleanup execute natively.
"""
import argparse
import hashlib
from fractions import Fraction
from input_combat_check import Checks, Q, u

class EffectChecks:
    def __init__(self,args):
        self.a=Checks(args);self.c=self.a.c
        c=self.c
        self.patch=c.read(c.bob+0x176a2,6)
        c.write(c.bob+0x1d63e,self.a.orig[0x1d63e:0x1d640])
        self.enable(True)

    def enable(self,on):
        c=self.c
        c.write(c.bob+0x176a2,self.patch if on else self.a.orig[0x176a2:0x176a8])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))

    def setup(self,kind,phase):
        a,c=self.a,self.c
        a.reset()
        c.write(c.a4+13394,bytes(152))
        c.write(c.a4+21254,bytes(152*7))
        c.write(c.a4+24756,bytes(70*8))
        c.set(24756,0xa1,'B')  # independent low-nibble terrain effect cycle
        c.set(13394,4,'B');c.set(13562,kind,'B')
        c.set(15506,100000,'i');c.set(19694,100)
        c.set(11700,8);c.set(11698,8)
        c.set(21254+3,phase,'B')
        c.set(21254+4,phase,'B')
        c.set(11702,1);c.set(11704,1)
        c.run(a.sym('dt_effect_init'))

    def state(self):
        c=self.c
        b=bytearray(c.read(c.a4-0x7ffe,0xfa14))
        b[0x7ffe+11698:0x7ffe+11706]=bytes(8)
        return hashlib.sha256(b).digest()

    def run(self):
        c,a=self.c,self.a
        schedules=[[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4],[50,16,50,16]]
        emitted=False;stopped=False;removed=False
        for kind,phase in [(1,0),(1,9),(2,9),(1,49),(2,49),(13,0),(14,14),(14,51),(4,0)]:
            self.enable(False);self.setup(kind,phase)
            reference=[self.state()]
            for tick in range(1,137):
                c.set(11704,1)
                c.run(c.bob+0x176a2)
                reference.append(self.state())
                emitted |= any(c.get(13394+n,'B') for n in range(100,112))
                stopped |= c.get(19694)==0
                removed |= c.get(13394,'B')==0
            self.enable(True)
            for schedule in schedules:
                self.setup(kind,phase);elapsed=Fraction(0)
                for i in range(3000):
                    t=schedule[i%len(schedule)]
                    c.set(11700,t);c.set(11698,t)
                    c.run(c.bob+0x176a2);elapsed+=Fraction(1,t)
                    tick=int(elapsed*8)
                    assert self.state()==reference[tick], (kind,phase,schedule,elapsed,tick)
                    assert c.get(11700)==t
                    if elapsed>=16:break
                else:raise AssertionError('frame bound')
            print('native animation/emission/cleanup equivalence:',kind,phase)
        assert emitted and stopped and removed, (emitted,stopped,removed)
        # Independently check 8Hz and preserved high nibble of the secondary loop.
        self.setup(0,0);c.set(13394,0,'B')
        for _ in range(7):
            c.set(11700,60);c.run(c.bob+0x176a2)
        assert c.get(24756,'B')==0xa1
        c.run(c.bob+0x176a2)
        assert c.get(24756,'B')==0xa2
        c.write(a.sym('dt_effect_time'),b'\xff'*4)
        c.set(11702,17);c.run(a.sym('dt_effect_init'))
        assert c.read(a.sym('dt_effect_time'),4)==bytes(4)
        assert c.get(11704)==17
        a.options()
        print('8Hz cadence, native emissions/stops/removals, secondary effects and reset passed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    EffectChecks(p.parse_args()).run()
