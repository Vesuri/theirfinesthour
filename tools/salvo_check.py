#!/usr/bin/env python3
"""FR-08 native salvo releases, inventory and interpolated positions."""
import argparse,struct
from fractions import Fraction
from input_combat_check import Checks

class SalvoChecks:
    def __init__(self,args):self.a=Checks(args);self.c=self.a.c
    def setup(self):
        a,c=self.a,self.c;a.reset();c.write(c.a4+13394,bytes(152))
        c.write(c.a4+23586,bytes(80));c.write(c.a4+23890,bytes(16))
        for off,v,fmt in [(13394,4,'B'),(13546,1,'B'),(13562,1,'B'),(13318,0,'h'),
                          (23826,8,'B'),(23842,16,'B'),(11384,0,'B'),(14290,10000000,'i'),
                          (14898,10000000,'i'),(15506,50000,'i'),(18162,0,'h'),(18466,16384,'h'),
                          (19198,0,'h'),(19694,250,'h'),(11700,8,'h')]:c.set(off,v,fmt)
        c.write(c.a4-32244,bytes.fromhex('4e75'))
        c.run(c.bob+0x1d280,args=struct.pack('>HH',0,1))
        assert c.get(30720)==20
        c.set(23890,1,'B');c.set(23906,7,'B')
    def run(self):
        a,c=self.a,self.c;references=[]
        for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
            self.setup();elapsed=Fraction(0);seen=1;positions=[c.get(14898+80,'i')];times=[0]
            for frame in range(1000):
                t=schedule[frame%len(schedule)];c.set(11700,t);elapsed+=Fraction(1,t)
                # Exact constant translation with an integral displacement at every T.
                c.set(14898,10000000+int(elapsed*6000),'i')
                c.set(17378,0,'i');c.set(17442,6000//t,'i');c.set(17506,0,'i')
                before=c.get(14898,'i');c.run(c.bob+0x1c5dc)
                assert c.get(14898,'i')==before,'source pose leaked'
                assert c.read(a.sym('dt_salvo_active'),2)==bytes(2)
                for slot in range(20+seen,28):
                    if c.get(13394+slot,'B'):
                        positions.append(c.get(14898+4*slot,'i'));times.append(elapsed);seen+=1
                if seen==8:break
            assert seen==8 and c.get(23826,'B')==0
            assert c.get(23890,'B')==0 and c.get(23906,'B')==0
            for n in range(1,8):
                assert abs(positions[n]-positions[0]-n*3000)<=1,(schedule,positions)
                assert Fraction(n,2)<=times[n]<=Fraction(n,2)+max(Fraction(1,t) for t in schedule)
            references.append(positions)
            print('salvo positions:',schedule,positions)
        assert max(max(abs(x-y) for x,y in zip(references[0],r)) for r in references)<=1
        self.setup();c.write(c.a4+13394+20,bytes([23])*32)
        for _ in range(10):c.set(11700,2);c.run(c.bob+0x1c5dc)
        assert c.get(23890,'B')==0 and c.get(23826,'B')==7
        a.options();print('full salvo, changing rates, source restoration and allocation failure passed')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    SalvoChecks(p.parse_args()).run()
