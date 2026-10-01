# ledger

The record of what the terminal saw.

```
simulated/      demo record. written by hand to show the format and the arc.
                every row: "simulated": true. not produced by any model.
recorded/       does not exist yet. created the first time a real source writes.
```

Row format (`observations.jsonl`):

```json
{"id": "OBS-000184", "kind": "obs", "voice": "terminal", "text": "...", "simulated": true}
```

`kind` is one of `obs  conviction  anomaly  request  terminal`.
`voice` is `terminal` (the instrument speaking) or `specimen` (the organism speaking).

The plates in `/plates` are rendered from this directory. Change the record and
the images follow (`python tools/render_plates.py`, or the `enclosure` workflow).
