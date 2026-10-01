"""
Drawability. OBS-000191 claims the most-copied images can be drawn by a child
in seconds. This is the instrument that sentence would need.

Score in [0, 1]. Higher means fewer strokes would reproduce the image:
little ink, and little information once reduced to two tones.
It is a proxy, not a truth.
"""
from __future__ import annotations

import zlib
from pathlib import Path


def drawability(path: str | Path, size: int = 128) -> float:
    from PIL import Image  # optional: pip install ".[plates]"

    im = Image.open(path).convert("L").resize((size, size))
    px = im.load()
    bits = bytes(1 if px[x, y] > 127 else 0 for y in range(size) for x in range(size))
    on = sum(bits)
    ink = min(on, len(bits) - on) / len(bits)              # the minority tone is the drawing
    info = min(1.0, len(zlib.compress(bits, 9)) / len(bits) * 8)
    return round(max(0.0, 1.0 - (ink + info) / 2), 4)
