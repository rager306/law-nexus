# Handoff

This is the stable project-state handoff for a future agent.

## Last completed milestone

`M046-x5gmog — ACP RDF Projection Hardening` is complete.

It adopted:

- diagnostic severity/category/remediation metadata for RDF projection diagnostics;
- report `diagnostic_summary`, `vocabulary`, and `safety_boundary` fields;
- non-writing `--diff` mode for projection freshness checks;
- continued custom-only, derived, non-authoritative status for RDF/SHACL/SPARQL projection.

## Current active milestone

`M047-igv5e2 — law-nexus Project State Documentation Pack` is active.

Completed in M047 so far:

- S01: documentation contract and evidence inventory;
- S02: machine-readable project-state JSON;
- S03: Mermaid project-state diagrams;
- S04: human-facing project-state docs;
- S05/T01: reader-test completed with pass verdict.

S05 is the current closeout slice. Remaining work is independent review resolution, final verification, validation, and milestone completion.

## Next recommended milestone after M047

Create **ACP Decision Lifecycle Workflow**.

Use GSD:

```text
gsd_milestone_generate_id
then gsd_plan_milestone
then plan slices/tasks
```

The milestone should focus on safe lifecycle movement from `decision_candidate` to accepted, deferred, rejected, or superseded states.

## Current verification commands

Before claiming current state, run:

```bash
uv run python scripts/verify-architecture-graph.py
uv run python scripts/verify-acp-records.py
uv run python scripts/export-architecture-rdf-projection.py --check
uv run python scripts/export-architecture-rdf-projection.py --diff
uv run pytest tests/test_architecture_rdf_projection.py
```

## Current open requirements

These remain active:

- `R035` — ontology architecture research needs bounded evidence/proof gates/source mappings before promotion.
- `R037` — FalkorDB graph ingestion path remains partially evidenced, not fully validated.
- `R038` — independent review gate remains a standing proof-heavy milestone requirement.

## Do not claim

Do not claim that this project-state package validates:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion/runtime loading;
- retrieval quality;
- production readiness;
- independent external review;
- ontology correctness;
- RDF completeness;
- SHACL completeness;
- SPARQL engine correctness;
- git-lex compatibility;
- product Legal KnowQL behavior.

## Do not do

- Do not treat RDF/SHACL/SPARQL/Turtle/triple-store artifacts as architecture source truth.
- Do not treat ACP `decision_candidate` rows as accepted decisions.
- Do not treat ACP `proof_gate` rows as proof-gate satisfaction.
- Do not run git-lex initialization in the main repository.
- Do not cite ignored execution-log artifacts, absolute local paths, raw provider payloads, raw vectors, secrets, or raw legal-answer prose as durable proof anchors.
- Do not stage `.gsd/...` paths directly; `.gsd` is symlink/ignored in this repository.

## Best next action

If S05 is not complete, finish independent review resolution, run final documentation/core verification, then validate and complete M047 through GSD.

After M047 is complete, start the ACP Decision Lifecycle Workflow milestone.
