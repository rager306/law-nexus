# Project-document gap disposition

**Assessment date:** 2026-08-12  
**Assessed revision:** `d99eadf70a22497052508df2c7e7c19b7d7e464e`  
**Lifecycle:** `[bounded]` repository-document assessment  
**Record role:** non-authoritative gap classification; not acceptance  

## 1. Scope and authority

This assessment classifies remaining gaps in tracked project documents after the
living-control reconciliation and local-to-published requirement inventory. It
is not a successor external assessment, does not reopen D150 and does not extend
D150 beyond packet revision `120d44be610b20ee537f402140eb3828e8e9a0f4`.

Canonical architecture authority remains `prd/ARCHITECTURE.md` plus active
`doc/adr/**`. Product and requirement projections remain `[proposed]` and below
their governing ADR/evidence ceilings. Assessment, Governor, `.gsd`, derived
registries, catalogs and GitNexus are process evidence only.

## 2. Documentation drift closed in this wave

| Surface | Closure at assessed revision | Boundary |
|---|---|---|
| `prd/architecture/documentation-semantic-control-plan.md` | DOC-01..DOC-10 now appear as a closure ledger rather than current open defects; current 20/20 structural trace coverage, bounded dirty-tree freshness and D150 packet state are distinguished from their historical freeze points | Documentation/process closure only; no product readiness |
| `prd/project-state/roadmap.md` and `prd/project-state/data/roadmap.json` | D150 packet revision is explicitly separated from post-D150 assessments 13/14 | Post-D150 evidence does not extend D150 or create successor acceptance |
| `assessment/04-adr-amendments.md` | `superseds` advisory is explicitly historical at its tested revision; later canonical metadata migration is recorded | Historical assessment substance is preserved rather than silently rewritten |
| `assessment/08-known-defects.md` | DOC-07 distinguishes frozen 11-chain closure evidence from later PC/RQ-001..020 structural expansion | Neither count is semantic or product proof |
| `assessment/13-current-head-gap-audit.md` | Its `ce46f43` disposition is marked historical and superseded by assessment 14 for later remediation status | D150 remains unchanged |
| `prd/REQUIREMENTS.md` and `prd/PRODUCT.md` | All 64 observed local requirement IDs are classified as aggregated, partially aggregated/detail-omitted, status-not-projected, deferred-omitted or out-of-scope | Inventory completeness does not transfer local validation/status or satisfy an RQ |

## 3. Remaining missing specification that can be written without product code

### 3.1 Self-contained temporal paper contract

**Status:** incomplete.

`prd/temporal-legal-model.md` and
`prd/architecture/temporal-semantic-gap-register.md` preserve the vocabulary and
open gaps, but no single paper contract yet defines:

- a complete distinction between text-change events and normative-effect events;
- request, result and typed error shapes for temporal resolution;
- a self-contained ownership/crosswalk for `edition_date`, `EvidenceSpan`,
  future `SourceBlock`, correction records and applicability inputs;
- how TL-G01..12 map to those paper shapes without implying implementation.

**Difficulty:** medium for paper design, high authority sensitivity. A writer can
prepare options and schemas, but cannot silently choose unresolved legal/event
semantics or declare the Rust API stable.

**Safe closure route:** a dedicated paper-design slice under ADR-0017/0018/0023
ceilings, with explicit `[proposed]` request/result/error schemas and human
review of every load-bearing term.

**Non-claim:** paper completeness would not implement CTV, NormativeState,
applicability or legal correctness.

### 3.2 Representative parser golden-corpus acceptance criteria

**Status:** under-specified.

`prd/parser/README.md` and parser record contracts preserve provider isolation
and parser non-claims, while `prd/ARCHITECTURE.md` still blocks representative
golden-corpus proof. The tracked documentation does not yet provide one
self-contained acceptance protocol covering provider mix, fixture selection,
span validity, candidate-vs-legal-resolution boundaries, error classes and
minimum evidence needed to claim representative parser behavior.

**Difficulty:** medium. Criteria can be specified on paper, but fixture selection
and thresholds require human/product ownership and later real-document runs.

**Safe closure route:** a parser golden-corpus protocol document that keeps
Consultant WordML and Garant ODT fixtures independent and labels all current
results `[bounded]` or `[smoke]` until representative execution exists.

**Non-claim:** acceptance criteria do not prove parser completeness, parity or
legal resolution.

### 3.3 Thin current-front product sequence

**Status:** incomplete planning surface.

Historical Rust and M131-M140 migration roadmaps are correctly frozen. The
living oracle lists blocked capabilities, but no thin post-M165 product sequence
connects the current gates in one evidence-ordered view.

**Difficulty:** medium. Ordering parser corpus proof, L2 CTV, RuVector/TEI,
retrieval/citation and release can materially change investment and dependencies.

**Safe closure route:** prepare alternative sequencing options with governing
ADRs and entry/exit evidence; require a human choice before publishing one as the
current plan.

**Non-claim:** a roadmap is planning authority only and does not unlock product
work or prove readiness.

### 3.4 Derived product-readiness blocker view

**Status:** stale/quarantined derived view.

`prd/architecture/product_readiness_blockers.md` retains era-specific
ACP/FalkorDB and old gate vocabulary. Its non-authoritative banner prevents it
from becoming canonical, but the body remains costly and misleading for cold
readers compared with the living oracle, TL-G01..12, current PC/RQ rows and TSG
register.

**Difficulty:** medium. A rewrite must preserve historical IDs while removing
current-looking priority semantics and must not create a second canonical
blocker list.

**Safe closure route:** either reduce it to a historical index with explicit
supersession pointers, or regenerate a diagnostic map from current oracle/TL/TSG
IDs. The living oracle remains the only current blocker authority.

**Non-claim:** cleaning a derived view does not close a blocker.

## 4. Open design decisions that documentation cannot safely invent

| Decision | Current evidence | Why human ownership is required |
|---|---|---|
| TQ-04 correction protocol owner and correction-ledger semantics | `prd/temporal-legal-model.md`; TSG-012 | Correction authority affects audit and temporal truth; a prose default could silently create legal semantics. |
| TQ-05 temporal cross-reference resolver owner | `prd/temporal-legal-model.md`; TSG-002/014 | Choosing latest-text, candidate-only or CTV-aware resolution changes citation authority and fail-closed behavior. |
| NormRule intermediate representation ownership | TSG-005; ADR-0023 dependencies | Whether it needs a dedicated ADR or remains deferred changes the ontology/application boundary. |
| Clean-tree/commit-range freshness comparison base | `assessment/14-post-remediation-gap-disposition.md` §3.2 | `HEAD^`, merge-base, PR range and assessment revision have different CI/branch semantics. |
| Stage D semantic advisory consumer and disposition workflow | Governor design Stage D; assessment 14 §3.4 | Without a concrete human disposition path, implementation risks authority laundering. |
| Successor assessment of the current source revision | `assessment/12-final-disposition.md`; assessments 13–15 | An agent cannot self-accept post-D150 changes. |

## 5. Product/runtime/legal capabilities that documents cannot close

The following remain implementation-and-evidence work even if their paper
specifications improve:

- TSG-003: Component Temporal Versioning operations and structural amendments;
- TSG-004: runtime `NormativeState` resolution;
- TSG-005: typed `NormRule` graph behavior;
- TSG-006: applicability runtime and typed ports;
- TSG-007: hierarchy, competence and conflict resolution;
- TSG-008: judicial/FAS practice overlay;
- TSG-009: transitional provisions and risk;
- TSG-010: industry profiles;
- TSG-011..016: correction, evidence, publication and API closure proofs as
  defined by the gap register;
- representative parser completeness/parity and real-document quality;
- production RuVector/TEI ingestion/query/citation behavior;
- representative retrieval quality and citation-safe answers;
- complete KnowQL execution and release-class PC-020 evidence.

**Difficulty:** high. Each capability needs Rust domain/application/port work,
positive and hostile semantic contracts, durable representative fixtures, real
adapter or real-document evidence where applicable and a source-bound human
acceptance decision for any stronger lifecycle.

## 6. Prioritized safe next actions

1. Prepare a human decision packet for temporal paper-contract scope and the
   TQ-04/TQ-05/NormRule owners; do not author accepted semantics without it.
2. Draft representative parser golden-corpus acceptance criteria while keeping
   provider fixtures and candidate/legal-resolution boundaries independent.
3. Prepare product-sequence alternatives rather than silently selecting a
   post-M165 roadmap.
4. Quarantine or rewrite the derived readiness blocker view only after agreeing
   whether historical IDs must remain visible to cold readers.
5. Plan the first Rust product slice from an accepted decision, preferably a
   thin TSG owner with hostile fail-closed proof, rather than adding more
   repository-control infrastructure.

## 7. Final disposition

At revision `d99eadf`, the confirmed living-document drift and the explicit
local-to-published requirement inventory gap are closed in repository-document
scope `[bounded]`.

The remaining project-document work is either:

- a paper specification needing human review of load-bearing semantics;
- a planning/derived-view choice requiring a human-selected policy;
- or product/runtime/legal implementation and evidence that documentation cannot
  satisfy.

No current document, assessment, Governor result or inventory validates those
remaining capabilities or extends D150 acceptance to this revision.
