"""Extraction precision/recall vs the human-reviewed events, plus commentary faithfulness.

Usage: python pipeline/eval.py <clip_id>
Writes eval/<clip_id>.md and prints it.
"""
import sys

import common

WINDOW = 2.0
# the score graphic updates a few seconds after the basket, so its events are matched with a wider window
SOURCE_WINDOW = {"scoreboard": 6.0}


def match(proposed, reviewed, window=WINDOW):
    """Greedy one-to-one matching, smallest |dt| first. Returns (proposed_idx, reviewed_idx) pairs."""
    pairs = sorted((abs(p["t"] - r["t"]), i, j) for i, p in enumerate(proposed) for j, r in enumerate(reviewed)
                   if p["type"] == r["type"] and abs(p["t"] - r["t"]) <= window)
    used_p, used_r, out = set(), set(), []
    for _, i, j in pairs:
        if i not in used_p and j not in used_r:
            used_p.add(i)
            used_r.add(j)
            out.append((i, j))
    return out


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def scores(proposed, reviewed):
    """{type: (tp, fp, fn)} plus an "overall" row."""
    pairs = match(proposed, reviewed)
    rows = {}
    for t in sorted({e["type"] for e in proposed + reviewed}):
        tp = sum(1 for i, _ in pairs if proposed[i]["type"] == t)
        rows[t] = (tp, sum(e["type"] == t for e in proposed) - tp, sum(e["type"] == t for e in reviewed) - tp)
    rows["overall"] = (len(pairs), len(proposed) - len(pairs), len(reviewed) - len(pairs))
    return rows


def by_source(proposed, reviewed):
    """{source: (tp, fp, fn, window)}: each proposer judged against the reviewed events it produced."""
    rows = {}
    for src in sorted({e.get("source", "nova") for e in proposed}):
        prop = [e for e in proposed if e.get("source", "nova") == src]
        rev = [e for e in reviewed if e.get("source", "nova") == src]
        w = SOURCE_WINDOW.get(src, WINDOW)
        tp = len(match(prop, rev, w))
        rows[src] = (tp, len(prop) - tp, len(rev) - tp, w)
    return rows


def report(clip_id, proposed, reviewed, lines=None):
    out = [f"# Eval: {clip_id}", "", f"Events matched on type and |dt| <= {WINDOW}s, one-to-one.", "",
           "| type | TP | FP | FN | precision | recall | F1 |", "|---|---|---|---|---|---|---|"]
    for t, (tp, fp, fn) in scores(proposed, reviewed).items():
        p, r, f = prf(tp, fp, fn)
        out.append(f"| {t} | {tp} | {fp} | {fn} | {p:.2f} | {r:.2f} | {f:.2f} |")
    out += ["", "## By source", "", "| source | TP | FP | FN | precision | recall | window |", "|---|---|---|---|---|---|---|"]
    for src, (tp, fp, fn, w) in by_source(proposed, reviewed).items():
        p, r, _ = prf(tp, fp, fn)
        out.append(f"| {src} | {tp} | {fp} | {fn} | {p:.2f} | {r:.2f} | {w:g}s |")
    reviewers = sorted({e.get("reviewedBy", "unknown") for e in reviewed})
    out += ["", f"Reviewed by: {', '.join(reviewers)}" + (" (AI review: spot-check welcome)" if "claude" in reviewers else "")]
    if lines is not None:
        bad = sum(1 for x in lines if x.get("judge") != "supported" or not x.get("grounded"))
        out += ["", "## Faithfulness", "", f"**{bad} unsupported / {len(lines)} lines** "
                "(a line counts as unsupported if it failed the grounding check or the judge)"]
    return "\n".join(out) + "\n"


def main(clip_id):
    d = common.clip_dir(clip_id)
    lines_path = d / "lines.json"
    md = report(clip_id, common.load(d / "events.proposed.json"), common.load(d / "events.reviewed.json"),
                common.load(lines_path) if lines_path.exists() else None)
    out = common.ROOT / "eval" / f"{clip_id}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(md)
    print(md)


if __name__ == "__main__":
    main(sys.argv[1])
