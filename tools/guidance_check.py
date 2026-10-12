#!/usr/bin/env python3
"""FR-09 synchronized native guidance and bomb-pool flight regression."""
import argparse,ctypes as C,struct
from bomb_check import BombChecks
from input_combat_check import u,P,Q,I

class GuidanceChecks:
    def __init__(self,args):
        self.b=BombChecks(args);self.a=self.b.a;self.c=self.a.c
        self.calls=0;self.transitions=[]
        callback=C.CFUNCTYPE(None,P,Q,I,P)
        def observe(handle,address,size,user):
            c=self.c
            if address==c.bob+0x1ff04:self.calls+=1
            elif address==c.bob+0x1ff5c:
                slot=c.reg(13)
                self.transitions.append((self.calls,slot,tuple(c.get(off+4*slot,'i') for off in (14290,14898,15506))))
        self.callback=callback(observe);self.hooks=[]
        u.uc_hook_add.argtypes=[P,C.POINTER(Q),I,P,P,Q,Q];u.uc_hook_add.restype=I
        for off in (0x1ff04,0x1ff5c):
            hook=Q();self.c.ck(u.uc_hook_add(self.c.h,C.byref(hook),4,self.callback,None,self.c.bob+off,self.c.bob+off));self.hooks.append(hook)
    def drop(self,schedule,native=False,altitude=60000,legacy=False):
        b,a,c=self.b,self.a,self.c
        b.enable(not native);b.setup(altitude=altitude,mode=1)
        c.set(13394,4,'B')
        for slot in (21,22):
            c.run(c.bob+0x1d280,args=struct.pack('>HH',0,1));assert c.get(30720)==slot
            c.set(14290+slot*4,10000000+(slot-20)*1000,'i')
            c.set(15506+slot*4,altitude+(slot-20)*1000,'i')
        c.set(13394,0,'B');c.set(16114+80,10010000,'i');c.set(16322+80,10050000,'i')
        self.calls=0;self.transitions=[];c.set(11716,0)
        c.write(c.bob+0x1fee4, a.orig[0x1fee4:0x1fee6] if legacy else bytes.fromhex('4e75'))
        if legacy:
            # Keep the previous per-bomb fixed-step patch; remove only FR-09's pool wrapper.
            for off,n in ((0x154b2,6),(0x154ba,8),(0x15b52,6)):
                c.write(c.bob+off,a.orig[off:off+n])
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
        # Native reference: prescribed 32-tick guidance cadence, original whole-pool movement.
        for frame in range(10000):
            t=schedule[frame%len(schedule)];c.set(11700,t)
            if legacy:c.run(c.bob+0x1fee4)
            if native and frame%32==0:
                # Recreate the native prologue, enter after its frame-count gate.
                c.write(0x1100,bytes.fromhex('4e55fffc48e70c004ef9')+struct.pack('>I',c.bob+0x1ff04))
                c.run(0x1100)
            c.run(c.bob+0x154b2)
            for slot in (20,21,22):
                if c.get(15506+slot*4,'i')==0:c.set(13394+slot,0,'B') # contact removes native bomb
            if all(c.get(15506+4*slot,'i')==0 for slot in (20,21,22)):break
        else:raise AssertionError('guided bombs never landed')
        assert c.get(11700)==t
        assert c.read(a.sym('dt_bomb_batch'),2)==bytes(2)
        assert self.transitions and all(c.get(20766+slot-20,'B')==3 for slot in (20,21,22))
        return tuple(self.transitions),tuple(tuple(c.get(off+4*slot,'i') for off in (14290,14898,15506)) for slot in (20,21,22))
    def run(self):
        old8=self.drop([8],legacy=True);old50=self.drop([50],legacy=True)
        assert old8!=old50,'legacy guidance reproduction did not diverge'
        print('legacy guidance with fixed bomb motion differs at 8/50:',old8,old50)
        for altitude in (60000,49152,49151,5000):
            reference=self.drop([64],True,altitude)
            for schedule in [[t] for t in (2,4,8,25,50,60)]+[[8,50,25,60,4]]:
                got=self.drop(schedule,False,altitude)
                assert got==reference,(altitude,schedule,reference,got)
            print('native guided cohort transition/impact:',altitude,reference)
        self.a.options();print('all guided transition positions and three-bomb impacts match native fixed-step reference')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
    p.add_argument('slave');p.add_argument('listing');p.add_argument('--cpu',choices=['68000','68040'],default='68000')
    GuidanceChecks(p.parse_args()).run()
