"""Mix each commentary track into the game audio, ducking the crowd under every line.

python pipeline/mix.py <clip_id> [--mode pertrack|multitrack]
  pertrack   (default, always works) data/<clip>/render/<trackId>.mp4
  multitrack                         data/<clip>/render/multi.mp4, one audio stream per track
"""
import argparse
import subprocess

from common import ROOT, clip_dir, load

ISO639_2 = {"en": "eng", "es": "spa", "hi": "hin", "zh": "zho"}


def lang_of(track_id):
    return track_id.rsplit("-", 1)[-1]


def build_mix_args(video, tracks, out, bed=None, duration=None):
    """tracks: {trackId: [(start_seconds, audio_path), ...]} in output stream order.
    bed: optional ambience file that replaces the game audio (looped, trimmed to `duration`), for
    footage whose own audio can't be used (e.g. it has a human commentator baked in).
    Returns one ffmpeg argv writing `out` with the copied video plus one mixed audio stream per track."""
    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video)]
    tids = list(tracks)
    game = "[0:a]"
    n = 1
    graph = []
    if bed:
        args += ["-stream_loop", "-1", "-i", str(bed)]
        graph.append(f"[1:a]atrim=duration={duration},asetpts=N/SR/TB,volume=0.6,aresample=48000[bed]")
        game, n = "[bed]", 2
    graph.append(f"{game}asplit={len(tids)}" + "".join(f"[g{k}]" for k in range(len(tids))) if len(tids) > 1
                 else f"{game}anull[g0]")
    for k, tid in enumerate(tids):
        clips = tracks[tid]
        if not clips:
            graph.append(f"[g{k}]anull[a{k}]")
            continue
        for j, (start, audio) in enumerate(clips):
            args += ["-i", str(audio)]
            graph.append(f"[{n}:a]adelay={round(start * 1000)}:all=1[c{k}_{j}]")
            n += 1
        inputs = "".join(f"[c{k}_{j}]" for j in range(len(clips)))
        graph += [
            f"{inputs}amix=inputs={len(clips)}:normalize=0,loudnorm=I=-16:TP=-1.5,aresample=48000,apad,asplit[sc{k}][v{k}]",
            f"[g{k}][sc{k}]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[d{k}]",
            f"[d{k}][v{k}]amix=inputs=2:normalize=0:duration=first[a{k}]",
        ]
    args += ["-filter_complex", ";".join(graph), "-map", "0:v"]
    for k in range(len(tids)):
        args += ["-map", f"[a{k}]"]
    args += ["-c:v", "copy", "-c:a", "aac", "-b:a", "160k"]
    for k, tid in enumerate(tids):
        args += [f"-metadata:s:a:{k}", f"language={ISO639_2.get(lang_of(tid), 'und')}",
                 f"-metadata:s:a:{k}", f"title={tid}", f"-disposition:a:{k}", "default" if k == 0 else "0"]
    return args + ["-movflags", "+faststart", str(out)]


def duration_of(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def mix(video, voiced, render_dir, mode="pertrack", bed=None):
    tracks = {}
    for x in sorted(voiced, key=lambda x: x["start"]):
        tracks.setdefault(x["trackId"], []).append((x["start"], x["audio"]))
    tracks = dict(sorted(tracks.items()))  # publish.py relies on this order for audioTrackIndex
    render_dir.mkdir(parents=True, exist_ok=True)
    jobs = [({tid: clips}, render_dir / f"{tid}.mp4") for tid, clips in tracks.items()] if mode == "pertrack" \
        else [(tracks, render_dir / "multi.mp4")]
    for t, out in jobs:
        subprocess.run(build_mix_args(video, t, out, bed, duration_of(video) if bed else None), check=True)
        print(out)
    return [out for _, out in jobs]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip_id")
    ap.add_argument("--mode", choices=["pertrack", "multitrack"], default="pertrack")
    a = ap.parse_args()
    d = clip_dir(a.clip_id)
    bed = load(d / "clip.json").get("audioBed")  # path relative to repo root
    mix(d / "source.mp4", load(d / "voiced.json"), d / "render", a.mode, ROOT / bed if bed else None)
