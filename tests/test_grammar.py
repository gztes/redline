import pytest

from redline.grammar import GrammarChecker, diff_flags


def test_replacement_flag():
    src = "He go home."
    flags = diff_flags(src, "He goes home.")
    assert [(src[f.start:f.end], f.suggestion, f.check) for f in flags] == [("go", "goes", "grammar")]


def test_insertion_flags_neighbour_token():
    src = "I home."
    flags = diff_flags(src, "I went home.")
    assert len(flags) == 1
    assert flags[0].end > flags[0].start
    assert "went" in flags[0].suggestion


def test_deletion_flag():
    src = "I went to home."
    flags = diff_flags(src, "I went home.")
    assert [src[f.start:f.end] for f in flags] == ["to"]
    assert flags[0].suggestion == ""


def test_identical_no_flags():
    assert diff_flags("All good here.", "All good here.") == []


def test_offset_applied():
    flags = diff_flags("He go home.", "He goes home.", offset=10)
    assert (flags[0].start, flags[0].end) == (13, 15)


@pytest.mark.model
def test_model_finds_error():
    flags = GrammarChecker().check("She have two cat. This sentence is fine.")
    assert flags
    assert all(f.start < 17 for f in flags)
