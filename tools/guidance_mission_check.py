#!/usr/bin/env python3
"""Read-only VERIFY tape-9 guided-bomb mission integration checkpoint."""
import argparse
from pathlib import Path
from state_fields import command
from slave_sym import addresses

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('out');p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
sym=addresses(Path(a.dump).read_bytes(),a.base,['probe_guidance_failed','probe_guidance_observed',
    'probe_guidance_slot','probe_guidance_state','probe_guidance_altitude'])
# All stimulus is in tape 9. The Barto stub drops memory/register writes.
result=command(f'''break *{sym['probe_guidance_failed']:#x}
break *{sym['probe_guidance_observed']:#x}
continue
printf "fixture state %d slot %d transition altitude %d\\n", *(short*){sym['probe_guidance_state']:#x}, *(short*){sym['probe_guidance_slot']:#x}, *(long*){sym['probe_guidance_altitude']:#x}
set $tfh_bomb = *(unsigned short*){sym['probe_guidance_slot']:#x}
printf "impact altitude %d mode %d\\n", *(long*)($a4+15506+$tfh_bomb*4), *(unsigned char*)($a4+20766+$tfh_bomb-20)
delete
''')
(out/'gdb.txt').write_text(result)
assert 'fixture state 3' in result,result
assert 'impact altitude 0 mode 3' in result,result
print('VERIFY live mission: native guided bomb transitioned and reached ground-impact dispatch')
