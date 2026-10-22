"""1920x1080 PNG cards for the demo video and Devpost, after design/handoff/06 Demo + Devpost (6a-6e, 6h).

  cards.py --out-dir scripts/demo/out/cards

Writes title, hood-pipeline, hood-numbers, end (used by edl.json), lowerthird (transparent overlay) and
devpost-grounding. ffmpeg here has no drawtext and the venv has no Pillow, so cards are SVG rendered by
rsvg-convert (`brew install librsvg`), with macOS's system Helvetica Neue. Every figure is from README.md.
"""
import argparse
import subprocess
from html import escape
from pathlib import Path

BG, PANEL, PANEL2, FOCUS, LINE, LINE2 = "#070b10", "#0c1218", "#111922", "#16202b", "#1c2733", "#2a3847"
FG, SOFT, MUTED, ACCENT, INK = "#e6edf3", "#c4ced8", "#8c99a8", "#FFD400", "#070b10"
FONT = "Helvetica Neue"
ATTRIBUTION = "Game footage: Hardwick Community Television (HCTV), CC BY 4.0, via Wikimedia Commons. Original audio removed."
REPO = "https://github.com/UgaTheDev/your-own-commentator"
W, H, SAFE_X, SAFE_Y = 1920, 1080, 96, 54


def text(x, y, s, size, fill=FG, weight="normal", anchor="start", spacing=0):
    """One line; `s` may be a list of (string, attrs) spans for mixed weight/size/colour."""
    spans = s if isinstance(s, list) else [(s, "")]
    inner = "".join(f"<tspan {a}>{escape(t)}</tspan>" for t, a in spans)
    return (f'<text xml:space="preserve" x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{spacing}">{inner}</text>')


def lines(x, y, rows, size, lh, **kw):
    return "".join(text(x, y + i * lh, r, size, **kw) for i, r in enumerate(rows))


def eyebrow(x, y, s, fill=MUTED, anchor="start"):
    return text(x, y, s, 24, fill, "bold", anchor, 24 * .14)


def mark(x, y, size, fill=ACCENT, ink=INK):
    """YOC mark (design/handoff/YOC Mark): ball r36 at (54,46) + speech tail, seams clipped to the ball."""
    return (f'<defs><clipPath id="ball"><circle cx="54" cy="46" r="36"/></clipPath></defs>'
            f'<g transform="translate({x},{y}) scale({size / 100})">'
            f'<circle cx="54" cy="46" r="36" fill="{fill}"/><path d="M27 70 L14 92 L44 80 Z" fill="{fill}"/>'
            f'<g clip-path="url(#ball)" fill="none" stroke="{ink}" stroke-width="4.5" stroke-linecap="round">'
            f'<path d="M18 46 H90"/><path d="M54 10 V82"/><path d="M30 17 C42 30 42 62 30 75"/>'
            f'<path d="M78 17 C66 30 66 62 78 75"/></g></g>')


def wordmark(x, y, size, anchor="start"):
    return text(x, y, [("Your Own ", ""), ("Commentator", 'font-weight="bold"')], size, anchor=anchor,
                spacing=-size * .025)


def svg(body, bg=BG):
    fill = f'<rect width="{W}" height="{H}" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">{fill}{body}</svg>'


def title():  # 6a
    glow = ('<defs><radialGradient id="g" cx="50%" cy="45%" r="60%"><stop offset="0" stop-color="#16212c"/>'
            f'<stop offset="1" stop-color="{BG}"/></radialGradient></defs><rect width="{W}" height="{H}" fill="url(#g)"/>')
    return svg(glow + '<circle cx="960" cy="540" r="650" fill="none" stroke="rgba(255,212,0,.12)" stroke-width="3"/>'
               + mark(850, 290, 220)
               + wordmark(960, 652, 120, "middle")
               + text(960, 750, "Pick who calls the game. Ask why. Get only the facts.", 36, SOFT, anchor="middle")
               + eyebrow(SAFE_X, H - SAFE_Y - 6, "A FIRE TV APP")
               + eyebrow(W - SAFE_X, H - SAFE_Y - 6, "HACKATHON DEMO", anchor="end"))


def pipeline():  # 6b
    steps = [(["Nova Pro reads", "the game"], ["Proposes plays", "from the video."]),
             (["Score graphic", "+ human review"], ["The on-screen", "score anchors", "every basket."]),
             (["Nova 2 Lite", "writes"], ["In your", "commentator’s", "voice."]),
             (["Fact gates", "in code"], ["Every number", "and play is", "checked. Fail =", "retry, then drop."]),
             (["Polly speaks"], ["Turns each", "checked line", "into speech."]),
             (["Fire TV"], ["Overlays,", "captions and", "talk-back from", "your phone."])]
    gap, top, h = 40, 380, 360
    w = (W - 2 * SAFE_X - 5 * gap) / 6
    body = eyebrow(SAFE_X, 116, "UNDER THE HOOD", ACCENT) + text(SAFE_X, 200, "From the broadcast to your living room",
                                                                  72, weight="bold", spacing=-1.8)
    for i, (head, sub) in enumerate(steps):
        x, gate, last = SAFE_X + i * (w + gap), i == 3, i == 5
        fill, num, ink = (ACCENT, INK, INK) if last else (FOCUS if gate else PANEL, ACCENT if gate else MUTED, FG)
        body += f'<rect x="{x}" y="{top}" width="{w}" height="{h}" rx="24" fill="{fill}"/>'
        if not last:
            sw = 3 if gate else 1
            body += (f'<rect x="{x + sw / 2}" y="{top + sw / 2}" width="{w - sw}" height="{h - sw}" rx="{24 - sw / 2}" '
                     f'fill="none" stroke="{ACCENT if gate else LINE2}" stroke-width="{sw}"/>')
            ax = x + w + gap / 2
            body += (f'<path d="M{ax - 12} {top + 172} H{ax + 8} M{ax + 1} {top + 164} L{ax + 10} {top + 172} '
                     f'L{ax + 1} {top + 180}" fill="none" stroke="{ACCENT}" stroke-width="4" stroke-linecap="round" '
                     f'stroke-linejoin="round"/>')
        tx = x + 28
        body += text(tx, top + 52, f"{i + 1:02d}", 24, num, "bold")
        body += lines(tx, top + 108, head, 28, 38, fill=ink, weight="bold")
        body += lines(tx, top + 108 + len(head) * 38 + 22, sub, 24, 34, fill=INK if last else SOFT,
                      weight="500" if last else "normal")
    body += (f'<line x1="{SAFE_X}" y1="801" x2="{W - SAFE_X}" y2="801" stroke="{LINE2}" stroke-width="2" '
             f'stroke-dasharray="14 12"/>')
    return svg(body + text(SAFE_X, 872, "Nothing is spoken unless every number and play in the line matches the "
                                        "reviewed play log.", 30, SOFT))


def numbers():  # 6c
    big = lambda a, b: [(a, ""), (b, 'font-size="96" letter-spacing="-1"')]
    cells = [(big("Exact", ""), FG, ["Score-graphic reader: points exact", "on all 3 games."]),
             (big("5", " / 182"), MUTED, ["Nova Pro video-only calls correct,", "so it never works alone."]),
             (big("0", " of 494"), ACCENT, ["Commentary lines with an", "invented play."]),
             (big("3.4", " s"), FG, ["Talk-back: from the end of your", "question to the answer audio."])]
    top, bottom = 180, H - 120
    mid_y = (top + bottom) / 2
    body = eyebrow(SAFE_X, 116, "THE NUMBERS", ACCENT)
    body += (f'<rect x="{W / 2 - 1}" y="{top}" width="2" height="{bottom - top}" fill="{LINE}"/>'
             f'<rect x="{SAFE_X}" y="{mid_y - 1}" width="{W - 2 * SAFE_X}" height="2" fill="{LINE}"/>')
    for i, (value, color, desc) in enumerate(cells):
        x = SAFE_X if i % 2 == 0 else W / 2 + 57
        cy = top + (mid_y - top) / 2 + (i // 2) * (mid_y - top)  # vertical centre of the cell
        y0 = cy - (160 + 16 + 88) / 2
        body += text(x, y0 + 128, value, 160, color, "bold", spacing=-6.4)
        body += lines(x, y0 + 160 + 16 + 32, desc, 32, 44, fill=SOFT)
    return svg(body)


def lowerthird():  # 6d: transparent, composited over 1920x1080 video, bottom-left in the safe area
    quote, w, h = "“Wait, why did blue just get a point?”", 980, 164
    x, y = SAFE_X, H - 96 - h
    return svg(f'<defs><clipPath id="lt"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24"/></clipPath>'
               f'<filter id="sh" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="28"/></filter></defs>'
               f'<rect x="{x}" y="{y + 32}" width="{w}" height="{h}" rx="24" fill="rgba(0,0,0,.6)" filter="url(#sh)"/>'
               f'<g clip-path="url(#lt)"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="rgba(9,14,20,.94)"/>'
               f'<rect x="{x}" y="{y}" width="16" height="{h}" fill="{ACCENT}"/></g>'
               f'<rect x="{x + 50}" y="{y + 30}" width="56" height="96" rx="12" fill="none" stroke="{FG}" stroke-width="4"/>'
               f'<rect x="{x + 68}" y="{y + 108}" width="20" height="4" rx="2" fill="{FG}"/>'
               + eyebrow(x + 140, y + 62, "ASKED FROM THE PHONE", ACCENT)
               + text(x + 140, y + 124, quote, 48, FG, "bold", spacing=-.96), bg=None)


def end():  # 6e
    cols = [("BUILT WITH", ["Amazon Nova Pro · Nova 2 Lite", "Amazon Nova Sonic · Polly", "Vega OS · React Native"], 30, 44, "bold", FG),
            ("CREDITS", ["Game footage: Hardwick Community", "Television (HCTV), CC BY 4.0, via", "Wikimedia Commons. Original", "audio removed."], 26, 38, "normal", SOFT),
            ("A NOTE ON PLAYERS", ["Players are minors. We refer to", "them only by team colour and", "jersey number."], 26, 38, "normal", SOFT)]
    body = ('<circle cx="1610" cy="310" r="550" fill="none" stroke="rgba(255,212,0,.12)" stroke-width="3"/>'
            + mark(SAFE_X, 96, 120) + wordmark(SAFE_X + 148, 178, 64)
            + lines(SAFE_X, 406, ["Your game. Your voice.", "Only the facts."], 88, 96, weight="bold", spacing=-2.6)
            + text(SAFE_X, 640, REPO, 40, ACCENT, "bold")
            + f'<rect x="{SAFE_X}" y="740" width="{W - 2 * SAFE_X}" height="1" fill="{LINE}"/>')
    cw = (W - 2 * SAFE_X - 2 * 48) / 3
    for i, (head, rows, size, lh, weight, fill) in enumerate(cols):
        x = SAFE_X + i * (cw + 48)
        body += eyebrow(x, 800, head) + lines(x, 852, rows, size, lh, fill=fill, weight=weight)
    return svg(body)


def grounding():  # 6h, Devpost gallery: the gates from README.md "Grounding"
    gates = [("Numbers gate", "Every number in the line must appear in the verified facts, in any script."),
             ("Play gate", "Every play the line names must match a verified play, credited to the right team."),
             ("Bedrock judge", "Nova 2 Lite checks names and claims. Fail twice and the line is dropped."),
             ("Facts-only fallback", "A viewer’s answer that fails is replaced by a sentence built only from facts.")]
    body = (eyebrow(SAFE_X, 116, "GROUNDING", ACCENT)
            + text(SAFE_X, 212, "No invented facts.", 88, weight="bold", spacing=-2.6)
            + eyebrow(SAFE_X, 384, "BEFORE ANY LINE IS SPOKEN"))
    for i, (head, desc) in enumerate(gates):
        y = 432 + i * 132
        body += (f'<rect x="{SAFE_X}" y="{y}" width="56" height="56" rx="14" fill="{ACCENT}"/>'
                 + text(SAFE_X + 28, y + 39, str(i + 1), 30, INK, "bold", "middle")
                 + text(SAFE_X + 84, y + 26, head, 32, FG, "bold")
                 + text(SAFE_X + 84, y + 70, desc, 26, SOFT))
    px, pw = W - SAFE_X - 560, 560
    body += (f'<rect x="{px}" y="360" width="{pw}" height="620" rx="28" fill="{PANEL}"/>'
             f'<rect x="{px + .5}" y="360.5" width="{pw - 1}" height="619" rx="27.5" fill="none" stroke="{LINE2}"/>'
             + eyebrow(px + 48, 428, "MEASURED")
             + text(px + 48, 590, "0", 160, ACCENT, "bold")
             + lines(px + 48, 660, ["invented plays in 494", "commentary lines"], 32, 44, weight="bold")
             + f'<rect x="{px + 48}" y="740" width="{pw - 96}" height="1" fill="{LINE}"/>'
             + lines(px + 48, 796, ["20 of 300 lines had one before the", "play gate. A model judge alone", "caught 0 of 2 in our A/B test,", "so the gates are plain code."], 24, 34, fill=SOFT))
    return svg(body)


CARDS = [("title", title), ("hood-pipeline", pipeline), ("hood-numbers", numbers), ("end", end),
         ("lowerthird", lowerthird), ("devpost-grounding", grounding)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(Path(__file__).with_name("out") / "cards"))
    out = Path(ap.parse_args().out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, make in CARDS:
        src = out / f"{name}.svg"
        src.write_text(make())
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(out / f"{name}.png"), str(src)], check=True)
        print(out / f"{name}.png")


if __name__ == "__main__":
    main()
