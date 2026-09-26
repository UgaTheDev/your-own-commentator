"""Polly TTS for every written line, then schedule lines so no track talks over itself.

python pipeline/voice.py <clip_id>  ->  data/<clip>/voiced.json
"""
import subprocess
import sys
from collections import Counter

from common import aws, cache_path, clip_dir, load, save

LANG = {"en": "en-US", "es": "es-US", "hi": "hi-IN", "zh": "cmn-CN"}
LEAD = 0.4  # seconds between the play and the call


def schedule(lines, event_times):
    """lines: [{trackId,eventId,t,priority,text,audio,duration}]. Returns (kept, dropped).

    A line starts at t+LEAD. On overlap with the previous kept line the lower priority loses
    (tie: the earlier stays). A line that runs past the next event (+LEAD) when that event has
    no line of its own on the track is dropped outright.
    """
    times = sorted(set(event_times))
    by_track = {}
    for line in sorted(lines, key=lambda x: x["t"]):
        by_track.setdefault(line["trackId"], []).append(line)
    kept, dropped = [], []
    for track in by_track.values():
        voiced_at = {x["t"] for x in track}
        out = []
        for line in track:
            start, end = line["t"] + LEAD, line["t"] + LEAD + line["duration"]
            nxt = next((t for t in times if t > line["t"]), None)
            # ponytail: a voiced next event is left to the overlap check below, where priority decides
            if nxt is not None and nxt not in voiced_at and end > nxt + LEAD:
                dropped.append(line)
                continue
            if out and start < out[-1]["_end"]:
                if line["priority"] > out[-1]["priority"]:
                    dropped.append(out.pop())
                else:
                    dropped.append(line)
                    continue
            out.append({**line, "_start": start, "_end": end})
        kept += out
    kept.sort(key=lambda x: (x["_start"], x["trackId"]))
    return [{"trackId": x["trackId"], "eventId": x["eventId"], "start": round(x["_start"], 3),
             "duration": x["duration"], "text": x["text"], "audio": x["audio"]} for x in kept], dropped


def synth(line):
    p = cache_path("polly", {k: line[k] for k in ("text", "voice", "engine", "lang")}, "mp3")
    if not p.exists():
        r = aws("polly").synthesize_speech(
            Text=line["text"], TextType="text", OutputFormat="mp3", VoiceId=line["voice"],
            Engine=line["engine"], LanguageCode=LANG.get(line["lang"], line["lang"]))
        tmp = p.with_suffix(".part")
        tmp.write_bytes(r["AudioStream"].read())
        tmp.replace(p)  # never cache a half-written mp3
    return p


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout)


def main(clip_id):
    d = clip_dir(clip_id)
    lines = []
    for line in load(d / "lines.json"):
        p = synth(line)
        lines.append({**line, "audio": str(p), "duration": round(duration(p), 3)})
    event_times = [e["t"] for e in load(d / "events.reviewed.json")]
    kept, dropped = schedule(lines, event_times)
    save(d / "voiced.json", kept)
    total = Counter(x["trackId"] for x in lines)
    lost = Counter(x["trackId"] for x in dropped)
    for tid in sorted(total):
        print(f"{tid}: kept {total[tid] - lost[tid]}/{total[tid]}, dropped {lost[tid]}")


if __name__ == "__main__":
    main(sys.argv[1])
