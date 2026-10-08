# Open work

The slave is at version **1.2b** (beta): Psygore's v1.1 plus the changes in `internals.md`.
`make dist` builds the release archives (`development.md`).

## Next

1. **Play-testing** with `CUSTOM2`+`3`+`4` (needs a person): a full mission; views other than
   the cockpit (`bob:16620..166b2` divide by T); AI behaviour; the Mission Builder and the v1.0
   and KIXX versions with the new slave; real hardware.
2. **NTSC in play:** the field-rate detection and the arithmetic are checked in the emulator,
   but no flight has run on a 60 Hz machine.
3. **Truncation at large T** (`internals.md`, known limitations): fractional accumulators in
   the flight model's integrators (heading `bob:146aa`, `14546`, `14582`).
4. **Release decisions:** the options are off by default (the icons carry no `CUSTOM` tooltypes);
   drop the "b" once 1–2 are done.
5. **More speed** (optional): `bob:11138`'s tile loop in registers (~3% of the 68020 frame).
6. **Baselines never measured:** the original slave at ground detail 1 on the 68030/50; gameplay
   equivalence of the rebuilt slave with the shipped one.
