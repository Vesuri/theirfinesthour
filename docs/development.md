# Development: building, running, measuring

How to build the slave, run the game in FS-UAE, drive it reproducibly, measure it and check
patches. How the game and the patches work is in `internals.md`.

## Inputs (local only, never committed)

| Path | What |
|---|---|
| `tmp/TheirFinestHour.lha` | Psygore's v1.1 installer archive |
| `tmp/TheirFinestHour_v1.1_0037.lha` | the preinstalled v1.1 archive (game files included) |
| `tmp/game/TheirFinestHour/` | that archive unpacked; `amiga/run.sh` mounts it as `DH1:` (`GAME=` overrides) |
| `tmp/code/` | `bob` split into hunks and disassembled, for reading code |

`data/bob` v1.1 is 254 400 bytes, CRC16 `$274F`. Everything the tools write (traces, dumps,
screenshots, snapshots, slave builds, scratch files) goes under `tmp/`, which git ignores.

## Shared files

Common Amiga files and the toolchain come from the shared environment that AmigaXDev installs
(`make setup` there): `amiga/env.sh` sources its `~/.local/share/amiga/env.sh`, and the Makefile
and the Python tools use the same defaults. An environment variable of the same name overrides
each one; AmigaXDev's `docs/environment.md` describes them all. The ones used here:

| Variable | Default (under `~/.local/share/amiga`) | Use |
|---|---|---|
| `KICKSTART` | `Kickstarts/kick40063.A600` | host Kickstart 3.1 |
| `KICKSTART_A1200` | `Kickstarts/kick40068.A1200` | host Kickstart 3.1 for the 68020/68030 setups |
| `KICK13` | `Kickstarts/kick34005.A500` | Kickstart 1.3 image that KickEmu boots inside WHDLoad |
| `RTB` | `Kickstarts/kick34005.A500.RTB` | its relocation table |
| `WORKBENCH_ADF` | `Workbenchv2.04rev37.67Workbench.adf` | host boot floppy |
| `WHDLOAD` | `WHDLoad-20.0` | API headers and KickEmu sources the slave builds with |
| `WHDLOAD_BINARY` | `WHDLoad-20.0/C/WHDLoad` | the WHDLoad that runs the slave |
| `LHA` | `lha-compressor/src/lha` | LHa for UNIX, for `make dist` (Lhasa, the usual `lha`, only extracts) |
| `AMIGA_TOOLCHAIN` | `~/.local/opt` | `bin/m68k-amiga-elf-{gdb,objdump}`, NDK headers |

`amiga/env.sh` puts the toolchain on `PATH`: vasm (`~/.local/vasmm68k_mot`), `m68k-amiga-elf`
gdb/objdump, and an x86_64 FS-UAE with the Barto gdb stub and profiler.
`~/.local/share/amiga/fsuae_common.sh` starts and tracks FS-UAE; it kills only this repo's
emulator (`amiga/.run/fsuae.pid`) and gives the repo its own gdb port. Never `pkill fs-uae` or
`pkill gdb`.

## Building

```sh
make -C whdload          # whdload/TheirFinestHour.slave, the release slave
make -C whdload verify   # VERIFY build (input tapes) with the listing whdload/TheirFinestHour.lst
make dist                # the two release archives in dist/ (tools/package_release.py)
```

The slave source is `whdload/TheirFinestHour.s` (Psygore's v1.1 slave rebuilt from its
disassembly) on the WHDLoad 20.0 KickEmu sources (`$WHDLOAD`, see `whdload/README.md`), with a
WHDLoad 17 interface, so WHDLoad 17 and later run it. Game changes are in `render.s`,
`transform.s`, `timing.s` and `sound.s`, instruments in `verify.s` (VERIFY build only).

`make dist` rebuilds the two `tmp/` archives into `dist/TheirFinestHour-<ver>.lha` and
`dist/TheirFinestHour_v<ver>_0037.lha`: the same members, with the game launch icons, slave and ReadMe
changed (Psygore's ReadMe with `whdload/readme-history.txt` added above his history), checked
member by member after re-extraction. All game launch icon styles include `CUSTOM2=1`,
so Enhanced framerate is checked when launched from Workbench. The slave itself defaults
to enhancements off when that tooltype/argument is absent. `<ver>` comes from the slave's `$VER`.

## Input and combat routine checks

The local CPU regression needs a fast-memory flight `code.bin` capture (with the live
code and data hunks), the normal slave, its matching listing, and the shared Unicorn
library (`AMIGA_UNICORN`, default `~/.local/share/amiga/unicorn`). It loads only local bytes:

```sh
mkdir -p tmp/input-combat
make -C whdload VASMFLAGS='-L ../tmp/input-combat/release.lst'
python3 tools/input_combat_check.py CAPTURE/code.bin 0x200000 whdload/TheirFinestHour.slave tmp/input-combat/release.lst
python3 tools/input_combat_check.py CAPTURE/code.bin 0x200000 whdload/TheirFinestHour.slave tmp/input-combat/release.lst --cpu 68000
python3 tools/bomb_check.py CAPTURE/code.bin 0x200000 whdload/TheirFinestHour.slave tmp/input-combat/release.lst
python3 tools/bomb_check.py CAPTURE/code.bin 0x200000 whdload/TheirFinestHour.slave tmp/input-combat/release.lst --cpu 68000
```

The checks cover signed mouse movement at multiple update rates, independent controller
settings, exact swept-hit geometry, and native projectile/damage paths. They do not emulate
Amiga hardware or measure time. See `internals.md` for the reproduced collision failure
and the test boundaries. Also run FS-UAE with the VERIFY build: tape 8 fires during fields
7800-8100 on the fast-machine setup. Choose the capture's `SKIP_FRAMES` so its recorded
`tape field` overlaps that interval; a flight before field 7800 does not test firing.

## Running

`amiga/run.sh` boots the Kickstart 3.1 host from `DH0` plus the Workbench floppy; its
startup-sequence runs `WHDLoad TheirFinestHour.Slave PRELOAD SPLASHDELAY=0 NOREQ` on `DH1`.

| Variable | Meaning |
|---|---|
| `SLAVE` | slave to run instead of the installed one |
| `WHD_ARGS` | extra WHDLoad arguments, e.g. `CUSTOM2=1` (Enhanced framerate; off by default) |
| `CPU`, `AMIGA_MODEL`, `CHIP_KB`, `FAST_KB`, `EXTRA_ARGS` | the machine |
| `WARP`, `SILENT`, `DEBUG`, `RECORD` | warp mode, no sound, gdb stub, FS-UAE input recording |
| `SOUND`, `WINDOW` | sound on/off and window `front`, `back` (behind the others) or `none` (no video); `DEBUG` and `WARP` runs default to silent and `back` |
| `JOY0` | port 0 (default `mouse`; `none` stops the host mouse injecting input) |

`--uae_ntsc=true` in `EXTRA_ARGS` gives an NTSC chipset, but FS-UAE stalled there with GLib
errors, so NTSC is not part of the test setups.

Machine setups (WHDLoad's Kickstart 1.3 inside; host ROM as listed):

| Name | Settings |
|---|---|
| A500-eq | defaults: `CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536`, 68000, `KICKSTART` default |
| 68020 | `AMIGA_MODEL=A1200 KICKSTART=~/.local/share/amiga/Kickstarts/kick40068.A1200 CHIP_KB=2048 FAST_KB=8192 CPU=68EC020 EXTRA_ARGS=--slow_memory=0`; `SERVE_WAIT=1500` (slow in warp with a breakpoint armed) |
| 68030/50 | as 68020 with `CPU=68030 EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=50000000 --uae_cpu_cycle_exact=true'`; no instruction trace, so `SWAP_ONLY=1 SERVE_WAIT=1700` |

## Driving the game: `tools/tfh.py`

```sh
WARP=1 python3 tools/tfh.py serve > amiga/.run/serve.log 2>&1 &   # boot (run.sh DEBUG=1) and serve
python3 tools/tfh.py shot "$PWD/tmp/now.png"                      # one field's screenshot
python3 tools/tfh.py profile 5 "$PWD/tmp/prof/x/trace.bin"        # cycle-exact trace of 5 fields
python3 tools/tfh.py gdb 'x/1dh $a4+11698'                        # any gdb command
python3 tools/tfh.py quit
```

`tfh.py` is AmigaXDev's shared gdb server (`amigaxdev.gdbserve`); the tools import the shared
`amigaxdev` package through `tools/_amigaxdev.py`. One lldb stays attached for the session, so
the first `profile` takes about 30 s and later ones a few seconds.

gdb runs in the repo root, and its `dump` command cannot take a path with spaces: dump to a
repo-relative path such as `tmp/x.bin`.

The game has no attract demo, and FS-UAE input playback does not work here (any live input
event during playback truncates the recording). Reproducible runs use the VERIFY input tapes.

## The VERIFY input tapes (`whdload/verify.s`, `CUSTOM5=n`)

The VERIFY build feeds input from tape n as a physical mouse and keyboard would. A tape is
indexed by `tape_vbl`, the game's VERTB count since its handler was installed; each entry
holds mouse counts per field, buttons and a decoded key byte until the next entry. With
`CUSTOM5` unset the VERIFY build patches nothing extra. Run with `JOY0=none`.

| n | Tape |
|---|---|
| 1 | mouse calibration |
| 2 | main menu → Fly Training Flight → Spitfire → flight 4 (bomber with escort) → GO FLIGHT |
| 3 | 2, then a 30° roll right: 7 counts per field for 100 fields from field 8600 |
| 4, 5 | 2, then Ctrl+G twice or once (fields 7900–7918): ground detail level change |
| 6 | 2, then the `T` key (time acceleration) at fields 8800 and 9300 |
| 7 | 2, then fire (left button, fields 8600–8606) |
| 8 | 2, then fire held (fields 7800–8100): the guns' reload, `tools/guns.py` on `STATE_FIELDS` snapshots |
| 9 | 2, plus the controlled native guided-bomb mission fixture described below |

The flight loop starts at tape field 8244 on the A500-eq and 7603 on the 68030/50. The tapes
are timed for PAL: under an NTSC chipset they miss the menus. Slave symbols (e.g. `tape_vbl`):
`tools/slave_sym.py CODE.bin BASE SYMBOL` with `SLAVE=` naming the running slave (without it,
the match finds the shipped slave's KickEmu code and returns a wrong base).
`tools/tape_probe.sh N OUTDIR` boots tape N and takes screenshots labelled with the tape field.

## The fixed window: `tools/fixed_window.sh OUTDIR [SLAVE]`

Boots once to learn `bob`'s load address (accepted only once the game's level-3 handler is at
`$6C`; cached per slave and machine in `tmp/prof/hunk-*.txt`), then reboots with the flight
loop `bob:12968` armed, skips `SKIP_FRAMES` (default 40) loop passes and traces `FIELDS`
(default 100). Set `WHD_ARGS="CUSTOM2=1"` to check the enhanced game; unset/0 runs
the original game. Uses tape 2 (`CUSTOM5=2`) unless `WHD_ARGS` names another. Boots are
deterministic: two fresh boots give byte-identical traces. `OUTDIR/anchor.txt` records T, the
detail level and the tape field at the anchor.

| Variable | Instead of the trace |
|---|---|
| `SWAP_ONLY=1` | count buffer swaps with breakpoints (CPUs without an instruction trace) |
| `STATE_FIELDS=N` | N data-hunk snapshots, one per level-3 entry (`tools/state_fields.py`) |
| `STATE_ONLY=1` | stop after the snapshots and checks |
| `C2P_CHECK=N` | check N C2P calls against a model of the original (`tools/c2p_check.py`) |
| `XFORM_CHECK=N` | check N calls of each routine in `XFORM_ROUTINE` (`xform`, `proj`, `div`, `clear`, `tile`, `scen`, `pnorm`, `aiturn`) against models of the originals (`tools/xform_check.py`) |

## Reading the results

```sh
SLAVE=OUT/slave.slave python3 tools/tfh_report.py OUT/trace.bin OUT/code.bin --base 0xc00000
python3 tools/frames.py   TRACE CODE.bin BASE              # buffer swaps per field, fps
. amiga/env.sh                                                    # for python3 -m amigaxdev...
python3 -m amigaxdev.disasm hotspots --label bob TRACE CODE.bin BASE HUNKBASE OFF,...  # hottest instructions
python3 -m amigaxdev.disasm disd CODE.bin BASE HUNKBASE START END  # disassemble by bob offset
python3 tools/speed.py [--window N] [--turn] [--hz 60] OUT/state # ground speed (and turn rate) per second
python3 tools/guns.py OUT/state                                  # rate of fire (tape 8): gaps between shots
python3 tools/compare_state.py A/state B/state                   # data hunk, snapshot by snapshot
```

`BASE` is `0xc00000` on the A500-eq (slow memory), `0x200000` with fast memory and `0` with chip
memory only.
`tfh_report.py` attributes cycles to `bob`, its data hunk, the Kickstart copy and the slave
(set `SLAVE=`). Snapshots come at every level-3 entry, which includes blitter interrupts on
the A500: time them by the game's VERTB count `-8010(a4)`, as `speed.py` does.
`compare_state.py` treats pointers into `bob` at equal offsets as equal; builds that change
timing or memory layout still differ (saved stack pointers, the VBL count, chip buffer
addresses), so use it between runs of the same build and judge other builds with the model
checks and `speed.py`.

**Which instrument for which claim:** fps from `frames.py` (traces) or `SWAP_ONLY` (68030),
with one frame of resolution per window; cycle costs from `tfh_report.py` (the steadier
measure for small changes); game speed from `speed.py`; correctness of a replaced routine
from the model checks.

## Traps

- `tfh.py until` with a breakpoint that never hits blocks the server: kill this repo's
  emulator (`kill $(cat amiga/.run/fsuae.pid)`) and this repo's `tfh.py` processes.
- Conditional breakpoints that fire every field are very slow.
- Each shell starts fresh: pass `SLAVE`, `WHD_ARGS` and the machine variables on every
  command line.
- Do not edit a script while a run is executing it.

## Remaining timing audit

[framerate-audit.md](framerate-audit.md) records coverage, findings and reproduction
commands for `tools/timing_audit_check.py`. These are defect reproductions of
currently unfixed behavior, not passing claims of frame-rate independence.

### FR-01 debris regression

`tools/debris_check.py` takes the same dump/base/slave/listing arguments as
`tools/bomb_check.py`, with `--cpu 68000` or `--cpu 68040`. Use a freshly built
matching normal slave/listing. It executes native fragment constructors and
movement for every debris class and pool slot; see `internals.md` for scenarios
and limits. Rerun the bomb checks when changing their shared movement wrapper.
`tools/timing_audit_check.py` now includes this fixed-behavior regression before
reproducing the other, still-open timing defects.

### FR-02 group scheduler regression

`tools/group_timer_check.py` takes the same dump/base/slave/listing arguments
as `tools/input_combat_check.py`, plus `--cpu 68000` or `--cpu 68040`. Build a
matching normal slave/listing first. It checks repeated five-second intervals,
rate changes, time acceleration divisors, overflow boundaries and native
mission-group eligibility/placement. It also checks the original-mode timing
gate. `tools/timing_audit_check.py` includes this regression alongside FR-01;
remaining open items still have defect-reproduction assertions.

### FR-03 effect regression

`tools/effect_check.py` takes the same dump/base/slave/listing arguments as
`tools/input_combat_check.py`, plus `--cpu 68000` or `--cpu 68040`. Build a matching
normal slave/listing first. It checks native effect-state progression, real
fragment creation, motion stops and cleanup against an 8 Hz reference across
steady/changing rates, including multi-tick catch-up. The aggregate timing audit
now includes FR-01, FR-02 and FR-03 regressions before remaining defect checks.

### FR-04 world-clock regression

`tools/world_clock_check.py` uses the standard dump/base/slave/listing arguments
and `--cpu 68000|68040`. It executes native rollover/daylight routines and tests
changing-rate and accelerated-time clocks. It is included in the timing audit.

### FR-05 projectile lifetime regression

`tools/projectile_life_check.py` uses the standard dump/base/slave/listing inputs
and `--cpu 68000|68040`. Run it with `input_combat_check.py` when modifying
projectile movement, expiry or age-based damage. The timing audit includes it.

### FR-06 flak regression

`tools/flak_check.py` uses standard dump/base/slave/listing inputs and the CPU
selector. It executes native launch, hit/miss selection, delivery and aircraft
reuse. Run `group_timer_check.py` too when changing the generation hook.


### Guided-bomb mission integration (VERIFY only)

Set `VERIFY_GUIDANCE=1 STATE_ONLY=1 WHD_ARGS="CUSTOM2=1 CUSTOM5=9"`
with `tools/fixed_window.sh` and a matching VERIFY slave/listing. Keep the
anchor before flight update 64 (the default `SKIP_FRAMES=40` is suitable).
Tape 9 follows the training input and constructs one controlled guided bomb
on update 64, using the native constructor. The source aircraft's temporary
fixture fields are restored immediately. Native guidance and impact hooks
record the transition and ground-contact checkpoint in VERIFY-only symbols.
`tools/guidance_mission_check.py` reads those symbols and stops on the recorded
impact or constructor failure. The transcript lives under `guidance/` in the
capture. This is mission integration, not a performance or hardware test.

The Barto stub silently drops memory/register writes; never use debugger writes
to set up a game fixture. Stimuli must execute inside the VERIFY binary. See
AmigaXDev's `docs/reference/headless-fsuae.md` before changing this workflow.
