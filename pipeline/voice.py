"""Polly TTS for every written line, then schedule lines so no track talks over itself.

python pipeline/voice.py <clip_id>  ->  data/<clip>/voiced.json
"""
import subprocess
import sys
from collections import Counter

from common import aws, cache_path, clip_dir, load, save

LANG = {"en": "en-US", "es": "es-US", "hi": "hi-IN", "zh": "cmn-CN"}
LEAD = 0.4  # seconds between the play and the call
GAP = 0.25  # booth: pause between the pbp call and the analyst's reaction


def schedule(lines, event_times):
    """lines: [{trackId,eventId,t,priority,text,audio,duration,role?}]. Returns (kept, dropped).

    A line starts at t+LEAD. An analyst line (booth) starts GAP after its own pbp line ends and is
    dropped if that pbp line was. On overlap with the previous kept line the lower priority loses
    (tie: the earlier stays). A line that runs past the next event (+LEAD) when that event has
    no line of its own on the track is dropped outright.
    """
    times = sorted(set(event_times))
    by_track = {}
    for line in sorted(lines, key=lambda x: (x["t"], x.get("role") == "analyst")):
        by_track.setdefault(line["trackId"], []).append(line)
    kept, dropped = [], []
    for track in by_track.values():
        voiced_at = {x["t"] for x in track if x.get("role") != "analyst"}
        out = []
        for line in track:
            start = line["t"] + LEAD
            if line.get("role") == "analyst":
                pbp = next((x for x in out if x["eventId"] == line["eventId"] and x.get("role") == "pbp"), None)
                if pbp is None:
                    dropped.append(line)
                    continue
                start = pbp["_end"] + GAP
            end = start + line["duration"]
            nxt = next((t for t in times if t > line["t"]), None)
            # ponytail: a voiced next event is left to the overlap check below, where priority decides
            if nxt is not None and nxt not in voiced_at and end > nxt + LEAD:
                dropped.append(line)
                continue
            while out and start < out[-1]["_end"]:
                if line["priority"] > out[-1]["priority"]:
                    dropped.append(out.pop())
                else:
                    dropped.append(line)
                    break
            else:
                out.append({**line, "_start": start, "_end": end})
        kept += out
    kept.sort(key=lambda x: (x["_start"], x["trackId"]))
    return [{"trackId": x["trackId"], "eventId": x["eventId"], "start": round(x["_start"], 3),
             "duration": x["duration"], "text": x["text"], "audio": x["audio"],
             **({"role": x["role"]} if "role" in x else {})} for x in kept], dropped


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


def voiced(line):
    p = synth(line)
    return {**line, "audio": str(p), "duration": round(duration(p), 3)}


def main(clip_id):
    d = clip_dir(clip_id)
    lines = []
    booth = d / "lines.booth.json"  # booth.py output, voiced alongside the single-voice tracks
    for line in load(d / "lines.json") + (load(booth) if booth.exists() else []):
        lines.append(voiced(line))
    event_times = [e["t"] for e in load(d / "events.reviewed.json")]
    kept, dropped = schedule(lines, event_times)
    save(d / "voiced.json", kept)
    total = Counter(x["trackId"] for x in lines)
    lost = Counter(x["trackId"] for x in dropped)
    for tid in sorted(total):
        print(f"{tid}: kept {total[tid] - lost[tid]}/{total[tid]}, dropped {lost[tid]}")


if __name__ == "__main__":
    main(sys.argv[1])
