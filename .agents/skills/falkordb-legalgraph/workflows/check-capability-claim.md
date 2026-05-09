<workflow>
<name>Check one FalkorDB capability claim</name>

<when_to_use>
Use this workflow when the task is a single capability question, for example “Does FalkorDB support full-text?”, “Can LegalGraph use vector search in FalkorDB?”, “Are UDFs available?”, “Does FalkorDB expose GraphBLAS?”, or “Can FalkorDBLite satisfy local smoke requirements?”.
</when_to_use>

<required_reading>
Read `../references/falkordb-evidence-protocol.md` first so the claim is classified with the project’s five claim classes.
</required_reading>

<process>
1. Normalize the claim into one testable sentence. If it mentions Neo4j, remove the Neo4j assumption and restate the FalkorDB-specific behavior to verify.
2. Split the evidence into five buckets:
   - `docs-backed`: official FalkorDB documentation or release notes describe the behavior.
   - `source-backed`: GitNexus/source evidence in matching vendor/reference repos shows the implementation or API surface.
   - `runtime-smoke`: S04 or S10 smoke output demonstrates the bounded behavior in the target environment.
   - `contradicted`: evidence shows the behavior is unavailable, unsupported, or materially different.
   - `out-of-scope`: the claim asks for product implementation or legal-domain truth outside M001 architecture-only scope.
3. Use `gitnexus_list_repos` and scope to matching repos discovered at runtime. If a matching repo exists, use `gitnexus_query` or `gitnexus_context` for the specific capability term.
4. If GitNexus is absent, errors, times out, or returns malformed/noisy results, inspect or point to `/root/vendor-source/` as the expected fallback and keep the class conservative.
5. Classify the claim:
   - `confirmed` only when source-backed or runtime-smoke evidence directly proves the bounded claim.
   - `docs-backed/source-pending` when docs support the claim but S03 source evidence is missing.
   - `smoke-needed` when behavior depends on runtime configuration, performance, persistence, UDF loading, full-text/vector query semantics, FalkorDBLite behavior, product suitability, legal retrieval quality, or candidate dimensions/models not directly covered by S04/S10.
   - `contradicted` when docs/source/runtime evidence rejects the claim.
   - `out-of-scope` when it asks this skill to build product code or decide legal authority.
6. Assign an owner. Use S03 for source/index proof, S04/S10 only when citing their existing runtime artifacts, S08 for final architecture-report caveats, M002/future proof for deferred embedding/runtime work, or “none” only when the bounded claim is already confirmed or out of scope.
</process>

<graphblas_rule>
For GraphBLAS, preserve conservative architecture wording. “FalkorDB GraphBLAS-backed functionality/internal architecture” can be docs-backed/source-pending when evidence supports FalkorDB internals. “LegalGraph can directly control GraphBLAS through a stable FalkorDB API” is not confirmed without source/runtime proof and should normally be `smoke-needed` or `docs-backed/source-pending`.
</graphblas_rule>

<embedding_runtime_rule>
When the claim mentions embeddings or vector dimensions, split model runtime from vector storage and legal quality. `.gsd/milestones/M001/slices/S10/S10-EMBEDDING-RUNTIME-PROOF.json` confirms `deepvk/USER-bge-m3` as a bounded local/open-weight runtime baseline on this host with `1024`-dimensional encode and FalkorDB vector proof. `GigaEmbeddings` / `ai-sage/Giga-Embeddings-instruct` and 2048-dimensional proof are `blocked-environment` / gated under current safety/runtime conditions, not disproven and not confirmed. D002/D003 allow local/open-weight candidate ordering only; they do not prove production legal retrieval quality.
</embedding_runtime_rule>

<output_format>
Return this minimal record:

- Claim: ...
- Evidence checked: docs / GitNexus repo(s) / `/root/vendor-source/` path(s) / smoke output / none available
- Claim class: `confirmed` | `docs-backed/source-pending` | `smoke-needed` | `contradicted` | `out-of-scope`
- Owner: S03 / S04 / S08 / none
- Reason: one or two evidence-grounded sentences
</output_format>

<failure_modes>
- Do not turn docs-only evidence into `confirmed`.
- Do not normalize ambiguous docs into a stronger claim.
- Do not accept “Neo4j supports X” as FalkorDB evidence.
- Do not treat LLM-generated summaries as source evidence.
- Do not phrase `GigaEmbeddings` as proven or convert fixture-ID-only metrics into production legal retrieval quality.
</failure_modes>
</workflow>
