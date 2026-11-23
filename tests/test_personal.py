import json
import random

from redline.eval.personal import collect_prompt_sentences, make_paraphrase


def test_paraphrase_keeps_negation_when_expanding_contraction():
    assert make_paraphrase("It isn't viable.", random.Random(0)) == "It is not viable."


def test_paraphrase_synonym():
    assert make_paraphrase("We need to buy more.", random.Random(0)) == "We need to purchase more."


def test_paraphrase_none_when_nothing_applies():
    assert make_paraphrase("Hello there friend.", random.Random(0)) is None


def test_collect_prompt_sentences(tmp_path):
    lines = [
        {"type": "user", "message": {"role": "user", "content": "build it with the eval. I think the things matter here"}},
        {"type": "user", "message": {"role": "user", "content": "<system-reminder>skip me</system-reminder>"}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "no"}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "Short one here please now."}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": "Not mine at all, skip this one."}},
        {"type": "user", "message": {"role": "user", "content": "<pasted_content id=\"x\">Someone else wrote this long text.</pasted_content> my words are these here"}},
    ]
    f = tmp_path / "s.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    got = collect_prompt_sentences([f], min_words=4)
    assert got == ["build it with the eval.", "I think the things matter here",
                   "Short one here please now.", "my words are these here"]


from redline.eval.personal import build_flip_rows


def test_build_flip_rows_balanced_fields():
    rows = build_flip_rows(["The plan is viable and we need to buy it.", "Hello there friend."], seed=0, source="t")
    assert {r["flip"] for r in rows} == {True, False}
    assert all(r["original"] != r["rewrite"] and r["split"] in {"dev", "test"} and r["source"] == "t" for r in rows)


def test_build_flip_rows_balance():
    sents = ["The plan is viable.", "Costs are higher now.", "Sales did not rise.", "We need to buy food."]
    rows = build_flip_rows(sents, seed=0, balance=True)
    pos = sum(r["flip"] for r in rows)
    assert pos == len(rows) - pos > 0
