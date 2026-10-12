#!/usr/bin/env python3
"""FR-04 native clock/daylight regression; standard dump/base/slave/listing inputs."""
import argparse
from fractions import Fraction
from input_combat_check import Checks, Q, u

class ClockChecks:
    def __init__(self,args):
        self.a=Checks(args);self.c=self.a.c
        self.patch=self.c.read(self.c.bob+0x14e5e,8)
    def enable(self,on):
        c=self.c;c.write(c.bob+0x14e5e,self.patch if on else self.a.orig[0x14e5e:0x14e66])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def setup(self,date):
        self.a.reset()
        for off,val in zip((11662,11663,11664),date):self.c.set(off,val,'B')
        self.c.set(11665,0,'B')
    def run(self):
        c,a=self.c,self.a
        for schedule in [[n] for n in (2,4,8,25,50,60)]+[[8,50,25,60,4],[50,16,50,16]]:
            self.setup((23,59,30));elapsed=Fraction(0)
            for i in range(20000):
                t=schedule[i%len(schedule)];c.set(11700,t)
                c.run(c.bob+0x14e5a);elapsed+=Fraction(1,t)
                seconds=(23*3600+59*60+30+int(elapsed))%86400
                actual=c.get(11662,'B')*3600+c.get(11663,'B')*60+c.get(11664,'B')
                assert actual==seconds,(schedule,elapsed,actual,seconds)
                if elapsed>=120:break
            print('elapsed time / midnight rollover:',schedule)
        # Hour-long run and hour/minute rollovers with accelerated divisor.
        self.setup((5,59,59));c.set(11700,2)
        for _ in range(7200):c.run(c.bob+0x14e5a)
        assert tuple(c.get(o,'B') for o in (11662,11663,11664))==(6,59,59)
        for date in ((5,59,59),(20,59,59),(23,59,59),(12,29,59)):
            states=[]
            for enabled in (False,True):
                self.enable(enabled);self.setup(date);c.set(11700,8)
                if not enabled:
                    c.set(11665,1,'B');c.run(c.bob+0x14e5a)
                for _ in range(8 if enabled else 1):c.run(c.bob+0x14e5a)
                # All native daylight fields, sun coordinates and date bytes.
                states.append(c.read(c.a4+11642,23)+c.read(c.a4+11666,1))
            assert states[0]==states[1],date
        c.write(a.sym('dt_world_time'),b'\xff'*4)
        c.set(11698,8);c.run(a.sym('dt_flight'))
        assert c.read(a.sym('dt_world_time'),4)==bytes(4)
        a.options()
        print('hour-long run, daylight boundaries, native rollover and flight reset passed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    ClockChecks(p.parse_args()).run()
