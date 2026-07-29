# ARCHITECTURE — law-nexus living truth oracle

> **Read this FIRST**, not memory or history. This is the single-page forced
> truth about law-nexus state. Updated at every milestone closeout (mandatory,
> D098 enforcement #2). Lifecycle tags are mandatory (D098 enforcement #1):
> `[bounded]` / `[smoke]` / `[validated]` / `[proposed]` / `[deferred]`.
>
> Detailed architecture: `prd/02_architecture.md`. Decisions: `.gsd/DECISIONS.md`.
> Requirements: `.gsd/REQUIREMENTS.md`.

## What law-nexus IS

A **citation-safe, evidence-verifiable legal graph for Russian normative acts**.
Goal (PRD `prd/01_general_idea.md`): turn a normative act into a graph-vector
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

## Where we actually are (truth, not optimism)

```
M009 Consultant XML hierarchy parser  [bounded]
   2185 records, 7 levels, HIER-CONS-*, stdlib xml.etree, 1 fixture (44-FZ-2026.xml)
   Consultant-primary / Garant-deferred
   ▼
M034 Workline Recovery Audit (2026-05)  [validated]
   identified M031-M033 drift (lifecycle/discovery upper layers, NOT parser foundation)
   produced corrected parser-hardening roadmap:
   prd/research/source_structuring/25-corrected-consultant-xml-parser-roadmap.md
   ▼
╳╳╳ GAP — parser-hardening NOT executed (project drifted to ACP M035-M067) ╳╳╳
   ▼
M067 ACP/git-lex externalization  [validated]
   reusable core → /root/git-lex-kit-acp/ (published github.com/rager306/git-lex-kit-acp v0.2.0)
   law-nexus = profile consumer; ACP-inline era CLOSED
   ▼
M086-M105 Parser-hardening wave (2026-06–07)  [bounded]
   M086-M090 debt closure (+115 tests restored)
   M088 RawBlock IR in ports/source_hierarchy.py (6 additive fields)
   M091 razdel level + M092 abzac diagnostic + M093 zone detection
   M094 FRBR act_id/edition_id derivation in consultant_wordml.py
   M095-M096 internal + external reference extraction
   M097 temporal markers (entry_into_force, invalidity, secrecy)
   M098 NormStatement deontic lexeme detection (22 patterns, 6 categories)
   M099-M100 Layer 2 YAML profiles (consultant_wordml.yaml + garant_odt.yaml)
   M101 internal reference resolution (83 hierarchy nodes in staging)
   M102 Pass A document profiler (profile_document census)
   M103 NormStatement candidate emission (1426 candidates)
   M104 NormStatement staging graph integration
   M105 Consultant source corpus migration 41→81 files
       15249 hierarchy records / 1378 relation candidates / 1567 norm candidates
       10 in-scope / 84 out-of-scope fixtures, 94-fixture inventory
   M106 test performance: session-scoped fixtures + slow markers
       fast run 32s (was 65+ min), 120x speedup
   ▼
M107 architecture crystallization  [bounded/proposed]
   Rust-only product transition selected (ADR-0004/0005, R063/R065)
   Python repository-control harness allowed (ADR-0007, R064)
   ACP/git-lex active role rejected; archive-only decommission planned (R066)
   parser artifact baseline mismatch detected; reconciliation required before parity
   ▼
M108 ACP/git-lex runtime disconnection  [bounded]
   750-path manifest: 546 archive candidates / 204 manual review
   git-lex-managed pre-commit removed with forced standard installation
   real hook proof: exit 0, .lex fingerprint unchanged
   pre-commit/CI/ADR gates neutralized; 43 tests + onion 4/0
   bulk archive NOT started; .lex and historical ACP artifacts still present
   ▼
M109-M129 Rust baseline and hostile contract closure  [bounded]
   root Cargo workspace + thin Python repository harness
   20 hostile cases: 20 PASS / 0 FAIL / 0 unsupported-case
   real WordML streaming decoder: 22 MB / 53,119 paragraphs without OOM
   ▼
ADR-0013 universal parser  [bounded] + ADR-0014 RuVector  [proposed]
   independent Consultant WordML and Garant ODT adapters
   shared bounded hierarchy, sentence, reference, temporal and deontic candidates
   TEI USER-bge-m3 1024d embedding boundary remains proposed
   RVF vectors + redb GraphDB CRUD; no ruvector-graph Cypher execution claim
   ▼
[LATEST COMPLETED] M148 — crate-qualified coverage identity + decode/observe/diagnostic shared contracts;
10/22 InMemory adapters shared-contracted. M149 further contract expansion is next.
```

## Current layer (where work happens now)

**Rust product runtime** — `[validated]` direction (ADR-0004/0005) with active
hexagonal crates under `crates/` and the observable product CLI
`law-nexus-inspect`. Rust owns decode, storage ports, KnowQL composition and
product behavior. One tracked real fixture per provider remains `[bounded]`
evidence; no corpus/legal/citation completeness claims.

**Python repository-control harness** — `[validated]` process boundary
(ADR-0007) under `src/law_nexus_harness/`. Active Python is governor/preflight
orchestration only: Cargo/ADR/document freshness/GSD glue. It must not import
product domain packages, PyO3/FFI bridges, or active FalkorDB adapters.

**`python_archive/product/`** — archived Python product prior art after M140/M141
cutover and residual dependency closure. Historical onion package surfaces,
legacy proof scripts and residual product-era tests live here only. They are not
the target product specification and do not gate active CI product behavior.

**Historical library boundary (ADR-0003):** Pydantic/domain and parser record
decisions remain prior-art evidence only. Rust equivalents are independently
defined serde/schemars types and traits behind current hexagonal boundaries.
FalkorDB is historical evidence, not active product infrastructure. ADR-0014
selects RuVector only at `[proposed]`; real TEI→RVF, graph materialization,
cross-store recovery and citation gates remain open.

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
| Universal parser | `[bounded]` independent Consultant/Garant block adapters, shared hierarchy/sentence/morphology and reference/temporal/deontic lexical candidates with one tracked real document per provider | needs representative golden corpus, quality convergence, legal resolution and citation mapping |
| RuVector graph-vector infrastructure | `[proposed]`; synthetic capability checks only | needs TEI 1024d real corpus, RVF/redb materialization, crash consistency and citation contract |
| Retrieval / citation-safe answers | `[bounded]` prior smoke only | needs real EvidenceSpan/SourceBlock fixtures, quality metrics and exact byte round-trip |
| KnowQL | `[bounded]` hand-coded AST demo only | needs real parser and typed application executor; `ruvector-graph` Cypher execution is not relied upon |
| R035 | `[proposed]` active, not validated | standing graph-vector proof-boundary requirement |
| R038 | `[bounded]` active | standing independent review gate |

## ACP / git-lex status

**`[proposed]` decommission, decision accepted (D104/R066).** ACP/git-lex has no
place in the target law-nexus architecture, runtime, CI, skills, requirements or
source of truth. Project-local history will move to
`python_archive/acp_git_lex/`; the external `/root/git-lex-kit-acp/` repository
is not modified. General ADR, evidence, requirement/state consistency and
fail-closed checks survive only after being rewritten without ACP/git-lex
runtime or vocabulary dependencies.

M108 disconnected the git-lex-managed hook. The installed standard pre-commit
hook has no legacy chain; real execution leaves `.lex` byte-identical. `.lex`
and ACP history remain only until manifest-driven D3-D6 archive waves.

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

- **Mandatory update** at every milestone closeout (D098 enforcement #2).
- One page. If it grows, split detail to `prd/02_architecture.md` / sub-docs.
- Truth over optimism. If a claim has no cited evidence + proof gate, it is
  `[bounded]` or `[smoke]`, never `[validated]`.
