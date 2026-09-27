"""Test questions without a mic: Polly -> 16 kHz mono s16le PCM (via ffmpeg, as the phone page will send).

python services/talk/make_questions.py <out_dir>  ->  <out_dir>/q1.pcm ... plus questions.json
"""
import json
import subprocess
import sys
from pathlib import Path

import boto3

QUESTIONS = ["Why is that worth three points?", "Who's winning?", "Wait, why did they stop?"]


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    polly = boto3.client("polly", region_name="us-east-1")
    for i, q in enumerate(QUESTIONS, 1):
        mp3 = polly.synthesize_speech(Text=q, OutputFormat="mp3", VoiceId="Joanna", Engine="neural")["AudioStream"].read()
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "pipe:0", "-f", "s16le", "-ar", "16000", "-ac", "1",
                        str(out / f"q{i}.pcm")], input=mp3, check=True)
    (out / "questions.json").write_text(json.dumps(QUESTIONS, indent=1))
    print(*(f"q{i}.pcm {(out / f'q{i}.pcm').stat().st_size}B  {q}" for i, q in enumerate(QUESTIONS, 1)), sep="\n")


if __name__ == "__main__":
    main(sys.argv[1])
