# Architecture registry contract

This directory defines the LegalGraph Nexus architecture registry contract for M004 and later slices. The registry is a git-tracked, machine-readable projection of architecture knowledge; it is not itself the architecture source of truth.

## Three derived views

Three human-readable views are generated from the registry and graph:

| View | Purpose | Run to generate |
|---|---|---|
| `architecture_health.md` | Architecture registry health: coverage, gates, risk, non-claims, orphans | `python scripts/generate-architecture-views.py` |
| `product_readiness_blockers.md` | Next proof work by capability area: active gates, blocked evidence, non-claims | `python scripts/generate-architecture-views.py` |
| `claims_ledger.md` | Claim safety classifications: safe-to-say, bounded, blocked, unsafe-to-assert | `python scripts/generate-architecture-views.py` |

All three views are derived, non-authoritative planning artifacts. Source-of-truth remains with PRD, GSD, ADR, and source anchor evidence.

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

## Validator priority taxonomy

The architecture validator preserves every GSD-derived validator idea, but it must separate implementation urgency from long-term usefulness. Use this priority taxonomy when adding verifier rules, generated-view fields, architecture drift diagnostics, or backlog entries:

| Priority | Meaning | Project importance | Implementation priority | Diagnostic wording |
|---|---|---|---|---|
| `P0` | Critical safety gate | Prevents false authority, unsafe claim promotion, or loss of source-truth boundaries. | Implement as a hard verifier failure before relying on the affected architecture claim. | `critical-gate` |
| `P1` | High-priority blocker | Protects R035/R029 proof boundaries or blocks validated architecture status when evidence is missing. | Implement as a hard verifier failure in the owning slice before promotion is allowed. | `high-priority-blocker` |
| `P2` | Medium diagnostic | Detects drift, stale generated artifacts, or remediation needs without changing authoritative sources. | Implement after P0/P1 gates; report actionable diagnostics without auto-repair. | `medium-diagnostic` |
| `P3` | Backlog-only signal | Useful future validator or reporting idea with no current milestone-blocking proof obligation. | Preserve with trigger conditions and proof requirements; do not fail the verifier until promoted by a future decision. | `backlog-only-signal` |

Diagnostics that reference this taxonomy should also name the lifecycle status and remediation class. The minimum diagnostic shape is: record or artifact ID, `priority`, lifecycle status, failure class, remediation class, and source anchor when available. Do not emit raw legal text, credentials, provider bodies, or local-only `.gsd/exec` paths.

### Claim lifecycle statuses

Architecture claims and validator ideas move through an append-only lifecycle. Later evidence may supersede, reject, or promote a record; it must not silently rewrite earlier evidence.

| Lifecycle status | Use when | Promotion rule |
|---|---|---|
| `proposed` | A useful idea or architecture claim exists, but no sufficient source mapping or proof gate exists yet. | May be preserved as `P2` or `P3`; cannot be asserted as validated architecture. |
| `bounded` | Evidence exists, but only within a stated scope such as source-anchor, static-check, runtime-smoke, or real-document proof. | May be cited with scope caveats; promotion requires matching proof level, source anchors, and gate coverage. |
| `blocked` | A claim or idea is strategically relevant but missing required evidence, owner, source mapping, or proof gate. | Must remain `P0`/`P1` failure or blocker until the missing evidence is added and verified. |
| `deferred` | The idea is valuable but intentionally out of current milestone scope. | Preserve as `P3` backlog with trigger/proof metadata; do not fail the verifier. |
| `validated` | Deterministic checks and required evidence support the claim at the stated proof level. | May be asserted only within the proof scope and non-claim boundary. |
| `rejected` or `superseded` | Later evidence invalidates or replaces the claim. | Keep traceability to the successor or rejection rationale; do not delete the old record. |

### Claim lifecycle invariants

Lifecycle status is not a cosmetic label. Validator policy must preserve these invariants whenever a registry row, edge, generated view, or future workflow check relies on a claim as proof:

- **Validated claims are append-only.** A `validated` record must have earned at least static or executable proof (`static-check`, `unit-test`, `integration-test`, `runtime-smoke`, `real-document-proof`, or `production-observation`). Later changes must supersede, reject, or add new evidence instead of silently downgrading or rewriting the validated claim in place.
- **Proposed and bounded ideas remain preservable.** `proposed`, `hypothesis`, `bounded-evidence`, and `blocked` records may stay in the registry when they are explicitly scoped and do not masquerade as validated architecture.
- **Deferred and rejected records are not proof.** Active proof-carrying edges such as `satisfies`, `evidenced_by`, `validated_by`, `checked_by`, or `bounded_by` must not use records in `deferred` or `rejected` status as positive support. Remediate by superseding the edge, rejecting it, or downgrading the dependent claim.
- **Diagnostics must name the lifecycle failure.** Lifecycle failures should include the record ID, current status, forbidden transition or proof use, and remediation class so another agent can repair the exact source mapping without promoting evidence automatically.

### Remediation classes

Use remediation classes to keep failures actionable without letting diagnostics mutate source truth:

| Remediation class | Safe action |
|---|---|
| `regenerate-derived-artifact` | Re-run the extractor, graph builder, or generated-view command when a derived artifact is stale. |
| `add-source-anchor` | Add or correct repository-relative source anchors in the authoritative source mapping. |
| `add-evidence-class` | Record the earned proof level and bounded evidence class before promotion. |
| `add-proof-gate` | Link the claim or decision to a proof gate or workflow check that can validate it. |
| `downgrade-claim` | Reword or reclassify positive overclaims into bounded, proposed, blocked, or non-claim language. |
| `defer-to-backlog` | Preserve a non-blocking future idea with trigger conditions and proof requirements. |

### Validator idea inventory

The current M018/D047-D048-derived inventory is classified as follows:

| Validator idea | Priority | Lifecycle status | Why it matters | Implementation priority / owner slice |
|---|---|---|---|---|
| Keep the registry derived from PRD/GSD/ADR/source/runtime anchors rather than prose authority. | `P0` | `validated` for current source-truth policy; still continuously checked. | Prevents generated reports, skills, or summaries from becoming authoritative proof. | Existing verifier/readme contract; preserve in every slice. |
| Make validated architecture claims append-only through supersession, rejection, or new evidence rather than silent rewrite. | `P0` | `blocked` until lifecycle transition rules are executable. | Protects auditability of architecture claims and decisions. | S01 defines; later S01/S02 verifier work enforces. |
| Require source mapping, evidence class, proof gate, and verifier coverage before promotion to architecture. | `P0` | `blocked` until all required gates exist. | Prevents R035 and future research claims from being promoted on aspiration alone. | S01 taxonomy plus S02/S03 enforcement. |
| Convert prompt-only guardrails that protect R035 into executable verifier checks. | `P0` | `blocked` until hard checks exist. | Critical ontology/external-standard boundaries must not depend on agent memory. | S02/S03 hard gates. |
| Enforce status and proof-level transition rules. | `P1` | `proposed` in this taxonomy; pending executable tests. | Keeps `validated`, `bounded`, `blocked`, and `deferred` from being used interchangeably. | S01/S02. |
| Harden source-anchor and evidence-class distinctions. | `P1` | `blocked` until unsafe anchors and evidence misuse fail deterministically. | Required for credible source-traceable architecture validation. | S02. |
| Add R035 ontology and external-standard promotion gates. | `P1` | `blocked` until bounded evidence, proof gates, and source mappings are present. | R035 remains active and must protect Akoma Ntoso, FRBR, LKIF, RusLegalCore, BFO, GOST, OWL, Common Logic, graph-vector, and pilot-scale claims. | S03. |
| Detect unsafe positive overclaims across generated views and guidance. | `P1` | `bounded` by existing S04 overclaim scanning; extend only with evidence. | Prevents runtime, parser, retrieval, legal-answer, FalkorDB-scale, generated-Cypher, and LLM-authority overclaims. | Existing verifier plus S02/S03 refinements. |
| Add typed architecture drift diagnostics following derive, detect, repair-or-block, re-derive. | `P2` | `proposed` diagnostics-only. | Helps future agents remediate stale or inconsistent architecture projections without changing sources automatically. | S04. |
| Produce actionable remediation classes without auto-promoting evidence. | `P2` | `proposed` diagnostics-only. | Makes failures fixable while preserving source-of-truth boundaries. | S04. |
| Limit deterministic repair to generated projection freshness where safe. | `P2` | `deferred` unless a future slice explicitly implements repair. | Avoids accidental edits to PRD/GSD/ADR/source evidence. | S04 diagnostics only; no automatic source repair. |
| Preserve code import-boundary checks, richer graph visualization, live activation telemetry, interactive dashboards, and cross-repo architecture comparisons. | `P3` | `deferred` backlog-only. | These ideas may be useful later but are not required for current R035 proof safety. | S06 backlog; no verifier failure until promoted by a future decision. |

### R035 ontology and external-standard promotion gates

R035-triggered ontology or external-standard claims may remain in the registry as `proposed`, `hypothesis`, `bounded-evidence`, `blocked`, or `deferred` research only when the claim text keeps non-authoritative boundary language such as `candidate`, `bounded`, `proof-gated`, `does not prove`, or `does not validate`. A trigger-matched claim may reach `validated` only after the architecture verifier can see all of the following on the same record:

- bounded source mapping through a repository-relative source anchor with a selector, section, or explicit line range;
- owner and status metadata on the promoted claim;
- an outgoing `checked_by`, `validated_by`, or `bounded_by` edge to the required proof gate or workflow check;
- a proof level at or above the rule-specific minimum proof level; and
- evidence classes that satisfy the general proof-level boundary rules.

| R035 trigger terms | Current safe bucket | Required promotion gate | Minimum validated proof level |
|---|---|---|---|
| Akoma Ntoso, LegalDocML, FRBR | Compatibility/reference projection only | `GATE-AKOMA-FRBR-NORMALIZATION` | `static-check` |
| LKIF, deontic mapping | Proof-gated candidate | `GATE-LKIF-DEONTIC-BENCHMARK` | `unit-test` |
| RusLegalCore | Proof-gated domain-scope candidate | `GATE-RUSLEGALCORE-SCOPE` | `static-check` |
| BFO, GOST, GOST R 59798-2021, OWL, OWL 2, Common Logic | Deferred formal-alignment review | `GATE-BFO-GOST-ALIGNMENT` | `static-check` |
| Ontology GraphRAG, ontology-aware GraphRAG, ontology-driven GraphRAG | Proof-gated integration candidate | `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | `integration-test` |
| graph-vector, HNSW, hybrid retrieval | Deferred runtime behavior claim | `GATE-G015` or `GATE-ONTOLOGY-GRAPHRAG-INTEGRATION` | `runtime-smoke` |
| pilot-scale, 1000-document, 1,000-document | Deferred readiness proof | `GATE-PILOT-SCALE-READINESS` | `integration-test` |

Verifier diagnostics for this gate use `rule=ontology-promotion-gate` and name the matched `r035_trigger`, the ontology rule, the missing source mapping, proof gate, owner, status, or proof-level requirement, plus a remediation class.

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

### Typed drift diagnostics

Verifier hard failures include a stable `drift_kind`, affected record ID, affected field, source-anchor context, safe remediation hint, and `safe_to_regenerate` flag. These diagnostics are read-only triage signals: only freshness failures for derived projections are marked safe to fix by regeneration, while source-truth changes require explicit source-evidence edits.

| Drift kind | Typical rules | Safe remediation boundary |
|---|---|---|
| `freshness-drift` | Upstream extractor/report `--check` failures and missing derived reports | Regenerate derived projection artifacts after confirming source evidence is current. |
| `source-anchor-drift` | Unsafe paths, missing anchor files, unbounded/stale selector anchors, source-anchor schema gaps | Edit repository-relative source anchors or authoritative source evidence; then regenerate projections. |
| `graph-integrity-drift` | Malformed JSONL, duplicate IDs, wrong record kinds, schema shape errors, missing endpoints, orphan traceability records | Fix schema or graph source mapping; do not hand-edit generated truth into existence. |
| `decision-fitness-drift` | Missing decision consequences, supersession coverage, or proof-gate coverage for high-risk decisions | Update source decision evidence and its proof-gate/workflow-check links. |
| `proof-gate-drift` | Unresolved proof-gate metadata, evidence-class mismatch, unsafe lifecycle promotion, ontology promotion gaps | Add earned proof evidence, owner/gate metadata, or downgrade the claim in source evidence. |
| `contradiction-drift` | Active/hypothesis/bounded `contradicts` edges | Resolve, reject, or supersede the contradiction in source evidence. |
| `overclaim-drift` | Positive unproven product/runtime/parser/retrieval/legal/FalkorDB/Cypher/LLM authority claims | Downgrade to bounded non-authoritative language or add required proof before promotion. |

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

## Minimal GSD validation report contract

GSD milestone validation may cite the architecture verifier and generated views only as derived evidence that the registry projection is current, claim-safe, and actionable for planning. The generated report surface must stay compact and non-authoritative: it is a validation handoff, not a dashboard, interactive graph UI, or broad visualization project.

The minimal report fields are:

| Field family | Required surface | Purpose for GSD validation | Non-authoritative boundary |
|---|---|---|---|
| Priority buckets | Counts and short lists for `P0`, `P1`, `P2`, and `P3` validator findings when available. | Let validation distinguish critical safety gates and high-priority blockers from diagnostics and backlog-only ideas. | Priority is triage metadata; it does not promote a claim or prove product readiness. |
| Promotion blockers | Open proof gates, blocked/open claim classifications, missing source anchors, missing proof gates, missing owner/status, and evidence-class mismatches. | Show what prevents a claim from being cited as validated architecture. | Blocker rows are repair guidance only; source evidence must be updated before promotion. |
| Typed drift classes | Compact counts and actionable rows keyed by `freshness-drift`, `source-anchor-drift`, `graph-integrity-drift`, `decision-fitness-drift`, `proof-gate-drift`, `contradiction-drift`, and `overclaim-drift`. | Let GSD validation identify whether the safe next action is regeneration, source-anchor repair, proof-gate work, contradiction resolution, or claim downgrade. | Only drift explicitly marked safe to regenerate may be fixed by rebuilding derived artifacts; all source-truth changes require authoritative evidence edits. |
| R035 gate status | Trigger term, current safe bucket, required promotion gate, minimum validated proof level, missing requirement(s), and remediation class for ontology/external-standard claims. | Keep ontology, external-standard, graph-vector, and pilot-scale claims from being promoted without the required gate and proof level. | R035 rows are guardrails around assertion safety; they do not validate Akoma Ntoso, LKIF, RusLegalCore, BFO/GOST/OWL/Common Logic, GraphRAG, graph-vector, or pilot-scale behavior by themselves. |
| Claim-safety buckets | Counts and short lists for `safe-to-say`, `bounded`, `blocked/open`, `unsafe-to-assert`, plus non-claims. | Give future agents a concise cite/do-not-cite handoff. | Even `safe-to-say` records must be cited with source anchors and proof scope; generated reports remain derived planning artifacts. |

Generated view ownership stays split:

- `architecture_health.md` should show global counts, typed drift counts, open proof gates, high/critical risks, non-claims, and later priority bucket summaries.
- `product_readiness_blockers.md` should show promotion blockers by capability area, including proof-gate status and next proof work.
- `claims_ledger.md` should show claim-safety buckets and, when implemented, the R035 gate status needed before ontology or external-standard claims can move out of bounded/proposed/deferred language.

Do not add raw legal text, provider payloads, credentials, local-only `.gsd/exec` paths, live telemetry dashboards, graph exploration widgets, or product-readiness assertions to these reports. Milestone validation should cite `uv run python scripts/verify-architecture-graph.py` for currentness proof and then use the generated views only to explain what is current, blocked, deferred, and unsafe to assert.

## Architecture Health Dashboard

The architecture health dashboard (`prd/architecture/architecture_health.md`) is a compact human-readable snapshot of architecture registry health derived from `prd/architecture/architecture_graph_report.json`. It is a **decision-support view, not proof or source truth**.

### What it shows

- **Quick Stats** — total nodes, edges, schema layers, missing layers, unresolved proof gates, orphan findings, contradiction edges, high/critical risk node counts, and non-claim tallies.
- **Layer Coverage** — which schema layers have architecture records and which are missing entirely.
- **Open Proof Gates** — unresolved gates with owner, risk level, and verification description.
- **High-Risk Nodes** — high/critical risk nodes with their type, layer, status, and current proof level.
- **Non-Authoritative Boundary** — the exhaustive list of claims this registry does **not** make (runtime proof, legal authority, parser completeness, etc.).
- **Orphan Findings** — nodes with no graph connectivity.
- **Weakly Connected Components** — graph fragment sizes indicating isolated record clusters.

### How to run it

The dashboard is generated by `scripts/generate-architecture-views.py`, which reads `architecture_graph_report.json` (the S03 output):

```bash
uv run python scripts/generate-architecture-views.py
```

This writes `prd/architecture/architecture_health.md`. The canonical freshness check is:

```bash
uv run python scripts/generate-architecture-views.py --check
```

### Interpretation rules

- **Missing layers** mean there are no architecture records for those schema layers — not that the product lacks those capabilities, only that they are not yet registered.
- **Unresolved proof gates** are known gaps in evidence; they are reported for visibility and planning, not automatically failed by the dashboard.
- **High/critical risk nodes** are flagged for attention; they do not indicate current product failure.
- **Non-authoritative boundary rows** enumerate every claim the registry explicitly does not make. Reading them helps future agents avoid over-claiming.
- **Orphan findings** are records with no graph edges — they may need relationships or may be intentionally isolated placeholders.
- **Weakly connected components** with small sizes may indicate records that should be connected to the main graph.

### Decision-support, not authority

`architecture_health.md` is a derived, non-authoritative projection. It does not:
- Prove product runtime behavior
- Validate legal-answer correctness
- Establish FalkorDB production-scale readiness
- Confer LLM authority on any claim
- Replace PRD, GSD, ADR, or source anchor evidence

Before acting on dashboard findings, verify against the source anchors recorded in `architecture_items.jsonl` and `architecture_edges.jsonl`.

## Product Readiness Blockers Report

The product readiness blockers report (`prd/architecture/product_readiness_blockers.md`) is a planning artifact that maps active proof gates, blocked evidence, and non-claims to the six capability areas required for LegalGraph Nexus product readiness.

### What it shows

- **Per-area proof gates** — active gates that block product-readiness claims, with risk level, verification description, and owner.
- **Blocked/bounded evidence** — evidence items that carry restrictions or caveats tied to proof gates.
- **Non-claims** — explicit statements of what each area does NOT validate (e.g., "No parser completeness claim", "No production-scale FalkorDB claim").
- **Next proof work** — actionable items that unblock the gate.

The six capability areas covered are: ETL/Parser, Graph Runtime, Legal Answering, Legal KnowQL/Generated Cypher, Retrieval/Embedding, and Temporal Model.

### How to run it

The blockers report is generated by `scripts/generate-architecture-views.py`, which reads `prd/architecture/architecture_graph_report.json`:

```bash
uv run python scripts/generate-architecture-views.py
```

This writes `prd/architecture/product_readiness_blockers.md`. The canonical freshness check is:

```bash
uv run python scripts/generate-architecture-views.py --check
```

### How it differs from verifier success

A passing architecture verifier (`verify-architecture-graph.py`) means the registry artifacts are current, well-formed, graph-consistent, and claim-safe against static evidence. It is a **static artifact health check**.

The blockers report does not run as part of the verifier. It is a **planning artifact** that answers a different question: *what blocks product-readiness claims, and what must future proof slices address?*

| | Architecture Verifier | Blockers Report |
|---|---|---|
| Purpose | Artifact health and claim safety | Next proof work prioritization |
| Trigger | Any registry/graph change | Explicit generation via `generate-architecture-views.py` |
| What it proves | Graph integrity, schema validity, claim-safety, source-anchor freshness | Nothing — it enumerates what is NOT proven |
| Pass/fail | Deterministic pass/fail | Always generated; interpretation is manual |
| Authoritative for | Architecture registry state at a point in time | No — it is a derived view, same as the dashboard |

Verifier pass **does not** mean a capability area is product-ready. The blockers report shows exactly which gates remain open for every area.

### Using it during milestone planning

Before choosing the next proof slice, read `product_readiness_blockers.md` to identify:

1. **Which gates are active** in the capability area you plan to address — each gate names the verification condition that must be met.
2. **Which blocked evidence items** are already available and just need a proof gate owner assigned — those are lower-risk to pick up.
3. **What non-claims apply** to the area — any claim you might be tempted to make must not contradict them.
4. **What next proof work is listed** — each listed item is the owner-addressable action that unblocks the gate.

Do not treat a blocker report entry as a commitment. It is a snapshot of the current registry state. Regenerate the report after significant milestone completions to refresh the next-proof-work guidance.

The blockers report does not itself prove product behavior. A capability area with zero listed gates means the current registry has no active blockers — it does not mean the product is ready for that area.

## Claims Ledger

The claims ledger (`prd/architecture/claims_ledger.md`) classifies every architecture registry item by the safety of asserting its claims in future planning, PRDs, or agent handoffs. It is the primary handoff surface for safe communication about what the architecture *can* and *cannot* assert.

### What it shows

- **safe-to-say** — `source-anchor` or `static-check` proof with `active` status. These records can be cited freely with source anchor reference.
- **bounded** — `runtime-smoke`, `real-document-proof`, or `bounded-evidence` proof; product-scale unproven. Cite scope; do not extrapolate beyond the bounded evidence.
- **blocked/open** — `proof_level=none` or explicit `blocked` status; unresolved proof gates. Do not assert these claims until the gate is resolved.
- **unsafe-to-assert** — `out-of-scope` guardrails or records without sufficient proof. Do not assert without independent evidence.

Each row carries its full `non_claims` list to make overclaim risk explicit and visible at a glance.

### How to run it

The claims ledger is generated by `scripts/generate-architecture-views.py`, which reads `prd/architecture/architecture_graph_report.json`:

```bash
uv run python scripts/generate-architecture-views.py
```

This writes `prd/architecture/claims_ledger.md`. The canonical freshness check is:

```bash
uv run python scripts/generate-architecture-views.py --check
```

### Using it during agent handoffs

Before drafting a PRD section, planning narrative, or architecture decision rationale:

1. **Check the ledger** — look up each record you plan to cite. Use `safe-to-say` records freely with their source anchors. Use `bounded` records with explicit scope caveats. Do not cite `blocked/open` or `unsafe-to-assert` records as positive evidence.
2. **Read the non-claims column** — each row's non-claims list enumerates exactly which assertions would be overclaims. Do not write prose that contradicts those non-claims.
3. **Regenerate after milestone completions** — proof slices that close gates may upgrade a record's classification. Re-run `generate-architecture-views.py` after each significant completion to keep the ledger current.

The ledger does not make claims authoritative. It classifies existing registry records. The source anchors in each record's `architecture_items.jsonl` entry remain the authoritative evidence.

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
