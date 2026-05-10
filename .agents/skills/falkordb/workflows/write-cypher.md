# Workflow: Write or Review FalkorDB Cypher

<required_reading>
Read now:
1. `references/cypher-falkordb.md`
2. `references/graph-modeling.md` if schema assumptions are unclear.
3. `templates/query-review.md` when reviewing or handing off a query.
</required_reading>

<process>
## Step 1 — Confirm graph shape
List labels, relationship types, key properties, expected cardinalities, and required parameters. If schema is unknown, ask for it or inspect existing migrations/queries.

## Step 2 — Write the smallest correct query
Prefer parameterized queries. Avoid string interpolation for user input. Use `MATCH`/`OPTIONAL MATCH` intentionally; keep write queries idempotent where possible using `MERGE` and uniqueness constraints/indexes if available.

## Step 3 — Check FalkorDB compatibility
Do not assume Neo4j APOC/GDS/functions/procedures. If a query relies on non-core behavior, route through `workflows/check-capability.md`.

## Step 4 — Add verification
Provide a tiny fixture, expected result, and cleanup when practical. For performance-sensitive queries, include `EXPLAIN`/plan inspection guidance if supported in the target runtime.

## Step 5 — Review risks
Call out fan-out, missing indexes, cartesian products, accidental writes, null handling, and injection risk.
</process>

<success_criteria>
- [ ] Query is parameterized.
- [ ] Schema assumptions are explicit.
- [ ] Neo4j-only constructs are not used without FalkorDB proof.
- [ ] Verification fixture or expected result is included.
- [ ] Performance and safety risks are stated.
</success_criteria>
