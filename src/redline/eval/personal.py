"""Personal eval sets, built from my own writing. Everything here stays in data/personal (gitignored)."""

import hashlib
import json
import random
import re
from pathlib import Path

from redline.eval.data import PERSONAL
from redline.eval.synth import make_flip
from redline.sentences import split_sentences

TRANSCRIPTS = Path.home() / ".claude" / "projects"
_TAG_BLOCK = re.compile(r"<([A-Za-z_-]+)[^>]*>.*?</\1>", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")

SYNONYMS = {
    "buy": "purchase", "big": "large", "show": "demonstrate", "help": "assist", "start": "begin",
    "use": "employ", "important": "significant", "many": "numerous", "enough": "sufficient",
    "quick": "fast", "hard": "difficult", "get": "obtain", "need": "require", "try": "attempt",
}
CONTRACTIONS = {
    "isn't": "is not", "aren't": "are not", "doesn't": "does not", "don't": "do not",
    "didn't": "did not", "wasn't": "was not", "it's": "it is", "i'm": "I am", "we're": "we are",
    "they're": "they are", "can't": "cannot", "won't": "will not",
}


def _case(src: str, new: str) -> str:
    return new[:1].upper() + new[1:] if src[:1].isupper() else new


def make_paraphrase(sentence: str, rng: random.Random) -> str | None:
    """A meaning-preserving edit: expand or contract one contraction, or swap one synonym."""
    options: list[tuple[int, int, str]] = []
    for m in re.finditer(r"\b[\w']+\b", sentence):
        w = m.group(0)
        low = w.lower()
        if low in CONTRACTIONS:
            options.append((m.start(), m.end(), _case(w, CONTRACTIONS[low])))
        elif low in SYNONYMS:
            options.append((m.start(), m.end(), _case(w, SYNONYMS[low])))
    if not options:
        return None
    s, e, rep = rng.choice(options)
    return sentence[:s] + rep + sentence[e:]


def _own_text(content) -> str:
    if isinstance(content, list):
        content = " ".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    if not isinstance(content, str):
        return ""
    return _TAG.sub(" ", _TAG_BLOCK.sub(" ", content)).strip()


def collect_prompt_sentences(files: list[Path], min_words: int = 4, max_words: int = 60) -> list[str]:
    """Sentences I typed myself into Claude Code: user turns only, minus pasted, tool and system text."""
    seen: set[str] = set()
    out: list[str] = []
    for f in files:
        for line in Path(f).read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = row.get("message") or {}
            if row.get("type") != "user" or msg.get("role") != "user":
                continue
            text = _own_text(msg.get("content"))
            for a, b in split_sentences(text):
                sent = " ".join(text[a:b].split())
                if min_words <= len(sent.split()) <= max_words and sent not in seen:
                    seen.add(sent)
                    out.append(sent)
    return out


def transcript_files() -> list[Path]:
    return sorted(TRANSCRIPTS.glob("*/*.jsonl"))


def _split(key: str) -> str:
    return "dev" if int(hashlib.sha1(key.encode()).hexdigest(), 16) % 2 == 0 else "test"


def build_sets(extra_sources: list[Path] | None = None, n_style: int = 300, seed: int = 0) -> dict:
    """Write candidates.jsonl (to label for style) and flip_synth.jsonl (flip/paraphrase pairs)."""
    rng = random.Random(seed)
    sents = collect_prompt_sentences(transcript_files())
    for src in extra_sources or []:
        text = Path(src).read_text(encoding="utf-8", errors="replace")
        sents += [" ".join(text[a:b].split()) for a, b in split_sentences(text)
                  if 4 <= len(text[a:b].split()) <= 60]
    PERSONAL.mkdir(parents=True, exist_ok=True)
    pool = sents[:]
    rng.shuffle(pool)
    with open(PERSONAL / "candidates.jsonl", "w", encoding="utf-8") as fh:
        for s in pool[:n_style]:
            fh.write(json.dumps({"text": s}, ensure_ascii=False) + "\n")
    rows = build_flip_rows(pool, seed=seed, source="own-writing", balance=True)
    _write_jsonl(PERSONAL / "flip_synth.jsonl", rows)
    n_pos = sum(r["flip"] for r in rows)
    n_neg = len(rows) - n_pos
    return {"sentences": len(sents), "candidates": min(n_style, len(pool)), "flip_pos": n_pos, "flip_neg": n_neg}


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def build_flip_rows(sentences: list[str], seed: int = 0, source: str = "", balance: bool = False) -> list[dict]:
    """One flipped and one paraphrased rewrite per sentence, where a cue exists.

    balance=True drops random rows from the larger class so flips and paraphrases are equal,
    which keeps precision from being inflated by the base rate.
    """
    rng = random.Random(seed)
    rows = []
    for s in sentences:
        for maker, label in ((make_flip, True), (make_paraphrase, False)):
            r = maker(s, rng)
            if r and r != s:
                rows.append({"original": s, "rewrite": r, "flip": label, "split": _split(s), "source": source})
    if balance:
        pos = [r for r in rows if r["flip"]]
        neg = [r for r in rows if not r["flip"]]
        k = min(len(pos), len(neg))
        keep = rng.sample(pos, k) + rng.sample(neg, k)
        rows = [r for r in rows if any(r is x for x in keep)]
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def build_public_flip_set(n_sentences: int = 4000, seed: int = 0) -> dict:
    """Synthetic flip pairs from BEA-2019 dev sentences, for when no personal source is approved yet."""
    from redline.eval.data import download
    from redline.eval.m2 import parse_m2
    from redline.eval.detok import detokenize

    sents = [detokenize(s.tokens)[0] for s in parse_m2(download("bea19dev"))]
    sents = [s for s in sents if 6 <= len(s.split()) <= 40]
    random.Random(seed).shuffle(sents)
    rows = build_flip_rows(sents[:n_sentences], seed=seed, source="bea19dev", balance=True)
    _write_jsonl(PERSONAL / "flip_synth.jsonl", rows)
    return {"pairs": len(rows), "flip": sum(r["flip"] for r in rows)}
