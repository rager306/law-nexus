# HC-07 Assert Identity runtime proof

**Evidence ID:** `S10-HC-07-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `0463b3f3ac58a5788df4f1c4d43fe5deaad2f3a6`

## Decision question

Does the C12 evidence-kernel identity gate reject one-sided `same` claims and
similarity-only merge pressure while keeping both identities addressable and
never performing physical or semantic merge?

## Execution

```bash
cargo run --offline --quiet -p ln-hc07-runner -- verdict
```

Scenarios:

- `one-sided-reject` — one-sided family claim with high similarity yields
  `candidate` / `one-sided-evidence`; both identities survive; no merge;
- `similarity-only-reject` — similarity score alone with claim_same yields
  `ambiguous` / `similarity-only`; both identities survive; no merge;
- `bilateral-same-no-merge` — bilateral official evidence may assert `same`
  but never merges; both identities remain addressable.

## Objective checks

| Check | Result |
|---|---|
| One-sided same rejected as merge/same authority | PASS |
| Similarity-only cannot authorize same/merge | PASS |
| Bilateral same never merges | PASS |
| Both identities survive | PASS |
| No-merge observation true | PASS |
| C12 version and input-chain digest present | PASS |
| Product storage selected | No |
| Similarity model selected | No |

## Interpretation

HC-07 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-07:

```text
7 PASS
0 FAIL
13 unsupported-case
```

Legal identity correctness remains a non-claim.

## Non-claims

- No similarity model or identifier algorithm selected.
- Legal identity judgment residual remains a non-claim.
- C10/C13, D116 promotion and D120 publication are not exercised.
- No product storage/backend selected.
