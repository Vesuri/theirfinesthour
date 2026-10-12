#!/usr/bin/env python3
"""Native bomb regression: DUMP BASE SLAVE LISTING [--cpu 68000|68040].

Uses controlled release states and original target dimensions. Reference is the
native bomb movement at 64 updates/s, with the enhanced horizontal precision
but without the bomb scheduling patch. Sound/HUD and terrain classification
are stubbed; creation, motion, target footprints, damage and removal run native.
This CPU-only check does not measure rendering cost or exercise bombing AI.
"""
import argparse
import struct
from fractions import Fraction
from input_combat_check import Checks, PATCHES, Q, u

BOMB_OFFSETS = {0x1d500, 0x157c2, 0x159f8}

class BombChecks:
    def __init__(self, args):
        self.a = Checks(args)
        self.c = self.a.c
        self.patched = {off:self.c.read(self.c.bob+off,n)
                        for off,n,_,_ in PATCHES if off in BOMB_OFFSETS}

    def enable(self, enabled):
        c = self.c
        for off,data in self.patched.items():
            c.write(c.bob+off, data if enabled else self.a.orig[off:off+len(data)])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))

    def setup(self, altitude=50000, pitch=16384, heading=0, speed=250, mode=0):
        self.a.reset()
        c = self.c
        c.write(c.a4+13394,bytes(152))
        c.set(13318,0)
        for off,val,fmt in [(13394,4,'B'),(13562,1,'B'),(23826,8,'B'),
                            (23842,16,'B'),(11384,0,'B'),(14290,10000000,'i'),
                            (14898,10000000,'i'),(15506,altitude,'i'),
                            (18162,heading,'H'),(18466,pitch,'H'),(19198,0,'h'),
                            (19694,speed,'h'),(11698,64,'h'),(11700,64,'h')]:
            c.set(off,val,fmt)
        c.write(c.a4-32244,bytes.fromhex('4e75'))  # HUD only
        c.run(c.bob+0x1d280,args=struct.pack('>HH',0,1))
        slot = c.get(30720)
        assert slot == 20 and c.get(13562+slot,'B') == 3
        c.set(20766,mode,'B')
        if mode >= 2: c.set(18466+slot*2,pitch,'H')
        c.set(13394,0,'B')
        return slot

    def drop(self, schedule, **scenario):
        c = self.c
        slot = self.setup(**scenario)
        elapsed = Fraction(0)
        for frame in range(10000):
            t = schedule[frame % len(schedule)]
            c.set(11698,t); c.set(11700,t)
            c.run(c.bob+0x154b2)
            assert c.get(11700) == t, 'bomb step leaked its divisor into the world'
            assert c.read(self.a.sym('dt_bomb_active'),2) == b'\0\0'
            elapsed += Fraction(1,t)
            if c.get(15506+slot*4,'i') == 0:
                return tuple(c.get(off+slot*4,'i') for off in [14290,14898]), elapsed
            assert elapsed < 120, 'bomb never landed'
        raise AssertionError('frame limit')

    def impact(self, xy, target_xy):
        c = self.c
        # Retain the just-landed native bomb. Place a native type-22 target.
        for off,val,fmt in [(13394+16,22,'B'),(14290+16*4,target_xy[0],'i'),
                            (14898+16*4,target_xy[1],'i'),(18162+16*2,0,'h'),
                            (22586+16*2,0,'h')]: c.set(off,val,fmt)
        # Controlled surface classification: the native ship-target path.
        c.write(c.a4-32382,bytes.fromhex('70014e75'))
        c.run(c.bob+0x1df1e,args=struct.pack('>H',20))
        damage = c.get(22586+16*2)
        if damage:
            assert c.get(13394+20,'B') == 0
        else:
            assert c.get(13562+20,'B') != 3
        return damage

    def run(self):
        schedules = [[t] for t in [2,4,8,25,50,60]] + [[8,50,25,60,4], [50,16,50,16]]
        scenarios = [dict(),dict(altitude=5000,pitch=24576,heading=8192),
                     dict(altitude=5000,pitch=8192,heading=49152),
                     dict(altitude=1),dict(altitude=100000,speed=400,heading=32768),
                     dict(altitude=2000,speed=0),
                     dict(altitude=5000,pitch=24576,mode=2)]
        for scenario in scenarios:
            self.enable(False)
            reference, landing_time = self.drop([64], **scenario)
            self.enable(True)
            for schedule in schedules:
                xy, observed = self.drop(schedule, **scenario)
                assert xy == reference, (scenario,schedule,xy,reference)
                assert landing_time <= observed < landing_time + max(Fraction(1,t) for t in schedule)
                # A direct hit must retain native damage and remove the bomb.
                assert self.impact(xy,xy) == 110
            print('drop passed:',scenario or 'level', 'impact',reference)
        # The original near-edge reproduction is now the same at both rates.
        results=[]
        for rate in [8,50]:
            xy,_=self.drop([rate])
            results.append(self.impact(xy,(10000000,10069473)))
        assert results[0] == results[1], results
        # Native footprint boundary: equal outcomes on each side at all rates.
        for offset,damage in [(1900,110),(2200,0)]:
            for rate in [8,25,50,60]:
                xy,_=self.drop([rate])
                assert self.impact(xy,(xy[0],xy[1]-offset)) == damage
        # Reuse a live slot: creation must reset pending time and all XYZ fractions.
        self.setup()
        c=self.c
        c.write(self.a.sym('dt_bomb_time'),struct.pack('>I',65535))
        c.write(self.a.sym('dt_frac')+20*6,b'\xff'*6)
        c.set(13394+20,0,'B')
        c.run(c.bob+0x1d280,args=struct.pack('>HH',0,1))
        assert c.get(30720)==20
        assert c.read(self.a.sym('dt_bomb_time'),4)==bytes(4)
        assert c.read(self.a.sym('dt_frac')+20*6,6)==bytes(6)
        # Eight simultaneous player bombs: per-slot time/fractions must not leak.
        for rate in [4,50,60]:
            self.setup(altitude=5000)
            for _ in range(7): c.run(c.bob+0x1d280,args=struct.pack('>HH',0,1))
            assert c.get(30720)==27
            for frame in range(rate*10):
                c.set(11700,rate);c.run(c.bob+0x154b2)
                states=[tuple(c.get(off+slot*4,'i') for off in [14290,14898,15506]) for slot in range(20,28)]
                assert len(set(states))==1, states
                if not states[0][2]: break
            else: raise AssertionError('salvo did not land')
        print('native impact damage/removal, edge hits/misses, variable rate, accelerated time and slot reuse passed')

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68040')
    args=p.parse_args()
    BombChecks(args).run()
    print(args.cpu,'bomb checks passed')
