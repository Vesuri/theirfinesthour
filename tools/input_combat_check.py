#!/usr/bin/env python3
"""Execute input, projectile and damage regressions in Unicorn's 68000/68040 CPU.

Inputs are local FS-UAE fast-memory flight dumps and a normal slave/listing:
        make -C whdload VASMFLAGS='-L ../tmp/input-combat/release.lst'
        python3 tools/input_combat_check.py DUMP BASE SLAVE LISTING [--cpu 68000|68040]

No emulator services, timing or performance are modelled. Native game routines
run with controlled actor positions and mouse counts. Sound and impact artwork
are stubbed in this isolated memory only; native damage accounting is exercised.
Original bytes and captures remain local. Run from the repository root.
"""
import argparse, ctypes as C, os, random, re, struct, sys
from fractions import Fraction
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tfh_report import regions
u=C.CDLL(str(Path(os.environ.get('AMIGA_UNICORN', '~/.local/share/amiga/unicorn')).expanduser()/'lib/libunicorn.2.dylib'))
P=C.c_void_p; I=C.c_int; Q=C.c_uint64; Z=C.c_size_t
for n, args in {'uc_open':[I,I,C.POINTER(P)],'uc_ctl':[P,C.c_uint32], 'uc_mem_map':[P,Q,Q,C.c_uint32], 'uc_mem_write':[P,Q,P,Z], 'uc_mem_read':[P,Q,P,Z], 'uc_reg_write':[P,I,P], 'uc_reg_read':[P,I,P], 'uc_emu_start':[P,Q,Q,Q,Z], 'uc_close':[P]}.items():
    getattr(u,n).argtypes=args; getattr(u,n).restype=I
u.uc_strerror.argtypes=[I]; u.uc_strerror.restype=C.c_char_p
class CPU:
    def ck(self,e):
        if e: raise RuntimeError(u.uc_strerror(e).decode())
    def __init__(self, dump, base, model):
        self.h=P(); self.ck(u.uc_open(7,1<<30,C.byref(self.h)))
        self.ck(u.uc_ctl(self.h,7|(1<<26)|(1<<30),C.c_int(model)))
        self.ck(u.uc_mem_map(self.h,0,0x2000000,7))
        self.write(base,dump)
        rr={n:lo for lo,hi,n,o in regions(dump,base)}
        self.bob=rr['bob']; self.a4=rr['bob-data']+0x7ffe
        self.reg(17,0x2700); self.reg(5,self.a4)

    def write(self,a,b): self.ck(u.uc_mem_write(self.h,a,b,len(b)))
    def read(self,a,n):
        b=C.create_string_buffer(n); self.ck(u.uc_mem_read(self.h,a,b,n)); return b.raw
    def reg(self,r,v=None):
        x=C.c_uint32(v or 0)
        self.ck(u.uc_reg_read(self.h,r,C.byref(x)) if v is None else u.uc_reg_write(self.h,r,C.byref(x))); return x.value
    def set(self,off,v,fmt='h'): self.write(self.a4+off,struct.pack('>'+fmt,v))
    def get(self,off,fmt='h'): return struct.unpack('>'+fmt,self.read(self.a4+off,struct.calcsize(fmt)))[0]
    def run(self,pc,stop=0x1000,args=b''):
        self.reg(8,0x1f00000); self.write(0x1f00000,struct.pack('>I',stop)+args)
        e=u.uc_emu_start(self.h,pc,stop,2000000,1000000)
        if e: raise RuntimeError(f'{u.uc_strerror(e)} pc=bob:{self.reg(18)-self.bob:x}')
        assert self.reg(18)==stop,hex(self.reg(18))

# Routine patches used by these tests. Frame scheduling and hardware interrupts
# belong to the independent FS-UAE test, not this CPU-only harness.
PATCHES = [(0x14402,6,'replay_gunner_gate','PS'), (0x14430,6,'replay_gunner_gate','PS'), (0x18c82,6,'replay_gauge','P'), (0x1972e,6,'replay_gauge_update','P'), (0x1ab8,6,'replay_save_prefix','PS'), (0x1c2a,6,'replay_load_prefix','PS'), (0x1b96,6,'replay_save_extension','P'), (0x1c9a,6,'replay_load_extension','P'), (0x19ee,6,'replay_saved','P'), (0x1a46,6,'replay_restored','P'), (0x13bf8,6,'replay_record','P'), (0x16ab6,6,'replay_rewind','PS'), (0x15f52,6,'replay_read_continuous','P'), (0x1619c,6,'replay_skip_second','P'), (0x16a3a,6,'replay_single','P'), (0x1c51a,12,'dt_message_load','PS'), (0x1c536,6,'dt_message_age','P'), (0xc304,6,'dt_wait_message','P'), (0xc32e,6,'dt_wait_mission','P'), (0x1298c,6,'dt_wait_report','P'), (0x12dc4,6,'dt_wait_transition','P'), (0x128a0,12,'dt_wait_initial','PS'), (0x12eaa,8,'dt_contact_world','P'), (0x1d974,8,'dt_contact_plane','P'), (0x1dc4a,6,'dt_contact_next','PS'), (0x155d6,6,'dt_drift_x','PS'), (0x1563a,6,'dt_drift_y','PS'), (0x1569e,6,'dt_drift_z','PS'), (0x1467a,8,'dt_ground_steer','PS'), (0x149b0,8,'dt_recovery','PS'), (0x20d18,6,'dt_att_fall_limit','PS'), (0x20e40,6,'dt_att_fall_limit','PS'), (0x20d32,6,'dt_att_syncfall','PS'), (0x20e5a,6,'dt_att_syncfall','PS'), (0x2076c,6,'dt_att_syncpitch','PS'), (0x21004,6,'dt_att_ground','PS'), (0x21026,6,'dt_att_ground','PS'), (0x202ca,8,'dt_att_roll','PS'), (0x20340,6,'dt_att_roll_done','PS'), (0x2038c,6,'dt_att_roll_done','PS'), (0x203b6,8,'dt_att_pitch','PS'), (0x20438,6,'dt_att_pitch_done','PS'), (0x204fe,6,'dt_att_pitch_done','PS'), (0x20478,6,'dt_att_reflect','PS'), (0x2053e,6,'dt_att_reflect','PS'), (0x205f4,10,'dt_att_bank','PS'), (0x206a2,10,'dt_att_bank','PS'), (0x20cf6,6,'dt_att_stall','PS'), (0x20e1e,6,'dt_att_fall','PS'), (0x20f02,6,'dt_att_spin','PS'), (0x210de,6,'dt_aiadd','PS'), (0x21170,6,'dt_aisub','PS'), (0x218a2,6,'dt_surface_ai','P'), (0x24fee,6,'dt_script_wait','P'), (0x267c6,6,'dt_taxi_left','PS'), (0x267fe,6,'dt_taxi_right','PS'), (0x26e46,6,'dt_ai_lead','P'), (0x1cf98,6,'dt_gunner_lead','P'), (0x22090,6,'dt_air_ai','P'), (0x22eaa,6,'dt_player_ai','P'), (0xb07e,6,'dt_ai_skill','PS'), (0xbca6,6,'dt_ai_default','PS'), (0x21890,6,'dt_ai_initial_delay','PS'), (0x22002,6,'dt_ai_script_delay','PS'), (0x1f4f6,6,'dt_surface_damage','P'), (0x1ea46,6,'dt_air_damage','P'), (0x154b2,6,'dt_move','P'), (0x154ba,8,'dt_move_object','PS'), (0x15b52,6,'dt_move_next','PS'), (0x1c690,8,'dt_salvo_step','PS'), (0x1c780,6,'dt_salvo_end','PS'), (0x1d4e0,6,'dt_salvo_reload','PS'), (0x1c876,6,'dt_gun_request','P'), (0x1c5f8,8,'dt_gun_step','PS'), (0x1f77e,6,'dt_flak_launch','P'), (0x1f7a8,8,'dt_flak_created','P'),
           (0x1fdd0,6,'dt_flak_age','PS'), (0xb308,8,'dt_plane_generation','PS'), (0x1cdaa,10,'dt_shot_init','PS'), (0x15a2c,8,'dt_shot_age','PS'),
           (0x1e6f0,6,'dt_shot_damage_age','PS'), (0x1dc54,6,'dt_shot_cleanup','P'), (0x14e5e,8,'dt_world_clock','PS'), (0x176a2,6,'dt_effects','P'), (0x126c8,6,'dt_effect_init','PS'), (0xbf96,6,'dt_group_timer','PS'), (0x15954,6,'dt_debris_gravity','PS'),
           (0x1d5fc,12,'dt_debris_init4','PS'), (0x1d702,10,'dt_debris_init5','PS'), (0x1d500,8,'dt_bomb_init','PS'), (0x157c2,6,'dt_bomb_begin','PS'),
           (0x159f8,6,'dt_bomb_end','PS'), (0x176,8,'dt_input_kind','PS'), (0x19e,8,'dt_stick','PS'),
           (0x304,6,'dt_deadzone','P'), (0x1448a,6,'dt_roll','PS'),
           (0x144ee,6,'dt_turn','PS'), (0x154dc,6,'dt_steplen','PS'),
           *[(a,6,'dt_polar','PS') for a in (0x15576,0x157a0,0x15800,0x158b2,0x15ac6)],
           (0x1e516,6,'dt_hit','PS')]
SLAVE_BASE=0x1800000

def intersects(a,b):
    """Independent exact segment/axis-aligned-box oracle, inclusive boundaries."""
    lo,hi=Fraction(0),Fraction(1)
    for x,y in zip(a,b):
        if x==y:
            if abs(x)>500: return False
            continue
        p,q=sorted((Fraction(-500-x,y-x),Fraction(500-x,y-x)))
        lo=max(lo,p); hi=min(hi,q)
    return lo<=hi

class Checks:
    def __init__(self,args):
        self.c=CPU(Path(args.dump).read_bytes(),args.base,1 if args.cpu=='68000' else 4)
        self.syms={m[1]:int(m[0],16) for m in re.findall(r'^([0-9A-F]{8}) (\S+)$',Path(args.listing).read_text(encoding='latin1'),re.M)}
        slave=Path(args.slave).read_bytes()
        assert int.from_bytes(slave[24:28],'big')==0x3e9, 'expected one code hunk'
        self.blob=slave[32:32+int.from_bytes(slave[28:32],'big')*4]
        self.orig=Path('tmp/game/TheirFinestHour/data/bob').read_bytes()[0x28:]
        c=self.c
        self.saved=c.read(c.a4-0x7ffe,0xfa14)
        self.reset()
        for off,n,name,kind in PATCHES:
            c.write(c.bob+off,(b'\x4e\xb9' if kind=='PS' else b'\x4e\xf9')+struct.pack('>I',self.sym(name))+b'\x4e\x71'*((n-6)//2))
        c.write(c.bob+0x1a7c,bytes.fromhex('42674e71'))
        c.write(c.bob+0x1a8a,bytes.fromhex('70004e71'))
        c.write(c.bob+0xc31e,b'\x4e\x71'*6)  # FR-20 message reload is private.
        self.collision_patch(True)
        self.c.write(self.c.bob+0x1fee4,bytes.fromhex('4e75'))
        # Skip impact artwork; retain native hit, shooter, damage and removal logic.
        c.write(c.bob+0x1d63e,b'\x4e\x75')
    def sym(self,name): return SLAVE_BASE+self.syms[name]
    def reset(self):
        c=self.c
        c.write(c.a4-0x7ffe,self.saved); c.write(SLAVE_BASE,self.blob)
        c.reg(5,c.a4)
        for off in (-32532,-32526): c.write(c.a4+off,b'\x4e\x75') # sound dispatch
    def collision_patch(self,enabled):
        c=self.c
        for off,n in [(0x1e516,6),(0x1e5ba,4)]:c.write(c.bob+off,self.orig[off:off+n])
        if enabled:
            c.write(c.bob+0x1e516,b'\x4e\xb9'+struct.pack('>I',self.sym('dt_hit')))
            c.write(c.bob+0x1e5ba,bytes.fromhex('600000e2'))
        # Unicorn retains translated blocks across code writes; invalidate when
        # switching original/fixed routines in the same engine.
        c.ck(u.uc_ctl(c.h,9|(2<<26)|(1<<30),Q(c.bob),Q(c.bob+0x31e40)))
    def segment(self,a,b):
        c=self.c;c.reg(6,0x1e00000)
        for i,(x,y) in enumerate(zip(a,b)):
            c.write(0x1e00000-6-4*i,struct.pack('>i',x))
            c.write(0x1e00000-18-4*i,struct.pack('>i',y))
        c.run(self.sym('dt_hit_test')); return bool(c.reg(9))
    def options(self):
        c=self.c; self.reset()
        c.write(self.sym('_improve'),struct.pack('>I',0))
        before=c.read(c.bob,0x31e40)
        c.run(self.sym('timing_patch'))
        assert c.read(c.bob,0x31e40)==before
        for option,shift in [(0,1),(1,0),(2,2),(3,3),(4,1),(0xffffffff,1)]:
            c.write(self.sym('_improve'),struct.pack('>I',1))
            c.write(self.sym('_custom3'),struct.pack('>I',option))
            # Stop before beam measurement / resload: only option decoding is tested.
            c.run(self.sym('timing_patch'),stop=self.sym('dt_rate'))
            assert int.from_bytes(c.read(self.sym('dt_mouse_shift'),2),'big')==shift
        self.reset()
        print('options: original-game timing gate and all mouse gain selections passed')
    def geometry(self):
        c=self.c;rng=random.Random(274)
        for _ in range(500):
            x,y=rng.getrandbits(32),rng.getrandbits(32)
            c.reg(9,x);c.reg(10,y);c.run(self.sym('dt_mul64'))
            assert c.reg(9)+(c.reg(10)<<32)==x*y
        cases=[((900,100,0),(-300,-1100,0)),((900,100,0),(300,-500,0)),
               ((300,-500,0),(-300,-1100,0)),((500,500,500),(500,500,500)),
               ((501,0,0),(501,0,0)),((-500,-500,-500),(-500,-500,-500))]
        for _ in range(2000):
            span=rng.choice([500,501,1000,20000,20000000])
            cases.append(tuple(tuple(rng.randint(-span,span) for _ in range(3)) for _ in range(2)))
        for a,b in cases:
            assert self.segment(a,b)==intersects(a,b),(a,b)
            assert self.segment(b,a)==intersects(a,b),(b,a)
        print(f'geometry: {2*len(cases)} segments and 500 full-width products passed')
    def damage_segment(self,a,b):
        self.reset();c=self.c
        c.write(c.a4+13394,bytes(152));c.set(13395,4,'B');c.set(13394+52,20,'B')
        c.set(21102+52,0,'B');c.set(13866+52,1,'B');c.set(13867,2,'B')
        c.set(22588,0);c.set(22707,0,'B');c.set(20798+52*2,1)
        for prev,cur,bullet,x,y in zip((16610,16674,16738),(14290,14898,15506),(16802,16994,17186),a,b):
            c.set(prev+4,10000000,'i');c.set(cur+4,10000000,'i')
            c.set(bullet,10000000-x,'i');c.set(cur+52*4,10000000-y,'i')
        c.run(c.bob+0x1e3d6,args=struct.pack('>H',52))
        return c.get(22588),c.get(13394+52,'B')
    def damage(self):
        a,b,m=(900,100,0),(-300,-1100,0),(300,-500,0)
        self.collision_patch(False)
        native=[self.damage_segment(x,y)[0] for x,y in [(a,b),(a,m),(m,b)]]
        assert native[0]>0 and native[1:]==[0,0],native
        c.write(c.bob+0x1a7c,bytes.fromhex('42674e71'))
        c.write(c.bob+0x1a8a,bytes.fromhex('70004e71'))
        c.write(c.bob+0xc31e,b'\x4e\x71'*6)  # FR-20 message reload is private.
        self.collision_patch(True)
        fixed=[self.damage_segment(x,y)[0] for x,y in [(a,b),(a,m),(m,b)]]
        assert fixed==[native[0]]*3,fixed
        assert self.damage_segment((600,1000,0),(600,-1000,0))==(0,20)
        # A real crossing shares a time interval; different-axis crossings alone
        # must not cause a hit (the original could accept these diagonal misses).
        a,b=(2000,10000,0),(-10000,-2000,0)
        assert not intersects(a,b) and self.damage_segment(a,b)==(0,20)
        print(f'native damage coarse/split: {native}; fixed: {fixed}; misses preserved')
    def mouse(self):
        c=self.c
        for axis in [0,1]:
            for shift in range(4):
                for total in [-200,-50,-2,2,50,200]:
                    results=[]
                    for t in [4,8,25,50,60]:
                        self.reset();c.write(self.sym('dt_mouse_shift'),struct.pack('>H',shift))
                        c.set(11698,t);c.set(11700,t);c.set(19198,0);c.set(18830,16384)
                        for i in range(t):
                            delta=(i+1)*total//t-i*total//t
                            for off,val in [(11958,0 if axis else delta),(11960,delta if axis else 0),
                                            (11940,0),(-4696,0),(-4694,0)]:c.set(off,val)
                            c.run(c.bob+0x112);c.run(c.bob+0x13c6e)
                        results.append(c.get(18830)-16384 if axis else c.get(19198))
                    assert max(results)-min(results)<=1,(axis,shift,total,results)
        # Mouse gain must not multiply joystick or keyboard controls.
        for key,joy in [(1,0),(2,0),(3,0),(4,0),(0,20),(0,-20)]:
            vals=[]
            for shift in range(4):
                self.reset();c.write(self.sym('dt_mouse_shift'),struct.pack('>H',shift))
                for off,val in [(11698,50),(11958,0),(11960,0),(11940,key),(-4696,joy),(-4694,joy)]:c.set(off,val)
                c.run(c.bob+0x112);vals.append((c.get(11968),c.get(11970)))
            assert len(set(vals))==1,vals
        print('mouse: both axes, both signs, 4 gains, 5 update rates; keyboard/joystick unaffected')
    def projectiles(self):
        c=self.c
        for t in [8,25,50,60]:
            for distance in [1000,5000,20000]:
                self.reset();c.write(c.a4+13394,bytes(152))
                for i in [0,1]:
                    c.set(13394+i,1 if i==0 else 4,'B')
                    for off,v in [(14290,10000000),(14898,10000000+(distance if i else 0)),(15506,50000)]:c.set(off+4*i,v,'i')
                    for off,v in [(18162,0),(18466,16384),(18830,16384),(19694,0),(19470,0),(19502,0),(19534,0),(22586,0)]:c.set(off+2*i,v)
                c.set(22707,0,'B');c.set(11698,t);c.set(11700,t);c.set(30914,1)
                c.run(c.bob+0x1cad0,args=struct.pack('>HHH',0,0,2))
                for frame in range(t*2):
                    c.run(c.bob+0x154b2)
                    if not c.get(13394+52,'B'):break
                    c.run(c.bob+0x1e3d6,args=struct.pack('>H',52))
                    if c.get(22588):break
                assert c.get(22588)>0 and c.get(13394+52,'B')==0,(t,distance,frame)
        print('projectiles: native creation, movement, hit, damage and removal passed at 8/25/50/60 updates/s')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump');p.add_argument('base',type=lambda v:int(v,0));p.add_argument('slave');p.add_argument('listing')
    p.add_argument('--cpu',choices=['68000','68040'],default='68040')
    args=p.parse_args();t=Checks(args)
    t.options();t.geometry();t.damage();t.mouse();t.projectiles()
    print(f'{args.cpu} input/combat checks passed (CPU routines, not a timing measurement)')
if __name__=='__main__':main()
