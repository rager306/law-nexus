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
legal authority** — all checkable operations are algorithmic via FalkorDB +
formal Legal KnowQL.

**Current status: `[bounded]` Python product reference with real parser artifacts;
artifact baseline reconciliation and complete Rust transition are `[proposed]`;
product is NOT ready.**

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
[YOU ARE HERE] — run three parallel tracks: manifest-driven history archive,
parser baseline reconciliation, and Rust workspace + Python harness tracer
```

## Current layer (where work happens now)

**`src/law_nexus` onion package** — `[bounded]` Python behavioral reference
(historical ADR-0001 is archived under `python_archive/adr/`). The
deterministic-first package surface remains dependency-directed during the Rust
transition: `domain/` (SourceDocument, SourceBlock, ActEdition,
EvidenceSpan, NormStatement, LegalUnit, Citation, SourceHierarchy), `ports/`
(Parser, GraphStore, Embedder, LLMClient protocols), `adapters/parsers/`
(ConsultantWordMLParser — document-level seam), `adapters/sources/`
(consultant_hierarchy.py — marker_for_text, hierarchy_records,
extract_internal_references, extract_external_references,
detect_temporal_markers, detect_deontic_lexemes, extract_norm_candidates,
profile_document), `application/` (Ingest use case), `composition.py`
(factory root). Existing import-linter and ADR checks remain general repository
controls until the ADR-0007 harness replaces/consolidates them; they are not ACP
mechanisms. The package is a `[bounded]` document-level seam with working
structural hierarchy, temporal/deontic markers, norm candidates, and staging
graph materialization (15249 hierarchy records / 1567 norm candidates /
1378 relation candidates / 271 hierarchy nodes in staging graph as of M105).
Retrieval, FalkorDB product runtime, and KnowQL remain `[proposed]`/`[deferred]`
(see `prd/02_architecture.md` per-layer tags).

**Python library boundary (historical ADR-0003):** Pydantic/domain and parser
record decisions remain part of the Python behavioral reference, not the Rust
target. Rust equivalents are serde/schemars types and traits per ADR-0005.

**Consultant XML parser hardening** — `[bounded]` through M086–M105: 81 XML
source files, multi-level hierarchy, FRBR IDs, internal/external references,
temporal/deontic markers, norm/relation candidates and staging graph artifacts.
The tracked artifact baseline is **not frozen**: M105 closeout reports 1,567 norm
candidates and 271 hierarchy nodes, while the current tracked artifacts contain
386 norm rows and 48 source blocks. R0 must separate single/corpus outputs and
reconcile hashes/counts before Rust parity starts.

## What is downstream and BLOCKED until parser data ready

| Capability | Status | Why blocked |
|---|---|---|
| Retrieval / citation-safe answers | `[bounded]` smoke only (M012-M016, M021-M026) | needs real EvidenceSpan/SourceBlock fixtures from parsed corpus |
| FalkorDB legal graph (production) | `[bounded]` synthetic smoke (M001/S04, M021) | needs materialized graph from parsed data |
| KnowQL / generated-Cypher | `[bounded]` synthetic proof (M003) | needs real legal graph schema |
| R035 (ontology architecture) | `[proposed]` active, not validated | needs registry extractor integration |
| R037 (FalkorDB ingest/runtime) | `[bounded]` active, partially evidenced | needs production ingest from real corpus |
| R038 (independent review) | `[bounded]` active | standing review gate |

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

- production retrieval; legal answers; FalkorDB product runtime; KnowQL product
- parser completeness; multi-document Consultant expansion; link/cross-ref
  extraction; legal correctness; Garant parity
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
