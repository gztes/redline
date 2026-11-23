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
