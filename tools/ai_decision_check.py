#!/usr/bin/env python3
"""FR-12 native decision opportunities, skill periods and gunner target refresh."""
import argparse,ctypes as C,struct
from fractions import Fraction
from input_combat_check import Checks,u,P,Q,I

class DecisionChecks:
    def __init__(self,args):
        self.a=Checks(args);self.c=self.a.c;self.calls=[];self.gunners=0;self.random=0
        def observe(handle,address,size,user):
            c=self.c
            if address==c.bob+0x22140:self.calls.append(c.get(11706))
            elif address==c.bob+0x22ec2:self.gunners+=1
            else:self.random+=1
        self.callback=C.CFUNCTYPE(None,P,Q,I,P)(observe);self.hooks=[]
        u.uc_hook_add.argtypes=[P,C.POINTER(Q),I,P,P,Q,Q];u.uc_hook_add.restype=I
        for off in (0x22140,0x22ec2,0x2915c):
            hook=Q();self.c.ck(u.uc_hook_add(self.c.h,C.byref(hook),4,self.callback,None,self.c.bob+off,self.c.bob+off));self.hooks.append(hook)
    def setup(self,t,script=0):
        a,c=self.a,self.c;a.reset();self.calls=[];self.gunners=0;self.random=0
        c.write(a.sym('dt_velocity_t'),struct.pack('>H',c.get(11700))) # captured movement rate
        c.write(c.a4+13394,bytes(152));c.set(11700,t);c.set(11706,0)
        for slot,skill in enumerate((0,0x4000,0x8000,0xc000)):
            c.set(13394+slot,4,'B');c.set(13562+slot,1,'B');c.set(13546+slot,1,'B')
            c.set(22706+slot,0,'B');c.set(22586+slot*2,0);c.set(22626+slot*2,100)
            c.set(14066+slot*2,skill,'H');c.set(20434+slot,script,'B')
            c.set(20470+slot,255,'B');c.set(20622+slot,5,'B')
            c.reg(6,0x1800000);c.write(0x1800000-2,struct.pack('>H',skill))
            c.write(0x1800000-3,bytes([max(1,[2*t,t,t//2,t//3][slot])]))
            c.reg(9,slot);c.reg(1,c.a4+20398);c.run(a.sym('dt_ai_skill'))
            c.run(c.bob+0x21872,args=struct.pack('>H',slot))
        c.set(13332,0,'B');c.set(13322,0,'B');c.set(-7828,1234,'H')
    def run(self):
        a,c=self.a,self.c
        patches={off:c.read(c.bob+off,6) for off in (0x22090,0x22eaa)}
        for off in patches:c.write(c.bob+off,a.orig[off:off+6])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        original=[]
        for t in (8,50):
            self.setup(t)
            for _ in range(t*24):c.run(c.bob+0x22090);c.run(c.bob+0x22eaa)
            original.append(([self.calls.count(i) for i in range(4)],self.gunners))
        assert original[0]!=original[1],original
        print('original equal-time decision/gunner counts differ:',original)
        for off,data in patches.items():c.write(c.bob+off,data)
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        # Real instruction hooks only observe calls; native bodies run unchanged.
        periods=[Fraction(2),Fraction(1),Fraction(1,2),Fraction(1,3)]
        for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
            self.setup(schedule[0]);elapsed=Fraction(0)
            for frame in range(2000):
                t=schedule[frame%len(schedule)]
                if elapsed+Fraction(1,t)>24:break
                c.set(11700,t);c.run(c.bob+0x22090);elapsed+=Fraction(1,t)
                expected=sorted((Fraction(2)+i*p,slot) for slot,p in enumerate(periods) for i in range(72) if Fraction(2)+i*p<elapsed)
                assert self.calls==[slot for _,slot in expected],(schedule,frame,len(self.calls),len(expected),self.calls[-12:],[s for _,s in expected[-12:]])
                assert c.get(11700)==t
            print('native skill decision ordering:',schedule,[self.calls.count(i) for i in range(4)])
        # Inactive/non-aircraft/disabled objects cannot consume decision opportunities.
        self.setup(50);c.set(13394,0,'B');c.set(22707,1,'B');c.set(13564,12,'B')
        for _ in range(250):c.run(c.bob+0x22090)
        assert set(self.calls)=={3}
        # Constructor/script reset renews the complete two-second delay.
        c.run(c.bob+0x21872,args=struct.pack('>H',3));self.calls=[]
        for _ in range(100):c.run(c.bob+0x22090)
        assert not self.calls
        c.run(c.bob+0x22090);assert self.calls==[3]
        # Native player gunner refresh: one pass/second, including changing T.
        for schedule in [[t] for t in (2,8,25,50,60)]+[[8,50,25,60,4]]:
            self.setup(schedule[0]);elapsed=Fraction(0)
            for frame in range(1600):
                t=schedule[frame%len(schedule)]
                if elapsed+Fraction(1,t)>20:break
                c.set(11700,t);c.run(c.bob+0x22eaa);elapsed+=Fraction(1,t)
                assert self.gunners==elapsed.__ceil__(),(schedule,frame,self.gunners,elapsed)
            print('native player gunner refresh:',schedule,self.gunners)
        self.setup(50);c.set(13322,1,'B')
        for _ in range(80):c.run(c.bob+0x22eaa)
        assert self.gunners==0
        c.set(13322,0,'B');c.run(c.bob+0x22eaa);assert self.gunners==1
        c.write(a.sym('dt_player_ai_left'),b'\xff'*4);c.set(13332,0,'B')
        c.run(c.bob+0x22eaa);assert self.gunners==2
        for slot in range(16):
            c.run(c.bob+0x21872,args=struct.pack('>H',slot))
            assert c.read(a.sym('dt_ai_left')+4*slot,4)==bytes.fromhex('02000000')
        # Native combat script 6 executes real target selection and random choices.
        # Its frame-valued aim/script wait outputs are audited in FR-13/14.
        reference=None
        for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
            self.setup(schedule[0],6);elapsed=Fraction(0)
            for frame in range(1000):
                t=schedule[frame%len(schedule)]
                if elapsed+Fraction(1,t)>12:break
                c.set(11700,t);c.run(c.bob+0x22090);elapsed+=Fraction(1,t)
            result=(tuple(self.calls),self.random,c.get(-7828,'H'),c.read(c.a4+20470,4),c.read(c.a4+20622,4))
            if reference is None:reference=result
            assert result==reference,(schedule,result,reference)
            assert self.random>0 and c.read(c.a4+20470,4)!=b'\xff'*4
        print('native combat target choices, state transitions, decision order and 15 random draws agree')
        a.options()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    DecisionChecks(p.parse_args()).run()
