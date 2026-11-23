from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Flag:
    """One problem found in a text: a character span plus why it was flagged."""

    start: int
    end: int
    check: str  # "style" | "grammar" | "meaning-flip"
    rule: str
    message: str
    suggestion: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
