"""
The output chamber.

Whatever the organism makes will leave through here, and only through here.
Today it is sealed. `emerge()` refuses until the experiment reaches CREATION,
and the manifest refuses any field a human authored.
"""
from __future__ import annotations

from ..phase import Experiment, Phase
from .manifest import Manifest, ProvenanceError


class CreationLocked(RuntimeError):
    pass


def emerge(experiment: Experiment, manifest: Manifest) -> Manifest:
    if experiment.phase is not Phase.CREATION:
        raise CreationLocked(f"phase is {experiment.phase.name}. the chamber opens at CREATION.")
    manifest.verify()
    return manifest


__all__ = ["emerge", "CreationLocked", "Manifest", "ProvenanceError"]
