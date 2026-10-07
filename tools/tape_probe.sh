#!/usr/bin/env bash
# Boot the verify slave with input tape N and take screenshots labelled with the tape field.
#   tools/tape_probe.sh N OUTDIR [SHOTS] [WAIT]    (A500-equivalent machine, JOY0=none)
# Leaves the server running (tools/tfh.py quit to stop) so the caller can continue.
set -euo pipefail
cd "$(dirname "$0")/.."
N=$1 OUT=$2 SHOTS=${3:-10} WAIT=${4:-2}
mkdir -p "$OUT"
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" EXTRA_ARGS="${EXTRA_ARGS---slow_memory=1536}"
export JOY0=none SLAVE="${SLAVE:-$PWD/tmp/slaves/verify.slave}" WHD_ARGS="CUSTOM5=$N ${WHD_ARGS:-}"
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi
tfh() { python3 tools/tfh.py "$@"; }
[ -S amiga/.run/tfh.sock ] && { tfh quit > /dev/null 2>&1 || true; sleep 1; }
WARP=1 python3 tools/tfh.py serve > amiga/.run/serve.log 2>&1 &
for _ in $(seq 1 120); do grep -q serving amiga/.run/serve.log 2>/dev/null && break; sleep 1; done
VBL=
for i in $(seq 1 "$SHOTS"); do
  tfh wait "$WAIT" > /dev/null
  tfh gdb "dump binary memory /tmp/tfh-probe.bin $BASE $(printf '%#x' $((BASE + SIZE)))" > /dev/null
  [ -n "$VBL" ] || VBL=$(python3 tools/slave_sym.py /tmp/tfh-probe.bin "$BASE" tape_vbl | cut -d' ' -f2)
  field=$(tfh gdb "x/1uh $VBL" | tail -1 | awk '{print $2}')
  tfh shot "$PWD/$OUT/$(printf '%02d' "$i")-f$field.png" > /dev/null
  echo "shot $i at tape field $field"
done
mv /tmp/tfh-probe.bin "$OUT/code.bin"
