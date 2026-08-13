# ARCHITECTURE — law-nexus living truth oracle

> **Read this FIRST**, not memory or history. This is the single-page forced
> truth about law-nexus state. Updated at every milestone closeout (mandatory,
> D098 enforcement #2). Lifecycle tags are mandatory (D098 enforcement #1):
> `[bounded]` / `[smoke]` / `[validated]` / `[proposed]` / `[deferred]`.
> Active ADRs must not depend on missing `prd/research/` or gitignored
> `AGENTS.md` as durable authority (RC12-F18).
>
> Detailed decisions: [`doc/adr/**`](../doc/adr/README.md).
> `.gsd/**` is local workflow state, not a cold-reader authority surface.
> [`PRODUCT.md`](PRODUCT.md) and [`REQUIREMENTS.md`](REQUIREMENTS.md) remain `[proposed]`;
> EA-02 marked their document state `ready-for-assessment` at `37f82c4`. This is
> not EA-10 acceptance and not product/legal readiness evidence.

## What law-nexus IS

A **citation-safe, evidence-verifiable legal graph for Russian normative acts**.
Current product direction `[bounded]`: turn a normative act into a graph-vector
representation for exact article/semantic search, temporal filtering by
edition/effective-date, and provable answers with legal citations. **LLM is not
legal authority** — all checkable operations remain deterministic and
source-anchored. Rust owns product behavior; formal Legal KnowQL remains a
law-nexus application concern.

**Current status:** 20/20 hostile contracts have `[bounded]` synthetic Rust
runtime PASS. The parser foundation has `[bounded]` independent Consultant and
Garant adapters plus one tracked real document per provider; RuVector integration
remains `[proposed]`, and real-corpus retrieval and citation safety are not
validated. Python is prior art
or repository-control harness only, not the product reference specification.

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

## Foundation ADR map (active, not archive)

| ADR | Topic | Lifecycle |
|-----|-------|-----------|
| ADR-0004 | Rust product transition | `[bounded]` |
| ADR-0005 | Rust target architecture (crate map superseded by ADR-0011) | `[bounded]` |
| ADR-0007 | Python repository-control harness | `[validated]` |
| ADR-0008 | Promotion / publication authority | `[bounded]` |
| ADR-0009 | Five-clock temporal model (safety contract; not full temporal algebra — RC11-F06) | `[bounded]` |
| ADR-0010 | Evidence kernel gates (C10/C12/C13) | `[bounded]` |
| ADR-0011 | KOF-DA exclusive ownership (`ln-*`) | `[bounded]` |
| ADR-0012 | Consequential evidence protocol | `[bounded]` |
| ADR-0013 | Universal multi-source parser | `[bounded]` |
| ADR-0014 | RuVector primary infrastructure | `[proposed]` |
| ADR-0015 | Hexagonal verification architecture | `[bounded]` |
| ADR-0016..0022 | Temporal legal ontology L1→L7 | `[proposed]` each |
| ADR-0023 | Applicability protocol ownership (core decision/trace + profile inputs; no runtime) | `[proposed]` |; capability inventory (RC12-F05)
| ADR-0024 | Review Case intake and disposition (non-authoritative projection + human promotion gate; no runtime) | `[proposed]` |

Index: `doc/adr/README.md`. Do not treat ACP/git-lex/FalkorDB-era docs as
active ADR substance.

## Temporal legal ontology — design spine (all `[proposed]`)

A progressive top-down ontology of what an agent needs to reason legally over
time. Each layer depends on the one below; all are **fail-closed** (missing
provenance → `Unknown`, never smoothed) and follow the D046 adoption ladder
(project-local evidence kernel is canon; LRMoo/AKML/ELI/LKIF are compatibility
references, not canon replacements). Full substance: `doc/adr/0016`..`0022`.

```text
L1 ADR-0016 [proposed]  FRBR/LRMoo structural identity   WEMI: Work/Expression/Manifestation/Item
             date + authority = identity canon (act numbers are non-unique)
   ▼
L2 ADR-0017 [proposed]  Component Temporal Versioning ◄── temporal core; TextChange≠NormativeEffect design taxonomy (RC11-F07); structural CTV ops spine (RC11-F08); structural apply S3
             CC/CTV/CLV (F1/F2); validity DERIVED from events (event-sourcing);
             macro/micro events (P9 consists of); F27∩E64 amendment typing;
             bitemporal valid/transaction time; fail-closed resolver (R070/R068).
             Adapted from de Martim arXiv:2506.07853 v5 (LRMoo, 2026).
   ▼
L3 ADR-0018 [proposed]  NormativeState(t)                text ≠ status (InForce/Suspended/Repealed/…); dimensional separation design (RC11-F09)
   ▼
L4 ADR-0019 [proposed]  hierarchy + conflict             lex superior/specialis/posterior, explainable
   ▼
L5 ADR-0020 [proposed]  practice overlay                 Суды/ФАС/Контроль (first-class temporality over five clocks; non-authoritative)
   ▼
L6 ADR-0021 [proposed]  transitional + risk              derived, non-authoritative; limitation periods
   ▼
L7 ADR-0022 [proposed]  industry profiles                бюджет/стройка/медицина/общий = adapters
   ▼
   ADR-0023 [proposed]  applicability ownership boundary neutral core protocol + versioned profile inputs; `ln-applicability` v0 is fail-closed abstention-only with NormRule IR + pure predicate algebra spines (no Applicable/NotApplicable product claim)
```

Proposed semantic reconciliation, glossary and graduation gates are tracked in [`temporal-legal-model.md`](temporal-legal-model.md). For work that changes temporal, parser, evidence, citation, retrieval, applicability, practice, risk or profile vocabulary, maintainers and coding agents must read its §3 glossary plus the owning active ADR before naming a public contract or Rust type; `deferred-undefined` and `runtime deferred` are stop-signs. The tracked update/injection process is [`architecture/glossary-governance.md`](architecture/glossary-governance.md). Governor checks inventory the glossary and warn on narrowly allowlisted presentation drift across vocabulary lifecycle and closed-clock boundaries; they remain advisory process controls. These process/design surfaces do not amend ADRs, generate product types or promote O1–O7.

**Kernel canon, standards compatibility (D046):** the project-local evidence
kernel (D119 C10/C12/C13) owns substance; LRMoo/CIDOC-CRM/AKML/ELI/LKIF are
deterministic reversible projections for interoperability. Budget cycle is a
profile projection over the five clocks (ADR-0009), NOT a sixth clock.

## Where we actually are (truth, not optimism)

```
[HISTORICAL FOOTNOTE — not active product work]
  Python-era parser/ACP/git-lex/FalkorDB milestones (M001–M108 era) are prior art.
  Detail lives under prd/archive/ and python_archive/ (R066 archive-only).
  Meta-drift lesson: anti-drift infrastructure must not replace product delivery.
   ▼
M109-M129 Rust baseline + 20 hostile contracts  [bounded]
   root Cargo workspace + thin Python repository harness (ADR-0007 [validated])
   20 PASS / 0 FAIL synthetic hostile cases; not product readiness
   ▼
M131-M140 parser foundation + archival cutover  [bounded]
   ADR-0013 universal parser [bounded] (Consultant WordML + Garant ODT)
   shared hierarchy/sentence/reference/temporal/deontic lexical candidates
   Python product → python_archive/; historical ACP/git-lex disconnected from active plane
   ▼
M141-M160 process/port-contract hardening  [bounded]
   shared port contracts, CI/governor honesty, clippy gates
   ▼
M161-M164 retrieval/process honesty  [bounded]
   real cosine ranking (InMemory); semantic-stub + historical-test-debt probes
   deterministic CLI vectors (non-semantic)
   ▼
M165 temporal legal ontology L1–L7  [proposed] design (ADR-0016..0022)
   Foundation LC hygiene: ADR-0004/0005 [bounded], ADR-0007 [validated]
   Docs/process follow-up: truth-oracle sync, vault untrack, archive relocate
   ▼
ASSESSMENT FRONT (no Rust)
   EA-10 complete: D150 accepted-with-findings after independent EA-09 at 120d44b
   retained process/staleness findings remain open; no lifecycle promotion
   product work is unchanged: L2 CTV and TEI/RuVector remain evidence-gated
```

## Current layer (where work happens now)

**Rust product runtime** — `[bounded]` direction (ADR-0004/0005) with active
hexagonal crates under `crates/` and the observable product CLI
`law-nexus-inspect`. Rust owns decode, storage ports, KnowQL composition and
product behavior. Direction is accepted and the runtime exists; this is not
product readiness (blocked on RuVector/TEI infrastructure + real-corpus proof;
no `[validated]` product capability claim).
One tracked real fixture per provider remains `[bounded]` evidence; no
corpus/legal/citation completeness claims.

**Python repository-control harness** — `[validated]` process boundary
(ADR-0007) under `src/law_nexus_harness/`. Active Python is governor/preflight
orchestration only: Cargo/ADR/document freshness/GSD glue. ADR-0024 `[proposed]`
places Review Case intake, disposition, residual inventory and continuity
bridges in this control plane as a non-authoritative, human-gated, hexagonal
contour. Live packets/ledger/CLI/Governor integrity exist as process machinery;
they do not accept findings or claim product readiness. Continuity keeps three
lifecycles orthogonal — L_review (residual), L_delivery (GSD/work), L_capability
(TSG/ADR proof) — with closure ceilings and B1–B5 bridges
(`prd/architecture/review-cases/continuity-contract.md`; GSD dual-truth bridge: `prd/architecture/review-cases/gsd-review-bridge.md`; L_capability promotion board: `prd/architecture/capability-promotion-board.md`). The harness must not
import product domain packages, forbidden PyO3/FFI bridges, or historical-only
graph-database adapters from retired eras.

**`python_archive/product/`** — archived Python product prior art after M140/M141
cutover and residual dependency closure. Historical onion package surfaces,
legacy proof scripts and residual product-era tests live here only. They are not
the target product specification and do not gate active CI product behavior.

**Historical library boundary (retired ADR-0003, prior art only):**
Pydantic/domain and parser-record decisions from the Python era remain
prior-art evidence only — not an active ADR file under `doc/adr/`. Rust
equivalents are independently defined serde/schemars types and traits behind
current hexagonal boundaries. FalkorDB is historical evidence, not active
product infrastructure. ADR-0014 selects RuVector only at `[proposed]`; real
TEI→RVF, graph materialization, cross-store recovery and citation gates remain
open.

**Consultant XML parser hardening** — `[bounded]` through M086–M105: 81 XML
source files, multi-level hierarchy, FRBR IDs, internal/external references,
temporal/deontic markers, norm/relation candidates and staging graph artifacts.
The tracked hierarchy baseline is `[bounded]` and frozen for Rust parity input:
single and corpus modes use distinct outputs, their source/output hashes and
semantic counts are recorded in the canonical baseline manifest, and CLI
`--check` verifies selected artifacts plus manifest without filesystem writes.
This closes the M105/current overwrite ambiguity; it does not prove parser
completeness, Consultant/Garant parity, or production graph readiness.

## What is downstream and BLOCKED until parser data ready

| Capability | Status | Why blocked |
|---|---|---|
| Universal parser | `[bounded]` independent Consultant/Garant block adapters, shared hierarchy/sentence/morphology and reference/temporal/deontic lexical candidates with one tracked real document per provider; `prd/parser/representative_golden_corpus_acceptance_protocol.md` defines the fail-closed G0–G3 evidence ladder | current evidence reaches G1 only; needs G2 multi-fixture human-reviewed structural goldens plus human-owned quality/representativeness criteria, then separate legal resolution and citation mapping |
| RuVector graph-vector infrastructure | `[proposed]`; synthetic capability checks only | needs TEI 1024d real corpus, RVF/redb materialization, crash consistency and citation contract |
| Retrieval / citation-safe answers | `[bounded]` real cosine-similarity ranking in the InMemory adapter + RetrievalGate (M161); retrieval scores are real per-result cosine values, not a constant. No live corpus/embedding yet. | needs future-schema `EvidenceSpan`/`SourceBlock` fixtures (both remain `deferred-undefined`), TEI 1024d corpus, quality metrics and exact byte round-trip |
| KnowQL | `[bounded]` hand-coded AST demo only | needs real parser and typed application executor; `ruvector-graph` Cypher execution is not relied upon |
| R035 | `[proposed]` active, not validated | standing graph-vector proof-boundary requirement |
| R038 | `[bounded]` active | standing independent review gate |
| Temporal legal ontology L1-L7 | `[proposed]` (ADR-0016..0022) | design crystallized M165; each layer graduates to `[bounded]` when its TDD Rust domain + fail-closed resolver ships, to `[validated]` only with real-corpus proof. L2 CTV is the first implementation priority once parser data is ready. |

## ACP / git-lex status (historical decommission only)

**Decommission decision accepted; active authority is archive-only (D104/R066).** Historical/archive-only ACP/git-lex has no place in the target law-nexus architecture, runtime, CI, skills, requirements or source of truth. Remaining D3–D6 manifest/archive hygiene is `[proposed]` process work only and cannot reopen the accepted architecture boundary. Project-local history lives under
`python_archive/acp_git_lex/` (archive-only); the external
`/root/git-lex-kit-acp/` repository is historical-only and is not modified. General ADR, evidence,
requirement/state consistency and fail-closed checks survive only after being
rewritten without historical ACP/git-lex runtime or vocabulary dependencies.

M108 disconnected the historical git-lex-managed hook. The installed standard
pre-commit hook has no legacy chain; real execution leaves `.lex` byte-identical.
Active authority is already archive-only after M108. Any residual D3–D6 work is manifest/archive hygiene and cannot restore runtime, hook, CI or source-of-truth authority.

## What law-nexus does NOT have (non-claims)

- production retrieval; legal answers; RuVector product runtime; KnowQL product
- parser completeness; Consultant/Garant parity; real-corpus link, temporal or
  deontic correctness
- cross-store atomicity, recovery, concurrency, scale or citation byte safety
- any `[validated]` product capability — all product work is `[bounded]`/`[smoke]`/`[proposed]`

## Repository truth rules

1. Read THIS first, not memory or archive history.
2. Lifecycle-tag state claims; never smooth bounded/smoke into validated.
3. Architecture/requirement claims need tracked source and executable proof.
4. Generated projections and harness reports are diagnostics, not product truth.
5. Rust owns product behavior; Python harness owns repository orchestration only.
6. ACP/git-lex history is archive-only and cannot gate or mutate active work.

## Maintenance

- Documentation correction and publication gaps are tracked in [`documentation-semantic-control-plan.md`](architecture/documentation-semantic-control-plan.md) and [`assessment/08-known-defects.md`](../assessment/08-known-defects.md); both are process evidence, not architecture authority.
- **Mandatory update** at every milestone closeout (D098 enforcement #2).
- One page. If it grows, split detail into tracked focused PRD sub-docs; do not restore retired pre-Rust filenames as active truth.
- Truth over optimism. If a claim has no cited evidence + proof gate, it is
  `[bounded]` or `[smoke]`, never `[validated]`.
