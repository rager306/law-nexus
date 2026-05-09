---
name: falkordb-legalgraph
description: Guides LegalGraph Nexus agents through FalkorDB architecture and capability questions by routing claims to GitNexus/source/docs/smoke evidence workflows without overclaiming unverified GraphBLAS, OpenCypher, full-text, vector, or UDF behavior.
---

<objective>
Use this focused skill when a task asks whether FalkorDB, FalkorDB Legal Graph, GraphBLAS-backed functionality, OpenCypher, full-text search, vector search, UDF behavior, FalkorDBLite, or driver/runtime capabilities can support LegalGraph Nexus architecture. The output must be evidence-classified and LLM non-authoritative.
</objective>

<scope>
This skill answers M001 architecture-only and capability questions only. Product ETL/import, Legal KnowQL, Legal Nexus runtime, product graph schemas, smoke harnesses, and product pipeline code remain outside this skill's implementation scope. S04 now confirms bounded FalkorDB runtime mechanics on this host; product suitability, legal retrieval quality, deployment readiness, and source-level API/control-surface claims remain bounded or pending unless the cited artifact directly proves them.
</scope>

<evidence_protocol>
Read `references/falkordb-evidence-protocol.md` before classifying material claims. Valid claim classes are `confirmed`, `docs-backed/source-pending`, `smoke-needed`, `contradicted`, and `out-of-scope`. Current FalkorDB documentation claims are not `confirmed` by themselves. Runtime mechanics that appear in `.gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json` may be cited as bounded `confirmed` / `confirmed-runtime`; embedding mechanics that appear in `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` may be cited only at the exact model/dimension/status recorded there.
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
- Assign every insufficient claim to an owner / resolution / verification path such as S03 source indexing, S08 architecture caveats, or a later runtime/legal-quality proof; do not reopen S04 for mechanics already confirmed by its artifact.
</required_guardrails>

<failure_handling>
If GitNexus errors, times out, or returns noisy/malformed results, fall back to `/root/vendor-source/` source paths and mark affected claims `docs-backed/source-pending` or `smoke-needed`; never upgrade them to `confirmed`. If FalkorDB docs snippets are unavailable, ambiguous, or malformed, record the evidence gap and keep the claim source-pending or smoke-needed.
</failure_handling>

<s06_evidence_refresh>
Route refreshed FalkorDB and embedding claims through these bounded anchors:
- `.gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json` confirms host-specific FalkorDB and FalkorDBLite runtime mechanics for synthetic graph, UDF, procedure listing, full-text, vector index/distance, and dimension-4 vector probes; it does not prove product suitability, production scale, legal retrieval quality, or a direct LegalGraph GraphBLAS control surface.
- `.gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json` records pre-runtime candidate ordering and constraints for `deepvk/USER-bge-m3`, `1024`, `ai-sage/Giga-Embeddings-instruct`, and 2048-dimensional challenger risk under D002/D003 local/open-weight embedding decisions.
- `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` upgrades `deepvk/USER-bge-m3` to a bounded local/open-weight `confirmed-runtime` baseline on this host: local encode succeeded, observed vector dimension is `1024`, and live FalkorDB 1024-dimensional index/query proof exists. It keeps `GigaEmbeddings` / `ai-sage/Giga-Embeddings-instruct` and 2048-dimensional vector proof `blocked-environment` / safety-gated, not disproven and not confirmed.
Keep every claim in owner / resolution / verification form. These anchors do not prove production legal retrieval quality, product hybrid retrieval readiness, managed embedding API suitability, or direct GraphBLAS control-surface access.
</s06_evidence_refresh>

<success_criteria>
A correct answer decomposes vague claims into verifiable subclaims, cites the evidence route used, produces a concise claim table under the five claim classes, avoids Neo4j carryover, preserves bounded GraphBLAS wording, and names downstream owners for source/runtime gaps.
</success_criteria>
