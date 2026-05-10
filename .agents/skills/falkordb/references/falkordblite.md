# FalkorDBLite Notes

## Intended role

FalkorDBLite is useful for embedded/local testing, quick demos, and CI-like smoke proof where a separate FalkorDB server is undesirable. Treat it as a runtime with its own boundaries, not a perfect substitute for server FalkorDB.

## Verification checklist

- Package installs in the target Python version.
- Embedded runtime starts.
- Graph can be selected/created.
- Basic write/read query succeeds.
- Cleanup works.
- Capability-specific tests run separately for indexes, full-text, vector, procedures/UDF, persistence, concurrency, and resource behavior.

## Caveats

- Do not assume server/container behavior from FalkorDBLite behavior.
- Do not assume FalkorDBLite behavior from server/container behavior.
- Record package/binary/startup failures as `blocked-environment` with exact diagnostics.
- Use synthetic data unless the workflow explicitly requires local-only real data.
