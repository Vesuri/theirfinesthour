# Framerate dependency audit

12 October 2026; original `bob` v1.1 and unreleased slave **1.3b**.
This is a system inventory and defect investigation, not another gameplay patch.
Individual fixes and coverage gaps are tracked as **FR-01 through FR-27** in
[open-work.md](open-work.md#framerate-work-items).

## Scope and evidence

Start at the world update (`bob:12eaa`), follow its calls, decode every entry in
movement (`bob:15b26`) and impact (`bob:1dc20`) dispatch, and inspect references
to the step divisor and derived clocks. Include counters decremented once per
update, integer rate divisions, sampled thresholds, and input/replay boundaries.
Cross-check against the existing slave patches. Searching only for divisions
misses byte accesses (the clock reads the low byte of T at `bob:14e68`) and
counters initialized somewhere else.

Here T means the current simulation divisor at A4+11700; normally one update
represents 1/T seconds. A4+11698 is the unaccelerated divisor. Enhanced mode
changes these as frame duration changes. Multiplying a countdown by T once
**does not** make its remaining duration independent of later changes in T.
Time acceleration is a separate case that future tests must also cover.

Evidence labels below distinguish native CPU reproductions, static arithmetic
findings, and candidates needing a controlled scenario. This covers the main
update and object dispatch families; it is not proof that every mission script,
indirect callback or state transition is free of other dependencies. In
particular fuel/engine/resource accounting and every AI script opcode have not
been exhaustively followed. No performance or physical-hardware claim is made.

## Reproduced issues (audit baseline)

**FR-01 through FR-04 are now implemented.** Effects now advance at a fixed
8 Hz, preserving native emission and cleanup transitions; see
[internals.md](internals.md#fr-03-effect-animation-clock-unreleased-13b).
 The group scheduler uses a five-second
elapsed-time countdown with native eligibility/placement preserved. See
[internals.md](internals.md#fr-02-aircraft-group-processing-clock-unreleased-13b).

**FR-01:** debris uses fixed 64 Hz movement, fractional
gravity and elapsed-time drag/expiry. See [internals.md](internals.md#fr-01-debris-and-wreckage-unreleased-13b)
for the correction and regression scope. The debris row below records the
pre-fix reproduction, as do the group-timer, effect-cadence and world-clock rows; other rows remain open.

`tools/timing_audit_check.py` executes the relevant original routines with the
current movement patches installed, on Unicorn's 68000 and 68040 models. Both
models produce the same results. Fixtures are controlled memory states; these
are not full missions. T is held constant except in the lifetime test.

| Concept | Evidence | Consequence |
|---|---|---|
| Falling fragments and wreckage (classes 9, 10, 11) | `bob:15954` subtracts `max(1, floor(22/T))` from vertical velocity every update. Starting at zero, after one simulated second velocity is -16 at T=8, -25 at T=25, -50 at T=50 and -60 at T=60. | Strongly different fall trajectories. The class-3 bomb fix does not cover these classes. Constructors are `bob:1d588` (10/11) and `bob:1d670` (9). |
| Aircraft-group processing clock | `bob:bfa4` computes 5T then stores only a byte at `bob:bfac`; decrement at `bob:bf9c`. Period is 5.125s at T=8, 5.02s at T=50, **0.75s at T=60**. | Overflow above T=51 changes group-processing cadence. This is reachable in NTSC enhanced mode, not ordinary PAL T<=50. Eligible groups pass to `bob:c0fe`, which prepares group placement and calls the aircraft constructor. Full mission consequences remain untested. |
| Effect animation, debris emission and cleanup | `bob:176aa` decrements a clock reloaded with `floor(T/8)+1`. Cadence is 4Hz at T=8, 6.25Hz at T=25, 7.142857Hz at T=50 and 7.5Hz at T=60. | More than drawing: the same update emits fragments (`bob:1785a`, `17864`), stops motion (`bob:178a0`) and removes objects (`bob:17838`, `178be`). |
| World clock / time of day | `bob:14e5e` decrements a byte and advances seconds only when it becomes negative, then reloads T. One clock second therefore takes T+1 updates: 1.125s at T=8 versus 1.02s at T=50. | Accumulating clock drift; this routine also updates daylight state. Not a claim that all mission timers use this clock. |
| Existing projectile lifetime when T changes | Bullets initialize a 2T countdown (`bob:1cdaa`), consumed once per update (`bob:15a2c`). A remaining count of 16 expires after 0.32s at T=50. | A lifetime originally budgeted as two seconds at T=8 can shrink sharply after a rate change. The test deliberately steps T abruptly to isolate the mechanism; real enhanced mode smooths changes, so this is not a measured in-game transition magnitude. |

## Other concepts requiring treatment or targeted validation

| Concept | Code evidence and current status | Targeted check |
|---|---|---|
| Flak / delayed anti-aircraft damage | Separate path `bob:1f77e` creates class-8 objects in slots 112..123. Hit/miss is selected at launch (`bob:1f92c`, `1f99e`), and a distance-derived delay is multiplied by T (`bob:1f9ce`). `bob:1fdb8` decrements it, turns a miss into an effect, or applies stored damage to a stored target (`bob:1feaa`). These slots skip ordinary bullet movement (`bob:15a1a`). **Not covered by swept bullet collision.** | Equal elapsed-time firing trials with fixed random seeds; compare attack opportunities, selected outcome and delayed damage at steady and changing rates. Do not replace the native launch-time probability model without a design decision. |
| Gun reloads and automatic bursts | Reload is integer T/3 (`bob:1cc30`), consumed by the frame-counted state machine at `bob:1c5dc`. Rounding and checking zero before decrement add cadence error; remaining counts are not rescaled when T changes. | Count shots, ammunition and applied damage over equal time, for player and AI guns, including changes of T. |
| Bomb salvos and automatic guidance | Release cooldown T/2 (`bob:1d4e0`, decrement `bob:1c6b6`); guidance countdown and altitude-triggered mode transitions in `bob:1fee4`. Fixed bomb motion does not fix outer-world guidance or release timing. | Compare spacing of a full salvo, guidance transition positions and impact patterns. Existing tests cover preset guided mode, not the changing guidance controller. |
| Progressive aircraft damage | `bob:1ea46` schedules processing using integer T/3 (`bob:1ea66`). This controls damage-related state changes and effects. | Apply identical initial damage, compare time to gun disablement, further state changes and destruction. Include changing T and animation interactions. |
| Ground/ship target damage progression | `bob:1f4f6` uses a 4T countdown (`bob:1f50a`) to process target damage/state. | Equal-time destruction and sinking/state progression, with identical initial damage. The exact visible interpretation of every state still needs validation. |
| AI decisions, target acquisition and script waits | Aircraft decision/control paths `bob:22090`, `22eaa`; ground/surface scheduler `bob:218a2` with 2T byte delays (`bob:2190a`), servicing at most one eligible object per update. Script delay helper `bob:24fee`; aiming/delay calculations `bob:26e46`. | Measure reaction latency, firing opportunities and random draws over equal elapsed time. More updates alone do not prove increased hit probability: follow each event's gate. Audit script opcodes before declaring full coverage. |
| AI manoeuvres and attitude corrections | Uncarried integer divisions remain in `bob:200c0`: e.g. 4096/T (`bob:200d0`), 455-based pitch increments (`bob:205fa`, `206a8`), aircraft-specific pitch rate (`bob:20cf6`), 728/T (`bob:20e1e`), 20480/T (`bob:20f02`). Player attitude recovery also has 1024/T and 512/T (`bob:149d2`, `14a66`). | Compare equal-time pitch/roll response and complete manoeuvres. AI heading fraction patches do not imply all attitude axes are corrected. Arithmetic quantization is evident; gameplay severity is not yet measured. |
| Ground steering and auxiliary drift/wind | Ground steering `bob:146aa`; extra position terms divide signed values by T at `bob:155d6`, `1563a`, `1569e`, with no carry. A component smaller than T can disappear. | Taxi/landing steering and small positive/negative drift, isolated from main polar movement. Trace all writers before attributing every auxiliary component to atmospheric wind. |
| Aircraft ground contact, landing and other collision transitions | Class-1 impact path `bob:1d974` tests altitude and attitude after movement; falling classes use `bob:1db62`. These do not use the bullet swept-box test. | Cross terrain/contact boundaries at identical real-time states, testing overshoot, landing versus crash, and any pair/object collision helpers reached by flight states. No newly reproduced tunnelling defect is claimed here. |
| Mission waits, radio/HUD expiry and flight transitions | Examples: 40T waits (`bob:c31e`, `c336`, `12dd0`), 180T (`bob:1299a`), 12T HUD message (`bob:1c51a`, decrement `bob:1c536`). | Compare elapsed-time expiries through sustained rate changes and time acceleration. Keep presentation-time and simulation-time policy explicit. |
| Recorded flight/replay | Recorder `bob:13bf8` stores one control tuple per update, capacity 1023 updates; playback `bob:16a3a` consumes one tuple and runs the world update. Replay initialization `bob:16a9e` restores saved state and RNG. | Recording capacity is frame-based (~127.9s at 8Hz, ~20.5s at 50Hz). Check whether saved state plus current timing patches reproduce the original timestep history; full snapshot contents and cross-rate replay determinism remain unverified. |
| Camera, gunner view and field-based input/audio | Camera divisions in `bob:16642`..`1674a`, gunner controls in `bob:139d2`. Mouse polling, joystick ramp and audio envelopes also have VERTB-based clocks. | Separate render-rate errors from PAL/NTSC field-rate differences. The existing mouse flight-control fix does not certify every view/control path. |

## Movement and impact coverage

The dispatch tables give a finite inventory of motion families. Object classes
are behavior codes, not artwork IDs or necessarily one-to-one gameplay names.

| Class | Movement | Impact dispatch / audit result |
|---|---|---|
| 0 | None | None |
| 1 | Aircraft motion, `bob:15502` | Aircraft contact/state path; main position fractions covered, auxiliary drift and contact sampling remain |
| 2 | Stationary bookkeeping, `bob:156f4` | No dedicated impact handler |
| 3 | Bomb/falling path, `bob:157c2` | Bomb impact `bob:1db46`; slots 20..51 now use fixed 64Hz bomb steps |
| 4, 5 | No movement | Effects/timers may still update elsewhere |
| 6 | Straight/polar motion, `bob:15770` | Ground-impact path `bob:1db62` |
| 7 | Projectile path, `bob:15a1a` | Swept bullet collision now patched; lifetime/reload still frame-counted |
| 8 | Same dispatch as 7, but slots >=112 bypass movement | No ordinary bullet impact handler; delayed damage/effects handled separately |
| 9, 10, 11 | Falling path, `bob:157c2` | Ground-impact path; gravity defect reproduced for all three |
| 12 | Straight/polar motion, `bob:15770` | No handler in this impact table; surface-object script/attack paths need their own clocks |
| >=13 | Outside movement table | Effect animation can still change or remove these objects |

Already present: fractional main position steps, player flight roll/turn/pitch,
AI heading changes, corrected mouse scaling, swept bullet hits, fixed bomb
motion. Native acceleration/deceleration helpers `bob:21394` and `2140c` already
carry fractional speed through A4+19998; they should not be classified as broken
just because they divide by T. Neither fraction carry nor time-scaled rates
prove frame-independent nonlinear integration or state transitions.

## Reproduction and next work

Build a matching normal slave/listing and use a local live flight dump as
specified in [development.md](development.md):

```sh
make -C whdload VASMFLAGS='-L ../tmp/input-combat/release.lst'
python3 tools/timing_audit_check.py tmp/input-combat/bomb-smoke/code.bin 0x200000 whdload/TheirFinestHour.slave tmp/input-combat/release.lst --cpu 68000
python3 tools/timing_audit_check.py tmp/input-combat/bomb-smoke/code.bin 0x200000 whdload/TheirFinestHour.slave tmp/input-combat/release.lst --cpu 68040
```

Apart from the completed FR-01/FR-02/FR-03/FR-04 regressions, checks assert unfixed behavior; revise them to assert equal
elapsed-time outcomes when fixes are implemented. Captures, disassembly and
compiled slave bytes remain local and ignored.

Prioritize combat clocks (flak, reloads, lifetimes, salvo/guidance, progressive
damage), then the group timer overflow, aircraft/ground contact and control
rounding, followed by debris/effects, world/mission clocks and replay. Test each
at T=8/25/50/60, changing T, and accelerated time. The aim is an explicit clock
policy for every system, with fractional elapsed-time counters or fixed-rate
updates where appropriate, rather than another collection of guessed patches.
