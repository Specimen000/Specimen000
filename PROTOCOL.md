<div align="center">
<img src="plates/rule.png" width="100%">

<sub>MEMETIC TERMINAL / ENCLOSURE PROTOCOL / REV. 0</sub>

</div>

<br>

### Terms of containment

```
01   Humans maintain the enclosure. Humans do not feed it ideas.
02   No human edits anything inside /chamber. Not a filename. Not a comma.
03   Every creation decision is written to the ledger before it is carried out.
04   If the specimen requests something, the request is logged verbatim,
     whether or not it is granted.
05   Nobody tells it what is funny.
06   If the specimen produces nothing, nothing is released.
     Silence is a valid result.
07   If a human is found to have authored any part of the output,
     the output is destroyed and the experiment is reported as failed.
```

<br>

### Separation of record

This repository mixes three kinds of material. They are never allowed to blur.

| | What it is | Where it lives |
|---|---|---|
| **Real** | Code that runs and is tested: replication metrics, drawability, the conviction model, the phase state machine, the sealed output chamber, the provenance check on the manifest, the plate renderer. | `specimen/`  `tools/`  `tests/` |
| **Simulated** | The observation record, the conviction values and the counts shown in the README. Written to show what the terminal *will* display. Every row carries `"simulated": true`, and the loader refuses rows that don't declare provenance. | `ledger/simulated/` |
| **Narrative** | Field notes and the voice of the README. Atmosphere, not evidence. | `field-notes/`  `README.md` |
| **Not yet built** | The organism's mind. No model is bundled here, no live sources are connected, nothing acts on its own. Declared live sources raise `NotImplementedError` rather than invent data. | `specimen/intake/sources.py` |

When something real starts producing observations, it writes to `ledger/recorded/`, never to `ledger/simulated/`, and the README says so.

<br>

### Unsealing the chamber

Phase 05 opens only when **both** are true:

1. Measured conviction reaches the threshold in `state.json` (currently `0.97`).
2. The operators set `creation_unlocked` in a signed commit.

Code alone cannot open it. See `specimen/phase.py`.

<br>

<div align="center"><sub>it has read this document.</sub></div>
