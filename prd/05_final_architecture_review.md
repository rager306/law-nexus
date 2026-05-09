# 5. Final Architecture Review: M001 Closure and M002-M007 Proof Gates

> **Reader and action.** This report is for a cold reader planning M002, M003, M004, M005, M006, or M007. After reading it, the planner should know which M001 architecture findings are fixed, which proof gates remain blocked, who owns each resolution path, and which claims must stay bounded until later executable evidence exists.
>
> **Source of truth.** The machine-readable row source is `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`, validated against `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`. This prose report does not introduce material claims beyond those rows and their cited S04/S05/S09/S10/S07 evidence.
>
> **Scope guardrail.** M001 is architecture-only. This report does not ship product ETL, a production graph schema, LegalNexus API, KnowQL parser, hybrid retrieval, parser extraction output, or legal-answering runtime behavior.

---

## 1. Executive verdict

M001 can close as an architecture review milestone, not as an implementation milestone. S07 fixed the original PRD consistency blockers and major wording mismatches, and T01 converted the remaining architecture risks into a compact machine-readable findings set. The remaining work is not more M001 prose cleanup; it is later proof work with explicit owners, verification criteria, and roadmap effect.

The four named handoff gates are:

- **G-005** — same-date multi-edition conflict semantics remain deferred and must be resolved before temporal behavior is treated as reliable for ambiguous consolidated editions.
- **G-008** — executable parser and retrieval golden tests remain deferred and must exist before parser quality, citation round-trip quality, no-answer behavior, or recall metrics are claimed.
- **G-011** — local/open-weight embedding posture is bounded by S09/S10 evidence: `deepvk/USER-bge-m3` is the practical 1024-dimensional runtime baseline on this host, while GigaEmbeddings remains a blocked challenger and managed embedding APIs remain outside the chosen boundary.
- **G-015** — FalkorDBLite-to-Docker migration safety is not proven by separate smoke success; it needs a future migration runbook and dry-run proof.

The final architecture recommendation is therefore: proceed to M002-M007 only through proof-gated implementation slices. Treat S04, S05, S09, and S10 as bounded evidence anchors, not as product readiness, legal-quality, production-scale, or parser-completeness proof.

---

## 2. Evidence inventory

| Evidence area | Row IDs | Evidence status | How a planner should use it |
|---|---|---|---|
| S07 PRD consistency closure | `S07-FIXED-PRD-CONSISTENCY` | `fixed` / `prd-fixed` | Start implementation planning from the normalized PRD text, but do not reopen fixed wording blockers unless new evidence contradicts them. |
| Temporal conflict policy | `G-005` | `deferred` / `deferred-proof-gate` | Add a future temporal proof task before relying on same-date conflict behavior across competing consolidated editions. |
| Parser and retrieval quality | `G-008`, `S05-PARSER-ODT-BOUNDARY`, `S05-OLD-PROJECT-PRIOR-ART` | `deferred` or `bounded` | Use S05 to choose an investigation direction, not to claim final extraction, EvidenceSpan, SourceBlock, citation round-trip, or retrieval quality. |
| FalkorDB runtime mechanics | `S04-FALKORDB-RUNTIME-BOUNDED`, `G-015` | `confirmed-runtime` within smoke boundary; migration deferred | Continue FalkorDB architecture exploration, but keep deployment migration, product scale, legal retrieval quality, and GraphBLAS control-surface claims behind later proof. |
| Local embeddings | `G-011`, `S10-USER-BGE-M3-BASELINE`, `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED` | `confirmed-runtime` for USER-bge-m3 baseline; `blocked-environment` for GigaEmbeddings challenger | Keep embeddings post-MVP and local/open-weight. Use USER-bge-m3 for planning only after repeating proof on target hardware; do not introduce managed API fallback. |
| M001 boundary | `M001-ARCHITECTURE-ONLY-GUARDRAIL` | `excluded` / `out-of-scope-guardrail` | Treat every product runtime behavior as future milestone work, not as delivered M001 output. |

---

## 3. Findings matrix

Table semantics are intentionally stable for human review and machine projection: **severity** expresses planning priority, **evidence** names the bounded proof source, **impact** explains what breaks or remains unsafe if ignored, **recommendation** states the next architecture action, **owner** names the accountable downstream lane, **verification** defines the proof of closure, and **roadmap** explains how M002-M007 should react.

| ID | Severity / status | Evidence | Impact | Recommendation | Owner | Verification | Roadmap effect |
|---|---|---|---|---|---|---|---|
| `S07-FIXED-PRD-CONSISTENCY` | INFO / fixed | `prd/04_review_findings.md` marks original S07 blockers and major consistency items fixed. | M001 can move from PRD normalization into final reporting without reopening closed wording defects. | Carry only remaining deferred or bounded proof gates into future planning. | S08 final architecture review. | Final report separates fixed PRD consistency work from deferred proof gates. | M002 may start from normalized PRD documents while preserving explicit proof gates. |
| `G-005` | MAJOR / deferred | `prd/04_review_findings.md` defers same-date multi-edition conflict policy. | Conflicting consolidated editions for one date can create ambiguous temporal answers and import validation behavior. | Define whether collisions become source revisions, competing `ActEdition` candidates, or validation-blocking conflicts. | S08 temporal model / future temporal proof slice. | Executable fixtures prove deterministic `active_at` and no-answer behavior for same-date collisions. | Blocks reliable temporal roadmap details for multi-source or conflicting consolidated editions; single-source MVP remains possible if ambiguity is rejected. |
| `G-008` | MAJOR / deferred | `prd/04_review_findings.md` has FR-30 skeleton only; S05 has bounded ODT smoke evidence. | Parser or retrieval quality claims would be unsupported without tracked golden fixtures. | Author golden parser and retrieval tests before any milestone depends on parser quality or recall metrics. | S08 validation/proof planning / future parser-retrieval proof slice. | CI runs golden parser tests, citation round-trip checks, no-answer tests, and recall checks against tracked fixtures. | Required before M002-M007 claim parser/retrieval quality; does not block M001 architecture-only closure. |
| `G-011` | MINOR / confirmed-runtime | S09 recommends USER-bge-m3 by integration posture; S10 confirms local USER-bge-m3 encode and 1024-dimensional FalkorDB vector proof on this host. | Embedding architecture has a bounded local baseline but no production legal retrieval quality or managed API suitability proof. | Use USER-bge-m3 as default local/open-weight runtime baseline; keep GigaEmbeddings as deferred challenger; exclude managed GigaChat API paths. | Future embedding/runtime proof. | Future proof records package/cache/download/runtime status, vector dimension, FalkorDB query proof, no raw vector leakage, and real evidence-backed retrieval metrics. | No MVP impact while embeddings stay post-MVP; affects Phase 5/vector-search and M002 proof budgeting. |
| `G-015` | MINOR / deferred | PRD defines an evolution path; S04 confirms Docker FalkorDB and FalkorDBLite separately. | Deployment milestones could overclaim safe embedded-to-container transition without export/import, persistence, rollback, auth/port, and smoke evidence. | Add a migration runbook and smoke validation proof before any deployment milestone depends on migration safety. | S08 deployment planning or later ops proof. | Later ops verifier records migration dry-run status, logs, rollback behavior, and configuration evidence. | Must be resolved before deployment milestones depend on safe storage migration. |
| `S04-FALKORDB-RUNTIME-BOUNDED` | INFO / confirmed-runtime | S04 confirms bounded Docker FalkorDB and FalkorDBLite mechanics on this host, including basic graph, UDF, procedure listing, full-text, and vector probes. | Architecture may rely on smoke-confirmed mechanics but not product suitability, production scale, legal retrieval quality, or direct GraphBLAS control-surface proof. | Cite S04 only as bounded runtime capability evidence. | S04 evidence owner / S08 final report. | S04 verifier passes and S08 labels S04 claims as bounded runtime mechanics. | Supports continued FalkorDB exploration while keeping deployment and legal-quality gates explicit. |
| `S05-PARSER-ODT-BOUNDARY` | MAJOR / bounded | S05 uses raw `content.xml` ordering as oracle, treats `odfdo` as parser direction to investigate, and keeps `odfpy` as comparison evidence. | Future parser/API guidance can choose a direction, but final hierarchy, table reconciliation, SourceBlock, EvidenceSpan, and ETL behavior remain unproven. | Investigate `odfdo`; preserve raw ordering as oracle; keep `odfpy` behind explicit manifest-cleaning review if ever used. | S05/S08 parser evidence consolidation / future parser implementation proof. | S05 verifier passes; future tests prove unmodified-source loading or reviewed manifest-cleaning with source mutation=false. | Guides M002 parser design but blocks final parser/product ETL claims until executable extraction proof exists. |
| `S05-OLD-PROJECT-PRIOR-ART` | MAJOR / bounded | S05 classifies Old_project candidates as adapt/defer or reject/defer; none are accepted unchanged. | Blind legacy reuse could import stale ConsultantPlus WordML/XML assumptions into current Garant ODT architecture. | Mine Old_project only for vocabulary/API ideas after mapping to current ODT evidence. | S08 final architecture review / future parser and API design owners. | Downstream designs classify legacy reuse as prior art and avoid blessing ConsultantPlus behavior for Garant ODT. | Allows selective concept reuse while preventing legacy runtime assumptions from entering M002 implementation plans. |
| `S10-USER-BGE-M3-BASELINE` | INFO / confirmed-runtime | S10 confirms local encode, observed 1024 vector dimension, live FalkorDB 1024-dimensional vector index/query, and fixture-ID-only retrieval metrics. | Downstream architecture can plan around a practical local/open-weight baseline without managed embedding APIs. | Carry USER-bge-m3 forward as the default practical baseline and require real EvidenceSpan/SourceBlock evaluation before quality claims. | S10 evidence owner / future embedding proof owner. | Embedding verifier passes with no managed credential literals, no raw embedding leakage, package/cache/runtime evidence, and 1024-dimensional FalkorDB proof. | Supports post-MVP embedding planning; does not change MVP scope. |
| `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED` | MINOR / blocked-environment | S10 blocks `ai-sage/Giga-Embeddings-instruct` on custom-code, `trust_remote_code`, flash-attn, acceleration/fallback, and no-swap gates; S09 flags 2048-dimensional/runtime risk. | Premature promotion would violate local safety assumptions and increase storage/runtime risk; managed fallback would violate local/open-weight decisions. | Defer challenger evaluation until explicit gates are accepted and verified; otherwise keep USER-bge-m3 baseline. | Future embedding/runtime proof. | Challenger proof records gate approvals, package/runtime status, vector dimension, FalkorDB 2048-dimensional behavior, resource envelope, and retrieval metrics without managed API fallback. | Does not block M001 closure or MVP; affects future quality-challenger budget. |
| `M001-ARCHITECTURE-ONLY-GUARDRAIL` | BLOCKER / excluded | R011 and S08 require M001 to remain architecture-only. | Final guidance could otherwise be mistaken for product runtime or legal-answering behavior. | Keep S08 artifacts as review/reporting contracts and route implementation to future proof-gated milestones. | S08 final architecture review. | S08 verifier rejects overclaim markers that promote architecture findings into production runtime, managed embedding API, final parser, product ETL, or legal-quality claims. | Protects M001 closure and clarifies M002-M007 implementation boundaries. |

---

## 4. Roadmap corrections for M002-M007

The roadmap should treat these as corrections or gates, not optional notes:

1. **M002 temporal/data-model planning must include G-005.** Same-date multi-edition conflict policy needs a design decision, fixture set, and verifier before ambiguous edition handling is treated as reliable.
2. **M002/M003 parser work must consume S05 cautiously.** `odfdo` is the current investigation direction; raw `content.xml` remains the ordering oracle; `odfpy` remains comparison evidence unless a later reviewed manifest-cleaning boundary is accepted.
3. **M003/M004 retrieval and answer-quality work must include G-008.** Golden fixtures must cover parser output, citation round-trips, no-answer behavior, and baseline recall before retrieval quality appears in product claims.
4. **M004/M005 FalkorDB work may use S04 only as bounded runtime evidence.** Do not convert synthetic smoke success into production scale, legal-quality, deployment readiness, or GraphBLAS control-surface claims.
5. **M005/M006 embedding work must preserve G-011.** USER-bge-m3 is the current local/open-weight baseline; GigaEmbeddings is a gated challenger; managed GigaChat or other managed embedding APIs are not a fallback path.
6. **M006/M007 deployment planning must include G-015.** FalkorDBLite-to-Docker migration needs a runbook, dry-run/smoke evidence, persistence checks, rollback path, and auth/port configuration proof before safe migration is claimed.
7. **All M002-M007 plans must preserve the M001 architecture-only boundary.** Implementation begins later, but this report is not itself implementation evidence.

---

## 5. Machine-readable findings path and schema proposal

S08’s local machine-readable artifact is already usable as the v1 contract:

- Current row artifact: `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`
- Current schema artifact: `.gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json`
- Proposed durable future path: `prd/findings/architecture-findings.v1.json`
- Proposed durable future schema path: `prd/findings/architecture-findings.v1.schema.json`

A future promoted `prd/findings/architecture-findings.v1.json` should preserve these required row fields:

- `id`
- `title`
- `source`
- `claim_class`
- `status`
- `severity`
- `evidence`
- `impact`
- `recommendation`
- `owner`
- `resolution_path`
- `verification_criteria`
- `roadmap_effect`
- `requirement_links`

Optional fields should remain `decision_links` and `non_goals`. The schema should continue to reject missing owner, missing resolution path, missing verification criteria, missing required IDs, invalid statuses, and overclaim-prone rows that lack non-goal boundaries.

Future tooling should keep the row artifact as the source of truth and render human reports from it, not maintain separate undocumented TODO lists. This makes machine-readable owner/resolution/verification/roadmap state visible to future agents and to human planners.

---

## 6. Non-goals and overclaim guardrails

The following claims are explicitly not made by M001, S08, or this report:

- No product ETL has been implemented.
- No production graph schema has been implemented.
- No LegalNexus API has been implemented.
- No KnowQL parser has been implemented.
- No hybrid retrieval runtime has been implemented.
- No legal-answering runtime has been implemented.
- No final legal hierarchy, SourceBlock, EvidenceSpan, or parser extraction output has been proven for the real Garant source.
- No parser/retrieval quality, citation round-trip quality, no-answer quality, or recall metric is proven without future G-008 fixtures.
- No managed GigaChat or managed embedding API fallback is allowed under the current local/open-weight boundary.
- No GigaEmbeddings default promotion is allowed while it remains blocked by environment and safety gates.
- No production-scale FalkorDB claim, legal-quality claim, deployment-readiness claim, or direct LegalGraph GraphBLAS control-surface claim follows from S04 smoke evidence.
- No FalkorDBLite-to-Docker migration safety claim follows from separate FalkorDB and FalkorDBLite smoke success.
- No Old_project artifact is accepted unchanged for Garant ODT; legacy material is prior art only.

If future work needs to promote any of these statements, it must add a row with evidence, impact, recommendation, owner, resolution path, verification criteria, and roadmap effect, then pass the relevant verifier.

---

## 7. Cold-reader action checklist

Before starting a future implementation slice, a planner should answer:

1. Which finding row does this slice close or consume?
2. Does the row already have an owner, resolution path, verification criterion, and roadmap effect?
3. Is the cited evidence fixed, bounded, confirmed-runtime, deferred, blocked-environment, or excluded?
4. Does the implementation plan upgrade a bounded claim into a product claim? If yes, add proof first.
5. Does the plan preserve local/open-weight embeddings and avoid managed API fallback?
6. Does the plan avoid treating S05 ODT smoke evidence as final legal extraction?
7. Does the plan avoid treating S04 smoke evidence as production-scale or legal-quality FalkorDB evidence?
8. Does the plan keep LLM output non-authoritative and require deterministic, evidence-backed behavior for legal answers?

A slice that cannot answer these questions should not claim closure of the relevant proof gate.
