#!/usr/bin/env python3
"""Read-only VERIFY tape-10 recording/replay integration checkpoint."""
import argparse
from pathlib import Path
from state_fields import command
from slave_sym import addresses
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('out');p.add_argument('dump');p.add_argument('base',type=lambda s:int(s,0))
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
sym=addresses(Path(a.dump).read_bytes(),a.base,['probe_replay_observed','probe_replay_state','probe_replay_expected','probe_replay_actual'])
result=command(f'''break *{sym['probe_replay_observed']:#x}
continue
printf "replay state %d expected %u actual %u\\n", *(short*){sym['probe_replay_state']:#x}, *(unsigned long*){sym['probe_replay_expected']:#x}, *(unsigned long*){sym['probe_replay_actual']:#x}
delete
''')
(out/'gdb.txt').write_text(result)
assert 'replay state 1 ' in result,result
print('VERIFY live mission: recorded object poses/classes replayed identically; live flight restored')
