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

## W1. Drive the game into a flight (in progress)

There is no attract demo, and FS-UAE playback breaks on the first live event (`profiling.md`
§6). The VERIFY input tape works (`profiling.md` §7): it moves the menu pointer. Next:
1. Write tape 2 (`tape_training`): pin the pointer to a known corner, or start from (160,40)
   at field ≥ 2090. Move to "Fly Training Flight" (screenshot (392,134), so pointer about
   (159,52)) and hold the left button for a few fields. Then follow the screens that come up
   (aircraft choice, briefing) with screenshots, until the plane is flying.
2. Check whether a flight needs keys (throttle `+`, etc.); the tape's key byte is still untested.
3. Find a start-of-flight anchor (first frame-end `bob:12f38` since boot is a candidate) and
   adapt `tools/fixed_window.sh` (still TD2's, uncommitted) to it.
4. Reproducibility: two boots must give identical traces. Note the menu's RNG (`bob:2915c`)
   advances while the menu waits, so the tape's timing must be exact.
5. Validate the swap counter (`frames.py` against `swap_fields.py`), then take the baselines.
