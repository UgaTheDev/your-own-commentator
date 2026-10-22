"""Build edl.json from the takes: every cut point comes from the app log (out/take.log) and the part start times in
out/take.marks, so a re-take re-cuts itself. Narration is placed where no commentator is speaking.

  python3 scripts/demo/cut.py && .venv/bin/python scripts/demo/assemble.py --segments scripts/demo/edl.json
"""
import json
import re
import subprocess
from pathlib import Path

D = Path(__file__).resolve().parent
OUT = D / "out"
EV = re.compile(r"YOC: @(\d+) (.*)")


def events(log=OUT / "take.log"):
    return [(int(m.group(1)) / 1000, m.group(2)) for m in map(EV.search, log.read_text(errors="replace").splitlines())
            if m]


def parts():
    """{part: (t0 epoch, webm)} from 'part a t0=...' marks."""
    return {m.group(1): (float(m.group(2)), OUT / f"take-{m.group(1)}.webm")
            for m in re.finditer(r"part (\w) t0=([\d.]+)", (OUT / "take.marks").read_text())}


def black_ends(webm):
    err = subprocess.run(["ffmpeg", "-i", webm, "-vf", "crop=iw:ih*0.5:0:ih*0.2,blackdetect=d=0.5:pix_th=0.08",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"black_end:([\d.]+)", err)]


def calibrate(evs, t0, webm):
    """Recorder start lag: a switch's 'seeked' log line lands when its black gap ends on screen."""
    seeked = [t - t0 for t, msg in evs if msg.startswith("seeked ") and "replay" not in msg and "highlights" not in msg]
    lags = [s - b for s in seeked for b in black_ends(webm) if 0 <= s - b < 2.5]
    return sorted(lags)[len(lags) // 2] if lags else 0.8


def main():
    evs, ps = events(), parts()
    cal = {p: (t0, webm, calibrate(evs, t0, webm)) for p, (t0, webm) in ps.items()}

    def at(epoch):  # (file, seconds in it) for a log time
        p = max((p for p in cal if cal[p][0] <= epoch), key=lambda p: cal[p][0])
        t0, webm, lag = cal[p]
        return webm, epoch - t0 - lag

    def first(pat, after=0.0, n=1):
        hits = [t for t, msg in evs if t > after and re.search(pat, msg)]
        return hits[n - 1]

    segs = []

    def shot(a, b, vo=None, **kw):  # a, b: log epochs, same part
        (fa, ta), (fb, tb) = at(a), at(b)
        assert fa == fb, f"segment crosses parts at {a}"
        segs.append({"type": "screen", "file": str(fa.relative_to(D.parents[1])), "in": round(max(ta, 0), 2),
                     "out": round(tb, 2), **({"vo": vo} if vo else {}), **kw})

    def card(name, secs, vo=None):
        segs.append({"type": "card", "file": f"scripts/demo/out/cards/{name}.png", "in": 0, "out": secs,
                     **({"vo": vo} if vo else {})})

    # Hook: the viewer's question (Polly, as if from the phone) lands just before the TV answers at ~13.7 s.
    segs.append({"type": "screen", "file": "scripts/demo/out/hook.webm", "in": 6.0, "out": 21.0,
                 "vo": [["ask", 4.6]], "overlay": ["scripts/demo/out/cards/lowerthird.png", 4.2, 8.6]})
    card("title", 4.0, [["hook", 0.3]])
    t0a = cal["a"][0]
    marks = {name: float(t) for t, name in re.findall(r"^([\d.]+) (\w+)$", (OUT / "take.marks").read_text(), re.M)}
    shot(t0a + marks["home"] - 0.4, t0a + marks["rookie"] - 0.6, [["pick", 0.5]])
    e2 = first(r"^card e2 ")
    shot(e2 - 0.6, e2 + 6.0, [["rules", 0.3]])
    # Same play, four voices. Each pass: rewind + tray, then the call of the 98.0 s two-pointer.
    s1 = first(r"^score pink 13 ")
    shot(s1 - 7.0, s1 + 6.7, [["switch", 0.2]])  # narration ends before Rookie's line (+0.3 s, 6.2 s)
    after, lens = s1, {"kid-en": 4.4, "rookie-es": 6.5, "rookie-hi": 5.6}
    for tid, secs in lens.items():
        sw = first(rf"^switch to {tid} ", after)
        shot(max(first(r"^seek \d", after) + 0.3, sw - 2.5), sw)  # the tray, at most 2.5 s
        s = first(r"^score pink 13 ", sw)
        shot(s - 1.0, s + secs)
        after = s
    sw = first(r"^switch to booth-en ", after)
    shot(max(first(r"^seek \d", after) + 0.3, sw - 3.5), sw, [["booth", 0.2]])  # room for the narration
    s = first(r"^score pink 13 ", sw)
    shot(s - 1.0, first(r"^caption ANALYST", s) - 0.2)  # play-by-play only: the replay cuts the analyst off
    p = first(r"^playing replay ", s)
    shot(p + 0.2, p + 11.8, [["replay", 0.5]])
    why = first(r"^why e\d+ ")
    closed = first(r"^overlay closed \(why", why)
    shot(closed + 2.5, closed + 7.5)  # the minimap
    shot(why + 0.15, why + 5.5, [["why", 0.3]])  # after the press: the game pauses, so no stray end of a line
    shot(first(r"^why audio playing", why) - 1.0, closed + 0.6)
    rc = first(r"^recap t=")
    shot(rc - 3.0, first(r"^overlay closed \(recap", rc) + 0.5, [["catchup", 0.2]])
    h = first(r"^playing highlights")
    shot(h + 2.0, h + 12.0)  # end of the title card + the whole first replay and its line (reel.py: 4 s card, 8 s each)
    card("hood-pipeline", 13.2, [["hood", 0.5]])
    card("hood-numbers", 12.2, [["numbers", 0.4]])
    shot(e2 + 8.0, e2 + 15.0, [["close", 0.4]])  # Rookie is quiet between the free throw and the 3
    card("end", 4.0)
    edl = {"_note": "Generated by cut.py from out/take.log + out/take.marks; edit cut.py, not this file.",
           # epoch of second 0 of each recording, for qa.py; the hook take is aligned on its answer panel (13.6 s)
           "_bases": {**{str(w.relative_to(D.parents[1])): t0 + lag for t0, w, lag in cal.values()},
                      "scripts/demo/out/hook.webm": [t for t, m in events(OUT / "hook.log") if m.startswith("talk answer")][0] - 13.6},
           "out": "scripts/demo/out/demo.mp4", "vo_dir": "scripts/demo/out/vo", "segments": segs}
    (D / "edl.json").write_text(json.dumps(edl, indent=1) + "\n")
    print(f"{len(segs)} segments, {sum(x['out'] - x['in'] for x in segs):.1f}s, lag "
          + ", ".join(f"{p}={c[2]:.2f}" for p, c in cal.items()))


if __name__ == "__main__":
    main()
