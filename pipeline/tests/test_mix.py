import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix import build_mix_args  # noqa: E402

TRACKS = {"kid-en": [(1.4, "a.mp3")], "rookie-es": [(1.4, "b.mp3"), (5.0, "c.mp3")]}


def test_multitrack_args():
    args = build_mix_args("in.mp4", TRACKS, "out.mp4")
    assert all(isinstance(a, str) for a in args) and args[0] == "ffmpeg"
    assert args.count("-map") == 1 + len(TRACKS)
    assert args.count("-i") == 4
    assert args[args.index("-movflags") + 1] == "+faststart" and args[-1] == "out.mp4"
    graph = args[args.index("-filter_complex") + 1]
    assert graph.count("sidechaincompress") == 2 and "adelay=5000:all=1" in graph and "normalize=0" in graph
    assert "title=rookie-es" in args and "language=spa" in args
    assert args[args.index("-c:v") + 1] == "copy"


def test_single_track_and_silent_track():
    args = build_mix_args("in.mp4", {"kid-en": []}, "out.mp4")
    assert args.count("-map") == 2 and args.count("-i") == 1
    assert "sidechaincompress" not in args[args.index("-filter_complex") + 1]
