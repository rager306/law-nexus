# Storage, ledger and workspace candidate assessment

**Date:** 2026-07-23  
**Lifecycle:** `[bounded]`  
**Decision owner:** ADR-0012 evidence protocol  
**Product adoption:** none

## Decision question

Which local storage candidates should be probed for the authoritative typed
evidence/event ledger, graph/vector projection and agent workspace without
collapsing those roles or promoting documentation and small smoke tests into
product selection?

## Candidate matrix

| Candidate | Role | Disposition | Current evidence | Proof ceiling |
|---|---|---|---|---|
| SQLite | Authoritative ledger comparison baseline | `adopt` as baseline only | Mature WAL, tooling, backup and recovery ecosystem; bounded crash/reopen matrix | No product ledger cutover; no E1-E3 or legal correctness proof |
| Turso Database | Future pure-Rust SQLite-compatible ledger candidate | `defer` | Active Rust engine; bounded crash matrix `9 PASS / 0 FAIL / 5 unsupported`; pre-1.0 compatibility and durability gaps remain | No authority adoption, checkpoint/ENOSPC or production durability claim |
| LadybugDB | Graph/vector/FTS projection | `separate-role`, candidate | Active Kùzu successor; local GitNexus graph/FTS/VECTOR runtime works on this host | No legal authority or law-nexus schema/capacity proof |
| ruVector | Agent runtime, memory, adaptive retrieval and optional hypergraph/vector computation | `separate-role`, candidate | Agent crates and graph mechanics have bounded source/test evidence | No authority, legal correctness or production recovery proof |
| AgentFS | Disposable agent COW workspace and audit | `defer`, `separate-role` | Official beta COW/session/audit/MCP documentation | No OS sandbox, base immutability or audit-completeness runtime proof |

`adopt as baseline` means reference implementation for comparison, not a selected
or implemented law-nexus product database.

## Turso Database assessment

Repository and revision observed on 2026-07-23:

```text
repository: https://github.com/tursodatabase/turso
source HEAD: fae58dc3ee11aaad12dff21bbb27089083231319
workspace version: 0.8.0-pre.1
probe crate version: 0.7.1 (published stable, exact pin)
license: MIT
```

Positive evidence:

- in-process SQLite-compatible engine written in Rust;
- SQLite on-disk model, pager, B-tree and WAL implementation;
- async Rust API and local-file mode;
- active deterministic simulation, differential and fault-testing work;
- explicit compatibility contract and experimental-feature gates;
- optional cloud/sync surfaces are not required for local operation.

Negative and transferability evidence:

- pre-1.0; upstream recommends independent backups until 1.0;
- incomplete SQLite parity and documentation drift;
- SQLite Backup API unsupported;
- rollback journals unsupported;
- only `OFF` and `FULL` synchronous modes supported;
- MVCC, encryption and multiprocess WAL remain experimental for critical use;
- Tantivy FTS and vector surfaces do not improve the authoritative ledger role;
- cloud sync and database MCP expand authority risk and remain forbidden;
- concurrent writers are not required for the single-authority append path.

Open issues checked through GitHub API on 2026-07-23:

| Issue | State | Consequential failure class |
|---|---|---|
| [#7952](https://github.com/tursodatabase/turso/issues/7952) | open | Checkpoint backfill not crash-atomic under default durability |
| [#7960](https://github.com/tursodatabase/turso/issues/7960) | open | MVCC passive checkpoint data loss and pager panic |
| [#7642](https://github.com/tursodatabase/turso/issues/7642) | open | DatabaseFull checkpoint failure followed by leaked root mapping/short read |
| [#6286](https://github.com/tursodatabase/turso/issues/6286) | open | `temp.` namespace alias can drop a main table |

These reports do not prove that every ordinary Turso database loses data. They
do block an authoritative legal-ledger selection until the failure classes are
retired or proven inapplicable to the exact configuration.

## Executable SQLite vs Turso probe

The isolated probe lives at:

```text
probes/sqlite-turso-crash-recovery/
```

It pins bundled stock SQLite through `rusqlite 0.39.0` and local Turso `0.7.1`.
Bundled C SQLite is comparison-probe linkage only, not a product-runtime storage
selection. Both engines use a deterministic synthetic typed-event schema with
five probe-local timestamp fields, stable operation IDs, payload digests, WAL
and `synchronous=FULL`. Those fields do not implement or exercise D118's five
independent clock kinds.

Runnable bounded scenarios:

- clean commit and reopen;
- parent `SIGKILL` while a transaction is uncommitted;
- parent `SIGKILL` after commit and before an explicitly requested checkpoint;
- fresh-connection row, payload digest and integrity checks;
- Turso-created file reopened by bundled stock SQLite.

Honest unsupported scenarios:

- a controllable cross-engine kill window inside checkpoint;
- true kernel/volume ENOSPC without a dedicated bounded filesystem.

The probe does not enable MVCC, encryption, multiprocess WAL, FTS, CDC, cloud
sync or MCP. The 2026-07-23 matrix produced `9 PASS / 0 FAIL / 5 unsupported`:
both engines passed clean commit, uncommitted-transaction kill, post-commit kill
and clean reopen; Turso also passed reopening through bundled stock SQLite.
Checkpoint-window and true ENOSPC scenarios remain unsupported. Results cannot
auto-promote Turso; they only refine its `defer` or support a later
`reject`/revisit packet. Durable results are recorded in
`prd/migration/rust-evidence/probes/sqlite-turso-crash-recovery.md` and `.json`.

## AgentFS role

LadybugDB remains a separate non-authoritative projection/proof-spike candidate
and does not replace the deferred FalkorDB product-graph direction. Neither may
become D116 Promotion Authority, D120 Publication Authority or sole legal-graph
truth through this assessment.

AgentFS is assessed separately in:

```text
prd/research/agentfs-filesystem-isolation-assessment-2026-07-23.md
```

It may be useful as a disposable COW filesystem and audit substrate for agent
runs. It is beta, does not replace an OS process sandbox, and must never contain
or mutate authoritative legal evidence, source truth or GSD authority state.
Cloud sync and remote exposure are outside the bounded role.

## Re-evaluation gates

Turso remains `defer` until all applicable gates pass:

1. stable release maturity or an explicitly justified exception stronger than
   the pre-1.0 vendor claim;
2. required SQLite compatibility and backup/restore surfaces implemented;
3. issues #7952, #7960, #7642 and #6286 closed or proven inapplicable;
4. no experimental feature underwrites authority durability;
5. the local crash/reopen/stock-exit probe passes at the exact proposed version;
6. a bounded checkpoint and true ENOSPC probe runs on an isolated filesystem;
7. deterministic backup, restore and exit-to-stock-SQLite drills pass;
8. representative capacity remains within host envelope;
9. authority remains single-writer, append-only and inaccessible to agent MCP;
10. a fresh human-reviewed ADR-0012 packet records any status change.

AgentFS remains `defer` until its separate base-immutability, symlink/path escape,
crash/reopen, MCP filtering, audit completeness and resource-growth probes pass.
Even then its maximum role remains non-authoritative workspace state unless a
new decision explicitly changes that boundary.

## Non-selection and proof ceiling

- No database, ledger implementation, graph backend or workspace technology is
  selected for product adoption by this assessment.
- SQLite is a comparison baseline, not an implemented product cutover.
- Turso remains `defer` even if the bounded probe passes.
- LadybugDB and ruVector occupy separate projection and agent roles.
- AgentFS is not an OS sandbox or legal evidence store.
- No claim is made about legal correctness, source completeness, retrieval
  quality, E1-E3 capacity, power-loss durability, production security or
  production readiness.
- The crash probe does not prove D118 temporal resolution or clock-substitution
  resistance and does not exercise C10, C12 or C13 gates.

## Primary evidence anchors

Checked 2026-07-23:

- <https://github.com/tursodatabase/turso>
- <https://github.com/tursodatabase/turso/blob/main/COMPAT.md>
- <https://github.com/tursodatabase/turso/blob/main/docs/manual.md>
- <https://github.com/tursodatabase/turso/blob/main/docs/internals/mvcc/RECOVERY_SEMANTICS.md>
- <https://github.com/tursodatabase/turso/issues/7952>
- <https://github.com/tursodatabase/turso/issues/7960>
- <https://github.com/tursodatabase/turso/issues/7642>
- <https://github.com/tursodatabase/turso/issues/6286>
- <https://docs.turso.tech/agentfs/introduction>
- <https://github.com/tursodatabase/agentfs>
- `doc/adr/0012-consequential-evidence-protocol.md`
- `prd/architecture/m111-final-architecture-baseline.md`
