#!/usr/bin/env python3
"""FR-02 native scheduler and controlled mission-group placement regression.

Same local dump/base/slave/listing inputs as input_combat_check.py. Uses original
eligibility and aircraft creation, with sound disabled by the common harness.
"""
import argparse
from fractions import Fraction
from input_combat_check import Checks, Q, u

class GroupChecks:
    def __init__(self,args):
        self.a=Checks(args);self.c=self.a.c
        self.patch=self.c.read(self.c.bob+0xbf96,6)

    def enable(self,on):
        c=self.c
        c.write(c.bob+0xbf96,self.patch if on else self.a.orig[0xbf96:0xbf9c])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))

    def setup(self,mission=False,blocked=False):
        a,c=self.a,self.c
        a.reset();c.set(24450,0,'B')
        c.write(c.a4+24440,bytes(10))
        if mission:
            c.write(c.a4+13394,bytes(152))
            c.set(13318,0)
            side=c.get(-29643+4*32,'B')
            c.set(13394,4,'B');c.set(13866,side^1,'B')
            for n in range(1,16): c.set(13866+n,side,'B')
            c.set(24440,2,'B')
            c.set(24180,1,'B');c.set(24181,4,'B')
            c.set(24203,255,'B')
            c.set(24464,7,'B')
            c.set(14018,255,'B')
            if blocked:
                c.set(13395,4,'B');c.set(14019,0,'B')
                c.set(20471,254,'B');c.set(19423,255,'B')
        c.set(11700,50)

    def run(self):
        a,c=self.a,self.c
        for schedule in [[t] for t in (2,4,8,25,50,51,52,60)]+[[8,50,25,60,4],[50,16,50,16]]:
            self.setup()
            c.run(c.bob+0xbf8e)
            assert c.get(24450,'B')==1
            assert int.from_bytes(c.read(a.sym('dt_group_left'),4),'big')==5*2**24
            elapsed=Fraction(0);events=[]
            for i in range(10000):
                t=schedule[i%len(schedule)];c.set(11700,t)
                old=int.from_bytes(c.read(a.sym('dt_group_left'),4),'big')
                c.run(c.bob+0xbf8e);elapsed+=Fraction(1,t)
                new=int.from_bytes(c.read(a.sym('dt_group_left'),4),'big')
                if new>old:
                    due=5*(len(events)+1)
                    assert elapsed-Fraction(1,t)<due
                    assert elapsed+Fraction(i+1,2**24)>=due
                    events.append(elapsed)
                    if len(events)==12:break
            assert len(events)==12
            # Native new-flight reset wins over any stale private countdown.
            c.set(24450,0,'B');c.run(c.bob+0xbf8e)
            assert int.from_bytes(c.read(a.sym('dt_group_left'),4),'big')==5*2**24
            print('five-second cadence/reset passed:',schedule)

        # Mission-level routine integration: actual eligibility, placement and
        # native aircraft constructor must give the same state as an original scan.
        for blocked in (False,True):
            results=[]
            for on in (False,True):
                self.enable(on);self.setup(mission=True,blocked=blocked)
                c.run(c.bob+0xbf8e)
                state=bytearray(c.read(c.a4-0x7ffe,0xfa14))
                state[0x7ffe+24450]=0 # deliberately replaced countdown
                results.append(state)
                assert c.get(24440,'B')==(2 if blocked else 1)
                assert c.get(24464,'B')==(7 if blocked else 0)
                if not blocked:
                    assert any(c.get(13394+n,'B')==4 and c.get(14018+n,'B')==0 for n in range(1,16))
            assert results[0]==results[1], 'native mission state changed'
            print('native mission eligibility/placement preserved:', 'blocked' if blocked else 'eligible')
        # Keep the eligible mission live across the new timer interval.
        self.setup(mission=True)
        c.run(c.bob+0xbf8e)
        # Mark the new group as ineligible; it must not be processed at expiry.
        c.set(19423,255,'B');c.set(20471,254,'B')
        for _ in range(250): c.run(c.bob+0xbf8e)
        assert c.get(24440,'B')==1
        print('pending mission group remains gated at next scheduled scan')
        self.setup(mission=True)
        c.run(c.bob+0xbf8e)
        for n in range(1,16): c.set(13394+n,0,'B')
        for _ in range(249): c.run(c.bob+0xbf8e)
        assert c.get(24440,'B')==1
        c.run(c.bob+0xbf8e)
        assert c.get(24440,'B')==0
        assert any(c.get(13394+n,'B')==4 and c.get(14018+n,'B')==0 for n in range(1,16))
        print('eligible replacement group created at five seconds, never early')
        a.options()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    GroupChecks(p.parse_args()).run()
