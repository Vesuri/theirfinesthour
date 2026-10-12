#!/usr/bin/env python3
"""FR-21 native message visibility, refresh, replacement and explicit clear."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,u,Q,PATCHES
class MessageChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def enable(self,on):
        a,c=self.a,self.c
        for off,n,name,kind in PATCHES:
            if name in ('dt_message_load','dt_message_age'):
                c.write(c.bob+off,(b'\x4e\xb9' if kind=='PS' else b'\x4e\xf9')+struct.pack('>I',a.sym(name))+b'\x4e\x71'*((n-6)//2) if on else a.orig[off:off+n])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def setup(self,manual=0,dual=0):
        a,c=self.a,self.c;a.reset();c.set(30640,0);c.set(30642,-1);c.set(11698,8);c.set(11700,8)
        c.set(13322,manual,'B');c.set(26004,0);c.set(-7960,dual)
        for off in (-32682,-32676,-32670,-32688,-32724,-31974):c.write(c.a4+off,b'\x4e\x75')
        c.write(0x1200,b'\x4e\x75');c.set(11762,0x1200,'I')
    def show(self,msg):self.c.run(self.c.bob+0x1c44a,args=struct.pack('>H',msg))
    def age(self):self.c.run(self.c.bob+0x1c52a)
    def baseline(self):
        self.enable(False);self.setup();self.show(13);self.c.set(11698,50)
        for _ in range(96):self.age()
        assert self.c.get(30642)==-1
        self.enable(True)
        print('FR-21 native 12s message expires in 1.92s after changing T=8 to T=50')
    def lifetime(self):
        c=self.c
        for schedule in ([2],[8],[25],[50],[60],[8,50,25,60,4]):
            for manual,dual in ((0,0),(1,0),(0,1)):
                self.setup(manual,dual);self.show(13);elapsed=Fraction(0)
                for frame in range(12*max(schedule)+1):
                    t=schedule[frame%len(schedule)];c.set(11698,t);c.set(11700,2)
                    elapsed+=Fraction(1,t);self.age()
                    if c.get(30642)==-1:break
                assert 12-Fraction(1,1000)<=elapsed<=12+max(Fraction(1,t) for t in schedule),(schedule,elapsed)
                assert c.get(30640)==0
                for _ in range(10):self.age()
                assert c.get(30642)==-1
        print('FR-21 native expiry, accelerated world time, manual station and dual buffers pass')
    def refresh(self):
        a,c=self.a,self.c
        for replacement in (13,14):
            self.setup();self.show(13);c.set(11698,50)
            for _ in range(500):self.age()
            self.show(replacement)
            for _ in range(599):self.age()
            assert c.get(30642)==replacement
            self.age();assert c.get(30642)==-1
        for msg in range(46,51):
            self.setup();self.show(msg);c.set(11698,2)
            for _ in range(24):self.age()
            assert c.get(30642) in (43,44),(msg,c.get(30642))
            assert c.get(30640)==2
            for _ in range(24):self.age()
            assert c.get(30642)==-1
        for msg in (13,46):
            self.setup();self.show(msg);c.set(30640,1);self.age()
            assert c.get(30642)==(-1 if msg==13 else 43+self.terrain())
        self.setup();self.show(13);c.set(30640,0)
        for _ in range(100):self.age()
        assert c.get(30642)==13
        c.run(a.sym('dt_effect_init'))
        assert c.get(30640)==0 and c.read(a.sym('dt_message_left'),4)==bytes(4)
        a.options()
        print('FR-21 same-message refresh, replacements, native follow-up messages, forced clear and flight reset pass')
    def terrain(self):
        self.c.run(self.c.bob+0x11ea2,args=struct.pack('>H',self.c.get(13318)))
        return self.c.reg(9)&65535
    def run(self):self.baseline();self.lifetime();self.refresh()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');MessageChecks(p.parse_args()).run()
