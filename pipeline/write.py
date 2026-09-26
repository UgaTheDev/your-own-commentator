"""Persona writer. Grounding gate lives here; Bedrock calls come next.

Rule (CLAUDE.md): commentary may only state facts present in the verified event and
game-state JSON (plus our hand-written rules.json entry). The writer must write numbers as
digits; unsupported_digits() rejects any digit sequence not in the allowed facts. Names,
claims and spelled-out numbers ("tres", 三) are the Bedrock judge's job.
"""
import re
import unicodedata

# t/ids are bookkeeping, not facts a commentator may say
NOT_FACTS = {"t", "id", "eventId", "ruleCardId"}
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")  # \d matches any Unicode digit: ३, ３, etc.


def _canon(match):
    # "३" -> "3", "1,2" (es decimal) -> "1.2", "12.0" -> "12"
    s = "".join(str(unicodedata.decimal(c)) if c.isdigit() else "." for c in match)
    return str(float(s)).removesuffix(".0")


def _numbers(s):
    return {_canon(m) for m in NUMBER.findall(str(s))}


def allowed_numbers(facts):
    found = set()
    if isinstance(facts, dict):
        for k, v in facts.items():
            if k not in NOT_FACTS:
                found |= _numbers(k) | allowed_numbers(v)
    elif isinstance(facts, (list, tuple)):
        for v in facts:
            found |= allowed_numbers(v)
    elif facts is not None and not isinstance(facts, bool):
        found |= _numbers(facts)
    return found


def unsupported_digits(text, facts):
    """Numbers in `text` that appear nowhere in `facts`. Empty set = passes the gate."""
    return _numbers(text) - allowed_numbers(facts)
