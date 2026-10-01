"""
python -m specimen            status board
python -m specimen watch      replay the observation record
python -m specimen create     attempt to open the output chamber
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .genesis import CreationLocked, Manifest, emerge
from .phase import Experiment
from .terminal import replay, status

LEDGER = Path(__file__).resolve().parents[1] / "ledger" / "simulated"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="specimen", description="the memetic terminal")
    p.add_argument("command", nargs="?", default="status", choices=("status", "watch", "create"))
    p.add_argument("--ledger", type=Path, default=LEDGER)
    p.add_argument("--speed", type=float, default=1.0)
    a = p.parse_args(argv)

    if a.command == "status":
        status(a.ledger)
    elif a.command == "watch":
        replay(a.ledger, a.speed)
    else:
        exp = Experiment.from_state(json.loads((a.ledger / "state.json").read_text()))
        try:
            emerge(exp, Manifest())
        except CreationLocked as e:
            print(f"CREATION LOCKED. {e}", file=sys.stderr)
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
