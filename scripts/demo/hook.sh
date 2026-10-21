#!/usr/bin/env bash
# Hook take: Rookie plays; right after the first free throw a viewer asks "why did they stop?" through the
# phone relay (ask.py, a Polly voice), and the TV pauses and answers. Records the VVD display (emurec.sh) to out/hook.webm.
set -uo pipefail
cd "$(dirname "$0")"
O=out/hook
mkdir -p out && rm -f $O.webm $O.log $O.ask.txt
. ./emurec.sh

vega run-app ../../app/build/aarch64-release/commentator_aarch64.vpkg >/dev/null 2>&1
sleep 8
vega device start-log-stream > $O.log 2>&1 & LP=$!
trap 'kill $LP 2>/dev/null' EXIT
sleep 2
vega device run-cmd -c "inputd-cli button_press KEY_ENTER" >/dev/null 2>&1   # Rookie
until grep -aq 'talk session code=' $O.log; do sleep 0.2; done
CODE=$(grep -a 'talk session code=' $O.log | tail -1 | sed -E 's/.*code=([A-Z2-7]{6}).*/\1/')
echo "code $CODE"
gt() { grep -a 'talk playhead' $O.log | tail -1 | sed -E 's/.* t=([0-9.]+).*/\1/'; }
until python3 -c "import sys; sys.exit(0 if float('$(gt)' or 0) >= 22 else 1)"; do sleep 0.2; done
erec_start "$PWD/$O.webm" "${HOOK_SECS:-45}"
until python3 -c "import sys; sys.exit(0 if float('$(gt)' or 0) >= 33 else 1)"; do sleep 0.2; done
N=$(grep -ac 'overlay closed' $O.log)
../../.venv/bin/python ask.py "$CODE" "Wait, why did they stop?" | tee $O.ask.txt
for _ in $(seq 200); do [ "$(grep -ac 'overlay closed' $O.log)" -gt "$N" ] && break; sleep 0.2; done   # answer spoken
sleep 3; erec_stop
echo "hook saved: $O.webm"
