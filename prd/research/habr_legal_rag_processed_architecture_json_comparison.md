---
source: "JSON-based comparison of Habr Legal RAG article against processed LegalGraph architecture state"
source_document: "prd/research/habr_legal_rag_17_iterations_scaling_wall.md"
prior_assessment: "prd/research/habr_legal_rag_17_iterations_scaling_wall_assessment.md"
prior_mapping: "prd/research/habr_legal_rag_graph_query_architecture_mapping.md"
processed_architecture_inputs:
  - "prd/architecture/architecture_items.jsonl"
  - "prd/architecture/architecture_edges.jsonl"
  - "prd/architecture/architecture_graph_report.json"
  - ".gsd/milestones/M001/slices/S08/S08-FINDINGS.json"
status: "research-json-comparison"
non_authoritative: true
requires_project_verification_before_adoption: true
human_review_decision: "D045"
created_at: "2026-05-13T06:20:00+00:00"
reviewed_at: "2026-05-13T06:24:00+00:00"
notes: "This artifact compares Habr Legal RAG ideas to processed architecture JSON/JSONL records. It does not use architecture Markdown as the comparison baseline and does not validate product behavior. Human review confirmed that transferable ideas require project-specific verification before adoption."
---

# Habr Legal RAG vs Processed Architecture JSON Comparison

## Human Review Status

Decision `D045` records the human review outcome: transferable ideas from the Habr Legal RAG case study are candidates requiring project-specific verification before adoption. This review does not close any proof gate and does not validate product retrieval quality, parser completeness, FalkorDB runtime behavior, generated-Cypher safety, or legal-answer correctness.

## Correction

The previous architecture mapping used PRD/architecture Markdown as context. That was useful for prose explanation, but it was not the comparison the project needed. The correct comparison baseline is the processed architecture state:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`
- `prd/architecture/architecture_graph_report.json`
- `.gsd/milestones/M001/slices/S08/S08-FINDINGS.json`

This document compares the Habr article's approaches against those processed records, not against architecture Markdown prose.

## Processed Architecture Snapshot Used

From `prd/architecture/architecture_graph_report.json`:

- nodes: `39`
- edges: `41`
- contradiction pairs: none
- active high/critical gates relevant to this comparison:
  - `GATE-G008` — Product parser and retrieval readiness gate
  - `GATE-G011` — Local embedding quality proof
  - `GATE-G005` — Temporal same-date multi-edition conflict policy
  - `GATE-GENERATED-CYPHER-SAFETY` — Generated-Cypher safety and validation gate
  - `GATE-EMBEDDING-SUPPLY-CHAIN` — Embedding model supply-chain integrity gate
  - `GATE-G015` — FalkorDBLite to Docker migration runbook
  - `GATE-LEGAL-NEXUS-ACCESS-CONTROL` — Legal Nexus access-control proof gate

The processed registry already encodes strong non-claims: no product retrieval quality claim, no parser completeness claim, no production-scale FalkorDB claim, no generated-Cypher execution authorization, no legal-answer correctness claim, and no LLM legal authority claim.

## Relevant Processed Records

| Record ID | Type / Layer | Processed Status | What It Means for Article Comparison |
| --- | --- | --- | --- |
| `DATA-LEGAL-EVIDENCE-CORE` | data entity / legal-evidence | `active`, `source-anchor`, high risk | Existing graph concept already contains `LegalAct`, `ActEdition`, `SourceDocument`, `SourceBlock`, `EvidenceSpan`, `NormStatement`. Article page-grounding maps here, but cannot validate schema completeness. |
| `DATA-TEMPORAL-PROPERTY-BUNDLE` | data entity / temporal-model | `active`, `source-anchor`, high risk | Article's scale/disambiguation lessons reinforce temporal routing, but do not solve same-date/multi-edition conflicts. |
| `COMP-LEGAL-NEXUS-ORCHESTRATOR` | component / api-product | `active`, `source-anchor`, high risk | Article's retrieval orchestration maps to this future boundary, but processed record says runtime behavior and access control are unproven. |
| `EVID-PARSER-GOLDEN-TEST-PROOF` | evidence / parser-ingestion | `bounded-evidence`, `unit-test` | Closest existing evidence to article's local eval-set lesson. It remains bounded and explicitly does not prove product retrieval quality. |
| `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` | evidence / parser-ingestion | `bounded-evidence`, `real-document-proof` | Provides bounded hierarchy records for one Consultant tracer; useful for future graph-scoped retrieval fixtures, not product completeness. |
| `EVID-PARSER-ODT-SMOKE` | evidence / parser-ingestion | `bounded-evidence`, `real-document-proof` | Gives raw ODT smoke evidence; article cannot upgrade it to final hierarchy/evidence extraction. |
| `EVID-PARSER-STAGING-GRAPH` | evidence / parser-ingestion | `bounded-evidence`, `static-check` | Existing non-FalkorDB staging graph is relevant to proving graph-shaped parser records before runtime loading. |
| `S10-USER-BGE-M3-BASELINE` | evidence / retrieval-embedding | `bounded-evidence`, `runtime-smoke` | Article supports evaluating local embedding retrieval, but processed record says no product retrieval quality and no managed fallback claim. |
| `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED` | evidence / retrieval-embedding | `blocked`, `none` | Article's local-model lesson does not unblock this. Managed GigaChat/GigaChat API remains excluded by project decision. |
| `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` | evidence / retrieval-embedding | `bounded-evidence`, `source-anchor` | Existing bounded research input. The Habr article should be represented similarly if added to registry. |
| `REQ-R028` | requirement / security-safety | `out-of-scope`, `source-anchor`, critical | Confirms LLM output and generated Cypher are not legal authority. Article's post-LLM verification aligns with this. |
| `RISK-OVERCLAIM-RUNTIME` | risk / security-safety | `active`, `source-anchor`, critical | Article must not be used to assert runtime, parser, retrieval, FalkorDB, generated-Cypher, or legal-answer readiness. |
| `M001-ARCHITECTURE-ONLY-GUARDRAIL` | workflow_check / architecture-governance | `out-of-scope`, `source-anchor`, critical | Prevents using article experience as implementation/product claim in M001-derived architecture state. |

## Article Idea → Processed Record Mapping

### 1. Format-first validation

**Article idea:** validate submission/citation output format before improving retrieval quality.

**Processed records:**

- `DATA-LEGAL-EVIDENCE-CORE`
- `REQ-R029`
- `CHECK-ARCHITECTURE-EXTRACTOR`
- `EVID-PARSER-GOLDEN-TEST-PROOF`

**Fit:** strong.

**JSON-grounded interpretation:** the architecture already has a machine-readable verification culture. The article suggests extending that pattern from architecture registry JSONL to retrieval/evidence output contracts: citation keys, EvidenceSpan IDs, SourceBlock IDs, ActEdition IDs, and answer schemas should fail closed if unresolved.

**Gap:** no processed record currently represents a dedicated retrieval-output ID validator proof. This is a candidate future proof item, likely under `GATE-G008` and `GATE-G011`.

### 2. Page-level grounding

**Article idea:** retrieve/cite pages because competition scorer evaluates page IDs.

**Processed records:**

- `DATA-LEGAL-EVIDENCE-CORE`
- `EVID-PARSER-ODT-SMOKE`
- `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF`
- `EVID-PARSER-GOLDEN-TEST-PROOF`

**Fit:** partial, transformed.

**JSON-grounded interpretation:** processed records prefer evidence concepts (`SourceBlock`, `EvidenceSpan`, hierarchy records), not page-level authority. The article supports citation-unit alignment, but the aligned unit for LegalGraph is not a page by default.

**Gap:** product `EvidenceSpan` creation is still explicitly unproven through `GATE-G008` and non-claims in parser evidence records.

### 3. Article index first

**Article idea:** article definition pages should be prioritized over arbitrary mentions.

**Processed records:**

- `DATA-LEGAL-EVIDENCE-CORE`
- `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF`
- `EVID-PARSER-STAGING-GRAPH`
- `GATE-G008`

**Fit:** strong as graph lookup principle.

**JSON-grounded interpretation:** this maps to deterministic graph traversal over legal hierarchy records before similarity search. The processed JSON already has bounded hierarchy/staging evidence, but not product graph retrieval readiness.

**Gap:** no processed record yet proves exact citation lookup over final FalkorDB graph records.

### 4. BM25 + embeddings + RRF hybrid retrieval

**Article idea:** hybrid lexical/semantic retrieval improves candidate generation.

**Processed records:**

- `GATE-G011`
- `GATE-EMBEDDING-SUPPLY-CHAIN`
- `S10-USER-BGE-M3-BASELINE`
- `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED`
- `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS`

**Fit:** proof-gated candidate only.

**JSON-grounded interpretation:** processed JSON allows local/open-weight embedding exploration only as bounded evidence. `S10-USER-BGE-M3-BASELINE` is a local runtime smoke baseline, but `GATE-G011` still says product retrieval quality is unproven.

**Gap:** no processed record proves BM25+embedding+RRF quality over real LegalGraph EvidenceSpan/SourceBlock fixtures.

### 5. Cross-encoder reranking

**Article idea:** rerank top candidates after BM25/embeddings.

**Processed records:**

- `GATE-G011`
- `GATE-EMBEDDING-SUPPLY-CHAIN`
- `RISK-OVERCLAIM-RUNTIME`

**Fit:** speculative / proof-gated.

**JSON-grounded interpretation:** the processed architecture has no validated reranker record. Reranking could become a future retrieval-quality experiment, but must be recorded with model provenance, local runtime envelope, metrics, and no-secret/no-raw-vector leakage checks.

**Gap:** no existing processed item for reranker runtime, supply chain, or quality impact.

### 6. Precision over citation volume

**Article idea:** extra citations reduce grounding; minimal sufficient evidence often beats broad citation lists.

**Processed records:**

- `DATA-LEGAL-EVIDENCE-CORE`
- `EVID-PARSER-GOLDEN-TEST-PROOF`
- `GATE-G008`
- `GATE-G011`
- `REQ-R028`

**Fit:** strong.

**JSON-grounded interpretation:** processed architecture already treats evidence as explicit and non-authoritative until verified. The article sharpens the metric design: future retrieval proofs should measure precision/recall/F-beta over stable EvidenceSpan or citation IDs, not just answer text quality.

**Gap:** current processed records do not expose an evidence precision benchmark item.

### 7. Deterministic fast paths for typed answers

**Article idea:** use deterministic extraction for numbers/dates/booleans where possible.

**Processed records:**

- `COMP-LEGAL-NEXUS-ORCHESTRATOR`
- `DATA-TEMPORAL-PROPERTY-BUNDLE`
- `DATA-LEGAL-EVIDENCE-CORE`
- `REQ-R028`
- `GATE-G005`

**Fit:** strong.

**JSON-grounded interpretation:** this matches deterministic-first architecture. For LegalGraph, fast paths correspond to graph queries for citation lookup, status checks, temporal applicability, references, deadlines, conditions, exceptions, and verified NormStatements.

**Gap:** Legal Nexus runtime behavior remains unimplemented/unproven in processed record `COMP-LEGAL-NEXUS-ORCHESTRATOR`.

### 8. Post-LLM verification

**Article idea:** reject or correct LLM answers if answer values do not appear in retrieved evidence.

**Processed records:**

- `REQ-R028`
- `DATA-LEGAL-EVIDENCE-CORE`
- `RISK-OVERCLAIM-RUNTIME`
- `GATE-GENERATED-CYPHER-SAFETY`

**Fit:** very strong.

**JSON-grounded interpretation:** processed architecture already rejects LLM output as legal authority. The article provides practical justification: LLM output should be a candidate answer that must resolve to graph evidence paths.

**Gap:** no product legal-answer verification proof exists; generated-Cypher safety is still critical/open.

### 9. No-answer/adversarial handling

**Article idea:** `null`/fallback behavior must be evaluated and can regress if the evaluator semantics are misunderstood.

**Processed records:**

- `EVID-PARSER-GOLDEN-TEST-PROOF`
- `GATE-G008`
- `REQ-R028`
- `M001-ARCHITECTURE-ONLY-GUARDRAIL`

**Fit:** strong as proof-design guidance.

**JSON-grounded interpretation:** no-answer must be scoped and evidence-driven. The architecture should not assert legal absence globally; it should report no verified evidence in a specific source/date/unit scope.

**Gap:** no processed product no-answer evaluation gate exists separately; it should be included under parser/retrieval readiness and legal-answer verification work.

### 10. Scale failure and retrieval dilution

**Article idea:** a pipeline that works on 30 documents lost 42% on 300 documents due to retrieval dilution and ambiguity.

**Processed records:**

- `GATE-G008`
- `GATE-G011`
- `GATE-G015`
- `RISK-OVERCLAIM-RUNTIME`
- `QS-OBSERVABILITY-OPERABILITY-BASELINE`

**Fit:** strong as risk evidence, not as proof.

**JSON-grounded interpretation:** processed architecture already blocks product retrieval quality and production-scale FalkorDB claims. The article argues future proofs must include synthetic scale/noise degradation tests before promoting retrieval quality.

**Gap:** no current processed item encodes scale/noise degradation benchmark as a required proof artifact.

## Processed Graph Implications

### Existing JSON State Already Supports These Principles

The processed records already support:

1. Architecture artifacts are derived and non-authoritative (`ASSUMP-PRD-SOURCE-TRUTH`, `DEC-D031`).
2. Core legal evidence entities exist as active source-anchored architecture concepts (`DATA-LEGAL-EVIDENCE-CORE`).
3. Temporal semantics are active but unresolved for conflict policy (`DATA-TEMPORAL-PROPERTY-BUNDLE`, `GATE-G005`).
4. Legal Nexus is only a future component boundary, not runtime (`COMP-LEGAL-NEXUS-ORCHESTRATOR`).
5. Local embedding work is bounded and not product quality proof (`S10-USER-BGE-M3-BASELINE`, `GATE-G011`).
6. Parser/golden evidence exists but is bounded (`EVID-PARSER-*`).
7. LLM/legal-answer/generated-Cypher overclaims are explicitly blocked (`REQ-R028`, `GATE-GENERATED-CYPHER-SAFETY`, `RISK-OVERCLAIM-RUNTIME`).

### Missing or Weakly Represented in Processed JSON

The Habr article suggests several architecture/proof records that are not yet first-class processed JSON items:

| Missing Candidate Record | Suggested Layer | Why It Matters |
| --- | --- | --- |
| Retrieval output ID validator proof | parser-ingestion / retrieval-embedding | Prevents `.pdf`-style citation/ID failures in LegalGraph outputs. |
| Evidence precision benchmark | retrieval-embedding | Measures precision/recall/F-beta over `EvidenceSpan`/citation IDs, not answer prose. |
| Hierarchical graph retrieval proof | retrieval-embedding / legal-evidence | Proves graph filters before similarity search. |
| Scoped no-answer evaluation | parser-ingestion / legal-answering | Ensures no-answer semantics are audited and do not hallucinate legal absence. |
| Scale/noise degradation benchmark | retrieval-embedding / graph-runtime | Catches retrieval dilution before product claims. |
| Reranker candidate gate | retrieval-embedding / security-safety | Keeps rerank models supply-chain and quality gated. |
| Retrieval run observability contract | observability-operability | Captures candidate counts, filters, rejected evidence, latency, and regression deltas. |

These should not be hand-added to derived JSONL. If adopted, update source evidence/requirements/decisions first, then regenerate through the extractor.

## Recommended JSON-Level Architecture Action

If we want the Habr article represented in processed architecture state, the correct pattern is to add a bounded research evidence record analogous to `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS`.

Candidate record shape, conceptually:

```text
id: EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING
layer: retrieval-embedding
status: bounded-evidence
proof_level: source-anchor
risk_level: high
source_anchors:
  - prd/research/habr_legal_rag_17_iterations_scaling_wall.md
  - prd/research/habr_legal_rag_17_iterations_scaling_wall_assessment.md
  - prd/research/habr_legal_rag_processed_architecture_json_comparison.md
verification:
  Assessment classifies ideas against processed architecture records and preserves proof gates.
non_claims:
  - Does not prove product retrieval quality.
  - Does not prove parser completeness.
  - Does not prove legal-answer correctness.
  - Does not prove FalkorDB runtime/vector/full-text/rerank behavior.
  - Does not authorize generated Cypher execution.
```

Relationships should link it to, or mark it as informing, the open gates:

- `GATE-G008`
- `GATE-G011`
- `GATE-EMBEDDING-SUPPLY-CHAIN`
- `GATE-G005`
- `GATE-GENERATED-CYPHER-SAFETY`
- `GATE-G015`

But the relationship should be advisory/input only, not validation/closure.

## Corrected Bottom Line

Compared against processed architecture JSON, the Habr article does not change current architecture state or close any gate. It aligns strongly with existing processed constraints: deterministic-first evidence, bounded parser/retrieval proof, local embedding caution, LLM non-authority, and runtime overclaim prevention.

Its main contribution is to expose missing future proof records: retrieval output ID validation, EvidenceSpan-level precision metrics, graph-constrained retrieval proof, scoped no-answer evaluation, scale/noise degradation tests, and retrieval observability. These should be added only through source-of-truth updates and extractor regeneration, not by hand-editing processed JSONL.
