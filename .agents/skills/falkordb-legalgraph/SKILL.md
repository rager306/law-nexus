---
name: falkordb-legalgraph
description: Guides LegalGraph Nexus agents through FalkorDB architecture and capability questions by routing claims to GitNexus/source/docs/smoke evidence workflows without overclaiming unverified GraphBLAS, OpenCypher, full-text, vector, or UDF behavior.
---

<objective>
Use this focused skill when a task asks whether FalkorDB, FalkorDB Legal Graph, GraphBLAS-backed functionality, OpenCypher, full-text search, vector search, UDF behavior, FalkorDBLite, or driver/runtime capabilities can support LegalGraph Nexus architecture. The output must be evidence-classified and LLM non-authoritative.
</objective>

<scope>
This skill answers M001 architecture-only and capability questions only. Product ETL/import, Legal KnowQL, Legal Nexus runtime, product graph schemas, smoke harnesses, and product pipeline code remain outside this skill's implementation scope. Treat runtime suitability as pending until S04 smoke evidence exists, and treat source-level claims as pending until S03 GitNexus/source evidence exists.
</scope>

<evidence_protocol>
Read `references/falkordb-evidence-protocol.md` before classifying material claims. Valid claim classes are `confirmed`, `docs-backed/source-pending`, `smoke-needed`, `contradicted`, and `out-of-scope`. Current FalkorDB documentation claims are not `confirmed` by themselves; they are `docs-backed/source-pending` or `smoke-needed` until GitNexus/source and runtime smoke evidence exist.
</evidence_protocol>

<routing>
- For broad LegalGraph Nexus architecture questions, follow `workflows/answer-architecture-question.md`.
- For one FalkorDB capability claim, follow `workflows/check-capability-claim.md`.
- If a question is about Russian legal citation units, EvidenceSpan, SourceBlock, ODT/Garant source evidence, or legal authority rather than FalkorDB capability, return to `legalgraph-nexus` and route to `russian-legal-evidence` when available.
</routing>

<required_guardrails>
- Preserve prior architecture decisions: FalkorDB GraphBLAS-backed functionality/internal architecture is valid wording, but a direct LegalGraph GraphBLAS API or control surface is unconfirmed until source/runtime proof.
- Do not transfer Neo4j capabilities, Cypher extensions, procedures, Graph Data Science assumptions, full-text semantics, vector semantics, or UDF behavior to FalkorDB without FalkorDB evidence.
- Scope GitNexus dynamically: call `gitnexus_list_repos`, choose matching vendor/reference repos discovered at runtime, and avoid hardcoding future repo names.
- Use `/root/vendor-source/` as the expected local checkout location when GitNexus reference indexes are absent or insufficient.
- Assign every insufficient claim to a downstream owner such as S03 source indexing or S04 runtime smoke checks.
</required_guardrails>

<failure_handling>
If GitNexus errors, times out, or returns noisy/malformed results, fall back to `/root/vendor-source/` source paths and mark affected claims `docs-backed/source-pending` or `smoke-needed`; never upgrade them to `confirmed`. If FalkorDB docs snippets are unavailable, ambiguous, or malformed, record the evidence gap and keep the claim source-pending or smoke-needed.
</failure_handling>

<s06_evidence_refresh>
Route refreshed FalkorDB and embedding claims through these bounded anchors:
- `.gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json` for runtime smoke evidence.
- `.gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json` for local embedding evaluation involving `deepvk/USER-bge-m3`, `1024` dimensions, and `ai-sage/Giga-Embeddings-instruct`.
- `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` for `GigaEmbeddings` runtime import/probe status and `blocked-environment` diagnostics.
Keep each claim in owner / resolution / verification form. These anchors do not prove production legal retrieval quality, a direct GraphBLAS control surface, or product hybrid retrieval readiness.
</s06_evidence_refresh>

<success_criteria>
A correct answer decomposes vague claims into verifiable subclaims, cites the evidence route used, produces a concise claim table under the five claim classes, avoids Neo4j carryover, preserves bounded GraphBLAS wording, and names downstream owners for source/runtime gaps.
</success_criteria>
