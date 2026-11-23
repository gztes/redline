import io
import json

from redline.cli import main


def test_check_stdin_json_no_grammar(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("a—b"))
    assert main(["check", "-", "--no-grammar", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert [(f["rule"], f["start"], f["end"]) for f in out] == [("em-dash", 1, 2)]


def test_check_file_human_output(tmp_path, capsys):
    p = tmp_path / "t.txt"
    p.write_text("Some things here.", encoding="utf-8")
    assert main(["check", str(p), "--no-grammar"]) == 0
    out = capsys.readouterr().out
    assert "things" in out and "filler" in out


def test_check_clean_says_so(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("Clean."))
    main(["check", "-", "--no-grammar"])
    assert "No issues" in capsys.readouterr().out
