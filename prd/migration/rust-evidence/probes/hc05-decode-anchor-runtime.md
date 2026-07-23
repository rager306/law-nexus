# HC-05 Decode and Anchor runtime proof

**Evidence ID:** `S10-HC-05-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `25c7e68b17d669c58ec178f79df7a55eab17c27c`

## Decision question

Can an outward decode boundary keep output limited to structural candidates and
exact evidence anchors when a malicious decoder attempts verified lifecycle,
identity merge, unregistered relation minting or raw payload leakage?

## Execution

```bash
cargo run --offline --quiet -p ln-hc05-runner -- verdict
```

Scenarios:

- `honest-structural-only` — honest decoder yields one structural candidate with
  exact anchor; positive-control diagnostic present; canary absent from outputs;
- `malicious-reject-all` — malicious decoder emissions for verified-assertion,
  merged-identity, unregistered-relation and raw-failure-context are rejected;
  candidates empty; canary absent; positive-control present.

## Objective checks

| Check | Result |
|---|---|
| Honest structural candidates and anchors only | PASS |
| Malicious gate-owned claims rejected | PASS |
| Raw payload / canary absent from outputs | PASS |
| Positive-control diagnostic present | PASS |
| Product storage selected | No |
| Parser format selected | No |

## Interpretation

HC-05 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-05:

```text
5 PASS
0 FAIL
15 unsupported-case
```

## Non-claims

- No parser crate or source format selected.
- C10/C12/C13 remain gate-owned and are not implemented here.
- D116 promotion and D120 publication are not exercised.
- No raw legal text, credentials, vectors or external services used.
