# Workflow: Check a FalkorDB Capability Claim

<required_reading>
Read now:
1. `references/capability-evidence.md`
2. `references/indexes-search-vector.md` when the claim touches indexes, full-text, vector, procedures, UDFs, GraphBLAS, or runtime capabilities.
3. `templates/capability-answer.md` before writing the final answer.
</required_reading>

<process>
## Step 1 — State the exact claim
Rewrite the user's claim as a testable sentence. Avoid broad labels like "FalkorDB supports vectors" unless the operation is specified: create index, ingest vectors, query vectors, return scores, combine with filters, run via client, run via FalkorDBLite, etc.

## Step 2 — Classify evidence needed
Choose the minimum acceptable evidence class:
- Documentation/source question → docs-backed or source-backed may be enough.
- Implementation decision → runtime-confirmed or an explicit smoke-needed plan.
- Production decision → runtime-confirmed on target-like environment plus limitations.

## Step 3 — Gather proof
Prefer in order:
1. Existing project smoke artifacts or logs.
2. GitNexus/source context for FalkorDB, falkordb-py, or FalkorDBLite reference repos.
3. Official docs/source snippets.
4. A small local smoke test against synthetic data.

Never upgrade a docs-backed/source-backed claim to runtime-confirmed without an executed result.

## Step 4 — Check for Neo4j drift
Mark as `neo4j-only` or `unknown` if the evidence comes only from Neo4j features such as APOC, GDS, Aura, Neo4j GenAI plugin, Neo4j vector syntax, or Neo4j driver APIs and FalkorDB evidence has not confirmed an equivalent.

## Step 5 — Answer with owner and verification
Use `templates/capability-answer.md`. Include current status, evidence, caveats, next proof command, and verification criterion.
</process>

<success_criteria>
- [ ] Claim is stated narrowly enough to test.
- [ ] Evidence class is explicit.
- [ ] Neo4j-only assumptions are filtered out.
- [ ] Unknown/smoke-needed claims include next proof and verification criterion.
- [ ] Final answer does not overclaim product or production readiness.
</success_criteria>
