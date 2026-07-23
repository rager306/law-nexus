# SQLite vs Turso crash/recovery probe

**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Disposition:** SQLite remains the authority comparison baseline; Turso remains `defer`  
**Adoption:** none

## Configuration

```text
SQLite wrapper: rusqlite 0.39.0
SQLite linkage: bundled stock SQLite
Turso: 0.7.1 local-only
rows: 40 deterministic synthetic typed events
payload: 4096 deterministic bytes per event
journal: WAL
synchronous: FULL
```

The event schema stores stable operation IDs, source scope, five probe-local
synthetic timestamp fields, payload bytes and SHA-256 digests. These fields do
not implement or exercise D118's five independent clock kinds. No legal text,
vectors, credentials or secrets were used. Turso MVCC, encryption,
multiprocess WAL, FTS, CDC, sync and MCP were not enabled.

## Results

| Backend | Scenario | Result | Evidence |
|---|---|---|---|
| SQLite | Clean commit and reopen | PASS | 40/40 rows, zero digest mismatches, integrity `ok` |
| SQLite | Kill during uncommitted transaction | PASS | 10 pre-transaction rows retained; in-flight rows absent; integrity `ok` |
| SQLite | Kill after commit before explicit checkpoint | PASS | 40/40 committed rows recovered from DB/WAL; integrity `ok` |
| SQLite | Kill during checkpoint | unsupported | No shared controllable checkpoint window; timing was not fabricated |
| SQLite | True ENOSPC | unsupported | Host disk was not filled; a simulated quota was not promoted as kernel evidence |
| SQLite | Clean reopen integrity | PASS | 40/40 rows, zero digest mismatches, integrity `ok` |
| SQLite | Exit to stock SQLite | unsupported | Candidate-only compatibility check |
| Turso | Clean commit and reopen | PASS | 40/40 rows, zero digest mismatches, integrity `ok` |
| Turso | Kill during uncommitted transaction | PASS | 10 pre-transaction rows retained; in-flight rows absent; integrity `ok` |
| Turso | Kill after commit before explicit checkpoint | PASS | 40/40 committed rows recovered from DB/WAL; integrity `ok` |
| Turso | Kill during checkpoint | unsupported | No shared controllable checkpoint window; timing was not fabricated |
| Turso | True ENOSPC | unsupported | Host disk was not filled; a simulated quota was not promoted as kernel evidence |
| Turso | Clean reopen integrity | PASS | 40/40 rows, zero digest mismatches, integrity `ok` |
| Turso | Exit to bundled stock SQLite | PASS | Turso-created DB/WAL reopened read-only; 40/40 rows; integrity `ok` |

Aggregate:

```text
9 PASS
0 FAIL
5 unsupported
```

## Interpretation

The probe confirms bounded local compatibility for clean transactions, rollback
of an uncommitted transaction after process kill, recovery of acknowledged WAL
commits after process kill, deterministic payload integrity, and stock-SQLite
readability of the tested Turso file.

It does not retire the load-bearing upstream risks:

- checkpoint crash atomicity was not exercised;
- true disk-full/ENOSPC behavior was not exercised;
- SQLite Backup API remains unsupported by Turso;
- Turso remains pre-1.0;
- open issues #7952, #7960, #7642 and #6286 remain unresolved;
- no power-loss, filesystem failure, backup/restore, multiprocess, concurrent
  writer or representative-capacity evidence exists.

Therefore Turso remains `defer`. A passing bounded matrix cannot auto-promote the
candidate.

## Reproduce

```bash
cd probes/sqlite-turso-crash-recovery
cargo test --test contracts
mkdir -p .probe-work/manual
cargo run --offline -- matrix .probe-work/manual
```

Runtime files under `.probe-work/` are ignored. The tracked summary is
`prd/migration/rust-evidence/probes/sqlite-turso-crash-recovery.json`.

## Proof ceiling and non-claims

This is process-kill evidence on one host and a tiny synthetic fixture. It does
not prove production durability, physical power-loss safety, legal correctness,
source completeness, retrieval quality, encryption, MVCC, CDC, sync, MCP,
AgentFS, E1-E3 capacity or product adoption. It does not prove D118 temporal
resolution or clock-substitution resistance, and it does not exercise C10, C12
or C13 gates.
