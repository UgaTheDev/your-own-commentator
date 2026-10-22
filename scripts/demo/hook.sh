#!/usr/bin/env bash
# Hook take: Rookie plays from the free-throw lineup (game 24 s); right after blue's free throw (+1 BLUE at 31 s) a
# viewer asks "why did blue just get a point?" through the
# phone relay (ask.py, a Polly voice), and the TV pauses and answers. Records the VVD display (emurec.sh) to out/hook.webm.
set -uo pipefail
cd "$(dirname "$0")"
O=out/hook
mkdir -p out && rm -f $O.webm $O.log $O.ask.txt $O.t0 $O.ask_at
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
# The app's 1 s clock; the talk heartbeat lags, which started this recording after the free throw.
gt() { grep -a 'tick t=' $O.log | tail -1 | sed -E 's/.* t=([0-9.]+).*/\1/'; }
until python3 -c "import sys; sys.exit(0 if float('$(gt)' or 0) >= 24 else 1)"; do sleep 0.2; done
python3 -c 'import time; print(time.time())' > $O.t0   # for cut.py / qa.py
erec_start "$PWD/$O.webm" "${HOOK_SECS:-45}"
until python3 -c "import sys; sys.exit(0 if float('$(gt)' or 0) >= 33 else 1)"; do sleep 0.2; done
N=$(grep -ac 'overlay closed' $O.log)
python3 -c 'import time; print(time.time())' > $O.ask_at   # the viewer starts speaking
../../.venv/bin/python ask.py "$CODE" "Wait, why did blue just get a point?" | tee $O.ask.txt
for _ in $(seq 200); do [ "$(grep -ac 'overlay closed' $O.log)" -gt "$N" ] && break; sleep 0.2; done   # answer spoken
sleep 3; erec_stop
echo "hook saved: $O.webm"
