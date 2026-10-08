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
- Level 0 profiled (`profiling.md` §13): map scenery `bob:11138`/`1142c` and the shared 3D
  transform routines (`2f4ae`, ...), which work in data-hunk globals.
- `CUSTOM2` merge C2P (32 pixels per step, longword plane writes): 68030/50 level 0 29.4 → 30.6 fps.
- Chip audit (`profiling.md` §14): only 40 sprite bytes of the data hunk need chip. `CUSTOM2`
  loads the data hunk into public memory: **68030/50 level 0 50.0 fps**, 68020 19.6 fps.
- Caches left to WHDLoad (`CACHE`, no caches-off `SetCPU`); the user's options override.
- Time acceleration checked under `CUSTOM4` (tape 6): 3.15–3.5× and back.
- One-shot sounds (explosions, splashes) no longer replay their sample until the envelope ends
  (`profiling.md` §15; always on).
- Expansion memory 768 KB (`FASTMEMSIZE`): the game uses 666 KB in flight with `CUSTOM2`.

## Decided: game time (2026-10-08)

Design A, dynamic T, with real time as the reference: `CUSTOM4` (`profiling.md` §11). The
coupling test gives ground speed within 1.4% and a 30° turn within 7% between the A500-eq
(8 fps) and the 68030/50 (50 fps). Left: integer truncation in the flight model at large T.

## Next, in order

1. **The user's roll-backs** (mouse wrap fix): confirm with the user. Tearing is gone (user,
   2026-10-08, after the COPJMP1 fix).
2. 68020 at level 0 is 19.6 fps. Not profiled since the data hunk move: the §13 costs of the
   transform routines (`bob:2f4ae`, `2f160`, `3041c`, `2f374`, ...) and the map scenery
   (`1142c`, `11138`) were measured with their globals in chip memory, and no speed-up for
   them has been designed or measured. Re-profile first.
3. Gameplay check of `CUSTOM4` beyond the fixed window: views other than the cockpit
   (`bob:16620..166b2` divide by T too), AI behaviour, a full mission.
4. `CUSTOM2` with the data hunk moved: a full mission (the user confirmed sound, one-shots
   included, and the map and briefing screens, 2026-10-08).
5. **Truncation at T = 50** (`profiling.md` §11), postponed (2026-10-08): fractional
   accumulators in the flight model's integrators (heading `bob:146aa`, `14546`, `14582`).
6. Unmeasured: the original slave at level 1 on the 68030; rebuilt-slave gameplay
   equivalence with the shipped slave.
7. NTSC, not run. The original has no 60 Hz path: the boot benchmark (`bob:2c24`) computes
   T = 380 / fields with no PAL check, and no read of VPOSR, VBlankFrequency or
   DisplayFlags was found. At 60 Hz that T comes out 5/6 of the PAL value, so the game runs
   1.2× fast. `CUSTOM4` assumes 50 fields/s too (`DT_HZ`, `DT_TMAX`). The fix is the field
   rate measured at boot against a CIA timer. Also counted in fields: the sound envelopes
   and the waits at `bob:411c`, `9ada`, `9ba2`, `2b416`.
