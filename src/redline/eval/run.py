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


class RedlineStyle:
    name = "redline-style"

    def spans(self, texts):
        from redline.checker import check_style_only

        return [[(f.start, f.end) for f in check_style_only(t)] for t in texts]

    def close(self):
        pass


def run_style_eval(systems: list, gold: list[dict] | None = None, out_dir: Path = RESULTS) -> dict:
    """Score systems against my own span labels from `redline label`."""
    from redline.eval.data import PERSONAL
    from redline.eval.personal import load_jsonl

    gold = gold if gold is not None else load_jsonl(PERSONAL / "style_gold.jsonl")
    if not gold:
        print("No labels yet. Run `redline label` to label your own sentences first.")
        return {}
    texts = [g["text"] for g in gold]
    golds = [{0: [(s, e, lab, False) for s, e, lab in g["spans"]]} for g in gold]
    results = {"n_sentences": len(gold), "systems": {}}
    for s in systems:
        system = RedlineStyle() if s == "redline-style" else _system(s)
        r = score(golds, system.spans(texts))
        system.close()
        results["systems"][system.name] = r
        print(f"style     {system.name:16s} {_fmt(r)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "style.json").write_text(json.dumps(results, indent=2))
    return results


def run_flip_eval(probs_fn=None, synth: list[dict] | None = None, real: list[dict] | None = None,
                  out_dir: Path = RESULTS) -> dict:
    """Threshold picked on the synthetic dev half, reported on the synthetic test half and on real pairs."""
    from redline.eval.data import PERSONAL
    from redline.eval.personal import load_jsonl
    from redline.eval.scoring import binary_scores, pick_threshold

    if probs_fn is None:
        from redline.checker import flip_checker

        probs_fn = flip_checker().contradiction_probs
    synth = synth if synth is not None else load_jsonl(PERSONAL / "flip_synth.jsonl")
    real = real if real is not None else load_jsonl(PERSONAL / "flip_real.jsonl")
    if not synth:
        print("No synthetic pairs. Run `redline build-sets` first.")
        return {}

    def probs(rows):
        return probs_fn([(r["original"], r["rewrite"]) for r in rows])

    dev = [r for r in synth if r["split"] == "dev"]
    test = [r for r in synth if r["split"] == "test"]
    dev_p = probs(dev)
    thr = pick_threshold(dev_p, [r["flip"] for r in dev])
    res = {
        "threshold": thr,
        "synthetic_dev": binary_scores(dev_p, [r["flip"] for r in dev], thr),
        "synthetic_test": binary_scores(probs(test), [r["flip"] for r in test], thr),
        "default_threshold_0.5_test": None,
    }
    test_p = probs(test)
    res["default_threshold_0.5_test"] = binary_scores(test_p, [r["flip"] for r in test], 0.5)
    if real:
        rp = probs(real)
        res["real"] = {
            "n": len(real), "n_pos": sum(r["flip"] for r in real),
            "caught": sum(p >= thr and r["flip"] for p, r in zip(rp, real)),
            "false_alarms": sum(p >= thr and not r["flip"] for p, r in zip(rp, real)),
        }
        res["real_probs"] = [round(p, 3) for p in rp]
    print(f"flip threshold {thr:.3f}  test {_fmt_bin(res['synthetic_test'])}  real {res.get('real')}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "flip.json").write_text(json.dumps(res, indent=2))
    return res


def _fmt_bin(r: dict) -> str:
    lo, hi = r["ci_f"]
    return f"P {r['p']:.3f} R {r['r']:.3f} F0.5 {r['f']:.3f} [{lo:.3f}, {hi:.3f}] n={r['n']}"
