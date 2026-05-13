# Graph Agent Knowledge Bases / FalkorDB Math Analysis — Architecture Assessment

## Status

- **Source document:** `prd/research/graph_agent_knowledge_bases_falkordb_math_analysis.md`
- **Assessment status:** bounded architecture research input
- **Non-authoritative:** yes
- **Prepared for:** M011/S01

This assessment converts the imported research document into safe LegalGraph Nexus planning guidance. It does **not** validate FalkorDB production behavior, GraphRAG-SDK behavior, parser completeness, retrieval quality, generated-Cypher safety, legal-answer correctness, benchmark numbers, cost savings, latency claims, or LLM legal authority.

## Executive Judgment

The document is strategically aligned with LegalGraph Nexus: it argues for graph-first, deterministic, source/provenance-preserving retrieval before LLM synthesis. That direction matches the current project architecture and open proof gates.

The document should **not** be treated as product proof. It contains strong claims about FalkorDB, GraphRAG-SDK, GraphBLAS, algorithms, cost reduction, latency, and accuracy. Those claims remain research hypotheses unless verified by project-specific source/runtime/golden-test evidence.

## Applicable Now as Architecture Principles

| Idea | Applicability | Evidence posture | Project mapping |
| --- | --- | --- | --- |
| LLM as non-authoritative natural-language interface over deterministic graph evidence | High | Already aligned with project guardrails | `REQ-R028`, `RISK-OVERCLAIM-RUNTIME`, `GATE-GENERATED-CYPHER-SAFETY` |
| Graph pre-filtering before LLM context assembly | High | Architecture principle; product retrieval not proven | `GATE-G008`, `GATE-G011`, `EVID-PARSER-GOLDEN-TEST-PROOF` |
| Temporal-first legal graph / point-in-time retrieval | High | Existing architecture direction; conflict policy unproven | `GATE-G005`, `DATA-TEMPORAL-PROPERTY-BUNDLE`, `REQ-TEMPORAL-STATUS-SEMANTICS` |
| Source/evidence provenance as first-class graph structure | High | Existing parser/evidence direction; product graph not loaded | `DATA-LEGAL-EVIDENCE-CORE`, `EVID-PARSER-CONSULTANT-HIERARCHY-PROOF` |
| Local/open-weight embedding constraints | High | Must follow existing human decision; no managed fallback | `GATE-G011`, `GATE-EMBEDDING-SUPPLY-CHAIN`, `S10-USER-BGE-M3-BASELINE` |

## Proof-Gated Candidates

These ideas are promising but require project-specific proof before adoption.

| Candidate | Suggested proof path | Evidence required before adoption |
| --- | --- | --- |
| BFS / bounded neighborhood expansion for evidence retrieval | Offline deterministic retrieval proof over M006/M009 artifacts | Golden-case comparison, source-anchor preservation, no-answer behavior |
| Shortest paths (`algo.SPpaths`, `algo.SSpaths`) for amendment/provenance chains | FalkorDB runtime algorithm smoke on legal-shaped fixture after offline prototype | Output shape, redacted diagnostics, bounded path semantics |
| WCC for graph hygiene diagnostics | Offline NetworkX or FalkorDB fixture proof | Detection of disconnected acts/amendments/source islands |
| PageRank / personalized PageRank for ranking candidate legal nodes | Retrieval benchmark over golden cases | Recall/precision or case-level pass/fail against expected evidence |
| Betweenness centrality for bridge-node exploration | Analysis-only proof; not answer authority | Demonstrate explanatory value without changing legal answer semantics |
| Label Propagation / CDLP for exploratory clusters | Optional diagnostics proof | Stability/interpretability checks; no legal classification authority |
| k-core / deterministic topology compression | Offline NetworkX proof first | Compare against golden cases; verify determinism and bounded output size |
| Heat diffusion / Laplacian scoring | Research spike only | Offline numerical prototype and comparison against simpler BFS/PageRank baselines |
| GraphRAG-SDK / MultiPathRetrieval | Compatibility spike | Actual API/version proof, provenance preservation, ability to avoid managed embeddings and uncontrolled LLM extraction |
| UDF/FLEX utilities | Capability/security spike | Runtime proof, security review, deterministic behavior, operational fallback |

## Deferred or Not Adopted Now

| Idea | Reason for deferral |
| --- | --- |
| GN-CDEs / neural differential graph dynamics | Requires temporal graph snapshots, training data, ML infrastructure, and explainability beyond current product gates. |
| TeaRAG / IP-DPO | Requires stable retrieval workload and answer-quality evaluation first. Premature optimization now. |
| Helium-style query-plan/KV-cache optimization | Requires production traffic patterns and repeated query workload. |
| Benchmark claims (60% cost reduction, 84% accuracy, microsecond/3.6s latency, $0.00065/query) | Not project-specific; must not be repeated as LegalGraph Nexus claims without reproducible local benchmark evidence. |
| “Absolute mathematical traceability” / “only production-grade choice” language | Overclaim risk; use bounded provenance and source-anchor language instead. |

## FalkorDB Claim Classification

| Claim family | Classification | Notes |
| --- | --- | --- |
| FalkorDB is GraphBLAS-backed internally | bounded / source-backed direction | Acceptable wording: “GraphBLAS-backed functionality/internal architecture.” Do not claim a direct LegalGraph GraphBLAS API/control surface. |
| FalkorDB algorithms PageRank, WCC, BFS, Betweenness, Label Propagation, SPpaths, SSpaths, MSF exist | bounded synthetic output-shape proof | Existing project notes confirm synthetic fixtures for output shape only; production suitability and legal retrieval quality are unproven. |
| GraphRAG-SDK pipeline and MultiPathRetrieval behavior | source-pending / spike-needed | Verify actual SDK/version/API before architecture dependency. |
| UDF/FLEX suitability for retrieval math | smoke-needed | Do not place on critical path before runtime/security proof. |
| Vector/full-text/hybrid retrieval quality | proof-gated | Existing mechanics do not prove product retrieval quality. |
| Production-scale FalkorDB performance | open | Tracked by `GATE-G015`; document benchmarks are not project evidence. |

## Recommended Next Proof Milestones

### Candidate M012 — Offline Graph Retrieval Strategy Proof

Use existing tracked artifacts only:

- `prd/parser/consultant_hierarchy_records.jsonl`
- `prd/parser/parser_staging_graph.json`
- M008 golden cases
- source/evidence anchors

Evaluate deterministic retrieval strategies before runtime adoption:

1. bounded BFS / neighborhood expansion;
2. shortest-path provenance chains;
3. WCC diagnostics;
4. optional PageRank / personalized PageRank;
5. optional k-core compression via NetworkX.

Success should be case-level and bounded: selected evidence nodes match expected golden-case anchors, no-answer remains no-answer, candidate-only remains non-authoritative, and no legal answer is generated.

### Candidate M013 — FalkorDB Legal-Shaped Runtime Algorithm Smoke

After offline proof, load a bounded legal-shaped fixture into FalkorDB and verify output shape for:

- BFS;
- PageRank;
- WCC;
- shortest paths;
- optionally Betweenness/CDLP/MSF.

This should remain a runtime mechanics proof, not retrieval-quality or production-scale proof.

### Candidate M014 — Temporal Conflict Policy Proof

Use Consultant/Garant source fixtures to prove:

- same-date conflict handling;
- amendment/supersession chain behavior;
- `AT "YYYY-MM-DD"` point-in-time query semantics;
- deterministic no-answer and superseded-answer diagnostics.

## Architecture Decision Recommendations

1. Treat the imported research document as **bounded research evidence**, not source/runtime/product proof.
2. Use its strongest near-term contribution to guide offline deterministic retrieval proof, not GraphRAG-SDK adoption.
3. Keep product readiness gates open until project-specific evidence exists.
4. Prefer simple deterministic graph algorithms first (BFS, shortest paths, WCC, PageRank) before advanced heat diffusion, GN-CDE, or LLM optimization methods.
5. Preserve local/open-weight embedding policy; do not introduce managed embedding APIs through GraphRAG-SDK or other external pipelines.

## Non-Claims

This assessment does not prove:

- FalkorDB production-scale behavior;
- GraphRAG-SDK compatibility with LegalGraph Nexus;
- product retrieval quality;
- parser completeness;
- legal-answer correctness;
- generated-Cypher safety;
- Legal Nexus API/access-control behavior;
- temporal conflict policy;
- benchmark/cost/latency claims;
- LLM legal authority.
