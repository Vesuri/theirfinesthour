# WHDLoad 20.0 source baseline

Public-domain KickEmu sources and API headers from the official WHDLoad 20.0
developer archive (https://www.whdload.de). The build takes `kick13.s` (with
`kickfs.s`), `whdload.i` and `whdmacros.i` from the shared WHDLoad 20.0 tree
(`$WHDLOAD`). The small `include/lvo/` aliases adapt the official source's include
names to the host NDK.

The slave follows `Src/slave-examples/kick13.asm` with a version-17 header
(`slv_Version = 17`): it uses none of the version-20 additions (`ws_MemConfig`,
the actual expansion size), so WHDLoad 17 and later run it. KickEmu supplies
`WHDLF_EmulPriv` and handles cache setup and flushes. CACHE is retained for
DMA-safe noncached chip memory and cached fast memory; CACHECHIPDATA is not
appropriate for the game's blitter buffers.

WHDLoad executables and the developer archive are not part of this repository.
This update alone does not establish 68060 compatibility.
