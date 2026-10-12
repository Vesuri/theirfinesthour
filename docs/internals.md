# Internals: the game and the patches

What is known about `data/bob` v1.1 and how each slave change works. Addresses are `bob` hunk-0
offsets (`bob:OFFSET`, the slave's `resload_PatchSeg` numbering); `NNNN(a4)` are small-data
globals with `a4` = data hunk + `$7FFE`; `data:OFFSET` is an offset into the data hunk.
Running and measuring: `development.md`.

## The program

`data/bob` is Aztec C (Manx): `link a5` prologues, small-data `d16(a4)` globals, library calls
through a `jsr d16(a4)` jump table that executes in the data hunk. Hunk 0 code at file `$28`,
`$31E40` bytes; hunk 1 data, `MEMF_CHIP`, `$AB70` bytes in the file, `$FA14` allocated; hunk 2
BSS, 4 bytes. `bob:00000` jumps to the startup at `bob:30b4a`. Some routines are compiled C
(locals in the stack frame), the 3D maths and drawing are hand-written assembly.

**The slave** (`whdload/TheirFinestHour.s`) is Psygore's v1.1: KickEmu (Kickstart 34.005 +
RTB) with HDINIT, BOOTDOS, DOSASSIGN; assigns `BobData`, `BOB1`, `BOB2` to `data`; loads `bob`
(or `mb`, the Mission Builder, with `CUSTOM1=1`), identifies it by CRC16 and applies a patch
list: v1.0 `$201F` and KIXX `$2D72` (`PL_P $57a` quit, `PL_NOP $60e` large-memory setting,
`PL_NOP $1bba6` manual protection), v1.1 `$274F` (the same with `$1bbd6`), `mb` `$A996`. The
improvements below apply to v1.1 only. Quit key `$5D` (numeric `*`).

## Display, interrupts, input

- **Level-3 handler `bob:28d4c`** (vector `$6C` in play). On VERTB (`bob:28d66`) it writes
  COP1LC from one of two copper lists chosen by `-7964(a4)`, clears the swap request
  `-7962(a4)`, increments the VBL count `-8010(a4)`, reads the mouse (`bob:29a76`; deltas of
  JOY0DAT's counters in `bob:29bb2`), buttons (`-8008(a4)`) and joystick (`bob:29c00`), then
  runs the sound routine (`bob:2b66c`). BLIT and COPER are only acknowledged. Level 2
  (keyboard): `bob:28e2a`.
- **Frames:** at the end of a frame in flight (`bob:12f2c`) the game sets the buffer to show,
  raises the swap request (`bob:12f38`) and flips the draw buffer without waiting.
- **Rendering:** the 3D view is drawn into a packed 4-bit chunky buffer (8 pixels per
  longword, 160 bytes per row; three buffers rotate, `12084/12088/12092(a4)`), then converted
  by the C2P at `bob:283a0` into 4 bitplanes 8 000 bytes apart (40-byte rows). The C2P compares
  each longword with the frame drawn two frames earlier and converts only changed ones,
  through a per-byte cockpit mask (`-9778(a4)`).
- **Chip memory the hardware reads:** bitplanes (2 × 32 000, `bob:28a80`/`28ab0`), copper
  lists (2 × 200, built at `bob:28b0a..28bd0`), the sound bank (`bob:29ac`), and 40 sprite bytes
  in the data hunk (`data:613C` pointer, `data:6160` empty sprite). Everything else in the data
  hunk is CPU-only.
- **Menu pointer** `11816/11818(a4)`, low-res pixels, clamped to `11832..11838(a4)`; one pixel
  per mouse count. The menu loop is `bob:4c18`, the choice in `11982(a4)`.
- **Random generator** `bob:2915c` (LFSR on `-7830/-7828(a4)`); the main menu calls it
  continuously, so input timing decides the RNG state at the start of a flight.

## Game time

No clock is read in flight. Each simulation step advances `1/T` seconds of game time, with
**`T = 11698(a4)`**: a rendering benchmark at boot (`bob:2b84..2c5c`) sets `T = 380 / fields
taken`, minimum 4, minus 2 above 6. The step code divides by `11700` (T, or `max(T/3, 2)`
while the `T` key accelerates time) and uses `11702 = 11700/8 + 1`. So the original's game
speed is fps/T: right only at the frame rate the benchmark predicted (the A500 ran 1.9× real
time, a 68030/50 at 0.55×). The benchmark assumes 50 fields per second; nothing in the game
checks for NTSC.

State: plane position `11668/11672(a4)` (x east, y north), altitude `11676`, heading word
`11680` (65 536 = 360°); per-plane arrays (player = 0): heading `18162`, roll `19198`. Stick
input: `bob:112` turns the counts since the last frame into a deflection (`11968/11970`),
divided by T in `bob:13c6e`.

**Ground detail** `11196(a4)`, cycled 0 → 1 → 2 by Ctrl+G (also Alt, Amiga) in flight:

| Level | Map scenery `bob:11138` | Ground polygons `bob:104b6` | Objects (`bob:10a00`, by detail byte) |
|---|---|---|---|
| 0 | yes | yes | marked 0 |
| 1 | no | yes | marked ≤ 1 |
| 2 | no | no (sea only) | all |

At boot (`bob:46`) a benchmark T > 10 picks level 2, otherwise 1.

## Sound

A sound descriptor (channel tables at `bob:2771e`) has a start segment (`6(a0)`, length
`10(a0)`), a repeat segment (`12(a0)`, `16(a0)`) and an envelope counted in fields (sustain
`28(a0)`). The VBL routine `bob:2b66c` writes the start segment and enables DMA, then queues the
repeat segment in the next field.

## The slave's changes

The game changes below make up **Enhanced framerate**: off by default, and enabled with
`CUSTOM2=1`. With CUSTOM2 unset/0, the enhancement patches leave the original bytes
untouched. The sound fix and cache setup are always on. `CUSTOM1=1` runs the Mission Builder. `CUSTOM3` selects
mouse gain in the improved game:
0/unset = 2x (default), 1 = 1x, 2 = 4x, 3 = 8x; other values use the default.

**Always on**

- **Caches:** the slave defines KickEmu's `CACHE` (WHDLoad's default setup: chip memory
  uncached, caches on) and no longer switches the caches off; the user's WHDLoad options
  override. Without an MMU (68020, 68030 without the `MMU` option) WHDLoad keeps the caches off.
- **One-shot sounds** (`sound.s`): one-shots have an empty repeat segment, and the routine then
  wrote nothing, so the channel replayed the sample until the envelope ended. An empty repeat
  now queues a cleared chip word (`PL_PS $2b6a4`).
- **Memory:** 768 KB expansion memory (`FASTMEMSIZE`); the game uses 666 KB of it in flight
  with the improved frame rate.

**Faster rendering, full ground detail** (`render.s`, `transform.s`)

- **Fast memory:** the chunky buffers are allocated `MEMF_PUBLIC` (`bob:27d8`, `2822`) and their
  blitter fill (`bob:29084`) is a CPU fill. During `LoadSeg` an exec `AllocMem` filter drops
  `MEMF_CHIP`, so the data hunk lands in fast memory; the 40 sprite bytes are copied to chip
  and the copper list immediates (`bob:28b34`, `28b4e`, `28b9a`, `28bb4`) and the two sprite
  `lea` sites (`bob:28ef0`, `29e8e`) are redirected. No other relocation points into them.
- **Merge C2P** (`c2p_merge`, at `bob:283a6`): compares and converts 32 pixels at a time with a
  5-pass merge network (bit-group swaps 16/8/4/2/1) and writes each plane as a longword
  through the mask (no write where the mask is 0, a direct write where it is all ones). Window
  widths not a multiple of 4 longwords, other plane spacings or odd addresses go to the
  original code.
- **Point transform** (`xform`, at `bob:2f4ae`): the 3×3 rotation of (point − camera) with the
  original's sign-magnitude arithmetic, in registers instead of data-hunk globals (every other
  user of those globals writes them before reading). On 68020+ each term is one `mulu.l`
  (bits 16–47 of the product equal the original's two 16×16 halves).
- **Projection** (`xproj`, at `bob:2f28a`, the 32-bit path of `bob:2f160`): five rounded
  sign-magnitude products in registers, one `mulu.l` each on 68020+. Its callers use only D0.
- **Projection entry** (`xpnorm`, at `bob:3041c`, the C entry with x, y, z on the stack):
  shifts x, y (as magnitudes) and z right together until x | y | z fits in 15 bits, into
  `4240`–`4244(a4)`, then `bob:2f160`. One shift by the count the original's one-bit passes
  reach (`bfffo` on 68020+) instead of ~7 passes, and only D1–D7/A0 saved (the registers
  `bob:2f160` and its callees use) instead of D1–A3/A6.
- **Perspective divide** (`xdiv20`, at `bob:2f374`, 68020+ only): one `divu.l` and one
  `mulu.l` for the original's two `divu.w` and two `mulu.w`.
- **Scenery clear** (`clr_scenery`, at `bob:11454`): `bob:1142c` cleared three 20-byte frame
  arrays a byte at a time; now 15 long-word writes, leaving the counter `-24(a5)` = 20.
- **Scenery tiles** (`tile_scenery`, at `bob:11138`): the map scenery around the plane (11
  rings of tile offsets from `12136(a4)`, looked up in the 64×64 nibble map at `12132(a4)`),
  compiled C with every variable in its frame, now in registers. It calls `bob:1133a` with the
  same argument and the same globals (`26360`–`26377(a4)`) as the original. It runs only at
  ground detail 0.
- **Scenery vertices** (`scen_verts`, at `bob:11604..11b34`): `bob:1142c`'s two loops over a
  polygon's vertices (transform each new one through `bob:2f48c` or average a midpoint vertex,
  count those behind the camera; then copy, average or project each screen point into
  `9126(a4)`), compiled C with every index in the frame, now in registers. Same calls, frame
  arrays and globals at each of its three exits (drawn, clipped, all behind). In the checked
  flights (`scen`, over 1 000 polygons per build) no polygon was all behind, used a midpoint vertex
  or shared a projected point; those paths follow the disassembly but are unexercised.
- **Ground detail:** the level fast machines boot with (`bob:50`) is 0 instead of 2.

All replaced routines give the original's results: checked against models of the originals on
the A500-eq (68000 code) and the 68020 (68020 code, and the scenery tiles and vertices, which
the A500 does not draw at its detail level), and the models against the originals.

**Frame pacing** (`render.s`)

The original flipped buffers without waiting, so on a fast CPU frames overtook the display:
some were never shown, and drawing restarted in the buffer on screen. The C2P now waits until
the VBL handler has taken the pending swap request (`PL_PS $283a0`), and the handler strobes
COPJMP1 while the beam is above line 36 (the display starts at line 41), so the new buffer is
shown in the same field (`PL_PS $28d86`); later in the field the request stays pending.

**Real-time simulation** (`timing.s`)

- **T per frame** (`bob:12954`, top of the flight loop): T = field rate / average frame length,
  as an integer within 4 and the field rate. The average moves 1/8 of the way to each frame's
  length; the time owed (frame lengths less the steps taken) carries, and a quarter of it is
  added to the next step aimed at. A frame of more than 25 fields (a pause, a disk load) adds
  no time. `11700`/`11702` follow T, keeping time acceleration. Each flight starts from the
  boot T (`bob:ad6e`).
- **Intervals in frames:** the game sets many countdowns as multiples of `11700` and counts
  them down once per frame: a gun's reload `23106` = T/3 (`bob:1cc30`, counted at `bob:1c61e`),
  an object's life `20798` = 2T for a bullet (`bob:1cda6`, counted at `bob:15844`). They last
  their time only while T matches the frames that follow; hence the average. With T from the
  last frame alone, frames of 2 and 3 fields on the 68020 gave T 25 and 17 by turns and gaps
  between shots of 12 or 20 fields.
- **Field rate:** measured at boot from the beam's highest line (PAL 312, NTSC 262). The boot
  benchmark itself stays as it is: its T is used outside flight too.
- **Stick:** the counts grow with the frame's length and the game divides them by T, so the
  slave scales them by T/8 at the end of `bob:112`: response is independent of the frame rate
  and, at 1x sensitivity, equal to the original's at T = 8 (about the A500's rate).
  `bob:176` records which axes came from the mouse before clearing the accumulators;
  mouse gain is applied after T/8, before the signed-word limit. The joystick keeps its
  existing scaling and keys set deflection directly. `bob:304` retains the original
  joystick/keyboard dead zones but preserves nonzero mouse movement: discarding small
  per-frame deflections lost counts depending on how a movement was split into frames.
- **Mouse wrap** (replaces `bob:29bb2`): more than 127 counts in a field read as a move the
  other way; a reading of 64 or more against an equally large opposite previous one is taken
  as wrapped.
- **Fractions at large T:** per-step increments are small at T = 50, and the game truncated
  each one. Positions: the object loop (`bob:154ba`, 152 objects) takes a step length
  `round(speed·4660/256 / 11700)` (`bob:154dc`) and splits it into x/y/z by heading and pitch
  (`bob:2eb4a`, each component truncated). The slave keeps the length's fraction and calls the
  split (`bob:2e9c0`) with the 16.16 length, which returns 16.16 components; each object's x, y
  and z fractions carry to its next step (`bob:15576`, `157a0`, `15800`, `158b2`, `15ac6`).
  The player's rates (`bob:13c6e`, plane `13318(a4)`): roll `30676` = `19230[P]`·|roll stick|/T
  (`bob:1448a`), and from the pitch stick, v = `19134[P]`·|pitch stick|/T, heading `30680` =
  v·sin(roll)/4 and pitch `30682` = v·cos(roll) (`bob:144ee`, the game's sine table). Each is
  computed in 16.16 with the plane's fraction carried. The AI planes' turn (`bob:210a6`):
  v = ((a/3)/`11700`·`22346[plane]`)>>16 from the bank a folded to 0..16384, added to the
  heading `18162` for a left bank and subtracted for a right one; it is computed in 16.16,
  signed, with the fraction carried per object (`bob:210de`, `21170`).

## Mouse and projectile regression checks (1.3b)

`tools/input_combat_check.py` runs the native input, flight model, projectile creation,
movement, collision and damage routines under Unicorn's 68000 and 68040 models, using a
local FS-UAE flight snapshot for the game tables and relocated calls. It patches only
isolated test memory. Sound dispatch and impact artwork are stubbed; native damage and
projectile removal remain active. It is a correctness instrument, not an FPS instrument.

- For each mouse axis and direction, 2, 50 and 200 counts over one second give results
  within one angle unit at T = 4, 8, 25, 50 and 60, for all four gains. Keyboard and
  joystick input are unchanged by the mouse gain.
- The original collision routine (`bob:1e3d6`) can miss a true crossing when split into
  smaller steps. Relative endpoints (900, 100, 0) -> (-300, -1100, 0) produce damage 4;
  splitting at (300, -500, 0) gives damage 0 for either subsegment. This reproduces a
  frame-dependent miss; it does not prove that every reported missed shot had this cause.
- The improved test (`bob:1e516`, `dt_hit`) intersects the swept relative segment with
  the original 500-unit tolerance on each axis. Exact rational entry/exit intervals
  share one time across all three axes; unsigned 64-bit cross products avoid rounding.
  Source/team exclusions, damage, hit effects and projectile removal stay native. The
  attacker bookkeeping is entered at `bob:1e590`, then a branch at `bob:1e5ba` reaches
  the original hit path at `bob:1e69e`. A miss resumes at `bob:1e75e`.
- The reproduction gives damage 4 with either subdivision after the fix. Geometry is
  checked against an independent rational oracle, including reversed segments, boundary
  contacts and misses whose axes cross at different times. Straight-on native projectiles
  at three distances hit and apply damage at 8, 25, 50 and 60 updates per second.

The mouse normalization already worked for ordinary unsaturated movement in 1.2b. Its
fixed low gain was a separate handling problem; 1.3b adds a usable default and a choice.
Maximum deflection is still limited, so arbitrary rapid swipes need not preserve every
count. The regression does not cover all aircraft, gunner positions or combat replays.

## Bomb audit and fix (unreleased 1.3b, 12 October 2026)

Bombs use movement class 3, created at `bob:1d280` / `bob:1d332` in slots
20-51. Their ground impact dispatch (`bob:1db46`) calls `bob:1df1e` after
altitude reaches zero. This is separate from the bullet/aircraft test patched
at `bob:1e516`; that fix does not make bomb impacts frame-independent.

- Gravity already carries its fractional acceleration: `bob:158d8..15950`
  divides 22 by T using `bob:29120`, carrying the fractional part in
  `20334[object-20]`. It does not have the minimum-one-per-frame acceleration
  used by the other falling-object classes at `bob:15954`.
- Vertical displacement still uses the original integer speed-to-step conversion
  at `bob:159a8` / `bob:159da`. Unlike horizontal movement, it has no displacement
  fraction carry. The updated integer vertical velocity is used for that entire
  step. The ground clamp at `bob:159f8` does not interpolate the horizontal
  position back to the time of contact.
- The separate target-footprint check `bob:1e1fc` tests the resulting impact
  position; `bob:1f456` adds bomb-type damage without a frame-rate multiplier.
  Release cooldown is T/2 (`bob:1d4e0`, decremented at `bob:1c6b6`), rather
  than a fixed number of frames, though changing T during a countdown can drift.

`tools/bomb_check.py` takes the same dump/base/slave/listing arguments as
`input_combat_check.py`. A controlled native level drop from altitude 50000,
heading 0 and speed 250, with enhanced horizontal movement, gives:

| Updates/s | Time to ground (simulation seconds) | Forward travel (game units) |
|---|---|---|
| 8 | 15.75 | 71373 |
| 50 | 15.84 | 71766 |

A fixed type-22 target with unchanged native dimensions, positioned near the
8 Hz impact's footprint edge, receives damage 110 at 8 Hz and no hit at 50 Hz.
This is a controlled CPU-routine reproduction, not a played mission or proof
that centre hits generally fail. The first probe also used a synthetic small
footprint; the native-dimension edge case above confirms that the effect is
not limited to that synthetic geometry. Sound/HUD are stubbed, while native
bomb creation, movement, target footprint and damage routines execute.
Map/terrain classification and the full impact effects were not exercised.

**1.3b correction:** bomb movement uses a fixed 64 Hz simulation clock, rather
than integrating once per rendered frame. `dt_bomb_begin` (`bob:157c2`) repeats
only the native movement block for class-3 objects in slots 20..51;
`dt_bomb_end` (`bob:159f8`) returns each step to that wrapper. It preserves the
native acceleration carry, drag, directed-flight branch and horizontal precision.
The wrapper stops at the first step reaching ground, before any further horizontal
movement, and the normal impact/damage dispatch runs once afterwards. No input,
AI, sound or whole-world update is repeated. T is temporarily 64 inside the block
and restored before continuing the world loop; time acceleration uses the supplied
simulation divisor as before.

`dt_bomb_init` (`bob:1d500`) clears the slot's time accumulator and XYZ fractions
and sets its initial native drag countdown to 5*64. Each frame adds ceil(64*65536/T)
to its 16.16 tick accumulator; the rounding error is less than 1/(64*65536) seconds
per outer update. Pending time is less than 1/64 second; impact notification still
waits for the outer world update. Ground contact is resolved at a fixed-step
boundary, not an analytic sub-step intersection. This makes its spatial rounding
consistent across rendering rates; it does not eliminate all discretisation.

The revised `tools/bomb_check.py` compares enhanced movement at divisors 2, 4, 8,
25, 50, 60 and changing-divisor sequences against the native movement at 64 Hz
(with the previous horizontal-precision patches but without bomb scheduling).
Landing coordinates match exactly for level, diving, climbing, near-ground,
high-altitude, stationary and preset directed-mode drops. The level case now
lands 71853 units forward at both 8 and 50 updates/s. Native type-22 footprint
edge tests retain the same 110 damage or miss at every tested rate, including
the complete native impact/removal path with controlled surface classification.
Eight-bomb salvos and slot reuse pass; both 68000 and 68040 CPU models are checked.

The native 64 Hz reference is a compatibility check, not an independent physical
ballistics model. Bombing sights, changing automatic guidance decisions (the
outer AI still updates separately), actual terrain classification and physical
Amiga gameplay remain unverified. Rendering cost with many bombs is not measured. A VERIFY boot into the training
flight on FS-UAE (68040/40, 8 MB fast, Enhanced framerate enabled) also completed;
the live code dump confirms all three bomb hooks point to their expected slave
routines. This smoke check did not drop bombs or measure frame rate.

## Measurements

Reference measurements from 1.2b below use 1x mouse gain. The 1.3b firing run is labelled
separately; the old tape-3 bank measurement does not describe the new 2x default.
Fixed window (tape 2), improved frame rate unless stated. These measurements predate
the opt-in toggle; with the current slave use `CUSTOM2=1` for enhanced and unset/0
for original:

| Machine | Ground detail | Frame rate |
|---|---|---|
| A500-eq, original | 1 | 7.6 fps |
| A500-eq | 1 | 7.5–7.6 fps |
| A500 + 2 MB fast, original | 1 | 7.7 fps |
| A500 + 2 MB fast | 1 | 7.8 fps |
| A1200 (68020, chip only), original | 1 | 10.6 fps |
| A1200 (68020, chip only) | 1 | 12.5 fps |
| 68020 + 8 MB fast, original | 1 | 18.8 fps |
| 68020 + 8 MB fast | 0 | 23.5 fps |
| 68030/50 + 8 MB fast, original | 2 (sea only) | 15.6 fps |
| 68030/50 + 8 MB fast | 0 | 50.0 fps |

Game speed (`speed.py`, same flight, nominal 4 715 units/s): A500-eq original 9 058 units/s
(1.9× real time); improved 4 716 on the A500-eq and 4 712 on the 68030/50 at 50 fps (4 649
before the fraction carry). A 30° bank (tape 3, `--turn`): 30.8° and 8.32°/s on the A500-eq,
30.8° and 8.24°/s on the 68030/50 (before the fraction carry 30.2° and 7.97°/s there). An AI
plane's turn over 300 steps there (tape 2, `aiturn` check): 4 913 heading units against 4 912.9
exact (4 764 before). Time acceleration (tape 6) gives 3.15–3.5×.

The 1.3b combined input/collision VERIFY build on an emulated 68040/40 with 8 MB fast
memory, full detail and tape 8 firing: 99 swaps in 99 PAL fields (50.0 fps). The capture
starts at tape field 7843; 50 state snapshots record three ammunition decrements with
16-field gaps. This verifies sustained firing and the loaded patch in FS-UAE; it is not
an on-hardware result or an all-missions combat test.

Rate of fire on the 68020 (tape 8, `guns.py`, 18 shots): gaps between shots of 14–18 fields,
mean 16.1 (a third of a second is 16.7), against 12 or 20 with T from the last frame alone.
Game speed with the average (`speed.py`): 4 720 units/s on the 68020 (T 18–26), 4 708 on the
A500-eq (T 7–8), 4 713 on the 68030/50 (T 50); 23.7 fps on the 68020 and 50.0 on the 68030/50.

Map scenery on the 68020 (`tfh_report.py`, cycles per call including callees): `bob:1142c`
17 481 → 14 863 with the vertex loops and the projection entry (its own code 6.1% → 0.9% of
the frame), `bob:3041c` 1 360 → 1 082; 22.4 → 23.5 fps in the same window. On the A500-eq
(no map scenery at level 1) `bob:3041c` 3 775 → 3 500 (0.6% of the frame; 7.6 fps either way).

Remaining 68020 hotspots at level 0 (of the frame): textured spans `bob:2bace` ~8.7% (already
tight assembly), the C2P ~9% (mostly its compare), the projection with its divides ~10%
(`bob:3041c` and callees), the scenery tiles 5.8% with their `bob:1133a` calls. 25 fps needs
2 fields per frame, about 6% less than now.

## Known limitations

- **Truncation at large T, remaining:** the fractions carry for every object's position, the
  player's roll, turn and pitch rates and the AI planes' turn. Not covered: ground steering
  (`bob:146aa`), the wind terms (`bob:155d6`) and other per-step increments divided by T.
  (`bob:1d60e` and `1d72c` set a spawned fragment's heading once, not per step.)
- **Still counted in fields** (17% faster at 60 Hz, as in the original on NTSC): the joystick
  ramp (`bob:29c00`), sound envelopes, fixed waits (`bob:411c`, `9ada`, `9ba2`, `2b416`).
- Not checked in play: views other than the cockpit (`bob:16620..166b2` divide by T), AI
  behaviour over a mission, a flight on a 60 Hz machine.

## FR-01: debris and wreckage (unreleased 1.3b)

Classes 9/10/11 in slots 100..111 now join the fixed 64 Hz movement wrapper
at `bob:157c2`, with separate per-slot tick and gravity accumulators. Bombs
continue to use their existing path and private native gravity carry. Debris
enters the native horizontal/vertical movement at `bob:1589c`, bypassing its
frame-counted drag/expiry block. `bob:15954` supplies exact fractional 22/64
velocity decrement instead of the native minimum-one-per-frame decrement.
The intended acceleration is taken from the native numerator 22; this deliberately
corrects the old 16 units/s at T=8 as well as the excessive 50 units/s at T=50.
Vertical displacement retains the native integer conversion, now at a constant
step size; this is deterministic discretisation, not analytic ballistic motion.

Class 9 expires after 256 completed steps (four simulation seconds), including
its final movement step. Classes 10/11 lose one horizontal speed unit after each
320 completed steps (five seconds), clamped at zero to avoid unsigned underflow.
These clocks replace the native extra-update delay rather than preserving its
rate-dependent error. Catch-up stops immediately on expiry or the first step
at ground level. Normal impact dispatch still happens once in the outer world
update; no effects, sound, AI or whole-world update is repeated. FR-03 still owns
the rate-dependent emission/animation of effects that create these objects.

Constructor hooks at `bob:1d5fc` and `bob:1d702` set fixed-step drag/expiry counts
and reset the allocated slot's pending time, gravity fraction and XYZ fractions.
They leave neighbouring slots untouched. All hooks are in the Enhanced framerate
patch list; original mode bypasses that list. Unsupported falling slots retain
the original gravity instructions through the hook's inactive fallback.

`tools/debris_check.py` executes both native constructors and the patched native
movement. It compares complete sampled position/velocity/timer states against a
64 Hz trajectory for each class, at divisors 2/4/8/25/50/60 and changing-divisor
sequences. Scenarios include high altitude, near-ground descent, initial climb
and zero horizontal speed. Independent assertions check 22 units/s gravity,
four-second expiry, repeated five-second drag intervals and reset/isolation for
all 12 pool slots with deliberately dirty private state. The reference trajectory
checks subdivision consistency; it is not an independent physical motion oracle.

As for bombs, accumulated time uses ceil(64*65536/T): rounding adds less than
1/(64*65536) second per outer update, and pending movement is less than 1/64
second. Impact/expiry becomes visible on the next outer update. Equal-time
comparisons are at completed fixed ticks, with that observation delay allowed.
Real-machine debris rendering, terrain classification, impact artwork and the
cost of a full debris pool have not been measured by these CPU checks.

FR-01 validation completed on both 68000 and 68040 CPU models. Existing bomb
regressions passed on both models; input/combat and original-mode gate checks
passed on 68040. Normal and VERIFY builds succeeded, and both 1.3b release
archives passed member-by-member packaging checks. No new FS-UAE integration
run or physical-Amiga test was performed for this change.

## FR-02: aircraft-group processing clock (unreleased 1.3b)

`bob:bf96` now enters `dt_group_timer`. A private 8.24-second countdown replaces
both the byte-wide 5T reload and the native extra-update delay. The first call
still scans immediately. Subsequent calls subtract ceil(2^24/T), with T from
A4+11700 so accelerated simulation time is respected. When due, five seconds
are added to the existing remainder instead of discarding overshoot. Each scan
therefore remains tied to elapsed simulation time even if the divisor changes
while waiting. The legal minimum divisor is 2; at most one scan can become due
per update, so there is no need to repeat the world or group-processing loop.

The old countdown byte at A4+24450 is now an initialized marker. The native
flight initialization clears it at `bob:126e4`; the next scheduler call resets
the private countdown and performs the initial scan regardless of stale state.
The patched return goes directly to `bob:bfb0` for a due scan or `bob:c0f6` for
the native epilogue. All group/team/target/distance gates, group placement at
`bob:c0fe`, and native aircraft construction at `bob:b29a` are unchanged. The
single hook belongs to the Enhanced framerate patch list; original mode keeps
the original timer and code.

A scan is observed on an outer simulation update. Its lateness is less than one
update; rounding can advance its deadline by less than 2^-24 seconds per update
(under 0.22 ms per simulated minute at 60 updates/s). The 8.24 representation
holds the five-second interval without the byte overflow at T=52 and above.
Replay restoration of private timing state is still part of FR-22.

`tools/group_timer_check.py` executes the native routine with empty groups for
12 repeated periods at each of T=2/4/8/25/50/51/52/60 and two changing-divisor
sequences. It uses rational elapsed time to check every observed deadline and
checks new-flight reset with a stale private countdown. Controlled mission-group
fixtures execute the actual eligibility, placement and aircraft constructor:
an eligible enemy group is created, a blocked group is retained, a newly blocked
group stays blocked at the next deadline, and an eligible replacement appears
at five seconds rather than before. Due-scan game data matches an original
native scan byte-for-byte except for the deliberately replaced timer byte.
The common harness disables sound; this is mission-routine integration, not an
end-to-end played mission or a physical-Amiga test.

FR-02 checks passed on both 68000 and 68040. The combined 68040 timing audit
also passed the FR-01 regressions and reproduced the other still-open baseline
issues. Normal/VERIFY builds and both 1.3b archive validations passed.

## FR-03: effect animation clock (unreleased 1.3b)

The effect routine at `bob:176a2` now uses a fixed **8 Hz simulation-time** clock.
Eight is the nominal target implied by the native T/8 interval; the old added
one and integer division made its actual rate 4 Hz at T=8, 7.14 Hz at T=50 and
7.5 Hz at T=60. This deliberately normalizes effect duration to that nominal
rate rather than retaining the slow-machine timing error.

`dt_effects` accumulates ceil(2^24/T) seconds per outer update. Every due eighth
of a second calls `dt_effect_tick`, which recreates the native stack frame and
enters the unmodified state machine at `bob:176bc`. The original epilogue returns
to the catch-up loop. No intermediate animation state is skipped: native
sentinel handling, fragment emission (`bob:1785a`, `17864`), motion stops
(`bob:178a0`) and object removal all execute in their original order. The
secondary 70-entry effect table loop at `bob:178fe` runs on the same clock,
including its low-nibble progression and preservation of the high nibble.
With the supported minimum divisor T=2, at most four effect ticks are due per
outer update. AI, movement, damage processing and rendering are not replayed.

`dt_effect_init`, patched at the native effect-clock initialization
`bob:126c8`, clears the private accumulator on each flight and retains the
original initialization of A4+11704. The first effect update occurs after an
eighth of a simulation second, not immediately. T is read from A4+11700 so
accelerated time remains effective. Both hooks are gated by Enhanced framerate.

Pending time is below 1/8 second. Tick quantization can advance a deadline by
less than 2^-24 second per outer update; visibility waits for the outer update.
Catch-up uses the current world state/positions, just as the native effect
routine does; it does not reconstruct sub-frame positions or replay other
systems. Consequently this fix guarantees the effect state-machine cadence,
not identical full-world encounters or debris positions when other systems
supply different inputs. Effect clock restoration in replays remains FR-22.

`tools/effect_check.py` compares complete game-data snapshots (excluding the
replaced clocks) against sequential native effect updates at 8 Hz. It restores
the native fragment-emission routine normally stubbed by the combat harness;
animation tables, constructors, random draws and cleanup execute natively.
Nine fixtures cover classes 1/2/4/13/14 with initial and boundary states, including
emission at frame 10, motion stops and removal paths. Each is checked over 16
simulation seconds at T=2/4/8/25/50/60 and two changing-divisor sequences.
Independent checks exercise the first 1/8-second deadline, the secondary effect
cycle, new-flight reset and the original-mode gate. Sound dispatch is stubbed;
visual rendering, physical hardware and the performance cost of catch-up are
not measured by these CPU tests.

FR-03 checks passed on both 68000 and 68040 CPU models. Normal and VERIFY
builds succeeded; both 1.3b archives passed member-by-member validation.

## FR-04: world clock and daylight (unreleased 1.3b)

`bob:14e5e` now accumulates elapsed simulation time in 8.24 seconds. Each full
second enters the unchanged seconds/minutes/hours/day rollover at `bob:14e6e`;
otherwise it jumps to the unchanged daylight calculation at `bob:14e9e`.
The native T+1 update interval and premature first second are removed.
`dt_flight` clears the accumulator at flight initialization. The helper
`dt_seconds` supplies ceil(2^24/T) with T=A4+11700, including accelerated time.
As with FR-02, rounding adds less than 2^-24 seconds per update; the visible clock
advances on the first outer update reaching its deadline. Supported T>=2 needs
at most one clock-second transition per update. Original mode remains unpatched.

`tools/world_clock_check.py` covers two minutes at T=2/4/8/25/50/60 and changing
rates, midnight rollover, an hour-long accelerated run, minute/hour boundaries,
sunrise/sunset and daylight-state equivalence to native transitions. The native
night routine retains previous sun coordinates, so the reference includes the
preceding daylight update. New-flight reset and original-mode gate are checked.
Both 68000 and 68040 CPU models pass; no rendered/hardware run is claimed.
Private-clock restoration for replay remains FR-22.

## FR-05: projectile lifetime and age (unreleased 1.3b)

The projectile constructor hook at `bob:1cdaa` initializes a two-second 8.24
countdown for each slot 52..99 and resets its pending-expiry and XYZ fractional
state. Movement at `bob:15a2c` subtracts elapsed simulation time, computes the
step length from that elapsed time and clips the final step to the remaining
life. The native direction split, previous-position bookkeeping and movement
helpers remain in use. Fractional distance and XYZ carry avoid losing the final
partial step when the update rate changes. Constructor pool rules remain native:
player shots use 52..67 and AI shots use 68..99.

A final segment stays active through the native impact dispatch. The epilogue
hook at `bob:1dc54` removes pending expiries afterwards, so a hit at the end of
life is not lost. Movement also removes an already expired shot if called again
without an intervening impact pass. Class-8 AI projectiles, which have no normal
bullet-hit handler, are retired by the same end-of-dispatch cleanup. The type-20
first-second double-damage comparison at `bob:1e6f0` uses remaining elapsed
lifetime (>1 second), replacing its comparison against the current divisor.
Original mode is unchanged. Replay restoration of these arrays remains FR-22.

`tools/projectile_life_check.py` covers divisors 2/4/8/25/50/60, rate transitions,
native allocation/reset across all 48 player/AI slots, class-7/8 AI expiry,
the exact one-second damage boundary, and a target reached only on the final
segment. The controlled level shot travels 59558 units at every tested rate;
its two-second deadline is observed on the next outer update. The oracle allows
at most two position units of fixed-point rounding, though this fixture matches
exactly. As elsewhere, elapsed-time rounding is <2^-24 seconds per update.
Existing native input/combat regressions pass. These CPU tests do not certify
all combat missions, rendering or physical hardware.

## FR-06: flak launch and delayed damage (unreleased 1.3b)

Native flak chooses hit/miss at launch, then stores a frame-counted delay in
slots 112..123. A controlled miss with the same seed gave 3.25 seconds at T=8,
3.08 at T=25, 3.04 at T=50 and 3.0333 at T=60: random delay offsets were frames.
Converting only an existing countdown to seconds would leave this launch defect.

`dt_flak_launch` (`bob:1f77e`) runs the native constructor with reference T=8,
matching the established low-rate input reference. Before the call, the target's
three previous-step displacement components are converted from the current T
to that reference for native prediction. The original components and T are
restored afterwards, including allocation failure. The native hit probability,
random draws, miss placement and timing jitter therefore retain their T=8
semantics rather than shrinking the jitter as rendering gets faster.

The constructor epilogue at `bob:1f7a8` captures its final delay as Q16 seconds
(native reference ticks /8). `bob:1fdd0` consumes ceil(65536/T) per update and
enters the original miss-effect or damage path exactly once when due. A zero
delay resolves on the next update instead of leaving a miss stuck indefinitely.
Completed miss effects (type 36) are excluded from subsequent delivery checks.
Timing rounding is <1/65536 second per update; delivery is observed at an outer
update. This is a clock fix, not a replacement of native launch-time probability.

Every native aircraft allocation at `bob:b308` increments a private 32-bit slot
generation. A flak launch records its target's generation. Delayed damage is
cancelled if its target has disappeared or the aircraft slot was reused, even
for the same aircraft type. The flak slot resets its own timer/stamp on every
allocation. All hooks are Enhanced-framerate-only. The private clocks and
identities must be included in FR-22's replay-state work.

`tools/flak_check.py` compares player/AI-target launch outcomes, native random
state, miss coordinates and delays with native T=8 for twelve seeds at each
T=2/4/8/25/50/60; both hit and miss outcomes occur. Delivery tests cover steady
and changing rates, both native branches, no repeated damage, zero delay,
target removal and real native aircraft-slot reuse. Slot tests cover all twelve
allocations and a full pool. The group placement regression still passes with
the allocation-generation hook installed. CPU checks pass on 68000 and 68040;
sound/HUD are stubbed and no hardware or rendered mission is claimed. Scheduling
of AI attack opportunities remains the separate FR-12/FR-13 work.
