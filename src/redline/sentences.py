"""Sentence spans over the original string (offsets, not copies)."""

import re

_LINE = re.compile(r"[^\n]+")
_SENT = re.compile(r".+?(?:[.!?]+[\"')\]]*(?=\s|$)|$)", re.DOTALL)


def split_sentences(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for line in _LINE.finditer(text):
        base = line.start()
        for m in _SENT.finditer(line.group()):
            seg = m.group()
            if not seg.strip():
                continue
            lead = len(seg) - len(seg.lstrip())
            trail = len(seg) - len(seg.rstrip())
            spans.append((base + m.start() + lead, base + m.end() - trail))
    return spans
