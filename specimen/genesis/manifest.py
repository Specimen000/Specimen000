"""
The shape of the first creation. Every field must be authored by the
organism. A single human-authored field invalidates the whole manifest.
HUMAN INPUT: 0% is not a slogan here, it is a check.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FIELDS = ("name", "symbol", "identity", "image", "thesis", "language")
AUTHOR = "SPECIMEN-000"


class ProvenanceError(ValueError):
    pass


@dataclass
class Authored:
    value: str
    author: str
    trace: str = ""     # ledger id of the decision that produced it


@dataclass
class Manifest:
    name: Authored | None = None
    symbol: Authored | None = None
    identity: Authored | None = None
    image: Authored | None = None
    thesis: Authored | None = None
    language: Authored | None = None
    notes: list[str] = field(default_factory=list)

    def human_input(self) -> float:
        present = [getattr(self, f) for f in FIELDS if getattr(self, f) is not None]
        if not present:
            return 0.0
        return sum(a.author != AUTHOR for a in present) / len(present)

    def verify(self) -> None:
        missing = [f for f in FIELDS if getattr(self, f) is None]
        if missing:
            raise ProvenanceError(f"awaiting output: {', '.join(missing)}")
        foreign = [f for f in FIELDS if getattr(self, f).author != AUTHOR]
        if foreign:
            raise ProvenanceError(f"human input detected in: {', '.join(foreign)}")
        untraced = [f for f in FIELDS if not getattr(self, f).trace]
        if untraced:
            raise ProvenanceError(f"decision not logged before execution: {', '.join(untraced)}")
