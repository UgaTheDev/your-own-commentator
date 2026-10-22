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
mkdir -p out && rm -f out/take-a.webm out/take-b.webm out/take-c.webm out/take.log out/take.marks
. ./emurec.sh

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
k() { local c=""; for key in "$@"; do c+="inputd-cli button_press KEY_$key; sleep 0.35; "; done; vega device run-cmd -c "$c" >/dev/null 2>&1; }  # gap: back-to-back presses drop
rec() { until_t "$(python3 -c "print($T0 + $1)")"; }   # wait until recording time $1
# Game time comes from the app's 1 s playhead heartbeat, so pauses (switches, replays, cards) can't drift the script.
gt() { grep -a 'tick t=' $O.log | tail -1 | sed -E 's/.* t=([0-9.]+).*/\1/'; }
g() { until python3 -c "import sys; sys.exit(0 if float('$(gt)' or 0) >= $1 else 1)"; do sleep 0.2; done; }
# Wait (max $2 s) for a NEW app log line matching $1.
w() { local n; n=$(grep -ac "$1" $O.log); for _ in $(seq $(( ${2:-30} * 5 ))); do
        [ "$(grep -ac "$1" $O.log)" -gt "$n" ] && return 0; sleep 0.2; done; echo "  (timeout waiting for: $1)"; }

# Full take on the redesigned UI. Home: hero -> games -> commentator grid, then Rookie from the grid.
rec 3;   mark home;       k DOWN RIGHT RIGHT LEFT LEFT
rec 9;   mark grid;       k DOWN DOWN RIGHT RIGHT LEFT LEFT   # games -> ▲Games link -> Rookie card (grid scrolls in)
rec 15;  mark rookie;     k ENTER
# Same play, four voices: Rookie calls the 98.0 two-pointer; each pass waits until every voice has finished (105),
# rewinds 20 s (two presses: key latency varies by ~3 s) and switches, so the next voice gets the same call.
# Recorder parts (180 s cap each) restart at pass boundaries, where nothing is being said.
part() { erec_stop; T0=$(python3 -c 'import time; print(time.time())'); erec_start "$PWD/out/take-$1.webm"; echo "part $1 t0=$T0" >> $O.marks; }
# After a rewind the last logged tick is still >= 105 until the next one, so wait for the clock to drop first.
lt() { until python3 -c "import sys; sys.exit(0 if 0 < float('$(gt)' or 0) < $1 else 1)"; do sleep 0.2; done; }
g 105;            mark kid;      k REWIND REWIND ENTER RIGHT ENTER; w 'seeked kid' 10; lt 100
g 105;   part b;  mark spanish;  k REWIND REWIND ENTER RIGHT RIGHT RIGHT ENTER; w 'seeked rookie-es' 10; lt 100
g 105;            mark hindi;    k REWIND REWIND ENTER RIGHT ENTER; w 'seeked rookie-hi' 10; lt 100
g 105;   part c;  mark booth;    k REWIND REWIND ENTER LEFT LEFT LEFT ENTER; w 'seeked booth' 10; lt 100
g 101;   mark replay;     k RIGHT RIGHT RIGHT ENTER; w 'YOC: @[0-9]* seeked .*back' 30
g 108.5; mark fantasy;    k RIGHT RIGHT ENTER RIGHT ENTER; w 'seeked fantasy' 10   # focus is on Why? after Replay hides
g 132;   mark why;        k LEFT LEFT ENTER; w 'why e9' 8; sleep 2.5; mark question; k ENTER; w 'overlay closed' 40
sleep 1; mark map;        k RIGHT RIGHT RIGHT ENTER
sleep 8; mark catchup;    k LEFT LEFT ENTER; w 'overlay closed' 40
sleep 1; mark highlights; k RIGHT RIGHT RIGHT RIGHT ENTER
sleep 10; mark end
erec_stop; trap 'kill $LP 2>/dev/null' EXIT
echo "take saved: out/take-{a,b,c}.webm"
