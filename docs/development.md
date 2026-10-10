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
`dist/TheirFinestHour_v<ver>_0037.lha`: the same members, with only the slave and the ReadMe
changed (Psygore's ReadMe with `whdload/readme-history.txt` added above his history), checked
member by member after re-extraction. `<ver>` comes from the slave's `$VER`.

## Running

`amiga/run.sh` boots the Kickstart 3.1 host from `DH0` plus the Workbench floppy; its
startup-sequence runs `WHDLoad TheirFinestHour.Slave PRELOAD SPLASHDELAY=0 NOREQ` on `DH1`.

| Variable | Meaning |
|---|---|
| `SLAVE` | slave to run instead of the installed one |
| `WHD_ARGS` | extra WHDLoad arguments, e.g. `CUSTOM2=1 CUSTOM3=1 CUSTOM4=1` |
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

The flight loop starts at tape field 8244 on the A500-eq and 7603 on the 68030/50. The tapes
are timed for PAL: under an NTSC chipset they miss the menus. Slave symbols (e.g. `tape_vbl`):
`tools/slave_sym.py CODE.bin BASE SYMBOL` with `SLAVE=` naming the running slave (without it,
the match finds the shipped slave's KickEmu code and returns a wrong base).
`tools/tape_probe.sh N OUTDIR` boots tape N and takes screenshots labelled with the tape field.

## The fixed window: `tools/fixed_window.sh OUTDIR [SLAVE]`

Boots once to learn `bob`'s load address (accepted only once the game's level-3 handler is at
`$6C`; cached per slave and machine in `tmp/prof/hunk-*.txt`), then reboots with the flight
loop `bob:12968` armed, skips `SKIP_FRAMES` (default 40) loop passes and traces `FIELDS`
(default 100). Uses tape 2 (`CUSTOM5=2`) unless `WHD_ARGS` names another. Boots are
deterministic: two fresh boots give byte-identical traces. `OUTDIR/anchor.txt` records T, the
detail level and the tape field at the anchor.

| Variable | Instead of the trace |
|---|---|
| `SWAP_ONLY=1` | count buffer swaps with breakpoints (CPUs without an instruction trace) |
| `STATE_FIELDS=N` | N data-hunk snapshots, one per level-3 entry (`tools/state_fields.py`) |
| `STATE_ONLY=1` | stop after the snapshots and checks |
| `C2P_CHECK=N` | check N C2P calls against a model of the original (`tools/c2p_check.py`) |
| `XFORM_CHECK=N` | check N calls of each routine in `XFORM_ROUTINE` (`xform`, `proj`, `div`, `clear`) against models of the originals (`tools/xform_check.py`) |

## Reading the results

```sh
SLAVE=OUT/slave.slave python3 tools/tfh_report.py OUT/trace.bin OUT/code.bin --base 0xc00000
python3 tools/frames.py   TRACE CODE.bin BASE              # buffer swaps per field, fps
python3 tools/hotspots.py TRACE CODE.bin BASE HUNKBASE OFF,...    # hottest instructions
python3 tools/disd.py     CODE.bin BASE HUNKBASE START END       # disassemble by bob offset
python3 tools/speed.py [--window N] [--hz 60] OUT/state          # ground speed per second
python3 tools/compare_state.py A/state B/state                   # data hunk, snapshot by snapshot
```

`BASE` is `0xc00000` on the A500-eq (slow memory) and `0x200000` with fast memory.
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
