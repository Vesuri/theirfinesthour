#!/usr/bin/env python3
"""FR-13 native pursuit and gunner lead at a fixed reference timestep."""
import argparse,struct
from input_combat_check import Checks,Q,u

class AimChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,t,skill=0xc000,burst=0,distance=10000,previous=None,seed=1234,velocity=(6000,-3000,600),speed=300):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152));c.set(11700,t)
        c.set(13318,0);c.set(11710,0);c.set(11718,distance,'i');c.set(-7828,seed,'H')
        for slot in (0,1):
            c.set(13394+slot,4,'B');c.set(13562+slot,1,'B');c.set(13866+slot,slot,'B')
            c.set(19694+slot*2,speed);c.set(18162+slot*2,0)
            c.set(18466+slot*2,16384);c.set(18830+slot*2,16384);c.set(19198+slot*2,0)
            c.set(14290+slot*4,10000000,'i');c.set(14898+slot*4,10000000+slot*distance,'i');c.set(15506+slot*4,50000,'i')
        c.set(14066,skill,'H');c.set(20470,1,'B');c.set(23586,burst,'B');c.set(14130,skill,'H')
        c.set(22786,4,'B');c.set(22866,1,'B');c.set(23506,255,'B');c.set(13327,1,'B')
        if previous:c.write(a.sym('dt_velocity_t'),struct.pack('>H',previous))
        for off,v in zip((17378,17442,17506),velocity):
            c.set(off+4,int(v/(previous or t)),'i')
    def sample(self,entry,t,**kwargs):
        self.setup(t,**kwargs);c=self.c
        args=struct.pack('>H',1) if entry==0x26e46 else struct.pack('>HHH',0,1,0)
        before=[c.get(off+4,'i') for off in (17378,17442,17506)]
        c.run(c.bob+entry,args=args)
        assert c.get(11700)==t
        assert before==[c.get(off+4,'i') for off in (17378,17442,17506)]
        if entry==0x26e46:return tuple(c.get(off,'i') for off in (16114,16322,16530))
        return c.reg(9),c.get(30918,'H'),c.get(30920,'H'),c.get(-7828,'H')
    def run(self):
        a,c=self.a,self.c
        patches={off:c.read(c.bob+off,6) for off in (0x26e46,0x1cf98)}
        def enable(on):
            for off,data in patches.items():c.write(c.bob+off,data if on else a.orig[off:off+6])
            c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        for entry in patches:
            enable(False);legacy=[self.sample(entry,t) for t in (8,50)]
            assert legacy[0]!=legacy[1],(entry,legacy)
            print('native aiming divergence:',hex(entry),legacy)
            for skill in (0,0x4000,0xa000,0xc000):
                for burst in (0,1):
                    for distance in (1000,8191,8192,10000,16384,16385,40000):
                        for velocity,speed in (((6000,-3000,600),300),((-6000,3000,-6000),300),((0,0,0),0)):
                            kw=dict(skill=skill,burst=burst,distance=distance,velocity=velocity,speed=speed)
                            enable(False);reference=self.sample(entry,8,**kw)
                            enable(True)
                            for t in (2,4,8,25,50,60):
                                assert self.sample(entry,t,**kw)==reference,(entry,t,kw)
                                previous={2:50,4:25,8:60,25:4,50:8,60:2}[t]
                                assert self.sample(entry,t,previous=previous,**kw)==reference,(entry,t,previous,kw)
            print('native reference lead, skill/RNG/arc result, range branches and rate changes:',hex(entry))
        # Real projectile creation consumes the same corrected gun angles.
        reference=None
        for t in (2,8,25,50,60):
            aim=self.sample(0x1cf98,t);assert aim[0]==1
            c.set(22946,1000);c.set(11384,0,'B')
            c.run(c.bob+0x1c8a8,args=struct.pack('>HH',0,0))
            shots=tuple((slot,c.get(13394+slot,'B'),*(c.get(off+slot*4,'i') for off in (14290,14898,15506)),*(c.get(off+slot*2,'H') for off in (18162,18830,19694))) for slot in range(52,100) if c.get(13394+slot,'B'))
            assert shots and c.get(22946)<1000
            result=(shots,c.get(22946),c.get(-7828,'H'))
            if reference is None:reference=result
            assert result==reference,(t,result,reference)
        print('native projectile launch states and ammunition agree after corrected aim')
        damages=[]
        for t in (2,4,8,25,50,60):
            assert self.sample(0x1cf98,t,distance=5000,velocity=(0,0,0),speed=0)[0]==1
            c.write(c.a4+23586,bytes(80));c.write(c.a4+23890,bytes(16))
            c.set(23586,1,'B');c.set(23666,6,'B');c.set(22946,1000);c.set(11384,0,'B')
            c.set(22588,0);c.set(22707,0,'B')
            for slot in (0,1):
                for off in (19470,19502,19534):c.set(off+2*slot,0)
            for _ in range(t*4):
                c.run(c.bob+0x1c5dc);c.run(c.bob+0x154b2)
                for slot in range(52,100):
                    if c.get(13394+slot,'B'):c.run(c.bob+0x1e3d6,args=struct.pack('>H',slot))
            damages.append((c.get(22946),c.get(22588)))
        assert len(set(damages))==1 and damages[0][1]>0,damages
        print('native aim, six-shot burst and resolved target damage agree:',damages)
        # A movement pass records the rate that produced the velocity arrays.
        a.reset();c.write(c.a4+13394,bytes(152))
        for t in (8,50,2,60):
            c.set(11700,t);c.run(c.bob+0x154b2)
            assert c.read(a.sym('dt_velocity_t'),2)==struct.pack('>H',t)
        c.run(a.sym('dt_effect_init'));assert c.read(a.sym('dt_velocity_t'),2)==bytes(2)
        a.options()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    AimChecks(p.parse_args()).run()
