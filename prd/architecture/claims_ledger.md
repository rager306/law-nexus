# Claims Ledger

> **Scope:** This ledger classifies each architecture registry item by the safety of asserting its claims in future planning, PRDs, or agent handoffs. It is a derived, non-authoritative planning artifact — do not use it as proof. Always cite source anchors, runtime artifacts, and real-document evidence.

## Classification Guide

| Class | Meaning | When to use |
| --- | --- | --- |
| **safe-to-say** | Source-anchor or static-check proof; active status. | Use freely with source anchor citation. |
| **bounded** | Bounded-evidence, runtime-smoke, or real-document-proof; product-scale unproven. | Cite scope; do not extrapolate. |
| **blocked/open** | Unresolved proof gate (proof_level=none) or blocked status. | Do not assert; resolve proof gate first. |
| **unsafe-to-assert** | Out-of-scope guardrail, or item without sufficient proof. | Do not assert without independent evidence. |

---

## safe-to-say

| ID | Title | Layer | Risk | Non-Claims |
| --- | --- | --- | --- | --- |
| `ASSUMP-PRD-SOURCE-TRUTH` | PRD and GSD artifacts remain source of truth | architecture-governance | high | ❌ Does not make generated artifacts authoritative. |
| `CHECK-ARCHITECTURE-EXTRACTOR` | Deterministic architecture extractor check | workflow-governance | high | ❌ Extractor check is not product runtime proof. |
| `DEC-D031` | Use docs-as-code architecture registry | architecture-governance | high | ❌ JSONL and GraphML are not source-of-truth replacements. |
| `DEC-D032` | Add architecture verification router skill in S05 | workflow-governance | medium | ❌ The skill is guidance, not a source of truth. |
| `REQ-R001` | Architecture review finding classification | architecture-governance | medium | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R009` | Architecture findings require owner and verification criteria | workflow-governance | high | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R010` | Machine-readable architecture findings path | architecture-governance | medium | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R017` | Assess FalkorDB text-to-cypher PyO3 route | generated-cypher | high | ❌ No product Legal KnowQL behavior claim.; ❌ No legal-answer correctness claim. |
| `REQ-R022` | Proof artifacts remain redacted and categorical | security-safety | critical | ❌ No raw provider body persistence claim.; ❌ No credential, prompt, raw legal text, or raw row emission claim. |
| `REQ-R029` | Executable architecture verification workflow | architecture-governance | high | ❌ Does not itself prove product runtime behavior. |
| `RISK-OVERCLAIM-RUNTIME` | Runtime and legal overclaim risk | security-safety | critical | ❌ Risk item does not assert current product failure. |

---

## bounded

| ID | Title | Layer | Risk | Proof Level | Non-Claims |
| --- | --- | --- | --- | --- | --- |
| `S04-FALKORDB-RUNTIME-BOUNDED` | FalkorDB runtime mechanics smoke boundary | graph-runtime | medium | runtime-smoke | ❌ No production-scale FalkorDB claim.; ❌ No legal retrieval quality claim. |
| `S05-OLD-PROJECT-PRIOR-ART` | Old_project artifacts remain prior art | parser-ingestion | high | source-anchor | ❌ No Old_project artifact accepted unchanged.; ❌ No parser completeness claim. |
| `S05-PARSER-ODT-BOUNDARY` | Real ODT parser evidence boundary | parser-ingestion | high | real-document-proof | ❌ No final legal hierarchy extraction claim.; ❌ No parser completeness claim. |
| `S07-FIXED-PRD-CONSISTENCY` | S07 PRD consistency closure | architecture-governance | low | source-anchor | ❌ Does not prove product behavior. |
| `S10-USER-BGE-M3-BASELINE` | USER-bge-m3 bounded local embedding baseline | retrieval-embedding | medium | runtime-smoke | ❌ No product retrieval quality claim.; ❌ No managed embedding API fallback claim. |

---

## blocked/open

| ID | Title | Layer | Risk | Proof Level | Verification | Non-Claims |
| --- | --- | --- | --- | --- | --- | --- |
| `GATE-G005` | Temporal same-date multi-edition conflict policy | temporal-model | high | none | A future proof slice defines and verifies same-date/multi-ed... |
| `GATE-G008` | Executable parser and retrieval golden tests | parser-ingestion | high | none | Golden tests pass on real legal source fixtures and retrieva... |
| `GATE-G011` | Local embedding quality proof | retrieval-embedding | high | none | Retrieval quality benchmark passes under local/open-weight e... |
| `GATE-G015` | FalkorDBLite to Docker migration runbook | graph-runtime | medium | none | Migration runbook is executed against bounded fixtures and r... |
| `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED` | GigaEmbeddings challenger blocked by environment and safety gates | retrieval-embedding | medium | none | Challenger proof records gate approvals, runtime status, vec... |

---

## unsafe-to-assert

| ID | Title | Layer | Risk | Status | Non-Claims |
| --- | --- | --- | --- | --- | --- |
| `M001-ARCHITECTURE-ONLY-GUARDRAIL` | M001 architecture-only guardrail | architecture-governance | critical | out-of-scope | ❌ No product ETL.; ❌ No production graph schema. |
| `REQ-R028` | LLM output is not legal authority | security-safety | critical | out-of-scope | ❌ No LLM legal authority claim.; ❌ No legal-answer correctness claim. |

---

*Claims ledger generated from `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_graph_report.json`. This is a derived, non-authoritative planning artifact. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
