# Demo video pipeline (run from the repo root)
1. Cards and narration (Polly, needs `aws login`): `.venv/bin/python scripts/demo/cards.py && .venv/bin/python scripts/demo/voiceover.py --out-dir scripts/demo/out/vo`
2. Find the VVD window's capture rectangle (captured pixels, 2x points on Retina), app open on Home.
3. Record (silent screen + app log + scripted keys): `scripts/demo/record.sh X Y W H scripts/demo/out/take scripts/demo/keys.demo.txt`
4. Rebuild its audio from the log: `.venv/bin/python scripts/demo/soundtrack.py --log scripts/demo/out/take.log --start-ms $(cat scripts/demo/out/take.start_ms) --duration $(ffprobe -v error -show_entries format=duration -of csv=p=0 scripts/demo/out/take.mp4) --manifest https://d2og06dnam3owj.cloudfront.net/lake-region/manifest.json --out scripts/demo/out/take.wav`
5. Check sync: `ffplay` the take with the wav (`ffmpeg -i take.mp4 -i take.wav -c:v copy -shortest check.mp4`); if the audio lags by N ms, rerun 4 with `--start-ms` + N.
6. Hook take (phone talk-back): repeat 3–5 with prefix `scripts/demo/out/hook` and a keys file containing only `20 STOP`.
7. Retime `scripts/demo/edl.example.json` against the takes, then: `.venv/bin/python scripts/demo/assemble.py --segments scripts/demo/edl.example.json`
8. Tests: `.venv/bin/python -m pytest scripts/demo/test_demo.py`
Output: `scripts/demo/out/demo.mp4` (1920x1080 30 fps, H.264 + AAC, asserted under 3:00). `out/` is gitignored.
