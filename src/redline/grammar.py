"""Grammar check: a local correction model rewrites each sentence; the diff becomes flags."""

import difflib
import re

from redline.flag import Flag
from redline.sentences import split_sentences

_TOKEN = re.compile(r"\S+")


def diff_flags(source: str, corrected: str, offset: int = 0) -> list[Flag]:
    """Turn a corrected rewrite into flags on spans of the source string."""
    src = [(m.group(), m.start(), m.end()) for m in _TOKEN.finditer(source)]
    out = [m.group() for m in _TOKEN.finditer(corrected)]
    a = [t for t, _, _ in src]
    flags: list[Flag] = []
    sm = difflib.SequenceMatcher(None, a, out, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        new = " ".join(out[j1:j2])
        if op == "insert":
            if not src:
                continue
            if i1 > 0:
                tok, start, end = src[i1 - 1]
                suggestion = f"{tok} {new}"
            else:
                tok, start, end = src[0]
                suggestion = f"{new} {tok}"
            flags.append(Flag(start + offset, end + offset, "grammar", "insert",
                              f'Something may be missing here: "{suggestion}".', suggestion))
            continue
        start, end = src[i1][1], src[i2 - 1][2]
        if op == "delete":
            flags.append(Flag(start + offset, end + offset, "grammar", "delete",
                              "This may not belong here.", ""))
        else:
            flags.append(Flag(start + offset, end + offset, "grammar", "replace",
                              f'Did you mean "{new}"?', new))
    return flags


class GrammarChecker:
    """Wraps a seq2seq grammar-correction model. Loads on first use."""

    PREFIXES = {"Unbabel/gec-t5_small": "gec: ", "vennify/t5-base-grammar-correction": "grammar: "}

    def __init__(self, model_id: str = "Unbabel/gec-t5_small", batch_size: int = 16):
        self.model_id = model_id
        self.batch_size = batch_size
        self.prefix = self.PREFIXES.get(model_id, "")
        self._tok = None
        self._model = None

    def _load(self):
        if self._model is None:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            self._tok = AutoTokenizer.from_pretrained(self.model_id)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id).eval()

    def correct_batch(self, sentences: list[str]) -> list[str]:
        import torch

        self._load()
        results: list[str] = []
        for i in range(0, len(sentences), self.batch_size):
            chunk = sentences[i : i + self.batch_size]
            enc = self._tok([self.prefix + s for s in chunk], return_tensors="pt",
                            padding=True, truncation=True, max_length=256)
            with torch.inference_mode():
                ids = self._model.generate(**enc, max_new_tokens=160, num_beams=1)
            results.extend(self._tok.batch_decode(ids, skip_special_tokens=True))
        return results

    def correct(self, sentence: str) -> str:
        return self.correct_batch([sentence])[0]

    def check(self, text: str) -> list[Flag]:
        spans = [(a, b) for a, b in split_sentences(text) if re.search(r"[A-Za-z]", text[a:b])]
        if not spans:
            return []
        fixed = self.correct_batch([text[a:b] for a, b in spans])
        flags: list[Flag] = []
        for (a, b), new in zip(spans, fixed):
            flags.extend(diff_flags(text[a:b], new, offset=a))
        return flags
