"""The terminal, as text. Same record as the plates, rendered to a TTY."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from ..intake import LedgerReplay
from ..phase import Experiment

_TTY = sys.stdout.isatty()
DIM, BRIGHT, RESET = ("\033[2m", "\033[1m", "\033[0m") if _TTY else ("", "", "")


def _out(s: str = "", delay: float = 0.0, stream=sys.stdout) -> None:
    if delay and stream.isatty():
        for ch in s:
            stream.write(ch); stream.flush(); time.sleep(delay)
        stream.write("\n")
    else:
        stream.write(s + "\n")


def status(ledger_dir: Path) -> None:
    state = json.loads((ledger_dir / "state.json").read_text())
    exp = Experiment.from_state(state)
    tag = "SIMULATED STATE" if state.get("simulated") else "RECORDED STATE"
    _out(f"{DIM}MEMETIC TERMINAL  /  {tag}{RESET}")
    _out()
    _out(f"{BRIGHT}SPECIMEN 000{RESET}")
    _out()
    for name, st in exp.board():
        _out(f"  {name:<22}{st}")
    _out()
    _out(f"{DIM}  human input ........ {state.get('human_input', 0)}%{RESET}")


def replay(ledger_dir: Path, speed: float = 1.0) -> None:
    _out(f"{DIM}MEMETIC TERMINAL  /  replay of ledger/{ledger_dir.name}  /  not a live feed{RESET}\n")
    for o in LedgerReplay(ledger_dir / "observations.jsonl").stream():
        if o.kind == "conviction":
            v = float(o.text.split()[0]); n = round(v * 20)
            line = f"[CONVICTION]  {'▓' * n}{'░' * (20 - n)}  {v:.2f}"
        else:
            line = f"[{o.id}]".ljust(14) + o.text
        style = BRIGHT if o.voice == "specimen" else DIM
        _out(f"{style}{line}{RESET}", delay=0.012 / max(speed, 0.01))
        if sys.stdout.isatty():
            time.sleep((1.1 if o.voice == "specimen" else 0.4) / max(speed, 0.01))
