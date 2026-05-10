# Workflow: Use FalkorDB Python Client

<required_reading>
Read now:
1. `references/python-client.md`
2. `references/cypher-falkordb.md`
3. `templates/query-review.md` for query handoff.
</required_reading>

<process>
## Step 1 — Identify runtime mode
Determine whether the code targets a remote FalkorDB server, local Docker/container, CI smoke test, or embedded FalkorDBLite. For embedded use, switch to `workflows/use-falkordblite.md`.

## Step 2 — Use safe client lifecycle
Create the client once per process/service boundary where possible. Keep connection parameters in environment/config, not hardcoded code. Never log credentials.

## Step 3 — Parameterize queries
Use parameter passing supported by the client rather than formatting values into query strings. Wrap write batches in explicit error handling and report graph name, operation, and query label without secrets.

## Step 4 — Verify with a smoke query
Use a synthetic graph fixture: create graph, write a node/relationship, read it back, and clean up. For capability-sensitive features, call `workflows/check-capability.md` first.

## Step 5 — Add observability
For production code, expose phase, graph name, operation name, retry count, duration, last error category, and timing. Do not log raw large vectors or sensitive document text.
</process>

<success_criteria>
- [ ] Runtime mode is clear.
- [ ] Credentials are not hardcoded or logged.
- [ ] Queries are parameterized.
- [ ] Smoke verification exists.
- [ ] Errors include enough context for the next agent to debug.
</success_criteria>
