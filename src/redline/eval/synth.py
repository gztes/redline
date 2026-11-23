"""Synthetic meaning flips: change exactly one negation or direction cue in a clean sentence.

Used to tune and stress-test the meaning-flip check. Reported separately from real rewrites,
never as the headline.
"""

import random
import re

SWAPS = {
    "above": "below", "more": "less", "higher": "lower", "increase": "decrease",
    "increases": "decreases", "increased": "decreased", "rise": "fall", "rises": "falls",
    "rose": "fell", "larger": "smaller", "better": "worse", "most": "least", "exceeds": "trails",
    "gain": "loss", "strong": "weak", "stronger": "weaker", "always": "never",
}
SWAPS |= {v: k for k, v in list(SWAPS.items())}
INSERT_AFTER = {"is", "are", "was", "were", "will", "should", "could", "would", "does", "do", "did"}


def _match_case(src: str, new: str) -> str:
    return new[:1].upper() + new[1:] if src[:1].isupper() else new


def make_flip(sentence: str, rng: random.Random) -> str | None:
    """Return the sentence with one cue flipped, or None if it has no cue.

    Removing a negation or swapping a direction word is preferred; inserting "not" is the fallback,
    because inserted negations are the easiest case for a model.
    """
    strong: list[tuple[int, int, str]] = []  # (start, end, replacement)
    weak: list[tuple[int, int, str]] = []
    for m in re.finditer(r"\b(\w+)('t)?\b", sentence):
        word = m.group(0)
        low = word.lower()
        if low in {"no", "not"}:
            end = m.end() + 1 if sentence[m.end():m.end() + 1] == " " else m.end()
            strong.append((m.start(), end, ""))
        elif low == "cannot":
            strong.append((m.start(), m.end(), _match_case(word, "can")))
        elif low.endswith("n't") and low not in {"can't", "won't"}:
            strong.append((m.start(), m.end(), word[:-3]))
        elif low in SWAPS:
            strong.append((m.start(), m.end(), _match_case(word, SWAPS[low])))
        elif low in INSERT_AFTER:
            weak.append((m.end(), m.end(), " not"))
        elif low == "can":
            weak.append((m.start(), m.end(), _match_case(word, "cannot")))
    pool = strong or weak
    if not pool:
        return None
    s, e, rep = rng.choice(pool)
    return sentence[:s] + rep + sentence[e:]
