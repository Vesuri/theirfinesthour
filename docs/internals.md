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

Each game change is gated by a `CUSTOMn` option (with it off, the original bytes are untouched),
except the sound fix and the cache setup.

**Always on**

- **Caches:** the slave defines KickEmu's `CACHE` (WHDLoad's default setup: chip memory
  uncached, caches on) and no longer switches the caches off; the user's WHDLoad options
  override. Without an MMU (68020, 68030 without the `MMU` option) WHDLoad keeps the caches off.
- **One-shot sounds** (`sound.s`): one-shots have an empty repeat segment, and the routine then
  wrote nothing, so the channel replayed the sample until the envelope ended. An empty repeat
  now queues a cleared chip word (`PL_PS $2b6a4`).
- **Memory:** 768 KB expansion memory (`FASTMEMSIZE`); the game uses 666 KB of it in flight
  with `CUSTOM2`.

**`CUSTOM2`: faster rendering, full ground detail** (`render.s`, `transform.s`)

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
- **Perspective divide** (`xdiv20`, at `bob:2f374`, 68020+ only): one `divu.l` and one
  `mulu.l` for the original's two `divu.w` and two `mulu.w`.
- **Scenery clear** (`clr_scenery`, at `bob:11454`): `bob:1142c` cleared three 20-byte frame
  arrays a byte at a time; now 15 long-word writes, leaving the counter `-24(a5)` = 20.
- **Ground detail:** the level fast machines boot with (`bob:50`) is 0 instead of 2.

All replaced routines give the original's results: checked against models of the originals on
the A500-eq (68000 code) and the 68020 (68020 code), and the models against the originals.

**`CUSTOM3`: frame pacing** (`render.s`)

The original flipped buffers without waiting, so on a fast CPU frames overtook the display:
some were never shown, and drawing restarted in the buffer on screen. The C2P now waits until
the VBL handler has taken the pending swap request (`PL_PS $283a0`), and the handler strobes
COPJMP1 while the beam is above line 36 (the display starts at line 41), so the new buffer is
shown in the same field (`PL_PS $28d86`); later in the field the request stays pending.

**`CUSTOM4`: real-time simulation** (`timing.s`)

- **T per frame** (`bob:12954`, top of the flight loop): T = field rate / fields the last frame
  took, as an integer whose rounding error carries to the next frame, within 4 and the field
  rate. A frame of more than 25 fields (a pause, a disk load) adds no time. `11700`/`11702`
  follow T, keeping time acceleration. Each flight starts from the boot T (`bob:ad6e`).
- **Field rate:** measured at boot from the beam's highest line (PAL 312, NTSC 262). The boot
  benchmark itself stays as it is: its T is used outside flight too.
- **Stick:** the counts grow with the frame's length and the game divides them by T, so the
  slave scales them by T/8 at the end of `bob:112`: response is independent of the frame rate
  and equal to the original's at T = 8 (about the A500's rate). Keys set the deflection directly.
- **Mouse wrap** (replaces `bob:29bb2`): more than 127 counts in a field read as a move the
  other way; a reading of 64 or more against an equally large opposite previous one is taken
  as wrapped.

## Measurements (current build)

Fixed window (tape 2), `CUSTOM2`+`3`+`4` unless stated:

| Machine | Ground detail | Frame rate |
|---|---|---|
| A500-eq, original | 1 | 7.6 fps |
| A500-eq | 1 | 7.5–7.6 fps |
| 68030/50 + 8 MB fast, original | 2 (sea only) | 15.6 fps |
| 68030/50 + 8 MB fast | 0 | 50.0 fps |
| 68020 + 8 MB fast | 0 | 21.3 fps (587 k cycles per frame) |

Game speed (`speed.py`, same flight): A500-eq original 9 058 units/s (1.9× real time);
`CUSTOM4` 4 690 on the A500-eq and 4 644 on the 68030/50 at 50 fps. A 30° bank (tape 3) reaches
the same roll and turn rate (within 7%) on both. Time acceleration (tape 6) gives 3.15–3.5×.

Remaining 68020 hotspots at level 0 (of the frame): map scenery `bob:1142c`/`11138` ~13%
(compiled C, every variable in the frame; `11138`'s tile loop might give 3% from a register
rewrite), textured spans `bob:2bace` ~7% (already tight assembly), the C2P ~9% (mostly its
compare). 25 fps needs 2 fields per frame, 16% less than now.

## Known limitations

- **Truncation at large T:** the flight model integrates in integers, so at T = 50 per-step
  increments lose more fraction: ground speed 1.4% low, a 30° turn about 4% slow, and a very
  shallow bank does not turn at all. Fractional accumulators in the integrators (heading
  `bob:146aa`, `14546`, `14582`) would fix it.
- **Still counted in fields** (17% faster at 60 Hz, as in the original on NTSC): the joystick
  ramp (`bob:29c00`), sound envelopes, fixed waits (`bob:411c`, `9ada`, `9ba2`, `2b416`).
- Not checked in play: views other than the cockpit (`bob:16620..166b2` divide by T), AI
  behaviour over a mission, a flight on a 60 Hz machine.
