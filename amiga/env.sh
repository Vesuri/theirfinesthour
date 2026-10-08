#!/usr/bin/env bash
# Source this to put the shared ~/.local Amiga toolchain on PATH and name the shared assets.
TC="$HOME/.local"
export PATH="$TC/opt/bin:$TC:$TC/fs-uae:$PATH"
AMIGA_SHARE="$TC/share/amiga"
# Host Kickstart 3.1, and the Kickstart 1.3 image + RTB that KickEmu boots inside WHDLoad.
export KICKSTART="${KICKSTART:-$AMIGA_SHARE/Kickstarts/kick40063.A600}"
export KICK13="${KICK13:-$AMIGA_SHARE/Kickstarts/kick34005.A500}"
export RTB="${RTB:-$AMIGA_SHARE/Kickstarts/kick34005.A500.RTB}"
export WORKBENCH_ADF="${WORKBENCH_ADF:-$AMIGA_SHARE/Workbenchv2.04rev37.67Workbench.adf}"
export WHDLOAD_BINARY="${WHDLOAD_BINARY:-$AMIGA_SHARE/WHDLoad-20.0/C/WHDLoad}"
