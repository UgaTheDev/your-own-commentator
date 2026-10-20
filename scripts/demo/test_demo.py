"""Timeline logic of soundtrack.py on a synthetic log. Run: .venv/bin/python -m pytest scripts/demo/test_demo.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from soundtrack import parse, timeline  # noqa: E402

T0 = 1_000_000
TRACKS = {"rookie-en": "R.mp4", "kid-en": "K.mp4"}
LOG = """
noise line without the prefix
W YOC: @1000000 play rookie-en
W YOC: @1000000 play rookie-en
W YOC: @1010000 seek 25
W YOC: @1020000 why e2 at t=35.00 questions=2
W YOC: @1021000 why answer "Why did they get a free shot?" -> A.mp3
W YOC: @1021500 why audio playing after 500ms
W YOC: @1021500 why audio playing after 500ms
W YOC: @1030000 overlay closed (why ended after 9000ms), resume t=35.00
W YOC: @1040000 switch to kid-en at t=45.00
W YOC: @1041000 seeked kid-en t=45.00 at=45.00 after 1000ms
W YOC: @1050000 replay e3 at t=54.00 -> RE3.mp4
W YOC: @1050500 playing replay e3 t=0.00 at=0.00 after 500ms
W YOC: @1062000 seeked replay back kid-en t=54.00 at=54.00 after 600ms
W YOC: @1070000 recap t=60 at t=62.00 -> REC.mp3
W YOC: @1075000 back
W YOC: @1075000 overlay closed (back), resume t=62.00
W YOC: @1080000 talk answer queued until replay ends "x"
W YOC: @1085000 back
"""


def test_timeline():
    ev = parse(LOG.splitlines())
    assert len(ev) == 16  # duplicates and noise dropped
    got = [(s["kind"], s["start"], s["end"], s["src"], s["offset"]) for s in timeline(ev, T0, TRACKS)]
    assert got == [
        ("game", 0.0, 10.0, "R.mp4", 0.0),
        ("game", 10.0, 20.0, "R.mp4", 25.0),  # seek
        ("game", 30.0, 40.0, "R.mp4", 35.0),  # resumed after the Why card; silent while loading kid-en
        ("game", 41.0, 50.0, "K.mp4", 45.0),
        ("game", 62.0, 70.0, "K.mp4", 54.0),  # back from the replay at the saved time
        ("game", 75.0, 85.0, "K.mp4", 62.0),  # recap closed by Back, then Back leaves the Player
        ("clip", 21.5, 30.0, "A.mp3", 0.0),  # starts when the audio actually played
        ("clip", 50.5, 62.0, "RE3.mp4", 0.0),
        ("clip", 70.0, 75.0, "REC.mp3", 0.0),
    ]


def test_starts_before_recording():
    ev = parse(["YOC: @1000000 play rookie-en"])
    (s,) = timeline(ev, T0 + 5000, TRACKS)
    assert s["start"] == -5.0 and s["offset"] == 0.0  # render() shifts it to offset 5 at time 0
