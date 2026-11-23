"""Hotkey app: select text in any app, press the hotkey, see flags in a small popup.

Style flags show instantly; grammar flags are appended when the model finishes.
"""

import queue
import threading
import time
import uuid

from redline.flag import Flag


def grab_selection(copy_fn, get_clip, set_clip, timeout: float = 0.4) -> str:
    """Copy the current selection via the clipboard, then put the old clipboard back."""
    try:
        old = get_clip()
    except Exception:
        return ""
    sentinel = f"redline-{uuid.uuid4()}"
    text = ""
    try:
        set_clip(sentinel)
        copy_fn()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = get_clip()
            if value != sentinel:
                text = value or ""
                break
            time.sleep(0.02)
    except Exception:
        text = ""
    finally:
        try:
            set_clip(old)
        except Exception:
            pass
    return text


def format_flags(text: str, flags: list[Flag]) -> list[str]:
    if not flags:
        return ["No issues found."]
    out = []
    for f in flags:
        span = " ".join(text[f.start:f.end].split())
        if len(span) > 50:
            span = span[:47] + "..."
        out.append(f'"{span}"  [{f.check}/{f.rule}]  {f.message}')
    return out


def run_app(hotkey: str = "ctrl+alt+r") -> None:  # pragma: no cover - manual UI
    import tkinter as tk

    import keyboard
    import pyperclip

    from redline.checker import check_style_only, grammar_checker

    print("Loading the grammar model...")
    gc = grammar_checker()
    gc.correct("Warm up.")
    events: queue.Queue = queue.Queue()

    root = tk.Tk()
    root.withdraw()
    state = {"win": None, "box": None}

    def show(lines: list[str], append: bool = False):
        if state["win"] is None or not state["win"].winfo_exists():
            win = tk.Toplevel(root)
            win.title("redline")
            win.attributes("-topmost", True)
            x, y = root.winfo_pointerx(), root.winfo_pointery()
            win.geometry(f"+{x + 12}+{y + 12}")
            box = tk.Text(win, width=80, height=12, wrap="word", font=("Segoe UI", 10), padx=8, pady=6)
            box.pack(fill="both", expand=True)
            win.bind("<Escape>", lambda e: win.destroy())
            state["win"], state["box"] = win, box
        box = state["box"]
        box.configure(state="normal")
        if not append:
            box.delete("1.0", "end")
        for line in lines:
            box.insert("end", line + "\n")
        box.configure(state="disabled")
        state["win"].lift()
        state["win"].focus_force()

    def on_hotkey():
        events.put(("grab", None))

    def worker(text: str):
        flags = gc.check(text)
        events.put(("grammar", (text, flags)))

    def pump():
        try:
            while True:
                kind, payload = events.get_nowait()
                if kind == "grab":
                    keyboard.release(hotkey)
                    text = grab_selection(lambda: keyboard.send("ctrl+c"), pyperclip.paste, pyperclip.copy)
                    if not text.strip():
                        show(["Nothing selected."])
                        continue
                    style = check_style_only(text)
                    show(["Style:"] + format_flags(text, style) + ["", "Grammar: checking..."])
                    threading.Thread(target=worker, args=(text,), daemon=True).start()
                elif kind == "grammar":
                    text, flags = payload
                    show(format_flags(text, flags), append=True)
        except queue.Empty:
            pass
        root.after(50, pump)

    keyboard.add_hotkey(hotkey, on_hotkey)
    print(f"redline is running. Select text anywhere and press {hotkey}. Ctrl+C here to quit.")
    root.after(50, pump)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
