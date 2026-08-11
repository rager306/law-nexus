# Claims Ledger

> **D7 QUARANTINE — DERIVED VIEW.** Disposition baseline `bfe2ee6`, as-of 2026-08-11. Historical/era and missing-anchor records are quarantined diagnostics; classifications remain non-authoritative.
> This view cannot satisfy requirements, promote lifecycle, or prove product/legal/runtime/parser/retrieval claims. Canonical truth: `prd/ARCHITECTURE.md`, `doc/adr/**`, `prd/PRODUCT.md`.

> **Scope:** This ledger classifies each architecture registry item by the safety of asserting its claims in future planning, PRDs, or agent handoffs. It is a derived, non-authoritative planning artifact — do not use it as proof. Always cite source anchors, runtime artifacts, and real-document evidence.

## Classification Guide

| Class | Meaning | When to use |
| --- | --- | --- |
| **safe-to-say** | Source-anchor or static-check proof; active status. | Use freely with source anchor citation. |
| **bounded** | Bounded-evidence, runtime-smoke, or real-document-proof; product-scale unproven. | Cite scope; do not extrapolate. |
| **blocked/open** | Unresolved proof gate (proof_level=none) or blocked status. | Do not assert; resolve proof gate first. |
| **unsafe-to-assert** | Out-of-scope guardrail, or item without sufficient proof. | Do not assert without independent evidence. |

## R035 Gate Status

Ontology, external-standard, GraphRAG, graph-vector, and pilot-scale rows are registry/view synchronization-only guardrails. They are not standard, runtime, product behavior, retrieval quality, FalkorDB runtime, or R035 validation.

Historical S07/S08 runtime-remediation artifacts are archive-only and are not tracked evidence anchors. R035 remains active and requires new tracked current-plane evidence; archive artifacts do not validate ontology behavior, formal standard conformance, graph-vector/HNSW behavior, parser completeness, product retrieval quality, legal-answer correctness, or pilot readiness.

| ID | Trigger | Current Safe Bucket | Required Gate | Minimum Proof | Status | Missing Requirements | Remediation Class |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` | FRBR | compatibility/reference projection only | GATE-AKOMA-FRBR-NORMALIZATION | static-check | blocked | proof_level<static-check | add-proof-gate |
| `DATA-LEGAL-SOURCE-HIERARCHY` | legal source hierarchy, source hierarchy, supersession | proof-gated legal-priority candidate | GATE-LEGAL-COLLISION-POLICY | static-check | blocked | proof_level<static-check | add-proof-gate |
| `DATA-LKIF-DEONTIC-MAPPING` | LKIF, deontic mapping | proof-gated candidate | GATE-LKIF-DEONTIC-BENCHMARK | unit-test | blocked | proof_level<unit-test | add-proof-gate |
| `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` | RusLegalCore | proof-gated domain-scope candidate | GATE-RUSLEGALCORE-SCOPE | static-check | blocked | proof_level<static-check | add-proof-gate |
| `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` | GraphRAG | proof-gated integration candidate | GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | integration-test | superseded | proof_level<integration-test | add-proof-gate |
| `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` | Akoma Ntoso, FRBR | compatibility/reference projection only | GATE-AKOMA-FRBR-NORMALIZATION | static-check | blocked | proof_level<static-check | add-proof-gate |
| `GATE-AKOMA-FRBR-NORMALIZATION` | Akoma Ntoso, FRBR | compatibility/reference projection only | GATE-AKOMA-FRBR-NORMALIZATION | static-check | blocked | proof_level<static-check | add-proof-gate |
| `GATE-BFO-GOST-ALIGNMENT` | BFO, GOST, OWL, Common Logic | deferred formal-alignment review | GATE-BFO-GOST-ALIGNMENT | static-check | blocked | proof_level<static-check | add-proof-gate |
| `GATE-LEGAL-COLLISION-POLICY` | legal collision policy, collision policy, lex superior, lex specialis, lex posterior, supersession | proof-gated legal-priority candidate | GATE-LEGAL-COLLISION-POLICY | static-check | blocked | proof_level<static-check | add-proof-gate |
| `GATE-LKIF-DEONTIC-BENCHMARK` | LKIF | proof-gated candidate | GATE-LKIF-DEONTIC-BENCHMARK | unit-test | blocked | proof_level<unit-test | add-proof-gate |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | Ontology GraphRAG | proof-gated integration candidate | GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | integration-test | blocked | proof_level<integration-test | add-proof-gate |
| `GATE-PILOT-SCALE-READINESS` | pilot-scale, 1,000-document | deferred readiness proof | GATE-PILOT-SCALE-READINESS | integration-test | blocked | proof_level<integration-test | add-proof-gate |
| `GATE-RUSLEGALCORE-SCOPE` | RusLegalCore | proof-gated domain-scope candidate | GATE-RUSLEGALCORE-SCOPE | static-check | blocked | proof_level<static-check | add-proof-gate |

---

## safe-to-say

| ID | Title | Layer | Claim Domain | Risk | Non-Claims |
| --- | --- | --- | --- | --- | --- |
| `REQ-R001` | Architecture review finding classification | architecture-governance | registry/process | medium | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R009` | Architecture findings require owner and verification criteria | workflow-governance | registry/process | high | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R010` | Machine-readable architecture findings path | architecture-governance | registry/process | medium | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R022` | Proof artifacts remain redacted and categorical | security-safety | architecture-planning | critical | ❌ No raw provider body persistence claim.; ❌ No credential, prompt, raw legal text, or raw row emission claim. |
| `REQ-R029` | Executable architecture verification workflow | architecture-governance | registry/process | high | ❌ Does not itself prove product runtime behavior.; ❌ This registry row is a non-authoritative derived diagnostic and cannot by itself satisfy a requirement or promote lifecycle. |
| `REQ-R034` | Retrieval output evidence identifiers fail closed | retrieval-embedding | bounded-technical-proof | high | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness. |

---

## bounded

| ID | Title | Layer | Claim Domain | Risk | Proof Level | Non-Claims |
| --- | --- | --- | --- | --- | --- | --- |
| `EVID-PARSER-ODT-SMOKE` | Bounded ODT smoke-record evidence | parser-ingestion | bounded-technical-proof | high | real-document-proof | ❌ No final legal hierarchy extraction claim.; ❌ No parser completeness claim.; ❌ This registry row is a non-authoritative derived diagnostic and cannot by itself satisfy a requirement or promote lifecycle. |
| `EVID-PARSER-RECORD-CONTRACT` | Parser record contract evidence | parser-ingestion | bounded-technical-proof | medium | static-check | ❌ Does not prove product ETL readiness.; ❌ Does not prove parser completeness.; ❌ This registry row is a non-authoritative derived diagnostic and cannot by itself satisfy a requirement or promote lifecycle. |

---

## blocked/open

| ID | Title | Layer | Claim Domain | Risk | Status | Proof Level | Verification | Non-Claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ASSUMP-PRD-SOURCE-TRUTH` | Quarantined missing-anchor: PRD and GSD artifacts remain source of truth | architecture-governance | registry/process | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not make generated artifacts authoritative.; ❌ Missing-anchor quarantine cannot satisfy requirements, establish current architecture, or promote lifecycle. |
| `CHECK-ARCHITECTURE-EXTRACTOR` | Quarantined missing-anchor: Deterministic architecture extractor check | workflow-governance | registry/process | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Extractor check is not product runtime proof.; ❌ Missing-anchor quarantine cannot satisfy requirements, establish current architecture, or promote lifecycle. |
| `COMP-LEGAL-NEXUS-ORCHESTRATOR` | Quarantined missing-anchor: Legal Nexus orchestrator component boundary | api-product | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not implement Legal Nexus runtime behavior.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` | Quarantined missing-anchor: FRBR-like legal document identity candidate | temporal-model | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-LEGAL-EVIDENCE-CORE` | Quarantined missing-anchor: Core legal evidence entities | legal-evidence | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not assert final legal graph schema completeness.; ❌ Does not prove legal-answer correctness. |
| `DATA-LEGAL-SOURCE-HIERARCHY` | Quarantined missing-anchor: Legal source hierarchy candidate | legal-evidence | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-LKIF-DEONTIC-MAPPING` | Quarantined missing-anchor: LKIF-inspired deontic mapping candidate | legal-evidence | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` | Quarantined missing-anchor: RusLegalCore domain ontology candidate | legal-evidence | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-TEMPORAL-PROPERTY-BUNDLE` | Quarantined missing-anchor: Temporal property bundle | temporal-model | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not specify temporal storage implementation.; ❌ Does not validate temporal conflict resolution. |
| `DEC-D031` | Quarantined missing-anchor: Use docs-as-code architecture registry | architecture-governance | registry/process | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ JSONL and GraphML are not source-of-truth replacements.; ❌ Missing-anchor quarantine cannot satisfy requirements, establish current architecture, or promote lifecycle. |
| `DEC-D032` | Quarantined missing-anchor: Add architecture verification router skill in S05 | workflow-governance | registry/process | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ The skill is guidance, not a source of truth.; ❌ Missing-anchor quarantine cannot satisfy requirements, establish current architecture, or promote lifecycle. |
| `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` | Quarantined missing-anchor: Local retrieval quality benchmark proof | retrieval-embedding | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness. |
| `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` | Quarantined missing-anchor: Offline citation-safe retrieval proof | retrieval-embedding | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness. |
| `EVID-PARSER-CONSULTANT-CANDIDATES` | Quarantined missing-anchor: Consultant relation-candidate evidence | parser-ingestion | bounded-technical-proof | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove Consultant relation correctness.; ❌ Does not prove parser completeness. |
| `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` | Quarantined missing-anchor: Consultant full-act hierarchy parser proof | parser-ingestion | bounded-technical-proof | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove multi-document Consultant expansion.; ❌ Does not prove Garant ODT parser regression. |
| `EVID-PARSER-GOLDEN-TEST-PROOF` | Quarantined missing-anchor: Bounded parser/retrieval golden-test proof | parser-ingestion | bounded-technical-proof | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove parser completeness.; ❌ Does not prove product retrieval quality. |
| `EVID-PARSER-SOURCE-FIXTURE-INVENTORY` | Quarantined missing-anchor: Parser source fixture inventory evidence | parser-ingestion | bounded-technical-proof | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove parser completeness.; ❌ Does not prove legal correctness. |
| `EVID-PARSER-STAGING-GRAPH` | Quarantined missing-anchor: Parser NetworkX staging graph evidence | parser-ingestion | bounded-technical-proof | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove FalkorDB loading/runtime behavior.; ❌ Does not prove legal-answer correctness. |
| `EVID-REAL-ARTIFACT-RETRIEVAL-PROOF` | Quarantined missing-anchor: Real-artifact retrieval output ID proof | retrieval-embedding | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness. |
| `EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF` | Quarantined missing-anchor: Representative retrieval runtime benchmark proof | retrieval-embedding | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness. |
| `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` | Quarantined missing-anchor: Ontology architecture intake research evidence | architecture-governance | registry/process | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` | Quarantined missing-anchor: Retrieval output ID validator bounded proof | retrieval-embedding | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness. |
| `GATE-AKOMA-FRBR-NORMALIZATION` | Quarantined missing-anchor: Akoma/FRBR normalization proof gate | parser-ingestion | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-BFO-GOST-ALIGNMENT` | Quarantined missing-anchor: BFO/GOST alignment proof gate | architecture-governance | registry/process | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-EMBEDDING-SUPPLY-CHAIN` | Quarantined missing-anchor: Embedding model supply-chain integrity gate | security-safety | open-proof-gate | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not promote any embedding model to product default.; ❌ Does not allow managed embedding API fallback. |
| `GATE-G005` | Quarantined missing-anchor: Temporal same-date multi-edition conflict policy | temporal-model | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not validate temporal conflict resolution.; ❌ Missing-anchor quarantine cannot satisfy requirements, establish current architecture, or promote lifecycle. |
| `GATE-G008` | Quarantined missing-anchor: Product parser and retrieval readiness gate | parser-ingestion | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ No parser completeness claim.; ❌ No product retrieval quality claim. |
| `GATE-G011` | Quarantined missing-anchor: Local embedding quality proof | retrieval-embedding | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ No product retrieval quality claim.; ❌ No managed embedding API fallback claim. |
| `GATE-GENERATED-CYPHER-SAFETY` | Quarantined missing-anchor: Generated-Cypher safety and validation gate | generated-cypher | product/legal-runtime | critical | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove provider generation quality.; ❌ Does not prove production Legal KnowQL behavior. |
| `GATE-LEGAL-COLLISION-POLICY` | Quarantined missing-anchor: Legal collision policy proof gate | legal-evidence | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-LEGAL-NEXUS-ACCESS-CONTROL` | Quarantined missing-anchor: Legal Nexus access-control proof gate | security-safety | open-proof-gate | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not assert current product is insecure.; ❌ Does not prove access-control enforcement. |
| `GATE-LKIF-DEONTIC-BENCHMARK` | Quarantined missing-anchor: LKIF deontic benchmark proof gate | legal-evidence | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | Quarantined missing-anchor: Ontology GraphRAG integration proof gate | retrieval-embedding | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-PILOT-SCALE-READINESS` | Quarantined missing-anchor: Pilot-scale readiness proof gate | observability-operability | open-proof-gate | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-RUSLEGALCORE-SCOPE` | Quarantined missing-anchor: RusLegalCore scope proof gate | legal-evidence | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `M001-ARCHITECTURE-ONLY-GUARDRAIL` | Quarantined missing-anchor: M001 architecture-only guardrail | architecture-governance | registry/process | critical | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ No product ETL.; ❌ No production graph schema. |
| `QS-OBSERVABILITY-OPERABILITY-BASELINE` | Quarantined missing-anchor: Deterministic observability and auditability baseline | observability-operability | architecture-planning | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove runtime SLOs.; ❌ Does not prove production observability. |
| `REQ-TEMPORAL-STATUS-SEMANTICS` | Quarantined missing-anchor: Temporal status semantics remain explicit | temporal-model | product/legal-runtime | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove import runtime behavior.; ❌ Does not validate same-date conflict policy. |
| `RISK-OVERCLAIM-RUNTIME` | Quarantined missing-anchor: Runtime and legal overclaim risk | security-safety | architecture-planning | critical | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Risk item does not assert current product failure.; ❌ Missing-anchor quarantine cannot satisfy requirements, establish current architecture, or promote lifecycle. |
| `S05-OLD-PROJECT-PRIOR-ART` | Quarantined missing-anchor: Old_project artifacts remain prior art | parser-ingestion | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ No Old_project artifact accepted unchanged.; ❌ No parser completeness claim. |
| `S05-PARSER-ODT-BOUNDARY` | Quarantined missing-anchor: Real ODT parser evidence boundary | parser-ingestion | bounded-technical-proof | high | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ No final legal hierarchy extraction claim.; ❌ No parser completeness claim. |
| `S07-FIXED-PRD-CONSISTENCY` | Quarantined missing-anchor: S07 PRD consistency closure | architecture-governance | registry/process | low | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ Does not prove product behavior.; ❌ Missing-anchor quarantine cannot satisfy requirements, establish current architecture, or promote lifecycle. |
| `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED` | Quarantined missing-anchor: GigaEmbeddings challenger blocked by environment and safety gates | retrieval-embedding | bounded-technical-proof | medium | blocked | none | Blocked diagnostic until every claimed anchor is retargeted ... | ❌ No managed embedding API fallback claim.; ❌ No default promotion while blocked-environment. |

---

## unsafe-to-assert

| ID | Title | Layer | Claim Domain | Risk | Status | Non-Claims |
| --- | --- | --- | --- | --- | --- | --- |
| `ACP-AHF-0001` | Historical/superseded: ACP runtime adoption is blocked until fixture validation exists | architecture-governance | registry/process | high | superseded | ❌ Does not validate R035.; ❌ Does not validate R037. |
| `ACP-AP-0001` | Historical/superseded: Validate ACP minimal fixture chain before broader tooling | architecture-governance | registry/process | medium | superseded | ❌ Does not validate R035.; ❌ Does not validate R037. |
| `ACP-APR-0001` | Historical/superseded: Capture ACP minimal fixture validation intent | architecture-governance | registry/process | medium | superseded | ❌ Does not validate R035.; ❌ Does not validate R037. |
| `ACP-DC-0001` | Historical/superseded: Require fixture validation before ACP runtime adoption | architecture-governance | registry/process | medium | superseded | ❌ Does not validate R035.; ❌ Does not validate R037. |
| `ACP-PG-0001` | Historical/superseded: Minimal ACP fixture validation gate | architecture-governance | registry/process | medium | superseded | ❌ Does not validate R035.; ❌ Does not validate R037. |
| `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` | Historical/superseded: GraphRAG/FalkorDB mathematical analysis research input | retrieval-embedding | bounded-technical-proof | high | superseded | ❌ Does not prove product retrieval quality.; ❌ Does not prove FalkorDB production-scale behavior. |
| `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` | Historical/superseded: Habr Legal RAG iteration and scaling research input | retrieval-embedding | bounded-technical-proof | high | superseded | ❌ Does not prove product retrieval quality.; ❌ Does not prove parser completeness. |
| `GATE-G015` | Historical/superseded: FalkorDBLite to Docker migration runbook | graph-runtime | bounded-technical-proof | medium | superseded | ❌ No production-scale FalkorDB claim.; ❌ D7 quarantine does not validate current product, legal, runtime, parser, retrieval, or infrastructure claims. |
| `REQ-R017` | Historical/superseded: Assess FalkorDB text-to-cypher PyO3 route | generated-cypher | product/legal-runtime | high | superseded | ❌ No product Legal KnowQL behavior claim.; ❌ No legal-answer correctness claim. |
| `REQ-R028` | LLM output is not legal authority | security-safety | architecture-planning | critical | out-of-scope | ❌ No LLM legal authority claim.; ❌ No legal-answer correctness claim. |
| `S04-FALKORDB-RUNTIME-BOUNDED` | Historical/superseded: FalkorDB runtime mechanics smoke boundary | graph-runtime | bounded-technical-proof | medium | superseded | ❌ No production-scale FalkorDB claim.; ❌ No legal retrieval quality claim. |
| `S10-USER-BGE-M3-BASELINE` | Historical/superseded: USER-bge-m3 bounded local embedding baseline | retrieval-embedding | bounded-technical-proof | medium | superseded | ❌ No product retrieval quality claim.; ❌ No managed embedding API fallback claim. |

---

*Claims ledger generated from `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_graph_report.json`. This is a derived, non-authoritative planning artifact. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
