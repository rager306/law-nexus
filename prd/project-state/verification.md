# Verification

This document lists the current verification commands and their boundaries. It is derived from `prd/project-state/data/verification-matrix.json` and current GSD closeout evidence.

## Core commands

Run these commands to check the current static/project-state surface:

```bash
uv run python scripts/verify-architecture-graph.py
uv run python scripts/verify-acp-records.py
uv run python scripts/export-architecture-rdf-projection.py --check
uv run python scripts/export-architecture-rdf-projection.py --diff
uv run pytest tests/test_architecture_rdf_projection.py
```

## What each command means

| Command | Current status | Proves | Does not prove |
|---|---|---|---|
| `uv run python scripts/verify-architecture-graph.py` | passed in recent M047 verification | Static registry freshness, graph integrity, source-anchor safety, decision-fitness checks, claim-safety checks. | Product readiness, runtime behavior, parser completeness, retrieval quality, legal-answer correctness, FalkorDB production scale, LLM legal authority. |
| `uv run python scripts/verify-acp-records.py` | passed in recent M046 handoff verification | ACP fixture record mechanics and bounded safety checks for the current fixture chain. | Full ACP decision lifecycle workflow, accepted architecture decision promotion, independent external review. |
| `uv run python scripts/export-architecture-rdf-projection.py --check` | passed in recent M046/M047 verification | Custom derived RDF/SHACL/SPARQL projection outputs are current. | RDF engine correctness, SHACL engine validation, SPARQL execution correctness, ontology completeness, architecture source truth. |
| `uv run python scripts/export-architecture-rdf-projection.py --diff` | passed in recent M046/M047 verification | Projection outputs can be compared without writing files. | Semantic RDF correctness, SPARQL runtime behavior, SHACL runtime behavior. |
| `uv run pytest tests/test_architecture_rdf_projection.py` | 12 focused tests passed in recent M046/M047 verification | Focused exporter/report/diff regression coverage and negative boundary checks. | Broad product runtime correctness, legal correctness, retrieval quality. |

## Current green state

Current verified static state:

- architecture verifier: green;
- architecture items: 63;
- architecture edges: 98;
- ACP governance items: 5;
- ACP governance edges: 7;
- RDF projection status: ok;
- RDF projection diagnostics: 0;
- focused RDF projection tests: 12 passed.

## Active requirements

The following remain active and not validated by the documentation or projection work:

| Requirement | State | Boundary |
|---|---|---|
| R035 | active | Ontology architecture research still needs bounded evidence, proof gates, and source mappings before ontology/product claims are promoted. |
| R037 | active | FalkorDB graph ingestion is partially evidenced but larger ingest and operational proof remain open. |
| R038 | active | Independent review remains a standing review gate for future proof-heavy milestones. |

## Marker and claim safety

Documentation and generated project-state files should avoid positive claims that promote active or unproven requirements. They should preserve negative boundary language such as:

- derived and non-authoritative;
- not source truth;
- does not validate R035/R037/R038;
- not engine-executed;
- does not prove parser completeness or legal correctness.

## Verification before future changes

For pure docs/JSON/Mermaid changes, run:

```bash
uv run python scripts/verify-architecture-graph.py
```

and the relevant JSON/link/marker checks for the documentation package.

For code changes, also run focused tests, ruff/LSP diagnostics, GitNexus impact before edits, and GitNexus detect changes before commits.
