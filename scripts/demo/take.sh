#!/usr/bin/env bash
# One demo take on Lake Region, driven by remote keys timed to the game's verified events.
# Records only the VVD window (with its audio) to out/take.mov; marks every step in out/take.marks.
# Player bar: Why?(0) Catch me up(1) Rookie(2) Kid(3) Booth(4) Fantasy(5) Novato(6) Hindi(7) 新手(8) Map(9)
#             Highlights(10) Replay(11, only within 10 s of an event with a replay).
set -uo pipefail
cd "$(dirname "$0")"
O=out/take
mkdir -p out && rm -f out/take.mov out/take.log out/take.marks out/take.rec.txt out/take.start_ms
[ out/winrec -nt winrec.swift ] || swiftc -O winrec.swift -o out/winrec
WID=$(osascript -l JavaScript -e 'ObjC.import("CoreGraphics"); var l=ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0,0))); var w=l.find(w=>w.kCGWindowName=="Vega Virtual Device"); w?w.kCGWindowNumber:""')
[ -n "$WID" ] || { echo "VVD window not found"; exit 1; }

vega run-app ../../app/build/aarch64-release/commentator_aarch64.vpkg >/dev/null 2>&1
sleep 8
vega device start-log-stream > $O.log 2>&1 & LP=$!
trap 'kill $LP 2>/dev/null' EXIT
sleep 2
out/winrec "$WID" $O.mov "${TAKE_SECS:-260}" > $O.rec.txt 2>&1 & RP=$!
until grep -q start_ms $O.rec.txt 2>/dev/null; do kill -0 $RP 2>/dev/null || { cat $O.rec.txt; exit 1; }; sleep 0.1; done
awk '/start_ms/{print $2}' $O.rec.txt > $O.start_ms; T0=$(awk '{printf "%.3f", $1/1000}' $O.start_ms)

now() { python3 -c 'import time; print(time.time())'; }
until_t() { python3 -c "import time; time.sleep(max(0, $1 - time.time()))"; }
mark() { echo "$(python3 -c "import time; print(round(time.time() - $T0, 1))") $*" | tee -a $O.marks; }
# All keys in one device round trip (~0.3 s each instead of ~1.1 s).
k() { local c=""; for key in "$@"; do c+="inputd-cli button_press KEY_$key; "; done; vega device run-cmd -c "$c" >/dev/null 2>&1; }
rec() { until_t "$(python3 -c "print($T0 + $1)")"; }   # wait until recording time $1
# Game time comes from the app's 1 s playhead heartbeat, so pauses (switches, replays, cards) can't drift the script.
gt() { grep -a 'talk playhead' $O.log | tail -1 | sed -E 's/.* t=([0-9.]+).*/\1/'; }
g() { until python3 -c "import sys; sys.exit(0 if float('$(gt)' or 0) >= $1 else 1)"; do sleep 0.2; done; }
# Wait (max $2 s) for a NEW app log line matching $1.
w() { local n; n=$(grep -ac "$1" $O.log); for _ in $(seq $(( ${2:-30} * 5 ))); do
        [ "$(grep -ac "$1" $O.log)" -gt "$n" ] && return 0; sleep 0.2; done; echo "  (timeout waiting for: $1)"; }

# Take 3: Rookie only, for the moments take 2 missed (Replay at e6, Why? at e9, Map, Catch me up).
rec 2;  mark rookie;  k ENTER
g 84;                 k RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT   # Rookie(2) -> Highlights(10)
g 98.6; mark replay; k RIGHT ENTER; w 'YOC: @[0-9]* seeked .*back' 30
g 109;  mark fantasy; k RIGHT RIGHT RIGHT RIGHT RIGHT ENTER; w 'seeked fantasy' 10   # focus is on Why? once Replay hides
g 124;                k LEFT LEFT LEFT LEFT LEFT
g 132;  mark why; k ENTER; w 'why e9' 8; sleep 2.5; mark question; k ENTER; w 'overlay closed' 40
sleep 1; mark map;    k RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT ENTER
sleep 9; mark catchup; k LEFT LEFT LEFT LEFT LEFT LEFT LEFT LEFT ENTER; w 'overlay closed' 40
sleep 2; mark end
wait $RP   # winrec finalizes the file itself; killing it would corrupt the .mov
echo "take saved: $O.mov"
