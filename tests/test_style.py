from redline.style import Rules, check_style, load_rules

RULES = Rules(filler=["things", "stuff"], ai_tells=["delve into", "testament to"])


def test_em_dash_flagged():
    flags = check_style("a—b", RULES)
    assert len(flags) == 1
    f = flags[0]
    assert (f.start, f.end, f.rule, f.check) == (1, 2, "em-dash", "style")
    assert f.suggestion == ", "


def test_filler_word_whole_word_only():
    flags = check_style("Some things. somethings thingsy", RULES)
    assert [(f.start, f.end, f.rule) for f in flags] == [(5, 11, "filler")]


def test_ai_tell_case_insensitive():
    flags = check_style("Let us Delve into it.", RULES)
    assert [(f.rule, "Let us Delve into it."[f.start:f.end]) for f in flags] == [("ai-tell", "Delve into")]


def test_unicode_offsets():
    text = "café — things \U0001F600 stuff"
    flags = check_style(text, RULES)
    assert [text[f.start:f.end] for f in flags] == ["—", "things", "stuff"]


def test_clean_text_no_flags():
    assert check_style("A plain sentence.", RULES) == []


def test_default_rules_load():
    rules = load_rules()
    assert "things" in rules.filler
    assert rules.ai_tells
