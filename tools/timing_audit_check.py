#!/usr/bin/env python3
"""Check fixed debris/group/effect timing and reproduce the remaining timing defects.

Same DUMP BASE SLAVE LISTING inputs as input_combat_check.py. Runs controlled
native routines, not rendering or a full mission. FR-01 through FR-04 assertions cover fixed behavior;
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

    # A nominal two-second bullet lifetime created at T=8, then T=50.
    a.reset()
    c.write(c.a4 + 13394, bytes(152))
    slot = 52
    c.set(13394 + slot, 33, 'B')
    c.set(13562 + slot, 7, 'B')
    c.set(20798 + slot*2, 16)
    c.set(19694 + slot*2, 100)
    c.set(18466 + slot*2, 16384)
    c.set(11698, 50)
    c.set(11700, 50)
    for _ in range(15):
        c.run(c.bob + 0x154b2)
    assert c.get(13394 + slot, 'B') != 0
    c.run(c.bob + 0x154b2)
    assert c.get(13394 + slot, 'B') == 0
    print('T=8 lifetime consumed at T=50: bullet expires after 16/50 = 0.32s')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump')
    p.add_argument('base', type=lambda s: int(s, 0))
    p.add_argument('slave')
    p.add_argument('listing')
    p.add_argument('--cpu', choices=['68000', '68040'], default='68000')
    audit(p.parse_args())
