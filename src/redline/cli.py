import argparse
import json
import sys
from pathlib import Path

from redline.flag import Flag


def _read(path: str) -> str:
    return sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")


def _print_flags(text: str, flags: list[Flag], as_json: bool) -> None:
    if as_json:
        print(json.dumps([f.to_dict() for f in flags], ensure_ascii=False))
        return
    if not flags:
        print("No issues found.")
        return
    for f in flags:
        line = text.count("\n", 0, f.start) + 1
        span = text[f.start:f.end].replace("\n", " ")
        if len(span) > 60:
            span = span[:57] + "..."
        print(f"line {line}  [{f.check}/{f.rule}]  \"{span}\"  {f.message}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="redline", description="Check my writing for my own recurring mistakes.")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="check a file, or - for stdin")
    c.add_argument("path", nargs="?", default="-")
    c.add_argument("--no-grammar", action="store_true", help="style rules only (instant)")
    c.add_argument("--json", action="store_true")

    cmp_ = sub.add_parser("compare", help="flag sentences in REWRITE that contradict ORIGINAL")
    cmp_.add_argument("original")
    cmp_.add_argument("rewrite")
    cmp_.add_argument("--json", action="store_true")

    e = sub.add_parser("eval", help="run an eval")
    e.add_argument("which", choices=["grammar", "style", "flip"])
    e.add_argument("--dataset", choices=["conll14", "bea19dev"], default="conll14")
    e.add_argument("--systems", default="redline,languagetool,harper")
    e.add_argument("--limit", type=int)

    sub.add_parser("data", help="download the public eval sets into data/public")

    b = sub.add_parser("build-sets", help="build the personal eval sets from your own writing")
    b.add_argument("--source", action="append", default=[], help="extra text file of your own writing")
    b.add_argument("--public-flips", action="store_true", help="only build synthetic flip pairs from public BEA sentences")

    a = sub.add_parser("label", help="label your own sentences for the style eval")
    a.add_argument("--port", type=int, default=8765)

    ap = sub.add_parser("app", help="run the hotkey app")
    ap.add_argument("--hotkey", default="ctrl+alt+r")

    args = p.parse_args(argv)

    if args.cmd == "check":
        from redline.checker import check

        text = _read(args.path)
        _print_flags(text, check(text, grammar=not args.no_grammar), args.json)
    elif args.cmd == "compare":
        from redline.checker import compare

        rewrite = _read(args.rewrite)
        _print_flags(rewrite, compare(_read(args.original), rewrite), args.json)
    elif args.cmd == "eval":
        from redline.eval import run

        if args.which == "grammar":
            run.run_grammar_eval(args.dataset, args.systems.split(","), limit=args.limit)
        elif args.which == "style":
            run.run_style_eval(["redline-style", *args.systems.split(",")])
        else:
            run.run_flip_eval()
    elif args.cmd == "data":
        from redline.eval.data import download_all

        download_all()
    elif args.cmd == "build-sets":
        from redline.eval.personal import build_public_flip_set, build_sets

        if args.public_flips:
            print(build_public_flip_set())
        else:
            print(build_sets([Path(x) for x in args.source]))
    elif args.cmd == "label":
        from redline.eval.label import serve

        serve(args.port)
    elif args.cmd == "app":
        from redline.app import run_app

        run_app(args.hotkey)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
