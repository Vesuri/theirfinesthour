#!/usr/bin/env python3
"""FR-23 native movie-camera movement, display clocks and selection debounce."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks,u,Q,PATCHES
class CameraChecks:
    entries={'left':0x16632,'right':0x1664e,'up':0x1666a,'down':0x16692,'rise':0x1670a,'sink':0x1673a,'xy':0x166bc}
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def enable(self,on):
        a,c=self.a,self.c
        for off,n,name,kind in PATCHES:
            if name.startswith('dt_cam_'):
                c.write(c.bob+off,(b'\x4e\xb9' if kind=='PS' else b'\x4e\xf9')+struct.pack('>I',a.sym(name))+b'\x4e\x71'*((n-6)//2) if on else a.orig[off:off+n])
        for off in (0x166d4,0x166ee):c.write(c.bob+off,struct.pack('>H',16384 if on else 2048))
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def setup(self,hz=50):
        a,c=self.a,self.c;a.reset();c.set(30698,0);c.set(30722,0);c.set(30712,0);c.set(30716,16384)
        c.set(30700,10000000,'i');c.set(30704,10000000,'i');c.set(30708,100000,'i');c.set(11840,2)
        c.set(11700,2);c.set(11698,8);c.set(-8010,0);c.write(a.sym('dt_hz'),struct.pack('>H',hz))
        c.run(a.sym('dt_cam_tick'))
    def action(self,name):self.c.run(self.c.bob+self.entries[name],stop=self.c.bob+0x167aa)
    def tick(self,field):self.c.set(-8010,field&65535,'H');self.c.run(self.a.sym('dt_cam_tick'))
    def pose(self):return tuple(self.c.get(o,f) for o,f in ((30712,'H'),(30716,'H'),(30700,'i'),(30704,'i'),(30708,'i')))
    def baseline(self):
        self.enable(False);out=[]
        for t in (8,50):
            self.setup();self.c.set(11698,t)
            for _ in range(t):self.action('right')
            out.append(self.c.get(30712,'H'))
        assert out==[10240,10200],out
        distance=[]
        for t in (8,50):
            self.setup();self.c.set(11698,t)
            for _ in range(t):self.action('xy')
            distance.append(self.pose()[2:4])
        assert distance[0]!=distance[1],distance
        self.enable(True);print('FR-23 native angular truncation and per-update horizontal camera speed reproduced')
    def motion(self):
        a,c=self.a,self.c
        for hz in (50,60):
            for schedule in ((1,),(2,),(6,6,7,6),(1,3,2,5)):
                for action,index,rate in (('right',0,10240),('left',0,-10240),('up',1,-4096),('down',1,4096),('rise',4,8192),('sink',4,-8192)):
                    self.setup(hz);start=self.pose()[index];field=0;i=0
                    while field<hz:
                        field+=min(schedule[i%len(schedule)],hz-field);self.tick(field)
                        c.set(11698,(8,25,50,60)[i%4]);self.action(action);i+=1
                        expected=start+Fraction(rate*field,hz)
                        error=((self.pose()[index]-int(expected)+32768)%65536)-32768 if index==0 else self.pose()[index]-expected
                        assert abs(error)<=1,(hz,schedule,action,field,self.pose(),expected)
                for heading in (0,1,4096,12345,16384,32768,65535):
                    self.setup(hz);c.set(30712,heading,'H')
                    c.run(c.bob+0x2eb4a,args=struct.pack('>3H',16384,heading,16384));rate=(c.get(4204,'i'),c.get(4208,'i'))
                    field=0;i=0
                    while field<hz:
                        field+=min(schedule[i%len(schedule)],hz-field);self.tick(field);self.action('xy');i+=1
                    got=self.pose()[2:4];assert all(abs(g-(10000000+r))<=1 for g,r in zip(got,rate)),(hz,schedule,heading,got,rate)
        print('FR-23 all camera axes, small polar components, PAL/NTSC and changing render rates agree')
    def boundaries(self):
        a,c=self.a,self.c
        for action,offset,value,fmt,expected in (('up',30716,1,'H',0),('down',30716,32767,'H',32768),('rise',30708,524286,'i',524287),('sink',30708,1025,'i',1024)):
            self.setup();c.set(offset,value,fmt);self.tick(1);self.action(action);assert c.get(offset,fmt)==expected
        self.setup();initial=self.pose()
        for field in range(1,51):self.tick(field);self.action('right');self.action('rise')
        for field in range(51,101):self.tick(field);self.action('left');self.action('sink')
        assert self.pose()==initial
        self.setup();c.set(30698,1);initial=self.pose()
        for action in self.entries:self.tick(1);self.action(action)
        assert self.pose()==initial
        c.write(a.sym('dt_cam_frac'),b'\xff'*10);c.set(30722,0);c.run(a.sym('dt_cam_mode'))
        assert c.read(a.sym('dt_cam_frac'),10)==bytes(10)
        # Clock wrap is elapsed time; stalls and duplicate field observations add none.
        self.setup();c.write(a.sym('dt_cam_clock'),struct.pack('>HH',65534,1));self.tick(1)
        assert abs(int.from_bytes(c.read(a.sym('dt_cam_elapsed'),4),'big')/(1<<24)-3/50)<1e-6
        self.tick(1);assert c.read(a.sym('dt_cam_elapsed'),4)==bytes(4)
        self.tick(100);assert c.read(a.sym('dt_cam_elapsed'),4)==bytes(4)
        c.run(a.sym('dt_cam_init'));assert c.read(a.sym('dt_cam_clock'),22)==bytes(22)
        assert c.get(30724,'B')==255
        print('FR-23 clamps, reversals, mode gates/reset, clock wrap and stalls pass')
    def debounce(self):
        a,c=self.a,self.c
        for hz in (50,60):
            for schedule in ((1,),(2,),(3,1,2)):
                self.setup(hz);c.run(a.sym('dt_cam_reload'),stop=c.bob+0x167aa);field=0;i=0
                while field<hz//5:
                    field+=schedule[i%len(schedule)];i+=1;self.tick(field)
                    ready=field>=hz//5
                    c.run(a.sym('dt_cam_cooldown'),stop=c.bob+(0x1607a if ready else 0x167aa))
                    assert bool(c.get(30730))!=ready
        self.setup();c.run(c.bob+0x16050,stop=c.bob+0x16056)
        a.options();print('FR-23 native viewer-entry hook, 0.2s debounce and original-mode gate pass')
    def run(self):self.baseline();self.motion();self.boundaries();self.debounce()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');CameraChecks(p.parse_args()).run()
