import random

from redline.eval.synth import make_flip


def test_negation_removed():
    assert make_flip("The brand has no clear positioning.", random.Random(0)) == "The brand has clear positioning."


def test_direction_swapped():
    out = make_flip("Costs are far below the threshold.", random.Random(0))
    assert out == "Costs are far above the threshold."


def test_negation_inserted():
    out = make_flip("The plan is viable.", random.Random(0))
    assert out == "The plan is not viable."


def test_no_cue_returns_none():
    assert make_flip("Hello there friend.", random.Random(0)) is None


def test_exactly_one_change_and_deterministic():
    s = "Sales did not rise and costs are higher."
    a = make_flip(s, random.Random(3))
    assert a == make_flip(s, random.Random(3))
    diff = [w for w, v in zip(s.split(), a.split()) if w != v]
    assert len(diff) <= 1 or len(a.split()) == len(s.split()) - 1


def test_preserves_capitalisation():
    assert make_flip("Higher prices hurt demand.", random.Random(0)) == "Lower prices hurt demand."
