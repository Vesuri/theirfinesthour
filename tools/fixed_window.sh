#!/usr/bin/env bash
# Benchmark window: trace FIELDS PAL fields from race-clock initialisation in duel v1.
# tools/fixed_window.sh OUTDIR [SLAVE]
# Build `make -C whdload verify`, use SLAVE=$PWD/whdload/TestDrive2.slave and
# WHD_ARGS=CUSTOM3=1 for the reproducibility study. ANCHOR overrides the hunk offset
# for diagnostic windows only. The old span anchor (0x789c) was already 7-8 s into a race.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=$1; mkdir -p "$OUT"; FIELDS=${FIELDS:-100}
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" EXTRA_ARGS="${EXTRA_ARGS---slow_memory=1536}"
# Retain exactly the slave used by this capture; later builds must not change
# region sizes or hook addresses when analysing a saved trace.
INPUT_SLAVE=${2:-tmp/game/TestDrive2/TestDrive2.slave}
if [ "$INPUT_SLAVE" != "$PWD/$OUT/slave.slave" ]; then
  cp "$INPUT_SLAVE" "$OUT/slave.slave"
fi
export DETERMINISTIC=1 SLAVE="$PWD/$OUT/slave.slave" CPU="${CPU:-68000}"
# The code is loaded into "other" memory: fast RAM at $200000 when there is any, else slow RAM.
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi
# Cache only the address, keyed by machine, arguments and slave build. A calibration
# boot discovers it; the measurement boot arms the race breakpoint at CPU reset.
mkdir -p tmp/prof
KEY=$(python3 -c 'import hashlib,os; from pathlib import Path; p=os.environ.get("SLAVE") or "tmp/game/TestDrive2/TestDrive2.slave"; h=hashlib.sha256(Path(p).read_bytes()); h.update(repr([(k,os.environ.get(k)) for k in ("AMIGA_MODEL","KICKSTART","CPU","CHIP_KB","FAST_KB","EXTRA_ARGS","WHD_ARGS")]).encode()); print(h.hexdigest()[:20])')
CACHE="tmp/prof/hunk-$KEY.txt"
BOOT_HUNK=${BOOT_HUNK:-$(cat "$CACHE" 2>/dev/null || true)}
if [ -n "$BOOT_HUNK" ]; then export BOOT_BREAK=$(printf '%#x' $((BOOT_HUNK + ${ANCHOR:-0xbbf8}))); fi
td2() { python3 tools/td2.py "$@"; }
retain_log() {
  cp amiga/.run/fsuae.log "$OUT/fsuae-stdout.log"
  local logfile
  logfile=$(sed -n 's/^LOGFILE: //p' amiga/.run/fsuae.log | tail -1)
  if [ -n "$logfile" ] && [ -f "$logfile" ]; then
    cp "$logfile" "$OUT/fsuae.log"
  else
    cp amiga/.run/fsuae.log "$OUT/fsuae.log"
  fi
}
[ -S amiga/.run/td2.sock ] && { td2 quit > /dev/null 2>&1 || true; sleep 1; }
rm -f amiga/.run/serve.log "$OUT/trace.bin"
WARP=1 python3 tools/td2.py serve > amiga/.run/serve.log 2>&1 &
trap 'td2 quit > /dev/null 2>&1 || true' EXIT
SERVER=$!
for _ in $(seq 1 "${SERVE_WAIT:-180}"); do
  grep -q serving amiga/.run/serve.log 2>/dev/null && break
  kill -0 "$SERVER" 2>/dev/null || { cat amiga/.run/serve.log >&2; exit 1; }
  sleep 1
done
grep -q serving amiga/.run/serve.log || { echo "race breakpoint not reached" >&2; exit 1; }

dump() { td2 gdb "dump binary memory /tmp/td2-code.bin $BASE $(printf '%#x' $((BASE + SIZE)))" > /dev/null; mv /tmp/td2-code.bin "$OUT/code.bin"; }
hunk=
for _ in $(seq 1 60); do
  [ -n "$BOOT_HUNK" ] || td2 wait 1 > /dev/null
  dump
  hunk=$(python3 -c "
import sys; sys.path.insert(0, 'tools'); from td2_report import regions
r = {n: lo for lo, hi, n, o in regions(open('$OUT/code.bin', 'rb').read(), $BASE)}
print(hex(r['duel']) if 'duel' in r else '')")
  [ -n "$hunk" ] && break
done
[ -n "$hunk" ] || { echo "duel never appeared in memory" >&2; exit 1; }
echo "duel code hunk at $hunk"
if [ -z "$BOOT_HUNK" ]; then
  printf '%s\n' "$hunk" > "$CACHE"
  td2 quit > /dev/null; trap - EXIT
  echo "calibrated code address; rebooting with the race breakpoint armed"
  exec bash "$0" "$OUT" "$SLAVE"
fi
[ "$((hunk))" = "$((BOOT_HUNK))" ] || { echo "loaded hunk differs from boot breakpoint" >&2; exit 1; }
# Watch the clock's initialising store, then stay stopped for state/trace capture.
td2 gdb 'info registers a4 pc' > "$OUT/anchor.txt"
if [ "${ANCHOR:-0xbbf8}" = 0xbbf8 ]; then
  td2 gdb 'watch *(int*)($a4-10146)' >> "$OUT/anchor.txt"
  td2 gdb continue >> "$OUT/anchor.txt"
  td2 gdb delete >> "$OUT/anchor.txt"
  # Race setup draws the initial dashboard, then the gameplay loop starts here.
  td2 until "$(printf '%#x' $((hunk + 0x5a4c)))" >> "$OUT/anchor.txt"
fi
td2 gdb 'x/1uw $a4-10146' >> "$OUT/anchor.txt"
# Optional read-only state study: sample N VBL entries before the traced window.
# The trace then starts after these N fields; record that offset when quoting its fps.
if [ "${STATE_FIELDS:-0}" -gt 0 ]; then
  python3 tools/state_fields.py "$STATE_FIELDS" "$OUT/state" "$OUT/code.bin" "$BASE"
fi
if [ "${RENDER_FRAMES:-0}" -gt 0 ]; then
  python3 tools/render_fields.py "$RENDER_FRAMES" "$OUT/render" "$OUT/code.bin" "$BASE"
fi
if [ "${SIDEWAYS_FRAMES:-0}" -gt 0 ]; then
  python3 tools/sideways_fields.py "$SIDEWAYS_FRAMES" "$OUT/sideways" "$OUT/code.bin" "$BASE" \
    $([ "${SIDEWAYS_RECOVERY:-0}" = 1 ] && echo --recovery)
fi
# State-only studies need no cycle trace or debugger attach to the host process.
# Deliberately emit no frame-rate figure in this mode.
if [ "${STATE_ONLY:-0}" = 1 ]; then
  [ "${STATE_FIELDS:-0}" -gt 0 ] || [ "${RENDER_FRAMES:-0}" -gt 0 ] || [ "${SIDEWAYS_FRAMES:-0}" -gt 0 ] ||
    { echo "STATE_ONLY requires STATE_FIELDS, RENDER_FRAMES or SIDEWAYS_FRAMES" >&2; exit 1; }
  dump
  td2 quit > /dev/null; trap - EXIT
  retain_log
  echo "state-only capture complete (no frame-rate measurement)"
  exit 0
fi
if [ "${SWAP_ONLY:-0}" = 1 ]; then
  python3 tools/swap_fields.py "$FIELDS" "$OUT" "$OUT/code.bin" "$BASE"
  dump
  td2 quit > /dev/null; trap - EXIT
  retain_log
  exit 0
fi
reply=$(td2 profile "$FIELDS" "$PWD/$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "no trace: $reply" >&2; exit 1; }
if [ "${WATCH_STATE:-0}" = 1 ]; then
  python3 tools/state_watch.py "$OUT/state"
fi
dump
td2 quit > /dev/null; trap - EXIT
retain_log
python3 - "$OUT" <<'EOF'
import sys; sys.path.insert(0, 'tools'); import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
EOF
python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" | tee "$OUT/frames.txt"
