#!/usr/bin/env python3
"""FR-15 native continuous aircraft attitude regression."""
import argparse,struct
from fractions import Fraction
from input_combat_check import PATCHES,u,Q
from input_combat_check import Checks

class AttitudeChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,t,axis='roll',direction=1,kind=4):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152))
        c.set(13318,0);c.set(13395,kind,'B');c.set(13563,1,'B');c.set(11700,t)
        c.set(19263,1 if axis=='roll' else 0,'B');c.set(19279,0,'B')
        c.set(19296,8192 if direction>0 else -8192)
        c.set(19327,(2 if direction>0 else 1) if axis=='pitch' else 0,'B')
        c.set(19343,0,'B');c.set(19360,24576 if direction>0 else 8192)
        c.set(19391,0,'B');c.set(19407,0,'B')
        c.set(18164,0);c.set(18468,16384);c.set(18832,16384);c.set(19200,0)
        c.set(19696,300);c.set(15510,50000,'i');c.set(22526,100000000,'i')
        c.set(22707,0,'B');c.set(22588,0);c.set(22387,0,'B');c.set(18771,0,'B')
    def patch(self,enabled):
        a,c=self.a,self.c
        for off,n,name,kind in PATCHES:
            if name.startswith('dt_att_'):
                c.write(c.bob+off,(b'\x4e\xb9'+struct.pack('>I',a.sym(name))+b'\x4e\x71'*((n-6)//2)) if enabled else a.orig[off:off+n])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def step(self,t):
        self.c.set(11700,t);self.c.run(self.c.bob+0x200c0)
    def baseline(self):
        self.patch(False);out=[]
        for t in (8,50):
            self.setup(t)
            for _ in range(t):self.step(t)
            out.append(self.c.get(19200))
        assert out==[4096,4050],out
        self.patch(True)
        print('FR-15 original one-second roll loss reproduced:',out)
    def commands(self):
        c=self.c
        seqs=[[t]*t for t in (2,4,8,25,50,60)]+[[2]+[50]*25,[8]*4+[60]*30]
        for kind in range(1,15):
            for axis in ('roll','pitch'):
                for sign in (-1,1):
                    for seq in seqs:
                        self.setup(seq[0],axis,sign,kind)
                        for t in seq:self.step(t)
                        off=19200 if axis=='roll' else 18832
                        rate=4096 if axis=='roll' or sign<0 else 5120
                        expected=(0 if axis=='roll' else 16384)+sign*rate
                        err=((c.get(off,'H')-expected+32768)&65535)-32768
                        assert abs(err)<=1,(kind,axis,sign,seq[0],err)
        for sign in (-1,1):
            for t in (2,8,25,50,60):
                self.setup(t,'roll',sign);c.set(19279,1,'B');c.set(19296,sign*24000)
                for _ in range(t):self.step(t)
                assert abs(c.get(19200)-sign*16384)<=1
                self.setup(t,axis='none');c.set(19200,sign*4096)
                c.set(18771,1,'B');c.set(22348,8192)
                for _ in range(t):self.step(t)
                assert c.get(18164)==(170 if sign<0 else -171)
                assert c.get(19200)==sign*4096
        # Complete commands, including tiny targets, and reversal after clamping.
        for axis in ('roll','pitch'):
            off=19200 if axis=='roll' else 18832
            targetoff=19296 if axis=='roll' else 19360
            flag=19263 if axis=='roll' else 19327
            for sign in (-1,1):
                rate=4096 if axis=='roll' or sign<0 else 5120
                for distance in (1,7,8192):
                    for t in (2,8,25,50,60):
                        self.setup(t,axis,sign)
                        target=(0 if axis=='roll' else 16384)+sign*distance
                        c.set(targetoff,target)
                        done=2 if axis=='roll' else 3
                        elapsed=Fraction(0)
                        for _ in range(4*t+1):
                            self.step(t);elapsed+=Fraction(1,t)
                            if c.get(flag,'B')==done:break
                        else:raise AssertionError(('incomplete',axis,sign,distance,t))
                        assert c.get(off)==target,(axis,sign,distance,t,c.get(off),target)
                        assert Fraction(distance,rate)<=elapsed<=Fraction(distance,rate)+Fraction(1,t),(axis,sign,distance,t,elapsed)
                        frac=self.a.sym('dt_att_'+('roll' if axis=='roll' else 'pitch')+'frac')+2
                        assert c.read(frac,2)==bytes(2)
                        # Reverse while retaining the native manoeuvre and object state.
                        c.set(targetoff,0 if axis=='roll' else 16384)
                        c.set(flag,1 if axis=='roll' or sign>0 else 2,'B')
                        for _ in range(4*t+1):
                            self.step(t)
                            if c.get(flag,'B')==done:break
                        assert c.get(off)==(0 if axis=='roll' else 16384)
        print('FR-15 all 14 aircraft kinds, signed commands, variable rates, tiny goals and completed reversals pass')
    def special(self):
        a,c=self.a,self.c
        for state in (1,3,4,5,8):
            out=[]
            for t in (2,8,25,50,60):
                self.setup(t,axis='none');c.set(22387,state,'B')
                # Stall remains below its recovery speed for this short trajectory.
                c.set(19696,0)
                for _ in range(t):self.step(t)
                out.append((c.get(18468,'H'),c.get(18832,'H'),c.get(19200,'H')))
            for row in out:
                assert all(abs(((x-y+32768)&65535)-32768)<=1 for x,y in zip(row,out[0])),(state,out)
            print('FR-15 native flight state',state,out)
        # Player bank-induced pitch: both native branches and the neutral gate.
        for bank,expected in ((0,16384),(2000,16455),(9692,17294)):
            for t in (2,8,25,50,60):
                self.setup(t,axis='none');c.set(13318,1);c.set(22387,7,'B')
                c.set(19200,bank);c.set(13378,1000);c.set(13380,3000);c.set(22404,0)
                for _ in range(t):self.step(t)
                assert abs(c.get(18832,'H')-expected)<=1,(bank,t,c.get(18832,'H'),expected)
        # The signed primitive handles sub-unit rates and reversal without bias.
        for rate in (1,7,455,728,4096,5120,16384,20480):
            for t in (2,8,25,50,60):
                self.setup(t);total=0
                for sign in (1,-1):
                    for _ in range(t):
                        c.reg(13,1);c.reg(9,(sign*rate)&65535);c.reg(1,a.sym('dt_att_rollfrac'))
                        c.run(a.sym('dt_att_rate'));v=c.reg(9)&65535
                        total+=v if v<32768 else v-65536
                assert total==0,(rate,t,total)
        # Cross both poles: leftover step time runs at the new direction's rate.
        for sign,expected in ((-1,4495),(1,29072)):
            for seq in [[t]*t for t in (2,8,25,50,60)]+[[8]*4+[50]*25]:
                self.setup(seq[0],'pitch',sign)
                initial=500 if sign<0 else 32268
                c.set(18832,initial);c.set(18468,initial)
                c.set(19360,16384);c.set(19343,1,'B')
                for t in seq:self.step(t)
                assert abs(c.get(18832,'H')-expected)<=1,(sign,seq[0],c.get(18832,'H'))
        # Exact fixed-point boundary oracle, including fractional borrow.
        for off,direction,angle in ((0x20478,1,65000),(0x2053e,2,33000)):
            for fraction in (0,1,32768,65535):
                self.setup(50);c.reg(13,1);c.reg(9,2);c.reg(1,c.a4+18830)
                c.set(19327,direction,'B');c.set(18832,angle,'H')
                c.write(a.sym('dt_att_pitchfrac')+2,struct.pack('>H',fraction))
                reflected=(-(angle*65536+fraction))&0xffffffff
                expected=reflected+reflected//4 if direction==1 else 0x80000000-((0x80000000-reflected)//5)*4
                c.run(a.sym('dt_att_reflect'))
                actual=c.get(18832,'H')*65536+int.from_bytes(c.read(a.sym('dt_att_pitchfrac')+2,2),'big')
                assert actual==expected,(direction,fraction,actual,expected)
        # Every construction slot and new-flight reset clear private attitude.
        for slot in range(16):
            self.setup(50)
            for name in ('roll','pitch','fall'):c.write(a.sym('dt_att_'+name+'frac'),b'\xff'*32)
            c.reg(13,slot);c.run(a.sym('dt_plane_generation'))
            for name in ('roll','pitch','fall'):
                b=c.read(a.sym('dt_att_'+name+'frac'),32)
                assert b==b'\xff'*(slot*2)+bytes(2)+b'\xff'*(30-slot*2)
        c.run(a.sym('dt_effect_init'))
        assert c.read(a.sym('dt_att_rollfrac'),96)==bytes(96)
        a.options()
        print('FR-15 sub-unit carries, reflections, constructor/flight resets and original gate pass')
    def run(self):
        self.baseline();self.commands();self.special()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    AttitudeChecks(p.parse_args()).run()
