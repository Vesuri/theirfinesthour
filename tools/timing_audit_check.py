#!/usr/bin/env python3
"""Check implemented elapsed-time fixes through native game routines.

Same DUMP BASE SLAVE LISTING inputs as input_combat_check.py. Runs controlled
native routines, not rendering or a full mission. Each implemented work item
adds its regression here.
"""
import argparse
from input_combat_check import Checks


def audit(args):
    from debris_check import DebrisChecks
    DebrisChecks(args).run()  # FR-01 is now an equality regression.
    from group_timer_check import GroupChecks
    GroupChecks(args).run()  # FR-02 elapsed-time and native placement checks.
    from effect_check import EffectChecks
    EffectChecks(args).run()  # FR-03 native effect-transition equivalence.
    a = Checks(args)
    c = a.c
    from world_clock_check import ClockChecks
    ClockChecks(args).run()  # FR-04 elapsed-time clock and native daylight.

    from projectile_life_check import LifeChecks
    LifeChecks(args).run()  # FR-05 lifetime, final segment and damage age.
    from flak_check import FlakChecks
    FlakChecks(args).run()  # FR-06 native flak launch and delivery.
    from gun_timer_check import GunChecks
    GunChecks(args).run()  # FR-07 player and AI gun cadence.
    from salvo_check import SalvoChecks
    SalvoChecks(args).run()  # FR-08 native salvo timing and spacing.
    from guidance_check import GuidanceChecks
    GuidanceChecks(args).run()  # FR-09 native guidance and synchronized bomb pool.
    from air_damage_check import AirDamageChecks
    AirDamageChecks(args).run()  # FR-10 progressive aircraft damage.
    from surface_damage_check import SurfaceDamageChecks
    SurfaceDamageChecks(args).run()  # FR-11 ship progression and event-driven ground damage.
    from ai_decision_check import DecisionChecks
    DecisionChecks(args).run()  # FR-12 aircraft and player gunner decisions.
    from aim_check import AimChecks
    AimChecks(args).run()  # FR-13 native lead normalization and projectile launch.
    from script_timer_check import ScriptChecks
    ScriptChecks(args).run()  # FR-14 surface service, script waits and taxi action.
    from attitude_check import AttitudeChecks
    AttitudeChecks(args).run()  # FR-15 continuous attitude and pole crossings.
    from recovery_check import RecoveryChecks
    RecoveryChecks(args).run()  # FR-16 player attitude recovery.
    from ground_steering_check import SteeringChecks
    SteeringChecks(args).run()  # FR-17 player ground steering.
    from drift_check import DriftChecks
    DriftChecks(args).run()  # FR-18 formation/descent movement.
    from contact_check import ContactChecks
    ContactChecks(args).run()  # FR-19 aircraft ground-contact classification.
    from mission_wait_check import WaitChecks
    WaitChecks(args).run()  # FR-20 native mission and flight-transition waits.
    from message_check import MessageChecks
    MessageChecks(args).run()  # FR-21 message visibility and replacements.


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump')
    p.add_argument('base', type=lambda s: int(s, 0))
    p.add_argument('slave')
    p.add_argument('listing')
    p.add_argument('--cpu', choices=['68000', '68040'], default='68000')
    audit(p.parse_args())
