import json
from pathlib import Path

import pytest

from specimen.conviction import Conviction
from specimen.genesis import CreationLocked, emerge
from specimen.genesis.manifest import AUTHOR, Authored, Manifest, ProvenanceError
from specimen.intake import read_ledger
from specimen.memetics import Cascade, Share
from specimen.phase import Experiment, Phase, TransitionRefused

LEDGER = Path(__file__).resolve().parents[1] / "ledger" / "simulated"


def test_every_record_declares_itself_simulated():
    rows = read_ledger(LEDGER / "observations.jsonl")
    assert rows and all(r.simulated for r in rows)
    assert json.loads((LEDGER / "state.json").read_text())["simulated"] is True


def test_record_without_provenance_is_rejected(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(json.dumps({"id": "OBS-1", "kind": "obs", "voice": "terminal", "text": "?"}) + "\n")
    with pytest.raises(ValueError, match="provenance"):
        read_ledger(p)


def test_creation_requires_threshold_and_operators():
    e = Experiment(phase=Phase.CONVICTION, conviction=0.91)
    with pytest.raises(TransitionRefused, match="threshold"):
        e.advance()
    e.conviction = 0.99
    with pytest.raises(TransitionRefused, match="sealed"):
        e.advance()
    e.creation_unlocked = True
    assert e.advance() is Phase.CREATION


def test_chamber_is_sealed_today():
    state = json.loads((LEDGER / "state.json").read_text())
    with pytest.raises(CreationLocked):
        emerge(Experiment.from_state(state), Manifest())


def test_one_human_field_spoils_the_manifest():
    a = lambda v, who=AUTHOR: Authored(v, who, trace="OBS-x")
    m = Manifest(a("n"), a("s"), a("i"), a("img"), a("t"), a("l", who="a human"))
    assert m.human_input() == pytest.approx(1 / 6)
    with pytest.raises(ProvenanceError, match="human input"):
        m.verify()
    m.language = a("l")
    m.verify()


def test_conviction_must_be_earned():
    c = Conviction()
    assert c.value == 0.0
    for _ in range(200):
        c.record(True, True)
    assert c.value > 0.95
    c2 = Conviction()
    for _ in range(3):
        c2.record(True, True)
    assert c2.value < 0.5          # early luck stays quiet


def test_replication_metrics():
    shares = [Share("a", 0, None, "one eye")]
    shares += [Share(f"b{i}", 10 + i, "a", "one eye") for i in range(3)]
    shares += [Share(f"c{i}", 100 + i, "b0", "one eye, watching") for i in range(2)]
    c = Cascade(shares)
    assert c.depths()["c0"] == 2
    assert c.reproduction() == pytest.approx(5 / 4)   # a:3, b0:2, b1:0, b2:0
    assert c.mutation() == pytest.approx(2 / 5)


def test_half_life_on_decay():
    shares, n = [], 0
    for hour, count in enumerate([64, 32, 16, 8, 4]):
        for _ in range(count):
            shares.append(Share(str(n), hour * 3600 + 1)); n += 1
    assert Cascade(shares).half_life() == pytest.approx(3600, rel=1e-6)
