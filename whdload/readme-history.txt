Version 1.2b (08.10.2026) by Vesuri (beta):
 - Rebuilt from the 1.1 slave on the WHDLoad 20.0 KickEmu sources; runs with
   WHDLoad 17 or later
 - The caches are no longer switched off: WHDLoad's defaults and the user's
   options (NoCache, Cache, DCache, ...) apply
 - Fixed one-shot sounds (explosions, splashes) replaying their sample until
   their envelope ended (an original bug)
 - 768 KB OtherMem
 - New options for version 1.1 of the game; with them off it runs as before:
   CUSTOM2=1 faster rendering: render buffers and game data in fast memory,
     a faster chunky-to-planar conversion, faster 3D maths (with 68020+ code
     where it helps), and full ground detail on fast machines
   CUSTOM3=1 frame pacing: each frame is shown once, without tearing
   CUSTOM4=1 real-time simulation: the game runs at the same speed at any
     frame rate, PAL or NTSC, and mouse response no longer depends on it;
     speeds, rolls and turns keep their fractions at high frame rates
   Measured with all three: 68030/50 MHz 50 fps at full ground detail (15.6
   fps at the reduced detail it chose before), A1200 with fast memory 23.5 fps
   at full ground detail. Ctrl+G cycles the ground detail in flight
