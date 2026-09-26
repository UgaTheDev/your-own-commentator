"""Scoring events from the broadcast's on-screen score bug.

Nova's video guesses for baskets are unreliable (it hallucinates periodic makes), but the
score bug is ground truth that changes exactly when points go up. We watch a crop of the bug
for pixel changes and have Nova read the digits only at those moments (an image, not video).

clip.json: "scoreBug": {"crop": "<ffmpeg crop w:h:x:y>", "labels": {"Hazen": "pink", "Guest": "blue"}}
"""
import json
import subprocess

import common

W, H = 48, 16  # tiny grayscale thumbnails are enough to see a digit change
CHANGE = 6.0  # mean abs pixel diff (0-255) that counts as a change
LAG = 1.5  # ponytail: seconds the bug operator lags the basket; review fixes exact times
POINTS_TO_TYPE = {1: "ft_made", 2: "made_2", 3: "made_3"}


def thumbnails(video, crop, fps=1):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps},crop={crop},scale={W}:{H},format=gray",
         "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return [raw[i:i + W * H] for i in range(0, len(raw) - W * H + 1, W * H)]


def change_points(frames, threshold=CHANGE):
    """Indices where a frame differs from the last stable frame; index 0 is always included."""
    if not frames:
        return []
    out, ref = [0], frames[0]
    for i, f in enumerate(frames[1:], 1):
        if sum(abs(a - b) for a, b in zip(f, ref)) / len(f) > threshold:
            out.append(i)
            ref = f
    return out


def read_score(video, t, crop, labels):
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1",
                          "-vf", f"crop={crop}", "-f", "image2", "-c:v", "png", "-"],
                         capture_output=True, check=True).stdout
    names = list(labels)
    reply = common.converse(
        "extract", f"This is a basketball score graphic. Read the score for {names}. "
                   f'Reply with JSON only, e.g. {json.dumps({n: 0 for n in names})}.',
        content=[{"image": {"format": "png", "source": {"bytes": png}}}], max_tokens=100, temperature=0)
    score = common.parse_json(reply)
    return {labels[n]: int(score[n]) for n in names}


def score_events(timeline):
    """timeline: [(t, {team: points})] in time order -> scoring events. Implausible jumps are skipped."""
    events, warnings = [], []
    for (t0, s0), (t1, s1) in zip(timeline, timeline[1:]):
        for team in s1:
            d = s1[team] - s0[team]
            if d in POINTS_TO_TYPE:
                events.append({"t": max(0.0, t1 - LAG), "type": POINTS_TO_TYPE[d], "team": team, "jersey": None,
                               "confidence": 1.0, "source": "scoreboard"})
            elif d:
                warnings.append(f"{t1:.0f}s {team} {s0[team]}->{s1[team]}: not a single basket, check in review")
    return events, warnings


def extract_scores(video, bug):
    frames = thumbnails(video, bug["crop"])
    # read 1s after the change so the graphic has finished animating
    points = [0] + [i + 1 for i in change_points(frames)[1:] if i + 1 < len(frames)]
    timeline = []
    for i in points:
        s = read_score(video, i, bug["crop"], bug["labels"])
        if not timeline or plausible(timeline[-1][1], s):
            if not timeline or s != timeline[-1][1]:
                timeline.append((float(i), s))
    return timeline


def plausible(last, s):
    """Scores never go down, and one reading step adds at most one basket per team. Anything else is a misread
    (Nova reads "17" as "7" when players pass behind the graphic) or an end-of-clip transition."""
    return all(0 <= s[t] - last[t] <= 3 for t in last)


def drop_periodic(events, min_run=3, jitter=0.3, max_gap=4.0):
    """Drop runs of >= min_run same-type events at a near-constant spacing: a looping model, not a game."""
    bad = set()
    by_type = {}
    for e in sorted(events, key=lambda e: e["t"]):
        by_type.setdefault(e["type"], []).append(e)
    for seq in by_type.values():
        i = 0
        while i < len(seq) - 1:
            gap = seq[i + 1]["t"] - seq[i]["t"]
            j = i + 1
            while j + 1 < len(seq) and abs((seq[j + 1]["t"] - seq[j]["t"]) - gap) <= jitter and gap <= max_gap:
                j += 1
            if j - i + 1 >= min_run and gap <= max_gap:
                bad.update(id(e) for e in seq[i:j + 1])
                i = j + 1
            else:
                i += 1
    return [e for e in events if id(e) not in bad]
