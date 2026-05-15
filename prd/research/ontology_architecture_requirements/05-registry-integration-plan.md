# M017 S04 Registry Integration Plan

## Purpose

This note records the architecture-registry contract that M017 ontology architecture intake must obey before any M017 research output is mapped into `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`.

The registry is a derived, machine-readable projection for graph analysis and architecture fitness checks. It is not the source of truth for ontology, LegalGraph, FalkorDB, parser, retrieval, Legal KnowQL, generated-Cypher, legal-answer, or LLM-authority claims.

## Source-of-truth hierarchy

Registry integration must preserve this hierarchy from `prd/architecture/README.md`:

1. Authoritative evidence lives in source documents and artifacts: PRD/research notes under `prd/`, GSD requirements/decisions/plans/summaries/validation artifacts, ADR/source code/tests/runtime smoke artifacts, and real-document proof artifacts where runtime or legal evidence is required.
2. `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_edges.jsonl` are derived JSONL projections. If generated records disagree with anchored source evidence, fix the source anchor or extractor mapping and regenerate; do not hand-edit JSONL to make a claim appear current.
3. Graph reports, health dashboards, product-readiness blocker reports, claims ledgers, GraphML/diagrams, and future router/skill guidance are downstream non-authoritative views. They may diagnose gaps or claim-safety boundaries, but they cannot upgrade proof beyond anchored evidence.
4. External references only count when represented as explicit `external-reference` source anchors and do not override local PRD/GSD/ADR decisions.

## Allowed item record shape

`architecture.schema.json` validates one `item` record at a time. Every item must include:

- `schema_version`: exactly `legalgraph-architecture-registry/v1`
- `record_kind`: `item`
- `id`: identifier matching `^[A-Z][A-Z0-9_-]*-[A-Za-z0-9_.:-]+$`
- `type`: one of `requirement`, `decision`, `assumption`, `risk`, `proof_gate`, `component`, `interface`, `data_entity`, `quality_scenario`, `viewpoint`, `evidence`, `workflow_check`
- `title`, `summary`
- `layer`: one of `legal-evidence`, `temporal-model`, `graph-runtime`, `parser-ingestion`, `retrieval-embedding`, `generated-cypher`, `api-product`, `security-safety`, `observability-operability`, `workflow-governance`, `architecture-governance`
- `status`: one of `proposed`, `active`, `hypothesis`, `bounded-evidence`, `validated`, `deferred`, `blocked`, `rejected`, `superseded`, `out-of-scope`
- `proof_level`, `risk_level`, `source_anchors`, `owner`, `verification`, `generated_draft`, and `non_claims`

Decision items carry extra ADR-style obligations: `deciders`, `decision_drivers`, and `considered_options` are schema-required. Active decisions must not be consequence-free under verifier policy, superseded decisions must name/link successors, and high/critical active decisions need `checked_by` or `validated_by` proof-gate/workflow-check coverage.

## Allowed edge record shape

Every `edge` record must include:

- `schema_version`: exactly `legalgraph-architecture-registry/v1`
- `record_kind`: `edge`
- `id`, `from`, `to`
- `type`: one of `satisfies`, `depends_on`, `blocks`, `contradicts`, `refines`, `implements`, `validated_by`, `bounded_by`, `supersedes`, `superseded_by`, `risks`, `owned_by`, `evidenced_by`, `uses_viewpoint`, `checked_by`, `has_option`, `chosen_over`, `has_consequence`, `has_assumption`, `has_constraint`, `implicates`, `reviewed_by`, `governs_artifact`
- `status`: one of `active`, `hypothesis`, `bounded-evidence`, `validated`, `rejected`, `superseded`
- `rationale`, `source_anchors`, and `generated_draft`

Verifier policy requires every edge endpoint to resolve to a current item record. Active/hypothesis/bounded `contradicts` edges are hard failures until resolved, rejected, or superseded.

## Proof-level discipline

Use the lowest accurate proof level. Valid proof levels are:

- `none`: no usable evidence yet; normally only for generated drafts or explicit placeholders.
- `source-anchor`: PRD/GSD/ADR/source anchor supports the statement, but runtime behavior is not proven.
- `static-check`: schema, graph integrity, or another static validation supports the claim.
- `unit-test`: focused tests cover the behavior or invariant.
- `integration-test`: multiple implemented components were exercised together.
- `runtime-smoke`: a concrete runtime smoke test was executed.
- `real-document-proof`: representative legal documents or evidence units were processed successfully.
- `production-observation`: observed production behavior supports the claim.

For M017 ontology research, `source-anchor` is the default ceiling for literature-backed or PRD-backed mapping candidates. Do not use `validated`, `runtime-smoke`, `real-document-proof`, or `production-observation` for ontology, parser, retrieval, generated-Cypher, legal-answer, FalkorDB production-scale, or LLM-authority claims unless the corresponding deterministic/runtime/real-document evidence exists and is anchored.

## Source-anchor requirements

Every non-generated draft record must have at least one `source_anchors` entry. A source anchor must use a repository-relative `path` and `kind`; allowed kinds are `prd`, `gsd-requirement`, `gsd-decision`, `gsd-summary`, `source-code`, `runtime-artifact`, `test-artifact`, `external-reference`, and `manual-note`.

Source anchors must be safe and inspectable:

- No absolute paths.
- No traversal outside the repository.
- No `.gsd/exec` local-only artifacts.
- Anchored files must exist and be readable.
- Line ranges must be bounded and within the file.
- `selector` or `section` text must still appear in the anchored file.
- Do not store raw legal text or secrets; optional `quote_hash` may identify a short supporting quote.

## Generator workflow constraints

Any registry integration for M017 must go through the generator workflow rather than manual JSONL/report edits:

1. Update authoritative source evidence first: M017 research note, GSD requirement/decision/summary, ADR, source, runtime smoke, or proof artifact.
2. Update the curated extractor mapping in `scripts/extract-prd-architecture-items.py` only when the source evidence and anchor are known.
3. Regenerate derived JSONL with `uv run python scripts/extract-prd-architecture-items.py`.
4. Rebuild graph views with `uv run python scripts/build-architecture-graph.py`.
5. Run the canonical verifier with `uv run python scripts/verify-architecture-graph.py` before claiming the registry/graph/report/router guidance is current.

Default-path verifier success means only that derived artifacts satisfy current static registry, graph, source-anchor, decision-fitness, and claim-safety rules. It does not validate product readiness, runtime behavior, parser completeness, retrieval quality, legal-answer correctness, generated-Cypher safety, FalkorDB production scale, or LLM authority.

## M017 integration guardrails

M017 ontology intake can safely prepare registry mapping candidates only if each candidate identifies:

- the authoritative source file and stable source anchor;
- whether the record is an `item` or `edge`;
- the intended item/edge type and architecture layer;
- status and lowest earned proof level;
- explicit `non_claims` for all tempting overclaims; and
- the owner/verification condition for any open proof gate.

Until those fields are available, integration should be deferred as a source-mapping plan rather than emitted into the registry. This is especially important for ontology framework adoption, external standard alignment, Russian legal evidence modeling, GraphRAG/retrieval claims, and any claim that could be mistaken for runtime or legal validation.
