"""Adapt the shared WHDLoad 20.0 templates without vendoring WHDLoad files."""
from pathlib import Path
import os
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def template(name):
    base = Path(os.environ.get('WHDLOAD', Path.home() / '.local/share/amiga/WHDLoad-20.0'))
    return (base / 'Install Template/Xxx Install' / name).read_bytes().decode('latin-1')


def readme(original):
    text = template('ReadMe')
    start = text.index(' This install applies to')
    requirements = text.index(' The game requires an installed A500')
    text = text[:start] + ''' This install applies to "Their Finest Hour: The Battle of Britain"
 (c) 1990 Lucasfilm. Supports game versions 1.0, 1.1, KIXX and Missions Volume 1.
 Enhanced framerate requires game version 1.1.

 Requirements:
 -------------
 WHDLoad 17 or later must be installed and accessible via the path.
 The installed game requires 512 KB ChipMem and 768 KB OtherMem, plus
 256 KB OtherMem for the Kickstart image.
 Quit with numeric '*' (PrtSc); change this with the QuitKey tooltype.

 Installation:
 -------------
 Run Install-TheirFinestHour and select a destination and game icon.
 Supply the BOB1 and BOB2 disks; Missions Volume 1 (BobData) is optional.
 Floppy disks and disk images are supported. The installer explains the
 additional software required for disk images when that option is selected.
 The manual and key reference are copied with the game.

''' + text[requirements:]
    start = text.index(' The game requires an installed A600')
    end = text.index(' History:')
    features = (ROOT / 'whdload/readme-features.txt').read_text()
    text = text[:start] + features + '\n\n' + text[end:]
    start = text.index(' version 1.0')
    end = text.index(' Contact:')
    old = original.decode('latin-1')
    history = old[old.index('Version 1.1 ('):old.index('Thanks to Philippe')].rstrip()
    current = (ROOT / 'whdload/readme-history.txt').read_text().rstrip()
    text = text[:start] + current + '\n\n' + history + '''

 Thanks to Philippe Bovier for the original disks and Mad-Matt for the
 KIXX version. Original install and Color/NewIcons by Psygore; KickEmu by Wepl.
 Psygore accepts donations via PayPal at psygore@whdload.de.


''' + text[end:]
    return text.encode('latin-1')


def installer(original):
    text = template('Install')
    old = original.decode('latin-1')
    text = replace_once(text, '(set #sub-dir "")', '(set #sub-dir "data")')
    text = replace_once(text, '(set #extra3-file "Extra3")', '(set #extra3-file "Keys")')
    text = replace_once(text, '(set #prefix @app-name)', '(set #prefix "TheirFinestHour")')
    # Keep the old disk labels, exclusions and optional mission-pack copy verbatim.
    start = old.index('      (set #AD_disk "bob1")')
    end = old.index('\n    )\n\n    (', start)
    disk_copy = old[start:end]
    start = text.index('(procedure P_MakeImages\n')
    end = text.index('\n;----------------------------', start)
    text = text[:start] + '(procedure P_MakeImages\n' + disk_copy + '\n)\n' + text[end:]
    # There is only one installation method: DOS files, for all supported releases.
    start = text.index('(procedure P_SelectVersion\n')
    end = text.index('\n;---------------------------------------------------------------------', start)
    text = text[:start] + '(procedure P_SelectVersion\n  ("")\n)\n' + text[end:]
    for program in ('RawDIC', 'Patcher', 'DIC'):
        text = replace_once(text, f'(set #program "{program}")\n(P_ChkRun)\n', '')
    # The template stores a suffix in #icon before askchoice; use the Normal index.
    text = replace_once(text, '(default #icon)', '(default 0)')
    # Preserve the prepared NewIcon tooltypes; explicitly retain the launch default.
    marker = '  (P_SelectIcon)\n'
    text = replace_once(text, marker, marker + '''  (tooltype
    (dest (tackon #dest #icon_newname))
    (settooltype "CUSTOM2" "1")
  )
''')
    validate_installer(text)
    return text.encode('latin-1')


def validate_installer(text):
    """Structural check only; does not substitute for running Amiga Installer."""
    tokens = re.findall(r';[^\n]*|"(?:\\.|[^"\\])*"|[()]|[^\s();"]+', text)
    depth = 0
    for token in tokens:
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
            assert depth >= 0, 'Unbalanced Installer script'
    assert depth == 0, 'Unbalanced Installer script'
    procedures = re.findall(r'\(procedure\s+(P\w+)', text)
    assert len(procedures) == len(set(procedures))
    calls = set(re.findall(r'\((P\w+)\)', text))
    assert calls <= set(procedures), calls - set(procedures)
    assert '(set #sub-dir "data")' in text
    assert '(set #extra3-file "Keys")' in text
    assert '(settooltype "CUSTOM2" "1")' in text
    assert '(PDI_Eject)\n' in text
