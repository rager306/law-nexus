# FalkorDB Cypher Guardrails

## Defaults

- Inspect schema before writing queries.
- Parameterize values; do not interpolate user input into query strings.
- Keep write queries idempotent when possible.
- Use small fixtures and expected outputs for verification.
- Avoid Neo4j-only APOC/GDS/procedure assumptions.

## Query safety checklist

- Are labels and relationship types known?
- Are relationship directions intentional?
- Are optional paths actually optional?
- Could this create a cartesian product?
- Are lookup predicates indexed or bounded?
- Are write operations protected against duplicates?
- Are null/missing properties handled?
- Is user input passed as parameters?

## Common patterns

Parameterized read:

```cypher
MATCH (n:Entity {id: $id})
RETURN n
```

Relationship traversal:

```cypher
MATCH (a:Source {id: $source_id})-[:RELATES_TO]->(b:Target)
RETURN b
ORDER BY b.name
LIMIT $limit
```

Idempotent-ish upsert pattern:

```cypher
MERGE (n:Entity {id: $id})
SET n.name = $name,
    n.updated_at = $updated_at
RETURN n
```

## Compatibility rule

If a query uses procedures, full-text, vector search, GraphBLAS-related behavior, custom functions, or non-obvious Cypher syntax, route through `workflows/check-capability.md` before presenting it as FalkorDB-supported.
