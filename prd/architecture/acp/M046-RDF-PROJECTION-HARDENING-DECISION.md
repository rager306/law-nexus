# M046 RDF Projection Hardening Decision

## Status

Adopted.

## Decision

Adopt the M046 RDF projection hardening result for the custom-only ACP RDF/SHACL/SPARQL projection workflow.

The projection remains custom-only, derived, and non-authoritative.

Do not promote RDF/SHACL/SPARQL projection to a default generated architecture artifact as part of M046.

Do not add `rdflib`, `pyshacl`, SPARQL runtime execution, RDF engine execution, SHACL engine execution, or git-lex runtime integration as part of M046.

## What M046 adopts

M046 adopts the following hardening changes:

1. Diagnostic metadata on projection diagnostics:
   - `severity`
   - `category`
   - `remediation`
2. Report-level diagnostic summary:
   - counts by rule;
   - counts by category;
   - counts by severity.
3. Report-level vocabulary notes:
   - `lgarch:` namespace;
   - `acp:` namespace;
   - projected classes;
   - projected predicates;
   - explicit vocabulary boundary.
4. Report-level safety boundary.
5. Non-writing diff mode:

```bash
uv run python scripts/export-architecture-rdf-projection.py --diff
```

Diff mode compares generated output content with current output files and reports each output as `current`, `missing`, or `stale`. It includes deterministic byte counts and SHA-256 hashes. It does not write or mutate output files.

## Current workflow

Write/update derived projection outputs:

```bash
uv run python scripts/export-architecture-rdf-projection.py
```

Check current outputs:

```bash
uv run python scripts/export-architecture-rdf-projection.py --check
```

Preview output freshness without writing:

```bash
uv run python scripts/export-architecture-rdf-projection.py --diff
```

## Current outputs

Approved derived outputs remain:

- `prd/architecture/acp/derived/architecture-projection.ttl`
- `prd/architecture/acp/derived/architecture-projection.shacl.ttl`
- `prd/architecture/acp/derived/architecture-projection.sparql`
- `prd/architecture/acp/derived/architecture-projection-rdf-report.json`

The projection continues to read:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`

Those input JSONL files are generated registry projections, not architecture source truth. PRD, GSD, ADR, source, tests, runtime proof, and real-document evidence remain authoritative.

## Evidence

M046 S01 created the hardening contract:

- `prd/architecture/acp/M046-RDF-PROJECTION-HARDENING-CONTRACT.md`

M046 S02 implemented and tested the hardening in:

- `scripts/export-architecture-rdf-projection.py`
- `tests/test_architecture_rdf_projection.py`
- `prd/architecture/acp/derived/architecture-projection-rdf-report.json`

Current report counts remain:

- items: 63
- edges: 98
- ACP items: 5
- ACP edges: 7
- RDF resources: 161
- Turtle statements: 422

Verification passed:

- `uv run python scripts/export-architecture-rdf-projection.py --check`
- `uv run python scripts/export-architecture-rdf-projection.py --diff`
- `uv run pytest tests/test_architecture_rdf_projection.py`
- focused projection tests: 12 passed
- `uv run python scripts/extract-prd-architecture-items.py --check`
- `uv run python scripts/build-architecture-graph.py --check`
- `uv run python scripts/verify-architecture-graph.py`
- `uv run python scripts/verify-acp-records.py`
- `uv run python scripts/export-acp-recovery-view.py --check`
- `uv run python scripts/export-acp-architecture-projection.py --check`
- `uv run python scripts/export-acp-architecture-projection.py --canonical-jsonl --check`
- `uv run ruff check scripts/export-architecture-rdf-projection.py tests/test_architecture_rdf_projection.py`
- LSP diagnostics for exporter and focused tests: clean
- generated-artifact marker scan: passed

GitNexus change detection during S02 reported high risk because the exporter file touched many local symbols. Targeted impact checks for modified exporter entry points and helpers were low and bounded to the local CLI flow. After commit and reindex, GitNexus reported no changes and risk none.

## Why this adoption level is correct

The hardening improves operational usefulness without changing authority boundaries.

It makes failures easier for future agents to diagnose by adding deterministic categories, severity, remediation, vocabulary notes, safety boundary text, and non-writing freshness checks.

It does not introduce RDF runtime parsing, SPARQL execution, SHACL validation, or ontology reasoning. Therefore custom-only derived adoption remains the correct level.

## Blocked actions after M046

The following remain blocked:

- Treating RDF, SHACL, SPARQL, Turtle, or any triple store as architecture source truth.
- Treating projection artifacts as legal truth.
- Treating projection artifacts as product runtime evidence.
- Treating projection artifacts as accepted architecture doctrine.
- Using generated RDF to validate requirements.
- Using SHACL smoke output to claim ontology correctness.
- Using SPARQL handoff queries to claim product runtime behavior.
- Using projection artifacts as FalkorDB ingestion proof.
- Treating ACP `decision_candidate` rows as accepted decisions.
- Treating proof-gate rows as proof-gate satisfaction.
- Running `git lex init` in the main repository.
- Promoting projection to default generated architecture artifact without a later explicit proof-gated milestone.

## Non-claims

This decision does not validate R035.

This decision does not validate R037.

This decision does not validate R038.

This decision does not prove parser completeness, legal correctness, graph-vector retrieval quality, FalkorDB ingestion/runtime loading, production readiness, independent external review, ontology correctness, RDF completeness, SHACL completeness, SPARQL engine correctness, git-lex compatibility, or product Legal KnowQL behavior.

Projection artifacts remain derived diagnostics and recovery/interoperability aids. They are not legal truth, not product runtime evidence, not accepted architecture doctrine, and not source-of-truth replacements.

## Next recommended ACP milestone

The next recommended milestone is **ACP Decision Lifecycle Workflow**.

Rationale:

1. ACP now has fixture records, default registry inclusion, recovery/export surfaces, and hardened projection diagnostics.
2. The next architectural gap is not another projection format; it is safe lifecycle movement from `decision_candidate` to accepted, deferred, rejected, or superseded decision states.
3. Decision lifecycle workflow should enforce authority requirements, proof-gate checks, blocked actions, non-claims, and source-anchor safety before promotion.

Alternative next milestones remain valid if needed:

1. Optional RDF engine spike if execution proof becomes valuable.
2. Optional SHACL engine spike if shape engine validation becomes valuable.
3. Isolated git-lex alignment spike if identity/provenance compatibility becomes the priority.
4. ACP recovery/dashboard views if operator navigation becomes the priority.

## Revisit trigger

Revisit this decision only when at least one of the following is true:

- A future milestone needs default generated RDF projection as part of regular architecture verification.
- A future spike proves `rdflib`, `pyshacl`, or SPARQL execution adds enough value to justify dependency and maintenance cost.
- ACP recovery/dashboard work needs RDF projection as a stable input.
- A git-lex alignment spike proves a safe isolated adoption path.

Until then, keep hardened RDF/SHACL/SPARQL projection custom-only, derived, and non-authoritative.
