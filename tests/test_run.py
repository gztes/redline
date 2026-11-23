import json

from redline.eval.run import run_grammar_eval

M2 = "S He go home .\nA 1 2|||Vform|||goes|||REQUIRED|||-NONE-|||0\n\nS Fine .\nA -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||0\n"


class FakeSystem:
    name = "fake"

    def spans(self, texts):
        return [[(3, 5)] if t.startswith("He") else [] for t in texts]

    def close(self):
        pass


def test_grammar_eval_with_fake_system(tmp_path):
    m2 = tmp_path / "t.m2"
    m2.write_text(M2, encoding="utf-8")
    res = run_grammar_eval("tiny", [FakeSystem()], m2=m2, out_dir=tmp_path, use_cache=False)
    assert res["systems"]["fake"]["f"] == 1.0
    saved = json.loads((tmp_path / "grammar-tiny.json").read_text())
    assert saved["systems"]["fake"]["n_sentences"] == 2
    assert "He go" not in json.dumps(saved)  # no sentence text in published results


from redline.eval.run import run_flip_eval, run_style_eval


def fake_probs(pairs):
    return [0.9 if " not " in b or "below" in b else 0.1 for _, b in pairs]


def test_flip_eval_threshold_from_dev_reported_on_test(tmp_path):
    synth = [
        {"original": "It is good.", "rewrite": "It is not good.", "flip": True, "split": "dev"},
        {"original": "It is big.", "rewrite": "It is large.", "flip": False, "split": "dev"},
        {"original": "It is ok.", "rewrite": "It is not ok.", "flip": True, "split": "test"},
        {"original": "It is hard.", "rewrite": "It is difficult.", "flip": False, "split": "test"},
    ]
    real = [{"original": "far above it", "rewrite": "far below it", "flip": True}]
    res = run_flip_eval(probs_fn=fake_probs, synth=synth, real=real, out_dir=tmp_path)
    assert res["synthetic_test"]["f"] == 1.0
    assert res["real"] == {"n": 1, "n_pos": 1, "caught": 1, "false_alarms": 0}
    assert "It is" not in (tmp_path / "flip.json").read_text()


class StyleFake:
    name = "fake"

    def spans(self, texts):
        return [[(0, 6)] if t.startswith("things") else [] for t in texts]

    def close(self):
        pass


def test_style_eval(tmp_path):
    gold = [{"text": "things are ok", "spans": [[0, 6, "filler"]]}, {"text": "all fine", "spans": []}]
    res = run_style_eval([StyleFake()], gold=gold, out_dir=tmp_path)
    assert res["systems"]["fake"]["f"] == 1.0
