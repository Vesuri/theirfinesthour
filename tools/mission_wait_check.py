#!/usr/bin/env python3
"""FR-20 native mission/transition waits and clock-domain regressions."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,P,Q,I,C,u,PATCHES

class WaitChecks:
    specs=((0xc2d0,11218,40,11698,0xc310),(0xc2d0,11216,40,11698,0xc342),
           (0x12984,24684,180,11700,0x129a6),(0x12dba,30646,40,11700,0x12ddc))
    def __init__(self,args):
        self.a=Checks(args);self.c=self.a.c;self.events=[];self.now=Fraction(0)
        def observe(h,addr,size,user):self.events.append((addr-self.c.bob,self.now))
        self.callback=C.CFUNCTYPE(None,P,Q,I,P)(observe);self.hooks=[]
        u.uc_hook_add.argtypes=[P,C.POINTER(Q),I,P,P,Q,Q];u.uc_hook_add.restype=I
        for off in (0xc310,0xc342,0x129a6,0x12ddc,0x12e24):
            hook=Q();self.c.ck(u.uc_hook_add(self.c.h,C.byref(hook),4,self.callback,None,self.c.bob+off,self.c.bob+off));self.hooks.append(hook)
    def enable(self,on):
        a,c=self.a,self.c
        for off,n,name,kind in PATCHES:
            if name.startswith('dt_wait_'):
                c.write(c.bob+off,(b'\x4e\xb9' if kind=='PS' else b'\x4e\xf9')+struct.pack('>I',a.sym(name))+b'\x4e\x71'*((n-6)//2) if on else a.orig[off:off+n])
        c.write(c.bob+0xc31e,b'\x4e\x71'*6 if on else a.orig[0xc31e:0xc32a])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def setup(self,index):
        a,c=self.a,self.c;a.reset();self.events=[];self.now=Fraction(0)
        c.write(c.a4+13394,bytes(152));c.set(13318,0);c.set(14018,0,'B');c.set(24186,255,'B')
        c.set(11214,46 if index==0 else 0,'B');c.set(11216,0);c.set(11218,0)
        c.set(24684,0);c.set(30646,0);c.set(30644,3,'B');c.set(26004,0);c.set(13322,0,'B');c.set(22386,0,'B')
        c.set(11698,8);c.set(11700,8)
        # Isolate UI/audio and the navigation predicate, retaining native decisions.
        c.write(c.a4-32244,b'\x4e\x75')
        c.write(c.a4-32250,b'\x70\x00\x4e\x75')
        c.write(c.a4-32448,b'\x4e\x75')
    def call(self,index):self.c.run(self.c.bob+self.specs[index][0],args=b'\x00\x01')
    def due(self,index):return [t for off,t in self.events if off==self.specs[index][4]]
    def baseline(self):
        self.enable(False)
        for i,(_,marker,period,clock,_) in enumerate(self.specs):
            self.setup(i);self.call(i);self.c.set(clock,50)
            for frame in range(period*8+2):
                self.now+=Fraction(1,50);self.call(i)
                if len(self.due(i))==2:break
            assert self.due(i)[1]==Fraction(period*8+1,50),(i,self.due(i))
        self.enable(True)
        print('FR-20 native changing-rate waits expire at 6.42/28.82 seconds instead of 40/180')
    def cadence(self):
        for i,(_,marker,period,clock,_) in enumerate(self.specs):
            for schedule in ([2],[8],[25],[50],[60],[8,50,25,60,4]):
                self.setup(i);self.call(i)
                for frame in range(period*2*max(schedule)+10):
                    t=schedule[frame%len(schedule)];self.c.set(clock,t)
                    # Deliberately unrelated other clock, including accelerated world time.
                    self.c.set(11700 if clock==11698 else 11698,2 if clock==11698 else 60)
                    self.now+=Fraction(1,t);self.call(i)
                    if len(self.due(i))==3:break
                times=self.due(i);assert len(times)==3,(i,schedule,times)
                for n,when in enumerate(times):
                    assert Fraction(n*period)-Fraction(1,1000)<=when<=n*period+max(Fraction(1,t) for t in schedule),(i,schedule,times)
                # Native zero is an explicit rearm, independent of private remainder.
                self.c.set(marker,0);before=len(times);self.call(i)
                assert len(self.due(i))==before+1
            print('FR-20 steady/changing clock and native rearm pass:',i)
    def gates(self):
        a,c=self.a,self.c
        for off,fmt in ((26004,'h'),(13322,'B')):
            self.setup(0);self.call(0);left=c.read(a.sym('dt_wait_left'),4);c.set(off,1,fmt)
            for _ in range(100):self.call(0)
            assert c.read(a.sym('dt_wait_left'),4)==left and len(self.due(0))==1
            c.set(off,0,fmt);self.call(0);assert c.read(a.sym('dt_wait_left'),4)!=left
        self.setup(3);c.run(a.sym('dt_wait_initial'));left=c.read(a.sym('dt_wait_left')+12,4)
        assert int.from_bytes(left,'big')==60<<24
        c.set(26004,1)
        for _ in range(100):self.call(3)
        assert c.read(a.sym('dt_wait_left')+12,4)==left
        c.set(26004,0);c.set(11700,2)
        for n in range(1,361):
            self.now=Fraction(n,2);self.call(3)
        assert self.due(3)==[60,100,140,180],self.due(3)
        assert c.get(30644,'B')==0 and [t for off,t in self.events if off==0x12e24]==[180]
        # Post-deadline gates consume the opportunity; they do not pause the timer.
        for field,value,fmt in ((13322,1,'B'),(22386,5,'B')):
            self.setup(3);c.set(field,value,fmt);self.call(3)
            assert len(self.due(3))==1 and c.get(30644,'B')==3
            c.set(field,0,fmt);self.call(3);assert c.get(30644,'B')==3
        self.setup(3);c.write(c.a4-32250,b'\x70\x01\x4e\x75')
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.a4-32768),Q(c.a4)))
        self.call(3)
        assert c.get(30644,'B')==3
        # Report refresh continues when its downstream radio/record gate is closed.
        self.setup(2);c.set(26004,1);c.write(c.a4+20726,b'\xff'*16);self.call(2)
        assert c.read(c.a4+20726,16)==bytes(16)
        c.write(a.sym('dt_wait_left'),b'\xff'*16);c.run(a.sym('dt_flight'))
        assert c.read(a.sym('dt_wait_left'),16)==bytes(16)
        a.options()
        print('FR-20 native eligibility, 60s initial wait, reminder/transition sequence and flight reset pass')
    def native_outcomes(self):
        c=self.c
        for i in range(4):
            for mode in (range(11) if i==1 else range(2)):
                outcomes=[]
                for enabled in (False,True):
                    self.enable(enabled);self.setup(i)
                    if i==1:c.set(24186,mode,'B')
                    if i==2 and mode:
                        # One moving friendly aircraft; native report data must survive.
                        c.set(13394,4,'B');c.set(19694,200);c.set(13866,0,'B');c.set(14018,1,'B')
                    if i==3:c.set(30644,mode,'B')
                    self.call(i)
                    data=bytearray(c.read(c.a4-0x7ffe,0xfa14))
                    for off in (11216,11218,24684,30646):data[off+0x7ffe:off+0x8000]=bytes(2)
                    outcomes.append(data)
                assert outcomes[0]==outcomes[1],('native due state changed',i,mode)
        print('FR-20 native mission conditions, contact-report updates and transition outcomes match due reference')
    def run(self):self.baseline();self.cadence();self.gates();self.native_outcomes()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');WaitChecks(p.parse_args()).run()
