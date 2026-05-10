<reference>
<name>FalkorDB evidence protocol</name>

<purpose>
This reference defines how LegalGraph Nexus agents classify FalkorDB capability and architecture claims. It exists to prevent Neo4j carryover, docs-only overclaiming, and unverified GraphBLAS/API assumptions while incorporating current S04/S10 bounded runtime evidence.
</purpose>

<required_terms>
Every FalkorDB architecture answer should preserve these terms accurately when relevant: FalkorDB, GraphBLAS, OpenCypher, full-text, vector, UDF, GitNexus, `/root/vendor-source/`.
</required_terms>

<claim_classes>
- `confirmed`: The bounded claim is directly supported by source-backed GitNexus/source evidence or by runtime-smoke evidence in the target environment. A docs-only claim is not confirmed. Runtime artifacts may also use `confirmed-runtime`; cite that status without broadening it.
- `docs-backed/source-pending`: FalkorDB documentation or release notes support the claim, but S03 source/GitNexus confirmation is missing or incomplete.
- `smoke-needed`: The claim depends on runtime behavior, configuration, compatibility, persistence, performance, UDF loading, full-text query behavior, vector behavior, FalkorDBLite behavior, or LegalGraph-specific suitability that is not already directly covered by current S04/S10 runtime artifacts.
- `contradicted`: Available docs, source, or runtime evidence shows the claim is false, unsupported, removed, or materially different from the architecture assumption.
- `out-of-scope`: The request asks for product-pipeline implementation, legal-authority judgment, ETL/import construction, Legal KnowQL parser/runtime work, or anything outside M001 architecture-only skill/evidence guidance.
</claim_classes>

<evidence_sources>
Use evidence in this order when available:
1. Current runtime-smoke output from S04/S10 for environment-sensitive behavior.
2. Source-backed GitNexus/source evidence from matching vendor/reference repos discovered at runtime.
3. Local source checkout paths under `/root/vendor-source/` when GitNexus indexes are missing or insufficient.
4. FalkorDB docs snippets as docs-backed evidence only.
5. PRD/GSD architecture text as project intent, not as proof of FalkorDB behavior.
</evidence_sources>


<current_m001_runtime_evidence>
Use these current M001 artifacts before treating runtime suitability as pending:

- `.gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json`: S04 records `confirmed-runtime` mechanics for host-local Docker FalkorDB and FalkorDBLite synthetic graph operations, JavaScript UDF load/list/execute, procedure listing, node full-text index behavior, node vector index behavior, vector-distance expressions, and dimension-4 synthetic vector probes. Cite these only as runtime mechanics on the recorded host/image/package boundary; they do not prove product readiness, production scale, legal retrieval quality, or direct LegalGraph GraphBLAS control-surface access.
- `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json`: S10 records `deepvk/USER-bge-m3` as the bounded local/open-weight `confirmed-runtime` practical baseline on this host: encode completed, observed vector dimension is `1024`, and live FalkorDB 1024-dimensional vector index/query proof exists. It records fixture-ID-only retrieval metrics as mechanics evidence, not production legal retrieval quality.
- `.gsd/runtime-smoke/legalgraph-shaped-falkordb/LEGALGRAPH-SHAPED-FALKORDB-PROOF.json`: a 2026-05-10 persistent-container proof records `confirmed-runtime` mechanics for storing, full-text querying, and traversing a tiny synthetic LegalGraph-shaped topology (`Act`, `Article`, `Authority`, `SourceBlock`, `EvidenceSpan`) with citation, authority, evidence, source-block, `db.idx.fulltext.queryNodes('SourceBlock', 'procurement')`, and validity-window query patterns. Cite it only for those topology mechanics; it does not prove Garant ODT parsing, production schema fitness, Legal KnowQL, Legal Nexus runtime, legal retrieval quality, or legal-answer correctness.
- The same S10 artifact records `GigaEmbeddings` / `ai-sage/Giga-Embeddings-instruct` and the 2048-dimensional vector proof as `blocked-environment` / safety-gated. This is blocked/gated evidence, not a disproof of future viability and not a confirmed runtime proof.
- `.gsd/milestones/M001/slices/S09/S09-LOCAL-EMBEDDING-EVALUATION.json` remains useful for D002/D003 candidate ordering and constraints, but S10 supersedes it for USER-bge-m3 runtime status.

Every answer that cites these artifacts must include owner, resolution, and verification status. If an artifact is missing, malformed, or ambiguous, preserve bounded wording and downgrade to pending rather than inventing a stronger claim.
</current_m001_runtime_evidence>

<gitnexus_protocol>
Call `gitnexus_list_repos` first. Scope follow-up `gitnexus_query` and `gitnexus_context` calls to matching vendor/reference repos discovered at runtime; do not hardcode future repo names. If no matching GitNexus repo exists, mark source evidence unavailable and use `/root/vendor-source/` as the expected fallback location.
</gitnexus_protocol>

<graphblas_protocol>
Current architecture guidance permits wording that FalkorDB has GraphBLAS-backed functionality/internal architecture for sparse-matrix graph operations when FalkorDB evidence supports that statement. It does not confirm a direct LegalGraph GraphBLAS API, a direct GraphBLAS control surface, or product-level algorithm control through FalkorDB. Those direct-control claims require source proof and runtime proof beyond the bounded S04 mechanics artifact.
</graphblas_protocol>

<capability_boundaries>
- OpenCypher support must be described as FalkorDB-specific OpenCypher behavior, not Neo4j Cypher parity.
- full-text claims require docs/source classification and bounded runtime evidence for query semantics and target-environment behavior; cite S04 when the exact synthetic mechanic is covered, and keep product/legal suitability separate.
- vector claims require docs/source classification plus dimension-specific runtime evidence before architecture reliance: S04 confirms dimension-4 mechanics; S10 confirms USER-bge-m3 1024-dimensional FalkorDB index/query mechanics; GigaEmbeddings/2048 remains blocked/gated.
- UDF claims require source/runtime evidence for loading, execution, failure behavior, and deployment constraints.
- FalkorDBLite or driver claims are runtime-sensitive; cite S04 where its embedded FalkorDBLite mechanics are directly covered, and keep uncovered deployment or suitability claims `smoke-needed`.
</capability_boundaries>

<failure_rules>
- GitNexus error/timeout/malformed response: classify conservatively as `docs-backed/source-pending` or `smoke-needed` and assign S03/S04 ownership.
- Docs error/timeout/malformed snippet: record docs unavailable and do not strengthen the claim.
- No source checkout under `/root/vendor-source/`: record the missing path as an evidence gap rather than inferring absence of capability.
- Broad claim such as “FalkorDB supports everything Neo4j supports”: reject the broad form and decompose into bounded subclaims.
</failure_rules>
</reference>
