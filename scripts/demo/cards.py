"""1920x1080 PNG cards for the demo: title, under-the-hood pipeline and numbers, end card.

  cards.py --out-dir scripts/demo/out/cards

ffmpeg here has no drawtext and the venv has no Pillow, so cards are SVG rendered by rsvg-convert
(`brew install librsvg`), with macOS's system Helvetica Neue.
"""
import argparse
import subprocess
from html import escape
from pathlib import Path

BG, FG, DIM, ACCENT, PINK, BLUE = "#0b0f1a", "#ffffff", "#9aa3b5", "#FFD400", "#d6247a", "#1f5fd6"
FONT = "Helvetica Neue"
ATTRIBUTION = "Game footage: Hardwick Community Television (HCTV), CC BY 4.0, via Wikimedia Commons. Original audio removed."
REPO = "https://github.com/UgaTheDev/your-own-commentator"


def text(x, y, s, size, fill=FG, weight="normal", anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def svg(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">'
            f'<rect width="1920" height="1080" fill="{BG}"/>'
            f'<rect x="0" y="1064" width="960" height="16" fill="{PINK}"/>'
            f'<rect x="960" y="1064" width="960" height="16" fill="{BLUE}"/>{body}</svg>')


def title():
    return svg(text(960, 470, "Your Own Commentator", 128, weight="bold")
               + f'<rect x="760" y="530" width="400" height="8" fill="{ACCENT}"/>'
               + text(960, 640, "Pick your own sports commentator on Fire TV", 56, DIM))


def pipeline():
    steps = [("Nova Pro", "reads the game"), ("Score graphic", "+ review"), ("Nova 2 Lite", "writes"),
             ("Fact gates", "in code"), ("Polly", "speaks"), ("Fire TV", "plays it")]
    w, gap, y = 270, 42, 470
    x0 = (1920 - len(steps) * w - (len(steps) - 1) * gap) // 2
    body = text(960, 260, "Under the hood", 96, weight="bold")
    for i, (head, sub) in enumerate(steps):
        x = x0 + i * (w + gap)
        edge = ACCENT if head == "Fact gates" else BLUE
        body += (f'<rect x="{x}" y="{y}" width="{w}" height="170" rx="18" fill="#141b2d" stroke="{edge}" '
                 f'stroke-width="4"/>' + text(x + w / 2, y + 75, head, 34, weight="bold")
                 + text(x + w / 2, y + 125, sub, 30, DIM))
        if i:
            ax = x - gap
            body += (f'<line x1="{ax + 8}" y1="{y + 85}" x2="{x - 16}" y2="{y + 85}" stroke="{ACCENT}" stroke-width="5"/>'
                     f'<polygon points="{x - 6},{y + 85} {x - 20},{y + 76} {x - 20},{y + 94}" fill="{ACCENT}"/>')
    return svg(body + text(960, 820, "Every spoken line is checked against the verified event and game-state data.", 40, DIM))


def numbers():
    stats = [("Exact", "score-graphic reader points on 3 games", ACCENT),
             ("5 / 182", "Nova Pro video-only calls correct", PINK),
             ("0 of 494", "invented plays in commentary lines", ACCENT),
             ("3.4 s", "talk-back: end of question to answer audio", BLUE)]
    body = text(960, 200, "Under the hood: the numbers", 80, weight="bold")
    for i, (big, small, color) in enumerate(stats):
        x, y = 520 + (i % 2) * 880, 450 + (i // 2) * 330
        body += text(x, y, big, 140, color, "bold") + text(x, y + 70, small, 38, DIM)
    return svg(body)


def end():
    return svg(text(960, 400, "Your Own Commentator", 96, weight="bold")
               + text(960, 520, REPO, 48, ACCENT)
               + text(960, 760, ATTRIBUTION, 30, DIM))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(Path(__file__).with_name("out") / "cards"))
    out = Path(ap.parse_args().out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, make in [("title", title), ("hood-pipeline", pipeline), ("hood-numbers", numbers), ("end", end)]:
        src = out / f"{name}.svg"
        src.write_text(make())
        subprocess.run(["rsvg-convert", "-w", "1920", "-h", "1080", "-o", str(out / f"{name}.png"), str(src)], check=True)
        print(out / f"{name}.png")


if __name__ == "__main__":
    main()
