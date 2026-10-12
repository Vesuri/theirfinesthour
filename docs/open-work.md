# Open work

The slave is at version **1.3b** (beta): Psygore's v1.1 plus the changes in `internals.md`.
`make dist` builds the release archives (`development.md`).
All current changes are unreleased and belong to 1.3b; do not bump the version
for further fixes before this release is published.

## Next

1. **Release decisions:** when to drop the "b". Enhanced framerate is off by default
   (`CUSTOM2=1` enables it); packaged game icons include that tooltype, so
   Workbench launches enable it by default. Real A1200/68040 feedback on mouse feel and combat
   in 1.3b is pending; the 68040 emulator is checked, not physical hardware. 68060 remains
   unmeasured.

2. **Bomb validation:** 1.3b fixes the reproduced ballistic landing drift using
   fixed bomb steps. Native CPU checks cover variable frame rates, dives, climbs,
   target boundaries, salvos and slot reuse. Real-machine bombing, bombing sights
   and full missions with automatic bomb guidance still need play-testing.

3. **Framerate fixes:** the individually tracked items below cover every family
   in [framerate-audit.md](framerate-audit.md), including its remaining coverage
   gaps. Start with combat clocks (FR-05 through FR-11), then FR-02 and aircraft
   controls/contact. IDs are stable references, not an implementation order.

## Framerate work items

FR-01 through FR-06 are **complete**; FR-07 through FR-27 remain **open**. Each item is
independently closable; shared timing
helpers may be reused, but do not close another item without its own evidence.
“Reproduced” means the audit's isolated native CPU check demonstrates a defect.
“Static finding” or “candidate” still requires a controlled reproduction before
choosing a gameplay change. A candidate may be closed as verified unaffected,
with the tested scope and evidence recorded, rather than patched speculatively.

For each fix: preserve original-mode behavior, gate changes behind Enhanced
framerate, keep version **1.3b**, and replace defect-reproduction assertions with
regression checks for the intended behavior. Compare equal elapsed simulation
time at T=8/25/50/60, changing T and time acceleration where applicable. Exercise
native code on 68000 and 68040; distinguish these checks from emulator integration
and physical-hardware validation. Record any accepted rounding or sampling
bounds. Input tapes, pinned RNG and other instruments stay in VERIFY builds.

### FR-01 — Falling debris and wreckage

- [x] **Complete — 12 October 2026, unreleased 1.3b.** Fixed gravity and vertical integration for falling
  classes 9/10/11, including their drag and expiry clocks. Entry: `bob:15954`;
  constructors: `bob:1d588`, `1d670`.
- **Done when:** equal-time trajectories, ground contact and lifetimes agree
  across rates for all three classes, including slot reuse. Keep class-3 bomb
  behavior covered by its existing regressions.
- **Validation:** native 68000 and 68040 checks pass for all three classes at
  T=2/4/8/25/50/60 and changing rates: trajectories, first ground contact,
  four-second expiry, repeated five-second drag, zero speed and all 12 slot
  resets. Bomb regressions pass on both CPUs; input/combat and original-mode
  gate checks pass on 68040. Normal/VERIFY builds and 1.3b archive validation pass.
  See [internals.md](internals.md#fr-01-debris-and-wreckage-unreleased-13b).
  Physical-Amiga play-testing and full-pool performance remain unmeasured;
  effect emission/animation timing is tracked separately in FR-03.

### FR-02 — Aircraft-group processing timer

- [x] **Complete — 12 October 2026, unreleased 1.3b.** Removed the 5T byte overflow and frame-counted
  scheduling error at `bob:bfa4`, `bfac`, `bf9c`.
- **Done when:** the intended interval survives rate changes and T=51/52/60,
  and a mission-level check confirms eligible group processing/placement through
  `bob:c0fe` retains its intended behavior.
- **Validation:** five-second elapsed-time cadence and new-flight reset pass
  on 68000 and 68040 at T=2/4/8/25/50/51/52/60 and changing-rate sequences.
  Controlled native mission-group eligibility, placement and aircraft creation
  match an original due scan; blocked groups remain blocked and eligible
  replacements wait for their deadline. Original-mode gate checks pass.
  The combined 68040 audit also passes FR-01 and the remaining baseline checks.
  Normal/VERIFY builds and both 1.3b archive validations pass. See
  [internals.md](internals.md#fr-02-aircraft-group-processing-clock-unreleased-13b).
  No end-to-end emulator mission or physical-Amiga test was performed.

### FR-03 — Effect animation, emission and cleanup

- [x] **Complete — 12 October 2026, unreleased 1.3b.** Gave the effect update a consistent
  elapsed-time cadence, including fragment emission, motion stops and removal.
- **Done when:** animation duration, emitted fragment counts and cleanup times
  agree across rates, with no skipped or duplicated state-transition effects.
- **Validation:** native effect-state equivalence passes on 68000 and 68040
  for nine fixtures at T=2/4/8/25/50/60 and changing rates. Native fragment
  emission, motion stops, removal, secondary effects, multi-tick catch-up,
  new-flight reset and original-mode gate are covered. Normal/VERIFY builds
  and both 1.3b archive validations pass. See
  [internals.md](internals.md#fr-03-effect-animation-clock-unreleased-13b).
  No visual emulator run, physical-Amiga test or catch-up cost measurement was
  performed; other world systems still supply state once per outer update.

### FR-04 — World clock and daylight

- [x] **Complete — unreleased 1.3b.** Corrected the T+1 update second and changing-rate
  countdown at `bob:14e5e`.
- **Done when:** long-run clock time tracks simulation time, including second,
  minute, hour and day rollover, daylight transitions and accelerated time.
- **Validation:** `world_clock_check.py` passes on 68000 and 68040, including
  an hour-long run, changing rates, daylight equivalence and flight reset.
  Normal slave build passes; visual/hardware validation remains pending.

### FR-05 — Projectile lifetimes

- [x] **Complete — unreleased 1.3b.** Replaced frame-counted bullet expiry initialized at
  `bob:1cdaa` and consumed at `bob:15a2c`; inspect associated age/grace checks.
- **Done when:** lifetime and expiry distance remain consistent across rate
  changes, slot reuse resets age correctly, and existing hit regressions pass.
- **Validation:** native lifetime and input/combat checks pass on 68000 and
  68040. Coverage includes final-segment hits, equal expiry distance, all 48
  constructor slots and the one-second damage-age boundary. Normal build
  passes; rendering/hardware tests remain pending.

### FR-06 — Flak and delayed anti-aircraft damage

- [x] **Complete — unreleased 1.3b.** Corrected timing in the separate launch/outcome
  and delayed-damage path (`bob:1f77e`, `1f9ce`, `1fdb8`, `1feaa`). Preserve the
  native launch-time probability model while establishing its timing policy.
- **Done when:** controlled equal-time trials compare attack opportunities,
  selected outcomes, damage delay and miss effects across rates; cover target
  removal/reuse while damage is pending. Coordinate attack scheduling with FR-13.
- **Validation:** native launch/RNG/placement equivalence to the T=8 reference
  and elapsed delivery pass on both CPU models, including removed/reused
  targets, no repeat and zero delay. All twelve flak slots/full-pool failure
  are checked; FR-02 group placement still passes. Native probability is
  preserved; AI attack-opportunity scheduling remains FR-12/FR-13.

### FR-07 — Gun reloads and automatic bursts

- [x] **Complete — unreleased 1.3b.** Replaced rounded T/3 reloads and frame-counted
  burst cadence (`bob:1cc30`, `1c5dc`) for player and AI guns.
- **Done when:** equal-time shots, ammunition use, burst length and damage agree
  across rates, including rate changes during reload and held-fire transitions.
- **Validation:** native player/AI firing, ammunition and burst completion agree
  at T=2/4/8/25/50/60 and changing rates on both CPU models. Six fire events
  give identical native target damage. Release/repress, empty ammo, full pool,
  allocation reset and original-mode gating pass. Rendered validation pending.

### FR-08 — Bomb-salvo release spacing

- [ ] **Open — static finding.** Correct the release cooldown at `bob:1d4e0`
  and its consumption at `bob:1c6b6`, independently of bomb motion.
- **Done when:** full-salvo release times, inventory use and spatial spacing
  agree across rates, including rate changes during an active salvo.

### FR-09 — Automatic bomb guidance

- [ ] **Open — candidate.** Investigate and fix countdown and sampled altitude
  transitions in `bob:1fee4`; the existing fixed bomb motion tests only preset
  guided mode, not the changing controller.
- **Done when:** complete guided drops compare transition times/positions and
  impact patterns across rates and accelerated time, with a mission integration
  check. Keep the existing bomb-motion and impact regressions passing.

### FR-10 — Progressive aircraft damage

- [ ] **Open — static finding.** Correct the T/3 damage-processing cadence in
  `bob:1ea46`, `1ea66`, including its interaction with effect state changes.
- **Done when:** identical initial damage produces consistent times to disabled
  guns, further damage states and destruction across rates.

### FR-11 — Ground and ship damage progression

- [ ] **Open — static finding.** Identify the target states and correct the 4T
  processing clock at `bob:1f4f6`, `1f50a`.
- **Done when:** identical damage produces consistent destruction and applicable
  sinking/state-transition times for each supported ground/surface target type.

### FR-12 — Aircraft AI decisions and target acquisition

- [ ] **Open — candidate.** Trace decision and target-selection gates in
  `bob:22090`, `22eaa`; correct dependencies on update opportunities.
- **Done when:** controlled encounters compare reaction latency, target changes
  and random-decision opportunities over equal time at different rates. Record
  which differences are expected consequences of changed physical encounters.

### FR-13 — AI aiming and firing opportunities

- [ ] **Open — candidate.** Trace aiming/delay calculations around `bob:26e46`
  and their callers; correct timing without changing intended skill/probability.
- **Done when:** fixed-state, controlled-RNG trials compare aim updates, attack
  opportunities and shot outcomes over equal time. Validate separately from
  weapon reload (FR-07) and delayed flak damage (FR-06).

### FR-14 — Surface-object scheduling and AI script waits

- [ ] **Open — static finding and coverage gap.** Correct 2T delays and the
  one-eligible-object-per-update scheduler (`bob:218a2`, `2190a`); audit script
  waits (`bob:24fee`) and every reachable timing-related script opcode.
- **Done when:** multiple active surface objects have consistent scheduling and
  script-wait durations across rates, without starvation; document opcode and
  callback coverage and create separate IDs for any newly discovered systems.

### FR-15 — AI manoeuvre pitch and roll

- [ ] **Open — static finding.** Correct uncarried attitude increments in
  `bob:200c0`, including `bob:200d0`, `205fa`, `206a8`, `20cf6`, `20e1e`, `20f02`.
- **Done when:** equal-time pitch/roll responses and complete manoeuvres agree
  for affected aircraft types, including small inputs and direction reversals.
  Existing AI heading fixes must remain covered.

### FR-16 — Player attitude recovery

- [ ] **Open — static finding.** Correct rounded recovery increments at
  `bob:149d2`, `14a66`, independently of the already patched flight controls.
- **Done when:** return-to-level/recovery trajectories and completion times
  agree across rates, including both signs and small remaining deflections.

### FR-17 — Ground steering

- [ ] **Open — static finding.** Investigate and fix lost fractional steering
  at `bob:146aa`.
- **Done when:** equal-time taxi/landing steering responses agree across rates
  for small and large inputs in both directions, without changing airborne input.

### FR-18 — Auxiliary drift and wind terms

- [ ] **Open — static finding.** Trace the writers and meaning of the extra
  position components, then fix truncation at `bob:155d6`, `1563a`, `1569e`.
- **Done when:** small positive and negative components accumulate consistently
  across rates, including zero crossings and object reuse; document which
  components actually represent wind.

### FR-19 — Landing, ground contact and collision transitions

- [ ] **Open — candidate.** Audit sampled contact/state tests (`bob:1d974`,
  `1db62`) and pair/object collision helpers reached by flight states.
- **Done when:** controlled boundary crossings compare landing versus crash,
  overshoot and contact outcomes across rates. Record handler coverage and
  validate any swept/contact-time correction independently of bullet collision.

### FR-20 — Mission waits and flight transitions

- [ ] **Open — static finding.** Correct frame-counted mission/transition waits,
  including `bob:c31e`, `c336`, `12dd0`, `1299a`; identify their intended clocks.
- **Done when:** relevant mission and flight transitions expire consistently
  through sustained rate changes and accelerated time, with mission-level checks.

### FR-21 — Radio and HUD message durations

- [ ] **Open — static finding.** Correct message expiry (`bob:1c51a`, `1c536`)
  and related display waits using an explicit presentation/simulation clock policy.
- **Done when:** message visibility and replacement behavior remain consistent
  across rates, including accelerated time and interrupted/replaced messages.

### FR-22 — Flight recording and replay

- [ ] **Open — static finding and candidate.** Resolve frame-based recording
  capacity and verify timestep history through recording/playback and saved-state
  restoration (`bob:13bf8`, `16a3a`, `16a9e`).
- **Done when:** recording duration has an explicit policy and replay reproduces
  recorded simulation events despite a different playback rendering rate; verify
  RNG, timing accumulators, end-of-recording behavior and save compatibility.

### FR-23 — Camera motion

- [ ] **Open — candidate.** Audit and correct rate divisions and sampled camera
  motion at `bob:16642` through `1674a`.
- **Done when:** equivalent view commands produce consistent camera movement
  over equal time across rates, including small inputs and mode changes.

### FR-24 — Gunner view and controls

- [ ] **Open — candidate.** Audit gunner control scaling around `bob:139d2`;
  do not assume the flight-control mouse fix covers this path.
- **Done when:** equivalent input produces consistent gunner aiming movement
  across rates, including entering/leaving stations and aim limits.

### FR-25 — Field-based input timing

- [ ] **Open — candidate.** Audit mouse polling and joystick deflection ramp
  (`bob:29bb2`, `29c00`) separately from rendering and PAL/NTSC field rate.
- **Done when:** controlled input sequences establish the intended elapsed-time
  response on PAL and NTSC at varying render rates, with any required fixes and
  regressions for existing mouse gain and counter-wrap handling.

### FR-26 — Audio envelopes and fixed waits

- [ ] **Open — candidate.** Trace VERTB-based sound envelopes and fixed waits;
  distinguish hardware field timing from simulation/rendering dependencies.
- **Done when:** each relevant wait/envelope has a documented clock policy and
  PAL/NTSC plus varying-render-rate checks, with corrected unintended timing
  differences and preserved sound behavior.

### FR-27 — Fuel, engine and resource accounting coverage

- [ ] **Open — coverage gap.** Follow fuel/engine/resource updates and indirect
  callbacks not exhausted by the first audit. Identify clocks, per-update
  increments and state transitions; fix any confirmed dependencies.
- **Done when:** each discovered resource system has mapped update paths and
  equal-time consumption/transition evidence across rates. Assign new stable IDs
  to independent defects before fixing them; do not treat an untraced system as
  verified unaffected. Ammunition and bomb inventory remain FR-07/FR-08 scope.
