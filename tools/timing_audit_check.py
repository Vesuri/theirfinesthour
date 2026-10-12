#!/usr/bin/env python3
"""Check fixed debris/group/effect timing and reproduce the remaining timing defects.

Same DUMP BASE SLAVE LISTING inputs as input_combat_check.py. Runs controlled
native routines, not rendering or a full mission. FR-01 through FR-05 assertions cover fixed behavior;
the other assertions describe current unfixed behavior and must be revised when those defects are addressed.
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


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump')
    p.add_argument('base', type=lambda s: int(s, 0))
    p.add_argument('slave')
    p.add_argument('listing')
    p.add_argument('--cpu', choices=['68000', '68040'], default='68000')
    audit(p.parse_args())
