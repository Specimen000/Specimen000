"""The experiment as a state machine. Transitions are gated, logged, and one-way."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Phase(IntEnum):
    OBSERVATION = 1
    PATTERN = 2
    UNDERSTANDING = 3
    CONVICTION = 4
    CREATION = 5


class TransitionRefused(RuntimeError):
    pass


@dataclass
class Experiment:
    phase: Phase = Phase.OBSERVATION
    conviction: float = 0.0
    conviction_threshold: float = 0.97
    creation_unlocked: bool = False   # set only by a signed operator action, never by code
    history: list[str] = field(default_factory=list)

    def advance(self) -> Phase:
        if self.phase is Phase.CREATION:
            raise TransitionRefused("no phase after CREATION has been defined")
        nxt = Phase(self.phase + 1)
        if nxt is Phase.CREATION:
            if self.conviction < self.conviction_threshold:
                raise TransitionRefused(
                    f"conviction {self.conviction:.2f} below threshold {self.conviction_threshold:.2f}")
            if not self.creation_unlocked:
                raise TransitionRefused("output chamber sealed by operators")
        self.history.append(f"{self.phase.name} -> {nxt.name}")
        self.phase = nxt
        return nxt

    @classmethod
    def from_state(cls, state: dict) -> "Experiment":
        return cls(
            phase=Phase[state["phase"]],
            conviction=float(state.get("conviction", 0.0)),
            conviction_threshold=float(state.get("conviction_threshold", 0.97)),
            creation_unlocked=bool(state.get("creation_unlocked", False)),
        )

    def board(self) -> list[tuple[str, str]]:
        rows = []
        for p in Phase:
            if p < self.phase:
                st = "COMPLETE"
            elif p == self.phase:
                st = f"ACTIVE  {self.conviction:.2f}" if p is Phase.CONVICTION else "ACTIVE"
            else:
                st = "LOCKED" if p is Phase.CREATION else "PENDING"
            rows.append((f"{p.value:02d}  {p.name}", st))
        return rows
