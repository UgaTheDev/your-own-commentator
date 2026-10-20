#!/usr/bin/env bash
# Record ONLY the VVD window (video + the device's own audio, even if other windows cover it) while
# streaming the app log and pressing keys.
#   scripts/demo/record.sh <out_prefix> [keys_file]
# Writes <prefix>.mov (raw window), <prefix>.mp4 (TV picture cropped, 1920x1080), <prefix>.wav (device audio),
# <prefix>.log (YOC lines), <prefix>.start_ms (epoch ms of the first recorded frame), <prefix>.keys.log.
# keys_file lines: "<seconds from start> <KEY_NAME>" (e.g. "12.5 KEY_ENTER"); "<seconds> STOP" ends the take.
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: $0 out_prefix [keys_file]" >&2; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
out=$1 keys=${2:-$here/keys.demo.txt}
now_ms() { python3 -c 'import time; print(int(time.time() * 1000))'; }
bin=$here/out/winrec
[ -x "$bin" ] && [ "$bin" -nt "$here/winrec.swift" ] || { mkdir -p "$here/out"; swiftc -O "$here/winrec.swift" -o "$bin"; }
wid=$(osascript -l JavaScript -e 'ObjC.import("CoreGraphics"); var l=ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0,0))); var w=l.find(w=>w.kCGWindowName=="Vega Virtual Device"); w?w.kCGWindowNumber:""')
[ -n "$wid" ] || { echo "Vega Virtual Device window not found" >&2; exit 1; }
total=$(awk '$2=="STOP"{print $1+1}' "$keys" | tail -1); total=${total:-600}

vega device start-log-stream > "$out.log" 2>&1 &
logpid=$!
trap 'kill $logpid 2>/dev/null' EXIT
sleep 2  # let the stream attach before anything happens
"$bin" "$wid" "$out.mov" "$total" > "$out.rec.txt" &
recpid=$!
until grep -q start_ms "$out.rec.txt" 2>/dev/null; do sleep 0.05; done
awk '/start_ms/{print $2}' "$out.rec.txt" > "$out.start_ms"
t0=$(cat "$out.start_ms")

while read -r at key _; do
  case "$at" in ''|\#*) continue ;; esac
  sleep "$(python3 -c "import time; print(max(0, $t0 / 1000 + $at - time.time()))")"
  [ "$key" = STOP ] && break
  echo "$(now_ms) $at $key" >> "$out.keys.log"
  vega device run-cmd -c "inputd-cli button_press $key" > /dev/null
done < "$keys"

wait $recpid
kill $logpid 2>/dev/null || true
trap - EXIT
# TV picture = window minus the 28 pt title bar (56 px), 16:9 from the left (the remote panel sits right of it)
ffmpeg -v error -y -i "$out.mov" -vf "crop=trunc((ih-56)*16/9/2)*2:ih-56:0:56,scale=1920:1080:flags=lanczos,fps=30" \
  -c:v libx264 -preset medium -crf 16 -pix_fmt yuv420p -an "$out.mp4"
ffmpeg -v error -y -i "$out.mov" -vn -ac 2 -ar 48000 "$out.wav"
echo "recorded $out.mp4 + $out.wav (start $t0), log $out.log"
