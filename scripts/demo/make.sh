#!/usr/bin/env bash
# Take -> cut -> assemble -> QA. A take whose playback froze (VVD decoder falling behind) is re-shot, up to 3 times.
set -uo pipefail
cd "$(dirname "$0")/../.."
PY=.venv/bin/python
for try in 1 2 3; do
  bash scripts/demo/take.sh > scripts/demo/out/take.run.txt 2>&1
  frozen=$($PY -c "
import sys; sys.path.insert(0, 'scripts/demo'); import qa
from pathlib import Path
print(round(sum(e - s for s, e in qa.stalls(qa.events(Path('scripts/demo/out/take.log')))), 1))")
  echo "take $try: playback froze ${frozen}s in total"
  python3 -c "import sys; sys.exit(0 if $frozen <= 3 else 1)" && break
  [ "$try" = 3 ] && { echo "the VVD kept freezing; close heavy apps and rerun"; exit 1; }
  sleep 20   # let the VVD settle before the re-shoot
done
python3 scripts/demo/cut.py && $PY scripts/demo/assemble.py --segments scripts/demo/edl.json | tail -2 && $PY scripts/demo/qa.py
