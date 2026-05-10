# FalkorDB Python Client Notes

## Use cases

Use the Python client when code needs to connect to a running FalkorDB server, execute Cypher, run smoke checks, or integrate graph operations into Python services/scripts.

## Safe defaults

- Keep connection config outside source code.
- Do not log credentials.
- Reuse client/connection objects at service boundaries when appropriate.
- Parameterize queries.
- Use operation names in logs: `graph`, `operation`, `phase`, `duration_ms`, `error_class`.
- For scripts/tests, create disposable graph data and clean up.

## Review checklist

- Runtime target is clear: server, Docker, CI, or local dev.
- Query parameters are passed as parameters, not interpolated.
- Errors include graph name and operation but no secrets.
- Writes are retried only when safe/idempotent.
- Batch operations have bounded chunk size and failure reporting.
- Capability-sensitive calls are proof-gated.

## Minimal smoke shape

```python
# Pseudocode: adapt to actual falkordb-py version/API in the project.
from falkordb import FalkorDB

client = FalkorDB(host="localhost", port=6379)
graph = client.select_graph("skill_smoke")
graph.query("CREATE (:Smoke {id: $id})", {"id": "ok"})
result = graph.query("MATCH (n:Smoke {id: $id}) RETURN n.id", {"id": "ok"})
assert result.result_set
```

Confirm exact constructor/API against installed `falkordb-py` docs/source before committing code.
