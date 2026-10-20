#!/usr/bin/env bash
# Record the VVD screen (no audio: macOS can't capture it) while streaming the app log and pressing keys.
#   scripts/demo/record.sh <x> <y> <w> <h> <out_prefix> [keys_file]
# Crop is in captured pixels (Retina: 2x the point coordinates). Writes <prefix>.mp4, <prefix>.log
# (YOC lines for soundtrack.py), <prefix>.start_ms (epoch ms when ffmpeg was launched) and <prefix>.keys.log.
# keys_file lines: "<seconds from start> <KEY_NAME>" (e.g. "12.5 KEY_ENTER"); "<seconds> STOP" ends the take.
set -euo pipefail
[ $# -ge 5 ] || { echo "usage: $0 x y w h out_prefix [keys_file]" >&2; exit 2; }
x=$1 y=$2 w=$3 h=$4 out=$5 keys=${6:-$(dirname "$0")/keys.demo.txt}
now_ms() { python3 -c 'import time; print(int(time.time() * 1000))'; }

vega device start-log-stream > "$out.log" 2>&1 &
logpid=$!
sleep 2  # let the stream attach before anything happens
now_ms > "$out.start_ms"
ffmpeg -v error -y -f avfoundation -framerate 30 -capture_cursor 0 -pixel_format nv12 -i "2:none" \
  -vf "crop=$w:$h:$x:$y" -c:v libx264 -preset ultrafast -crf 18 -pix_fmt yuv420p "$out.mp4" < /dev/null &
ffpid=$!
trap 'kill -INT $ffpid 2>/dev/null; kill $logpid 2>/dev/null' EXIT
t0=$(cat "$out.start_ms")

while read -r at key _; do
  case "$at" in ''|\#*) continue ;; esac
  wait_s=$(python3 -c "import time; print(max(0, $t0 / 1000 + $at - time.time()))")
  sleep "$wait_s"
  [ "$key" = STOP ] && break
  echo "$(now_ms) $at $key" >> "$out.keys.log"
  vega device run-cmd -c "inputd-cli button_press $key" > /dev/null
done < "$keys"

kill -INT $ffpid; wait $ffpid 2>/dev/null || true
kill $logpid 2>/dev/null || true
trap - EXIT
echo "recorded $out.mp4 (start $(cat "$out.start_ms")), log $out.log"
