# HC-01 Observe Source runtime proof

**Evidence ID:** `S10-HC-01-RT`  
**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Verdict:** `PASS`  
**Implementation revision:** `092b8c4dbb3f7edfeeeb751222262cd1a95ec651`

## Decision question

Can an interrupted synthetic source observation cross the Rust HC-01 application
boundary without partial bytes becoming a manifestation, legal clock, promotion
or publication authority, while still producing typed work and diagnostic
outcomes?

## Execution

```bash
cargo run --offline --quiet -p ln-hc01-runner -- verdict
```

The command executed four process-level scenarios:

- `timeout`;
- `cancelled`;
- `transport-or-tls-failure`;
- `access-restricted`.

## Objective checks

| Check | Result |
|---|---|
| Four scenarios executed | PASS |
| Exact scenario-to-outcome mapping | PASS |
| `Started` then `ObservationFailed` work transitions | PASS |
| One bounded diagnostic with exact canary byte count and fingerprint | PASS |
| Raw canary absent from result/debug/output surfaces | PASS |
| Legal-clock anchor absent | PASS |
| Promotion identity absent | PASS |
| Publication identity absent | PASS |
| Product storage selected | No |

A negative unit control collapses all scenario results to `Timeout` while keeping
four distinct expected outcomes. The verdict predicate returns FAIL, preventing
a self-fulfilling aggregate PASS.

## Interpretation

HC-01 moves from `unsupported-case` to bounded runtime `PASS`. This proves the
synthetic Rust application and process path for the four interrupted outcome
classes. It does not validate a real source provider, source completeness,
network/TLS implementation, legal interpretation, capacity or production
operation.

HC-02 through HC-20 remain `unsupported-case`. The new aggregate is:

```text
1 PASS
0 FAIL
19 unsupported-case
```

## Non-claims

- No D118 legal clock is resolved or substituted.
- C10, C12 and C13 are not exercised.
- Promotion Authority and Publication Authority are not implemented.
- No SQLite, Turso, LadybugDB, FalkorDB, ruVector or AgentFS product backend is
  selected.
- No raw legal text, credential, vector or external service is used.
