from redline.app import format_flags, grab_selection
from redline.flag import Flag


class Clip:
    def __init__(self, value, after_copy):
        self.value, self.after_copy, self.history = value, after_copy, []

    def get(self):
        return self.value

    def set(self, v):
        self.history.append(v)
        self.value = v

    def copy(self):
        if self.after_copy is not None:
            self.value = self.after_copy


def test_grab_returns_selection_and_restores_clipboard():
    c = Clip("old", "selected text")
    assert grab_selection(c.copy, c.get, c.set, timeout=0.05) == "selected text"
    assert c.value == "old"


def test_grab_empty_selection_returns_empty():
    c = Clip("old", None)  # copy did nothing: no selection
    assert grab_selection(c.copy, c.get, c.set, timeout=0.05) == ""
    assert c.value == "old"


def test_grab_survives_clipboard_errors():
    def boom():
        raise RuntimeError("clipboard locked")

    assert grab_selection(lambda: None, boom, lambda v: None, timeout=0.01) == ""


def test_format_flags():
    text = "Some things here."
    lines = format_flags(text, [Flag(5, 11, "style", "filler", "adds nothing", None)])
    assert lines == ['"things"  [style/filler]  adds nothing']
    assert format_flags(text, []) == ["No issues found."]
