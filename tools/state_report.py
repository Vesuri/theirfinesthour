#!/usr/bin/env python3
"""Report per-field state snapshots (raw big-endian game values, never screenshots).
  state_report.py OUT/state [--changes] [--fields 0,5,99,299]
Snapshot n is at VBL entry n; initial.bin is taken at the anchor.
"""
import argparse, collections, json, struct
from pathlib import Path
VARIABLES = {
    'distance': (-17238, 4), 'speed': (-13282, 4), 'clock': (-10146, 4),
    'opponent_distance': (-13356, 4), 'opponent_speed': (-13348, 4),
    'render_distance': (-13394, 4), 'traffic_forward': (-13470, 4),
    'traffic_oncoming': (-13466, 4), 'vbl': (-17216, 4),
    'deadline': (-17212, 4), 'rpm': (-13188, 4), 'fuel': (-10822, 2),
    'animation_1': (-3008, 2), 'animation_2': (-3006, 2),
    'engine_period': (-2792, 2), 'needle_speed': (-24648, 2), 'needle_rpm': (-24652, 2),
    'background_1': (-3120, 4), 'background_2': (-3116, 4),
    'background_3': (-3112, 4), 'background_4': (-3108, 4),
    'lane': (-13386,4), 'heading': (-13390,2), 'yaw': (-9862,2),
    'heat': (-24718,2), 'gear': (-13036,2), 'clutch': (-13038,2),
    'police': (-7642,2), 'police_wait': (-12980,2), 'crash': (-14916,2),
    'lives': (-17228,2), 'crash_count': (-10872,2), 'damage_count': (-10870,2),
    'penalties': (-10864,4), 'engine_damage': (-12938,2), 'running': (-7670,2),
    'gear_envelope': (-24720,2), 'opponent_lane': (-13352,4),
    'opponent_clock': (-10844,4), 'player_sum': (-7674,4), 'opponent_sum': (-10836,4),
    'road_length': (-17240, 2), 'stage': (-10866, 2), 'rng': (-18632, 2),
}
def value(b, offset, size):
    return int.from_bytes(b[0x7ffe+offset:0x7ffe+offset+size], 'big')
def main():
    p=argparse.ArgumentParser(); p.add_argument('path'); p.add_argument('--changes',action='store_true')
    p.add_argument('--fields',default='0,5,11,71,77,99,149,199,249,299');a=p.parse_args()
    root=Path(a.path); m=json.loads((root/'metadata.json').read_text())
    files=sorted(root.glob('[0-9][0-9][0-9][0-9].bin')); data=[f.read_bytes() for f in files]
    initial=(root/'initial.bin').read_bytes()
    print('initial:',{n:value(initial,*v) for n,v in VARIABLES.items()})
    print('field,'+','.join(VARIABLES))
    for f in map(int,a.fields.split(',')):
        if f<len(data):print(str(f)+','+','.join(str(value(data[f],*v)) for v in VARIABLES.values()))
    print('update fields (observed changes, excluding same-value stores):')
    for n,v in VARIABLES.items():
        changes=[i for i in range(1,len(data)) if value(data[i],*v)!=value(data[i-1],*v)]
        periods=collections.Counter(b-a for a,b in zip(changes,changes[1:]))
        print(n, 'count',len(changes),'first',changes[:25],'periods',dict(periods))
    if a.changes:
        for off in range(0,len(initial),2):
            changes=[i for i in range(1,len(data)) if data[i][off:off+2]!=data[i-1][off:off+2]]
            if changes:
                periods=collections.Counter(b-a for a,b in zip(changes,changes[1:]))
                print(f'word {off-0x7ffe:+d}: {len(changes)} changes; first={changes[:15]}; periods={dict(periods)}')
if __name__=='__main__':main()
