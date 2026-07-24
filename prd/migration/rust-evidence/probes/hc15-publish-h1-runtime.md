# HC-15: Publish Authoritative H1 Unit — Runtime Proof

**Evidence ID:** `S10-HC-15-RT`
**Case ID:** HC-15
**Verdict:** PASS `[bounded]`
**Generated:** 2026-07-24
**Implementation revision:** `cea36e3`
**Command:** `cargo run --offline --quiet -p ln-hc15-runner -- verdict`

## Scenarios

| Scenario | Pass | Description |
|----------|------|-------------|
| first-complete-publish | ✅ | Complete candidate first publish is authoritative |
| identical-duplicate | ✅ | Identical operation/digest returns Duplicate, same unit |
| competing-writer-rejected | ✅ | Competing writer for same scope is rejected, first unit unchanged |
| partial-incomplete | ✅ | Partial candidate is Incomplete and non-authoritative |
| hostile-dual-writer-one-authority | ✅ | Hostile dual-writer ledger cannot mint second authority |

## Aggregate

- Runtime PASS: 15/20
- Runtime FAIL: 0/20
- Unsupported-case: 5/20 (HC-16 through HC-20)

## Non-claims

- This proof does not select a product storage, fencing, or transaction infrastructure.
- Application-owned publication authority is synthetic only; product durability is unproven.
- No SQLite, Turso, LadybugDB, FalkorDB, ruVector or AgentFS product backend is selected.
- HC-16 through HC-20 remain unsupported-case.
