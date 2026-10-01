"""
Replication metrics for a single cascade: one symbol, many hands.

A cascade is a list of Share events. Each share may name the share it
came from (parent). Variants are compared by text to estimate mutation.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class Share:
    id: str
    t: float                    # seconds since cascade start
    parent: str | None = None
    variant: str = ""           # caption / text / description of this copy


class Cascade:
    def __init__(self, shares: list[Share]):
        if not shares:
            raise ValueError("an empty cascade has nothing to measure")
        self.shares = sorted(shares, key=lambda s: s.t)
        self.by_id = {s.id: s for s in self.shares}
        self.children: dict[str, list[str]] = defaultdict(list)
        for s in self.shares:
            if s.parent is not None and s.parent in self.by_id:
                self.children[s.parent].append(s.id)

    def depths(self) -> dict[str, int]:
        d: dict[str, int] = {}
        for s in self.shares:
            d[s.id] = d[s.parent] + 1 if s.parent in d else 0
        return d

    def reproduction(self) -> float:
        """Mean copies made per copy, over copies old enough to have had children
        (the newest generation is excluded; it would drag the number down)."""
        depth = self.depths()
        last = max(depth.values())
        eligible = [s.id for s in self.shares if depth[s.id] < last]
        if not eligible:
            return 0.0
        return sum(len(self.children[i]) for i in eligible) / len(eligible)

    def half_life(self, bucket: float = 3600.0) -> float | None:
        """Fit exponential decay to activity after the peak. Seconds, or None
        if the cascade has not started to decline."""
        counts = Counter(int(s.t // bucket) for s in self.shares)
        series = [counts.get(i, 0) for i in range(max(counts) + 1)]
        peak = max(range(len(series)), key=series.__getitem__)
        tail = [(i, c) for i, c in enumerate(series[peak:]) if c > 0]
        if len(tail) < 3:
            return None
        xs = [i for i, _ in tail]
        ys = [math.log(c) for _, c in tail]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0.0
        if slope >= 0:
            return None
        return math.log(2) / -slope * bucket

    def mutation(self, threshold: float = 0.9) -> float:
        """Share of copies whose text differs meaningfully from their parent."""
        pairs = [(s, self.by_id[s.parent]) for s in self.shares if s.parent in self.by_id]
        if not pairs:
            return 0.0
        changed = sum(
            1 for c, p in pairs
            if SequenceMatcher(None, c.variant, p.variant).ratio() < threshold
        )
        return changed / len(pairs)
