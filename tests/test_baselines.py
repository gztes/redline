import pytest

from redline.eval.baselines import Harper, LanguageToolLocal, RedlineGrammar

TEXTS = ["She have two cat.", "This sentence is fine.", "café owners is happy."]


@pytest.mark.model
@pytest.mark.parametrize("system_cls", [RedlineGrammar, Harper, LanguageToolLocal])
def test_system_returns_one_span_list_per_text(system_cls):
    system = system_cls()
    spans = system.spans(TEXTS)
    assert len(spans) == 3
    assert spans[0], f"{system.name} found nothing in an obvious error"
    for text, ss in zip(TEXTS, spans):
        for a, b in ss:
            assert 0 <= a <= b <= len(text)
    system.close()
