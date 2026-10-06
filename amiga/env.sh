#!/usr/bin/env bash
# Source this to put the shared ~/.local Amiga toolchain on PATH.
TC="$HOME/.local"
export PATH="$TC/opt/bin:$TC:$TC/fs-uae:$PATH"
export KICKSTART="${KICKSTART:-$HOME/Documents/RetroPie/BIOS/kick31.rom}"
