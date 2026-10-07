# Open work

Goal: profile Their Finest Hour as Test Drive II was profiled, then improve it. Setup follows
`~/Projects/Test Drive 2/docs/new-game-playbook.md`; its §12 checklist is the definition of done.

## Status (2026-10-06)

| Playbook step | State |
|---|---|
| §2 identify game and slave | done (`docs/profiling.md` §1) |
| §3 scaffold | done: tools copied from TD2 and adapted (`tfh.py`, `tfh_report.py`, `frames.py`, `swap_fields.py`, `state_*`) |
| §4 first boot | done: boots to the main menu on the A500-equivalent machine |
| §5 trace with PCs | done (menu trace) |
| §6 regions | done; **driving: blocked, no demo** (below) |
| §6 reproducible window, §7 frame counter, §8 baseline, §9 game time | not started; need gameplay |
| §10 rebuilt slave | built on WHDLoad 20.0 and boots; gameplay equivalence unchecked; VERIFY build has the input tape (`CUSTOM5`) |

## Done

- W1 drive the game into a flight: tape 2, reproducible fixed window (`profiling.md` §8).
- `CUSTOM2`: chunky buffers in public memory with a CPU fill (`profiling.md` §9).

## Next, in order

1. **Frame pacing** on fast machines: before drawing into a buffer, wait until the VBL has
   taken the previous swap request (cap: one frame per field). Needed before any 50 fps
   claim; measure with `SWAP_ONLY` on the 68030/50.
2. **Time model measurements** (§10): state map (aircraft position, attitude, speed) and the
   coupling test: same tape on A500-eq and 68020, game state compared field by field.
   Decide between (a) a dynamic `T` from measured fields per frame and (b) a fixed-step
   simulation run N times per frame. The user asked whether (a) works. Watch integer
   granularity at small `T`, `T>10` detail selection and time acceleration (`11700`).
3. **Chip audit of the data hunk** and the other MEMF_CHIP allocations: move everything
   the hardware does not read to public memory. The data hunk needs a load-time change
   (e.g. clear its MEMF_CHIP flag while KickEmu reads the file, then copy the chip-needing
   parts out).
4. The C2P compare on fast CPUs and a Kalms-style merge conversion for heavy scenes (when
   many longwords change, e.g. while banking).
5. CPU caches: the 1.1 slave's `SetCPU` disables them; try KickEmu's `CACHE` (data cache off in
   chip) on 020+.
6. Tape: bank the plane after the anchor, for a turning view (user's suggestion). In flight,
   mouse counts are rate input (`bob:112`).
