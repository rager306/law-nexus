# Workflow: Debug FalkorDB Runtime or Performance

<required_reading>
Read now:
1. `references/troubleshooting.md`
2. `references/cypher-falkordb.md`
3. `references/indexes-search-vector.md` if indexes/full-text/vector are involved.
</required_reading>

<process>
## Step 1 — Reproduce narrowly
Capture graph name, operation, query text with parameters redacted, data size/cardinality hints, runtime mode, client version, FalkorDB version if known, and exact error/output.

## Step 2 — Classify failure
Use categories: connection/auth, graph selection, syntax/unsupported Cypher, missing index, cardinality/fan-out, write conflict, memory/resource, environment/package, capability unsupported, unknown.

## Step 3 — Reduce to a fixture
Create the smallest synthetic dataset that reproduces the behavior. If real data is required, mask or minimize it.

## Step 4 — Inspect plan/indexes/runtime
Check whether indexes exist for lookup predicates, whether query shape creates cartesian products or broad expansions, and whether the capability is runtime-confirmed for this FalkorDB mode.

## Step 5 — Fix and verify
Change one variable at a time. Rerun the reproduction. Record the passing command/query and the before/after evidence.
</process>

<success_criteria>
- [ ] Failure is reproduced or explicitly blocked.
- [ ] Root-cause category is stated.
- [ ] Fix targets cause, not symptoms.
- [ ] Verification reruns the reproduction.
- [ ] Diagnostic output is safe to share.
</success_criteria>
