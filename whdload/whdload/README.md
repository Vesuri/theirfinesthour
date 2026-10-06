# WHDLoad 20.0 source baseline

Public-domain KickEmu sources and API headers from the official WHDLoad 20.0
developer archive, downloaded 2026-10-06:
https://www.whdload.de/whdload/WHDLoad_dev.lha

Archive SHA-256: f177636d615345fddeeec2df7b6b588d1f8d154925e2e1af12d68d31f894c0ce

`kick13.s`, `kickfs.s`, `segtracker.s`, `kick.readme`, `include/whdload.i` and
`include/whdmacros.i` are copied verbatim. The small `include/lvo/` aliases adapt
the official source's include names to the host NDK. The API headers are found
before any shared developer installation, making builds independent of its age.

The slave follows `Src/slave-examples/kick13.asm`: the version-20 header includes
`ws_MemConfig`, disabled by setting `slv_MemConfig = slv_base`; KickEmu supplies
`WHDLF_EmulPriv`, obtains the actual expansion size and handles cache setup and
flushes. CACHE is retained for DMA-safe noncached chip memory and cached fast
memory; CACHECHIPDATA is not appropriate for the game's blitter buffers.

WHDLoad executables, archive and extracted developer-package binaries remain
local in ignored tmp/. This update alone does not establish 68060 compatibility.
