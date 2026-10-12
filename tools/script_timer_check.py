#!/usr/bin/env python3
"""FR-14 surface scheduling, script decision-count waits and taxi action."""
import argparse,ctypes as C,struct
from fractions import Fraction
from input_combat_check import Checks,u,P,Q,I

class ScriptChecks:
    def __init__(self,args):
        self.a=Checks(args);self.c=self.a.c;self.calls=[]
        def observe(handle,address,size,user):self.calls.append(self.c.get(11708))
        self.callback=C.CFUNCTYPE(None,P,Q,I,P)(observe);hook=Q()
        u.uc_hook_add.argtypes=[P,C.POINTER(Q),I,P,P,Q,Q];u.uc_hook_add.restype=I
        self.c.ck(u.uc_hook_add(self.c.h,C.byref(hook),4,self.callback,None,self.c.bob+0x21954,self.c.bob+0x21954));self.hook=hook
    def setup(self,t,script=0):
        a,c=self.a,self.c;a.reset();self.calls=[]
        c.write(a.sym('dt_velocity_t'),struct.pack('>H',c.get(11700)))
        c.set(11700,t);c.set(11708,16);c.set(-7828,1234,'H')
        c.write(c.a4+13394,bytes(152));c.set(13394,4,'B');c.set(13562,1,'B');c.set(13866,0,'B')
        c.set(14290,10000000,'i');c.set(14898,10000000,'i');c.set(15506,50000,'i')
        for slot in range(16,20):
            c.set(13394+slot,15,'B');c.set(13562+slot,12,'B');c.set(13866+slot,1,'B');c.set(22706+slot,0,'B')
            c.set(20434+slot,script,'B');c.set(20470+slot,0,'B')
            for off,v in ((14290,10020000),(14898,10020000),(15506,0)):c.set(off+slot*4,v,'i')
            c.run(c.bob+0x21872,args=struct.pack('>H',slot))
    def state(self):
        c=self.c;b=bytearray(c.read(c.a4-0x7ffe,0xfa14))
        # Native math library leaves its restored caller A5 in a scratch cell.
        for off,n in ((11698,6),(20414,20),(-10352,4)):
            b[0x7ffe+off:0x7ffe+off+n]=bytes(n)
        return bytes(b)
    def run(self):
        a,c=self.a,self.c
        patched=c.read(c.bob+0x218a2,6)
        c.write(c.bob+0x218a2,a.orig[0x218a2:0x218a8]);c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        old=[]
        for t in (2,50):
            self.setup(t)
            events=[]
            for frame in range(t*8):
                before=len(self.calls);c.run(c.bob+0x218a2)
                events.extend((Fraction(frame+1,t),slot) for slot in self.calls[before:])
            old.append(tuple(events))
        assert old[0]!=old[1],old
        print('native one-object service causes rate-dependent surface decisions:',[events[:4] for events in old])
        c.write(c.bob+0x218a2,patched);c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        for script in range(3):
            self.setup(8,script);reference=[self.state()]
            for _ in range(9):
                for slot in range(16,20):c.set(11708,slot);c.run(c.bob+0x21954)
                c.set(11708,16);reference.append(self.state())
            for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
                self.setup(schedule[0],script);elapsed=Fraction(0)
                for frame in range(1500):
                    t=schedule[frame%len(schedule)]
                    if elapsed+Fraction(1,t)>20:break
                    c.set(11700,t);c.run(c.bob+0x218a2);elapsed+=Fraction(1,t)
                    n=max(0,(elapsed/2).__ceil__()-1)
                    assert self.calls==list(range(16,20))*n,(script,schedule,frame,self.calls,n)
                    assert self.state()==reference[n],(script,schedule,frame,n,[(i-0x7ffe,x,y) for i,(x,y) in enumerate(zip(self.state(),reference[n])) if x!=y][:24])
            print('native surface script/state/RNG equivalence:',script)
        wait_patch=c.read(c.bob+0x24fee,6)
        c.write(c.bob+0x24fee,a.orig[0x24fee:0x24ff4]);c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        waits=[]
        for t in (2,8,50):
            self.setup(t);c.set(11710,0);c.set(20398,t//3,'B')
            c.run(c.bob+0x24fee,args=struct.pack('>H',15));waits.append(c.reg(9))
        assert len(set(waits))>1;print('native high-skill wait counts differ:',waits)
        c.write(c.bob+0x24fee,wait_patch);c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        turns={off:c.read(c.bob+off,6) for off in (0x267c6,0x267fe)}
        for off in turns:c.write(c.bob+off,a.orig[off:off+6])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        headings=[]
        for t in (8,50):
            self.setup(t);c.set(11710,0);c.set(19694,10);c.set(18162,32768,'H')
            c.run(c.bob+0x26696);headings.append(c.get(18162,'H'))
        assert headings[0]!=headings[1];print('native taxi correction differs:',headings)
        for off,data in turns.items():c.write(c.bob+off,data)
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        self.setup(50);c.set(13394+16,0,'B');c.set(22706+17,1,'B')
        c.write(a.sym('dt_ai_left'),b'\x11'*64)
        for _ in range(251):c.run(c.bob+0x218a2)
        assert self.calls==[18,19,18,19]
        assert c.read(a.sym('dt_ai_left'),64)==b'\x11'*64,'surface scheduler aged aircraft deadlines'
        for period,mult in ((0x2000000,1),(0x1000000,2),(0x800000,4),(5592406,6)):
            for t in (2,4,8,25,50,60):
                self.setup(t);c.set(11710,0);c.write(a.sym('dt_ai_period'),struct.pack('>I',period))
                for n in (2,3,4,5,6,8,10,12,15,20):
                    c.run(c.bob+0x24fee,args=struct.pack('>H',n));assert c.reg(9)==n*mult
                    c.set(20622,1,'B');c.set(20670,n*mult,'B');c.set(20686,255,'B')
                    for _ in range(n*mult):c.run(c.bob+0x222c2);assert c.reg(9)==0
                    c.run(c.bob+0x222c2);assert c.reg(9)==1
        print('every native wait argument fits its byte and expires at the same decision count')
        for state in range(34):
            for phase in (0,1,5):
                reference=None
                for t in (8,50):
                    self.setup(t);c.set(11710,0);c.set(30964,phase,'B');c.set(20686,phase,'B')
                    c.set(30960,1,'B');c.set(30974,2,'B');c.set(20470,1,'B');c.set(18146,1,'B')
                    c.set(13395,4,'B');c.set(13563,1,'B');c.set(14066,0xc000,'H')
                    c.write(a.sym('dt_ai_period'),struct.pack('>I',5592406))
                    entry=c.get(-11074+state*4,'I');c.run(entry)
                    result=(self.state(),c.reg(9) if state<17 else None) # initializers return void
                    if reference is None:reference=result
                    assert result==reference,(state,phase,hex(entry-c.bob),t)
            print('native action/initializer equality:',state)
        reference={};turns_seen=set()
        for t in (2,4,8,25,50,60):
            for speed in (10,20,30):
                for heading in (0,16384,32768,49152):
                    self.setup(t);c.set(11710,0);c.set(19694,speed);c.set(18162,heading,'H')
                    c.run(c.bob+0x26696)
                    state=self.state();key=(speed,heading)
                    turns_seen.add(((c.get(18162,'H')-heading+32768)%65536)-32768)
                    if t==2:reference[key]=state
                    assert state==reference[key],(t,key)
        assert {-1024,1024}<=turns_seen,turns_seen
        print('native taxi action: both turn directions and all speed branches agree')
        a.options()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    ScriptChecks(p.parse_args()).run()
