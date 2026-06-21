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

**Current status: `[bounded]` foundation, data NOT prepared, product NOT ready.**

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
[YOU ARE HERE] — anti-drift enforcement in place (D098); product track resumes
```

## Current layer (where work happens now)

**Consultant XML parser hardening** — `[proposed]` (M034 roadmap, never executed).
7 proof-gated slices: S01 baseline lock, S02 lxml eval, S03 structural rules,
S04 semantic diagnostics, S05 razdel/pymorphy3 eval, S06 source-span/stable-ID,
S07 final proof package. Boundary (M034): NO FalkorDB, NO graph-vector, NO
R035/R037/R038 validation, NO legal answers, NO retrieval quality, NO Garant
parity, NO Old_project as authority.

**Baseline to harden:** M009 extractor — stdlib `xml.etree.ElementTree.iterparse`,
context-first, 2185 hierarchy records from `law-source/consultant/44-FZ-2026.xml`.
**Does NOT extract links/cross-references yet** (open question — graph-relations
value depends on it).

## What is downstream and BLOCKED until parser data ready

| Capability | Status | Why blocked |
|---|---|---|
| Retrieval / citation-safe answers | `[bounded]` smoke only (M012-M016, M021-M026) | needs real EvidenceSpan/SourceBlock fixtures from parsed corpus |
| FalkorDB legal graph (production) | `[bounded]` synthetic smoke (M001/S04, M021) | needs materialized graph from parsed data |
| KnowQL / generated-Cypher | `[bounded]` synthetic proof (M003) | needs real legal graph schema |
| R035 (ontology architecture) | `[proposed]` active, not validated | needs registry extractor integration |
| R037 (FalkorDB ingest/runtime) | `[bounded]` active, partially evidenced | needs production ingest from real corpus |
| R038 (independent review) | `[bounded]` active | standing review gate |

## ACP / git-lex role (D098)

**Anti-drift enforcement, NOT endless infrastructure.** CHECKPOINT mode
(detect+log+flag, not gate). FROZEN until parser data ready — product-only
track. ACP expands ONLY if drift detected+logged OR explicit user decision.
M067 closed the ACP-inline era; expanding ACP now = repeating meta-drift.

- Reusable core: external `/root/git-lex-kit-acp/` v0.2.0 (published)
- law-nexus: profile consumer (`.agents/skills/{git-lex,acp}/` profile overrides,
  `prd/architecture/PROFILE-ADAPTER.md` binding contract)
- Enforcement: mandatory lifecycle tagging; record rule on
  architectural/requirement/state claims; drift log via ACP HealthFinding;
  git-lex traceability (parser output → ACP SourceRecords)

## What law-nexus does NOT have (non-claims)

- production retrieval; legal answers; FalkorDB product runtime; KnowQL product
- parser completeness; multi-document Consultant expansion; link/cross-ref
  extraction; legal correctness; Garant parity
- any `[validated]` product capability — all product work is `[bounded]`/`[smoke]`/`[proposed]`

## Anti-drift rules (D098, enforced)

1. Read THIS first, not memory. Memory drifts; this oracle is forced.
2. Lifecycle-tag every state claim. No smoothing `[bounded]`→`[validated]`.
3. Record rule on architectural/requirement/state claims: source+lifecycle+
   evidence+proof, not prose.
4. Meta-work budget: ACP frozen until parser data ready.
5. Drift → ACP HealthFinding log, not silent fix.
6. Checkpoint, not gate — do not block product work.

## Maintenance

- **Mandatory update** at every milestone closeout (D098 enforcement #2).
- One page. If it grows, split detail to `prd/02_architecture.md` / sub-docs.
- Truth over optimism. If a claim has no cited evidence + proof gate, it is
  `[bounded]` or `[smoke]`, never `[validated]`.
