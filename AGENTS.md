# Their Finest Hour (Amiga) — performance study

Profiling the ORIGINAL 1990 Lucasfilm game, run under Psygore's WHDLoad install (slave v1.1,
`data/bob` v1.1, 254 400 bytes, CRC16 `$274F`). No game or slave source: work from cycle-exact
FS-UAE traces and disassembly. The slave is rebuilt from its disassembly (`whdload/`, on the
WHDLoad 20.0 KickEmu sources); any change to the game ships as patches in that slave.

## Shared environment and knowledge

The shared environment comes from AmigaXDev, the repository next to this one: `make setup`
there installs `~/.local` and `~/.local/share/amiga`, and `amiga/env.sh` sources
`~/.local/share/amiga/env.sh`. The method and the lessons the projects share are in AmigaXDev:

| AmigaXDev doc | Holds |
|---|---|
| `docs/playbooks/new-game-playbook.md` | the method this repo follows |
| `docs/playbooks/new-game-playbook-hardware.md` | black screens and dumps on real Amigas, CPU caches |
| `docs/playbooks/whdload-mmu.md` | MMU compatibility and crash diagnosis |
| `docs/playbooks/fixed-time-simulation.md` | game time, fixed ticks, input per tick, raising the update rate |
| `docs/playbooks/simulation-and-presentation.md` | uncapped drawing, interpolation, smaller timesteps |
| `docs/environment.md` | the shared variables |
| `docs/reference/headless-fsuae.md` | the shared launcher, FS-UAE builds, the gdb stub |
| `docs/reference/measurement-method.md` | instruments, A/B discipline, pricing a change |
| `docs/reference/m68k-optimisation.md` | 68000/68020 cost model and code rules |
| `docs/reference/amiga-hardware.md` | Chip bus, FMODE, copper, blitter, caches |

Generic lessons go into those docs (edit them in AmigaXDev); this repository keeps what is
specific to this game.


## Rules

- **Never commit game, Kickstart or WHDLoad bytes**, or anything made from them: unpacked data,
  traces, memory dumps, screenshots, input recordings, built slaves. They live in `tmp/`
  (ignored). Addresses in docs are `bob` hunk-0 offsets (the slave's `resload_PatchSeg`
  numbering, `bob:OFFSET`), never absolute addresses.
- Commits: author Vesa Halttunen <vesuri@jormas.com>, unsigned, no hooks, no Co-Authored-By lines.
  One commit per coherent feature.
- Never `pkill fs-uae` or `pkill gdb` (other projects run emulators): `fsuae_common.sh` kills
  only our own pid and gives this directory its own gdb-stub port.
- No performance claim without a measurement from the right instrument (`docs/development.md`).
- Instruments (input tapes, RNG pinning, slow drawing) go in the `VERIFY` slave build only.
  Every game change is part of the improved frame rate (on by default); `CUSTOM2=1` (the original
  game) switches all of it off and leaves the original bytes untouched.

## Reference docs — read before working in the area

| Doc | Read it when |
|---|---|
| `docs/open-work.md` | **First.** Where the work stands and what is next |
| `docs/development.md` | Building, running, driving, tracing or checking the game, or quoting any performance number |
| `docs/internals.md` | Working on the game's code or the slave's patches |

Local paths (home directories, other projects' locations) do not belong in this repository;
shared files come from `~/.local/share/amiga` through the variables in `docs/development.md`.
