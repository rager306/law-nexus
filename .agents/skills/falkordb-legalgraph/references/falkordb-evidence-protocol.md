<reference>
<name>FalkorDB evidence protocol</name>

<purpose>
This reference defines how LegalGraph Nexus agents classify FalkorDB capability and architecture claims. It exists to prevent Neo4j carryover, docs-only overclaiming, and unverified GraphBLAS/API assumptions while S03/S04 evidence is still pending.
</purpose>

<required_terms>
Every FalkorDB architecture answer should preserve these terms accurately when relevant: FalkorDB, GraphBLAS, OpenCypher, full-text, vector, UDF, GitNexus, `/root/vendor-source/`.
</required_terms>

<claim_classes>
- `confirmed`: The bounded claim is directly supported by source-backed GitNexus/source evidence or by runtime-smoke evidence in the target environment. A docs-only claim is not confirmed.
- `docs-backed/source-pending`: FalkorDB documentation or release notes support the claim, but S03 source/GitNexus confirmation is missing or incomplete.
- `smoke-needed`: The claim depends on runtime behavior, configuration, compatibility, persistence, performance, UDF loading, full-text query behavior, vector behavior, FalkorDBLite behavior, or LegalGraph-specific suitability that must be checked by S04.
- `contradicted`: Available docs, source, or runtime evidence shows the claim is false, unsupported, removed, or materially different from the architecture assumption.
- `out-of-scope`: The request asks for product-pipeline implementation, legal-authority judgment, ETL/import construction, Legal KnowQL parser/runtime work, or anything outside M001/S02 skill/evidence guidance.
</claim_classes>

<evidence_sources>
Use evidence in this order when available:
1. Runtime-smoke output from S04 for environment-sensitive behavior.
2. Source-backed GitNexus/source evidence from matching vendor/reference repos discovered at runtime.
3. Local source checkout paths under `/root/vendor-source/` when GitNexus indexes are missing or insufficient.
4. FalkorDB docs snippets as docs-backed evidence only.
5. PRD/GSD architecture text as project intent, not as proof of FalkorDB behavior.
</evidence_sources>

<gitnexus_protocol>
Call `gitnexus_list_repos` first. Scope follow-up `gitnexus_query` and `gitnexus_context` calls to matching vendor/reference repos discovered at runtime; do not hardcode future repo names. If no matching GitNexus repo exists, mark source evidence unavailable and use `/root/vendor-source/` as the expected fallback location.
</gitnexus_protocol>

<graphblas_protocol>
D004/D009 permit architecture wording that FalkorDB has GraphBLAS-backed functionality/internal architecture for sparse-matrix graph operations when FalkorDB evidence supports that statement. They do not confirm a direct LegalGraph GraphBLAS API, a direct GraphBLAS control surface, or product-level algorithm control through FalkorDB. Those direct-control claims require S03 source proof and usually S04 smoke proof.
</graphblas_protocol>

<capability_boundaries>
- OpenCypher support must be described as FalkorDB-specific OpenCypher behavior, not Neo4j Cypher parity.
- full-text claims require docs/source classification and may still need S04 smoke evidence for query semantics and target-environment behavior.
- vector claims require docs/source classification and S04 smoke evidence for runtime suitability before architecture reliance.
- UDF claims require source/runtime evidence for loading, execution, failure behavior, and deployment constraints.
- FalkorDBLite or driver claims are runtime-sensitive and usually `smoke-needed` until S04.
</capability_boundaries>

<failure_rules>
- GitNexus error/timeout/malformed response: classify conservatively as `docs-backed/source-pending` or `smoke-needed` and assign S03/S04 ownership.
- Docs error/timeout/malformed snippet: record docs unavailable and do not strengthen the claim.
- No source checkout under `/root/vendor-source/`: record the missing path as an evidence gap rather than inferring absence of capability.
- Broad claim such as “FalkorDB supports everything Neo4j supports”: reject the broad form and decompose into bounded subclaims.
</failure_rules>
</reference>
