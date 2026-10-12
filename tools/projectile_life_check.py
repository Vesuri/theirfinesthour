#!/usr/bin/env python3
"""FR-05 native creation/movement/impact lifetime regression."""
import argparse
import struct
from fractions import Fraction
from input_combat_check import Checks

class LifeChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,slot=52):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152))
        c.set(13394,1,'B');c.set(13318,0 if slot<68 else 1)
        c.set(23746,slot%2,'B')
        for off,val,fmt in [(14290,10000000,'i'),(14898,10000000,'i'),(15506,50000,'i'),
                            (18162,0,'h'),(18466,16384,'h'),(18830,16384,'h'),
                            (19694,0,'h'),(11700,8,'h'),(11698,8,'h'),(30914,1,'h')]:c.set(off,val,fmt)
        for n in range(52,slot):c.set(13394+n,20,'B')
        c.write(a.sym('dt_shot_left'),b'\xff'*192)
        c.write(a.sym('dt_shot_pending'),b'\xff'*48)
        c.write(a.sym('dt_frac')+slot*6,b'\xff'*6)
        c.run(c.bob+0x1cad0,args=struct.pack('>HHH',0,0,2))
        assert c.get(13394+slot,'B')!=0
        assert c.read(a.sym('dt_shot_left')+(slot-52)*4,4)==struct.pack('>I',2*2**24)
        assert c.read(a.sym('dt_shot_pending')+slot-52,1)==b'\0'
        assert c.read(a.sym('dt_frac')+slot*6,6)==bytes(6)
        for n in range(152):
            if n!=slot:c.set(13394+n,0,'B')
        c.write(a.sym('dt_shot_pending'),bytes(48))
        return slot
    def run(self):
        c,a=self.c,self.a
        results=[]
        for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4],[50,16,50,16]]:
            slot=self.setup();start=c.get(14898+slot*4,'i');speed=c.get(19694+slot*2)
            elapsed=Fraction(0)
            for i in range(200):
                t=schedule[i%len(schedule)];c.set(11700,t);c.set(11698,t)
                c.run(c.bob+0x154b2);elapsed+=Fraction(1,t)
                left=int.from_bytes(c.read(a.sym('dt_shot_left'),4),'big')
                if not left:
                    assert c.get(13394+slot,'B')!=0,'final segment removed before collision'
                    assert elapsed+Fraction(i+1,2**24)>=2
                    assert elapsed-Fraction(1,t)<2
                c.run(c.bob+0x1d948)
                if not c.get(13394+slot,'B'):break
                assert left>0
            else:raise AssertionError('no expiry')
            distance=c.get(14898+slot*4,'i')-start
            expected=2*((speed*4660+128)//256)
            assert abs(distance-expected)<=2,(schedule,distance,expected)
            results.append(distance)
            print('two-second expiry/final distance:',schedule,distance)
        assert max(results)-min(results)<=2
        # A target reached only by the final segment must still receive damage.
        slot=self.setup();c.set(13395,4,'B');c.set(13563,2,'B')
        c.set(13866+slot,1,'B');c.set(13867,2,'B');c.set(22588,0);c.set(22707,0,'B')
        distance=2*((c.get(19694+slot*2)*4660+128)//256)
        for off in (14290,14898,15506):
            value=c.get(off+slot*4,'i')+(distance-50 if off==14898 else 0)
            c.set(off+4,value,'i')
        c.set(11700,50)
        for frame in range(100):
            c.run(c.bob+0x154b2);c.run(c.bob+0x1d948)
            if frame<99:assert c.get(22588)==0
        assert c.get(22588)>0 and c.get(13394+slot,'B')==0
        for slot in range(52,100):self.setup(slot)
        for ai_slot in (68,69):
            self.setup(ai_slot);c.set(11700,60)
            for step in range(120):
                c.run(c.bob+0x154b2);c.run(c.bob+0x1d948)
                assert bool(c.get(13394+ai_slot,'B'))==(step<119)
        # Execute the actual age-branch hook with a stand-in four-byte shift.
        slot=self.setup()
        c.write(0x1100,b'\x4e\xb9'+struct.pack('>I',a.sym('dt_shot_damage_age'))+bytes.fromhex('343c00014e75'))
        c.reg(13,slot) # D4
        for left,young in [(2*2**24,1),(2**24+1,1),(2**24,0),(2**24-1,0),(0,0)]:
            c.write(a.sym('dt_shot_left'),struct.pack('>I',left))
            c.reg(11,0) # D2
            c.run(0x1100)
            assert c.reg(11)==young,(left,c.reg(11))
        print('all 48 slot resets and one-second damage-age boundary passed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    LifeChecks(p.parse_args()).run()
