#!/usr/bin/env bash
# One demo take on Lake Region, driven by remote keys timed to the game's verified events.
# Records the VVD display (with its audio) through the emulator console in parts (180 s cap each):
# out/take-a.webm, -b (from Spanish), -c (from Booth). Marks are seconds in that part, in out/take.marks.
# Player strip (redesign): Why?(0) Catch me up(1) <commentator> ▲(2, opens the tray; focus starts here) Map(3)
#   Highlights(4) Replay(5, only within 10 s of an event with a replay). Tray: Rookie Kid Booth Fantasy Novato Hindi 新手,
#   opens on the on-air one; OK switches and focus returns to the commentator button.
set -uo pipefail
cd "$(dirname "$0")"
O=out/take
mkdir -p out/prev && for f in out/take-?.webm out/take.log out/take.marks; do [ -e "$f" ] && mv "$f" out/prev/; done   # keep the last take
. ./emurec.sh

pkill -f "device start-log-stream" 2>/dev/null   # a stream left by an aborted take doubles the device load
vega run-app ../../app/build/aarch64-release/commentator_aarch64.vpkg >/dev/null 2>&1
sleep 8
vega device start-log-stream > $O.log 2>&1 & LP=$!
trap 'erec_stop; kill $LP 2>/dev/null' EXIT
sleep 2
T0=$(python3 -c 'import time; print(time.time())'); erec_start "$PWD/out/take-a.webm"; echo "part a t0=$T0" >> $O.marks

now() { python3 -c 'import time; print(time.time())'; }
until_t() { python3 -c "import time; time.sleep(max(0, $1 - time.time()))"; }
mark() { echo "$(python3 -c "import time; print(round(time.time() - $T0, 1))") $*" | tee -a $O.marks; }
# All keys in one device round trip (~0.3 s each instead of ~1.1 s).
k() { local c=""; for key in "$@"; do c+="inputd-cli button_press KEY_$key; sleep 0.35; "; done; perl -e 'alarm 20; exec @ARGV' vega device run-cmd -c "$c" >/dev/null 2>&1; }  # a hung run-cmd can't stall the take  # gap: back-to-back presses drop
rec() { until_t "$(python3 -c "print($T0 + $1)")"; }   # wait until recording time $1
# Game time comes from the app's 1 s playhead heartbeat, so pauses (switches, replays, cards) can't drift the script.
gt() { grep -a 'tick t=' $O.log | tail -1 | sed -E 's/.* t=([0-9.]+).*/\1/'; }
g() { local i=0; until python3 -c "import sys; sys.exit(0 if float('$(gt)' or 0) >= $1 else 1)"; do sleep 0.2
        i=$((i+1)); [ $i -gt 900 ] && die "game clock never reached $1"; done; }   # 3 min
# Wait (max $2 s) for a NEW app log line matching $1.
w() { local n; n=$(grep -ac "$1" $O.log); for _ in $(seq $(( ${2:-30} * 5 ))); do
        [ "$(grep -ac "$1" $O.log)" -gt "$n" ] && return 0; sleep 0.2; done; echo "  (timeout waiting for: $1)"; return 1; }
die() { echo "TAKE FAILED: $*"; exit 1; }   # make.sh re-shoots
# Keys that must land: re-send if the app logged no focus/press within 2 s (a run-cmd can be lost silently).
kc() { local p=${KP:-'YOC: (press|focus) '} n; n=$(grep -acE "$p" $O.log); for _ in 1 2 3; do k "$@"; sleep 2
         [ "$(grep -acE "$p" $O.log)" -gt "$n" ] && return 0; done; die "keys lost: $*"; }
# The switch must land before the 98.0 call, or that voice has nothing to say (run-cmd latency varies 1-7 s).
early() { python3 -c "import re,sys; t=float(re.findall(r'switch to \S+ at t=([\d.]+)', open('$O.log', errors='replace').read())[-1]); sys.exit(t >= 97)" || die "switched in too late"; }
kr() { KP='YOC: @[0-9]+ seek [0-9]' kc REWIND REWIND; }   # rewind 20 s; a rewind logs a seek, not a press

# Full take on the redesigned UI. Home: hero -> games -> commentator grid, then Rookie from the grid.
rec 3;   mark home;       k DOWN RIGHT RIGHT LEFT LEFT
rec 9;   mark grid;       k DOWN DOWN RIGHT RIGHT LEFT LEFT   # games -> ▲Games link -> Rookie card (grid scrolls in)
rec 15;  mark rookie;     k ENTER
# Same play, four voices: Rookie calls the 98.0 two-pointer; each pass waits until every voice has finished (105),
# opens the tray over live video, then in one burst moves to the next voice, rewinds 30 s and selects it: the
# rewind's ~2 s picture freeze falls in the switch's black gap. (Keys sent seconds after a rewind are lost.)
# Recorder parts (180 s cap each) restart at pass boundaries, where nothing is being said.
part() { erec_stop; T0=$(python3 -c 'import time; print(time.time())'); erec_start "$PWD/out/take-$1.webm"; echo "part $1 t0=$T0" >> $O.marks; }
# After a rewind the last logged tick is still >= 105 until the next one, so wait for the clock to drop first.
lt() { local i=0; until python3 -c "import sys; sys.exit(0 if 0 < float('$(gt)' or 0) < $1 else 1)"; do sleep 0.2
         i=$((i+1)); [ $i -gt 150 ] && die "rewind never landed (clock stayed >= $1)"; done; }
g 105;            mark kid;      kc ENTER; sleep 1.5; k RIGHT REWIND REWIND REWIND ENTER; w 'seeked kid' 15 || die 'seeked kid'; early; lt 100
g 105;   part b;  mark spanish;  kc ENTER; sleep 1.5; k RIGHT RIGHT RIGHT REWIND REWIND REWIND ENTER; w 'seeked rookie-es' 15 || die 'seeked rookie-es'; early; lt 100
g 105;            mark hindi;    kc ENTER; sleep 1.5; k RIGHT REWIND REWIND REWIND ENTER; w 'seeked rookie-hi' 15 || die 'seeked rookie-hi'; early; lt 100
g 105;   part c;  mark booth;    kc ENTER; sleep 1.5; k LEFT LEFT LEFT REWIND REWIND REWIND ENTER; w 'seeked booth' 15 || die 'seeked booth'; early; lt 100
g 101;   mark replay;     k RIGHT RIGHT RIGHT ENTER; w 'YOC: @[0-9]* seeked .*back' 30
g 108.5; mark fantasy;    k RIGHT RIGHT ENTER RIGHT ENTER; w 'seeked fantasy' 10   # focus is on Why? after Replay hides
g 137;   mark why;        k LEFT LEFT ENTER; w 'why e9' 8; sleep 2.5; mark question; k ENTER; w 'overlay closed' 40
sleep 1; mark map;        k RIGHT RIGHT RIGHT ENTER
sleep 8; mark catchup;    k LEFT LEFT ENTER; w 'overlay closed' 40
sleep 1; mark highlights; k RIGHT RIGHT RIGHT RIGHT ENTER
sleep 10; mark end
erec_stop; trap 'kill $LP 2>/dev/null' EXIT
echo "take saved: out/take-{a,b,c}.webm"
