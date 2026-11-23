from redline.eval.detok import detokenize


def check(tokens, expected):
    text, offs = detokenize(tokens)
    assert text == expected
    assert [text[a:b] for a, b in offs] == tokens


def test_contractions_and_punct():
    check(["I", "do", "n't", "know", "."], "I don't know.")


def test_brackets():
    check(["(", "a", ")", "b", ","], "(a) b,")


def test_quotes_toggle():
    check(["He", "said", '"', "hi", '"', "."], 'He said "hi".')


def test_possessive():
    check(["John", "'s", "car"], "John's car")


def test_empty():
    assert detokenize([]) == ("", [])
