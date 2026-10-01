"""
Conviction: how sure the organism is that it understands why things spread.

Modelled as a Beta posterior over "the current theory predicts spread".
Each scored prediction adds evidence. Conviction is the posterior mean,
discounted by how uncertain the posterior still is. It cannot be set
directly; it can only be earned by predictions resolving.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Conviction:
    hits: float = 1.0     # Beta(1, 1) prior: no opinion
    misses: float = 1.0

    def record(self, predicted_spread: bool, did_spread: bool, weight: float = 1.0) -> None:
        if weight < 0:
            raise ValueError("evidence weight cannot be negative")
        if predicted_spread == did_spread:
            self.hits += weight
        else:
            self.misses += weight

    @property
    def mean(self) -> float:
        return self.hits / (self.hits + self.misses)

    @property
    def spread(self) -> float:
        a, b = self.hits, self.misses
        return math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))

    @property
    def value(self) -> float:
        """Mean minus two standard deviations, floored at zero. Loud early luck stays quiet."""
        return max(0.0, self.mean - 2 * self.spread)
