# Their Finest Hour (Amiga) — performance study

Profiling the ORIGINAL 1990 Lucasfilm game, run under Psygore's WHDLoad install (slave v1.1,
`data/bob` v1.1, 254 400 bytes, CRC16 `$274F`). No game or slave source: work from cycle-exact
FS-UAE traces and disassembly. The slave is rebuilt from its disassembly (`whdload/`, on the
WHDLoad 20.0 KickEmu sources); any change to the game ships as patches in that slave.

## Rules

- **Never commit game, Kickstart or WHDLoad bytes**, or anything made from them: unpacked data,
  traces, memory dumps, screenshots, input recordings, built slaves. They live in `tmp/`
  (ignored). Addresses in docs are `bob` hunk-0 offsets (the slave's `resload_PatchSeg`
  numbering, `bob:OFFSET`), never absolute addresses.
- Commits: author Vesa Halttunen <vesuri@jormas.com>, unsigned, no hooks, no Co-Authored-By lines.
  One commit per coherent feature.
- Never `pkill fs-uae` or `pkill gdb` (other projects run emulators): `fsuae_common.sh` kills
  only our own pid and gives this directory its own gdb-stub port.
- No performance claim without a measurement from the right instrument (`docs/profiling.md`).
- Instruments (input tapes, RNG pinning, slow drawing) go in the `VERIFY` slave build only.
  Every game change is gated by a `CUSTOMn` option; with it off the original bytes are untouched.

## Reference docs — read before working in the area

| Doc | Read it when |
|---|---|
| `docs/open-work.md` | **First.** Where setup stands, what is known, ordered work items |
| `docs/profiling.md` | Running the game, driving it, tracing it, or quoting any performance number |
| `~/Projects/Test Drive 2/docs/new-game-playbook.md` | The setup procedure this repo follows |
