#!/usr/bin/env bash
# Catch-me-up take: Rookie plays to ~2:05, then Catch me up reads the 2:00 recap (re-shot after the recap fix).
set -uo pipefail
cd "$(dirname "$0")"
O=out/catchup
mkdir -p out && rm -f $O.mov $O.log $O.rec.txt $O.start_ms $O.ask.txt
[ out/winrec -nt winrec.swift ] || swiftc -O winrec.swift -o out/winrec
WID=$(osascript -l JavaScript -e 'ObjC.import("CoreGraphics"); var l=ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0,0))); var w=l.find(w=>w.kCGWindowName=="Vega Virtual Device"); w?w.kCGWindowNumber:""')
[ -n "$WID" ] || { echo "VVD window not found"; exit 1; }

vega run-app ../../app/build/aarch64-release/commentator_aarch64.vpkg >/dev/null 2>&1
sleep 8
vega device start-log-stream > $O.log 2>&1 & LP=$!
trap 'kill $LP 2>/dev/null' EXIT
sleep 2
vega device run-cmd -c "inputd-cli button_press KEY_ENTER" >/dev/null 2>&1   # Rookie
gt() { grep -a 'talk playhead' $O.log | tail -1 | sed -E 's/.* t=([0-9.]+).*/\1/'; }
until python3 -c "import sys; sys.exit(0 if float('$(gt)' or 0) >= 118 else 1)"; do sleep 0.2; done
out/winrec "$WID" $O.mov "${CATCHUP_SECS:-30}" > $O.rec.txt 2>&1 & RP=$!
until grep -q start_ms $O.rec.txt 2>/dev/null; do sleep 0.1; done
awk '/start_ms/{print $2}' $O.rec.txt > $O.start_ms
sleep 4; vega device run-cmd -c "inputd-cli button_press KEY_LEFT; inputd-cli button_press KEY_ENTER" >/dev/null 2>&1   # Rookie(2) -> Catch me up(1)
wait $RP
echo "catchup saved: $O.mov"
