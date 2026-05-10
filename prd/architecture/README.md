# Architecture registry contract

This directory defines the LegalGraph Nexus architecture registry contract for M004 and later slices. The registry is a git-tracked, machine-readable projection of architecture knowledge; it is not itself the architecture source of truth.

## Source-of-truth boundary

Authoritative claims remain in the source documents and evidence artifacts that the registry anchors to:

- PRD and research notes under `prd/`, especially `prd/09_architecture_planning_verification_research.md`.
- GSD requirements, decisions, plans, summaries, and validation artifacts.
- Source code, tests, runtime smoke artifacts, and real-document proof artifacts when a claim requires implementation or runtime evidence.
- External references only when recorded as explicit `external-reference` anchors; they do not override local PRD/GSD decisions.

Registry records in JSONL form are derived projections for graph analysis, coverage checks, generated views, and architecture fitness functions. Generated graph exports, Markdown reports, GraphML files, diagrams, and later skill/router guidance are downstream artifacts. They must be rebuilt or checked from the registry and its anchors, never hand-edited into authority over PRD/GSD/ADR evidence.

## End-to-end architecture verification workflow

Use this lifecycle whenever an agent changes architecture claims, architecture registry mappings, graph/report logic, verifier policy, or project guidance that summarizes architecture state:

1. **Update source evidence first.** The source of truth is the PRD/GSD/ADR/source/runtime evidence listed above. Do not make the JSONL registry, NetworkX report, verifier summary, or router skill the authority for a claim that lacks anchored source evidence.
2. **Regenerate the conservative JSONL projection.** Run:

   ```bash
   uv run python scripts/extract-prd-architecture-items.py
   ```

   This emits `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_edges.jsonl` from curated mappings only. Treat both files as derived, non-authoritative projections. If a row is stale or wrong, fix the source anchor or extractor mapping and regenerate; do not hand-edit JSONL to make a claim appear current.
3. **Rebuild the derived NetworkX views.** Run:

   ```bash
   uv run python scripts/build-architecture-graph.py
   ```

   This consumes the JSONL registry and rewrites `prd/architecture/architecture_graph_report.json` plus `prd/architecture/architecture_report.md`. These reports diagnose coverage, graph integrity, unresolved gates, contradictions, risk concentration, and overclaim boundaries, but they remain derived views.
4. **Verify before claiming currency.** Run the canonical verifier:

   ```bash
   uv run python scripts/verify-architecture-graph.py
   ```

   On default paths the verifier first runs the extractor and graph builder freshness gates in read-only mode:

   ```bash
   uv run python scripts/extract-prd-architecture-items.py --check
   uv run python scripts/build-architecture-graph.py --check
   ```

   A passing verifier means the derived artifacts satisfy the current static registry, graph, source-anchor, decision-fitness, and claim-safety rules. It does not validate product readiness, runtime behavior, parser completeness, retrieval quality, legal-answer correctness, generated-Cypher safety, FalkorDB production scale, or LLM authority.

Agents must run `uv run python scripts/verify-architecture-graph.py` before saying the architecture registry, graph report, verifier policy, or router guidance is current. For narrow checks, `--check` on the extractor or graph builder is acceptable only when the claim is limited to that layer's freshness. For tests or fixtures that pass custom `--items`, `--edges`, `--report-json`, or `--report-md` paths, remember that upstream freshness checks are intentionally skipped; do not use custom-path verifier success as evidence that the tracked project architecture is current.

### Failure classes and remediation hints

The expected verifier failures are meant to be actionable and should include rule, record ID, field, path, and source-anchor context where available:

- **Extractor freshness drift:** `extract-prd-architecture-items.py --check` reports that generated JSONL differs from the extractor output. Remediate by regenerating the JSONL after confirming the curated source mapping is correct.
- **Graph/report freshness drift:** `build-architecture-graph.py --check` reports stale JSON or Markdown reports. Remediate by rebuilding the graph reports from current JSONL.
- **Malformed or invalid JSONL:** malformed lines, wrong `record_kind`, duplicate IDs, missing required fields, enum violations, or invalid path/date/identifier shapes fail deterministically. Remediate the extractor mapping, schema-aware fixture, or source record that produced the bad row, then regenerate.
- **Unsafe or stale source anchors:** absolute paths, ignored local-only paths, missing files, unbounded line ranges, or selectors/sections that no longer appear in the source fail. Remediate by updating the authoritative source document or the repository-relative anchor.
- **Graph integrity failures:** missing edge endpoints, orphan traceability-critical records, unresolved active contradictions, and unresolved proof-gate metadata gaps fail when they would make the registry misleading. Remediate by adding anchored relationships, resolving/superseding contradictions, or documenting owner/status/verification metadata.
- **Decision fitness failures:** active decisions without consequences, superseded decisions without successor coverage, or high/critical active decisions lacking `checked_by`/`validated_by` proof-gate coverage fail. Remediate in the source decision evidence and regenerate the registry.
- **Positive overclaim failures:** generated artifacts or policy prose that assert unproven runtime, Legal KnowQL parser, ODT/parser completeness, retrieval-quality, FalkorDB production-scale, generated-Cypher safety, legal-answer correctness, or LLM-authority claims fail. Remediate by downgrading to source-anchored boundary language or adding the required deterministic/runtime/real-document proof before raising the claim.

Negative boundary language such as “derived,” “non-authoritative,” “does not validate,” and “must not be used as legal authority” is part of the claim-safety contract, not an overclaim.

## S02 extractor contract

The canonical S02 extractor is `scripts/extract-prd-architecture-items.py`. Run it from the repository root to regenerate the tracked projection files:

```bash
uv run python scripts/extract-prd-architecture-items.py
```

The canonical freshness check is:

```bash
uv run python scripts/extract-prd-architecture-items.py --check
```

The extractor owns these generated JSONL projections:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`

These files are derived, non-authoritative projections over PRD, GSD, ADR, source, and smoke/proof evidence. They are stable inputs for later automation, but they do not replace the documents and artifacts named in each record's source anchors. If generated JSONL disagrees with anchored source evidence, update the source mapping or regenerate the projection; do not treat the generated row as source truth.

S02 extraction is deliberately conservative:

- Records come from curated mappings only; the extractor does not infer architecture truth from broad Markdown scans.
- Every generated record must retain repository-relative source anchors that allow a future agent to inspect the claim source.
- S02 must not emit generated `validated` status. Existing validated GSD material is projected as anchored active or hypothesis architecture context until a later verifier earns stronger proof.
- `non_claims` must be preserved so runtime, legal-answer, parser-completeness, retrieval-quality, managed-API, production-scale, and LLM-authority overclaims stay explicit.
- Agents must use `--check` to detect stale generated files instead of bypassing the extractor or hand-editing the JSONL output.

Downstream ownership is separate from this extractor contract. S03/S04 may consume these files to build graph integrity and verification checks, promote only evidence-backed proof levels, and diagnose stale or unsafe records. S05 may create the architecture-verification workflow/router skill after those verifier checks exist. S02 must not create that router skill or final workflow handoff content.

## S03 graph-report contract

The canonical S03 graph/report generator is `scripts/build-architecture-graph.py`. Run it from the repository root after S02 JSONL projection files are current:

```bash
uv run python scripts/build-architecture-graph.py
```

The canonical read-only freshness and consistency check is:

```bash
uv run python scripts/build-architecture-graph.py --check
```

The graph/report layer consumes the S02 JSONL registry as generated input and writes these derived views:

- `prd/architecture/architecture_graph_report.json`
- `prd/architecture/architecture_report.md`

These JSON and Markdown reports are derived, non-authoritative views over the JSONL registry and its anchors. The JSONL registry, JSON report, Markdown report, diagrams, and optional future GraphML exports must not be treated as source truth, legal proof, product/runtime validation, or replacements for PRD/GSD/ADR/source/runtime evidence. If a graph report disagrees with anchored evidence, fix the source mapping or graph rule and regenerate the report; do not hand-edit a derived view to make the evidence fit.

S03 exposes graph health signals for maintainers and later verifier slices:

- layer coverage and missing architecture layers;
- unresolved proof gates;
- orphan or isolated records;
- explicit contradiction edges;
- high-risk or critical records;
- non-claim boundaries that prevent runtime, parser, retrieval, legal-answer, and LLM-authority overclaims.

Those findings are diagnostic handoff inputs, not automatic validation outcomes. R029 requires an architecture-verification workflow/router skill with testable, evidence-backed checks; S03 advances that requirement by producing deterministic graph inputs and report surfaces, but it does not fully validate R029. S04 owns the decision and tests for which unresolved gates, orphan records, contradiction edges, report mismatches, or high-risk rows become hard architecture-verifier failures under R029. S05 may then package the verified workflow/router handoff after those hard-failure rules exist.

A future agent should interpret `--check` failures as stale or inconsistent generated artifacts. A successful `--check` only proves the report is current with the present registry and graph rules; it does not prove product readiness, runtime behavior, legal correctness, parser completeness, retrieval quality, or LLM authority.

## S04 verifier contract

The canonical S04 verifier is `scripts/verify-architecture-graph.py`. Run it from the repository root after the S02/S03 generated outputs are expected to be current:

```bash
uv run python scripts/verify-architecture-graph.py
```

The verifier is read-only. On default paths it first composes these freshness gates before applying S04 policy checks:

```bash
uv run python scripts/extract-prd-architecture-items.py --check
uv run python scripts/build-architecture-graph.py --check
```

Verifier output is derived and non-authoritative. Its compact JSON summary includes `non_authoritative=true`, and hard failures are deterministic diagnostics intended to identify stale upstream artifacts, malformed JSONL, duplicate IDs, wrong record kinds, missing report outputs, and R029 decision/claim-safety drift categories. A passing verifier run means the derived artifacts satisfy the current verifier rules; it does not validate product readiness, runtime behavior, legal correctness, parser completeness, retrieval quality, generated-Cypher safety, or LLM authority.

The current hard-failure policy is intentionally fail-closed and deterministic:

- Upstream freshness drift: default-path verifier runs compose S02 `--check` and S03 `--check` before local policy checks.
- Schema/shape errors: malformed JSONL, wrong record kinds, duplicate IDs, missing required schema fields, unknown fields, enum violations, and invalid date/identifier/path shapes fail with record ID and field context.
- Stale or unsafe anchors: source anchors must be repository-relative, outside `.gsd/exec`, readable, line-range bounded, and selector/section text must still appear in the anchored file.
- Missing endpoints: every edge endpoint must resolve to a current item record.
- Orphan traceability-critical records: active requirement, decision, and proof-gate records must have meaningful graph connectivity unless explicitly exempted by status or generated-draft state.
- Unresolved proof-gate metadata gaps: active proof gates with `proof_level=none` must retain owner, status, verification, and source-anchor context.
- Decision fitness failures: active decisions need consequences; superseded decisions need successor coverage; high/critical active decisions need `checked_by` or `validated_by` proof-gate/workflow-check coverage.
- Active contradictions: active, hypothesis, or bounded-evidence `contradicts` edges must be resolved, rejected, or superseded before the verifier passes.
- Forbidden positive overclaims: verifier prose scanning rejects promotional upgrades that assert unproven LegalGraph product readiness, Legal KnowQL runtime/parser proof, ODT/parser completeness, retrieval-quality proof, FalkorDB production scale, generated-Cypher safety, legal-answer correctness, or LLM authority.

Negative boundary language is allowed and expected. Wording such as “does not validate product/runtime/legal claims,” “must not be used as legal authority,” and `non_claims` entries is a guardrail, not an overclaim. The overclaim scanner is limited to prose claim fields and derived Markdown/policy text; it intentionally avoids treating `non_claims` as positive assertions.

S05 workflow integration should package this command as the project-local architecture verification handoff for future agents. S05 should reference this README, `scripts/verify-architecture-graph.py`, and `tests/test_architecture_verifier.py`; it should not duplicate registry truth or weaken the non-authoritative boundary.

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
