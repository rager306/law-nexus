# FalkorDB Troubleshooting Notes

## Failure classes

- connection/auth/config
- graph selection/name mismatch
- syntax or unsupported Cypher
- Neo4j-only feature used accidentally
- missing index or wrong lookup shape
- cartesian product / broad expansion
- write duplication or missing idempotency
- package/client version mismatch
- Docker/container/runtime unavailable
- memory/resource limits
- capability unsupported in this runtime
- unknown

## Reproduction protocol

1. Capture exact error and query with secrets redacted.
2. Record runtime mode: server, Docker, FalkorDBLite, CI, local.
3. Record client/library version when available.
4. Reduce data to a synthetic fixture.
5. Change one variable at a time.
6. Rerun the failing command/query after each change.

## Performance triage

- Check whether the starting node set is bounded.
- Check index support for lookup predicates.
- Check accidental cartesian products.
- Check variable-length paths and high fan-out expansions.
- Check whether filtering happens after too much traversal.
- Check result cardinality and LIMIT/ORDER BY interaction.

## Logging rule

Log operation names, counts, durations, and error classes. Do not log credentials, raw sensitive documents, or large raw embedding arrays.
