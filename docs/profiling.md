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
  absolute `$60BC`. On VERTB (`bob:28d66`) it writes COP1LC from one of two copper lists
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
input tape in the slave (`docs/open-work.md`).
