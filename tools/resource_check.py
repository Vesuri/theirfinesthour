#!/usr/bin/env python3
"""FR-27 resource audit: native speed fractions and engine damage event accounting."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks
class ResourceChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def speed(self):
        a,c=self.a,self.c
        for routine,sign in ((0x21394,1),(0x2140c,-1)):
            for rate in (1,7,31,255,1024):
                for schedule in ((2,),(8,),(25,),(50,),(60,),(8,50,25,60)):
                    a.reset();c.set(19696,10000);c.set(20000,0);elapsed=Fraction(0)
                    for i in range(120):
                        t=schedule[i%len(schedule)];elapsed+=Fraction(1,t)
                        expected=10000+sign*rate*elapsed
                        if not 0<=expected<32768:break
                        c.set(11700,t);c.run(c.bob+routine,args=struct.pack('>HH',1,rate))
                        assert abs(c.get(19696,'H')-expected)<1.01,(routine,rate,schedule,i,c.get(19696,'H'),expected)
        print('FR-27 existing native acceleration/deceleration fractions pass equal-time rate checks without another patch')
    def engine_events(self):
        a,c=self.a,self.c
        # Execute the damage subtraction branches with controlled hit strengths.
        # Event count, not render count, controls these engine-health resources.
        for branch,off in ((0x1e940,19598),(0x1e98a,19566)):
            results=[]
            for t in (2,8,25,50,60):
                a.reset();c.set(11700,t);c.set(off+2,65535,'H');c.reg(13,1);c.reg(6,0x1e00000)
                for hit in (1,3,7,19,100):
                    c.write(0x1e00000+10,struct.pack('>H',hit));c.run(c.bob+branch,stop=c.bob+0x1e9d2)
                results.append(c.get(off+2,'H'))
            assert results==[0]*5,results
        # Engine power is recomputed from health and throttle, not integrated wear.
        for health in (0,16384,32768,65535):
            results=[]
            for t in (2,8,25,50,60):
                a.reset();c.reg(13,1);c.reg(6,0x1e00000);c.set(30942,4,'B');c.set(13318,1)
                c.set(19568,health,'H');c.set(19600,health,'H');c.set(22444,50000,'H');c.set(11700,t)
                c.run(c.bob+0x20126,stop=c.bob+0x201c4)
                results.append((c.get(22404,'H'),c.get(19568,'H'),c.get(19600,'H')))
            assert len(set(results))==1 and results[0][1:]==(health,health),results
        print('FR-27 native engine-health event deductions, saturation and derived power are independent of update count')
    def run(self):self.speed();self.engine_events();self.a.options()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');ResourceChecks(p.parse_args()).run()
