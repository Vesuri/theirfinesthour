#!/usr/bin/env python3
"""FR-25 physical mouse polling and 50-Hz reference joystick/keyboard cadence."""
import argparse, struct
from input_combat_check import Checks,u,Q
class FieldChecks:
    clears=(0x29c56,0x29c8a,0x29cbc,0x29cd4,0x29d08,0x29d3a)
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self,hz=50,menu=0):
        a,c=self.a,self.c;a.reset();c.write(a.sym('dt_hz'),struct.pack('>H',hz))
        c.write(c.a4-4708,bytes(24));c.set(-4718,menu);c.set(-4710,20)
        c.set(11958,0);c.set(11960,0);c.set(11940,0)
        for off,val in ((11816,100),(11818,100),(11832,0),(11834,1000),(11836,0),(11838,1000)):c.set(off,val)
    def field(self,joy=2):
        a,c=self.a,self.c;c.write(0xdff00c,struct.pack('>H',joy))
        c.run(c.bob+0x29a76,stop=c.bob+0x29a80);c.run(c.bob+0x28dd8,stop=c.bob+0x28df6)
    def baseline(self):
        a,c=self.a,self.c;result=[]
        for off in self.clears:c.write(c.bob+off,a.orig[off:off+4])
        self.flush()
        for hz in (50,60):
            self.setup(hz);c.write(0xdff00c,b'\x00\x02')
            for _ in range(hz):
                c.run(c.bob+0x29c00);c.set(-4696,c.get(-4696)+c.get(-4700))
            result.append((c.get(-4692),c.get(-4696)))
        assert result[0]!=result[1],result
        # A release discards accumulated motion before a slow renderer reads it.
        self.setup();c.set(-4696,123);c.write(0xdff00c,bytes(2));c.run(c.bob+0x29c00)
        assert c.get(-4696)==0
        for off in self.clears:c.write(c.bob+off,b'\x4e\x71'*2)
        self.flush();print('FR-25 native PAL/NTSC ramp divergence and loss of unread joystick movement reproduced')
    def flush(self):
        c=self.c;c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def joystick(self):
        a,c=self.a,self.c
        for menu in (0,1):
            result=[]
            for hz in (50,60):
                self.setup(hz,menu)
                for second,joy in enumerate((2,2,0,512,512,0,1,256)):
                    for field in range(hz):self.field(joy)
                    result.append((hz,second,c.read(c.a4-4700,16),c.get(11816),c.get(11818)))
            assert [r[1:] for r in result[:8]]==[r[1:] for r in result[8:]],result
        # The exact same virtual field sequence must survive arbitrary render reads.
        for hz in (50,60):
            sums=[]
            for draw in (1,2,5,7):
                self.setup(hz);total=[0,0]
                for field in range(hz*2):
                    self.field((2,0,512,1,256)[(field*5//hz)%5])
                    if (field+1)%draw==0:
                        total[0]+=c.get(-4696);total[1]+=c.get(-4694);c.set(-4696,0);c.set(-4694,0)
                total[0]+=c.get(-4696);total[1]+=c.get(-4694);sums.append(total)
            assert len(set(map(tuple,sums)))==1,(hz,sums)
        for hz in (50,60):
            self.setup(hz)
            for field in range(1,hz*2//5+1):
                self.field(0);assert (c.get(-4710)==0)==(field==hz*2//5)
        print('FR-25 native joystick ramps/caps/reversals, cursor movement, varying render reads and 0.4s keyboard repeat agree')
    def mouse(self):
        a,c=self.a,self.c
        for hz in (50,60):
            for total in (-1200,-100,100,1200):
                for draw in (1,3,7):
                    self.setup(hz);counter=250;c.set(-4708,counter,'B');c.set(-4706,counter,'B');read=[0,0]
                    for field in range(hz):
                        delta=(field+1)*total//hz-field*total//hz;counter=(counter+delta)&255
                        c.write(0xdff00a,bytes((counter,counter)));c.run(a.sym('dt_mouse'))
                        for i,o in enumerate((-4704,-4702)):read[i]+=c.get(o)
                    assert read==[total,total],(hz,total,draw,read)
        # Existing ambiguity heuristic: continuation across the signed-byte limit.
        self.setup();c.write(a.sym('dt_mdx'),struct.pack('>h',100));c.set(-4708,0,'B')
        c.write(0xdff00b,bytes((140,)));c.run(a.sym('dt_mouse'));assert c.get(-4704)==140
        self.a.options();print('FR-25 mouse signed counters, wrap, PAL/NTSC count conservation and original gating pass')
    def run(self):self.baseline();self.joystick();self.mouse()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68000');FieldChecks(p.parse_args()).run()
