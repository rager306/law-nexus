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

Local smoke harness:
- Use `uv run python scripts/smoke-s04-falkordb-capabilities.py --output-dir .gsd/runtime-smoke/falkordb-capabilities --timeout-seconds 300`, then verify with `uv run python scripts/verify-s04-falkordb-smoke.py --markdown .gsd/runtime-smoke/falkordb-capabilities/S04-FALKORDB-CAPABILITY-SMOKE.md --json .gsd/runtime-smoke/falkordb-capabilities/S04-FALKORDB-CAPABILITY-SMOKE.json --require-runtime-results`.
- The harness waits for container readiness with `docker exec <container> redis-cli PING` before probing. If a probe fails before readiness, classify it as `blocked-environment`, not capability contradiction.
- A 2026-05-10 local run against `falkordb/falkordb:edge` image `sha256:4246e809a5fd74d233196e08c879885adc47bde499a8e25fa5ff83fd39644d80` confirmed synthetic Docker FalkorDB basic graph, UDF load/execute, procedure list, full-text index, vector index, vector-distance, PageRank, WCC, BFS, betweenness, label propagation, SPpaths, SSpaths, and MSF output-shape probes, plus FalkorDBLite basic/UDF/vector/full-text probes. This confirms only the bounded synthetic runtime behavior, not LegalGraph ETL/import/product retrieval quality or production algorithm suitability. MSF proof is specifically for `YIELD nodes, edges`; `YIELD edge, weight` was rejected by the tested runtime. Negative-contract smoke also confirmed Neo4j GDS carryover forms are rejected: `gds.pageRank.stream` is not registered, and `algo.pageRank(... ) YIELD nodeId` is not a FalkorDB yield shape.
- A 2026-05-10 local persistent-container run using `scripts/prove-legalgraph-shaped-falkordb.py` wrote `.gsd/runtime-smoke/legalgraph-shaped-falkordb/LEGALGRAPH-SHAPED-FALKORDB-PROOF.json` and confirmed bounded synthetic storage, full-text SourceBlock lookup, and traversal mechanics for a LegalGraph-shaped topology: `Act`, `Article`, `Authority`, `SourceBlock`, `EvidenceSpan`, `HAS_ARTICLE`, `CITES`, `ISSUED`, `SUPPORTED_BY`, `IN_BLOCK`, `SUPPORTS`, `db.idx.fulltext.queryNodes('SourceBlock', 'procurement')`, and a string validity-window filter. This upgrades only those small topology mechanics to `runtime-confirmed`; it does not prove Garant ODT parsing, production graph schema fitness, Legal KnowQL, Legal Nexus runtime, legal retrieval quality, or legal-answer correctness.

Weak proof:
- A blog says a related RedisGraph/Neo4j feature exists.
- A query string compiles in another database.
- A source file contains a similar term but no call path or runtime test.
