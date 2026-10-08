# Open work

Goal: profile Their Finest Hour as Test Drive II was profiled, then improve it. Setup follows
`~/Projects/Test Drive 2/docs/new-game-playbook.md`; its §12 checklist is the definition of done.

## Status (2026-10-08)

| Playbook step | State |
|---|---|
| §2 identify game and slave | done (`docs/profiling.md` §1) |
| §3 scaffold | done: tools copied from TD2 and adapted (`tfh.py`, `tfh_report.py`, `frames.py`, `swap_fields.py`, `state_*`) |
| §4 first boot | done: boots to the main menu on the A500-equivalent machine |
| §5 trace with PCs | done (menu trace) |
| §6 regions | done; driving by the VERIFY input tape |
| §6 reproducible window, §7 frame counter, §8 baseline, §9 game time | done (`profiling.md` §8–11) |
| §10 rebuilt slave | built on WHDLoad 20.0 and boots; gameplay equivalence unchecked; VERIFY build has the input tape (`CUSTOM5`) |

## Done

- W1 drive the game into a flight: tape 2, reproducible fixed window (`profiling.md` §8).
- `CUSTOM2`: chunky buffers in public memory with a CPU fill (`profiling.md` §9).
- `CUSTOM3`: frame pacing; 50.0 fps on the 68030/50 with `CUSTOM2` (`profiling.md` §9).
- `CUSTOM4`: real-time simulation (`profiling.md` §11).
- Tape 3: a 30° bank in flight. Tapes 4/5: ground detail 1/0 by Ctrl+G.
- `CUSTOM3` strobes COPJMP1 so the swap shows in the same field (user-reported tearing).
- `CUSTOM4` unwraps fast mouse moves (8-bit counter, user-reported roll-backs).
- Ground detail (`profiling.md` §12): fast machines booted at level 2 (no terrain);
  `CUSTOM2` gives them level 0. Level 0 is 30.9 fps on the 68030/50.

## Decided: game time (2026-10-08)

Design A, dynamic T, with real time as the reference: `CUSTOM4` (`profiling.md` §11). The
coupling test gives ground speed within 1.4% and a 30° turn within 7% between the A500-eq
(8 fps) and the 68030/50 (50 fps). Left: integer truncation in the flight model at large T.

## Next, in order

1. **Level 0 on fast machines** costs 19 fps on the 68030/50 (§12): profile it there
   (`11138`, the extra objects, the C2P with more changed longwords).
2. **The user's tearing and roll-backs**: not reproduced in the cycle-exact profiling
   configuration; check with the user after the COPJMP1 and mouse fixes.
3. **Truncation at T = 50** (`profiling.md` §11): fractional accumulators in the flight
   model's integrators (heading first: `bob:146aa`, `14546`, `14582`), AI planes included.
   Measure with tape 3 and `tools/speed.py`-style snapshot analysis.
4. Gameplay check of `CUSTOM4` beyond the fixed window: time acceleration (`T` key), views
   other than the cockpit (`bob:16620..166b2` divide by T too), AI behaviour, a full mission.
5. **Chip audit of the data hunk** and the other MEMF_CHIP allocations: move everything
   the hardware does not read to public memory. The data hunk needs a load-time change
   (e.g. clear its MEMF_CHIP flag while KickEmu reads the file, then copy the chip-needing
   parts out).
6. The C2P compare on fast CPUs and a Kalms-style merge conversion for heavy scenes (when
   many longwords change, e.g. while banking).
7. CPU caches: the 1.1 slave's `SetCPU` disables them; try KickEmu's `CACHE` (data cache off in
   chip) on 020+.
8. Profile a turning view (tape 3) on the 68020: more longwords change, so the C2P conversion
   counts.
