#!/usr/bin/env bash
# Benchmark window: trace FIELDS PAL fields in a training flight driven by the verify tape.
#   tools/fixed_window.sh OUTDIR [SLAVE]
# The tape (CUSTOM5=2: training flight 4, bomber with escort) flies the menus. A calibration
# boot learns bob's load address (cached per machine, arguments and slave); the measurement
# boot arms the flight-loop anchor bob:12968 at CPU reset, skips SKIP_FRAMES more passes of
# the loop (one per rendered frame), then traces.
# Env: FIELDS (default 100), SKIP_FRAMES (default 40), SWAP_ONLY=1 (count swaps with
# breakpoints, for CPUs without an instruction trace), STATE_FIELDS=N, C2P_CHECK=N (check N
# C2P calls against a model of the original), XFORM_CHECK=N (the same for N calls of the
# routines in XFORM_ROUTINE: xform, the default, proj, div, clear, tile,
# scen, pnorm, aiturn; tools/xform_check.py), SERVE_WAIT (seconds).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=$1; mkdir -p "$OUT"; FIELDS=${FIELDS:-100}
export CHIP_KB="${CHIP_KB:-512}" FAST_KB="${FAST_KB:-0}" EXTRA_ARGS="${EXTRA_ARGS---slow_memory=1536}"
# Retain exactly the slave used by this capture.
INPUT_SLAVE=${2:-tmp/slaves/verify.slave}
if [ "$INPUT_SLAVE" != "$PWD/$OUT/slave.slave" ]; then
  cp "$INPUT_SLAVE" "$OUT/slave.slave"
fi
export DETERMINISTIC=1 JOY0=none SLAVE="$PWD/$OUT/slave.slave" CPU="${CPU:-68000}"
# Add the tape option once: the script re-executes itself after the calibration boot.
case " ${WHD_ARGS:-} " in *" CUSTOM5="*) ;; *) export WHD_ARGS="CUSTOM5=2 ${WHD_ARGS:-}";; esac
SLOW_KB=$(sed -n 's/.*--slow_memory=\([0-9]*\).*/\1/p' <<< "$EXTRA_ARGS")
if [ "$FAST_KB" -gt 0 ]; then BASE=0x200000; SIZE=$((FAST_KB * 1024))
else BASE=0xc00000; SIZE=$((${SLOW_KB:-512} * 1024)); fi
mkdir -p tmp/prof
KEY=$(python3 -c 'import hashlib,os; from pathlib import Path; h=hashlib.sha256(Path(os.environ["SLAVE"]).read_bytes()); h.update(repr([(k,os.environ.get(k)) for k in ("AMIGA_MODEL","KICKSTART","CPU","CHIP_KB","FAST_KB","EXTRA_ARGS","WHD_ARGS")]).encode()); print(h.hexdigest()[:20])')
CACHE="tmp/prof/hunk-$KEY.txt"
BOOT_HUNK=${BOOT_HUNK:-$(cat "$CACHE" 2>/dev/null || true)}
ANCHOR=${ANCHOR:-0x12968}
if [ -n "$BOOT_HUNK" ]; then export BOOT_BREAK=$(printf '%#x' $((BOOT_HUNK + ANCHOR))); fi
tfh() { python3 tools/tfh.py "$@"; }
[ -S amiga/.run/tfh.sock ] && { tfh quit > /dev/null 2>&1 || true; sleep 1; }
rm -f amiga/.run/serve.log "$OUT/trace.bin"
WARP=1 python3 tools/tfh.py serve > amiga/.run/serve.log 2>&1 &
trap 'tfh quit > /dev/null 2>&1 || true' EXIT
SERVER=$!
for _ in $(seq 1 "${SERVE_WAIT:-300}"); do
  grep -q serving amiga/.run/serve.log 2>/dev/null && break
  kill -0 "$SERVER" 2>/dev/null || { cat amiga/.run/serve.log >&2; exit 1; }
  sleep 1
done
grep -q serving amiga/.run/serve.log || { echo "anchor not reached" >&2; exit 1; }

# gdb runs in the repo root and its dump command takes no spaces in the path: dump to tmp/.
dump() { tfh gdb "dump binary memory tmp/tfh-code.bin $BASE $(printf '%#x' $((BASE + SIZE)))" > /dev/null; mv tmp/tfh-code.bin "$OUT/code.bin"; }
hunk=
for _ in $(seq 1 300); do
  [ -n "$BOOT_HUNK" ] || tfh wait 1 > /dev/null
  dump
  hunk=$(python3 -c "
import sys; sys.path.insert(0, 'tools'); from tfh_report import regions
r = {n: lo for lo, hi, n, o in regions(open('$OUT/code.bin', 'rb').read(), $BASE)}
print(hex(r['bob']) if 'bob' in r else '')")
  # Accept only the live copy: the game's level-3 handler (bob:28d4c) is installed at $6C.
  # Early in the boot other bob-shaped copies exist (before LoadSeg finished).
  if [ -n "$hunk" ]; then
    vec=$(tfh gdb 'x/1xw 0x6c' | tail -1 | awk '{print $2}')
    [ "$((vec))" = "$((hunk + 0x28d4c))" ] && break
    hunk=
  fi
done
[ -n "$hunk" ] || { echo "bob never appeared in memory" >&2; exit 1; }
echo "bob code hunk at $hunk"
if [ -z "$BOOT_HUNK" ]; then
  printf '%s\n' "$hunk" > "$CACHE"
  tfh quit > /dev/null; trap - EXIT
  echo "calibrated code address; rebooting with the flight anchor armed"
  exec bash "$0" "$OUT" "$SLAVE"
fi
[ "$((hunk))" = "$((BOOT_HUNK))" ] || { echo "loaded hunk differs from boot breakpoint" >&2; exit 1; }
tfh gdb 'info registers pc a4' > "$OUT/anchor.txt"
if [ "${SKIP_FRAMES:-40}" -gt 0 ]; then
  tfh gdb "break *$BOOT_BREAK" >> "$OUT/anchor.txt"
  tfh gdb "ignore \$bpnum $((${SKIP_FRAMES:-40} - 1))" >> "$OUT/anchor.txt"
  tfh gdb continue >> "$OUT/anchor.txt"
  tfh gdb delete >> "$OUT/anchor.txt"
fi
# The boot benchmark's time divisor T (11698(a4)) and the detail level (11196(a4)).
tfh gdb 'x/1dh $a4+11698' | tail -1 | sed 's/^/T /' >> "$OUT/anchor.txt"
tfh gdb 'x/1db $a4+11196' | tail -1 | sed 's/^/detail /' >> "$OUT/anchor.txt"
# The verify tape's field (tape_vbl), so that tape entries can be placed in flight.
tape=$(python3 tools/slave_sym.py "$OUT/code.bin" "$BASE" tape_vbl 2>/dev/null | awk '{print $2}') || true
[ -n "$tape" ] && tfh gdb "x/1uh $tape" | tail -1 | sed 's/^/tape field /' >> "$OUT/anchor.txt"
grep -E '^(T|detail|tape field) ' "$OUT/anchor.txt" || true
if [ "${STATE_FIELDS:-0}" -gt 0 ]; then
  python3 tools/state_fields.py "$STATE_FIELDS" "$OUT/state" "$OUT/code.bin" "$BASE"
fi
if [ "${C2P_CHECK:-0}" -gt 0 ]; then
  python3 tools/c2p_check.py "$C2P_CHECK" "$OUT/c2p" "$OUT/code.bin" "$BASE" | tee "$OUT/c2p.txt"
fi
if [ "${XFORM_CHECK:-0}" -gt 0 ]; then
  for r in ${XFORM_ROUTINE:-xform}; do
    python3 tools/xform_check.py --routine "$r" "$XFORM_CHECK" "$OUT/code.bin" "$BASE" | tee "$OUT/xform-$r.txt"
  done
fi
if [ "${STATE_ONLY:-0}" = 1 ]; then
  dump; tfh quit > /dev/null; trap - EXIT
  cp amiga/.run/fsuae.log "$OUT/fsuae-stdout.log"
  echo "state-only capture complete (no frame-rate measurement)"
  exit 0
fi
if [ "${SWAP_ONLY:-0}" = 1 ]; then
  python3 tools/swap_fields.py "$FIELDS" "$OUT" "$OUT/code.bin" "$BASE"
  dump; tfh quit > /dev/null; trap - EXIT
  cp amiga/.run/fsuae.log "$OUT/fsuae-stdout.log"
  exit 0
fi
reply=$(tfh profile "$FIELDS" "$PWD/$OUT/trace.bin")
[ -f "$OUT/trace.bin" ] || { echo "no trace: $reply" >&2; exit 1; }
dump
tfh quit > /dev/null; trap - EXIT
cp amiga/.run/fsuae.log "$OUT/fsuae-stdout.log"
python3 - "$OUT" <<'EOF'
import sys; sys.path.insert(0, 'tools'); import barto
out = sys.argv[1]; t = barto.load(f'{out}/trace.bin')
open(f'{out}/first.png', 'wb').write(t.fields[0].shot)
open(f'{out}/last.png', 'wb').write(t.fields[-1].shot)
EOF
python3 tools/frames.py "$OUT/trace.bin" "$OUT/code.bin" "$BASE" | tee "$OUT/frames.txt"
