"""Parse M2 files (CoNLL-2014, BEA-2019) and map gold edits to character spans."""

from dataclasses import dataclass, field
from pathlib import Path

from redline.eval.detok import detokenize

SKIP_TYPES = {"noop", "UNK"}  # UNK = annotator marked an error but gave no correction type


@dataclass
class Sentence:
    tokens: list[str]
    edits: dict[int, list[tuple[int, int, str]]] = field(default_factory=dict)


def parse_m2(path: Path) -> list[Sentence]:
    sents: list[Sentence] = []
    cur: Sentence | None = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("S "):
            cur = Sentence(tokens=line[2:].split())
            sents.append(cur)
        elif line.startswith("A ") and cur is not None:
            fields = line[2:].split("|||")
            start, end = map(int, fields[0].split())
            etype, annot = fields[1], int(fields[-1])
            bucket = cur.edits.setdefault(annot, [])
            if etype not in SKIP_TYPES and start >= 0:
                bucket.append((start, end, etype))
    # An annotator with no edits on a sentence often has no line at all (CoNLL-2014 combined),
    # so every annotator seen anywhere in the file gets an empty edit list where missing.
    annotators = {a for s in sents for a in s.edits} or {0}
    for s in sents:
        for a in annotators:
            s.edits.setdefault(a, [])
        s.edits = dict(sorted(s.edits.items()))
    return sents


GoldSpan = tuple[int, int, str, bool]  # start, end, type, is_insertion


def gold_char_spans(sent: Sentence) -> tuple[str, dict[int, list[GoldSpan]]]:
    """Detokenised text plus, per annotator, gold spans in characters.

    An insertion (no source tokens) becomes the gap between its neighbours, from the end of the
    previous token to the start of the next.
    """
    text, offs = detokenize(sent.tokens)
    out: dict[int, list[GoldSpan]] = {}
    for annot, edits in sent.edits.items():
        spans = []
        for ts, te, etype in edits:
            if te > ts:
                spans.append((offs[ts][0], offs[te - 1][1], etype, False))
            else:
                prev_end = offs[ts - 1][1] if ts > 0 else 0
                next_start = offs[ts][0] if ts < len(offs) else len(text)
                spans.append((prev_end, next_start, etype, True))
        out[annot] = spans
    return text, out
