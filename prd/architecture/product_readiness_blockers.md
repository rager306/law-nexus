# Product Readiness Blockers Report

> **Scope:** This report maps active proof gates, blocked evidence, and non-claims to the six capability areas required for LegalGraph Nexus product readiness. It is a planning artifact only — it does **not** assert product readiness and does not validate runtime behavior, retrieval quality, parser completeness, generated-Cypher safety, FalkorDB production scale, or legal-answer correctness.

---

## Summary Table

| Capability Area | Gate Count | Blocked / Bounded Count |
| --- | ---: | ---: |
| ETL / Parser | 1 | 2 |
| Graph Runtime | 1 | 0 |
| Legal Answering | 0 | 0 |
| Legal KnowQL / Generated Cypher | 0 | 0 |
| Retrieval / Embedding | 1 | 0 |
| Temporal Model | 1 | 0 |

## ETL / Parser

### Proof Gates

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-G008` | Executable parser and retrieval golden tests | high | Golden tests pass on real legal source fixtures and retrieval expectations. | future-parser-retrieval-proof |
|  | No parser completeness claim. | — | — | — |
|  | No product retrieval quality claim. | — | — | — |

### Blocked / Bounded Evidence

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `S05-OLD-PROJECT-PRIOR-ART` | Old_project artifacts remain prior art | high | Downstream designs classify legacy reuse as prior art and avoid blessing ConsultantPlus behavior for Garant ODT. | S08 final architecture review / future parser owners |
|  | No Old_project artifact accepted unchanged. | — | — | — |
|  | No parser completeness claim. | — | — | — |
| `S05-PARSER-ODT-BOUNDARY` | Real ODT parser evidence boundary | high | S05 verifier passes; future parser tests prove final extraction behavior before promotion. | S05/S08 parser evidence consolidation |
|  | No final legal hierarchy extraction claim. | — | — | — |
|  | No parser completeness claim. | — | — | — |
|  | No production SourceBlock/EvidenceSpan creation claim. | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| No parser completeness claim. |
| No product retrieval quality claim. |
| No Old_project artifact accepted unchanged. |
| No final legal hierarchy extraction claim. |
| No production SourceBlock/EvidenceSpan creation claim. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G008`](#proof-gates): Golden tests pass on real legal source fixtures and retrieval expectations.
- Resolve [`S05-OLD-PROJECT-PRIOR-ART`](#blocked--bounded-evidence): Downstream designs classify legacy reuse as prior art and avoid blessing ConsultantPlus behavior for Garant ODT.
- Resolve [`S05-PARSER-ODT-BOUNDARY`](#blocked--bounded-evidence): S05 verifier passes; future parser tests prove final extraction behavior before promotion.

## Graph Runtime

### Proof Gates

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-G015` | FalkorDBLite to Docker migration runbook | medium | Migration runbook is executed against bounded fixtures and runtime diagnostics. | future-runtime-migration-proof |
|  | No production-scale FalkorDB claim. | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| No production-scale FalkorDB claim. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G015`](#proof-gates): Migration runbook is executed against bounded fixtures and runtime diagnostics.

## Legal Answering

No active proof gates or blocked evidence for this area in the current architecture registry.


## Legal KnowQL / Generated Cypher

No active proof gates or blocked evidence for this area in the current architecture registry.


## Retrieval / Embedding

### Proof Gates

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-G011` | Local embedding quality proof | high | Retrieval quality benchmark passes under local/open-weight embedding constraints. | future-retrieval-quality-proof |
|  | No managed embedding API fallback claim. | — | — | — |
|  | No product retrieval quality claim. | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| No managed embedding API fallback claim. |
| No product retrieval quality claim. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G011`](#proof-gates): Retrieval quality benchmark passes under local/open-weight embedding constraints.

## Temporal Model

### Proof Gates

| ID | Title | Risk | Verification | Owner |
| --- | --- | --- | --- | --- |
| `GATE-G005` | Temporal same-date multi-edition conflict policy | high | A future proof slice defines and verifies same-date/multi-edition conflict policy. | future-temporal-proof |
|  | Does not validate temporal conflict resolution. | — | — | — |

### What This Area Does Not Prove

_Below non-claims are drawn directly from architecture registry records. They are not exhaustive._

| Non-Claim |
| --- |
| Does not validate temporal conflict resolution. |

### Next Proof Work

Proof work for this area should:

- Address [`GATE-G005`](#proof-gates): A future proof slice defines and verifies same-date/multi-edition conflict policy.

---

## Global Non-Claims Summary

_The following statements appear across one or more architecture records and collectively define what this architecture does NOT validate:_

| Non-Claim | Appears In |
| --- | --- |
| Does not make generated artifacts authoritative. | `ASSUMP-PRD-SOURCE-TRUTH` |
| Extractor check is not product runtime proof. | `CHECK-ARCHITECTURE-EXTRACTOR` |
| JSONL and GraphML are not source-of-truth replacements. | `DEC-D031` |
| The skill is guidance, not a source of truth. | `DEC-D032` |
| Does not validate temporal conflict resolution. | `GATE-G005` |
| No parser completeness claim. | `GATE-G008` |
| No product retrieval quality claim. | `GATE-G008` |
| No managed embedding API fallback claim. | `GATE-G011` |
| No production-scale FalkorDB claim. | `GATE-G015` |
| No KnowQL parser. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No LegalNexus API. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No hybrid retrieval. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No legal-answering runtime. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No product ETL. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No production graph schema. | `M001-ARCHITECTURE-ONLY-GUARDRAIL` |
| No LLM legal authority claim. | `REQ-R001` |
| No legal-answer correctness claim. | `REQ-R001` |
| No product Legal KnowQL behavior claim. | `REQ-R001` |
| No live legal graph execution claim. | `REQ-R017` |
| No credential, prompt, raw legal text, or raw row emission claim. | `REQ-R022` |
| No raw provider body persistence claim. | `REQ-R022` |
| No generated Cypher authority claim. | `REQ-R028` |
| Does not itself prove product runtime behavior. | `REQ-R029` |
| Risk item does not assert current product failure. | `RISK-OVERCLAIM-RUNTIME` |
| No direct LegalGraph GraphBLAS API/control surface claim. | `S04-FALKORDB-RUNTIME-BOUNDED` |
| No legal retrieval quality claim. | `S04-FALKORDB-RUNTIME-BOUNDED` |
| No Old_project artifact accepted unchanged. | `S05-OLD-PROJECT-PRIOR-ART` |
| No final legal hierarchy extraction claim. | `S05-PARSER-ODT-BOUNDARY` |
| No production SourceBlock/EvidenceSpan creation claim. | `S05-PARSER-ODT-BOUNDARY` |
| Does not prove product behavior. | `S07-FIXED-PRD-CONSISTENCY` |
| No default promotion while blocked-environment. | `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED` |
| No raw embedding leakage claim beyond verifier scope. | `S10-USER-BGE-M3-BASELINE` |

---

*Blockers report generated from `prd/architecture/architecture_graph_report.json`. This is a planning artifact — it makes next proof work visible without asserting product readiness. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
