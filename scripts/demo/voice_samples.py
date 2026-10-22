"""Audition every lifelike en-US Polly narrator: one file per voice + engine, and one reel that announces each.

  .venv/bin/python scripts/demo/voice_samples.py   ->  scripts/demo/out/vo-samples/{reel.mp3, <Voice>-<engine>.mp3}
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline.common import aws  # noqa: E402

TEXT = ("Never watched basketball? Just ask your TV. "
        "This is Your Own Commentator on Fire TV. Pick a game, then pick your commentator.")
OUT = Path(__file__).resolve().parent / "out" / "vo-samples"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    polly, parts = aws("polly"), []
    for engine in ("long-form", "generative"):
        for v in polly.describe_voices(Engine=engine, LanguageCode="en-US")["Voices"]:
            name = f"{v['Id']}-{engine}"
            for label, text in ((f"{name}-label", f"{v['Id']}, {engine.replace('-', ' ')}."), (name, TEXT)):
                mp3 = OUT / f"{label}.mp3"
                r = polly.synthesize_speech(Text=text, VoiceId=v["Id"], Engine=engine, OutputFormat="mp3",
                                            SampleRate="24000")
                mp3.write_bytes(r["AudioStream"].read())
                parts.append(mp3)
            print(name)
    lst = OUT / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    OUT / "reel.mp3"], check=True)
    print(OUT / "reel.mp3")


if __name__ == "__main__":
    main()
