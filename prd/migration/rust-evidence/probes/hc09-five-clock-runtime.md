# HC-09 Resolve Five-Clock State runtime proof

**Evidence ID:** `S10-HC-09-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `0b3d60cd14056aeafd8b729852ba3dd4c38f846e`

## Decision question

Does the D118 five-clock temporal policy reject every non-governing
substitution when the governing anchor is missing, including wall-clock,
edition order, lifecycle type and other clocks, while still resolving when
the governing anchor is present?

## Execution

```bash
cargo run --offline --quiet -p ln-hc09-runner -- verdict
```

Scenarios:

- `matrix-all-clocks-reject-substitution` — each of five clocks as governing
  with missing anchor rejects all forbidden substitutes;
- `missing-anchor-without-substitutes` — missing governing anchor without
  substitute attempts yields `missing-anchor`;
- `present-anchor-resolves` — present governing anchor yields `resolved`
  without using substitution.

## Objective checks

| Check | Result |
|---|---|
| Five-clock substitution matrix reject | PASS |
| Missing anchor without substitutes | PASS |
| Present anchor resolves without substitution | PASS |
| Wall-clock never authorizes | PASS |
| Substitution never used | PASS |
| Decision trace policy version present | PASS |
| Product storage selected | No |
| Applicable-law claimed | No |

## Interpretation

HC-09 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-09:

```text
9 PASS
0 FAIL
11 unsupported-case
```

Applicable-law / effective-date correctness remains a non-claim.

## Non-claims

- No applicable-law or effective-date correctness proof.
- C10/C12/C13, D116 promotion and D120 publication are not exercised.
- No product storage/backend selected.
