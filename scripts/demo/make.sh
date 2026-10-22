#!/usr/bin/env bash
# Take -> cut -> assemble -> QA. A take that fails, hangs (10 min watchdog) or froze (VVD decoder falling behind)
# is re-shot, up to 3 times; a VVD that stopped answering is restarted first.
set -uo pipefail
cd "$(dirname "$0")/../.."
PY=.venv/bin/python
ok=
for try in 1 2 3; do
  if ! perl -e 'alarm 600; exec @ARGV' bash scripts/demo/take.sh > scripts/demo/out/take.run.txt 2>&1; then
    echo "take $try failed: $(grep "TAKE FAILED" scripts/demo/out/take.run.txt || echo 'watchdog')"
    pkill -f "device start-log-stream"
    if ! perl -e 'alarm 20; exec @ARGV' vega device run-cmd -c true >/dev/null 2>&1; then
      echo "VVD not answering: restarting it"; vega virtual-device stop >/dev/null 2>&1; vega virtual-device start >/dev/null 2>&1
    fi
    sleep 20; continue
  fi
  frozen=$($PY -c "
import sys; sys.path.insert(0, 'scripts/demo'); import qa
from pathlib import Path
print(round(sum(e - s for s, e in qa.stalls(qa.events(Path('scripts/demo/out/take.log')))), 1))")
  echo "take $try: playback froze ${frozen}s in total"
  if python3 -c "import sys; sys.exit(0 if $frozen <= 3 else 1)"; then ok=1; break; fi
  sleep 20   # let the VVD settle before the re-shoot
done
[ -n "$ok" ] || { echo "no usable take after 3 tries"; exit 1; }
python3 scripts/demo/cut.py && $PY scripts/demo/assemble.py --segments scripts/demo/edl.json | tail -2 && $PY scripts/demo/qa.py
