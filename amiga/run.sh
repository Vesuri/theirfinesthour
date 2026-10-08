#!/usr/bin/env bash
# Boot the installed original Their Finest Hour under WHDLoad in FS-UAE.
#   amiga/run.sh            windowed, real speed, with sound
#   DEBUG=1 amiga/run.sh    also open the Barto gdb stub on $DEBUG_PORT (no trigger)
#   JOY0=none amiga/run.sh  leave port 0 empty (the host mouse otherwise injects input)
#   SLAVE=path amiga/run.sh run another slave build instead of the installed one
# Shared files (amiga/env.sh; each variable overrides): KICKSTART, KICK13, RTB, WORKBENCH_ADF,
# WHDLOAD_BINARY.
# Host: Kickstart 3.1 + Workbench 2.04 floppy boots DH0, which runs WHDLoad on DH1;
# the slave itself runs Kickstart 1.3 (kick34005.A500 + .RTB) inside WHDLoad.
set -euo pipefail
cd "$(dirname "$0")"
. ./env.sh
. "${FSUAE_COMMON:-$HOME/.local/share/amiga/fsuae_common.sh}"

GAME="${GAME:-../tmp/game/TheirFinestHour}"
WB="$WORKBENCH_ADF"
WHD="$WHDLOAD_BINARY"
CPU="${CPU:-68000}"
AMIGA_MODEL="${AMIGA_MODEL:-A500}"
RUN=.run; DH0="$RUN/dh0"; DH1="$RUN/dh1"

fsuae_claim_port
rm -rf "$DH0" "$DH1"
mkdir -p "$DH0/s" "$DH0/devs/Kickstarts" "$RUN/state"
cp -R "$GAME" "$DH1"
cp -f "$WHD" "$DH1/WHDLoad"
# SLAVE= runs a rebuilt or patched slave in place of the installed one.
[ -n "${SLAVE:-}" ] && cp -f "$SLAVE" "$DH1/TheirFinestHour.Slave"
cp -f "$KICK13" "$DH0/devs/Kickstarts/kick34005.A500"
cp -f "$RTB" "$DH0/devs/Kickstarts/"
chmod -R u+w "$DH0" "$DH1"
printf 'Expert\nReadDelay=0\n' > "$DH0/s/WHDLoad.prefs"
printf '%s\n' 'DF0:C/Assign C: DF0:C' 'DF0:C/Assign LIBS: DF0:Libs' 'DF0:C/Assign DEVS: DH0:devs' \
  'Stack 16384' 'FailAt 999' 'CD DH1:' \
  "WHDLoad TheirFinestHour.Slave PRELOAD SPLASHDELAY=0 NOREQ ${WHD_ARGS:-}" > "$DH0/s/startup-sequence"
rm -f "$RUN"/state/*.uss

AUDIO=(); [ "${SILENT:-0}" = 1 ] && AUDIO=(--audio_driver=dummy)
DBG=(); [ "${DEBUG:-0}" = 1 ] && DBG=(--remote_debugger=20 --remote_debugger_port="$DEBUG_PORT")
REC=(); [ -n "${RECORD:-}" ] && REC=(--record="$RECORD" --deterministic=1)
[ "${DETERMINISTIC:-0}" = 1 ] && REC+=(--deterministic=1)
SHOTS="${FSEMU_SCREENSHOTS_DIR:-$PWD/$RUN/shots}"; mkdir -p "$SHOTS"; export FSEMU_SCREENSHOTS_DIR="$SHOTS"

"${FSUAE:-fs-uae}" \
  --base_dir="$PWD/$RUN/fsuae" \
  --amiga_model="$AMIGA_MODEL" --cpu="$CPU" --chip_memory="${CHIP_KB:-1024}" --fast_memory="${FAST_KB:-2048}" \
  --kickstart_file="$KICKSTART" \
  --hard_drive_0="$DH0" --hard_drive_0_priority=10 --hard_drive_1="$DH1" \
  --floppy_drive_0="$WB" \
  --joystick_port_0="${JOY0:-mouse}" --joystick_port_1="${JOY1:-keyboard}" \
  --automatic_input_grab=0 --fullscreen=0 --window_width=760 --window_height=568 \
  --ntsc_mode=0 --warp_mode="${WARP:-0}" --state_dir="$RUN/state" \
  "${AUDIO[@]}" "${DBG[@]}" "${REC[@]}" ${EXTRA_ARGS:-} > "$RUN/fsuae.log" 2>&1 &
fsuae_track $!
echo "fs-uae pid $FSUAE_PID (log $RUN/fsuae.log, port $DEBUG_PORT)"
