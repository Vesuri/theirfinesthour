#!/usr/bin/env python3
"""FR-11 native surface damage at four-second elapsed-time deadlines."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,Q,u

class SurfaceDamageChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,damage,seed):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152))
        c.write(c.a4+21254,bytes(152*7))
        c.write(c.bob+0x1d63e,a.orig[0x1d63e:0x1d640])
        c.set(11712,0);c.set(-7828,seed,'H');c.set(11639,0,'B')
        for slot in range(16,20):
            c.set(13394+slot,15,'B');c.set(13562+slot,12,'B')
            c.set(22586+slot*2,damage);c.set(22626+slot*2,100)
            c.set(22666+slot*2,200);c.set(22706+slot,0,'B')
            c.set(18162+slot*2,16384);c.set(19694+slot*2,100)
            for off,v in [(14290,10000000),(14898,10000000),(15506,0)]:c.set(off+slot*4,v,'i')
        c.write(0x1100,bytes.fromhex('4e55fff82f044ef9')+struct.pack('>I',c.bob+0x1f514))
    def state(self):
        c=self.c;data=bytearray(c.read(c.a4-0x7ffe,0xfa14))
        for off in (11698,11700,11702,11712):data[0x7ffe+off:0x8000+off]=bytes(2)
        return bytes(data)
    def run(self):
        c=self.c;a=self.a
        patched=c.read(c.bob+0x1f4f6,6);legacy=[]
        c.write(c.bob+0x1f4f6,a.orig[0x1f4f6:0x1f4fc])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        for t in (2,50):
            self.setup(60,1234);c.set(11700,t)
            for _ in range(t*40):c.run(c.bob+0x1f4f6)
            legacy.append(self.state())
        assert legacy[0]!=legacy[1],'original damage cadence reproduction did not diverge'
        c.write(c.bob+0x1f4f6,patched)
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        print('original 40-second damage state/RNG differs at T=2/50')
        for damage,seed in ((0,1),(25,1234),(74,321),(75,1),(100,42)):
            self.setup(damage,seed);reference=[self.state()]
            for _ in range(10):c.run(0x1100);reference.append(self.state())
            if damage>=75:
                assert c.get(11639,'B')==4
                for slot in range(16,20):
                    assert c.get(22706+slot,'B')==1
                    assert c.get(21258+slot*7,'B')==22
            for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
                self.setup(damage,seed);elapsed=Fraction(0)
                for frame in range(2500):
                    t=schedule[frame%len(schedule)]
                    if elapsed+Fraction(1,t)>40:break
                    c.set(11700,t);c.run(c.bob+0x1f4f6);elapsed+=Fraction(1,t)
                    n=(elapsed/4).__ceil__()
                    assert self.state()==reference[n],(damage,seed,schedule,frame,n)
            print('native damage state/RNG sequence preserved:',damage,seed)
        self.setup(80,1);c.write(self.a.sym('dt_surface_damage_left'),b'\xff'*4)
        c.set(11712,0);c.set(11700,50);c.run(c.bob+0x1f4f6)
        assert c.get(22722,'B')==1 and c.get(11712)==1
        assert 0<int.from_bytes(c.read(self.a.sym('dt_surface_damage_left'),4),'big')<0x4000000
        # Damage threshold starts native sinking; FR-03 then owns its animation.
        times=[]
        for t in (2,4,8,25,50,60):
            self.setup(200,1);c.set(11700,t);c.set(11702,1)
            c.run(a.sym('dt_effect_init'));c.run(c.bob+0x1f4f6)
            # The first due pass disables; the next due pass starts state 22.
            c.run(0x1100)
            assert all(c.get(21258+slot*7,'B')==22 for slot in range(16,20))
            for frame in range(t*10):
                c.run(c.bob+0x176a2)
                if c.read(c.a4+13410,4)==bytes(4):break
            else:raise AssertionError('native ship sinking did not remove all four ships')
            times.append(Fraction(frame+1,t))
        assert max(times)-min(times)<=Fraction(1,2),times
        print('native sinking removes all four ships; observation times:',times)
        # Static land targets apply damage on impact, without a processing timer.
        for kind in (4,16,17,18,19):
            for direct in (0,1):
                reference=None
                for t in (2,8,25,50,60):
                    self.setup(0,1);c.set(11700,t);c.set(13318,0)
                    c.write(c.a4-32244,bytes.fromhex('4e75'))
                    c.set(13394+20,kind,'B');c.set(21102+20,0,'B')
                    c.write(c.a4+24756,bytes([0xa0,100])*4)
                    for component in range(4):
                        c.run(c.bob+0x10dac,args=struct.pack('>HHHH',0,component,20,direct))
                    state=self.state()
                    if reference is None:reference=state
                    assert state==reference,(kind,direct,t)
        print('native ground damage: aircraft and all four bomb types, direct and nearby impacts agree')
        self.a.options()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    SurfaceDamageChecks(p.parse_args()).run()
