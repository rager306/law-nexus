# HC-04 Commit Curated Promotion runtime proof

**Evidence ID:** `S10-HC-04-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `a28323cdcb21402dac4d4f86f482dcbc1e3e3fae`

## Decision question

Do cancel, identical retry and mismatched identity/digest reuse preserve one
D116 curated-promotion effect without granting publication authority?

## Execution

```bash
cargo run --offline --quiet -p ln-hc04-runner -- verdict
```

Scenarios:

- `cancel-no-effect` — cancel mid-attempt leaves no curated commit;
- `identical-retry-one-commit` — after cancel, commit once then retry yields
  `already-committed` with the same identity/digest and cardinality 1;
- `mismatch-reject` — same operation identity with different digest is rejected
  without minting a second commit.

## Objective checks

| Check | Result |
|---|---|
| Cancel leaves no curated effect | PASS |
| Identical retry one commit / already-committed | PASS |
| Mismatched reuse rejected | PASS |
| One D116 effect | PASS |
| Publication authority absent | PASS |
| Product storage selected | No |

## Interpretation

HC-04 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-04:

```text
4 PASS
0 FAIL
16 unsupported-case
```

## Non-claims

- No product filesystem dual-write or storage mechanism selected.
- D120 publication is not implemented and is not granted by promotion success.
- D118 clocks and C10/C12/C13 are not exercised.
- No raw legal text, credentials, vectors or external services used.
