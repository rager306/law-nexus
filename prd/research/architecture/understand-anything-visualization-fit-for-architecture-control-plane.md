# Understand-Anything Visualization Fit for a Reusable Architecture Control Plane — Research

**Date:** 2026-05-21

## Summary

Understand-Anything is useful to the reusable Architecture Control Plane (ACP) as a **derived visualization and recovery layer**. Its strongest transferable mechanics are: a compact graph JSON schema, dashboard loading and validation, graph issue surfacing, local-token dashboard access, source-file preview guardrails, graph merge scripts with fixed/unfixable reports, and path sanitization before persistence.

It should not become the ACP authority. In ACP, authority must remain with typed source records, provenance records, ADR/decision records, proof gates, project-profile policy, and deterministic verifiers. Understand-Anything-style graphs can help future agents and humans recover current architecture state visually, but generated nodes/edges and dashboard warnings are derived views over authoritative records.

The recommended ACP use is an adapter: `ACP typed records -> visual graph JSON -> dashboard/recovery view`. The adapter should export prompt-to-proposal-to-decision-to-proof chains, blockers, supersession, health findings, and allowed/blocked next actions. It must also emit provenance and verifier references so the dashboard points back to source evidence rather than replacing it.

## Recommendation

Adopt Understand-Anything as an inspiration for ACP visualization, not as a primary architecture store. The first ACP proof should implement a small exporter from ACP records to an Understand-Anything-compatible or similar graph shape, then render a recovery view that answers:

- What architecture decisions are active?
- Which prompt/provenance records produced them?
- Which decision candidates remain unresolved?
- Which proof gates block verification?
- Which ADRs supersede or conflict with earlier records?
- Which next actions are allowed or blocked by profile policy?

The adapter should be read-only relative to ACP source records. If the visual graph has validation issues, ACP should surface them as `ArchitectureHealthFinding` records or dashboard warnings, but must not mutate authoritative architecture state from the visualization layer.

## Implementation Landscape

### Source inventory

Local vendor source was cloned outside this repository and indexed with GitNexus:

| Source | Local reference | Commit | GitNexus repo |
| --- | --- | --- | --- |
| `Lum1104/Understand-Anything` | vendor source outside this repo | `58411ac` | `understand-anything-reference` |

Primary source files inspected:

| File | Why it matters |
| --- | --- |
| `README.md` | Defines product intent: interactive codebase/knowledge graph, guided tours, search, diff impact, domain view, dashboard commands. |
| `understand-anything-plugin/packages/core/src/types.ts` | Defines graph node/edge/layer/tour/project metadata schema. |
| `understand-anything-plugin/packages/core/src/schema.ts` | Defines graph validation, sanitization, auto-fix, dropped items, fatal errors, aliases, and issue categories. |
| `understand-anything-plugin/packages/core/src/persistence/index.ts` | Defines `.understand-anything` persistence and path sanitization before writing graphs. |
| `understand-anything-plugin/packages/dashboard/vite.config.ts` | Defines graph file discovery, local token access, localhost binding, source preview guardrails, and graph-file whitelist for file reads. |
| `understand-anything-plugin/packages/dashboard/src/App.tsx` | Defines dashboard load path, token gate, graph validation, warnings, diff overlay, domain graph loading, and error surfaces. |
| `understand-anything-plugin/packages/dashboard/src/store.ts` | Defines UI state: graph indexes, selected node, search, diff mode, filters, view modes, navigation, tours, and containers. |
| `understand-anything-plugin/packages/dashboard/src/components/GraphView.tsx` | Defines ReactFlow visualization, overview/layer-detail navigation, layout, search/tour focus behavior, and container/layer handling. |
| `understand-anything-plugin/packages/dashboard/src/components/WarningBanner.tsx` | Defines issue display and copyable diagnostic text for fatal, dropped, and auto-corrected graph issues. |
| `understand-anything-plugin/skills/understand/merge-batch-graphs.py` | Merges batch analysis output into assembled graph, normalizes IDs and complexity, links tests, and reports warnings. |
| `understand-anything-plugin/skills/understand/merge-subdomain-graphs.py` | Merges subdomain graph files into one graph, deduplicates nodes/edges, drops dangling references, and reports fixed/unfixable issues. |
| `understand-anything-plugin/skills/understand-knowledge/merge-knowledge-graph.py` | Merges deterministic manifest and LLM analysis batches for wiki/knowledge graphs, normalizes types, deduplicates entities, drops invalid edges, and builds layers/tours. |

GitNexus context checks were used for:

- `saveGraph`
- `validateGraph`
- `graphFileCandidates`
- `merge_graphs`
- `WarningBanner`

### Key source-backed mechanics

#### Graph persistence

`saveGraph(projectRoot, graph)` writes `.understand-anything/knowledge-graph.json` after calling `sanitiseFilePaths`. The sanitization rule converts absolute paths inside the project root to relative paths and reduces absolute paths outside the project root to their basename. This is directly relevant to ACP because durable visualization artifacts should not leak user home directories or local checkout paths.

`loadGraph(projectRoot, { validate })` validates by default through `validateGraph`, and returns `null` if no persisted graph exists. ACP should copy the pattern of validating visualization data before display, while preserving source records as the authority.

#### Graph schema

`types.ts` defines a compact root `KnowledgeGraph`:

- `version`
- optional `kind`
- `project`
- `nodes`
- `edges`
- `layers`
- `tour`

Node fields include:

- `id`
- `type`
- `name`
- optional `filePath`
- optional `lineRange`
- `summary`
- `tags`
- `complexity`
- optional domain/knowledge metadata

Edge fields include:

- `source`
- `target`
- `type`
- `direction`
- optional `description`
- `weight`

ACP can map its records into this shape, but should not compress away ACP-specific semantics. Some ACP relationships map naturally to existing edge types:

| ACP relationship | Possible visualization edge |
| --- | --- |
| Prompt record produced proposal | `builds_on` or custom ACP overlay edge if supported |
| Decision candidate accepted as decision | `builds_on` or `related` |
| Decision supersedes earlier decision | `contradicts` for visual conflict or ACP-specific `supersedes` if using a custom schema |
| Decision requires proof gate | `validates` or `depends_on` |
| Proof gate references test/evidence | `tested_by`, `documents`, or `cites` |
| Health finding blocks next action | `depends_on`, `contradicts`, or custom ACP edge |

For S04, the safer design is to define ACP-native relationship names first and then map them to dashboard-compatible edge categories for visualization.

#### Validation and issue model

`validateGraph` uses layered behavior:

- sanitizes graph shape;
- normalizes aliases;
- auto-fixes defaults and coercions;
- treats malformed top-level collections or missing project metadata as fatal;
- drops invalid nodes;
- drops invalid edges and missing references;
- filters dangling layer and tour references;
- returns structured issues.

`WarningBanner` groups issues by:

- `fatal`
- `auto-corrected`
- `dropped`

It also creates copyable diagnostic text. Fatal issues are framed as dashboard rendering bugs; non-fatal graph issues are framed as fixable graph-generation errors.

ACP should adopt the diagnostic pattern but tune semantics:

| Understand-Anything issue | ACP equivalent |
| --- | --- |
| Fatal dashboard error | Visualization renderer failure, not architecture truth failure. |
| Auto-corrected graph issue | Derived-view normalization; source records unchanged. |
| Dropped graph item | Derived-view loss that should become an architecture health warning if it hides an authoritative record. |
| Copyable issue text | Agent-ready remediation bundle for the ACP exporter or record author. |

#### Dashboard mechanics

`App.tsx` loads `knowledge-graph.json`, validates it, sets graph state, reports validation issues, optionally loads `diff-overlay.json`, optionally loads `domain-graph.json`, and displays `WarningBanner`. In non-demo mode, access is gated through a generated session token passed in the URL and then stored in session storage.

`vite.config.ts` binds the dev server to `127.0.0.1`, generates an access token, finds graph files through `graphFileCandidates`, and restricts source preview reads:

- no absolute request paths;
- no traversal outside project root;
- source file must be referenced by the graph;
- maximum preview size is 1 MiB;
- binary files are rejected;
- graph data endpoints require the token.

These are strong transferable operational patterns for ACP visualization:

- local-only dashboard by default;
- token-gated graph and source preview endpoints;
- graph-file whitelist for source previews;
- path traversal rejection;
- file-size caps;
- no secret echoing in dashboard diagnostics.

#### UI recovery mechanics

`store.ts` builds graph indexes and holds navigation/recovery state:

- `nodesById`
- `nodeIdToLayerId`
- `nodeIdToLayerIds`
- selected node
- search query/results
- view mode: structural/domain/knowledge
- diff mode changed/affected sets
- focus node
- sidebar node history
- filters
- tour state
- container expansion and layout cache

For ACP, this maps well to a recovery dashboard:

- selected architecture record;
- active decision layer;
- provenance layer;
- proof gate layer;
- health/blocker layer;
- diff mode between two architecture snapshots;
- guided tour for onboarding future agents.

`GraphView.tsx` uses ReactFlow and ELK layout for overview and layer-detail navigation. It supports guided-tour fit behavior and selected-node fit behavior, including fallback behavior if nodes do not materialize after layout. This confirms the dashboard is suitable for navigation and recovery, but not for validating architecture state.

#### Merge and assembly scripts

`merge-subdomain-graphs.py` merges graph dictionaries and returns both a merged graph and report lines. It:

- deduplicates nodes by `id`, with later occurrence winning;
- deduplicates edges by `(source, target, type)`, keeping higher weight;
- drops edges referencing missing nodes;
- merges layers by ID and unions node IDs;
- drops dangling layer and tour references;
- concatenates/merges tour steps;
- emits `Fixed` and `Could not fix` report sections.

`merge-knowledge-graph.py` combines deterministic scan manifest data with LLM analysis batches. It normalizes node/edge aliases, deduplicates entities, drops invalid edges, and records counts such as new entities, new claims, new edges, deduped entities, and dropped edges.

ACP should copy the reporting structure, not necessarily the merge policy. For architecture governance, later-wins deduplication is dangerous if it hides a conflicting decision. ACP should instead preserve conflicts as explicit health findings or `DecisionConflict` records. A visualization exporter may collapse duplicates for display only, but the authoritative registry must retain the conflict chain.

### ACP adapter requirements

A first ACP visualization adapter should:

1. read typed ACP records from source-controlled Markdown/frontmatter or registry JSONL;
2. validate records through ACP schema/profile before export;
3. produce visual graph nodes for:
   - `ArchitecturePromptRecord`
   - `ArchitectureProposal`
   - `DecisionCandidate`
   - `ArchitectureDecision`
   - `ProofGate`
   - `EvidenceAnchor`
   - `ArchitectureHealthFinding`
   - `GSDMilestone`, `GSDSlice`, or `GSDTask` references when available;
4. produce visual graph edges for:
   - `producedProposal`
   - `suggestedDecision`
   - `acceptedAs`
   - `supersedes`
   - `conflictsWith`
   - `requiresProof`
   - `verifiedBy`
   - `blockedBy`
   - `referencesFile`
   - `referencesTest`
   - `ownedByProfile`;
5. group layers by lifecycle:
   - provenance;
   - proposal;
   - decision;
   - proof;
   - implementation;
   - health;
   - profile policy;
6. emit a guided tour for recovery:
   - current architecture position;
   - active decisions;
   - unresolved candidates;
   - blocking proof gates;
   - supersession chain;
   - allowed and blocked next actions;
7. preserve source links so every graph item points back to a source record.

### ACP warning and health model

Use Understand-Anything's warning pattern as a UI model, but use ACP-specific categories:

| ACP warning level | Meaning |
| --- | --- |
| `fatal` | Visualization cannot render or ACP registry cannot be read. Does not prove architecture invalid by itself. |
| `blocking` | Profile or proof gate blocks a requested next action. |
| `conflict` | Two active decisions conflict or supersession chain is unresolved. |
| `missing-evidence` | Decision/proof/claim lacks required source or verifier evidence. |
| `dropped-derived-item` | Exporter omitted a source record from the visual graph. |
| `auto-normalized` | Exporter normalized display-only fields without changing source state. |

The copyable diagnostic bundle should include source record IDs and repo-relative paths, not secrets, raw provider payloads, raw legal text, or local absolute paths.

### Authority boundary

Understand-Anything-style visualization is derived and non-authoritative for ACP.

It must not validate:

- law-nexus parser completeness;
- legal correctness;
- FalkorDB ingestion;
- graph-vector retrieval quality;
- R035;
- R037;
- R038;
- production readiness;
- independent external review.

It may help discover, display, and recover:

- current architectural position;
- decision lifecycle status;
- ADR supersession chain;
- PHR/provenance chain;
- proof gates;
- architecture health findings;
- drift indicators;
- allowed/blocked next actions.

### Reusable ACP vs law-nexus profile

Reusable ACP core should define graph export semantics without legal-domain assumptions. The law-nexus profile should add stricter policy:

- no secrets;
- no raw provider payloads;
- no unnecessary raw legal text;
- no local absolute paths;
- no promotion of external AI dialogue into authority;
- no PHR/ADR/visualization proof of R035, R037, or R038;
- explicit source-role distinction for Consultant XML and other legal source roles;
- explicit non-authoritative boundary for generated views.

## Build Order

1. Finish S03 source-backed research and safety verification.
2. In S04, define ACP core record types, lifecycle, source of truth, and adapters.
3. Define `acp-visual-export` as a future proof slice, not as part of the S04 written contract unless the user asks for implementation immediately.
4. First proof should use a tiny fixture with one prompt record, one proposal, one decision candidate, one proof gate, one health finding, and one GSD reference.
5. Validate that the generated graph can show a recovery chain without mutating source records.

## Verification Approach

For this research slice:

- focused artifact scan for required source markers and forbidden overclaims;
- current architecture verifier after writing artifact;
- no vendor source modification;
- no `.understand-anything` runtime graph generation inside the main repository.

For a future implementation proof:

- unit test ACP fixture export;
- assert all source records appear in the visual graph;
- assert conflicts/supersession/proof gates are represented;
- assert no absolute paths are emitted;
- assert dashboard/export warnings are copyable and source-linked;
- assert visualization cannot set `accepted` or `verified` status.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
| --- | --- | --- |
| Interactive graph navigation | Understand-Anything dashboard patterns: ReactFlow, layer overview/detail, search, tours | Good prior art for visual recovery and onboarding. |
| Local dashboard hardening | Understand-Anything token, localhost binding, graph-file whitelist, path normalization | Useful safety baseline for ACP dashboard adapter. |
| Graph issue UX | `WarningBanner` severity grouping and copyable diagnostics | Agent-friendly remediation loop. |
| Graph validation model | `validateGraph` style sanitize/normalize/auto-fix/drop/fatal pipeline | Useful pattern for derived graph validation, not authoritative record validation. |

## Constraints

- ACP source of truth remains typed records, provenance, decisions, proof gates, and deterministic verifier outputs.
- Visualization artifacts are derived and may be regenerated.
- Visualization must preserve source links back to authoritative records.
- Conflict handling must not use later-wins semantics for authoritative architecture decisions.
- The law-nexus profile must preserve R035, R037, and R038 proof boundaries.
- Do not initialize Understand-Anything runtime or `.understand-anything` outputs in the main repository without an explicit safe spike.

## Common Pitfalls

- **Confusing visualization with authority** — keep dashboard graph read-only and derived.
- **Losing conflict history through deduplication** — visual dedup can be acceptable, but authoritative ACP records must retain conflicts and supersession.
- **Leaking local paths** — copy `sanitiseFilePaths` style behavior for any visual export.
- **Overclaiming from generated graph completeness** — graph render success does not prove architecture correctness or legal/product readiness.
- **Using generic edge labels too early** — define ACP-native relationships first, then map to dashboard-compatible display categories.

## Open Risks

- Understand-Anything's graph schema may be too codebase-oriented for ACP without custom node/edge labels.
- Dashboard source preview patterns are code-file oriented; ACP records may live in Markdown, JSONL, GSD artifacts, or derived reports.
- Existing warnings distinguish dashboard bugs from graph-generation errors, while ACP needs richer health categories tied to profile policy and proof gates.
- A future adapter may need either a forked dashboard schema or an intermediate compatibility projection.

## Sources

- Product intent, dashboard workflow, graph commands, and feature categories (source: `README.md` in `Lum1104/Understand-Anything` at commit `58411ac`).
- Graph persistence and path sanitization (source: `understand-anything-plugin/packages/core/src/persistence/index.ts`).
- Graph type contract (source: `understand-anything-plugin/packages/core/src/types.ts`).
- Graph validation, issue categories, and auto-fix/drop/fatal model (source: `understand-anything-plugin/packages/core/src/schema.ts`).
- Dashboard data loading, validation, warning, diff, and domain graph behavior (source: `understand-anything-plugin/packages/dashboard/src/App.tsx`).
- Localhost/token/source preview safety model and graph file discovery (source: `understand-anything-plugin/packages/dashboard/vite.config.ts`).
- Dashboard state/recovery model (source: `understand-anything-plugin/packages/dashboard/src/store.ts`).
- ReactFlow graph navigation and layout behavior (source: `understand-anything-plugin/packages/dashboard/src/components/GraphView.tsx`).
- Warning display and copyable diagnostics (source: `understand-anything-plugin/packages/dashboard/src/components/WarningBanner.tsx`).
- Batch/subdomain/knowledge graph merge and reporting mechanics (sources: `understand-anything-plugin/skills/understand/merge-batch-graphs.py`, `understand-anything-plugin/skills/understand/merge-subdomain-graphs.py`, `understand-anything-plugin/skills/understand-knowledge/merge-knowledge-graph.py`).

## Verification notes

This artifact is research and design evidence only. It does not validate law-nexus parser completeness, legal correctness, FalkorDB ingestion, graph-vector retrieval quality, R035, R037, or R038. It does not make generated graphs, dashboards, PHRs, ADRs, external AI dialogue, or visualization warnings authoritative proof.
