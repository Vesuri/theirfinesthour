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
| §10 rebuilt slave | built on WHDLoad 20.0 and boots; gameplay equivalence unchecked; no VERIFY build yet |

## W1. Drive the game into a flight (next)

There is no attract demo, and FS-UAE playback breaks on the first live event (`profiling.md`
§6). Plan: a VERIFY-only input tape in the rebuilt slave, indexed by VBL count since boot,
that overrides what the level-3 handler reads:
- pointer deltas `-4704/-4702(a4)` (added to the pointer at `11958/11960(a4)`) and the button
  bits `-8008(a4)`, to click through the menus;
- key presses, through the keyboard handler (`bob:28e2a`) or its buffer, for flight keys.
Hook with `PL_PS` inside the VERTB branch (`bob:28d66..28df6`), replacing whole instructions.
Capture with `JOY0=none`.

Then: find the start-of-flight anchor, prove two boots identical (§6 of the playbook), validate
the swap counter, take the baseline.
