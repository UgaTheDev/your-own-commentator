"""Amazon Polly narration for the demo: one 48 kHz stereo wav per line plus durations.json.

  voiceover.py --script scripts/demo/voiceover.json --out-dir scripts/demo/out/vo
"""
import argparse
import json
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.common import aws, cache_path, load, save  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default=str(Path(__file__).with_name("voiceover.json")))
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    script = load(a.script)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    durations = {}
    for line in script["lines"]:
        voice = line.get("voice", script["voice"])  # a line may override, e.g. the viewer asking the TV
        engine = line.get("engine", script.get("engine", "generative"))
        key = {"voice": voice, "engine": engine, "text": line["text"]}
        mp3 = cache_path("demo-vo", key, "mp3")  # re-runs cost nothing unless the text changes
        if not mp3.exists():
            r = aws("polly").synthesize_speech(Text=line["text"], VoiceId=voice, Engine=engine,
                                               OutputFormat="mp3", SampleRate="24000")
            mp3.write_bytes(r["AudioStream"].read())
        wav = out / f"{line['id']}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ac", "2", "-ar", "48000", str(wav)], check=True)
        with wave.open(str(wav)) as w:
            durations[line["id"]] = round(w.getnframes() / w.getframerate(), 2)
    save(out / "durations.json", durations)
    print(json.dumps(durations), f"total {sum(durations.values()):.1f}s")


if __name__ == "__main__":
    main()
