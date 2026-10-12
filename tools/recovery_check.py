#!/usr/bin/env python3
"""FR-16 native player recovery, goal clamps and control-clock regressions."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,u,Q

class RecoveryChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def patch(self,on):
        a,c=self.a,self.c
        c.write(c.bob+0x149b0,b'\x4e\xb9'+struct.pack('>I',a.sym('dt_recovery'))+b'\x4e\x71' if on else a.orig[0x149b0:0x149b8])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob+0x14982),Q(c.bob+0x14ac6)))
    def setup(self,roll,pitch,slot=1):
        a,c=self.a,self.c;a.reset();self.slot=slot
        c.set(13318,slot);c.set(13326,1,'B');c.set(22386+slot,0,'B')
        c.set(13546+slot,0,'B');c.set(22402+slot*2,24576)
        c.set(19198+slot*2,roll);c.set(18830+slot*2,pitch,'H')
    def step(self,t,world=None):
        c=self.c;c.set(11698,t);c.set(11700,world or t)
        # Enter the native recovery tail with the caller's LINK frame.
        c.reg(6,0x1e00000);c.write(0x1e00000,struct.pack('>II',0,0x1000))
        c.run(c.bob+0x14982)
        return c.get(19198+self.slot*2),c.get(18830+self.slot*2,'H')
    @staticmethod
    def oracle(roll,pitch,elapsed,throttle=True):
        r=max(Fraction(0),abs(roll)-elapsed*1024)
        ptime=max(Fraction(0),elapsed-Fraction(abs(roll),1024)) if throttle else 0
        p=max(Fraction(0),abs(pitch-16384)-ptime*512)
        return (r if roll>=0 else -r),16384+(p if pitch>=16384 else -p)
    def baseline(self):
        self.patch(False);out=[]
        for t in (8,50):
            self.setup(8192,16384)
            for _ in range(t):state=self.step(t)
            out.append(state[0])
        assert out==[7168,7192],out
        self.setup(0,16383);overshoot=self.step(8)[1]
        assert overshoot==16447,overshoot
        self.patch(True)
        print('FR-16 native recovery loss and pitch overshoot reproduced:',out,overshoot)
    def trajectories(self):
        seqs=[[t]*(t*4) for t in (2,4,8,25,50,60)]+[[2]*2+[50]*50+[8]*8+[60]*60]
        fixtures=[(8192,16384),(-8192,16384),(0,18000),(0,8000),(0,16383),(0,16385),
                  (1,16383),(-1,16385),(300,18000),(-300,8000),(0,0),(0,65535),(-32768,16384)]
        for roll,pitch in fixtures:
            for seq in seqs:
                self.setup(roll,pitch);elapsed=Fraction(0)
                previous=(roll,pitch)
                for t in seq:
                    actual=self.step(t,max(2,t//3));elapsed+=Fraction(1,t)
                    expected=self.oracle(roll,pitch,elapsed)
                    assert all(abs(x-y)<=1 for x,y in zip(actual,expected)),(roll,pitch,t,elapsed,actual,expected)
                    assert abs(actual[0])<=abs(previous[0])
                    assert abs(actual[1]-16384)<=abs(previous[1]-16384)
                    previous=actual
        # Both signs, short distances and complete roll-then-pitch recovery.
        for roll,pitch in ((7,16377),(-7,16391),(1024,16896),(-1024,15872)):
            deadline=Fraction(abs(roll),1024)+Fraction(abs(pitch-16384),512)
            for t in (2,8,25,50,60):
                self.setup(roll,pitch);elapsed=Fraction(0)
                while elapsed<deadline+Fraction(2,t):
                    state=self.step(t);elapsed+=Fraction(1,t)
                    if state==(0,16384):break
                assert state==(0,16384) and abs(elapsed-deadline)<=Fraction(1,t),(roll,pitch,t,elapsed,deadline)
                assert self.c.read(self.a.sym('dt_recovery_frac')+2,2)==bytes(2)
                assert self.c.read(self.a.sym('dt_recovery_frac')+34,2)==bytes(2)
        print('FR-16 monotonic equal-time recovery, all boundaries and roll-to-pitch completion pass')
    def gates(self):
        a,c=self.a,self.c
        for off,val in ((13326,0),(22387,1),(13547,1)):
            self.setup(1024,17000);c.set(off,val,'B')
            for _ in range(50):assert self.step(50)==(1024,17000)
            c.set(off,1 if off==13326 else 0,'B')
            for _ in range(50):state=self.step(50)
            assert abs(state[0])<=1 and abs(state[1]-17000)<=1
        self.setup(300,17000);c.set(22404,0)
        for _ in range(100):state=self.step(50)
        assert state==(0,17000)
        c.set(22404,24576)
        for _ in range(50):state=self.step(50)
        assert abs(state[1]-16488)<=1
        # Input reversal part-way through recovery does not retain an old sign.
        self.setup(1000,16384);self.step(50);c.set(19200,-1)
        assert self.step(50)==(0,16384)
        for slot in range(16):
            self.setup(1,16385,slot);self.step(50)
            c.write(a.sym('dt_recovery_frac'),b'\xff'*64)
            c.reg(13,slot);c.run(a.sym('dt_plane_generation'))
            for offset in (0,32):
                b=c.read(a.sym('dt_recovery_frac')+offset,32)
                assert b==b'\xff'*(slot*2)+bytes(2)+b'\xff'*(30-slot*2)
        c.run(a.sym('dt_effect_init'))
        assert c.read(a.sym('dt_recovery_frac'),64)==bytes(64)
        a.options()
        print('FR-16 native gates, throttle, reversal, all player slots, reset and original mode pass')
    def run(self):self.baseline();self.trajectories();self.gates()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    RecoveryChecks(p.parse_args()).run()
