# FalkorDB Capability Evidence Protocol

## Claim classes

- `runtime-confirmed` — a command/query/smoke test ran successfully in the stated runtime.
- `source-backed` — FalkorDB/falkordb-py/FalkorDBLite source supports the claim, but no local runtime proof was run.
- `docs-backed` — official docs or README state the behavior, but source/runtime proof was not checked.
- `smoke-needed` — plausible, but implementation should not rely on it until a small test runs.
- `blocked-environment` — verification could not run because of Docker, package, hardware, cache, network, or permission constraints.
- `neo4j-only` — evidence exists for Neo4j but not FalkorDB.
- `redisgraph-legacy` — evidence comes from RedisGraph-era material and needs FalkorDB revalidation.
- `unknown` — no reliable evidence found.

## Evidence hierarchy

Prefer:
1. Existing runtime smoke artifacts for the target runtime.
2. Direct runtime smoke on synthetic data.
3. FalkorDB/falkordb-py/FalkorDBLite source navigation.
4. Official docs or repository README.
5. Third-party examples, only as hints.

## Mandatory proof shape

Every capability-sensitive answer should include:

```text
Claim:
Status:
Runtime/context:
Evidence:
Caveats:
Next proof:
Verification criterion:
```

## Neo4j drift filter

Do not assume these Neo4j concepts exist in FalkorDB without evidence:

- APOC procedures/functions
- Graph Data Science library algorithms (GDS)
- Aura-specific operations
- Neo4j GenAI plugin APIs
- Neo4j driver API methods
- Neo4j-specific Cypher version features
- Neo4j vector syntax, Neo4j vector index syntax, or full-text syntax

Use Neo4j skills as structure: when-to-use, when-not-to-use, preflight, decision tables, safety checks, verification loops. Do not use them as FalkorDB capability proof.

## Runtime proof examples

Good proof:
- A script creates a disposable graph, creates the target index, inserts synthetic data, runs the target query, asserts returned rows/scores, and cleans up.

Weak proof:
- A blog says a related RedisGraph/Neo4j feature exists.
- A query string compiles in another database.
- A source file contains a similar term but no call path or runtime test.
