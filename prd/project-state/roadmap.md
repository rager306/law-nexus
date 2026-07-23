# Roadmap

> **Source of truth:** `prd/ARCHITECTURE.md` and GSD state. This document is a
> non-authoritative cold-reader projection of
> `prd/project-state/data/roadmap.json`.
>
> Refreshed 2026-07-23 after M122 completion.

## Current position

- **Latest completed milestone:** M122-0jpqp4, HC 10 Transition Work State Runtime Proof.
- **Active milestone:** none (plan HC-11 next).
- **M111 result:** final `[bounded]` implementation-neutral semantic baseline for heterogeneous Russian legal evidence.
- **M112 result:** ADR-0005 topology superseded; ADR-0008 through ADR-0012 authored `[bounded]`; executable ADR/decision/owner drift checks active in pre-commit and CI.
- **M113 result:** first hostile-case Rust runtime proof. `S10-HC-01-RT` is bounded PASS.
- **M114 result:** second hostile-case Rust runtime proof. `S10-HC-02-RT` is bounded PASS.
- **M115 result:** third hostile-case Rust runtime proof. `S10-HC-03-RT` is bounded PASS.
- **M116 result:** fourth hostile-case Rust runtime proof. `S10-HC-04-RT` is bounded PASS.
- **M117 result:** fifth hostile-case Rust runtime proof. `S10-HC-05-RT` is bounded PASS.
- **M118 result:** sixth hostile-case Rust runtime proof. `S10-HC-06-RT` is bounded PASS.
- **M119 result:** seventh hostile-case Rust runtime proof. `S10-HC-07-RT` is bounded PASS.
- **M120 result:** eighth hostile-case Rust runtime proof. `S10-HC-08-RT` is bounded PASS.
- **M121 result:** ninth hostile-case Rust runtime proof. `S10-HC-09-RT` is bounded PASS.
- **M122 result:** tenth hostile-case Rust runtime proof. `S10-HC-10-RT` is bounded PASS.
- **M123 progress:** `S10-HC-11-RT` is bounded PASS. Current aggregate is **11 PASS / 0 FAIL / 9 unsupported-case**.
- **Product target:** Rust-only runtime under ADR-0004; Python may remain only as ADR-0007 subprocess repository harness.
- **Implementation topology:** not selected. Database, FalkorDB schema, storage, queue/ledger, product crate map, API, concurrency runtime and deployment remain evidence-gated future decisions.
- **Product readiness:** not proven.

## Completed milestone bands

| Range | Theme | Boundary |
|---|---|---|
| M001-M034 | Architecture, parser direction, FalkorDB/retrieval evidence and source structuring | Foundational and bounded proof, not product readiness. |
| M035-M067 | ACP/git-lex construction and externalization | Closed historical era; derived projections are non-authoritative. |
| M068-M085 | Onion architecture, compliance gates, parser foundation and repository health | Structural and parser groundwork; no whole-system parity. |
| M086-M110 | Debt repair, corpus stabilization, Rust-only transition, ACP/git-lex decommission, first Rust tracer and capability evidence map | Rust workspace/harness and bounded acceptance evidence exist; product/domain parity remains unproven. |
| M111-M112 | Zero-based legal evidence architecture and post-M111 ADR synchronization | Semantic owners, authorities, clocks, gates and hostile oracles are bounded; ADR enforcement is executable. |
| M113-M113 | HC-01 Observe Source first Rust hostile-case runtime proof | Bounded synthetic interrupted-source PASS only; 19 hostile cases remain unsupported; no product storage/backend selection. |
| M114-M114 | HC-02 Inventory Immutable Intake second Rust hostile-case runtime proof | Bounded synthetic re-inventory PASS; 18 hostile cases remained unsupported at that point. |
| M115-M115 | HC-03 Dispose Review third Rust hostile-case runtime proof | Bounded synthetic non-accepted rejection PASS; 17 hostile cases remain unsupported; no product storage/backend selection. |
| M116-M116 | HC-04 Commit Curated Promotion fourth Rust hostile-case runtime proof | Bounded synthetic cancel/retry/mismatch PASS; 16 hostile cases remain unsupported; no product storage/backend selection. |
| M117-M117 | HC-05 Decode and Anchor fifth Rust hostile-case runtime proof | Bounded synthetic honest/malicious decoder PASS; 15 hostile cases remain unsupported; no product storage/parser-format selection. |
| M118-M118 | HC-06 Gate Lifecycle sixth Rust hostile-case runtime proof | Bounded synthetic confidence-only/in-place rejection PASS; 14 hostile cases remain unsupported; no product storage/confidence-threshold selection. |
| M119-M119 | HC-07 Assert Identity seventh Rust hostile-case runtime proof | Bounded synthetic one-sided/similarity reject and bilateral same without merge PASS; 13 hostile cases remain unsupported; legal identity residual non-claim; no similarity model selected. |
| M120-M120 | HC-08 Validate Relation eighth Rust hostile-case runtime proof | Bounded synthetic unknown/wrong-owner rejection PASS; 12 hostile cases remain unsupported; no product storage/graph-schema selection. |
| M121-M121 | HC-09 Resolve Five-Clock State ninth Rust hostile-case runtime proof | Bounded synthetic five-clock forbidden-substitution matrix PASS; 11 hostile cases remain unsupported; applicable-law/effective-date remain non-claims; no product storage selected. |
| M122-M122 | HC-10 Transition Work State tenth Rust hostile-case runtime proof | Bounded synthetic cancel/resume domain freeze and progress-to-legal rejection PASS; 10 hostile cases remain unsupported; no product storage or workflow engine selected. |

## M111 semantic baseline

M111 selected:

- D116 sole Promotion Authority, separate from D120 Publication Authority;
- D118 five clocks with no silent substitution;
- D119 compositional evidence kernel with inward C10/C12/C13;
- D120 complete immutable H1-only authority with provisional outputs always non-authoritative, incomplete and not-current;
- D123 KOF-DA with exactly twenty primary capability owners;
- HC-01 through HC-20 and twelve selection-time rejection oracles.

Architecture-static checks passed. Runtime hostile cases remain mostly unsupported; only HC-01 now has a bounded synthetic Rust process proof.

## M112 ADR and enforcement result

- ADR-0004 retains Rust-only whole-system migration and no in-process bridge.
- ADR-0005 pre-M111 crate/port topology is superseded `[deferred]`.
- ADR-0007 retains a subprocess-only Python repository harness with no product logic.
- ADR-0008 records authority separation, complete H1 and provisional ceilings.
- ADR-0009 records the five-clock temporal model.
- ADR-0010 records D119 evidence gates.
- ADR-0011 records KOF-DA and exact twenty owners.
- ADR-0012 records the ongoing evidence-before-selection protocol.
- `scripts/verify-m112-adr-sync.py` checks index, lifecycle, decision/contract markers, owner parity, stale topology, authority/clock/gate/composite-owner regressions, technology adoption and proof inflation.
- The derived architecture registry now has 69 items and 109 edges; it remains non-authoritative.

R072 is validated only for ADR synchronization and static enforcement. R067, R068 and R071 remain active.

## M113 HC-01 runtime result

- Closed Turso/AgentFS storage evidence debt under ADR-0012 without product adoption.
- Implemented pure hexagonal `ln-observe` domain/ports/application/adapters.
- Sealed hostile partial-byte metadata and four interrupted outcome contracts.
- Added dependency-free `ln-hc01-runner` process surface.
- Tracked `S10-HC-01-RT` PASS with exact scenario-to-outcome mapping and a negative collapsed-mapping control.
- D128 kept product SQLite outside M113.

Proof anchors:

- `prd/migration/rust-evidence/probes/hc01-observe-source-runtime.json`
- `prd/migration/rust-evidence/probes/hc01-observe-source-runtime.md`

## Recommended next milestone

After M123 closeout, execute HC-12 Rebuild Disposable Projection:

1. pure outward projection rebuild policy for partial/stale/cancelled rebuilds;
2. ensure rebuild output remains disposable and non-authoritative;
3. dependency-free process runner and tracked `S10-HC-12-RT` PASS or FAIL;
4. update aggregates honestly and gate HC-13 only if HC-12 PASS.

Do not select product filesystem/storage/graph/agent backends as part of the next thin hostile slice.

## Downstream gates

| Capability | Gate | Current lifecycle |
|---|---|---|
| Rust product parity | Implement all required capability surfaces and whole-system parity before Python archival | `[proposed]` |
| HC-02 inventory intake | Re-inventory remains staging/review; no curated/current/authority labels | `[bounded]` runtime PASS |
| HC-03 dispose review | Pending/quarantined is not acceptance; promotion blocked | `[bounded]` runtime PASS |
| HC-04 promotion | Cancel/retry/duplicate preserve one D116 effect | `[bounded]` runtime PASS |
| HC-05 decode and anchor | Decoder cannot verify/merge/mint relations or leak payload | `[bounded]` runtime PASS |
| HC-06 gate lifecycle | C10 rejects confidence-only and in-place lifecycle promotion | `[bounded]` runtime PASS |
| HC-07 assert identity | C12 preserves identities under false-match pressure | `[bounded]` runtime PASS |
| HC-08 validate relation | C13 rejects open and wrong-owner relations | `[bounded]` runtime PASS |
| HC-09 resolve five-clock state | Five-clock resolution rejects every substitution | `[bounded]` runtime PASS |
| HC-10 transition work state | Work cancellation and resume cannot alter legal state | `[bounded]` runtime PASS |
| HC-11 compute dependency closure | Incomplete/unbounded closure cannot prove completeness | `[bounded]` runtime PASS |
| HC-12 rebuild disposable projection | Partial rebuild remains disposable and non-authoritative | `[proposed]` active next |
| Temporal resolver | Five-clock runtime plus complete substitution/conflict fixtures | `[proposed]` |
| Promotion/publication | Idempotent D116 and complete H1/D120 hostile fixtures | `[proposed]` |
| FalkorDB product integration | ADR-0012 evidence pass and disposable runtime probes after an owning capability needs it | `[deferred]` |
| Retrieval/citations | Real EvidenceSpan fixtures and evidence-bounded answer/citation runtime | `[bounded]` prior evidence only |
| E1-E3 capacity | Comparable local measurements for selected runtime | `[proposed]` unknown |
| Python archival | Complete Rust whole-system parity and one controlled cutover | `[deferred]` |

## Frozen tracks

- ACP/git-lex active runtime, hooks, CI, skills and source-of-truth roles remain decommissioned.
- PyO3, C ABI, FFI, embedded Python and shared-library product bridges remain forbidden.
- ADR-0005 named crate topology is not a default or implementation plan.
- Generated registry JSONL/reports/views are diagnostics, not architecture authority.
- Product storage remains unselected after M113 D128.

## Non-claims

This roadmap does not prove Rust product readiness, parser completeness, Russian legal correctness, source completeness, FalkorDB production readiness, retrieval quality, diagnostic sink safety, E1-E3 capacity or whole-system parity. HC-01 through HC-11 bounded synthetic runtime PASS proofs do not establish aggregate conformance or product storage readiness.
