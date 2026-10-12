#!/usr/bin/env python3
"""FR-28 fuel fractions and FR-27 native fuel/engine gates."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,u,Q
class FuelChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def patch(self,on):
        a,c=self.a,self.c;c.write(c.bob+0x20264,b'\x4e\xb9'+struct.pack('>I',a.sym('dt_fuel_burn')) if on else a.orig[0x20264:0x2026a])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def burn(self,rate,t,slot=0):
        c=self.c;c.reg(1,c.a4+22522+slot*4);c.reg(13,slot);c.reg(9,rate);c.reg(10,t)
        c.run(c.bob+0x20264,stop=c.bob+0x2026a)
    def baseline(self):
        a,c=self.a,self.c;self.patch(False);out=[]
        for t in (8,25,50,60):
            a.reset();c.set(22522,10000000,'I')
            for _ in range(t):self.burn(65536,t)
            out.append(10000000-c.get(22522,'I'))
        assert out==[65536,65525,65500,65520],out
        self.patch(True);print('FR-28 native fuel rounding divergence reproduced:',out)
    def fractions(self):
        a,c=self.a,self.c
        for slot in range(16):
            for schedule in ((2,),(4,),(8,),(25,),(50,),(60,),(8,25,50,60,2)):
                for rate in (0,1,31,65536,152916):
                    a.reset();c.set(22522+slot*4,10000000,'I');used=Fraction(0)
                    for i in range(120):
                        t=schedule[i%len(schedule)];self.burn(rate,t,slot);used+=Fraction(rate,t)
                        assert 0<=used-(10000000-c.get(22522+slot*4,'I'))<1+Fraction(120,65536),(slot,schedule,rate,i)
            c.write(a.sym('dt_fuel_frac')+slot*2,b'\xff\xff');c.reg(13,slot);c.run(a.sym('dt_att_reset'))
            assert c.read(a.sym('dt_fuel_frac')+slot*2,2)==bytes(2)
        a.reset();c.set(22522,1,'I');self.burn(152916,2);assert c.get(22522,'I')==0
        assert c.read(a.sym('dt_fuel_frac'),2)==bytes(2)
        # Long-running low burn must still consume fuel, within sub-unit error.
        a.reset();c.set(22522,10000000,'I')
        for _ in range(6000):self.burn(1,60)
        assert 99<=10000000-c.get(22522,'I')<=100
        print('FR-28 all 16 slots, tiny/full burn rates, changing T/acceleration, depletion and reuse pass')
    def native(self):
        a,c=self.a,self.c
        # Execute the actual engine computation, burn-rate curve and zero-fuel gates.
        for kind in range(1,15):
            for throttle in (0,1,100,21845,43690,65535):
                for t in (2,8,25,50,60):
                    a.reset();slot=1;c.reg(13,slot);c.reg(6,0x1e00000);c.set(30942,kind,'B');c.set(13318,slot)
                    c.set(19568,65535,'H');c.set(19600,32768,'H');c.set(22444,throttle,'H');c.set(11700,t)
                    c.set(22526,1000000,'I');c.set(11386,0,'B')
                    # Starts before engine health/throttle product, stops before attitude.
                    c.run(c.bob+0x20126,stop=c.bob+0x202b8)
                    power=c.get(22404,'H');expected=(power*3)//2 if power<43690 else ((power-43690)*4+65536)
                    used=1000000-c.get(22526,'I')
                    assert abs(Fraction(expected,t)-used)<1.01,(kind,throttle,t,power,used,expected)
                    if power:
                        c.set(22526,0,'I');c.reg(13,slot);c.run(c.bob+0x20126,stop=c.bob+0x202b8)
                        assert c.get(22404)==0 and c.get(13372)==0 and c.get(13374)==0
        # The unlimited-fuel option only gates player slot zero.
        for slot in (0,1):
            a.reset();c.reg(13,slot);c.reg(6,0x1e00000);c.set(30942,4,'B');c.set(13318,slot)
            c.set(19566+slot*2,65535,'H');c.set(19598+slot*2,65535,'H');c.set(22442+slot*2,65535,'H')
            c.set(11700,50);c.set(22522+slot*4,1000000,'I');c.set(11386,1,'B')
            c.run(c.bob+0x20126,stop=c.bob+0x202b8)
            assert (c.get(22522+slot*4,'I')==1000000)==(slot==0)
        a.options();print('FR-27/28 native aircraft-type engines, throttle curve, empty-fuel cutoff and unlimited-player gate pass')
    def run(self):self.baseline();self.fractions();self.native()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');FuelChecks(p.parse_args()).run()
