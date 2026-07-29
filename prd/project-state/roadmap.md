# Roadmap

> **Source of truth:** `prd/ARCHITECTURE.md` and GSD state. This document is a
> non-authoritative cold-reader projection of
> `prd/project-state/data/roadmap.json`.
>
> Refreshed 2026-07-24 after M129 completion — all 20 hostile cases PASS.

## Active Direction Contract

```text
runtime=rust-only
python=repository-control-only
graph_vector=ruvector
infrastructure_lifecycle=proposed
embedding=tei-user-bge-m3-1024d
acp_git_lex=archive-only
falkordb=historical-only
```

## Current position

- **Latest completed milestone:** M159-08fl5d, architecture generator test CI coverage.
- **Recommended next milestone:** M160, live adapter implementation path when infrastructure exists.
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
- **M123 result:** eleventh hostile-case Rust runtime proof. `S10-HC-11-RT` is bounded PASS.
- **M124 result:** twelfth hostile-case Rust runtime proof. `S10-HC-12-RT` is bounded PASS.
- **M125 result:** thirteenth hostile-case Rust runtime proof. `S10-HC-13-RT` is bounded PASS.
- **M129 result:** All 5 remaining hostile cases closed. **20 PASS / 0 FAIL / 0 unsupported-case**. All 20 HC cases have bounded runtime PASS.
- **Product target:** Rust-only runtime under ADR-0004; Python may remain only as ADR-0007 subprocess repository harness.
- **Parser direction:** ADR-0013 universal parser is `[bounded]`; Consultant WordML and Garant ODT keep independent adapters behind shared domain contracts, and M131–M134 add shared reference, temporal and deontic lexical candidates. Representative golden corpus and citation mapping remain open for M135.
- **Graph-vector direction:** ADR-0014 selects RuVector at `[proposed]`: RVF vectors and redb GraphDB CRUD behind law-nexus ports. FalkorDB is historical-only.
- **Embedding boundary:** local TEI serves USER-bge-m3 1024d; product adapter and TEI→RVF integration remain unproven.
- **Still unselected:** cross-store journal/recovery implementation, product API, concurrency runtime and deployment topology remain evidence-gated.
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
| M123-M123 | HC-11 Compute Dependency Closure eleventh Rust hostile-case runtime proof | Bounded synthetic incomplete/unknown/unbounded/version-skew publication block PASS; 9 hostile cases remain unsupported; no product storage or dependency index selected. |
| M124-M124 | HC-12 Rebuild Disposable Projection twelfth Rust hostile-case runtime proof | Bounded synthetic non-authoritative rebuild and hostile-label demotion PASS; 8 hostile cases remain unsupported; no product storage or projection store selected. |
| M125-M125 | HC-13 Decide Admission thirteenth Rust hostile-case runtime proof | Bounded synthetic bound-unknown/saturated/retry fail-closed and vendor-capacity rejection PASS; 7 hostile cases remain unsupported; no product storage, queue, hardware or throughput selected; E1-E3 product capacity unproven. |
| M126-M126 | HC-14 Coordinate Checkpoint and Replay fourteenth Rust hostile-case runtime proof | Bounded synthetic suppress-by-identity and corrupt/version-skew fail-closed PASS; 6 hostile cases remain unsupported; no product storage, checkpoint store or exactly-once infrastructure selected. |
| M127-M127 | HC-15 Publish Authoritative H1 Unit fifteenth Rust hostile-case runtime proof | Bounded synthetic complete-publish, duplicate, competing-writer, partial-incomplete and hostile dual-writer PASS; 5 hostile cases remain unsupported; no product storage, fencing or transaction infrastructure selected. |

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

## Active and forward milestones

M130 closes repository-control debt before product work:

1. executable governor CLI;
2. semantic direction drift gate and living document synchronization;
3. active requirement contradiction closure;
4. unified preflight and renumbered long-horizon roadmap.

After M130, the non-conflicting product sequence is M131–M140: shared parser
domain/morphology contracts; real Consultant hierarchy; independent Garant ODT;
shared extractors; golden corpus; TEI + RuVector components behind ports with
recovery; typed KnowQL; product composition/CLI; whole-system acceptance; and
Python product archival. `prd/migration/forward-roadmap.md` owns the detailed
sequence and proof gates.

M131 foundation progress is `[bounded]`: provider-neutral validated block and
hierarchy types, dependency-free lexical morphology markers, and legal sentence
boundaries now have contract tests. Explicit source-stream `SourceLocation` and
decoded `TextSpan` are distinct; adapter-owned mapping remains unproven. This
does not validate parser completeness, real Consultant/Garant offsets, legal structure,
NormStatement extraction or citation safety.

M132 Consultant progress is `[bounded]`: the fail-closed Rust WordML adapter,
shared start-marker hierarchy extractor, and one tracked real federal-law tracer
produce deterministic blocks and bounded marker counts. Paragraph
`SourceLocation(artifact:whole, SourceSpan)` integrity is proven for that fixture,
while automatic cross-stream or source-to-`TextSpan` translation, corpus
completeness, full hierarchy coverage, legal correctness,
Garant behavior, retrieval and citation readiness remain unproven.

M133 Garant progress is `[bounded]`: in-memory ODT package intake and an
independent namespace-aware `content.xml` adapter have hostile synthetic runtime
contracts. The package reader enforces archive/member limits without filesystem
extraction; the XML adapter emits `package-member:content.xml` locations and
fails atomically on malformed topology, DTD/entity input, unknown ODF text
semantics and decoded whitespace amplification. Synthetic Garant blocks compose
directly with the shared provider-neutral hierarchy extractor while preserving
member `SourceLocation` and decoded marker `TextSpan` as distinct coordinates.
One tracked real Garant ODT now produces 5,124 deterministic non-empty blocks
and 140 supported hierarchy markers with exact `content.xml` member spans. This
single-document proof does not validate provider style completeness, full ODF
coverage, corpus coverage, legal correctness, Consultant/Garant parity or
citation mapping.

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
| HC-12 rebuild disposable projection | Partial rebuild remains disposable and non-authoritative | `[bounded]` runtime PASS |
| HC-13 decide admission | Unknown bounds and retry amplification fail closed | `[bounded]` runtime PASS |
| HC-14 coordinate checkpoint and replay | Corrupt lineage rejected; prior external effects suppressed | `[bounded]` runtime PASS |
| HC-15 publish authoritative H1 unit | Dual-writer and partial-authority rejected; one authoritative unit per scope | `[bounded]` runtime PASS |
| HC-15 publish authoritative H1 unit | Dual-writer and partial-authority rejected; one authoritative unit per scope | `[bounded]` runtime PASS |
| Temporal resolver | Five-clock runtime plus complete substitution/conflict fixtures | `[proposed]` |
| Promotion/publication | Idempotent D116 and complete H1/D120 hostile fixtures | `[proposed]` |
| RuVector product integration | Real parser output, TEI 1024d embeddings, RVF/redb recovery contract and exact citation gates | `[proposed]` |
| FalkorDB product integration | Historical evidence only; no active product role under ADR-0014 | `[deferred]` historical |
| Retrieval/citations | Real EvidenceSpan fixtures and evidence-bounded answer/citation runtime | `[bounded]` prior evidence only |
| E1-E3 capacity | Comparable local measurements for selected runtime | `[proposed]` unknown |
| Python archival | Complete Rust whole-system parity and one controlled cutover | `[deferred]` |

## Frozen tracks

- ACP/git-lex active runtime, hooks, CI, skills and source-of-truth roles remain decommissioned.
- PyO3, C ABI, FFI, embedded Python and shared-library product bridges remain forbidden.
- ADR-0005 named crate topology is not a default or implementation plan.
- Generated registry JSONL/reports/views are diagnostics, not architecture authority.
- RuVector is the `[proposed]` graph-vector direction, not validated product storage; RVF/redb journal, recovery and concurrency policy remain unselected.

## Non-claims

This roadmap does not prove Rust product readiness, parser completeness, Russian legal correctness, source completeness, FalkorDB production readiness, retrieval quality, diagnostic sink safety, E1-E3 capacity or whole-system parity. HC-01 through HC-15 bounded synthetic runtime PASS proofs do not establish aggregate conformance or product storage readiness.
