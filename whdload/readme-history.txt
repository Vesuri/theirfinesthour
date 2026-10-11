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
