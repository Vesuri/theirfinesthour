# Their Finest Hour — Amiga

An enhanced WHDLoad installation of Lucasfilm's 1990 flight simulator,
**Their Finest Hour: The Battle of Britain**, based on Psygore's original install.
Fly British and German aircraft in training missions and the Battle of Britain campaign.

**Version 2.0b (13.10.2026) is a beta.** Real-Amiga play-testing is still in progress.

## What's improved

- Faster, tear-free rendering, with full ground detail on fast Amigas.
- Consistent game speed and controls as the frame rate changes.
- Corrected aiming, bullet hits, bombing, AI and other gameplay timing.
- Adjustable mouse sensitivity and improved gunner controls.
- Improved flight recording and playback, with 128-second recordings.
- Fixed repeating explosion and splash sounds.

## Requirements and installation

- Your own copy of the Amiga game. Versions 1.0, 1.1 and KIXX are supported;
  **Enhanced framerate requires game version 1.1**. Missions Volume 1 is optional.
- WHDLoad 17 or later.
- 512 KB Chip RAM and 896 KB other RAM, plus 256 KB for the Kickstart image.
  Allow extra memory for the host system and PRELOAD.
- A500 Kickstart 1.3 image `kick34005.A500` and its matching
  `kick34005.A500.RTB` in `Devs:Kickstarts`.

Unpack **TheirFinestHour-2.0b.lha**, open **TheirFinestHourHD** and run
**Install-TheirFinestHour**. Choose a destination and icon, then supply the
BOB1 and BOB2 disks or disk images. The installer also offers Missions Volume 1
and copies the manual and key reference. Start the installed game icon.

The installer archive contains no original game data. Game files, Kickstart
images and WHDLoad binaries are not included in this repository.

## Startup options and controls

The WHDLoad startup window offers:

| Option | What it does |
| --- | --- |
| Mission Builder | Start the mission editor (`CUSTOM1=1`) |
| Enhanced framerate | Enable the improvements (`CUSTOM2=1`); checked by default in the supplied icons |
| Mouse sensitivity | Choose 1x, 2x (default), 4x or 8x with Enhanced framerate enabled |

Uncheck **Enhanced framerate** to use the original game mode.
Press **Ctrl+G** during flight to cycle ground detail, or **numeric \*** to quit
through WHDLoad. See the installed **Manual** and **Keys** for flight controls.
New enhanced movie saves require Enhanced framerate in this slave;
original movie files can still be loaded.

## Building

With the shared Amiga toolchain and local source archives configured:

```sh
make dist
```

Build instructions and checks are in [development.md](docs/development.md).
[Open work](docs/open-work.md) records the remaining validation, and
[internals.md](docs/internals.md) describes the patches.

## Credits

Original game by Lucasfilm. Original WHDLoad install by Psygore, KickEmu by
Wepl, and enhancements by Vesuri. Thanks to Philippe Bovier for the original
disks and Mad-Matt for the KIXX version.

This is an unofficial fan project, not affiliated with or endorsed by Lucasfilm.
