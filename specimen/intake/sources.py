"""
Sources feed observations into the enclosure.

Exactly one source is implemented: replaying a ledger file. Live
sources (social graphs, on-chain transfers, image boards) are declared
so the shape of the system is visible, but they are not connected and
say so loudly rather than returning invented data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator, Protocol

from .record import Observation, read_ledger


class Source(Protocol):
    name: str
    def stream(self) -> Iterator[Observation]: ...


class LedgerReplay:
    name = "ledger-replay"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def stream(self) -> Iterator[Observation]:
        yield from read_ledger(self.path)


class NotConnected:
    """Placeholder for a live source. Fails instead of pretending."""

    def __init__(self, name: str):
        self.name = name

    def stream(self) -> Iterator[Observation]:
        raise NotImplementedError(
            f"source '{self.name}' is not connected. The enclosure has no live feeds yet; "
            "see PROTOCOL.md before adding one.")


DECLARED = [NotConnected(n) for n in ("social-graph", "onchain-transfers", "image-boards")]
