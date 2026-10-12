#!/usr/bin/env python3
"""FR-10 native progressive aircraft damage at elapsed-time deadlines."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,Q,u

class AirDamageChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,damage,role,seed):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152))
        c.write(c.bob+0x1d63e,a.orig[0x1d63e:0x1d640]) # real smoke/fragment emission
        c.write(c.a4-32244,bytes.fromhex('4e75'))
        c.set(13318,0);c.set(13395,4,'B');c.set(13563,1,'B');c.set(13547,role,'B')
        c.set(14035,1,'B');c.set(14051,3,'B');c.set(22387,0,'B');c.set(22707,0,'B')
        c.set(22588,damage);c.set(22628,100);c.set(22668,80);c.set(11714,0)
        c.set(-7828,seed,'H');c.write(c.a4+23591,bytes([1])*5)
        for off,v in [(14294,10000000),(14902,10000000),(15510,50000)]:c.set(off,v,'i')
        c.write(0x1100,bytes.fromhex('4e55fff448e70c004ef9')+struct.pack('>I',c.bob+0x1ea6e))
    def state(self):
        c=self.c;data=bytearray(c.read(c.a4-0x7ffe,0xfa14))
        for off in (11698,11700,11702,11714):data[0x7ffe+off:0x8000+off]=bytes(2)
        return bytes(data)
    def run(self):
        c=self.c;a=self.a
        patched=c.read(c.bob+0x1ea46,6);legacy=[]
        c.write(c.bob+0x1ea46,a.orig[0x1ea46:0x1ea4c])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        for t in (8,50):
            self.setup(60,4,1234);c.set(11700,t)
            for _ in range(t*30):c.run(c.bob+0x1ea46)
            legacy.append(self.state())
        assert legacy[0]!=legacy[1],'original damage cadence reproduction did not diverge'
        c.write(c.bob+0x1ea46,patched)
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        print('original 30-second damage state/RNG differs at T=8/50')
        for damage,role,seed in ((25,4,1),(60,4,1234),(79,9,321),(80,9,1),(100,4,42)):
            self.setup(damage,role,seed);reference=[self.state()]
            for _ in range(90):c.run(0x1100);reference.append(self.state())
            if damage>=80:
                assert c.get(22707,'B')==1 and c.read(c.a4+23591,5)==bytes(5)
            if damage>=100:assert 29 in c.read(c.a4+13394+124,16),'missing native destruction effect'
            for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
                self.setup(damage,role,seed);elapsed=Fraction(0)
                for frame in range(2000):
                    t=schedule[frame%len(schedule)]
                    if elapsed+Fraction(1,t)>30:break
                    c.set(11700,t);c.run(c.bob+0x1ea46);elapsed+=Fraction(1,t)
                    n=(elapsed*3).__ceil__()
                    assert self.state()==reference[n],(damage,role,seed,schedule,frame,n)
            print('native damage state/RNG sequence preserved:',damage,role,seed)
        self.setup(80,9,1);c.write(self.a.sym('dt_air_damage_left'),b'\xff'*4)
        c.set(11714,0);c.set(11700,50);c.run(c.bob+0x1ea46)
        assert c.get(22707,'B')==1 and c.get(11714)==1
        assert 0<int.from_bytes(c.read(self.a.sym('dt_air_damage_left'),4),'big')<5592406
        self.a.options()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    AirDamageChecks(p.parse_args()).run()
