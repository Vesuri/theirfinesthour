# Resource and callback timing audit (FR-27)

Unreleased 1.3b, original `bob` v1.1. Addresses below are hunk-0 offsets.
This follows the world-update call graph and the writers/readers of discovered
resource fields. It complements the movement/impact inventory in
[framerate-audit.md](framerate-audit.md) and the complete AI dispatch inventory
in [ai-script-timing.md](ai-script-timing.md).

## Resources

| Resource or derived quantity | Writers/readers and clock | Result |
|---|---|---|
| Fuel, native Q16 long per aircraft | Construction `bob:b6dc`–`b8c4` chooses capacity, adjusts for pre-flight travel, then shifts to Q16. Recurring burn `bob:201c4`–`202b8`; display `bob:1a5a4`; AI low-fuel eligibility `bob:23dfc`. | Burn rate depends on effective engine power and is divided by simulation T. Lost division remainder was independently tracked and fixed as **FR-28**. Construction/travel adjustment is a one-time event, not an update counter. |
| Engine health, two word arrays | Constructor `bob:b68e`, `b69e`; aircraft setup `bob:bb36`, `bb4e`; damage branches `bob:1e940`–`1e9d2`. | Health changes on damage events, saturating at zero. Native event deductions agree across T; damage opportunity/progression is covered by FR-05/06/10/13, not a new per-frame wear clock. |
| Effective engine power | `bob:20126`–`201c4`: throttle × health, selecting one engine or averaging two according to aircraft type. Zero-fuel cutoff `bob:2028c`–`202b8`. | Recomputed from current state, not accumulated per update. Controlled native checks cover healthy/damaged/dead engines, aircraft selectors, throttle curve and cutoff. |
| Throttle command | Player key handlers `bob:13da0`, `13dfe`; AI script setters across `bob:24c36`–`26db2`. | Player changes are command events; keyboard field repeat is FR-25 and remembered-key/UI waits are FR-26. AI callbacks are in the FR-14 dispatch inventory and run behind FR-12/14 scheduling. A throttle change per decision is not also scaled as a continuous burn rate. |
| Speed and fractional acceleration | `bob:212ee`, `21394`, `2140c`, called by aircraft physics. | Native code already carries its division fraction. Equal-time acceleration/deceleration checks pass within one speed unit at steady/changing T. No second fraction patch is added. This does not make the entire nonlinear flight model a fixed-step integrator. |
| Ammunition, gun reload and bursts | `bob:1c5dc`, `1c876`, `1cc30`; gun inventories updated on successful fire. | FR-07 verifies equal-time shots and resource deductions, including full pools and empty inventory. |
| Bomb inventory and salvos | `bob:1c690`, `1d4e0`, bomb constructor/release path. | FR-08 verifies release timing, inventory and spacing. FR-09 synchronizes guidance; bomb motion/contact uses its existing fixed-step tests. |
| Aircraft/ship damage and destruction state | `bob:1ea46`, `1f4f6`; direct damage paths and impact dispatch. | FR-10/11 fix recurring progression. FR-19 classifies aircraft contact at the crossing. Event damage is not multiplied by rendering rate. |
| Group availability and mission conditions | `bob:bf8e`, `c2d0` plus eleven mission-condition branches. | FR-02/20 cover elapsed scheduling, eligibility, replacement and mission-state transitions. This is not evidence for unexecuted campaign/debrief UI paths. |
| Recording capacity and replay state | `bob:13bf8`, native save/restore companions. | FR-22 supplies 128 control seconds, timestep/RNG history and private-state coverage; FR-28 adds fuel fractions to that manifest. |
| Engine/damage instruments | `bob:18dce`–`18e40`, `19326`–`1946c`, and engine audio `bob:3066`. | Read/derive values from engine health/power and throttle. No additional independent heat, oil or wear accumulator was identified in these inspected paths. Audio envelopes have their own display clock (FR-26). |

## World-update callback closure

Every direct or A4 jump-table call from `bob:12eaa` is accounted for below.
Callbacks inside the aircraft/surface AI script dispatch are separately inventoried
by FR-14; movement and impact tables by FR-01/09/19. This is a finite inspected
scope, not a claim that every arbitrary state in the binary was executed.

| Target | Responsibility and coverage |
|---|---|
| `bob:13c6e` | Player controls, FR-16/17/24; command accounting above |
| `bob:14e5a` | World/daylight clock, FR-04 |
| `bob:22090` | Aircraft AI, FR-12/13/14 |
| `bob:bf8e` | Aircraft groups, FR-02 |
| `bob:22eaa` | Player/automatic gunner decisions, FR-12/13 |
| `bob:218a2` | Surface AI, FR-14 |
| `bob:200c0` | Aircraft physics, attitude/recovery, engine power and fuel; FR-15/18/28 |
| `bob:3066` | Engine audio dispatch; envelope service occurs separately in VERTB |
| `bob:1fee4` | Bomb guidance, FR-09 |
| `bob:154b2` | Object movement and class dispatch, FR-01/05/09/18 |
| `bob:1c5dc` | Guns and salvos, FR-07/08 |
| `bob:176a2` | Effects, FR-03 |
| `bob:1d948` | Impact dispatch, existing bullets/bombs and FR-19 |
| `bob:1fdb8` | Delayed flak outcome, FR-06 |
| `bob:1f4f6` | Surface damage, FR-11 |
| `bob:1ea46` | Aircraft damage progression, FR-10 |
| `bob:c2d0` | Mission conditions, FR-20 |

## Evidence and limits

`tools/resource_check.py` runs native fractional speed helpers, event-driven
engine-health deductions and derived-power calculations on 68000 and 68040.
`tools/fuel_check.py` additionally covers all sixteen fuel slots, fourteen type
selectors, the native engine/burn curve, zero-fuel cutoff and the unlimited-fuel
player gate. Earlier work-item regressions provide the weapon, damage, AI and
mission evidence named above. The aggregate audit includes both new checks. The complete FR-01 through FR-28
audit passes on both 68000 and 68040 with the final normal slave.

Fuel was the newly confirmed independent defect and received FR-28 before its
patch. No other inspected resource path justified an additional timing patch.
Long hardware endurance runs, audible hardware checks and exhaustive campaign
play-throughs remain outside these CPU fixtures. Complete nonlinear trajectories
can still differ when the surrounding flight model takes different timesteps;
resource accounting tests must not be presented as proof otherwise.
