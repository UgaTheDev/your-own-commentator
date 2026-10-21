"""Cut the edit decision list into demo.mp4: 1920x1080 30 fps H.264 + AAC, narration over ducked game audio.

  assemble.py --segments scripts/demo/edl.example.json

EDL: {"out", "vo_dir", "screen", "audio", "segments": [{"type": "card"|"screen", "file", "in", "out",
"vo": [[line_id, offset_s], ...]}]}. A screen segment's `file`/`audio` default to the top-level `screen`
(the silent recording) and `audio` (soundtrack.py's wav for that recording); both are cut at the same in/out.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

MAX_S = 180
DUCK = 0.06  # one voice at a time: the commentator is all but muted under narration
V = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30"]
A = ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
FIT = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
       "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0b0f1a,fps=30,setsar=1")


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def plan(edl, durations):
    """Absolute narration placements [(line_id, start, end)] and the total length."""
    t, vo = 0.0, []
    for seg in edl["segments"]:
        for line_id, offset in seg.get("vo", []):
            vo.append((line_id, t + offset, t + offset + durations[line_id]))
        t += seg["out"] - seg["in"]
    return vo, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments", required=True)
    edl = json.loads(Path(ap.parse_args().segments).read_text())
    vo_dir = Path(edl["vo_dir"])
    durations = json.loads((vo_dir / "durations.json").read_text())
    vo, total = plan(edl, durations)
    assert total < MAX_S, f"video is {total:.1f}s, the limit is under {MAX_S}s"
    for (a, _, a_end), (b, b_start, _) in zip(vo, vo[1:]):
        if b_start < a_end:
            print(f"warning: narration {b} starts {a_end - b_start:.1f}s before {a} ends")
    if vo and vo[-1][2] > total:
        print(f"warning: narration {vo[-1][0]} runs {vo[-1][2] - total:.1f}s past the end")

    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, seg in enumerate(edl["segments"]):
            part, dur = Path(tmp) / f"{i:02}.mkv", seg["out"] - seg["in"]
            if seg["type"] == "card":
                ff("-loop", "1", "-framerate", 30, "-t", dur, "-i", seg["file"],
                   "-f", "lavfi", "-t", dur, "-i", "anullsrc=r=48000:cl=stereo",
                   "-vf", FIT, *V, *A, "-t", dur, part)
            else:
                ff("-ss", seg["in"], "-t", dur, "-i", seg.get("file", edl.get("screen")),
                   "-ss", seg["in"], "-t", dur, "-i", seg.get("audio", edl.get("audio")),
                   "-map", "0:v", "-map", "1:a", "-vf", FIT, "-af", "apad", *V, *A, "-t", dur, part)
            parts.append(part)
        lst = Path(tmp) / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        joined = Path(tmp) / "joined.mkv"
        ff("-f", "concat", "-safe", 0, "-i", lst, "-c", "copy", joined)

        ins, mix = ["-i", joined], []
        for k, (line_id, start, _) in enumerate(vo, 1):
            ins += ["-i", vo_dir / f"{line_id}.wav"]
            ms = int(start * 1000)
            mix.append(f"[{k}:a]adelay={ms}|{ms}[v{k}]")
        duck = "+".join(f"between(t,{s:.2f},{e:.2f})" for _, s, e in vo) or "0"
        graph = ";".join([f"[0:a]volume={DUCK}:enable='{duck}'[g]", *mix,
                          "[g]" + "".join(f"[v{k}]" for k in range(1, len(vo) + 1))
                          + f"amix=inputs={len(vo) + 1}:duration=first:normalize=0[a]"])
        out = Path(edl["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        ff(*ins, "-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", total, out)
    got = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(out)], capture_output=True, text=True, check=True).stdout)
    assert got < MAX_S, f"{out} is {got:.1f}s"
    print(f"wrote {out} ({got:.1f}s)")


if __name__ == "__main__":
    main()
