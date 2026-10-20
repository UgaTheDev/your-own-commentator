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
out/winrec "$WID" $O.mov "${TAKE_SECS:-290}" > $O.rec.txt 2>&1 & RP=$!
until grep -q start_ms $O.rec.txt 2>/dev/null; do kill -0 $RP 2>/dev/null || { cat $O.rec.txt; exit 1; }; sleep 0.1; done
T0=$(awk '/start_ms/{print $2/1000}' $O.rec.txt); echo "${T0%.*}000" > $O.start_ms

now() { python3 -c 'import time; print(time.time())'; }
until_t() { python3 -c "import time; time.sleep(max(0, $1 - time.time()))"; }
mark() { echo "$(python3 -c "import time; print(round(time.time() - $T0, 1))") $*" | tee -a $O.marks; }
k() { for key in "$@"; do vega device run-cmd -c "inputd-cli button_press KEY_$key" >/dev/null 2>&1; done; }
rec() { until_t "$(python3 -c "print($T0 + $1)")"; }   # wait until recording time $1
P=0 D=0
g() { until_t "$(python3 -c "print($P + 3 + $D + $1)")"; }  # wait until ~game time $1 (+ paused seconds D)

mark home;            rec 2;  k RIGHT RIGHT LEFT LEFT
rec 8;  mark rookie;  k ENTER; P=$(now)
g 42;   mark kid;     k RIGHT ENTER
g 51;   mark spanish; k RIGHT RIGHT RIGHT ENTER
g 70;   mark hindi;   k RIGHT ENTER
g 82;   mark booth;   k LEFT LEFT LEFT ENTER
g 88;                 k RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT      # park on Highlights before e6 (98.0)
g 99.5; mark replay;  k RIGHT ENTER;  D=14                       # Replay appears after e6; 12 s clip pauses the game
g 104;  mark fantasy; k RIGHT RIGHT RIGHT RIGHT RIGHT ENTER       # focus returned to Why? after the replay
g 127;                k LEFT LEFT LEFT LEFT LEFT                  # back to Why? before e9 (131.5)
g 133;  mark why;     k ENTER; sleep 3; mark question; k ENTER
sleep 15; mark map;   k RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT RIGHT ENTER
sleep 8;  mark catchup; k LEFT LEFT LEFT LEFT LEFT LEFT LEFT LEFT ENTER
sleep 15; mark home2; k BACK
sleep 4;  mark highlights; k DOWN RIGHT RIGHT ENTER
sleep 25; mark end
wait $RP
echo "take saved: $O.mov"
