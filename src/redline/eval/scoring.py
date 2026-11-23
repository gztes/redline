"""Detection-level scoring: did the tool flag the place where the error is?

A flag hits a gold error if their spans overlap. For a missing-word error the gold span is the
gap between two words, and a flag hits it if it touches the gap. Precision counts flags that hit
any gold error; recall counts gold errors hit by any flag. Headline metric F0.5 (precision
weighted, since false alarms are what make you stop using a checker).
"""

import random
import re

Span = tuple[int, int]


def _hit(gold: tuple, pred: Span) -> bool:
    gs, ge, _, is_insert = gold
    ps, pe = pred
    if is_insert:
        return ps <= ge and pe >= gs
    return ps < ge and gs < pe


def hits(gold: list[tuple], preds: list[Span]) -> tuple[int, int]:
    pred_hit = sum(any(_hit(g, p) for g in gold) for p in preds)
    gold_hit = sum(any(_hit(g, p) for p in preds) for g in gold)
    return pred_hit, gold_hit


def _f(tp_p: int, n_pred: int, tp_g: int, n_gold: int, beta: float) -> tuple[float, float, float]:
    p = tp_p / n_pred if n_pred else 1.0
    r = tp_g / n_gold if n_gold else 1.0
    b2 = beta * beta
    f = (1 + b2) * p * r / (b2 * p + r) if (p + r) else 0.0
    return p, r, f


def _base_type(t: str) -> str:
    return re.sub(r"^[RMU]:", "", t)


def score(gold: list[dict[int, list[tuple]]], pred: list[list[Span]], beta: float = 0.5,
          n_boot: int = 1000, seed: int = 0) -> dict:
    assert len(gold) == len(pred)
    rows = []  # per sentence: (pred_hit, n_pred, gold_hit, n_gold, chosen gold list)
    for annots, preds in zip(gold, pred):
        best = None
        for spans in annots.values():
            ph, gh = hits(spans, preds)
            key = (ph + gh, -len(spans))
            if best is None or key > best[0]:
                best = (key, ph, gh, spans)
        _, ph, gh, spans = best
        rows.append((ph, len(preds), gh, len(spans), spans, preds))

    def agg(sample):
        return _f(sum(r[0] for r in sample), sum(r[1] for r in sample),
                  sum(r[2] for r in sample), sum(r[3] for r in sample), beta)

    p, r, f = agg(rows)
    rng = random.Random(seed)
    fs = sorted(agg([rows[rng.randrange(len(rows))] for _ in rows])[2] for _ in range(n_boot))
    ci = (fs[int(0.025 * (n_boot - 1))], fs[int(0.975 * (n_boot - 1))])

    type_tot: dict[str, int] = {}
    type_hit: dict[str, int] = {}
    for _, _, _, _, spans, preds in rows:
        for g in spans:
            t = _base_type(g[2])
            type_tot[t] = type_tot.get(t, 0) + 1
            type_hit[t] = type_hit.get(t, 0) + any(_hit(g, pp) for pp in preds)

    return {
        "p": p, "r": r, "f": f, "ci_f": ci, "beta": beta,
        "n_sentences": len(rows), "n_gold": sum(r_[3] for r_ in rows), "n_pred": sum(r_[1] for r_ in rows),
        "per_type_recall": {t: type_hit[t] / type_tot[t] for t in sorted(type_tot)},
        "per_type_count": dict(sorted(type_tot.items())),
    }
