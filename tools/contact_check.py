#!/usr/bin/env python3
"""FR-19 native aircraft contact, coastline, attitude and moving-ship checks."""
import argparse,random,struct
from fractions import Fraction
from input_combat_check import Checks,u,Q

class ContactChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c;self.boundary=self.find_coast()
    def terrain(self,x,y):
        c=self.c;c.set(14294,x,'i');c.set(14902,y,'i')
        c.run(c.bob+0x11ea2,args=struct.pack('>H',1));return c.reg(9)&65535
    def find_coast(self):
        self.a.reset()
        for y in range(100<<16,220<<16,8<<16):
            prev=self.terrain(100<<16,y)
            for x in range(108<<16,220<<16,8<<16):
                val=self.terrain(x,y)
                if prev==1 and val==0:
                    lo,hi=x-(8<<16),x
                    while hi-lo>1:
                        mid=(lo+hi)//2
                        if self.terrain(mid,y)==prev:lo=mid
                        else:hi=mid
                    return hi,y
                prev=val
        raise AssertionError('no controlled native water-to-land boundary')
    def patch(self,on):
        a,c=self.a,self.c
        for off,n,name,kind in ((0x12eaa,8,'dt_contact_world','P'),(0x1d974,8,'dt_contact_plane','P'),(0x1dc4a,6,'dt_contact_next','PS')):
            c.write(c.bob+off,(b'\x4e\xb9' if kind=='PS' else b'\x4e\xf9')+struct.pack('>I',a.sym(name))+b'\x4e\x71'*((n-6)//2) if on else a.orig[off:off+n])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def setup(self,player=True,gear=1):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152))
        c.set(13395,4,'B');c.set(13563,1,'B');c.set(13318,1 if player else 0)
        c.set(22387,0,'B');c.set(22491,gear,'B');c.set(11385,0,'B')
        c.set(22707,0,'B');c.set(14035,1,'B');c.set(22767,0,'B')
        c.set(19198+2,0);c.set(18830+2,16384);c.set(18164,0)
        c.write(c.a4+21254,bytes(152*7))
    def crossing(self,schedule,offset=-590,vx=2400,roll=(0,0),pitch=(16384,0),player=True,gear=1,ship=False,ground_target=False):
        self.setup(player,gear);a,c=self.a,self.c;boundary,y=self.boundary
        x0=boundary+offset;elapsed=Fraction(0)
        if ground_target:
            tx=((boundary>>16)+1)<<16
            assert self.terrain(tx,y)==0
            c.write(c.a4-22946,bytes([240])*70);c.write(c.a4-22876,bytes([240])*70)
            c.set(-22946,(tx>>16)-96,'B');c.set(-22876,(y>>16)-96,'B');c.set(-22806,0,'B')
            c.set(-22010,0x1200,'I')
            c.write(0x1200,struct.pack('>14h',1,1,0,0,0,0,-2,2,-2,2,-4,4,-4,4))
            c.write(c.a4+24756,bytes([0xa0,100])*4)

        if ship:
            c.set(13410,15,'B');c.set(13578,12,'B');c.set(22618,0)
            c.set(22722,0,'B');c.set(18194,0)
            width=c.get(-29642+15*32,'H')
            shipv=max(width*20,40000)
            impactx=x0+int(Fraction(vx*6,25))
        for frame in range(100):
            t=schedule[frame%len(schedule)];before=elapsed;elapsed+=Fraction(1,t);c.set(11700,t)
            start=(int(x0+vx*before),y,int(144-600*before))
            end=(int(x0+vx*elapsed),y,int(144-600*elapsed))
            for off,v in zip((14294,14902,15510),start):c.set(off,max(0,v),'i')
            for off,(v,rate) in ((19200,roll),(18832,pitch)):
                c.set(off,int(v+rate*before)&65535,'H')
            if ship:
                c.set(14354,int(impactx+shipv*(before-Fraction(6,25))),'i')
                c.set(14962,y,'i');c.set(15570,0,'i')
            c.run(a.sym('dt_contact_snapshot'))
            for off,v in zip((14294,14902,15510),end):c.set(off,max(0,v),'i')
            for off,v in zip((16614,16678,16742),start):c.set(off,max(0,v),'i')
            for off,old,new in zip((17382,17446,17510),start,end):c.set(off,new-old,'i')
            for off,(v,rate) in ((19200,roll),(18832,pitch)):
                c.set(off,int(v+rate*elapsed)&65535,'H')
            if ship:
                ship_end=int(impactx+shipv*(elapsed-Fraction(6,25)))
                c.set(14354,ship_end,'i')
            c.run(c.bob+0x1d948)
            state=c.get(22387,'B')
            if state!=0 or c.get(13395,'B')!=4:
                if ship:assert c.get(14354,'i')==ship_end,('ship pose not restored',t)
                return state,c.get(14294,'i'),c.get(15510,'i'),c.get(22618),elapsed
        raise AssertionError('no contact')
    def baseline(self):
        self.patch(False)
        out=[self.crossing([t])[0] for t in (8,50)]
        assert out==[2,6],out
        # Native AI can snap to ground before actual contact, at sampled altitude <125.
        self.setup(False);x,y=self.boundary
        self.c.set(14294,x+5000,'i');self.c.set(14902,y,'i');self.c.set(15510,100,'i')
        self.c.run(self.c.bob+0x1d948);assert self.c.get(22387,'B')==2
        self.patch(True)
        print('FR-19 native shoreline outcomes disagree at T=8/50:',out)
    def trajectories(self):
        x,y=self.boundary
        for player in (True,False):
            cases=[dict(offset=-590,expected=6 if player else 7),dict(offset=-562,expected=2),
                   dict(offset=5000,vx=0,roll=(6000,400),expected=2),
                   dict(offset=5000,vx=0,pitch=(20100,1000),expected=2),
                   dict(offset=5000,vx=0,roll=(7000,400),expected=7)]
            if player:cases.append(dict(offset=5000,vx=0,gear=0,expected=9))
            for case in cases:
                expected=case.pop('expected')
                for schedule in ([2],[4],[8],[25],[50],[60],[50,8,25,60,4]):
                    state,px,z,damage,when=self.crossing(schedule,player=player,**case)
                    assert state==expected,(player,case,schedule,state,expected)
                    exact=x+case.get('offset',-590)+Fraction(case.get('vx',2400)*6,25)
                    assert abs(px-exact)<=1,(case,schedule,px,exact)
                    assert z==0
                    assert Fraction(6,25)<=when<=Fraction(6,25)+max(Fraction(1,t) for t in schedule)
        # AI remains airborne within the old snap band until the ground crossing.
        self.setup(False);c=self.c;c.set(14294,x+5000,'i');c.set(14902,y,'i');c.set(15510,100,'i')
        c.run(c.bob+0x1d948);assert c.get(22387,'B')==0 and c.get(15510,'i')==100
        print('FR-19 coastline/attitude boundaries, player and AI, gear and real ground crossing agree')
    def ships(self):
        for player in (True,False):
            for schedule in ([2],[8],[25],[50],[60],[8,50,25,60]):
                state,px,z,damage,when=self.crossing(schedule,offset=-10000,vx=0,roll=(8192,0),player=player,ship=True)
                assert state==7 and damage==1500,(player,schedule,state,damage)
                assert self.c.get(30922)==16
                assert self.c.read(self.a.sym('dt_contact_ship_active'),2)==bytes(2)
        print('FR-19 moving-ship impact damage and restored end-of-update ship poses agree')
    def other_contacts(self):
        a,c=self.a,self.c;boundary,y=self.boundary
        tx=((boundary>>16)+1)<<16
        for edge,hit in ((124,True),(132,False)):
            outcomes=[]
            for t in (2,8,25,50,60):
                self.crossing([t],offset=tx-boundary+edge-576,roll=(8192,0),ground_target=True)
                outcomes.append(c.get(24757,'B'))
            assert len(set(outcomes))==1 and (outcomes[0]!=100)==hit,(edge,outcomes)
        # Class 6 is a parachute, constructed with pitch $8000 and speed 35.
        # It falls vertically; terrain classification has no horizontal overrun.
        for slot in (128,140):
            for water in (False,True):
                outcomes=[]
                for t in (2,8,25,50,60):
                    a.reset();c.write(c.a4+13394,bytes(152))
                    c.set(13394+slot,37,'B');c.set(13562+slot,6,'B')
                    c.set(19694+slot*2,35);c.set(18466+slot*2,32768,'H')
                    c.set(18162+slot*2,8192);c.set(11700,t)
                    for off,v in ((14290,boundary+(-1000 if water else 1000)),(14898,y),(15506,300)):
                        c.set(off+slot*4,v,'i')
                    for _ in range(t*3):
                        c.run(c.bob+0x154b2);c.run(c.bob+0x1d948)
                        if c.get(15506+slot*4,'i')==0:break
                    else:raise AssertionError('parachute never landed')
                    outcomes.append((c.get(13394+slot,'B'),c.get(13562+slot,'B'),c.get(19694+slot*2),c.get(14290+slot*4,'i'),c.get(14898+slot*4,'i')))
                assert len(set(outcomes))==1,(slot,water,outcomes)
        print('FR-19 native static-component hit/miss boundaries and parachute contacts agree')
    def snapshot_guards(self):
        a,c=self.a,self.c;boundary,y=self.boundary
        self.setup();c.set(14294,boundary+5000,'i');c.set(14902,y,'i');c.set(15510,10,'i')
        c.run(c.bob+0x12eaa,stop=c.bob+0x13c6e)
        assert c.read(a.sym('dt_contact_valid'),2)==b'\x00\x01'
        assert int.from_bytes(c.read(a.sym('dt_contact_angles')+34,2),'big')==16384
        # Reusing this slot must not interpolate the prior occupant's level bank.
        c.reg(13,1);c.run(a.sym('dt_plane_generation'))
        c.set(19200,8192);c.set(15510,0,'i');c.set(16742,10,'i');c.set(17510,-1000,'i')
        c.set(16614,boundary+5000,'i');c.set(16678,y,'i');c.set(17382,0,'i');c.set(17446,0,'i')
        c.run(c.bob+0x1d948);assert c.get(22387,'B')==7
        c.run(a.sym('dt_effect_init'))
        assert c.read(a.sym('dt_contact_valid'),4)==bytes(4)
        print('FR-19 world snapshot hook, slot-generation guard and flight reset pass')
    def math(self):
        a,c=self.a,self.c;r=random.Random(19)
        for _ in range(1000):
            den=r.randint(1,0xffffffff);num=r.randint(0,den)
            c.reg(9,num);c.reg(10,den);c.run(a.sym('dt_contact_fraction'))
            assert c.reg(9)==(num<<16)//den
            value=r.randint(-0x7fffffff,0x7fffffff);alpha=r.randint(0,65536)
            c.reg(9,value&0xffffffff);c.reg(10,alpha);c.run(a.sym('dt_contact_scale'))
            expected=(abs(value)*alpha)//65536
            if value<0:expected=-expected
            assert c.reg(9)==expected&0xffffffff
        a.options()
        print('FR-19 full-width interpolation arithmetic and original-mode gate pass')
    def run(self):self.baseline();self.trajectories();self.ships();self.other_contacts();self.snapshot_guards();self.math()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    ContactChecks(p.parse_args()).run()
