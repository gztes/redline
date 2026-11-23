from redline.sentences import split_sentences


def spans_text(text):
    return [text[a:b] for a, b in split_sentences(text)]


def test_three_sentences():
    assert spans_text("One. Two? Three!") == ["One.", "Two?", "Three!"]


def test_trailing_fragment_is_a_sentence():
    assert spans_text("Done. and then") == ["Done.", "and then"]


def test_empty():
    assert split_sentences("") == []
    assert split_sentences("   \n ") == []


def test_newlines_split_paragraphs():
    assert spans_text("Title line\nBody here.") == ["Title line", "Body here."]
