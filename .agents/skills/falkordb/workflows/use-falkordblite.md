# Workflow: Use FalkorDBLite

<required_reading>
Read now:
1. `references/falkordblite.md`
2. `references/python-client.md`
3. `references/capability-evidence.md`
</required_reading>

<process>
## Step 1 — Confirm why embedded mode is needed
Use FalkorDBLite for local tests, demos, CI smoke checks, or constrained embedded workflows. Do not assume it matches a production FalkorDB deployment until the capability is smoke-tested in both runtimes.

## Step 2 — Verify installation/runtime
Check package installation, binary availability, startup, graph creation, basic query, and cleanup. Record exact failure class if startup fails.

## Step 3 — Bound capability claims
For indexes, full-text, vector, UDF/procedure behavior, persistence, concurrency, or resource limits, use `workflows/check-capability.md`. Embedded success does not automatically prove server success, and server success does not automatically prove embedded success.

## Step 4 — Write disposable fixtures
Use synthetic graph data and deterministic cleanup. Avoid real sensitive documents in embedded smoke tests unless the workflow explicitly requires local-only handling.

## Step 5 — Hand off status
Classify the embedded path as runtime-confirmed, blocked-environment, smoke-needed, or unknown with logs and next proof steps.
</process>

<success_criteria>
- [ ] Embedded use case is justified.
- [ ] Startup/basic query/cleanup are verified or blocked with diagnostics.
- [ ] Server-vs-embedded differences are not hidden.
- [ ] Capability claims have explicit proof class.
</success_criteria>
