# M045 RDF SHACL SPARQL Projection Decision

## Status

Adopted as a custom-only derived projection proof.

## Decision

Keep the RDF/SHACL/SPARQL projection custom-only under ACP derived paths for now.

Do not promote the projection to a default generated architecture artifact yet.

Do not add RDF engine dependencies, SHACL engine dependencies, SPARQL runtime execution, or git-lex runtime integration as part of M045.

## What M045 adopted

M045 adopts the following custom-only projection workflow:

```bash
uv run python scripts/export-architecture-rdf-projection.py
uv run python scripts/export-architecture-rdf-projection.py --check
```

The workflow reads the generated default architecture registry:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`

It writes these derived ACP proof artifacts:

- `prd/architecture/acp/derived/architecture-projection.ttl`
- `prd/architecture/acp/derived/architecture-projection.shacl.ttl`
- `prd/architecture/acp/derived/architecture-projection.sparql`
- `prd/architecture/acp/derived/architecture-projection-rdf-report.json`

The projection uses stable repository-local IRIs such as:

```text
urn:law-nexus:architecture:<record-id>
```

## Evidence from S02

S02 produced a deterministic stdlib-first projection with these current report counts:

- items: 63
- edges: 98
- ACP items: 5
- ACP edges: 7
- RDF resources: 161
- Turtle statements: 422

S02 verification passed:

- `uv run python scripts/export-architecture-rdf-projection.py --check`
- `uv run pytest tests/test_architecture_rdf_projection.py`
- `uv run python scripts/extract-prd-architecture-items.py --check`
- `uv run python scripts/build-architecture-graph.py --check`
- `uv run python scripts/verify-architecture-graph.py`
- `uv run python scripts/verify-acp-records.py`
- `uv run python scripts/export-acp-recovery-view.py --check`
- `uv run python scripts/export-acp-architecture-projection.py --check`
- `uv run python scripts/export-acp-architecture-projection.py --canonical-jsonl --check`
- `uv run ruff check scripts/export-architecture-rdf-projection.py tests/test_architecture_rdf_projection.py`
- relevant combined tests: 89 passed

The default architecture verifier remained green with:

- status: ok
- items: 63
- edges: 98
- failure_count: 0
- upstream_checks: passed

## Why custom-only is the right adoption level

Custom-only is the correct current level because:

1. The projection is useful as an interoperability and recovery artifact.
2. The output is deterministic and test-covered.
3. The default architecture verifier remains green.
4. SHACL is currently a minimal shape-smoke artifact, not pySHACL execution.
5. SPARQL is currently a handoff query artifact, not engine-executed proof.
6. RDF output is a derived projection of generated registry rows, not a source evidence layer.
7. Promoting to default generated projection should wait until a future hardening milestone confirms maintenance value.

## Blocked actions after M045

The following remain blocked:

- Treating RDF, SHACL, SPARQL, Turtle, or any triple store as architecture source truth.
- Treating the projection as legal truth.
- Treating the projection as product runtime evidence.
- Treating the projection as accepted architecture doctrine.
- Using generated RDF to validate requirements.
- Using SHACL smoke output to claim ontology correctness.
- Using SPARQL handoff queries to claim product runtime behavior.
- Using projection artifacts as FalkorDB ingestion proof.
- Treating ACP `decision_candidate` rows as accepted decisions.
- Treating proof-gate rows as proof-gate satisfaction.
- Running `git lex init` in the main repository.

## Non-claims

This decision does not validate R035.

This decision does not validate R037.

This decision does not validate R038.

This decision does not prove parser completeness, legal correctness, graph-vector retrieval quality, FalkorDB ingestion/runtime loading, production readiness, independent external review, ontology correctness, RDF completeness, SHACL completeness, SPARQL engine correctness, git-lex compatibility, or product Legal KnowQL behavior.

Projection artifacts remain derived diagnostics and recovery/interoperability aids. They are not legal truth, not product runtime evidence, not accepted architecture doctrine, and not source-of-truth replacements.

## Follow-up roadmap

Recommended next ACP milestones:

1. RDF projection hardening: richer diagnostics, vocabulary notes, and optional diff mode.
2. Optional RDF engine spike: evaluate `rdflib` for Turtle parse and SPARQL count-query execution in a separate proof.
3. Optional SHACL engine spike: evaluate `pyshacl` only if there is a concrete need for engine-backed shape validation.
4. Isolated git-lex alignment spike: test identity/provenance alignment without running `git lex init` in the main repo.
5. ACP recovery/dashboard views: generated next-action and blocker surfaces, still derived and non-authoritative.
6. ACP decision lifecycle workflow: safe promotion from decision candidate to accepted/deferred/rejected decision with authority and proof-gate checks.

## Revisit trigger

Revisit this decision only when at least one of the following is true:

- A future milestone needs default generated RDF projection as part of regular architecture verification.
- A future spike proves `rdflib` or `pyshacl` adds enough value to justify dependency cost.
- ACP recovery/dashboard work needs RDF projection as a stable input.
- A git-lex alignment spike proves a safe isolated adoption path.

Until then, keep RDF/SHACL/SPARQL projection custom-only and derived.
