from redline.eval.m2 import gold_char_spans, parse_m2

M2 = """S He go to school every days .
A 1 2|||Vform|||goes|||REQUIRED|||-NONE-|||0
A 5 6|||Nn|||day|||REQUIRED|||-NONE-|||0
A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||1

S I like it .
A 1 1|||Mec|||really|||REQUIRED|||-NONE-|||0
"""


def test_parse_two_annotators_with_noop(tmp_path):
    p = tmp_path / "t.m2"
    p.write_text(M2, encoding="utf-8")
    sents = parse_m2(p)
    assert len(sents) == 2
    assert sents[0].tokens[1] == "go"
    assert sents[0].edits == {0: [(1, 2, "Vform"), (5, 6, "Nn")], 1: []}
    assert sents[1].edits == {0: [(1, 1, "Mec")], 1: []}


def test_gold_char_spans(tmp_path):
    p = tmp_path / "t.m2"
    p.write_text(M2, encoding="utf-8")
    s0, s1 = parse_m2(p)
    text, spans = gold_char_spans(s0)
    assert text == "He go to school every days."
    assert [(text[a:b], t, ins) for a, b, t, ins in spans[0]] == [("go", "Vform", False), ("days", "Nn", False)]
    assert spans[1] == []
    text1, spans1 = gold_char_spans(s1)
    # insertion between "I" and "like": the gap from end of "I" to start of "like"
    assert spans1[0] == [(1, 2, "Mec", True)]


def test_missing_annotator_means_no_edits(tmp_path):
    p = tmp_path / "t.m2"
    p.write_text("S A b .\nA 1 2|||X|||c|||REQUIRED|||-NONE-|||1\n\nS Fine .\n\nS C d .\nA 0 1|||Y|||e|||REQUIRED|||-NONE-|||0\n",
                 encoding="utf-8")
    s = parse_m2(p)
    assert s[0].edits == {0: [], 1: [(1, 2, "X")]}
    assert s[1].edits == {0: [], 1: []}
    assert s[2].edits == {0: [(0, 1, "Y")], 1: []}
