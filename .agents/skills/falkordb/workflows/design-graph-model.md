# Workflow: Design or Review a FalkorDB Graph Model

<required_reading>
Read now:
1. `references/graph-modeling.md`
2. `references/cypher-falkordb.md` if query shapes are part of the design.
3. `templates/graph-model-review.md` before producing a review.
</required_reading>

<process>
## Step 1 — Inspect domain and query workload
Identify entities, relationships, cardinalities, required traversals, update frequency, temporal/versioning needs, and evidence/provenance requirements. Do not model from nouns alone; model from questions the graph must answer.

## Step 2 — Choose labels, relationships, and properties
Prefer stable labels for entity classes, typed relationships for traversals, and properties for scalar attributes used in filters/sorts. Use intermediate nodes when a relationship needs identity, many attributes, lifecycle, or provenance.

## Step 3 — Design indexes from access patterns
For every high-frequency lookup, state the lookup pattern and proposed index. If using full-text or vector features, run `workflows/check-capability.md` before treating them as available in the target runtime.

## Step 4 — Validate with sample queries
Provide representative `CREATE`/`MERGE` examples and read queries. Check that every major product question has a traversable path without excessive fan-out.

## Step 5 — Produce review output
Use `templates/graph-model-review.md`: model, rationale, query coverage, indexes, risks, and verification plan.
</process>

<success_criteria>
- [ ] Model is driven by real query/workload needs.
- [ ] Relationship direction and cardinality are explicit.
- [ ] Indexes map to access patterns.
- [ ] Capability-sensitive features are proof-gated.
- [ ] The output includes verification queries.
</success_criteria>
