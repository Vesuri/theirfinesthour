# Profiling the original Their Finest Hour

> **Read this before running, driving or tracing the game, or quoting any performance number.**
> Set up 2026-10-06 following `~/Projects/Test Drive 2/docs/new-game-playbook.md`, with the
> same host tools (x86_64 FS-UAE with the Barto gdb stub in `~/.local/fs-uae`).

## 1. The game and the slave

Archive `tmp/TheirFinestHour_v1.1_0037.lha` (Retroplay, pre-installed; checksums in
`tmp/archive.sha256`), unpacked to `tmp/archive/` and copied to `tmp/game/TheirFinestHour/`,
which `run.sh` mounts as `DH1:`. No slave source exists; this table comes from disassembling
the shipped `TheirFinestHour.Slave` (4 312 bytes).

| Field | Value |
|---|---|
| Slave | Psygore v1.1 (16.11.2008), `ws_Version` 16, flags `$3402` = NoError, EmulPriv, ClearMem, Examine |
| Memory | `ws_BaseMemSize` `$80000` (512 KB chip), `ws_ExpMem` `$C0000` (512 KB + the 256 KB 1.3 image) |
| Type | **OS game**: KickEmu `kick13.s` (Kickstart 34.005 + `.RTB`), HDINIT, BOOTDOS, DOSASSIGN |
| Options | `CUSTOM1=1` loads the Mission Builder (`data/mb`) instead of the game; quit key `$5D` (num `*`) |
| `_bootdos` | `SetCPU` (Base NC, Exp/Slave CB), assigns `BobData`, `BOB1`, `BOB2` → `data`, loads the file once to take its CRC16, `LoadSeg`, `resload_PatchSeg`, `jmp 4(seg)` with `d2` = stack size − 20 (Manx stack check) |
| Patch lists | CRC `$201F` (v1.0) / `$2D72` (KIXX): `PL_P $57a,quit`, `PL_NOP $60e,2`, `PL_NOP $1bba6,2`. **CRC `$274F` (v1.1, ours)**: `PL_P $57a,quit`, `PL_NOP $60e,2`, `PL_NOP $1bbd6,2`. CRC `$A996` (`mb`): `PL_P $d50,quit`, `PL_P $3d68,quit` |
| Buffer swap patch | none: the slave does not touch the display; the frame counter is in the game (§5) |

`bob:0060e` is a `ble` after a memory-size test (NOPed: always the large-memory setting,
`-29132(a4)=2`); `bob:1bbd6` is the `bne` of the manual-protection compare.

**`data/bob`** (the code file): Aztec C (Manx) — `link a5` prologues, small-data `d16(a4)`
globals with `a4` = data hunk + `$7FFE`, library calls through a `jsr d16(a4)` jump table.
Hunk 0 code at file `$28`, `$31E40` bytes, 15 relocations; hunk 1 data **MEMF_CHIP**, `$AB70`
bytes in the file, `$FA14` allocated; hunk 2 BSS, 4 bytes. `bob:00000` is `jmp` to the
startup at `bob:30b4a`.

**The rebuilt slave** (`whdload/TheirFinestHour.s`, `make -C whdload`) reproduces `_bootdos`
and all three patch lists on the vendored WHDLoad 20.0 `kick13.s` (`slv_Version` 20,
`slv_MemConfig = slv_base`, same flags and memory sizes). It boots to the main menu on the
A500-equivalent machine. Its behavioural equivalence in gameplay is not yet checked.

## 2. The machine

`amiga/run.sh` boots a Kickstart 3.1 host from DH0 plus the Workbench 2.04 floppy; the
startup-sequence runs `WHDLoad TheirFinestHour.Slave PRELOAD SPLASHDELAY=0 NOREQ` on DH1 with
WHDLoad 20.0. Variables as in TD2 (`CHIP_KB`, `FAST_KB`, `EXTRA_ARGS`, `CPU`, `WARP`, `SILENT`,
`DEBUG`, `RECORD`, `SLAVE`, `WHD_ARGS`) plus `JOY0` (port 0, default `mouse`; `none` stops the
host mouse from injecting input).

**A500-equivalent profiling machine:** `CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536`.
On it `bob`'s code hunk loads into slow RAM (`$CFEC18` in the first boot), its data hunk into
chip (`$105B8`), the Kickstart copy at `$CB5000`, the slave at `$D7DE68`.

The RTB lives at `~/Projects/amiberry/whdboot/save-data/Kickstarts/kick34005.A500.RTB`
(TD2's `run.sh` still points at the old `~/Documents/amiberry` path, which no longer exists).

## 3. Driving and tracing: `tools/tfh.py`

Identical to TD2's `td2.py` (socket `amiga/.run/tfh.sock`):

```sh
WARP=1 python3 tools/tfh.py serve > amiga/.run/serve.log 2>&1 &
python3 tools/tfh.py shot "$PWD/amiga/.run/now.png"
python3 tools/tfh.py profile 5 "$PWD/tmp/prof/x/trace.bin"
python3 tools/tfh.py gdb 'dump binary memory /tmp/tfh-code.bin 0xc00000 0xd80000'
python3 tools/tfh.py quit
```

The lldb profiler-window fix (`BASETEXT_VM = 0x32dea04`) still matches the FS-UAE binary:
traces have PCs (first check, 2026-10-06, a 5-field menu trace).

## 4. Reading a trace

```sh
python3 tools/tfh_report.py TRACE CODE.bin --base 0xc00000
python3 tools/frames.py     TRACE CODE.bin 0xc00000
python3 tools/hotspots.py   TRACE CODE.bin 0xc00000 <bob-hunk-base> <off,...>
python3 tools/disd.py       CODE.bin 0xc00000 <bob-hunk-base> <start> <end>
```

`tfh_report.regions()` byte-matches the dump for `bob` hunk 0, the Kickstart copy and the
slave's code hunk, and follows LoadSeg's BPTR chain from hunk 0 to the data hunk in chip RAM
(read from the trace's chip snapshot). Set `SLAVE=` to the slave the capture used.

In the menu the game runs almost entirely in `bob` (no Kickstart time): it has taken over the
hardware. The jump-table `jmp abs.l` stubs execute in the data hunk (`bob-data:` in reports).

## 5. Display, interrupts and time (static analysis, 2026-10-06)

- **Level-3 handler `bob:28d4c`** (the vector at `$6C` during play). It reloads `a4` from
  `data:60BC` through a relocated pointer at `bob:28d68`. On VERTB (`bob:28d66`) it writes COP1LC from one of two copper lists
  chosen by `-7964(a4)`, clears the swap request `-7962(a4)`, increments the VBL counter
  `-8010(a4)`, reads the mouse (`bob:29a76`), the buttons (`-8008(a4)`: bit 0 right mouse
  via POTGOR, bit 1 port-0 fire, port-1 fire through the mask `-8006(a4)`) and the joystick
  (`bob:29bb2`, `29c00`), then runs sound (`bob:2b66c`). BLIT (`bob:28e0e`) and COPER
  (`bob:28e1c`) are only acknowledged. Level 2 (keyboard): `bob:28e2a`.
- **Frame marker:** the swap requests `move.w #1,-7962(a4)` at `bob:12f38` (end of a frame in
  flight: show buffer `-7958`, request, flip the draw buffer), `bob:14d78` and `bob:28f9e`
  (show-and-wait helper). `bob:1b08a` and `bob:28fa4` spin until the VBL takes the request.
  `frames.py` counts the requests; not yet validated on gameplay.
- **Blitter waits:** seven `btst #14,$dff002` / `bne.s` loops, all in `bob:288e6..290e4`.
- **Random generator `bob:2915c`**: a 16-step LFSR on `-7830/-7828(a4)`. The main-menu loop
  calls it continuously (60% of menu CPU time), so the RNG state at the start of a flight
  depends on how long the menu waited for input. Input timing must therefore be exact
  (the tape, §7), or the RNG pinned in a VERIFY build.
- **Time sources found so far:** the VBL counter `-8010(a4)`; CIA-A timer A as a one-shot
  delay (`bob:2b3ee`); a startup routine (`bob:2b84..2c2e`) that times work in VBLs and divides
  380 by the count. No `VPOSR`/`VHPOSR` reads in hunk 0.

## 6. Input: no attract demo, and FS-UAE playback does not work

The game sits in its main menu indefinitely (checked over ~70 s of warp). There is no demo.

FS-UAE `--record=FILE` (`RECORD=` in `run.sh`) records when FILE is missing and plays it
back when it exists. But in this build's `fsuae-recording.c`, **any live input event during
playback truncates the recording and switches back to recording**. An idle recording played
back under `tfh.py serve` logged live events at frame 1 (182, 169, 156), so the playback ended at
once ("Truncating recording" in `amiga/.run/fsuae.log`). The route left is a VERIFY-only
input tape in the slave (§7).

## 7. The VERIFY input tape (`whdload/verify.s`, `CUSTOM5=n`)

`make -C whdload verify` builds a slave whose `CUSTOM5=n` (n ≥ 1) selects input tape n. With
`CUSTOM5` unset, even the verify build applies no extra patches. The tape is indexed by
`tape_vbl`, a count of the game's VERTB interrupts. Each entry holds from its field until the
next one: mouse counts per field, buttons (bit 0 right, bit 1 left) and a decoded key byte.
Hooks (`_pl_tape`): `PL_PSS $28dc4` after the VBL's mouse-delta routine (adds deltas, ORs
buttons into `-8008(a4)`), `PL_P $29b44` (the menu's button read, reimplemented plus the tape),
`PL_PS $29a96`/`$29ad6` (the VBL key poll's CIA-A serial reads). Capture with `JOY0=none`.

Verified 2026-10-07 on the A500-equivalent machine: the hooks are installed, and tape counts
move the menu pointer.

**The menu pointer** is in `11816/11818(a4)`, in low-res pixels, clamped to the bounds at
`11832..11838(a4)` (main menu: x 42..275, y 20..163). It moves one pixel per mouse count,
starts at (160,40), and maps to screenshots as `shot = (74 + 2x, 30 + 2y)`. Pointer mode is
`-4718(a4)=1`. The VBL then routes mouse deltas `11958/11960(a4)` through `bob:29d4e`. The
main menu sets its bounds (`bob:35dc`) at **tape field 2090** (with the shipped
slave layout, `JOY0=none`). The menu loop is `bob:4c18`: buttons through `bob:35fc`
(`11956|11950` → `11840`), then a hit test `bob:5026`, with the choice in `11982(a4)`.

**Finding slave variables:** assemble with a listing to get symbol offsets
(`vasm ... -DVERIFY=1 -L /tmp/tfh.lst`, then e.g. `tape_vbl` = `$14E6`), and add the
slave's base from `regions()`. **Set `SLAVE=` to the running slave when calling
`regions()`.** Without it, `regions()` matches the shipped slave's KickEmu code and returns a
wrong base: that misled the first calibration runs. The match also rejects a PRELOAD file
copy (one preceded by its own hunk header).

**Traps hit:**
- `tfh.py until` with a breakpoint that never hits blocks the server. Recover by killing our
  own emulator (`kill -9 $(cat amiga/.run/fsuae.pid)`) and our own `tfh.py` processes.
- Conditional breakpoints that fire every field (`until 'ADDR if *(short*)V == N'`) are very
  slow. Prefer a breakpoint on code that runs once, such as `bob:35dc` for the menu.
- Each shell starts fresh, so pass `SLAVE`/`WHD_ARGS` on every command line.

## 8. Getting into a flight, and the fixed window (2026-10-07)

Tape 2 (`CUSTOM5=2`): main menu → Fly Training Flight → Spitfire → flight 4 (intercept a
bomber with a Bf 109 escort) → GO FLIGHT. The pointer positions and fields are in
`whdload/verify.s`. The same tape works on the 68020 configuration. Tape 3 is tape 2 plus a
30° roll to the right in flight (§11). Tapes 4 and 5 press Ctrl+G twice or once in flight
(fields 7900–7918), which takes the 68030's boot detail level 2 to level 1 or 0 (§12). They use
the key column: decoded key bytes, bit 7 = down (Ctrl `$E3`, G `$A4`, G up `$24`). `tools/tape_probe.sh N
OUTDIR` boots a tape and takes screenshots labelled with the tape field.

`tools/fixed_window.sh OUTDIR [SLAVE]` boots once to learn `bob`'s address, accepting it
only when the game's level-3 handler is at `$6C`. Earlier in the boot there are other
`bob`-shaped copies, and with 8 MB fast RAM calibration picked one. It then reboots with the
flight loop `bob:12968` armed at reset, skips `SKIP_FRAMES` (default 40) more loop passes,
and traces `FIELDS`. **Two fresh boots gave byte-identical traces in all 100 fields**
(`tools/compare_traces.py`, A500-equivalent, 2026-10-07). With a breakpoint armed, the
68020 emulation is slow in warp: use `SERVE_WAIT=1500`. `anchor.txt` records T, the detail
level and the tape field at the anchor (`SKIP_FRAMES=0 STATE_ONLY=1`: where the flight starts).

Configurations (Kickstart 1.3 inside WHDLoad; host ROM as listed):

| Name | Settings |
|---|---|
| A500-eq | defaults: `CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536`, 68000 |
| 68020 | `AMIGA_MODEL=A1200 KICKSTART=~/Documents/RetroPie/BIOS/kick40068.A1200 CHIP_KB=2048 FAST_KB=8192 CPU=68EC020 EXTRA_ARGS=--slow_memory=0` |
| 68030/50 | as 68020 with `CPU=68030 EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000 --uae_cpu_cycle_exact=true'` and `SWAP_ONLY=1 SERVE_WAIT=1700` |

## 9. Where the time goes (fixed window, 2026-10-07)

| Configuration | Original | `CUSTOM2=1` |
|---|---|---|
| A500-eq (100 fields) | **7.6 fps** (6.6 fields/frame) | 7.5 fps |
| 68020 + 8 MB fast (50 fields) | **18.5 fps** | **21.9 fps** |
| 68030/50 + 8 MB fast (100 fields, swap requests) | **15.6 fps** | **80 requests/s**: more than one per field, see below |

Per frame (A500 profile; frame = `bob:1294e` loop: `12dba`, `13b40`, `12eaa`, `12efc`):

| Inclusive | Routine |
|---|---|
| 78% | `bob:12efc` render: `12f9c` (3D: `104b6` 38%, `293b4` sky/ground + horizon 14%), C2P `283a0` 19% |
| 18% | `bob:12eaa` simulation (flight model, AI; calls `13c6e`, `176a2`, `154b2`, ...) |

The CPU never idles. On the 68020 the C2P is 21%, of which 18 points are its compare loop
(`cmpm.l (a5)+,(a6)+` / `dbne`) reading two chunky buffers in chip RAM. The blitter
sky/ground fill `bob:29084` (CPU busy-waiting on it) is 11.4%, and the 2D shape drawer
`bob:2bace` (into the chunky buffer) 7.7%.

**The C2P (`bob:283a0`)**: the 3D view is drawn into a packed 4-bit chunky buffer (8 pixels per
longword, 16 colours, 160 bytes per row). Three buffers rotate (`12084/12088/12092(a4)`).
The C2P compares the new frame with the one drawn two frames earlier (what the
double-buffered planes hold), longword by longword. It converts only changed longwords
(`add`/`addx` bit shuffle into one byte of each of 4 planes), merging through a per-byte mask
(`-9778(a4)`, the cockpit window shape). Kalms' collection has no packed-4-bit converter. Its
4-plane routines take one byte per pixel; this format is the input after their first merge pass.
In this scene few longwords change, so the conversion is not the cost; the compare is.

**Chip memory audit:** done 2026-10-08, see §14. (The list once here gave `bob:29ac` as the
bitplanes; it is the sound bank. Bitplanes and copper lists are allocated at `bob:28a80..28ad4`.)

**No frame pacing.** At `bob:12f2c` the game sets the buffer to show, raises the swap request
and flips the draw buffer without waiting for the VBL to take the previous request. The VBL
handler clears it when it loads COP1LC. On a fast CPU (68030/50 with `CUSTOM2`) frames finish
faster than the display: up to 2 requests per field, some never shown, and drawing restarts in
the buffer that is still on screen.

**`CUSTOM3` (frame pacing):** the C2P first waits until the VBL handler has taken the pending
swap request. The handler only writes COP1LC, and the copper loads COP1LC at the next vertical
blank, so the new buffer appeared one field after the request was cleared. A C2P started on the
clear wrote into the buffer still on screen. The user saw tearing, and frames where the view
went back (2026-10-08, interactive FS-UAE). So `CUSTOM3` also strobes COPJMP1 in the handler
while the beam is above line 36 (DIWSTRT line 41), which shows the buffer in the same field.
A later handler leaves the request pending for the next field. The profiling configuration
(cycle-exact 68030/50) never wrote ahead of the beam: per-field screenshots of the tape 3 bank
show clean horizons before and after this change. Swap count after it: still 50.0 fps.

## 10. How game time advances

No clock is read in flight. Each simulation step divides its per-step motion by
**`T = 11698(a4)`**. A rendering benchmark at boot (`bob:2b84..2c5c`) sets
`T = 380 / VBLs taken`, minimum 4; above 6 it subtracts 2. At `bob:0046`, `T > 10` selects the
higher detail level (`11196(a4)=2`) and subtracts 2 again. The `T` key (time acceleration)
uses `11700 = T/3`, minimum 2, in place of `T` in the step code. On the A500-eq `T = 4`. So
**game speed ∝ frames per second / T**: correct only while the frame rate stays where the boot
benchmark measured it. Mouse stick input is per frame (`bob:112`: counts since the last frame
×64 roll, ×32 pitch), divided by `T` in `bob:13c6e`.

### Measurements of T and game speed (2026-10-07)

| Machine | fps (window) | T | detail | game speed fps/T | vs A500 |
|---|---|---|---|---|---|
| A500-eq | 7.6 | 4 (clamp minimum) | 1 | 1.9 | 100% |
| 68030/50, original | 15.6 | 15 | 2 | 1.04 | 55% |
| 68030/50, `CUSTOM2`+`CUSTOM3` | 50.0 | 15 | 2 | 3.3 | 175% |
| 68030/50, `CUSTOM2`+`3`+`4` | 50.0 | 50 (dynamic; boot T 16) | 2 | 1.0 | real time |
| A500-eq, `CUSTOM4` | 7.9 | 7–9 (dynamic) | 1 | 1.0 | real time |

**State found** (A500-eq, `STATE_FIELDS=60`): plane position longs `11668(a4)` x (east),
`11672(a4)` y (north), `11676(a4)` altitude (148 956 here; copies at `4154`, `4216`), heading
word `11680(a4)` (65 536 = 360°). Per frame at T=4 the plane moved (+529, +1052) = 1 177 units.

**Time model, confirmed by the coupling test below:** one frame advances 1/T seconds of game
time, and the boot benchmark is meant to predict the frame rate (68030/50: T=15 against 15.6
fps measured). Real-time ground speed in this flight is 1 177 units × 4 = 4 710 units/s: 260 mph
if the bottom-left dial shows 12 000 ft (12.4 units/ft), or 200 mph at 16 units/ft.

**State snapshots are not fields.** `state_fields.py` stops at every level-3 entry, which on
the A500 includes the blitter-finished interrupt (0.3 per field). Time snapshots by the game's
VERTB count `-8010(a4)`, as `tools/speed.py` does.

Per-plane state is in arrays indexed by plane (player = 0): heading `18162(a4)` (words,
65 536 = 360°), roll `19198(a4)`, and `18830(a4)` (pitch, unconfirmed). The camera copies
the viewed plane into `11668..11684`.

## 11. Real-time simulation (`CUSTOM4`, `whdload/timing.s`)

Design A from `open-work.md`, with real time as the reference (user's choice, 2026-10-08).

- **T per frame.** At the top of the flight loop (`bob:12954`) the slave reads the fields the
  last frame took from `-8010(a4)` and sets `T = round(50 / fields)` within 4..50. It carries
  each frame's rounding error to the next, so integer T still adds up to real time: the A500
  alternates T 7/8/9 at 6.3 fields/frame. A frame of more than 25 fields (a pause, a disk
  load) adds no time. Above 50 fps (no `CUSTOM3`) the game runs faster than real time.
- **Derived values:** `11700` (step divisor: T, or T/3 with a minimum of 2 while the `T` key
  accelerates time), and `11702 = 11700/8 + 1`, as at flight start (`bob:ad6e`). Each flight
  starts from the boot T. The detail level picked from the boot T stays.
- **Stick input.** Mouse and joystick counts are summed per field by the VERTB handler, then
  divided by T. So a frame's input grows with its length and response fell with fps. At the
  end of `bob:112` the slave scales them by T/8 (saturating). Response is then
  frame-rate independent, and equal to the original's at T = 8, about the A500's frame rate.
  The keyboard sets a deflection directly and is not scaled.
- **Mouse counter wrap.** The VERTB handler reads the mouse as the change of JOY0DAT's 8-bit
  counters per field (`bob:29bb2`), so a field of more than 127 counts reads as a move the
  other way. Host mice under FS-UAE reach that when wiggled fast. On the A500 one such field
  was averaged into a 6-field frame, but at 50 fps it is a whole frame, and the plane rolls
  back for that frame (user report, 2026-10-08: screen recording of a rapid left-right
  wiggle). `CUSTOM4` replaces the read: a reading of 64 counts or more whose sign is opposite
  to an equally large previous reading counts as wrapped, because a real reversal slows down
  through small readings first. Tape input is added after this read, so tape runs are
  unchanged (68030/50 tape 3: identical state over 300 snapshots). Not measured with a real
  mouse.

**Coupling test** (same tape, same flight; `tools/speed.py`; 2026-10-08):

| Run | fps | T | Ground speed, units per wall-clock second |
|---|---|---|---|
| A500-eq, original | 7.6 | 4 | 9 058 (1.92× real time) |
| A500-eq, `CUSTOM4` | 7.9 | 7–9 | **4 690** |
| 68030/50, `CUSTOM2`+`3`+`4` | 50.0 | 50 | **4 644** |

**Stick test** (tape 3, `CUSTOM5=3`: 7 mouse counts right per field for 100 fields from tape
field 8600; flight starts at tape field 8244 on the A500-eq and 7603 on the 68030/50):

| Run | Bank reached (`19198`) | Turn rate, heading units/s |
|---|---|---|
| A500-eq, `CUSTOM4` (T 4–6 while banking, ~5 fps) | −5 589 (30.7°) | 1 555 (8.5°/s) |
| 68030/50, `CUSTOM2`+`3`+`4` | −5 500 (30.2°) | 1 450 (8.0°/s) |

**Time acceleration** (`T` key, `bob:13cf2`: the step divisor 11700 becomes max(T/3, 2), and
`T` again restores it). `CUSTOM4` keeps the accelerated divisor while it updates T every frame.
Tape 6 (`CUSTOM5=6`) presses `T` at tape fields 8800 and 9300; `tools/speed.py --window 100`
gives ground speed per 100 fields (2026-10-08):

| Run | Normal | Accelerated (divisor) | Normal again |
|---|---|---|---|
| A500-eq, `CUSTOM2`+`3`+`4` (T 6–9) | 4 694 | 16 600 (2–3): 3.5× | 4 665–4 783 |
| 68030/50, `CUSTOM2`+`3`+`4`, level 0 (T 25–50) | 4 668 | 14 703 (8–16): 3.15× | 4 665 |

The factor is T / max(T/3, 2) as in the original: 3 to 4 depending on how T rounds (the
original A500 at T = 4 gets 2×).

**Truncation at large T.** The flight model integrates in integers, so per-step increments
lose their fraction, and at T = 50 a step is 1/12 of an A500 step. Ground speed is 1.4% low
(41, 83 per step against 42.3, 84.2), the 30° turn about 4% slow (29 per step against about
30.2), and a 0.86° bank that turns the A500 0.19°/s does not turn at all at T = 50. The
original already ran at T up to 26 on fast machines (boot benchmark under 2 fields). Fixing
it needs fractional accumulators in the flight model's integrators (heading `bob:146aa`,
`14546`/`14582`, ...).

## 12. Ground detail (`11196(a4)`, 2026-10-08)

Ctrl+G (also Alt or Amiga; key code 231 = `g` + 128, `bob:14c8a`) cycles 0 → 1 → 2 → 0 in flight.

| Level | Map scenery `bob:11138` | Ground polygons `bob:104b6` (land, coastline) | Objects (`bob:10a00`: drawn if their detail byte ≤ level) |
|---|---|---|---|
| 0 | yes | yes | marked 0 |
| 1 | no | yes | marked ≤ 1 |
| 2 | no | no | all |

The boot code (`bob:46`) gives machines with benchmark T > 10 **level 2**, so fast machines
showed only sea. A user report ("no polygonal seashore") led here. Same 68030 flight and frame
at each level (tapes 2, 4, 5): level 2 is sea to the horizon, level 1 adds land and the
coastline, level 0 adds fields and small objects near the horizon. The A500-eq (T = 4) gets
level 1, where `104b6` is 38% of the frame. **The 68030/50 fps figures in §9–11 are level 2.**

68030/50, `CUSTOM2`+`3`+`4`, straight flight (swap count):

| Level | fps |
|---|---|
| 2 | 50.0 |
| 1 | 47.5 |
| 0 | 30.9 |

`CUSTOM2` now also sets the level stored at `bob:4e` (immediate at `bob:50`) to 0 (the user's choice, knowing it costs fps):
fast machines boot with full ground detail, slower ones keep level 1.

## 13. Level 0 on fast machines, and the merge C2P (2026-10-08)

**Where level 0's time goes** (68020, `CUSTOM2`+`3`+`4`, tape 4 to level 0, 50 fields traced
after the level change, `SKIP_FRAMES=90`): **14.1 fps** against 21.9 at level 1 in the same
flight. Per frame the extra cost is the map scenery (`bob:11138` and `1142c`, ~119 k cycles)
and, for the extra objects, the shared 3D point transform and projection routines
`bob:2f4ae` (+61 k), `2f160` (+40 k), `3041c`, `2f374`, `2fbb2`, `2fa12`, `2ffa4` (+~90 k
together). These routines work in scratch globals of the data hunk (`2f4ae`: about 30
`d16(a4)` accesses per call, ~1 000 calls per field), which is chip memory (§9).
The C2P is 11% of level 0 here and changes little with the level: in straight flight few
longwords change (5–18 per frame at the anchor), so its cost is the compare.

**Merge C2P (`CUSTOM2`, `whdload/render.s` `c2p_merge`, replaces the body at `bob:283a6`).** The
original converts each changed longword with 64 `add`/`addx` into one byte per plane and
merges it into the planes with `and.b`/`or.b`: 16 chip accesses per 8 pixels. The new one
compares and converts 32 pixels at a time with a 5-pass merge network (Kalms' bit-group
swaps between register pairs, shifts 16/8/4/2/1; the sequence was derived and checked in a
Python model) and writes each plane as a longword through the window mask: one chip write
per plane, plus a read where the mask is partial. Window widths that are not a multiple of 32
pixels, odd addresses or a plane spacing other than 8000 go to the original code.

| Run | Original C2P | Merge C2P |
|---|---|---|
| 68020, level 0, C2P cycles per frame (trace) | ~113 k | ~31 k |
| 68020, level 0 | 14.1 fps | 14.9 fps |
| 68030/50, boot level 0, tape 2 (swap count, 100 fields) | 29.4 fps | 30.6 fps |

**Check:** `C2P_CHECK=N tools/fixed_window.sh` (`tools/c2p_check.py`) stops at the C2P N times,
dumps its inputs and the planes before and after, and compares the planes with a model of the
original routine. It passed on the 68020 (3 calls, straight flight) and on the A500-eq during
the tape 3 bank (10 calls with 167–516 changed longwords each, i.e. the 68000 path):
byte-identical planes.

## 14. Chip memory audit and CPU caches (2026-10-08)

**What the hardware reads.** Static analysis of every DMA pointer write, plus the per-field DMA
records in the earlier traces (flight, A500-eq and 68020; main menu):

| Consumer | Memory | Where |
|---|---|---|
| Bitplanes, 2 × 32 000 bytes | AllocMem(32000, CHIP\|CLEAR) at `bob:28a80`/`28ab0` | `-7998/-7994(a4)` |
| Copper lists, 2 × 200 bytes | AllocMem(200, CHIP\|CLEAR) at `bob:28a98`/`28ac8`, built at `28b0a..28bd0` | `-7982/-7978(a4)` |
| Sound bank, `$1A9C8` bytes | AllocMem at `bob:29ac`; AUDxLC at `bob:2b6b2` | `12996(a4)` |
| Sprites: pointer (36 bytes) and an empty sprite | **the data hunk**, `data:613C..6163` | copper list immediates `bob:28b34/28b9a` (pointer) and `28b4e/28bb4` (empty); control words through `lea -7874(a4)` at `bob:28ef0`, `29e8e` |
| Blitter | bitplanes; the chunky buffers (sky/ground fill, replaced by `CUSTOM2`) | `bob:288e6..290e4` |
| Disk DMA (`bob:2b146`) | buffers from `bob:2860`/`2876` | not reached: the `PL_NOP $60e` setting skips their allocation |

Everything else in the data hunk is CPU-only. Measured from the 68020 trace with `CUSTOM2`: 10 577
CPU accesses per field to the data hunk, and 10.6 to all other chip memory; the data hunk is
99.9% of the CPU's remaining chip traffic, spread over the whole hunk.

**`CUSTOM2` loads the data hunk into public memory** (`whdload/render.s` `data_fast_on`,
`data_sprites`). While `LoadSeg` runs, exec `AllocMem` (via `SetFunction`) drops `MEMF_CHIP`;
afterwards the 40 sprite bytes are copied to a chip allocation and the four copper list
immediates and the two `lea` sites are redirected. No other relocation points into those bytes
(checked over all of `bob`'s reloc32 tables).

| Run (`CUSTOM2`+`3`+`4`, merge C2P) | Data hunk in chip | In public memory |
|---|---|---|
| 68030/50, boot level 0, tape 2 (swap count, 100 fields) | 30.6 fps | **50.0 fps** |
| 68020, level 0 (trace, 50 fields; tape 4 vs tape 2, see below) | 14.9 fps | **19.6 fps** |

Checks: the C2P check passed with the moved hunk (A500-eq tape 3 bank, 3 calls, ~500 changed
longwords each), and the flight view draws normally (A500-eq screenshots). The first version
copied the sprites from a register `AllocMem` had trashed, so the pointer was garbage (user
report, 2026-10-08; a gdb watchpoint on the chip copy caught the slave's own copy loop). Fixed:
the chip copy holds the arrow and it shows as in the original (A500-eq menu screenshot). On the A500-eq the hunk lands in slow memory, which is no slower than chip.
On the 68030/50 the tape 3 bank reaches the same roll (−5 500) and turn rate (1 450 heading
units/s) as before the move, and the C2P check passes with 117–144 changed longwords per call.
**Expansion memory.** With the data hunk moved, the slave's 512 KB of expansion memory overflowed
into chip memory. With 2 MB the game used 666 KB of it in flight (68030, `CUSTOM2`+`3`+`4`, exec's
memory header after reaching the flight), so `FASTMEMSIZE` is now `$C0000` (768 KB; `ws_ExpMem`
1 MB with the Kickstart image). More than that would fall back to chip memory, as before.
The boot benchmark runs faster too: the 68020 now gets T > 10 and boots at level 0 (it booted at
level 1 before), so its level 0 figures come from tape 4 before and tape 2 after the move.

**CPU caches.** The 1.1 slave's `_bootdos` called `resload_SetCPU` with `Base_NC|Exp_CB|Slave_CB`
under the mask `WCPUF_All`, which also cleared the cache enables; KickEmu's `_boot` does the same
unless the slave defines `CACHE`. The slave now defines `CACHE` and no longer calls `SetCPU` itself:
chip memory uncached, expansion memory and slave copyback, caches enabled, which is WHDLoad's own
default. Without the MMU (68020, or a 68030 without the `MMU` option) WHDLoad cannot leave chip
memory uncached alone, so the caches stay off; on 68040/060 (MMU always in use) the code and data
in expansion memory are cached. The user's options (`NoCache`, `Cache`, `DCache`, ...) override
the slave's setup. The game writes no code at run time (no stores into the code hunk).

| Run (68030/50, boot level 0, tape 2, merge C2P, data hunk in chip) | fps |
|---|---|
| caches as the 1.1 slave set them | 30.6 |
| `CACHE` defined, no user option | 30.6 (identical swap pattern) |
| user option `DCACHE` | 37.8 |

## 15. One-shot sounds looped (always-on fix, 2026-10-08)

User report: explosion and splash sounds did not end with their sample but restarted and were cut
off about 200 ms later; remembered from the original too. A sound descriptor (copied into the
channel tables at `bob:2771e`; the bank's list from `31180(a4)`) has a start segment (`6(a0)`,
length `10(a0)`) and a repeat segment (`12(a0)`, `16(a0)`), a period, and an envelope counted in
fields (sustain `28(a0)`). The VBL sound routine `bob:2b66c` writes the start segment to
`AUDxLC`/`AUDxLEN` and enables DMA, and in the next field queues the repeat segment. One-shots
(ids 1002–1008, 1010, 1012, 1013) have a repeat of 0, and the routine then skipped the write
(`tst.l`/`beq` at `bob:2b6a4`), so the channel replayed the start segment until the envelope
switched it off. Whether that is audible depends on the sound: 1002 is a 2.2 s sample (6 032
words at period 650) against a 120-field sustain plus release.

`whdload/sound.s` (no option, at the user's request) queues a word of silence (`AUDxLEN` 1, a
cleared chip word) for an empty repeat. Checked with tape 7 (`CUSTOM5=7`: fire in flight,
A500-eq): the gun sound (1004) now gets `AUD1LC`/`AUD1LEN` written in its second field and
otherwise plays as before (the envelope ends it after 19 fields, before its 28-field sample ends,
so gunfire never showed the loop). A long one-shot (explosion, splash) was not triggered in the
emulator.
