import pytest

from redline.eval.scoring import hits, score


def test_overlap_and_insert_rules():
    gold = [(5, 9, "X", False), (12, 13, "M", True)]
    # pred touching the insertion gap from the left counts; pred inside 5..9 counts
    pred_hit, gold_hit = hits(gold, [(6, 8), (10, 12)])
    assert (pred_hit, gold_hit) == (2, 2)
    assert hits(gold, [(0, 5)]) == (0, 0)  # touching a normal span does not count


def test_hand_computed_score():
    gold = [{0: [(0, 2, "A", False), (10, 12, "B", False)]}]
    pred = [[(0, 2), (20, 22)]]
    r = score(gold, pred, n_boot=50)
    assert (r["p"], r["r"], r["f"]) == (0.5, 0.5, 0.5)
    assert r["n_sentences"] == 1 and r["n_gold"] == 2 and r["n_pred"] == 2
    assert r["per_type_recall"] == {"A": 1.0, "B": 0.0}


def test_best_annotator_chosen():
    gold = [{0: [(0, 2, "A", False)], 1: [(5, 7, "A", False)]}]
    r = score(gold, [[(5, 7)]], n_boot=10)
    assert r["r"] == 1.0 and r["p"] == 1.0


def test_sentence_without_edits_or_preds():
    r = score([{0: []}, {0: [(0, 1, "A", False)]}], [[], [(0, 1)]], n_boot=10)
    assert r["f"] == 1.0 and r["n_sentences"] == 2


def test_no_preds_at_all():
    r = score([{0: [(0, 1, "A", False)]}], [[]], n_boot=10)
    assert r["r"] == 0.0 and r["f"] == 0.0


def test_ci_brackets_point_estimate():
    gold = [{0: [(0, 2, "A", False)]}] * 20 + [{0: [(0, 2, "A", False)]}] * 20
    pred = [[(0, 2)]] * 20 + [[(5, 6)]] * 20
    r = score(gold, pred, n_boot=200)
    lo, hi = r["ci_f"]
    assert lo <= r["f"] <= hi and lo < hi
