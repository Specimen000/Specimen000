"""
The observation record. Every row must say whether it is simulated.
A row that does not say is rejected: the record cannot be ambiguous
about its own provenance.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

KINDS = {"obs", "conviction", "anomaly", "request", "terminal"}
VOICES = {"terminal", "specimen"}


@dataclass(frozen=True)
class Observation:
    id: str
    kind: str
    voice: str
    text: str
    simulated: bool

    @classmethod
    def from_row(cls, row: dict) -> "Observation":
        if "simulated" not in row:
            raise ValueError(f"{row.get('id', '?')}: provenance missing (field 'simulated')")
        if row["kind"] not in KINDS:
            raise ValueError(f"{row['id']}: unknown kind {row['kind']!r}")
        if row["voice"] not in VOICES:
            raise ValueError(f"{row['id']}: unknown voice {row['voice']!r}")
        return cls(row["id"], row["kind"], row["voice"], row["text"], bool(row["simulated"]))


def read_ledger(path: str | Path) -> list[Observation]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [Observation.from_row(json.loads(l)) for l in lines if l.strip()]
