# Post-parser-protocol project-document gap disposition

**Assessment date:** 2026-08-12  
**Assessed revision:** `98e5b51d8c568c45b9b3a55d1cac2a32f059815f`  
**Lifecycle:** `[bounded]` repository-document assessment  
**Role:** non-authoritative status classification; not acceptance  

## 1. Authority boundary

This record evaluates project-document gaps after publication of the
representative parser golden-corpus acceptance protocol and quarantine of
historical parser workflow instructions. It does not reopen or extend D150,
which remains revision-bound to packet
`120d44be610b20ee537f402140eb3828e8e9a0f4`.

Canonical architecture authority remains `prd/ARCHITECTURE.md` plus active
`doc/adr/**`. This assessment, Governor output, `.gsd`, derived views and parser
protocol results cannot satisfy requirements, validate legal behavior or
promote lifecycle.

## 2. Closed project-document gaps

| Gap | Disposition | Evidence and ceiling |
|-----|-------------|----------------------|
| Representative parser acceptance criteria were under-specified | Specification closed `[bounded]` | `prd/parser/representative_golden_corpus_acceptance_protocol.md` defines provider strata, manifest fields, positive/hostile gates, span separation, annotation provenance, determinism, failure visibility and G0–G3. Current execution remains G1 `[bounded]`. |
| Self-derived enrichment could be read as independent gold | Closed as a documented non-claim | The protocol classifies parser-self-derived annotations as self-consistency only and requires independently human-reviewed structural annotations for G2. |
| Candidate extraction could be read as legal resolution | Closed as a documented hard boundary | Decode-layer goldens may contain structural spans/candidate kinds only; authoritative resolution, NormStatement, applicability and citation authority are forbidden. |
| Provider assumptions could be mixed | Closed as a documented hard boundary | Consultant WordML and Garant ODT have independent strata, streams, fixtures, oracles and failure taxonomies. |
| Parser README published historical scripts/absent JSONL as current routes | Closed `[bounded]` | `prd/parser/README.md` exposes current Cargo routes and places M006–M009 scripts/artifacts under an explicit historical-workflow boundary. |
| M072 fixture counts looked current | Closed as historical qualification | The 53-fixture/12-ODT count is marked a frozen M072 snapshot, not current corpus inventory or representative proof. |
| Historical golden contract listed absent active artifacts without warning | Closed as historical qualification | `prd/parser/golden_test_contract.md` marks the M008 artifact table historical and points current structural acceptance to the new protocol. |

## 3. Parser evidence still not implemented

### 3.1 G2 independent structural golden corpus

**Status:** not implemented.

Current evidence reaches G1 only: one tracked real document per provider plus
synthetic/hostile contracts. G2 requires:

- multiple tracked fixtures for every claimed provider stratum;
- independently authored and human-reviewed structural annotations;
- manifest-bound source hashes and annotation provenance;
- deterministic metrics and unknown-form reporting;
- a human decision on representativeness and numeric acceptance thresholds.

**Difficulty:** high. Existing `golden_real_enrichment.rs` annotations are built
from the same extractors under test and are circular as a quality oracle.
Additional tracked corpus files are raw inputs, not annotations or acceptance
proof.

**Non-claim:** current G1 tests do not prove representative parser quality,
parser completeness, cross-provider parity or legal interpretation.

### 3.2 G3 lifecycle review

**Status:** not implemented and human-owned.

Any parser claim stronger than G2 `[bounded]` requires a source-bound packet,
independent review and explicit human disposition under ADR-0012/0013 ceilings.
No protocol or green test can promote ADR-0013 to `[validated]` automatically.

## 4. Remaining missing project specification

### 4.1 Self-contained temporal paper contract

Still missing are a complete text-change versus normative-effect event taxonomy,
proposed request/result/error shapes and explicit ownership of
`edition_date`, `EvidenceSpan`, future `SourceBlock`, correction and
applicability inputs.

**Difficulty:** medium for paper structure, high for load-bearing semantics.
TQ-04, TQ-05 and NormRule ownership require human decisions before accepted
substance can be written.

### 4.2 Thin post-M165 product sequence

Historical migration roadmaps remain correctly frozen, but no current planning
surface orders parser G2, L2 CTV, RuVector/TEI, retrieval/citation and release.

**Difficulty:** medium-high. Parser-first, CTV-first and infrastructure-first
sequences have materially different dependencies. An agent should prepare
options, not silently select one.

### 4.3 Derived readiness blocker view

`prd/architecture/product_readiness_blockers.md` remains a quarantined era-stale
derived view with old ACP/FalkorDB and gate vocabulary.

**Difficulty:** medium. The project must choose whether to preserve historical
IDs in a reduced archaeology index or regenerate a current diagnostic map. The
living oracle must remain the sole current blocker authority.

## 5. Human-owned decisions still open

| Decision | Why automation is unsafe |
|----------|--------------------------|
| G2 representative fixture strata and counts | Inventory labels do not establish representativeness. |
| Parser P/R/F1 and unknown-form thresholds | No accepted numeric floors exist; inventing them creates false precision. |
| Human structural annotations and disputed spans | Gold must be independent of the parser under test. |
| TQ-04 correction owner | Changes correction/audit authority and temporal truth. |
| TQ-05 cross-reference resolver | Changes citation authority and latest-text/CTV behavior. |
| NormRule IR owner/ADR | Changes ontology and application boundaries. |
| Post-M165 product sequence | Changes investment and dependency order. |
| Clean-tree freshness comparison base | `HEAD^`, merge-base, PR range and assessment revision have different semantics. |
| Successor assessment of current HEAD | An agent cannot self-accept post-D150 work. |
| Stage D semantic intake | Requires a concrete consumer and mandatory human disposition to avoid authority laundering. |

## 6. Product/runtime/legal work documents cannot close

The following remain Rust implementation and evidence work:

- Component Temporal Versioning and structural amendments;
- runtime NormativeState;
- NormRule graph behavior;
- applicability ports and resolver;
- hierarchy/competence/conflict decisions;
- practice overlay, transitional risk and industry profiles;
- correction/evidence/publication/API closure proofs under TSG-011..016;
- G2 parser execution and representative real-document quality;
- production storage and RuVector/TEI behavior;
- representative retrieval quality and citation-safe answers;
- complete KnowQL execution;
- release-class PC-020 evidence.

These require Rust domain/application/port contracts, positive and hostile
semantic tests, durable representative fixtures, real adapter/document evidence
and source-bound human acceptance for stronger lifecycle.

## 7. Final bounded disposition

At revision `98e5b51`, the missing parser acceptance-protocol specification and
the active/historical parser documentation boundary are closed in
repository-document scope `[bounded]`.

The principal remaining gap is no longer “write a parser protocol”; it is
execute G2 with independently reviewed multi-fixture gold and human-owned
thresholds. The other major documentation gaps require human legal/design or
planning choices. Product/runtime/legal gaps cannot be closed by further prose.

No current document or test extends D150, validates parser completeness or
promotes any product capability.
