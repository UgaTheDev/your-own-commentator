#!/usr/bin/env bash
# One demo take on Lake Region, driven by remote keys timed to the game's verified events.
# Records only the VVD window (with its audio) to out/take.mov; marks every step in out/take.marks.
# Player strip (redesign): Why?(0) Catch me up(1) <commentator> ▲(2, opens the tray; focus starts here) Map(3)
#   Highlights(4) Replay(5, only within 10 s of an event with a replay). Tray: Rookie Kid Booth Fantasy Novato Hindi 新手,
#   opens on the on-air one; OK switches and focus returns to the commentator button.
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
out/winrec "$WID" $O.mov "${TAKE_SECS:-300}" > $O.rec.txt 2>&1 & RP=$!
until grep -q start_ms $O.rec.txt 2>/dev/null; do kill -0 $RP 2>/dev/null || { cat $O.rec.txt; exit 1; }; sleep 0.1; done
awk '/start_ms/{print $2}' $O.rec.txt > $O.start_ms; T0=$(awk '{printf "%.3f", $1/1000}' $O.start_ms)

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
g 40;    mark kid;        k ENTER RIGHT ENTER; w 'seeked kid' 10
g 50;    mark spanish;    k ENTER RIGHT RIGHT RIGHT ENTER; w 'seeked rookie-es' 10
g 69;    mark hindi;      k ENTER RIGHT ENTER; w 'seeked rookie-hi' 10
g 80;    mark booth;      k ENTER LEFT LEFT LEFT ENTER; w 'seeked booth' 10
g 98.4;  mark replay;     k RIGHT RIGHT RIGHT ENTER; w 'YOC: @[0-9]* seeked .*back' 30
g 108.5; mark fantasy;    k RIGHT RIGHT ENTER RIGHT ENTER; w 'seeked fantasy' 10   # focus is on Why? after Replay hides
g 132;   mark why;        k LEFT LEFT ENTER; w 'why e9' 8; sleep 2.5; mark question; k ENTER; w 'overlay closed' 40
sleep 1; mark map;        k RIGHT RIGHT RIGHT ENTER
sleep 8; mark catchup;    k LEFT LEFT ENTER; w 'overlay closed' 40
sleep 1; mark highlights; k RIGHT RIGHT RIGHT RIGHT ENTER
sleep 18; mark end
wait $RP   # winrec finalizes the file itself; killing it would corrupt the .mov
echo "take saved: $O.mov"
