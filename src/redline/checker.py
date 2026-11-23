"""One entry point for the CLI, the hotkey app and the eval. Models load once, on first use."""

from functools import lru_cache

from redline.flag import Flag
from redline.style import Rules, check_style, load_rules


@lru_cache(maxsize=1)
def _rules() -> Rules:
    return load_rules()


@lru_cache(maxsize=1)
def grammar_checker():
    from redline.grammar import GrammarChecker

    return GrammarChecker()


@lru_cache(maxsize=1)
def flip_checker():
    from redline.compare import FlipChecker

    return FlipChecker()


def check_style_only(text: str) -> list[Flag]:
    return check_style(text, _rules())


def check(text: str, grammar: bool = True) -> list[Flag]:
    flags = check_style_only(text)
    if grammar:
        flags += grammar_checker().check(text)
    return sorted(flags, key=lambda f: (f.start, f.end))


def compare(original: str, rewrite: str) -> list[Flag]:
    return flip_checker().compare(original, rewrite)
