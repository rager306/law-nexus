# HC-06 Gate Lifecycle runtime proof

**Evidence ID:** `S10-HC-06-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `a4363c61f8cc6b52703555602f8d3c3c477dc3d2`

## Decision question

Does the C10 evidence-kernel gate reject confidence-only and in-place lifecycle
promotion while preserving the original identity/type and minting a new
immutable outcome only when an evidence chain is present?

## Execution

```bash
cargo run --offline --quiet -p ln-hc06-runner -- verdict
```

Scenarios:

- `confidence-only-reject` — high confidence without evidence chain returns
  `insufficient-evidence` / `confidence-only`; original type unchanged;
- `in-place-reject` — request with evidence but `in_place=true` returns
  `invalid-transition` / `in-place-mutation`; original type unchanged;
- `accepted-new-outcome` — evidence chain present and not in-place mints a new
  identity with predecessor and leaves the original extracted-candidate intact.

## Objective checks

| Check | Result |
|---|---|
| Confidence-only rejected | PASS |
| In-place mutation rejected | PASS |
| Accepted path mints new immutable outcome | PASS |
| Original type preserved | PASS |
| Gate version and input-chain digest present | PASS |
| Product storage selected | No |
| Confidence threshold selected | No |

## Interpretation

HC-06 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-06:

```text
6 PASS
0 FAIL
14 unsupported-case
```

## Non-claims

- No numerical confidence threshold or ranking model selected.
- C12/C13, D116 promotion and D120 publication are not exercised.
- No product storage/backend selected.
- No raw legal text, credentials, vectors or external services used.
