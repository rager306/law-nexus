# HC-08 Validate Relation runtime proof

**Evidence ID:** `S10-HC-08-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `437bd53be332b8f2f6f3b7823aee633666750dd2`

## Decision question

Does the C13 evidence-kernel relation registry gate reject unknown predicates
and wrong-owner emissions while keeping the closed registry unchanged and
keeping rejected relations off the query-fact surface?

## Execution

```bash
cargo run --offline --quiet -p ln-hc08-runner -- verdict
```

Scenarios:

- `unknown-predicate-reject` — unknown predicate `relates-to` yields
  `unknown-predicate`; registry unchanged; not a query fact;
- `wrong-owner-reject` — family-B emits family-A owned `amends` yields
  `wrong-owner`; registry unchanged; not a query fact;
- `correct-owner-accept` — family-A emits `amends` with evidence is accepted
  and exposed as a query fact without mutating registry membership.

## Objective checks

| Check | Result |
|---|---|
| Unknown predicate rejected | PASS |
| Wrong-owner rejected | PASS |
| Correct owner with evidence accepted | PASS |
| Registry unchanged on reject | PASS |
| Rejected relations not query facts | PASS |
| C13 version and input-chain digest present | PASS |
| Product storage selected | No |
| Graph schema selected | No |

## Interpretation

HC-08 moves from `unsupported-case` to bounded runtime `PASS`. After HC-01 through HC-08:

```text
8 PASS
0 FAIL
12 unsupported-case
```

## Non-claims

- No graph/database schema selected.
- C10/C12, D116 promotion and D120 publication are not exercised.
- No product storage/backend selected.
