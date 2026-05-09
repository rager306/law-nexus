<workflow>
<name>Answer a FalkorDB architecture question</name>

<when_to_use>
Use this workflow for architecture questions that ask whether FalkorDB can support a LegalGraph Nexus design choice, such as GraphBLAS-backed graph operations, OpenCypher query shape, full-text retrieval, vector retrieval, UDF/procedure usage, FalkorDBLite suitability, or driver/runtime integration.
</when_to_use>

<required_reading>
- `../references/falkordb-evidence-protocol.md`
- `.gsd/DECISIONS.md` for current D002/D003 embedding decisions and `/root/vendor-source/` conventions; do not cite stale decision IDs as authoritative GraphBLAS proof.
- `prd/02_architecture.md` and `prd/03_PRD.md` only for the architecture claim being assessed, not as proof of FalkorDB behavior.
</required_reading>

<process>
1. Restate the architecture question as 2-6 material claims. Reframe vague inputs such as “FalkorDB supports everything Neo4j supports” into verifiable subclaims instead of answering globally. Split graph runtime, embedding model runtime, vector storage dimension, Russian legal answer quality, and product-readiness into separate rows.
2. For each claim, name the expected evidence class before searching: docs, source, runtime smoke, contradiction, or M001 scope boundary.
3. Call `gitnexus_list_repos` when S03 reference indexes may exist. Select only repos whose path/name clearly match FalkorDB, falkordb-py, FalkorDBLite, or other relevant vendor/reference checkouts discovered at runtime. Do not hardcode future repo names.
4. For matching GitNexus repos, use bounded `gitnexus_query` / `gitnexus_context` lookups per claim. Prefer batching related claims to avoid noisy 10x evidence expansion.
5. If no matching repo exists, GitNexus fails, results are noisy, or results are malformed, fall back to source files expected under `/root/vendor-source/` and mark the claim `docs-backed/source-pending` or `smoke-needed` rather than `confirmed`.
6. Treat docs snippets as useful but insufficient for final architecture proof. FalkorDB docs can support `docs-backed/source-pending`; runtime-sensitive claims remain `smoke-needed` unless S04/S10 directly confirms the same bounded mechanic, model, dimension, and host/runtime boundary.
7. Apply conservative GraphBLAS wording exactly: it is acceptable to say FalkorDB has GraphBLAS-backed functionality/internal architecture when evidence supports it; do not claim LegalGraph has a direct GraphBLAS API/control surface until source/runtime proof exists.
8. For embedding claims, cite `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` when saying `deepvk/USER-bge-m3` is a local/open-weight `confirmed-runtime` baseline with `1024`-dimensional FalkorDB proof. Keep `GigaEmbeddings` / `ai-sage/Giga-Embeddings-instruct` and 2048-dimensional storage as `blocked-environment` / gated unless a later artifact closes the safety/runtime gates.
9. Produce a concise claim table rather than long prose. Include claim, evidence route, class, owner, and next verification step.
</process>

<output_format>
Use this compact table:

| Claim | Evidence route | Claim class | Owner | Next verification |
|---|---|---|---|---|
| Graph runtime mechanic | S04 smoke/source/docs/out-of-scope | confirmed/docs-backed/source-pending/smoke-needed/contradicted/out-of-scope | S03/S04/S08/none | ... |
| Embedding model runtime | S10 runtime proof/S09 evaluation | confirmed-runtime/blocked-environment/smoke-needed/out-of-scope | S10/M002/S08/none | ... |
| Vector storage dimension | S04 dimension-4 or S10 1024/2048 proof | confirmed-runtime/blocked-environment/smoke-needed | S10/M002/S08 | ... |
| Legal-quality/product-readiness | EvidenceSpan/SourceBlock evaluation or out-of-scope | smoke-needed/out-of-scope | S08/M002+ | ... |

Then add a short “Architecture answer” paragraph that uses only the classified claims and explicitly preserves uncertainty.
</output_format>

<failure_modes>
- GitNexus error or timeout: record the GitNexus lookup as unavailable, fall back to `/root/vendor-source/`, and assign S03/S04 ownership.
- Malformed or irrelevant GitNexus response: treat it as insufficient evidence and require repo scoping/source confirmation.
- FalkorDB docs unavailable or ambiguous: do not block the workflow; classify as `docs-backed/source-pending` or `smoke-needed`.
- Product-pipeline implementation request: classify as `out-of-scope` for M001 architecture-only guidance and route to later implementation planning.
</failure_modes>

<negative_tests>
- “FalkorDB supports everything Neo4j supports” must become separate OpenCypher, indexing, procedure/UDF, full-text, vector, and driver/runtime claims.
- “Use GraphBLAS directly from LegalGraph” must be `smoke-needed` or `docs-backed/source-pending` unless source/runtime evidence proves a direct control surface.
- “Implement the import pipeline now” must be `out-of-scope` for this skill and for M001 architecture-only guidance.
- “GigaEmbeddings proven” must be rejected unless a later artifact closes the recorded safety/runtime gates.
- “USER-bge-m3 proves production legal retrieval quality” must be split: USER-bge-m3 runtime mechanics are confirmed by S10; production legal retrieval quality remains unproven.
</negative_tests>
</workflow>
