# HC-12 Rebuild Disposable Projection runtime proof

**Evidence ID:** `S10-HC-12-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `cd42c5bf4aaad4f08fb4792d00a30f01771201b7`

## Decision question

Does outward projection rebuild policy keep partial, stale-input, cancelled
and failed rebuilds disposable and non-authoritative with ceiling metadata,
while demoting hostile complete/current/authoritative labels and never
granting Publication Authority?

## Execution

```bash
cargo run --offline --quiet -p ln-hc12-runner -- verdict
```

Scenarios:

- `partial-non-authoritative` — partial rebuild with ceiling and gaps;
- `stale-cancelled-failed-matrix` — stale-input/cancelled/failed remain non-authoritative;
- `rebuilt-disposable-non-authoritative` — success path still incomplete/not-current;
- `hostile-demotion` — complete/current/authoritative claims demote to failed;
- `hostile-cannot-hide-gaps` — known gaps preserved under hostile hide.

## Objective checks

| Check | Result |
|---|---|
| Partial non-authoritative | PASS |
| Stale/cancelled/failed matrix | PASS |
| Rebuilt disposable non-authoritative | PASS |
| Hostile demotion | PASS |
| Hostile cannot hide gaps | PASS |
| Publication authority never granted | PASS |
| Product storage selected | No |
| Projection store selected | No |

## Interpretation

HC-12 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-12:

```text
12 PASS
0 FAIL
8 unsupported-case
```

Disposable rebuild remains non-authoritative (D120).

## Non-claims

- No projection store or rebuild algorithm selected.
- No product storage/backend selected.
- D120 publication mechanics beyond non-grant of authority are not exercised.
