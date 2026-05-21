# Architecture Governance Tooling Research: git-lex and Understand-Anything

## Status

- Milestone: `M035-775l5y — Architecture Governance Tooling Research`
- Research status: `initial-source-backed-assessment`
- Date: 2026-05-20
- Scope: architecture design, architecture planning, architecture change governance, drift detection, visualization, onboarding, and tool layering for law-nexus
- Non-validation boundaries: this research does not validate R035, R037, R038, parser completeness, legal correctness, graph runtime behavior, retrieval quality, or production readiness

## Executive conclusion

Both tools are relevant, but they serve different layers:

1. `git-lex` is a promising candidate for a governed RDF/SHACL/SPARQL architecture metadata layer, especially for typed decisions, temporal supersession, and queryable proof-gate coverage.
2. `Understand-Anything` is a promising visualization and onboarding layer for code/docs/domain exploration, but it should remain non-authoritative because much of its value comes from LLM-generated summaries, inferred relationships, and generated graph artifacts.
3. Neither tool should replace the existing law-nexus architecture registry and verifier today.
4. The existing law-nexus verifier is already live and passed at the time of research:

```json
{
  "status": "ok",
  "items": 58,
  "edges": 91,
  "failure_count": 0,
  "upstream_checks": "passed",
  "non_authoritative": true
}
```

Recommended integration model:

```text
PRD/GSD/ADR/source/runtime evidence = source of truth
law-nexus architecture registry + verify-architecture-graph.py = primary drift gate
git-lex = optional RDF/SHACL/SPARQL sidecar candidate
Understand-Anything = optional visualization/onboarding/exploration candidate
```

Recommended next action: run an isolated spike, not main-repo adoption.

## Current law-nexus baseline

law-nexus already has a working architecture governance layer:

- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`
- `prd/architecture/architecture_graph_report.json`
- generated views such as `architecture_health.md`, `product_readiness_blockers.md`, and `claims_ledger.md`
- `scripts/extract-prd-architecture-items.py`
- `scripts/build-architecture-graph.py`
- `scripts/verify-architecture-graph.py`
- project-local router skill: `legalgraph-architecture-verification`

The current source-of-truth hierarchy is explicit:

```text
PRD / GSD / ADR / source code / tests / runtime proof / real-document proof
→ derived architecture registry JSONL
→ derived graph/report/views
→ verifier diagnostics
→ agent/router guidance
```

Generated artifacts are derived and non-authoritative. Hand-editing generated JSONL or reports to create authority is forbidden by existing project convention.

## Research method

This research used:

- project memory and GSD memory for prior architecture verifier decisions;
- current law-nexus verifier command:
  - `uv run python scripts/verify-architecture-graph.py`
- direct source reads from GitHub raw URLs;
- Jina MCP / Jina Reader extraction for the Grok shared dialogue supplied by the user;
- two independent researcher subagents:
  - one for `repolex-ai/git-lex`;
  - one for `Lum1104/Understand-Anything`.

Additional extracted source:

- `prd/research/architecture/grok-book-as-context-git-lex-dialogue.md` — external AI-generated discussion about Book-as-context, git-lex/GSD integration, SHACL, temporal architecture, and architecture control. This is context evidence only, not authoritative proof or a project decision.

Some claims from the user-provided idea were confirmed, some were not fully confirmed, and some require local spike testing.

## Tool 1: git-lex

### Verified facts

Source URLs checked:

- `https://raw.githubusercontent.com/repolex-ai/git-lex/main/README.md`
- `https://github.com/repolex-ai/git-lex/releases`
- `https://raw.githubusercontent.com/repolex-ai/git-lex/main/Cargo.toml`
- `https://raw.githubusercontent.com/repolex-ai/git-lex/main/src/main.rs`
- `https://raw.githubusercontent.com/repolex-ai/git-lex/main/src/kit.rs`
- `https://raw.githubusercontent.com/repolex-ai/git-lex/main/src/shacl.rs`
- `https://raw.githubusercontent.com/repolex-ai/git-lex/main/docs/2026_03_28_DATA_ARCHITECTURE_SPEC.md`
- `https://raw.githubusercontent.com/repolex-ai/git-lex/main/docs/2026_04_04_MARKDOWN_TO_RDF_IDENTITY_SPEC.md`
- `https://raw.githubusercontent.com/repolex-ai/git-lex/main/docs/2026_04_21_SHACL_OWL_LOSSLESS_SUBSET.md`
- `https://raw.githubusercontent.com/repolex-ai/git-lex-kit-squad/main/README.md`

Confirmed capabilities from README and source-level research:

- Rust git extension installed as a git subcommand: `git lex ...`.
- Turns a git repository into a SHACL-validated, SPARQL-queryable knowledge graph.
- Markdown files remain normal repo content.
- Frontmatter uses dot notation such as `kit.class.property: value`.
- `.lex/` is a git-tracked index for sidecars, kit definitions, and generated SHACL shapes.
- `.git/lex/` stores derived Oxigraph data and is rebuildable/untracked.
- Core commands include:
  - `git lex init`
  - `git lex create`
  - `git lex save`
  - `git lex sync`
  - `git lex query`
  - `git lex list`
  - `git lex status`
  - `git lex serve`
  - `git lex nuke`
- Kits are installed from GitHub using the pattern `repolex-ai/git-lex-kit-{name}`.
- `git-lex-kit-squad` exists and includes document classes such as Agent, Pod, Message, Project, Task, Decision, Brief, Discovery, Situation, and Freeform.
- SHACL shapes are described as generated from kit ontology and should not be hand-edited.

### Maturity signals

Observed maturity concerns:

- The repository is young.
- Public repo signals are low adoption:
  - small star/fork counts at time of research;
  - no public release binaries were available from the releases page;
  - README documents release install, but releases page reported no releases.
- Cargo version was reported by subagent research as `0.0.1`.
- Some docs and implementation appear to be moving quickly.
- Kits may be fetched from GitHub `main` tarballs, which is convenient but weak for reproducibility unless pinned or vendored.

Therefore this research rejects the pasted claim that git-lex is already safely `production-ready` for law-nexus. It is better classified as a strong spike candidate.

### Fit for law-nexus

High conceptual fit:

| law-nexus need | git-lex fit |
|---|---|
| Typed architecture decisions | Markdown documents with typed frontmatter and ontology classes. |
| Strict field validation | SHACL shapes. |
| Queryable architecture graph | Oxigraph + SPARQL. |
| Git-traceable architecture history | Architecture documents and `.lex/` sidecars live in Git. |
| Temporal supersession | Can be modeled with properties such as `validFrom`, `validTo`, `supersedes`. |
| Agent preflight queries | SPARQL can answer active decisions, blocked claims, proof gates, and supersession paths. |

But there are important boundaries:

- SHACL validates graph/data shape; it does not replace project-specific proof gates.
- git-lex RDF/SPARQL should not become source of truth over GSD/PRD/ADR/source/runtime evidence.
- `git lex save` can stage/commit and may conflict with GSD commit ownership.
- `.lex/` generated/tracked sidecars may add review noise.
- A custom `legal-arch-kit` would be required before this can encode law-nexus proof-level and non-claim rules.

### Best possible role

Recommended role:

```text
git-lex as optional RDF/SHACL/SPARQL sidecar for architecture governance metadata.
```

Not recommended role:

```text
git-lex as replacement for verify-architecture-graph.py or GSD decision/requirement workflow.
```

### Concrete value if spike succeeds

Potential queries:

- active architecture decisions by topic;
- claims without proof gates;
- R035-related claims not validated;
- R037 claims missing runtime-smoke or graph load/query proof;
- decisions depending on M009;
- decisions superseded after M034;
- components governed by decisions that require re-review;
- proof gates older than a review interval;
- claims with source anchors but no verifier coverage.

## Tool 2: Understand-Anything

### Verified facts

Source URLs checked:

- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/README.md`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/install.sh`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/skills/understand/SKILL.md`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/skills/understand-dashboard/SKILL.md`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/skills/understand-diff/SKILL.md`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/skills/understand-domain/SKILL.md`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/skills/understand-knowledge/SKILL.md`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/packages/core/src/types.ts`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/packages/core/src/schema.ts`
- `https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/understand-anything-plugin/packages/dashboard/vite.config.ts`

Confirmed capabilities:

- Multi-platform agent plugin/skill system.
- Pi Agent is explicitly listed as a supported platform.
- Main command `/understand` analyzes a project and writes `.understand-anything/knowledge-graph.json`.
- Dashboard command `/understand-dashboard` starts an interactive local graph dashboard.
- Additional commands include:
  - `/understand-chat`
  - `/understand-diff`
  - `/understand-explain`
  - `/understand-onboard`
  - `/understand-domain`
  - `/understand-knowledge`
- Multi-agent pipeline includes roles such as project scanner, file analyzer, architecture analyzer, tour builder, graph reviewer, domain analyzer, and article analyzer.
- Generated artifacts include:
  - `.understand-anything/knowledge-graph.json`
  - `.understand-anything/domain-graph.json`
  - `.understand-anything/diff-overlay.json`
  - `.understand-anything/meta.json`
  - `.understand-anything/config.json`
  - `.understand-anything/intermediate/*`
- README recommends committing some graph artifacts for team sharing, but not intermediate/diff overlay.
- Dashboard is a local Vite/React app and includes token/path safeguards according to source-level research.

### Fit for law-nexus

Understand-Anything has strong fit for visualization and onboarding:

| law-nexus need | Understand-Anything fit |
|---|---|
| Human-visible architecture map | Interactive graph dashboard. |
| Codebase onboarding | Guided tours and node summaries. |
| Architecture layer visualization | Built-in layer visualization. |
| Business/domain flow view | `/understand-domain`. |
| Diff visualization | `/understand-diff` overlay. |
| Knowledge-base exploration | `/understand-knowledge` for wiki-style docs. |

But it is not a governance source:

- Many nodes/summaries/relationships are produced by LLM agents.
- Domain and claim extraction can hallucinate or over-interpret legal/project meaning.
- It overlaps with GitNexus for code graph and impact analysis, but GitNexus remains mandatory for code impact in this repo.
- Generated graph artifacts may be large and noisy.
- It may expose source content through a local dashboard; should stay bound to local-only access.
- Auto-update hooks should be disabled initially.

### Best possible role

Recommended role:

```text
Understand-Anything as optional visual onboarding, architecture exploration, and human comprehension layer.
```

Not recommended role:

```text
Understand-Anything as architecture source of truth, proof-gate validator, legal evidence validator, or replacement for GitNexus impact analysis.
```

### Concrete value if spike succeeds

Potential uses:

- visualize `scripts/`, `tests/`, `prd/architecture/`, and verifier code;
- produce onboarding graph for new agents/humans;
- compare its domain graph against law-nexus architecture registry;
- visually show architecture verifier components and generated views;
- generate draft onboarding docs, then manually verify them against GSD/PRD/source evidence;
- use `/understand-diff` as a human-friendly overlay next to GitNexus impact output.

## Combined architecture-governance model

Recommended layered model:

```text
Layer 0 — authoritative evidence
  PRD, GSD requirements/decisions/summaries, ADRs, source code, tests, runtime smoke, real-document proof

Layer 1 — existing law-nexus architecture registry
  architecture_items.jsonl, architecture_edges.jsonl, graph reports, claims ledger
  Derived and non-authoritative

Layer 2 — existing law-nexus verifier
  verify-architecture-graph.py
  Primary architecture drift gate and project-specific fitness functions

Layer 3A — git-lex sidecar candidate
  typed markdown, .lex sidecars, RDF triples, SHACL, Oxigraph, SPARQL
  Useful for ontology/query/temporal governance if spike passes

Layer 3B — Understand-Anything visualization candidate
  knowledge-graph.json, domain-graph.json, dashboard, tours, diff overlay
  Useful for comprehension and onboarding if spike passes

Layer 4 — agent workflow
  preflight queries, decision impact review, proof-gate reminders, drift diagnostics, generated views
```

The central rule remains:

```text
No generated graph, visualization, LLM summary, SHACL pass, SPARQL query result, or dashboard view can validate a claim that lacks source evidence and project verifier proof.
```

## Architectural drift prevention pattern

A robust architecture-governance flow for law-nexus should be:

1. Change proposed.
2. Identify whether it is architecture-impacting.
3. Recover prior decisions from memory/logs/GSD artifacts.
4. Check existing architecture registry and verifier.
5. Require or update an architecture decision/proof gate if needed.
6. Regenerate derived architecture projections.
7. Run `verify-architecture-graph.py`.
8. Optionally update git-lex sidecar/query projection.
9. Optionally update Understand-Anything visual graph.
10. Commit only after deterministic verification.

## Additional applications

### 1. Architecture preflight for agents

Before answering architecture questions or planning architecture-changing work, an agent can be required to retrieve:

- active decisions by topic;
- superseded decisions;
- blocked claims;
- proof gates;
- non-claims;
- impacted components.

This can use existing registry now and may later use SPARQL if git-lex is adopted.

### 2. Decision impact map

For a proposed change, show:

- decisions depending on it;
- requirements it supports;
- proof gates it affects;
- generated views that may become stale;
- code/source artifacts governed by the decision.

### 3. Proof debt dashboard

Expose:

- validated claims;
- bounded claims;
- blocked claims;
- claims without proof gates;
- decisions needing review;
- stale source anchors;
- active contradictions;
- unsafe overclaims.

### 4. Architecture timeline

Track milestones and decisions over time:

```text
M006 → M009 → M031 → M032 → M033 → M034 → future parser hardening
```

Use temporal metadata to answer what was valid before or after a milestone.

### 5. Visual onboarding

Use Understand-Anything to generate a visual explanation of:

- architecture verifier pipeline;
- parser proof pipeline;
- source lifecycle/discovery/staging layers;
- how generated artifacts relate to source truth.

### 6. Architecture PR review pack

Before merging architecture-impacting changes, generate a compact pack:

- changed architecture items;
- impacted decisions;
- required proof gates;
- verifier result;
- GitNexus impact result for code;
- optional Understand-Anything visual diff overlay.

## Risks and mitigations

| Risk | Tool | Mitigation |
|---|---|---|
| Replacing current verifier prematurely | git-lex | Treat git-lex as sidecar only until spike proves value. |
| Split-brain source of truth | git-lex / Understand-Anything | Preserve PRD/GSD/ADR/source/runtime evidence as authority. |
| Commit workflow conflict with GSD | git-lex | Do not use `git lex save` in main repo during spike. Use disposable repo. |
| Unpinned kit downloads | git-lex | Vendor/pin kit commit SHA before any serious use. |
| Sidecar/rebuild noise | git-lex | Measure `.lex/` churn in spike. |
| LLM hallucinated graph/domain claims | Understand-Anything | Mark all UA outputs non-authoritative and compare against verifier/GitNexus. |
| Generated graph size/churn | Understand-Anything | Keep `.understand-anything/` ignored during spike. |
| Source exposure via dashboard | Understand-Anything | Bind localhost only, use token, exclude sensitive files. |
| Auto-update hooks mutate graphs unexpectedly | Understand-Anything | Disable auto-update initially. |
| Duplicate GitNexus capability | Understand-Anything | Use only as visualization, not as impact authority. |

## Recommended spike plan

### Spike principle

Run both tools only in an isolated workspace or disposable clone. Do not initialize `.lex/` or `.understand-anything/` in the main repo until a later explicit adoption decision.

### S01 — git-lex install and isolated smoke

Checks:

- build/install from source;
- `git lex --help` works;
- initialize disposable repo;
- create typed document;
- run validation and SPARQL query;
- delete derived store and rebuild with `git lex sync`;
- record whether `.lex/` outputs are deterministic and reviewable.

Pass/fail:

- pass if commands work without mutating law-nexus;
- fail if install is unstable, network dependency is unpinned, or sidecars are too noisy.

### S02 — minimal legal-arch model in git-lex

Prototype classes:

- `ArchitecturalDecision`
- `ArchitectureClaim`
- `Requirement`
- `ProofGate`
- `Evidence`
- `NonClaim`
- `Supersession`

Test records:

- M009 is current Consultant XML baseline.
- M031-M033 are upper layers.
- R037 cannot validate without FalkorDB load/query.
- R035 cannot close from documentation-only evidence.
- R038 requires independent external review result.

Pass/fail:

- pass if missing proof/source/supersession fails validation;
- fail if SHACL cannot express useful constraints or requires too much custom glue.

### S03 — SPARQL value test

Queries:

- active decisions by topic;
- claims without proof gates;
- claims blocked by R035/R037/R038;
- decisions superseded after M034;
- claims depending on M009;
- proof gates without owner.

Pass/fail:

- pass if SPARQL answers are clearer than existing reports for at least three real governance questions;
- fail if results duplicate current verifier views without added value.

### S04 — Understand-Anything isolated visualization smoke

Checks:

- install for Pi in isolated or reversible way;
- run on a narrow scope first, e.g. `scripts/` plus `prd/architecture/`;
- generate `knowledge-graph.json`;
- open dashboard locally;
- check graph accuracy against GitNexus and current architecture verifier;
- inspect generated summaries for overclaims.

Pass/fail:

- pass if dashboard helps explain architecture verifier/code relationships without dangerous hallucinations;
- fail if it invents misleading domains or creates too much generated noise.

### S05 — Combined governance recommendation

Decide one of:

1. Adopt neither.
2. Adopt Understand-Anything only for optional onboarding visualization.
3. Adopt git-lex only as architecture RDF/SPARQL sidecar.
4. Adopt both with strict boundaries.
5. Defer both until current architecture verifier needs are clearer.

## Initial recommendation

Run the spike.

Do not adopt either tool directly into the main repo yet.

Expected likely outcome:

```text
git-lex: promising architecture governance sidecar, needs spike and custom kit.
Understand-Anything: useful visualization/onboarding layer, non-authoritative.
Existing law-nexus verifier: remains primary architecture drift gate.
```

## Honest unknowns

The following were not proven in this research:

- git-lex local build success in this environment;
- git-lex sidecar determinism under repeated sync;
- git-lex kit pinning/offline reproducibility;
- git-lex SHACL expressiveness for all law-nexus proof gates;
- Understand-Anything local install in Pi;
- Understand-Anything graph quality on law-nexus;
- Understand-Anything dashboard performance on this repo;
- generated artifact size/churn for `.understand-anything/`;
- whether either tool will materially improve over the current verifier after hands-on testing.

These require the isolated spike above.
