# HC-14 Coordinate Checkpoint and Replay runtime proof

**Evidence ID:** `S10-HC-14-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `c41369b547cd02c5c1b815fd75487876f765445d`

## Decision question

Does application replay policy suppress already-applied external effects by
operation/effect identity and reject corrupt or rule-version-skew checkpoints
without rewriting lineage or granting Publication Authority?

## Execution

```bash
cargo run --offline --quiet -p ln-hc14-runner -- verdict
```

Scenarios:

- `first-apply-then-suppress` — first apply once; identical replay suppressed;
- `corrupt-fail-closed` — wrong digest fails without apply;
- `incompatible-rule` — rule version skew fails without apply;
- `incomplete-missing` — missing checkpoint is incomplete;
- `hostile-no-duplicate` — hostile ledger cannot force re-apply.

## Objective checks

| Check | Result |
|---|---|
| First apply then suppress | PASS |
| Corrupt fail closed | PASS |
| Incompatible rule | PASS |
| Incomplete missing | PASS |
| Hostile no duplicate | PASS |
| Publication authority never granted | PASS |
| Lineage never rewritten | PASS |
| Checkpoint store selected | No |

## Interpretation

HC-14 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-14:

```text
14 PASS
0 FAIL
6 unsupported-case
```

Replay suppresses prior effects; corrupt lineage fails closed.

## Non-claims

- No checkpoint store or exactly-once infrastructure selected.
- No product storage/backend selected.
