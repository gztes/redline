"""Meaning-flip check: does a rewrite contradict the text it was rewritten from?

1. Split both texts into sentences.
2. Pair each rewrite sentence with the original sentence it came from, by embedding similarity.
3. Ask an NLI model whether the pair contradicts. Flag the rewrite sentence if it does.
"""

from collections.abc import Callable

import numpy as np

from redline.flag import Flag
from redline.sentences import split_sentences

Embed = Callable[[list[str]], np.ndarray]  # returns L2-normalised rows


def align(orig: list[str], rew: list[str], embed: Embed, min_sim: float = 0.5) -> list[tuple[int, int, float]]:
    """Greedy one-to-one pairing, most similar pair first. Returns (orig_i, rew_j, sim) sorted by rew_j."""
    if not orig or not rew:
        return []
    sims = embed(orig) @ embed(rew).T
    used_i: set[int] = set()
    used_j: set[int] = set()
    pairs = []
    for flat in np.argsort(-sims, axis=None):
        i, j = divmod(int(flat), sims.shape[1])
        if sims[i, j] < min_sim:
            break
        if i in used_i or j in used_j:
            continue
        used_i.add(i)
        used_j.add(j)
        pairs.append((i, j, float(sims[i, j])))
    return sorted(pairs, key=lambda p: p[1])


class FlipChecker:
    def __init__(self, nli: str = "cross-encoder/nli-deberta-v3-small",
                 embedder: str = "sentence-transformers/all-MiniLM-L6-v2", threshold: float = 0.5):
        self.nli_id = nli
        self.embedder_id = embedder
        self.threshold = threshold
        self._nli = None
        self._emb = None
        self._contra = None

    def _load(self):
        if self._nli is None:
            from sentence_transformers import CrossEncoder, SentenceTransformer

            self._emb = SentenceTransformer(self.embedder_id, device="cpu")
            self._nli = CrossEncoder(self.nli_id, device="cpu")
            labels = {v.lower(): int(k) for k, v in self._nli.model.config.id2label.items()}
            self._contra = labels["contradiction"]

    def embed(self, texts: list[str]) -> np.ndarray:
        self._load()
        return self._emb.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    def contradiction_probs(self, pairs: list[tuple[str, str]]) -> list[float]:
        """P(contradiction), taking the max over both directions (contradiction is roughly symmetric)."""
        self._load()
        if not pairs:
            return []
        both = pairs + [(b, a) for a, b in pairs]
        logits = np.asarray(self._nli.predict(both, convert_to_numpy=True, show_progress_bar=False))
        probs = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs /= probs.sum(axis=1, keepdims=True)
        c = probs[:, self._contra]
        n = len(pairs)
        return [float(max(c[k], c[k + n])) for k in range(n)]

    def compare(self, original: str, rewrite: str) -> list[Flag]:
        o_spans, r_spans = split_sentences(original), split_sentences(rewrite)
        o = [original[a:b] for a, b in o_spans]
        r = [rewrite[a:b] for a, b in r_spans]
        pairs = align(o, r, self.embed)
        probs = self.contradiction_probs([(o[i], r[j]) for i, j, _ in pairs])
        flags = []
        for (i, j, _), p in zip(pairs, probs):
            if p >= self.threshold:
                a, b = r_spans[j]
                flags.append(Flag(a, b, "meaning-flip", "contradicts-source",
                                  f'May contradict the original ({p:.0%}): "{o[i]}"'))
        return flags
