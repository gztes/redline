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


def chunk_long(text: str, spans: list[tuple[int, int]], max_words: int = 60) -> list[tuple[int, int]]:
    """Split sentences longer than max_words, preferring clause boundaries (, ; :).

    The correction model has fixed input and output lengths. A run-on sentence past them comes back
    cut short, and the diff would report the missing tail as errors.
    """
    out: list[tuple[int, int]] = []
    for a, b in spans:
        toks = [(m.start() + a, m.end() + a) for m in _TOKEN.finditer(text[a:b])]
        if len(toks) <= max_words:
            out.append((a, b))
            continue
        i = 0
        while i < len(toks):
            window = toks[i : i + max_words]
            if i + max_words >= len(toks):
                cut = len(window)
            else:
                cut = max((k + 1 for k, (s, e) in enumerate(window) if text[e - 1] in ",;:"), default=len(window))
            out.append((window[0][0], window[cut - 1][1]))
            i += cut
    return out


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
                            padding=True, truncation=True, max_length=512)
            with torch.inference_mode():
                ids = self._model.generate(**enc, max_new_tokens=256, num_beams=1)
            results.extend(self._tok.batch_decode(ids, skip_special_tokens=True))
        return results

    def correct(self, sentence: str) -> str:
        return self.correct_batch([sentence])[0]

    def check_many(self, texts: list[str]) -> list[list[Flag]]:
        """Check several texts with one batched pass through the model."""
        jobs: list[tuple[int, int, int]] = []  # (text index, start, end)
        for ti, text in enumerate(texts):
            for a, b in chunk_long(text, split_sentences(text)):
                if re.search(r"[A-Za-z]", text[a:b]):
                    jobs.append((ti, a, b))
        fixed = self.correct_batch([texts[ti][a:b] for ti, a, b in jobs]) if jobs else []
        out: list[list[Flag]] = [[] for _ in texts]
        for (ti, a, b), new in zip(jobs, fixed):
            out[ti].extend(diff_flags(texts[ti][a:b], new, offset=a))
        return out

    def check(self, text: str) -> list[Flag]:
        return self.check_many([text])[0]
