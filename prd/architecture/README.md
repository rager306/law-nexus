# Architecture registry contract

This directory defines the LegalGraph Nexus architecture registry contract for M004 and later slices. The registry is a git-tracked, machine-readable projection of architecture knowledge; it is not itself the architecture source of truth.

## Source-of-truth boundary

Authoritative claims remain in the source documents and evidence artifacts that the registry anchors to:

- PRD and research notes under `prd/`, especially `prd/09_architecture_planning_verification_research.md`.
- GSD requirements, decisions, plans, summaries, and validation artifacts.
- Source code, tests, runtime smoke artifacts, and real-document proof artifacts when a claim requires implementation or runtime evidence.
- External references only when recorded as explicit `external-reference` anchors; they do not override local PRD/GSD decisions.

Registry records in JSONL form are derived projections for graph analysis, coverage checks, generated views, and architecture fitness functions. Generated graph exports, Markdown reports, GraphML files, diagrams, and later skill/router guidance are downstream artifacts. They must be rebuilt or checked from the registry and its anchors, never hand-edited into authority over PRD/GSD/ADR evidence.

## Record boundary

`architecture.schema.json` validates one record at a time using `record_kind`:

- `item` records describe requirements, decisions, assumptions, risks, proof gates, components, interfaces, data entities, quality scenarios, viewpoints, evidence, and workflow checks.
- `edge` records describe typed relationships such as `satisfies`, `depends_on`, `validated_by`, `bounded_by`, `checked_by`, `has_consequence`, `has_assumption`, `governs_artifact`, and supersession links.

Every non-generated draft record must include at least one repository-relative `source_anchors` entry. `generated_draft: true` is allowed only for provisional extraction output that still needs anchoring and review before downstream graph conclusions rely on it.

## ADR-derived decision metadata

Decision items are first-class architecture records, not comments attached to components. A decision item must carry ADR-style metadata sufficient for later traceability and review:

- `deciders`, `decision_drivers`, and `considered_options` identify who/what shaped the decision and what alternatives were evaluated.
- `positive_consequences` and/or `negative_consequences` capture why the decision matters operationally.
- `assumptions`, `constraints`, `implications`, `related_requirements`, `related_decisions`, and `governed_artifacts` preserve graphable decision context.
- `last_reviewed`, `review_due`, `superseded_by`, and explicit supersession edges keep living decision state separate from immutable historical ADR evidence.

Accepted or active decisions must not be consequence-free. Superseded decisions must name and link to a successor. High-risk and critical decisions must be covered by a `checked_by` or `validated_by` proof gate edge so that decision fitness can be evaluated as code or by a documented manual gate.

## Proof levels and claim discipline

`proof_level` is the highest support level currently earned by the record, not an aspiration. Use the lowest accurate value:

- `none`: no usable evidence yet; normally only acceptable for generated drafts or explicit placeholders.
- `source-anchor`: a PRD/GSD/ADR/source anchor supports the statement, but runtime behavior is not proven.
- `static-check`: schema, graph integrity, or other static validation supports the claim.
- `unit-test`: focused tests cover the behavior or invariant.
- `integration-test`: multiple implemented components were exercised together.
- `runtime-smoke`: a concrete runtime smoke test was executed.
- `real-document-proof`: representative legal documents or evidence units were processed successfully.
- `production-observation`: observed production behavior supports the claim.

Do not mark FalkorDB, GraphBLAS, vector/full-text, UDF, ODT/parser, retrieval, generated-Cypher, temporal-validity, legal-answer, or LLM-authority claims as `validated` unless the proof level and anchors match the risk. LLM-generated or generated-Cypher records remain proposals/drafts until deterministic validation and evidence gates accept them.

## Derived artifacts and fitness functions

Future slices may build NetworkX graphs, GraphML exports, Markdown architecture reports, diagrams, or project-local skills from these records. Those outputs are derived and non-authoritative. They are useful for finding gaps and contradictions, but if they disagree with anchored PRD/GSD/ADR/source evidence, the source evidence wins and the derived artifact must be regenerated or fixed.

Architecture fitness functions should be split by purpose:

- Schema fitness: record shape, enum values, required fields, relative paths, and generated-draft anchor rules.
- Graph integrity fitness: edge endpoints, orphan records, supersession paths, contradiction resolution, and layer coverage.
- Decision fitness: ADR metadata completeness, consequences, review state, high-risk proof gates, and governed-artifact traceability.
- Claim-safety fitness: no over-upgraded legal/runtime/parser/retrieval/LLM claims without matching proof level and anchors.

## Expected validator failure classes

Validator failures must be diagnostic enough for another agent to fix the exact record. Error output should include record ID, record kind/type where available, field, rule, and source anchor where available.

Current expected classes include:

- Missing source anchor: non-generated records with empty or absent `source_anchors` should fail with the record ID, `field=source_anchors`, the min-items/required rule, and `<no-source-anchor>` when no anchor exists.
- Decision without consequences: active decision records should fail when neither `positive_consequences` nor `negative_consequences` is present.
- Superseded decision without successor coverage: superseded decision records should fail when `superseded_by` is absent or no active `supersedes`/`superseded_by` edge connects the old and successor decisions.
- High-risk decision without a proof gate: high or critical decision records should fail unless an active, validated, or hypothesis `checked_by`/`validated_by` edge points from the decision to a proof gate or workflow check.
- Generated artifact overclaim: generated graph/report/diagram/skill outputs should fail claim-safety checks if they assert authority beyond the anchored registry evidence.
- Stale or unsafe anchors: source anchors should fail when they use absolute paths, ignored local-only paths, missing files, unstable selectors, or anchors that no longer support the record claim.

When adding new fixtures or verifier rules, preserve these diagnostic fields so schema/test failures remain actionable during auto-mode execution.
