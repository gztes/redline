"""Eval runners. Results files hold numbers only, never sentence text."""

import json
import time
from pathlib import Path

from redline.eval.data import PUBLIC, REPO_ROOT, download
from redline.eval.m2 import gold_char_spans, parse_m2
from redline.eval.scoring import score

RESULTS = REPO_ROOT / "results"


def _system(s):
    if isinstance(s, str):
        from redline.eval.baselines import SYSTEMS

        return SYSTEMS[s]()
    return s


def _fmt(r: dict) -> str:
    lo, hi = r["ci_f"]
    return f"P {r['p']:.3f}  R {r['r']:.3f}  F0.5 {r['f']:.3f} [{lo:.3f}, {hi:.3f}]  flags {r['n_pred']}"


def run_grammar_eval(dataset: str, systems: list, limit: int | None = None, m2: Path | None = None,
                     out_dir: Path = RESULTS, use_cache: bool = True) -> dict:
    sents = parse_m2(m2 or download(dataset))
    if limit:
        sents = sents[:limit]
    gold_pairs = [gold_char_spans(s) for s in sents]
    texts = [t for t, _ in gold_pairs]
    gold = [g for _, g in gold_pairs]
    cache_dir = PUBLIC / "cache"
    results = {"dataset": dataset, "n_sentences": len(sents), "systems": {}}
    for s in systems:
        system = _system(s)
        cache = cache_dir / f"{dataset}-{system.name}-{len(texts)}.json"
        t0 = time.time()
        if use_cache and cache.exists():
            preds = [[tuple(x) for x in row] for row in json.loads(cache.read_text())]
        else:
            preds = system.spans(texts)
            if use_cache:
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(preds))
        system.close()
        r = score(gold, preds)
        r["seconds"] = round(time.time() - t0, 1)
        results["systems"][system.name] = r
        print(f"{dataset:9s} {system.name:16s} {_fmt(r)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"grammar-{dataset}.json").write_text(json.dumps(results, indent=2))
    return results
