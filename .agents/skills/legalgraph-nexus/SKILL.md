---
name: legalgraph-nexus
description: Routes LegalGraph Nexus architecture, FalkorDB Legal Graph, Legal Nexus, Legal KnowQL, Russian legal evidence, citation-safe retrieval, and M001 scope questions to the right project-local evidence workflow while preserving deterministic-first, temporal-first, and LLM non-authoritative guardrails.
---

<objective>
Use this compact project-local router when work touches LegalGraph Nexus architecture, FalkorDB Legal Graph terminology, Legal Nexus, Legal KnowQL, EvidenceSpan, SourceBlock, citation-safe retrieval, Russian legal source evidence, or architecture claims for M001.
</objective>

<essential_terms>
- **LegalGraph Nexus** is the product architecture being reviewed in M001.
- **FalkorDB Legal Graph** is the graph substrate concept; do not transfer Neo4j behavior or GraphBLAS control-surface assumptions without FalkorDB evidence.
- **Legal Nexus** and **Legal KnowQL** are architecture concepts only in M001, not product implementations.
- **EvidenceSpan** and **SourceBlock** are source-grounding concepts for citation-safe retrieval and must remain tied to real source evidence.
- **Deterministic-first** and **temporal-first** mean algorithmic evidence and validity-time handling outrank LLM composition.
- **LLM non-authoritative** means an LLM may summarize or draft only from verified evidence; it is never legal authority.
</essential_terms>

<scope_boundaries>
M001 is architecture-only. Keep product ETL/import, a production graph schema, Legal Nexus runtime, Legal KnowQL parser, hybrid retrieval, ODT parser behavior, and any legal-answering product flow outside this slice. Treat `Old_project/` as prior art only, not trusted runtime or legal evidence. Prefer GitNexus-backed source evidence, PRD text, smoke-check output, and tracked GSD artifacts over assumptions.
</scope_boundaries>

<routing>
- For FalkorDB capability, GraphBLAS positioning, Cypher, UDF, index, FalkorDBLite, driver, source-code, smoke-check, vector-storage, or local embedding runtime questions: load `falkordb-legalgraph` after inspecting local project context.
- For Russian legal structure, citation units, EvidenceSpan, SourceBlock, ODT/Garant source evidence, `Old_project/` prior art, legal authority, parser/source evidence, or citation-safe retrieval questions: load `russian-legal-evidence` after inspecting local project context.
- For broad architecture-review questions that cross FalkorDB runtime, ODT parser evidence, `Old_project` reuse, local embeddings, and citation-safe retrieval: use this router to preserve M001 boundaries, then load both focused skills and split the answer into graph runtime, parser/source evidence, Old_project reuse, embedding runtime/storage, citation-safe retrieval, legal-quality, and product-implementation claim rows.
</routing>

<workflow>
1. Inspect local task context, PRD/GSD artifacts, and relevant code or GitNexus evidence before making a claim.
2. Route to the focused skill when the question needs detailed FalkorDB or Russian legal evidence rules.
3. Classify each material claim as verified source evidence, bounded evidence, hypothesis pending verification, or out of M001 scope.
4. State uncertainty explicitly when FalkorDB behavior, ODT behavior, or legacy prior-art relevance has not been verified.
5. Keep recommendations architecture-level unless a later milestone explicitly authorizes implementation.
</workflow>

<s06_evidence_refresh>
Use S06-refresh evidence anchors when routing refreshed M001 claims:
- FalkorDB runtime/capability anchor: `.gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json`.
- ODT parser anchor: `.gsd/milestones/M001/slices/S05/S05-ODT-PARSER-FINDINGS.md` with bounded `odfdo`, `odfpy`, and raw `content.xml` evidence.
- Local embedding evaluation anchor: `.gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json` for `deepvk/USER-bge-m3`, `1024`, and `ai-sage/Giga-Embeddings-instruct` comparisons.
- Embedding runtime proof anchor: `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` for `deepvk/USER-bge-m3` confirmed-runtime, `1024`-dimensional FalkorDB proof, `GigaEmbeddings` / `ai-sage/Giga-Embeddings-instruct`, and `blocked-environment` diagnostics.
- Exercise/handoff anchor: `.gsd/milestones/M001/slices/S06/S06-SKILL-EVIDENCE-UPDATE.md` classifies the cross-domain question “Can LegalGraph use FalkorDB vector retrieval over Garant ODT evidence with local embeddings?” without copying raw legal text, embedding arrays, credentials, or managed API secret names.
Every refreshed claim should expose an owner, resolution, and verification status instead of upgrading bounded evidence into product proof.
</s06_evidence_refresh>

<success_criteria>
A correct use of this router names the relevant focused skill, preserves M001 architecture-only scope, keeps LLM output non-authoritative, grounds legal claims in EvidenceSpan/SourceBlock-style evidence, and avoids unverified FalkorDB, GraphBLAS, ODT, or Old_project overclaims.
</success_criteria>
