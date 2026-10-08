#!/usr/bin/env python3
"""Rebuild Psygore's two v1.1 archives with the new slave -> dist/ (LH5, level-1 headers).

    python3 tools/package_release.py        (make dist)

Inputs, kept local in tmp/ (never committed): the installer tmp/TheirFinestHour.lha and the
preinstalled archive tmp/TheirFinestHour_v1.1_0037.lha. Outputs:

  dist/TheirFinestHour-<ver>.lha            the same members as tmp/TheirFinestHour.lha
  dist/TheirFinestHour_v<ver>_0037.lha      the same members as the 0037 archive

Only two members change: the slave (a fresh normal build of whdload/) and the ReadMe
(Psygore's text with whdload/readme-history.txt added above his history and the
requirements updated). Everything else is copied byte for byte; the archives are
re-extracted and checked member by member against their sources. The preinstalled archive
holds the game itself: dist/ is ignored by git. LHA names LHa for UNIX (Lhasa, the usual
`lha`, cannot create archives).
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LHA = os.environ.get('LHA', os.path.expanduser('~/.local/share/amiga/lha-compressor/src/lha'))
# source archive, top directory, slave member name, output name pattern
ARCHIVES = [(ROOT / 'tmp/TheirFinestHour.lha', 'TheirFinestHourHD', 'TheirFinestHour.slave',
             'TheirFinestHour-{v}.lha'),
            (ROOT / 'tmp/TheirFinestHour_v1.1_0037.lha', 'TheirFinestHour', 'TheirFinestHour.Slave',
             'TheirFinestHour_v{v}_0037.lha')]
REQUIREMENTS = [(b' - WHDLoad 16+\n', b' - WHDLoad 17+\n'),
                (b'512 KB ChipMem and 512 KB OtherMem', b'512 KB ChipMem and 768 KB OtherMem')]


def members(archive):
    return subprocess.run(['lsar', archive], capture_output=True, text=True,
                          check=True).stdout.splitlines()[1:]


def extract(archive, into):
    subprocess.run(['lha', f'xqw={into}', str(archive)], check=True)


def readme(original):
    entry = (ROOT / 'whdload/readme-history.txt').read_bytes()
    key = b'Version 1.1 (16.11.2008) by Psygore:\n'
    assert original.count(key) == 1 and entry not in original
    text = original.replace(key, entry + b'\n' + key)
    for old, new in REQUIREMENTS:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text


def archive(stage, names, out, source, changed):
    out.unlink(missing_ok=True)
    subprocess.run([LHA, 'a1o5q2', str(out), *names], cwd=stage, check=True)
    test = subprocess.run([LHA, 't', str(out)], capture_output=True, text=True)
    assert test.returncode == 0, test.stdout + test.stderr
    assert sorted(members(out)) == sorted(names), out  # LHa for UNIX sorts the members
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as new, tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as old:
        extract(out, new)
        extract(source, old)
        for name in names:
            a, b = (Path(new) / name).read_bytes(), (Path(old) / name).read_bytes()
            assert a == (stage / name).read_bytes(), name
            assert (a != b) == (name in changed), name
    print(f'{out.relative_to(ROOT)}: {len(names)} files, {out.stat().st_size} bytes; '
          f'changed: {", ".join(sorted(changed))}')


def main():
    subprocess.run(['make', '-C', str(ROOT / 'whdload')], check=True, capture_output=True)
    slave = (ROOT / 'whdload/TheirFinestHour.slave').read_bytes()
    assert b'C5:' not in slave, 'VERIFY build'
    version = re.search(rb'\$VER: slave ([0-9.a-z]+)', slave).group(1).decode()
    assert f'Version {version} '.encode() in (ROOT / 'whdload/readme-history.txt').read_bytes()
    (ROOT / 'dist').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
        for source, top, slave_name, pattern in ARCHIVES:
            stage = Path(tmp) / top
            extract(source, stage)
            names = members(source)
            changed = {f'{top}/{slave_name}', f'{top}/ReadMe'}
            assert changed <= set(names), source
            (stage / top / slave_name).write_bytes(slave)
            (stage / top / 'ReadMe').write_bytes(readme((stage / top / 'ReadMe').read_bytes()))
            archive(stage, names, ROOT / 'dist' / pattern.format(v=version), source, changed)


if __name__ == '__main__':
    main()
