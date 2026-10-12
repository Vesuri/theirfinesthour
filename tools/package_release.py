#!/usr/bin/env python3
"""Rebuild Psygore's two v1.1 archives with the new slave -> dist/ (LH5, level-1 headers).

    python3 tools/package_release.py        (make dist)

Inputs, kept local in tmp/ (never committed): the installer tmp/TheirFinestHour.lha and the
preinstalled archive tmp/TheirFinestHour_v1.1_0037.lha. Outputs:

  dist/TheirFinestHour-<ver>.lha            the same members as tmp/TheirFinestHour.lha
  dist/TheirFinestHour_v<ver>_0037.lha      the same members as the 0037 archive

Changed members are the game launch icons (CUSTOM2=1), the freshly built slave,
the template-based ReadMe, and (in the installer archive) Install-TheirFinestHour.
Everything else is copied byte for byte; the archives are
re-extracted and checked member by member against their sources. The preinstalled archive
holds the game itself: dist/ is ignored by git. LHA names LHa for UNIX (Lhasa, the usual
`lha`, cannot create archives).
"""
from pathlib import Path
import os
import re
import subprocess
import struct
import tempfile

from install_package import readme, installer

ROOT = Path(__file__).resolve().parents[1]
LHA = os.environ.get('LHA', os.path.expanduser('~/.local/share/amiga/lha-compressor/src/lha'))
# source archive, top directory, slave member name, output name pattern
ARCHIVES = [(ROOT / 'tmp/TheirFinestHour.lha', 'TheirFinestHourHD', 'TheirFinestHour.slave',
             'TheirFinestHour-{v}.lha'),
            (ROOT / 'tmp/TheirFinestHour_v1.1_0037.lha', 'TheirFinestHour', 'TheirFinestHour.Slave',
             'TheirFinestHour_v{v}_0037.lha')]


def members(archive):
    return subprocess.run(['lsar', archive], capture_output=True, text=True,
                          check=True).stdout.splitlines()[1:]


def extract(archive, into):
    subprocess.run(['lha', f'xqw={into}', str(archive)], check=True)


def enhanced_icon(original):
    """Add CUSTOM2=1 to these source archives' classic/NewIcon/ColorIcon launchers.

    Locate their length-prefixed WHDLoad default tool, then validate the whole
    tooltype array. Preserve image data, padding and trailing ColorIcon chunks.
    The stored array size includes the terminating null pointer.
    """
    marker = b'\x00\x00\x00\x08WHDLoad\x00'
    assert original[:2] == b'\xe3\x10' and original.count(marker) == 1
    start = original.index(marker) + len(marker)
    size = struct.unpack_from('>I', original, start)[0]
    assert size >= 4 and size % 4 == 0
    cursor = start + 4
    entries = []
    for _ in range(size // 4 - 1):
        length = struct.unpack_from('>I', original, cursor)[0]
        cursor += 4
        value = original[cursor:cursor + length]
        assert length and len(value) == length and value.endswith(b'\0')
        entries.append(value.rstrip(b'\0').upper())
        cursor += length
    assert b'SLAVE=THEIRFINESTHOUR.SLAVE' in entries
    assert not any(value.lstrip(b'(').startswith(b'CUSTOM2=') for value in entries)
    entry = b'CUSTOM2=1\0'
    addition = struct.pack('>I', len(entry)) + entry
    updated = (original[:start] + struct.pack('>I', size + 4) + addition
               + original[start + 4:])
    # Reversing the insertion must reproduce every original byte, including artwork.
    assert (updated[:start] + struct.pack('>I', size)
            + updated[start + 4 + len(addition):]) == original
    return updated


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
            install_name = f'{top}/Install-TheirFinestHour'
            if install_name in names:
                install = stage / install_name
                install.write_bytes(installer(install.read_bytes()))
                changed.add(install_name)
            icon_suffixes = ('.info', '.inf', '.newicon', '.colicon', '.colicon2',
                             '.colbox', '.colbox2')
            icons = [name for name in names
                     if name.startswith(f'{top}/TheirFinestHour.')
                     and name.endswith(icon_suffixes)]
            assert len(icons) == (6 if top == 'TheirFinestHourHD' else 1), icons
            for name in icons:
                icon = stage / name
                icon.write_bytes(enhanced_icon(icon.read_bytes()))
                changed.add(name)
            archive(stage, names, ROOT / 'dist' / pattern.format(v=version), source, changed)


if __name__ == '__main__':
    main()
