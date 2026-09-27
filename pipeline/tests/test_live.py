import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import live  # noqa: E402

A, B, C = bytes([10] * 32), bytes([120] * 32), bytes([240] * 32)
RULES = {"made_3": {"title": "Three-pointer", "body": "Worth 3 points."}}


def test_chunk_scheduling():
    assert [live.chunk_due(i, 100.0) for i in range(3)] == [105.0, 110.0, 115.0]
    assert live.chunk_due(1, 100.0, speed=4) == 102.5
    assert live.aired_at(63.0, 100.0, start=60.0, speed=2) == 101.5


class FakeVideo:
    """Score graphic frames at 2 fps: A until 12 s, B from 12 s (score changes), C from 23.5 s; `scores` by read time."""

    def __init__(self, scores):
        self.scores, self.reads = scores, []

    def frame(self, t):
        return A if t < 12 else B if t < 23.5 else C

    def thumbs(self, t0, dur):
        return [self.frame(t0 + k / 2) for k in range(int(dur * 2))]

    def read(self, t):
        self.reads.append(t)
        return next(s for until, s in self.scores if t < until)


def test_reader_emits_only_aired_score_changes_across_chunks():
    v = FakeVideo([(13, {"pink": 11, "blue": 2}), (24.5, {"pink": 11, "blue": 5}), (99, {"pink": 11, "blue": 6})])
    r = live.Reader(v.thumbs, v.read)
    assert r.process(0, 5) == [] and r.process(5, 10) == []
    assert r.process(10, 15)[0][0]["type"] == "made_3"  # change at 12 s, read at 13 s: same chunk
    out = r.process(20, 25)  # change at 23.5 s, read due at 24.5 s < 25
    (e, tc), = out
    assert (e["type"], e["team"], e["id"], tc, e["state"]) == ("ft_made", "blue", "live2", 23.5, {"pink": 11, "blue": 6})
    assert e["source"] == "scoreboard" and e["t"] == 24.5 - live.scoreboard.LAG
    assert v.reads == [0, 13.0, 24.5]  # a baseline read, then one read per change; none into the future


def test_reader_defers_a_read_into_the_next_chunk_and_ignores_misreads():
    v = FakeVideo([(12.5, {"pink": 11, "blue": 2}), (99, {"pink": 1, "blue": 2})])  # "11" misread as "1"
    r = live.Reader(lambda t0, dur: [v.frame(t0 + k / 2) for k in range(int(dur * 2))], v.read)
    r.process(0, 5)
    r.process(5, 10)
    v.frame = lambda t: A if t < 14.5 else B  # change at 14.5 s: its read (15.5 s) is in the next chunk
    assert r.process(10, 15) == [] and r.pending == [[14.5, 15.5]]
    assert r.process(15, 20) == [] and r.warnings and r.score == {"pink": 11, "blue": 2}


def test_live_facts_are_score_graphic_only():
    e = {"id": "live1", "t": 61.5, "type": "made_3", "team": "blue", "jersey": None, "confidence": 1.0,
         "source": "scoreboard", "status": "proposed", "state": {"pink": 11, "blue": 5}}
    assert live.live_facts(e, RULES) == {
        "event": {"id": "live1", "t": 61.5, "type": "made_3", "team": "blue", "jersey": None},
        "state": {"score": {"pink": 11, "blue": 5}}, "rule": RULES["made_3"]}
    assert "rule" not in live.live_facts({**e, "type": "made_2"}, RULES)


def test_cue_message_shape():
    msg = live.cue({"t": 61.5}, "Blue hits a three!", "https://cdn/x/live/a.mp3")
    assert msg == {"type": "cue", "t": 61.5, "text": "Blue hits a three!", "audioUrl": "https://cdn/x/live/a.mp3",
                   "label": "live replay"}
    assert "live replay" not in msg["text"]  # the label is metadata, never spoken


def test_narrate_speaks_only_gated_lines(monkeypatch, tmp_path):
    e = {"id": "live1", "t": 61.5, "type": "made_3", "team": "blue", "jersey": None, "state": {"pink": 11, "blue": 5}}
    facts = live.live_facts(e, RULES)
    persona = {"lang": "en", "voice": "Matthew", "engine": "neural", "style": "calm"}
    uploads = []
    monkeypatch.setattr(live.voice, "synth", lambda line: tmp_path / "a.mp3")
    monkeypatch.setattr(live, "upload", lambda mp3, clip, name: uploads.append(name) or f"https://cdn/{clip}/live/{name}")
    monkeypatch.setattr(live.write, "gate", lambda prompt, f: ("Blue hits a three, 5 to 11.", None))
    msg, reason = live.narrate("dev", e, facts, persona)
    assert reason is None and msg["audioUrl"].startswith("https://cdn/dev/live/live1-") and msg["label"] == "live replay"
    monkeypatch.setattr(live.write, "gate", lambda prompt, f: ("Number 23 scores!", "numbers not in facts: ['23']"))
    assert live.narrate("dev", e, facts, persona) == (None, "numbers not in facts: ['23']") and len(uploads) == 1


def test_pct():
    assert live.pct([], 50) is None
    assert live.pct([3, 1, 2], 50) == 2 and live.pct(list(range(1, 21)), 95) == 19
