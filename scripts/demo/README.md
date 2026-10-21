# Demo video pipeline (run from the repo root)
1. Cards and narration (Polly, needs `aws login`): `.venv/bin/python scripts/demo/cards.py && .venv/bin/python scripts/demo/voiceover.py --out-dir scripts/demo/out/vo`
2. VVD running, relay scaled to 1 (services/talk/deploy.md). Other windows may cover the VVD: `emurec.sh` records the
   device's own display and audio through the emulator console (`screenrecord`, 1920x1080, max 180 s per file).
   Window capture (`winrec.swift`) dropped below 1 fps whenever the window was covered.
3. Main take, keys timed to the game clock in the app log: `bash scripts/demo/take.sh` → `out/take-a.webm`, `out/take-b.webm`, `out/take.marks`
4. Hook take (a Polly viewer asks through the phone relay): `bash scripts/demo/hook.sh` → `out/hook.webm`
5. Cut: `.venv/bin/python scripts/demo/assemble.py --segments scripts/demo/edl.json` (screen segments set `file`; the
   webm carries its own audio, so `audio` is the same file)
6. Tests: `.venv/bin/python -m pytest scripts/demo/test_demo.py`
Output: `scripts/demo/out/demo.mp4` (1920x1080 30 fps, H.264 + AAC, asserted under 3:00). `out/` is gitignored.
