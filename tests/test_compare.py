import numpy as np
import pytest

from redline.compare import FlipChecker, align

VECS = {
    "a": [1, 0, 0], "a2": [0.95, 0.05, 0],
    "b": [0, 1, 0], "b2": [0.05, 0.95, 0],
    "c": [0, 0, 1],
}


def fake_embed(texts):
    m = np.array([VECS[t] for t in texts], dtype=float)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def test_align_pairs_by_similarity():
    assert align(["a", "b"], ["b2", "a2"], fake_embed) == [(1, 0, pytest.approx(0.9986, abs=1e-3)),
                                                         (0, 1, pytest.approx(0.9986, abs=1e-3))]


def test_align_unequal_counts_leave_extras_unmatched():
    pairs = align(["a", "b"], ["a2", "c", "b2"], fake_embed)
    assert [(i, j) for i, j, _ in pairs] == [(0, 0), (1, 2)]


def test_align_is_one_to_one():
    pairs = align(["a"], ["a2", "a"], fake_embed)
    assert len(pairs) == 1


def test_align_empty():
    assert align([], ["a"], fake_embed) == []


@pytest.mark.model
def test_flip_detected():
    rew = "The brand has a defined positioning."
    flags = FlipChecker().compare("The brand has no clear positioning.", rew)
    assert len(flags) == 1
    assert flags[0].check == "meaning-flip"
    assert rew[flags[0].start:flags[0].end] == rew


@pytest.mark.model
def test_paraphrase_not_flagged():
    assert FlipChecker().compare("Sales rose sharply last year.", "Sales increased a lot last year.") == []
