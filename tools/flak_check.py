#!/usr/bin/env python3
"""FR-06 native flak launch/outcome/delivery checks; standard capture inputs."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,Q,u

class FlakChecks:
    def __init__(self,args):
        self.a=Checks(args);self.c=self.a.c
        self.patches={o:self.c.read(self.c.bob+o,n) for o,n in [(0x1f77e,6),(0x1f7a8,8)]}
    def enable(self,on):
        c=self.c
        for o,data in self.patches.items():c.write(c.bob+o,data if on else self.a.orig[o:o+len(data)])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def launch(self,t,seed,target=0,previous=None):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152))
        c.set(11700,t);c.set(13318,0);c.set(-7828,seed,'H')
        for n,kind,cl,y,z in [(target,4,1,10000000,50000),(16,22,12,10100000,0)]:
            c.set(13394+n,kind,'B');c.set(13562+n,cl,'B')
            c.set(14290+4*n,10000000,'i');c.set(14898+4*n,y,'i');c.set(15506+4*n,z,'i')
        c.set(11968,0);c.set(11970,0);c.set(22586+target*2,0);c.set(22706+target,0,'B')
        if previous:c.write(a.sym('dt_velocity_t'),struct.pack('>H',previous))
        before=[]
        for off,v in zip((17378,17442,17506),(600,1200,-600)):
            c.set(off+target*4,v//(previous or t),'i');before.append(c.get(off+target*4,'i'))
        c.write(c.a4-32244,bytes.fromhex('4e75')) # radio only
        c.run(c.bob+0x1f77e,args=struct.pack('>HHH',16,target,0))
        assert c.get(11700)==t
        assert [c.get(off+target*4,'i') for off in (17378,17442,17506)]==before
        return (c.get(13394+112,'B'),c.get(20798+224),
                tuple(c.get(off+448,'i') for off in (14290,14898,15506)),c.get(-7828,'H'))
    def run(self):
        c,a=self.c,self.a;outcomes=set()
        for target in (0,1):
            for seed in range(12):
                self.enable(False);reference=self.launch(8,seed,target)
                self.enable(True)
                for t in (2,4,8,25,50,60):
                    got=self.launch(t,seed,target)
                    assert got==reference,(target,seed,t,reference,got)
                    outcomes.add(got[0])
                    assert self.launch(t,seed,target,previous=8)==reference
                assert int.from_bytes(c.read(a.sym('dt_flak_left'),4),'big')==reference[1]*8192
        print('native launch outcome, RNG, miss placement and jitter preserved at reference 8Hz:',outcomes)
        # Cover native delivery/miss branches explicitly, independent of chance.
        for kind in (34,35):
            for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
                self.launch(8,1234)
                c.set(13394+112,kind,'B');c.set(20470+112,0,'B')
                c.set(20742,5);c.set(21102+112,16,'B')
                c.write(a.sym('dt_flak_left'),struct.pack('>I',3*65536+16384))
                elapsed=Fraction(0)
                for i in range(500):
                    t=schedule[i%len(schedule)];c.set(11700,t)
                    c.run(c.bob+0x1fdb8);elapsed+=Fraction(1,t)
                    if c.get(13394+112,'B')!=kind:break
                assert elapsed+Fraction(i+1,65536)>=Fraction(13,4)
                assert elapsed-Fraction(1,t)<Fraction(13,4)
                assert c.get(13394+112,'B')==(36 if kind==34 else 0)
                damage=c.get(22586)
                assert (damage>0)==(kind==35),(kind,damage)
                for _ in range(3):c.run(c.bob+0x1fdb8)
                assert c.get(22586)==damage,'duplicate delayed damage'
        for stale in ('removed','reused'):
            self.launch(8,1234);c.set(13394+112,35,'B');c.set(20470+112,0,'B')
            c.set(20742,5);c.write(a.sym('dt_flak_left'),bytes(4))
            if stale=='removed':c.set(13394,0,'B')
            else:
                c.set(13394,0,'B');c.set(25990,0);c.set(24181,4,'B')
                c.run(c.bob+0xb29a,args=struct.pack('>H',0))
                assert c.get(13394,'B')==4
                assert c.read(a.sym('dt_plane_ids'),4)==struct.pack('>I',1)
                c.set(22586,0)
            c.run(c.bob+0x1fdb8)
            assert c.get(22586)==0 and c.get(13394+112,'B')==0
        self.launch(60,1);c.write(a.sym('dt_flak_left'),bytes(4))
        c.set(13394+112,34,'B');c.run(c.bob+0x1fdb8)
        assert c.get(13394+112,'B')==36,'zero-delay miss stuck'
        self.launch(60,1);c.set(13394+112,0,'B')
        for slot in range(112,124):
            index=slot-112
            c.write(a.sym('dt_flak_left')+index*4,b'\xff'*4)
            c.write(a.sym('dt_flak_generation')+index*4,b'\xff'*4)
            c.run(c.bob+0x1f77e,args=struct.pack('>HHH',16,0,0))
            assert c.get(13394+slot,'B') in (34,35)
            assert int.from_bytes(c.read(a.sym('dt_flak_left')+index*4,4),'big')==c.get(20798+slot*2,'H')*8192
            assert c.read(a.sym('dt_flak_generation')+index*4,4)==bytes(4)
        before=c.read(a.sym('dt_flak_left'),96)
        c.run(c.bob+0x1f77e,args=struct.pack('>HHH',16,0,0))
        assert c.read(a.sym('dt_flak_left'),96)==before
        assert c.get(11700)==60
        a.options()
        print('elapsed delivery, no repeat, removed/reused targets and zero delay passed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    FlakChecks(p.parse_args()).run()
