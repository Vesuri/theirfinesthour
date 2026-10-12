# AI script timing inventory (FR-14, unreleased 1.3b)

The audit covers the complete dispatch tables, including entries not exercised
by the captured training mission. These are native `bob` v1.1 tables; addresses
below are hunk-0 offsets. Table locations are offsets from a4.

- Surface: three script pointers at `-12488(a4)`, four condition handlers at
  `-12476(a4)` (0: `222b8`, 1: `219e0`, 2: `21ae4`, 3: `21c9e`).
  `21954` dispatches them. Target search, firing and retargeting use native RNG
  and geometry. FR-14 gives every eligible slot 16–19 a two-second deadline;
  the old scheduler deferred subsequent ready slots by one rendering update.
- Aircraft: 66 script pointers at `-11502(a4)` and 41 condition handlers at
  `-11238(a4)`. `22140` dispatches conditions 0–40. Condition 1 (`222c2`)
  dispatches the current action; condition 2 (`22370`) handles transitions.
  Decision opportunities are the independent skill clocks from FR-12.
- Actions: 34 pointers at `-11074(a4)`: 17 update entries, followed by the
  corresponding 17 initializers. Primary wait state is `20670(a4)` (copied
  through `30964(a4)` by the action dispatcher). Secondary action state/counters
  use `20686(a4)`; that field is not uniformly a timer and must not be globally
  decremented as elapsed time.

| Action | Initializer | Update | Timing-bearing state / classification |
|---|---|---|---|
| 0 | `222b8` | `222b8` | No operation |
| 1 | `2503e` | `250c6` | Primary wait 15; secondary skill-table wait 10/6/3 |
| 2 | `25170` | `251d8` | Attitude/phase conditions |
| 3 | `25210` | `252ea` | Primary wait 5, attitude/phase conditions |
| 4 | `25400` | `25496` | Primary wait 20; secondary waits 2 and 4 |
| 5 | `25548` | `2559e` | Secondary action-count/phase state |
| 6 | `255ee` | `256b0` | Geometry, phase and secondary action-count state |
| 7 | `25a7a` | `25aa6` | Secondary action-count/phase state |
| 8 | `25af8` | `25b26` | Attitude target update |
| 9 | `25b3e` | `25bb0` | Primary wait 8; secondary skill-dependent state |
| 10 | `25bec` | `25bf4` | Geometry/approach conditions |
| 11 | `25f5e` | `25fc0` | Secondary action-count/phase state |
| 12 | `26042` | `26080` | Staged primary waits 4, 12 and 5 |
| 13 | `263e0` | `2650c` | Primary waits 3 or 5 |
| 14 | `2653a` | `265de` | Literal five decisions; position/expiry exit |
| 15 | `26610` | `2662a` | Speed/phase conditions |
| 16 | `2667c` | `26696` | Taxi speed changes per decision; heading corrections divided by T |

Every call to the wait helper `24fee` uses N in
`{2,3,4,5,6,8,10,12,15,20}`. Its intended unit is two seconds, converted to
**decision opportunities**, not outer frames. FR-14 replaces `floor(2T /
20398[plane]) * N` with `N`, `2N`, `4N` or `6N` from the private skill period.
The maximum is 120, so every native destination byte fits. The high-skill
15-unit wait previously produced 60, 120 and 90 counts at T=2/8/50. Native
zero checks, phase transitions and secondary counters remain unchanged;
expiry is observed at a native decision opportunity. Literal decision counts
remain skill-dependent, as in the original, but no longer rendering-dependent.

The only direct T reads inside the action table are the wait conversion and
action 16's `267c6`/`267fe` taxi turns. The latter run per decision, so their
correction is now the native reference-T=8 value (1024 angle units per decision).
Speed/acceleration changes in that action were already per decision; FR-12
makes their opportunities consistent.

The complete condition table contains these handler entries:

```
0:222b8 1:222c2 2:22370 3:226a0 4:22e4a 5:22704 6:228d8
7:229fc 8:22e62 9:232e0 10:23340 11:23444 12:2344c 13:23604
14:237ac 15:23c54 16:23cb4 17:23e3e 18:23af6 19:23c02
20:2409c 21:24136 22:24280 23:23dca 24:2280c 25:22c0a
26:22cb4 27:242da 28:2442e 29:245c6 30:246c2 31:24858
32:22cf4 33:248e4 34:249f0 35:24b20 36:24c4c 37:24da4
38:24f22 39:24e6a 40:24f2c
```

Their clock-bearing external paths are the two-second script reset `21872` /
`21ff4` (FR-12/14), native bombing `1d280` (FR-08/09), flak launch `1f77e`
(FR-06/13), gunner lead `1cf98` and pursuit helper `26c1e` → `26e46` (FR-13).
The remaining external target/geometry/transition helpers (`be7e`, `11ea2`,
`12150`, `15344`, `1e9d6`, `2685c`, `2694c`, `26afc`, `26b52`, `27082`,
`270ec`, `2735a`, `27420`) contain no independent T-based countdown or division.
Math and RNG library calls remain native. This inventory distinguishes those
paths from the continuous flight-control update tracked in FR-15.

`tools/script_timer_check.py` executes all three surface scripts, compares
native data/RNG against prescribed simultaneous two-second service, tests all
wait arguments and skill periods through the native action dispatcher, and
compares all 34 action/initializer entries at three controlled phase values.
Dedicated taxi fixtures cover both turn signs, heading clamping and all speed
branches. This combines static table/caller coverage with controlled native CPU
checks; it is not exhaustive branch coverage of every possible mission state.
