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


from redline.grammar import chunk_long


def test_chunk_long_keeps_short_spans():
    assert chunk_long("Short one.", [(0, 10)], max_words=5) == [(0, 10)]


def test_chunk_long_splits_at_clause_boundaries():
    text = "one two three, four five six; seven eight nine, ten."
    chunks = chunk_long(text, [(0, len(text))], max_words=4)
    assert all(len(text[a:b].split()) <= 4 for a, b in chunks)
    assert "".join(text[a:b] for a, b in chunks).replace(" ", "") == text.replace(" ", "")


def test_chunk_long_hard_splits_without_punctuation():
    text = " ".join(["w"] * 10)
    chunks = chunk_long(text, [(0, len(text))], max_words=4)
    assert [len(text[a:b].split()) for a, b in chunks] == [4, 4, 2]


class _FakeChecker:
    def __init__(self):
        from redline.grammar import GrammarChecker

        self.gc = GrammarChecker()
        self.gc.correct_batch = lambda sents: sents  # identity "model"


def test_check_long_sentence_no_spurious_flags():
    gc = _FakeChecker().gc
    text = ("word " * 300).strip() + "."
    assert gc.check(text) == []


def test_check_many_matches_check():
    gc = _FakeChecker().gc
    gc.correct_batch = lambda sents: [s.replace(" go ", " goes ") for s in sents]
    texts = ["He go home. She go too.", "Fine.", ""]
    assert gc.check_many(texts) == [gc.check(t) for t in texts]
    assert len(gc.check_many(texts)[0]) == 2


def test_eval_system_uses_check_path():
    from redline.eval.baselines import RedlineGrammar

    sys_ = RedlineGrammar.__new__(RedlineGrammar)
    sys_.checker = _FakeChecker().gc
    sys_.checker.correct_batch = lambda sents: [s.replace(" go ", " goes ") for s in sents]
    assert sys_.spans(["He go home."]) == [[(3, 5)]]
