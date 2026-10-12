Version 1.3b (12.10.2026) by Vesuri (beta):
 - Fixed progressive aircraft damage processing across changing frame rates
 - Fixed automatic bomb guidance timing and synchronized the entire bomb salvo
   during altitude-triggered turns, including slow and accelerated updates
 - Fixed bomb-salvo release timing and interpolated release positions across
   frame rates
 - Fixed player gun reload and AI burst cadence across changing frame rates
 - Fixed flak timing jitter and delayed damage across frame rates. Pending
   damage cannot transfer to a replacement aircraft in a reused slot
 - Fixed projectile lifetime and age-based damage across changing frame rates;
   final movement is clipped to two seconds and tested before expiry
 - Fixed world-clock drift across frame rates, including time acceleration
   and daylight transitions (Enhanced framerate)
 - Fixed frame-rate-dependent effect animation, fragment emission and cleanup.
   Effects now advance at a fixed eight updates per simulation second, keeping
   intermediate state transitions on slow frames (Enhanced framerate)
 - Fixed the aircraft-group processing timer overflowing above 51 updates/s.
   It now runs every five simulation seconds across changing frame rates,
   preserving native group eligibility and placement (Enhanced framerate)
 - Fixed frame-rate-dependent debris and wreckage trajectories, drag and
   fragment lifetimes. Movement uses fixed 64 Hz steps with fractional gravity;
   reused slots reset their clocks and movement fractions (Enhanced framerate)
 - Fixed frame-rate-dependent bomb landing positions. Bomb movement now runs
   in 64 fixed steps per simulation second, retaining the native gravity,
   drag, target checks and damage. Unused partial time carries per bomb
 - Bomb slot reuse resets its movement fractions and clock. Catch-up stops
   at ground contact so a bomb cannot slide forward before its hit is tested
 - Part of Enhanced framerate (CUSTOM2=1); the original mode is unchanged

 - Fixed projectile hits missed when a crossing was split across frames.
   Tests the swept shot path against the aircraft instead of requiring
   coordinate crossings to occur in the same frame; damage is unchanged
 - Mouse sensitivity defaults to 2x. Select 1x, 2x, 4x or 8x in the WHDLoad
   startup options (CUSTOM3=1: 1x, unset/0: 2x, 2: 4x, 3: 8x)
 - Small mouse movements are no longer discarded by a frame-dependent
   flight-control dead zone; keyboard and joystick sensitivity are unchanged
 - Enhanced framerate is now opt-in: enable it in the WHDLoad startup
   options (CUSTOM2=1). It includes the bomb, mouse and projectile fixes above;
   with the option off/unset, the game runs without these enhancements
 - Packaged game icons set CUSTOM2=1, enabling Enhanced framerate by default
   when launched from Workbench; uncheck it to disable the enhancements

Version 1.2b (08.10.2026) by Vesuri (beta):
 - Rebuilt from the 1.1 slave on the WHDLoad 20.0 KickEmu sources; runs with
   WHDLoad 17 or later
 - The caches are no longer switched off: WHDLoad's defaults and the user's
   options (NoCache, Cache, DCache, ...) apply
 - Fixed one-shot sounds (explosions, splashes) replaying their sample until
   their envelope ended (an original bug)
 - 768 KB OtherMem
 - Improved frame rate for version 1.1 of the game, on by default (CUSTOM2=1
   runs the game as before):
     faster rendering: render buffers and game data in fast memory, a faster
     chunky-to-planar conversion, faster 3D maths (with 68020+ code where it
     helps), and full ground detail on fast machines
     frame pacing: each frame is shown once, without tearing
     real-time simulation: the game runs at the same speed at any frame rate,
     PAL or NTSC (the original ran an A500 at 1.9x real time, a 68030/50 at
     0.55x), and neither mouse response nor the guns' rate of fire depends on it
   Measured: 68030/50 MHz 50 fps at full ground detail (15.6 fps at the reduced
   detail it chose before), A1200 with fast memory 23.5 fps at full ground
   detail (18.8 fps at reduced detail), A1200 without fast memory 12.5 fps
   (10.6), A500 unchanged at 7.6 fps. Ctrl+G cycles the ground detail in flight
