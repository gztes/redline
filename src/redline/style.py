"""Deterministic style rules: em-dashes, filler words, AI-tell phrases."""

import re
import tomllib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from redline.flag import Flag

EM_DASH = re.compile("—")


@dataclass
class Rules:
    filler: list[str]
    ai_tells: list[str]


def load_rules(path: Path | None = None) -> Rules:
    raw = path.read_bytes() if path else files("redline").joinpath("rules.toml").read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    return Rules(filler=list(data.get("filler", [])), ai_tells=list(data.get("ai_tells", [])))


def _phrase_pattern(phrases: list[str]) -> re.Pattern | None:
    if not phrases:
        return None
    # Longest first so "delve into" wins over "delve".
    parts = [r"\s+".join(map(re.escape, p.split())) for p in sorted(phrases, key=len, reverse=True)]
    return re.compile(r"(?<!\w)(?:" + "|".join(parts) + r")(?!\w)", re.IGNORECASE)


def check_style(text: str, rules: Rules) -> list[Flag]:
    flags: list[Flag] = []
    for m in EM_DASH.finditer(text):
        flags.append(Flag(m.start(), m.end(), "style", "em-dash",
                          "Em-dash reads as AI-written. Use a comma, colon or full stop.", ", "))
    filler = _phrase_pattern(rules.filler)
    if filler:
        for m in filler.finditer(text):
            flags.append(Flag(m.start(), m.end(), "style", "filler",
                              f'"{m.group()}" adds nothing. Cut it or name the specific thing.'))
    tells = _phrase_pattern(rules.ai_tells)
    if tells:
        for m in tells.finditer(text):
            flags.append(Flag(m.start(), m.end(), "style", "ai-tell",
                              f'"{m.group()}" is a common AI-writing phrase.'))
    return sorted(flags, key=lambda f: (f.start, f.end))
