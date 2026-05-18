# Claims Ledger

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

| ID | Trigger | Current Safe Bucket | Required Gate | Minimum Proof | Status | Missing Requirements | Remediation Class |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` | FRBR | compatibility/reference projection only | GATE-AKOMA-FRBR-NORMALIZATION | static-check | hypothesis | proof_level<static-check | add-proof-gate |
| `DATA-LEGAL-SOURCE-HIERARCHY` | legal source hierarchy, source hierarchy, supersession | proof-gated legal-priority candidate | GATE-LEGAL-COLLISION-POLICY | static-check | hypothesis | proof_level<static-check | add-proof-gate |
| `DATA-LKIF-DEONTIC-MAPPING` | LKIF, deontic mapping | proof-gated candidate | GATE-LKIF-DEONTIC-BENCHMARK | unit-test | hypothesis | proof_level<unit-test | add-proof-gate |
| `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` | RusLegalCore | proof-gated domain-scope candidate | GATE-RUSLEGALCORE-SCOPE | static-check | hypothesis | proof_level<static-check | add-proof-gate |
| `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` | GraphRAG | proof-gated integration candidate | GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | integration-test | bounded-evidence | proof_level<integration-test | add-proof-gate |
| `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` | Akoma Ntoso, FRBR | compatibility/reference projection only | GATE-AKOMA-FRBR-NORMALIZATION | static-check | bounded-evidence | proof_level<static-check | add-proof-gate |
| `GATE-AKOMA-FRBR-NORMALIZATION` | Akoma Ntoso, FRBR | compatibility/reference projection only | GATE-AKOMA-FRBR-NORMALIZATION | static-check | proposed | proof_level<static-check | add-proof-gate |
| `GATE-BFO-GOST-ALIGNMENT` | BFO, GOST, OWL, Common Logic | deferred formal-alignment review | GATE-BFO-GOST-ALIGNMENT | static-check | proposed | proof_level<static-check | add-proof-gate |
| `GATE-LEGAL-COLLISION-POLICY` | legal collision policy, collision policy, lex superior, lex specialis, lex posterior, supersession | proof-gated legal-priority candidate | GATE-LEGAL-COLLISION-POLICY | static-check | proposed | proof_level<static-check | add-proof-gate |
| `GATE-LKIF-DEONTIC-BENCHMARK` | LKIF | proof-gated candidate | GATE-LKIF-DEONTIC-BENCHMARK | unit-test | proposed | proof_level<unit-test | add-proof-gate |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | Ontology GraphRAG | proof-gated integration candidate | GATE-ONTOLOGY-GRAPHRAG-INTEGRATION | integration-test | proposed | proof_level<integration-test | add-proof-gate |
| `GATE-PILOT-SCALE-READINESS` | pilot-scale, 1,000-document | deferred readiness proof | GATE-PILOT-SCALE-READINESS | integration-test | proposed | proof_level<integration-test | add-proof-gate |
| `GATE-RUSLEGALCORE-SCOPE` | RusLegalCore | proof-gated domain-scope candidate | GATE-RUSLEGALCORE-SCOPE | static-check | proposed | proof_level<static-check | add-proof-gate |

---

## safe-to-say

| ID | Title | Layer | Claim Domain | Risk | Non-Claims |
| --- | --- | --- | --- | --- | --- |
| `ASSUMP-PRD-SOURCE-TRUTH` | PRD and GSD artifacts remain source of truth | architecture-governance | registry/process | high | ❌ Does not make generated artifacts authoritative. |
| `CHECK-ARCHITECTURE-EXTRACTOR` | Deterministic architecture extractor check | workflow-governance | registry/process | high | ❌ Extractor check is not product runtime proof. |
| `COMP-LEGAL-NEXUS-ORCHESTRATOR` | Legal Nexus orchestrator component boundary | api-product | product/legal-runtime | high | ❌ Does not implement Legal Nexus runtime behavior.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-LEGAL-EVIDENCE-CORE` | Core legal evidence entities | legal-evidence | product/legal-runtime | high | ❌ Does not assert final legal graph schema completeness.; ❌ Does not prove legal-answer correctness. |
| `DATA-TEMPORAL-PROPERTY-BUNDLE` | Temporal property bundle | temporal-model | product/legal-runtime | high | ❌ Does not specify temporal storage implementation.; ❌ Does not validate temporal conflict resolution. |
| `DEC-D031` | Use docs-as-code architecture registry | architecture-governance | registry/process | high | ❌ JSONL and GraphML are not source-of-truth replacements. |
| `DEC-D032` | Add architecture verification router skill in S05 | workflow-governance | registry/process | medium | ❌ The skill is guidance, not a source of truth. |
| `QS-OBSERVABILITY-OPERABILITY-BASELINE` | Deterministic observability and auditability baseline | observability-operability | architecture-planning | medium | ❌ Does not prove runtime SLOs.; ❌ Does not prove production observability. |
| `REQ-R001` | Architecture review finding classification | architecture-governance | registry/process | medium | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R009` | Architecture findings require owner and verification criteria | workflow-governance | registry/process | high | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R010` | Machine-readable architecture findings path | architecture-governance | registry/process | medium | ❌ No legal-answer correctness claim.; ❌ No product Legal KnowQL behavior claim. |
| `REQ-R017` | Assess FalkorDB text-to-cypher PyO3 route | generated-cypher | product/legal-runtime | high | ❌ No product Legal KnowQL behavior claim.; ❌ No legal-answer correctness claim. |
| `REQ-R022` | Proof artifacts remain redacted and categorical | security-safety | architecture-planning | critical | ❌ No raw provider body persistence claim.; ❌ No credential, prompt, raw legal text, or raw row emission claim. |
| `REQ-R029` | Executable architecture verification workflow | architecture-governance | registry/process | high | ❌ Does not itself prove product runtime behavior. |
| `REQ-R034` | Retrieval output evidence identifiers fail closed | retrieval-embedding | bounded-technical-proof | high | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness. |
| `REQ-TEMPORAL-STATUS-SEMANTICS` | Temporal status semantics remain explicit | temporal-model | product/legal-runtime | high | ❌ Does not prove import runtime behavior.; ❌ Does not validate same-date conflict policy. |
| `RISK-OVERCLAIM-RUNTIME` | Runtime and legal overclaim risk | security-safety | architecture-planning | critical | ❌ Risk item does not assert current product failure. |

---

## bounded

| ID | Title | Layer | Claim Domain | Risk | Proof Level | Non-Claims |
| --- | --- | --- | --- | --- | --- | --- |
| `EVID-LOCAL-RETRIEVAL-QUALITY-BENCHMARK-PROOF` | Local retrieval quality benchmark proof | retrieval-embedding | bounded-technical-proof | high | unit-test | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness.; ❌ Does not prove parser completeness.; ❌ Does not prove production FalkorDB runtime behavior.; ❌ Does not prove production graph schema readiness.; ❌ Does not allow managed embedding API fallback.; ❌ Does not promote GigaEmbeddings.; ❌ Does not close GATE-G011.; ❌ Does not close GATE-G008.; ❌ Does not make LLM output legal authority.; ❌ Does not make proof-local fixture metrics production metrics. |
| `EVID-OFFLINE-CITATION-RETRIEVAL-PROOF` | Offline citation-safe retrieval proof | retrieval-embedding | bounded-technical-proof | high | unit-test | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness.; ❌ Does not prove parser completeness.; ❌ Does not prove production FalkorDB runtime behavior.; ❌ Does not prove production graph schema readiness.; ❌ Does not prove local embedding quality.; ❌ Does not close GATE-G008.; ❌ Does not close GATE-G011.; ❌ Does not make LLM output legal authority.; ❌ Does not make proof-local IDs production IDs. |
| `EVID-PARSER-CONSULTANT-CANDIDATES` | Consultant relation-candidate evidence | parser-ingestion | bounded-technical-proof | medium | static-check | ❌ Does not prove Consultant relation correctness.; ❌ Does not prove parser completeness. |
| `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` | Consultant full-act hierarchy parser proof | parser-ingestion | bounded-technical-proof | medium | real-document-proof | ❌ Does not prove multi-document Consultant expansion.; ❌ Does not prove Garant ODT parser regression.; ❌ Does not prove parser completeness.; ❌ Does not prove product ETL readiness.; ❌ Does not prove FalkorDB loading/runtime behavior. |
| `EVID-PARSER-GOLDEN-TEST-PROOF` | Bounded parser/retrieval golden-test proof | parser-ingestion | bounded-technical-proof | medium | unit-test | ❌ Does not prove parser completeness.; ❌ Does not prove product retrieval quality.; ❌ Does not prove citation-safe retrieval readiness.; ❌ Does not prove legal-answer correctness.; ❌ Does not prove FalkorDB loading/runtime behavior. |
| `EVID-PARSER-ODT-SMOKE` | Bounded ODT smoke-record evidence | parser-ingestion | bounded-technical-proof | high | real-document-proof | ❌ No final legal hierarchy extraction claim.; ❌ No parser completeness claim. |
| `EVID-PARSER-RECORD-CONTRACT` | Parser record contract evidence | parser-ingestion | bounded-technical-proof | medium | static-check | ❌ Does not prove product ETL readiness.; ❌ Does not prove parser completeness. |
| `EVID-PARSER-SOURCE-FIXTURE-INVENTORY` | Parser source fixture inventory evidence | parser-ingestion | bounded-technical-proof | medium | static-check | ❌ Does not prove parser completeness.; ❌ Does not prove legal correctness. |
| `EVID-PARSER-STAGING-GRAPH` | Parser NetworkX staging graph evidence | parser-ingestion | bounded-technical-proof | medium | static-check | ❌ Does not prove FalkorDB loading/runtime behavior.; ❌ Does not prove legal-answer correctness. |
| `EVID-REAL-ARTIFACT-RETRIEVAL-PROOF` | Real-artifact retrieval output ID proof | retrieval-embedding | bounded-technical-proof | high | unit-test | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness.; ❌ Does not prove parser completeness.; ❌ Does not prove production FalkorDB runtime behavior.; ❌ Does not prove production graph schema readiness.; ❌ Does not prove local embedding quality.; ❌ Does not close GATE-G008.; ❌ Does not close GATE-G011.; ❌ Does not make LLM output legal authority.; ❌ Does not make proof-local IDs production IDs. |
| `EVID-REPRESENTATIVE-RETRIEVAL-RUNTIME-BENCHMARK-PROOF` | Representative retrieval runtime benchmark proof | retrieval-embedding | bounded-technical-proof | high | runtime-smoke | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness.; ❌ Does not prove parser completeness.; ❌ Does not prove production ranker quality.; ❌ Does not prove production FalkorDB runtime behavior.; ❌ Does not prove production graph schema readiness.; ❌ Does not allow managed embedding API fallback.; ❌ Does not authorize GigaChat or GigaEmbeddings runtime use.; ❌ Does not make proof-local IDs production IDs.; ❌ Does not persist raw legal text, raw query text, raw prompts, vectors, provider payloads, managed-API evidence, raw FalkorDB rows, secrets, or generated legal advice.; ❌ Does not close GATE-G011. |
| `EVID-RESEARCH-GRAPHRAG-MATH-ANALYSIS` | GraphRAG/FalkorDB mathematical analysis research input | retrieval-embedding | bounded-technical-proof | high | source-anchor | ❌ Does not prove product retrieval quality.; ❌ Does not prove FalkorDB production-scale behavior.; ❌ Does not prove GraphRAG-SDK compatibility.; ❌ Does not validate benchmark, cost, or latency claims.; ❌ Does not prove legal-answer correctness. |
| `EVID-RESEARCH-HABR-LEGAL-RAG-ITERATION-SCALING` | Habr Legal RAG iteration and scaling research input | retrieval-embedding | bounded-technical-proof | high | source-anchor | ❌ Does not prove product retrieval quality.; ❌ Does not prove parser completeness.; ❌ Does not prove legal-answer correctness.; ❌ Does not prove FalkorDB runtime/vector/full-text/rerank behavior.; ❌ Does not authorize generated Cypher execution. |
| `EVID-RESEARCH-ONTOLOGY-AKOMA-LKIF-BFO` | Ontology architecture intake research evidence | architecture-governance | registry/process | high | source-anchor | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior.; ❌ Does not prove parser completeness.; ❌ Does not prove ontology benchmark quality.; ❌ Does not prove pilot-scale readiness.; ❌ Does not prove FalkorDB graph-vector/runtime capability.; ❌ Does not make LLM output legal authority.; ❌ Does not prove GOST/BFO source correctness.; ❌ Does not prove LKIF/deontic extraction correctness.; ❌ Does not prove ontology GraphRAG retrieval quality.; ❌ Does not prove RusLawOD corpus priority. |
| `EVID-RETRIEVAL-OUTPUT-ID-VALIDATOR-PROOF` | Retrieval output ID validator bounded proof | retrieval-embedding | bounded-technical-proof | high | unit-test | ❌ Does not prove product retrieval quality.; ❌ Does not prove legal-answer correctness.; ❌ Does not prove parser completeness.; ❌ Does not prove production FalkorDB runtime behavior.; ❌ Does not prove raw legal text evidence quality.; ❌ Does not make LLM output legal authority.; ❌ Does not promote D045 research into validated product behavior.; ❌ Does not make fixture IDs production IDs. |
| `S04-FALKORDB-RUNTIME-BOUNDED` | FalkorDB runtime mechanics smoke boundary | graph-runtime | bounded-technical-proof | medium | runtime-smoke | ❌ No production-scale FalkorDB claim.; ❌ No legal retrieval quality claim.; ❌ No direct LegalGraph GraphBLAS API/control surface claim. |
| `S05-OLD-PROJECT-PRIOR-ART` | Old_project artifacts remain prior art | parser-ingestion | bounded-technical-proof | high | source-anchor | ❌ No Old_project artifact accepted unchanged.; ❌ No parser completeness claim. |
| `S05-PARSER-ODT-BOUNDARY` | Real ODT parser evidence boundary | parser-ingestion | bounded-technical-proof | high | real-document-proof | ❌ No final legal hierarchy extraction claim.; ❌ No parser completeness claim.; ❌ No production SourceBlock/EvidenceSpan creation claim. |
| `S07-FIXED-PRD-CONSISTENCY` | S07 PRD consistency closure | architecture-governance | registry/process | low | source-anchor | ❌ Does not prove product behavior. |
| `S10-USER-BGE-M3-BASELINE` | USER-bge-m3 bounded local embedding baseline | retrieval-embedding | bounded-technical-proof | medium | runtime-smoke | ❌ No product retrieval quality claim.; ❌ No managed embedding API fallback claim.; ❌ No raw embedding leakage claim beyond verifier scope. |

---

## blocked/open

| ID | Title | Layer | Claim Domain | Risk | Status | Proof Level | Verification | Non-Claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `GATE-EMBEDDING-SUPPLY-CHAIN` | Embedding model supply-chain integrity gate | security-safety | open-proof-gate | high | active | none | Future embedding proof records model source, checksum or rev... | ❌ Does not promote any embedding model to product default.; ❌ Does not allow managed embedding API fallback. |
| `GATE-G005` | Temporal same-date multi-edition conflict policy | temporal-model | product/legal-runtime | high | active | none | A future proof slice defines and verifies same-date/multi-ed... | ❌ Does not validate temporal conflict resolution. |
| `GATE-G008` | Product parser and retrieval readiness gate | parser-ingestion | bounded-technical-proof | high | active | none | Future product proof demonstrates parser completeness bounda... | ❌ No parser completeness claim.; ❌ No product retrieval quality claim. |
| `GATE-G011` | Local embedding quality proof | retrieval-embedding | bounded-technical-proof | high | active | none | Retrieval quality benchmark passes under local/open-weight e... | ❌ No product retrieval quality claim.; ❌ No managed embedding API fallback claim. |
| `GATE-G015` | FalkorDBLite to Docker migration runbook | graph-runtime | bounded-technical-proof | medium | active | none | Migration runbook is executed against bounded fixtures and r... | ❌ No production-scale FalkorDB claim. |
| `GATE-GENERATED-CYPHER-SAFETY` | Generated-Cypher safety and validation gate | generated-cypher | product/legal-runtime | critical | active | none | A future product proof demonstrates validator acceptance/rej... | ❌ Does not prove provider generation quality.; ❌ Does not prove production Legal KnowQL behavior. |
| `GATE-LEGAL-NEXUS-ACCESS-CONTROL` | Legal Nexus access-control proof gate | security-safety | open-proof-gate | high | active | none | Future security proof defines caller boundaries, authorizati... | ❌ Does not assert current product is insecure.; ❌ Does not prove access-control enforcement. |
| `S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED` | GigaEmbeddings challenger blocked by environment and safety gates | retrieval-embedding | bounded-technical-proof | medium | blocked | none | Challenger proof records gate approvals, runtime status, vec... | ❌ No managed embedding API fallback claim.; ❌ No default promotion while blocked-environment. |

---

## unsafe-to-assert

| ID | Title | Layer | Claim Domain | Risk | Status | Non-Claims |
| --- | --- | --- | --- | --- | --- | --- |
| `DATA-LEGAL-DOCUMENT-IDENTITY-FRBR` | FRBR-like legal document identity candidate | temporal-model | product/legal-runtime | high | hypothesis | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-LEGAL-SOURCE-HIERARCHY` | Legal source hierarchy candidate | legal-evidence | product/legal-runtime | high | hypothesis | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-LKIF-DEONTIC-MAPPING` | LKIF-inspired deontic mapping candidate | legal-evidence | product/legal-runtime | high | hypothesis | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `DATA-RUSLEGALCORE-DOMAIN-ONTOLOGY` | RusLegalCore domain ontology candidate | legal-evidence | product/legal-runtime | high | hypothesis | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-AKOMA-FRBR-NORMALIZATION` | Akoma/FRBR normalization proof gate | parser-ingestion | bounded-technical-proof | high | proposed | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-BFO-GOST-ALIGNMENT` | BFO/GOST alignment proof gate | architecture-governance | registry/process | medium | proposed | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-LEGAL-COLLISION-POLICY` | Legal collision policy proof gate | legal-evidence | product/legal-runtime | high | proposed | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-LKIF-DEONTIC-BENCHMARK` | LKIF deontic benchmark proof gate | legal-evidence | product/legal-runtime | high | proposed | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | Ontology GraphRAG integration proof gate | retrieval-embedding | bounded-technical-proof | high | proposed | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-PILOT-SCALE-READINESS` | Pilot-scale readiness proof gate | observability-operability | open-proof-gate | high | proposed | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `GATE-RUSLEGALCORE-SCOPE` | RusLegalCore scope proof gate | legal-evidence | product/legal-runtime | high | proposed | ❌ Does not prove legal-answer correctness.; ❌ Does not prove product Legal KnowQL behavior. |
| `M001-ARCHITECTURE-ONLY-GUARDRAIL` | M001 architecture-only guardrail | architecture-governance | registry/process | critical | out-of-scope | ❌ No product ETL.; ❌ No production graph schema. |
| `REQ-R028` | LLM output is not legal authority | security-safety | architecture-planning | critical | out-of-scope | ❌ No LLM legal authority claim.; ❌ No legal-answer correctness claim. |

---

*Claims ledger generated from `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_graph_report.json`. This is a derived, non-authoritative planning artifact. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.*
