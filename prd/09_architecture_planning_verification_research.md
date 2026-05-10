# Architecture Planning and Verification Research for LegalGraph Nexus

## Reader and action

This note is for future agents planning the post-M003 architecture-systematization milestone. After reading it, they should be able to design a machine-readable architecture registry, connect it to PRD/GSD/ADR evidence, and add executable architecture verification without letting generated graph artifacts become the source of truth.

## Search queries used

- `2026 software architecture planning best practices ISO IEC IEEE 42010 viewpoints views architecture description ADR C4 arc42 ATAM quality attributes`
- `software architecture verification best practices architecture fitness functions continuous architecture quality attribute scenarios ATAM 2026`
- `architecture knowledge management requirements traceability architecture decision records knowledge graph software architecture best practices 2026`

## Sources consulted

- ISO/IEC/IEEE 42010 architecture description summaries from `iso-architecture.org` and arc42 quality model material.
- Continuous Architecture material on architecture fitness functions.
- ATAM / Architecture Tradeoff Analysis Method summaries, including CMU SEI-derived material and contemporary explanatory articles.
- Architecture documentation practice material covering ADRs, C4, arc42, quality attributes, tradeoffs, risk analysis, and docs-as-code.
- ADR reference material from `adr.github.io` and the architecture-decision-record template repository.
- Architecture decision traceability literature, including a systematic mapping study on tracing architectural design decisions to software artifacts.
- Contemporary knowledge graph / context graph material, used only for graph-structure inspiration, not as authority for LegalGraph product architecture.

## Research synthesis

The best fit for LegalGraph Nexus is not a single architecture-documentation method. It is a layered architecture-knowledge workflow:

1. **ISO/IEC/IEEE 42010 frame**: define the entity of interest, stakeholders, concerns, viewpoints, views, decisions, and rationale. The key lesson is that the architecture is not the document. The architecture description is a work product that must address stakeholder concerns and preserve traceability.
2. **ATAM / quality-scenario frame**: evaluate architecture choices against prioritized quality attributes, scenarios, sensitivity points, tradeoff points, and risks. For LegalGraph Nexus, this means legal correctness, citation safety, temporal validity, source traceability, runtime safety, parser reliability, local/open-weight retrieval constraints, and non-authoritative LLM behavior must become explicit scenarios.
3. **ADR frame**: record important decisions with context, alternatives, consequences, and status. ADRs should not be documentation theater; they should feed the architecture registry and verification workflow.
4. **C4 / arc42 frame**: use human-readable views for communication: context, containers/components, runtime/data flows, deployment, risks, quality goals, and decisions. These views should be generated from or cross-checked against the registry where practical.
5. **Continuous Architecture / fitness-function frame**: turn architectural constraints into checks. Static checks cover schema validity, source anchors, edge integrity, missing owners, orphan decisions, and stale references. Dynamic/runtime checks remain separate proof gates for FalkorDB, parser, retrieval, generated Cypher, and MiniMax/PyO3 behavior.
6. **Architecture Knowledge Management frame**: link requirements, decisions, risks, assumptions, evidence, components, interfaces, proof gates, and implementation artifacts. The graph is valuable because it exposes coverage gaps and contradictions, not because it replaces PRD/GSD/ADR documents.

## LegalGraph Nexus-specific implications

LegalGraph Nexus needs stronger guardrails than a normal software architecture project because many claims can become legally or operationally dangerous if over-upgraded:

- LLM output is non-authoritative. The registry must mark any LLM-generated artifact as draft/proposal unless deterministic validation and evidence gates accept it.
- Russian legal evidence claims require source anchors, evidence units, and citation-safe boundaries.
- FalkorDB, GraphBLAS, vector, full-text, UDF, timeout, and read-only execution behavior must stay `hypothesis` or `bounded-evidence` until verified by source/runtime proof.
- `Old_project/` artifacts are prior art only, not trusted implementation evidence.
- Temporal validity is an architectural concern, not a data-cleanup detail. Same-date/multi-edition conflict policy must remain a visible unresolved gate until proven.
- Parser and retrieval quality must be represented as proof gates, not as completed architecture because docs describe them.

## Recommended registry model

### `prd/architecture/architecture_items.jsonl`

Each line should be one architecture item. Recommended fields:

- `id`: stable ID, e.g. `REQ-R017`, `DEC-D031`, `GATE-G005`, `COMP-legalgraph-schema`.
- `type`: one of `requirement`, `decision`, `assumption`, `risk`, `proof_gate`, `component`, `interface`, `data_entity`, `quality_scenario`, `viewpoint`, `evidence`, `workflow_check`.
- `title`: short human-readable name.
- `summary`: concise description.
- `layer`: one of `legal-evidence`, `temporal-model`, `graph-runtime`, `parser-ingestion`, `retrieval-embedding`, `generated-cypher`, `api-product`, `security-safety`, `observability-operability`, `workflow-governance`.
- `status`: one of `proposed`, `active`, `bounded-evidence`, `validated`, `deferred`, `blocked`, `superseded`, `out-of-scope`.
- `proof_level`: one of `none`, `source-anchor`, `static-check`, `unit-test`, `integration-test`, `runtime-smoke`, `real-document-proof`, `production-observation`.
- `source_anchors`: array of file anchors, ideally `path#section` or `path:line` where stable enough.
- `owner`: owning milestone/slice/task or `architecture-graph-and-verification`.
- `verification`: command, artifact, or manual review condition that can update status.
- `non_claims`: list of claims this item explicitly does not make.

### `prd/architecture/architecture_edges.jsonl`

Each line should be one typed relationship:

- `from`: item ID.
- `to`: item ID.
- `type`: one of `satisfies`, `depends_on`, `blocks`, `contradicts`, `refines`, `implements`, `validated_by`, `bounded_by`, `supersedes`, `risks`, `owned_by`, `evidenced_by`, `uses_viewpoint`, `checked_by`.
- `rationale`: why the relationship exists.
- `source_anchors`: source evidence for the edge.
- `status`: `active`, `hypothesis`, `validated`, `rejected`, or `superseded`.

## Recommended NetworkX analysis

The NetworkX graph should be a derived artifact, rebuilt from JSONL and never hand-edited. Useful analyses:

- Orphan detection: requirements, decisions, proof gates, and risks with no incoming or outgoing traceability.
- Unresolved-gate surfacing: proof gates with status not validated and no owner/verification.
- Coverage checks: every active requirement has at least one decision or planned proof gate; every decision has rationale and consequences; every high-risk item has verification.
- Contradiction checks: active edges of type `contradicts` without a resolution/supersession path.
- Layer coverage: missing architecture layers or layers with only assumptions and no evidence.
- Staleness checks: source anchors that reference missing files or sections.
- Overclaim checks: product/legal/runtime claims marked `validated` without sufficient proof level.

## Architecture verification workflow

Add the following docs-as-code flow in the next milestone:

1. `scripts/extract-prd-architecture-items.py`
   - Read PRD, GSD requirements, decisions, known proof gates, and selected summary artifacts.
   - Emit draft JSONL items and edges.
   - Must not invent validation status; default uncertain claims to `proposed`, `active`, `bounded-evidence`, or `hypothesis`.
2. `scripts/build-architecture-graph.py`
   - Validate JSONL shape.
   - Build a NetworkX graph.
   - Export GraphML and a Markdown report.
3. `scripts/verify-architecture-graph.py`
   - Enforce schema, anchors, edge endpoints, orphan rules, unresolved-gate rules, proof-level rules, stale references, and forbidden overclaim patterns.
4. `tests/test_architecture_graph.py`
   - Unit tests for schema validation and representative failure cases.
   - Regression fixtures for known gates: `G-005`, `G-008`, `G-011`, `G-015`, `R017`, and the M003 proof boundary.

## Verification rules that should fail the build

- An item has no `source_anchors` unless explicitly marked generated draft.
- A `validated` item lacks proof evidence.
- A `proof_gate` has no owner or verification condition.
- An active requirement has no edge to a decision, proof gate, or evidence item.
- An active decision has no rationale/consequence source.
- A `contradicts` edge is active without a resolution path.
- A FalkorDB/vector/full-text/UDF/ODT/parser/retrieval/legal-answer claim is marked validated without matching source/runtime/real-document proof.
- A generated-Cypher or LLM item claims authority rather than draft/proposal status.
- A source anchor points to a missing file.

## Proposed next milestone shape

Title: **Architecture Knowledge Graph and Verification Workflow**

Suggested slices:

1. **S01: Taxonomy and schema contract**
   - Define JSON schema, item taxonomy, edge taxonomy, status/proof levels, and fixture examples.
   - Proof: schema tests reject malformed items and unsafe statuses.
2. **S02: PRD/GSD extractor**
   - Extract initial architecture items from PRD and GSD artifacts.
   - Proof: deterministic extraction produces stable JSONL and preserves source anchors.
3. **S03: NetworkX graph and report**
   - Build graph, GraphML export, and Markdown architecture report.
   - Proof: report surfaces unresolved gates, orphan nodes, coverage gaps, and high-risk layers.
4. **S04: Architecture verifier / fitness functions**
   - Add build-failing checks for anchors, graph integrity, unresolved gates, overclaims, and coverage.
   - Proof: tests include both passing current fixtures and intentional failure fixtures.
5. **S05: Workflow integration and handoff**
   - Add verification command to the documented workflow and update PRD/GSD guidance.
   - Create a compact project-local `legalgraph-architecture-verification` router skill after schema/verifier stabilization.
   - Add a deterministic skill consistency check so the skill references current artifact paths/commands and does not contain stale fields or forbidden overclaims.
   - Proof: one command regenerates and verifies the architecture graph from tracked sources, and the architecture skill consistency test passes.

## ADR repository addendum

Additional source studied: `https://github.com/architecture-decision-record/architecture-decision-record`.

Relevant findings:

- The repository defines ADRs as part of **Architecture Knowledge Management**: architecture decisions, architecture decision records, architecture decision logs, and architecturally significant requirements belong together.
- It recommends maintaining a **decision todo list** that complements the product todo list. For LegalGraph Nexus, this maps naturally to unresolved proof gates and architecture questions that are not yet decisions.
- A good ADR should be **specific**: one decision per record. This supports the JSONL registry model: each decision item should be atomic enough to have its own status, proof level, related requirements, and consequences.
- Good ADRs need **timestamps**, **status**, **context**, **decision**, and **consequences**. Existing GSD decisions already capture much of this, but the architecture registry should add machine-readable `last_reviewed`, `superseded_by`, and `consequences` fields or equivalent edges.
- The repo presents two competing practices around mutability: ideal immutability with superseding ADRs, and practical living updates with dated notes. For this project, keep `.gsd/DECISIONS.md` append-only, but allow JSONL architecture items to carry lifecycle/status fields derived from current evidence.
- The Jeff Tyree / Art Akerman template is especially relevant because it includes **issue, status, group, assumptions, constraints, positions/options, argument, implications, related decisions, related requirements, related artifacts, related principles, and notes**. This is closer to our architecture graph needs than the minimal Nygard template.
- The MADR template adds explicit **deciders**, **decision drivers**, **considered options**, **positive consequences**, **negative consequences**, and links. These should become either fields or edges in the architecture registry.
- The Planguage template emphasizes requirement-quality metadata: persistent tag, gist, rationale, priority, stakeholders, owner, revision, assumptions, and risks. This is useful for quality scenarios and proof gates.
- The repository explicitly connects decisions to **views/viewpoints**. It treats architecture diagrams as views instantiated from viewpoints, each with an audience and concerns. This reinforces the ISO 42010-style design: registry items should support multiple generated views, not one universal diagram.
- The repository explicitly supports **fitness functions for decisions as code**: a decision record documents the decision, while a fitness function assures the decision. This maps directly to `scripts/verify-architecture-graph.py` and future PR/CI guardrails.
- Decision guardrails for pull requests are presented as a way to surface relevant decisions when code changes touch governed areas. For LegalGraph Nexus, a later version can connect architecture graph nodes to file globs or symbols so PRs changing graph/runtime/parser/retrieval/generated-Cypher code surface the relevant decisions and proof gates.

ADR-derived registry changes:

- Add or preserve these item fields: `deciders`, `decision_drivers`, `considered_options`, `positive_consequences`, `negative_consequences`, `assumptions`, `constraints`, `implications`, `last_reviewed`, `superseded_by`, `review_due`, `stakeholders`, and `priority`.
- Add edge types: `has_option`, `chosen_over`, `has_consequence`, `has_assumption`, `has_constraint`, `implicates`, `superseded_by`, `reviewed_by`, and `governs_artifact`.
- Add lifecycle statuses beyond simple active/validated where needed: `initiating`, `researching`, `evaluating`, `implementing`, `maintaining`, `sunsetting`, plus decision statuses `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`.
- Add verifier rules:
  - every accepted decision has at least one related requirement or explicit justification for being architecture-significant;
  - every accepted decision has consequences and at least one source anchor;
  - every superseded decision has a valid successor edge;
  - every decision older than a configured review interval has `last_reviewed` or an explicit `review_due` exception;
  - every decision governing a high-risk layer has a corresponding fitness function or manual proof gate;
  - every decision with assumptions has those assumptions represented as graph nodes or typed fields so they can be invalidated later.

Impact on the proposed milestone:

- S01 should not start with a generic schema. It should start with a **decision-aware schema** that can represent Nygard-style minimal decisions and Tyree/MADR-style rich decisions.
- S04 should call its checks **decision fitness functions** where they verify decisions, and **architecture graph integrity checks** where they verify traceability/shape.
- S05 should document how future PRs or GSD task completion can surface relevant decisions and proof gates before accepting architecture-impacting changes.

## Current GSD recording

- Decision recorded: `D031`.
- Requirement recorded: `R029`.
- Durable memory recorded: architecture registry is an evidence projection, not a source of truth.
- ADR repo follow-up source studied and incorporated into this research note.
- New milestone created: `M004` — Architecture Knowledge Graph and Verification Workflow.
- First slice planned: `M004/S01` — ADR-aware architecture registry schema.
- Final integration slice planned: `M004/S05` includes a compact project-local `legalgraph-architecture-verification` router skill plus a deterministic consistency/overclaim test after schema/verifier stabilization.

## Recommendation

Proceed with the architecture graph work as a verification milestone, not as a documentation cleanup. The first deliverable should be a small, strict schema and verifier that can fail on overclaims. Only after the verifier exists should extraction become broader, because a broad extractor without proof-level constraints will reproduce the same ambiguity the graph is meant to eliminate.
