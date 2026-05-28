# M047 Documentation Contract

## Status

Accepted as the S01 contract for the law-nexus project-state documentation pack.

## Reader and post-read action

The reader is a fresh engineer, reviewer, or future agent landing in `law-nexus` without this session's chat history.

After reading the package, the reader must be able to:

1. understand what `law-nexus` is and is not;
2. see which architecture and ACP claims are verified, bounded, active, deferred, or explicitly unproven;
3. run the current verification commands;
4. identify the next safe GSD milestone;
5. avoid overclaiming product, legal, parser, FalkorDB, retrieval, RDF, SHACL, SPARQL, or ACP lifecycle readiness.

## Package location

The package lives under:

- `prd/project-state/`
- `prd/project-state/data/`
- `prd/project-state/diagrams/`

The package is a documentation and state-summary layer. It does not replace PRD, GSD, ADR, source, tests, runtime proof, real-document evidence, architecture registry source mappings, or accepted decision artifacts.

## Human-facing documents

The following Markdown files must be created in S04:

| File | Purpose |
|---|---|
| `prd/project-state/README.md` | Main cold-reader entry point for the project state package. |
| `prd/project-state/roadmap.md` | Completed milestone themes, current phase, and next recommended milestones. |
| `prd/project-state/architecture.md` | Current law-nexus architecture layers and source/projection boundaries. |
| `prd/project-state/verification.md` | What is checked, what passed, and what each check does not prove. |
| `prd/project-state/acp.md` | ACP concept, purpose, current state, projections, and remaining gaps. |
| `prd/project-state/handoff.md` | Stable current handoff for next agents, derived from GSD state and M046/M047 evidence. |

Markdown files may link to tracked project-relative paths. They must not depend on ignored local execution logs or absolute local paths.

## Machine-readable JSON files

The following JSON files must be created in S02:

| File | Required top-level keys |
|---|---|
| `prd/project-state/data/project-overview.json` | `project`, `working_name`, `current_phase`, `last_completed_milestone`, `active_milestone`, `recommended_next_milestone`, `source_of_truth_policy` |
| `prd/project-state/data/roadmap.json` | `completed_milestone_groups`, `current_milestone`, `recommended_next`, `alternatives` |
| `prd/project-state/data/architecture-map.json` | `layers`, `flows`, `source_of_truth_boundary` |
| `prd/project-state/data/verification-matrix.json` | `checks`, `last_fresh_verification`, `non_claims` |
| `prd/project-state/data/proof-boundaries.json` | `not_validated`, `blocked_claims`, `allowed_claims`, `source_truth_policy` |
| `prd/project-state/data/acp-state.json` | `concept`, `purpose`, `current_state`, `current_counts`, `outputs`, `remaining_gaps` |
| `prd/project-state/data/open-requirements.json` | `active`, `deferred`, `out_of_scope_note` |
| `prd/project-state/data/next-milestones.json` | `recommended`, `alternatives`, `planning_constraints` |

JSON files are derived summaries. They are not authoritative project state. If they disagree with GSD/PRD/ADR/source/test/runtime evidence, the source evidence wins and the JSON must be regenerated or corrected.

## Mermaid diagrams

The following Mermaid files must be created in S03:

| File | Diagram type | Purpose |
|---|---|---|
| `prd/project-state/diagrams/system-overview.mmd` | `flowchart` | Compress project architecture layers and derived outputs. |
| `prd/project-state/diagrams/acp-control-plane.mmd` | `flowchart` | Explain ACP prompt/proposal/candidate/gate/finding flow. |
| `prd/project-state/diagrams/proof-boundary-map.mmd` | `flowchart` | Show what static checks prove and do not prove. |
| `prd/project-state/diagrams/milestone-timeline.mmd` | `timeline` | Summarize major completed milestone bands and next step. |
| `prd/project-state/diagrams/data-flow.mmd` | `flowchart` | Show source/registry/graph/ACP/RDF projection data flow. |

Diagrams are compression aids only. They must not imply source-truth, product-readiness, legal correctness, runtime, or engine-backed proof beyond the documented evidence.

## Evidence inventory

Safe evidence sources for S02-S04:

| Source | Use |
|---|---|
| `.gsd/STATE.md` | Current GSD phase, active milestone, completed milestone registry, active requirements count. |
| `.gsd/REQUIREMENTS.md` | Active/open requirements, especially R035, R037, R038. |
| `.gsd/milestones/M046-x5gmog/M046-x5gmog-SUMMARY.md` | Latest completed ACP hardening milestone summary, decisions, files, follow-ups. |
| `.gsd/milestones/M046-x5gmog/slices/S03/continue.md` | Current handoff and next-step recommendation. |
| `prd/architecture/README.md` | Architecture registry source-of-truth boundary and verifier workflow. |
| `prd/architecture/architecture_graph_report.json` | Current derived graph/report counts and diagnostics. |
| `prd/architecture/architecture_report.md` | Human-readable derived architecture graph report. |
| `prd/architecture/acp/README.md` | ACP fixture concept, record kinds, non-goals, safety policy. |
| `prd/architecture/acp/M046-RDF-PROJECTION-HARDENING-CONTRACT.md` | Latest ACP RDF projection hardening contract. |
| `prd/architecture/acp/M046-RDF-PROJECTION-HARDENING-DECISION.md` | Latest ACP RDF projection hardening adoption decision. |
| `prd/architecture/acp/derived/architecture-projection-rdf-report.json` | Current RDF projection status, counts, diagnostic summary, vocabulary, safety boundary. |
| `scripts/verify-architecture-graph.py` | Canonical architecture verifier command owner. |
| `scripts/verify-acp-records.py` | ACP fixture verifier command owner. |
| `scripts/export-architecture-rdf-projection.py` | Custom RDF/SHACL/SPARQL projection exporter and check/diff CLI. |
| `tests/test_architecture_rdf_projection.py` | Focused projection test coverage. |

Do not cite ignored execution-log artifacts, absolute local paths, raw provider payloads, raw vectors, secrets, or raw legal-answer prose as durable proof anchors.

## Current facts to preserve

Current GSD state at S01 start:

- Active milestone: `M047-igv5e2 — law-nexus Project State Documentation Pack`.
- Last completed milestone: `M046-x5gmog — ACP RDF Projection Hardening`.
- Requirements status: 3 active, 30 validated, 3 deferred, 3 out of scope.
- Active requirements: R035, R037, R038.

Current architecture/RDF projection facts:

- Architecture graph verifier remains the canonical static architecture drift gate.
- Current architecture registry counts are 63 items and 98 edges.
- Current ACP contribution is 5 ACP items and 7 ACP edges.
- Current custom RDF projection report has 161 RDF resources and 422 Turtle statements.
- Current RDF projection report status is `ok`, `non_authoritative` is `true`, `mode` is `custom`, and `diagnostic_count` is 0.
- Current RDF projection includes diagnostic metadata, `diagnostic_summary`, `vocabulary`, `safety_boundary`, and non-writing `--diff` support.

## Source-of-truth hierarchy

Authoritative project evidence:

1. PRD, GSD, ADR, accepted decision artifacts, and source documents.
2. Source code, tests, runtime proof, and real-document evidence where a claim requires implementation or runtime evidence.
3. External references only when recorded as explicit tracked evidence and bounded by local decisions.

Derived, non-authoritative artifacts:

1. `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_edges.jsonl`.
2. Architecture graph JSON/Markdown reports.
3. ACP recovery/projection outputs.
4. RDF/SHACL/SPARQL projection outputs.
5. This `prd/project-state/` documentation package and its JSON/Mermaid summaries.

## Required verification commands

S02 JSON verification:

```bash
uv run python -m json.tool prd/project-state/data/project-overview.json
uv run python -m json.tool prd/project-state/data/roadmap.json
uv run python -m json.tool prd/project-state/data/architecture-map.json
uv run python -m json.tool prd/project-state/data/verification-matrix.json
uv run python -m json.tool prd/project-state/data/proof-boundaries.json
uv run python -m json.tool prd/project-state/data/acp-state.json
uv run python -m json.tool prd/project-state/data/open-requirements.json
uv run python -m json.tool prd/project-state/data/next-milestones.json
```

Core project verification for S01-S05:

```bash
uv run python scripts/verify-architecture-graph.py
uv run python scripts/verify-acp-records.py
uv run python scripts/export-architecture-rdf-projection.py --check
uv run python scripts/export-architecture-rdf-projection.py --diff
uv run pytest tests/test_architecture_rdf_projection.py
```

If code changes are made, also run focused ruff/LSP checks for changed code. Pure docs/JSON/Mermaid changes do not require code formatters, but must pass marker/link/JSON checks.

## Marker and overclaim scan rules

The documentation package must not contain positive claims that say or imply:

- active requirements R035, R037, or R038 are validated;
- RDF or any projection artifact is authoritative source truth;
- SHACL output proves ontology correctness;
- SPARQL handoff queries prove product runtime behavior;
- parser completeness, legal correctness, FalkorDB ingestion, retrieval quality, or production readiness has been proven.

The package must also avoid literal local/secret markers:

- absolute local root paths;
- ignored GSD execution-log anchors;
- common secret key prefixes or environment variable assignments;
- raw provider payloads;
- raw vectors;
- raw legal-answer prose.

Negative boundary language is required and safe, for example:

- `does not validate R035`;
- `derived and non-authoritative`;
- `not source truth`;
- `not engine-executed`;
- `does not prove parser completeness`.

## Reader-test criteria

A cold reader must be able to answer these questions from `prd/project-state/README.md` and linked files:

1. What is `law-nexus`?
2. What is ACP and why does it exist?
3. Which milestones are complete and what phase is next?
4. What is currently verified?
5. What remains unverified or active?
6. Which commands check current state?
7. Which artifacts are authoritative and which are derived?
8. What should the next GSD milestone be?
9. What must not be claimed?
10. Where are the JSON summaries and Mermaid diagrams?

S05 must record a reader-test result and address any gaps.

## Independent review expectation

R038 remains active as a standing proof-heavy review gate. S05 should include an independent review if available, or explicitly record why the review is scoped/deferred. The documentation package itself must not claim R038 validation unless a separate accepted proof exists.

## Next milestone recommendation to preserve

The recommended milestone after this documentation package remains:

- **ACP Decision Lifecycle Workflow**

Expected focus:

- safe `decision_candidate` promotion;
- accepted/deferred/rejected/superseded lifecycle states;
- authority checks;
- proof-gate checks;
- blocked-action enforcement;
- source-anchor safety;
- non-claim preservation;
- independent review gate for proof-heavy transitions.
