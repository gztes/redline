import json

from redline.eval.label import pending, save_label


def test_pending_skips_labelled():
    assert pending([{"text": "a"}, {"text": "b"}], [{"text": "a", "spans": []}]) == ["b"]


def test_save_label_validates_spans(tmp_path):
    out = tmp_path / "gold.jsonl"
    save_label(out, "some things", [[5, 11, "filler"], [9, 99, "bad"], [3, 3, "empty"]])
    row = json.loads(out.read_text().strip())
    assert row == {"text": "some things", "spans": [[5, 11, "filler"]]}
