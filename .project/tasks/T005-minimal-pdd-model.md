---
id: T005
title: Create the minimal PDD product model
wave: 2
deps: []
status: done
agent: build_T005
base: 61effa6efe68df1efff2c71f4bd39c4b701e434c
worktree: null
task_branch: null
files:
  - product-model
  - tests/test_product_model.py
---

# T005 — Create the minimal PDD product model

## Context

AGENTS.md and docs/agent-stack/WORKFLOW.md both state that product behavior is described by PDD in product-model/ (audit rows 6 and 19), and the tracked tree has no such directory, so those claims are aspirational today. SC4 creates the minimal PDD Product Model of already established product behavior so the claims become true without editing either file. Established behavior per the codebase evidence: the product CLI law-nexus-inspect (crates/ln-product-cli) with health, inspect, replay, and subordinates subcommands; in-memory graph and vector stores; the fail-closed StubEmbedding that returns a typed error instead of a fake vector; the hc01-hc20 runner belt as executable hostile-contract evidence. E4 and N5 set the boundary: minimal means existing observable behavior only, stubs are modeled as stubs, and no future or desired behavior enters the model.

## Approach

- Follow the bundled pdd-map adoption workflow (installed under the project skills directory; it is not tracked in Git, so its files are host-local). Its format reference defines the file shapes; the layout core is a product-model directory with README.md, config.yaml, the product file (product.md, or product/product.md in the expanded form), coverage.md, at least one interface, capabilities with scenarios, and entities.
- The coding worker has no product author available: per the pdd-map contract, do not quietly choose — split rather than collapse, omit rather than assert, and carry every unanswered question into the model's open questions.
- Model only what a person can run and see today: the terminal interface of law-nexus-inspect and its four subcommands; health succeeds without embeddings; embedding-dependent behavior fails closed through StubEmbedding and says so by name; storage is in-memory and non-persistent; the runner belt is evidence tooling rather than a user-facing capability — record it as such or leave it out entirely.
- Nothing aspirational enters the model: no RuVector, no live retrieval stack, no corpus ingestion, no planned persistence (product direction is a later owner decision, INTENT scope-out).
- Run the bundled pinned pdd lint when the host provides it and record its output in the task Log; the tracked regression test below is the Verify and must pass without any host-only tool.
- Write tests/test_product_model.py: the layout core files exist and are tracked; the model names StubEmbedding as the fail-closed stub it is; no capability file claims a live embedding or a persistent store.

## Interface contract

- None

## Intent coverage

- SC4

## Acceptance criteria

1. product-model/ exists in the tracked tree with the PDD layout core — README.md, config.yaml, the product file, coverage.md, at least one interface, its capabilities with scenarios, and entities — following the bundled format reference shapes.
2. The model records only established observable behavior: StubEmbedding is named as the fail-closed stub it is and the stores are recorded as in-memory; no capability claims live embeddings, persistent storage, or corpus behavior (E4, N5 — review judges the prose, the test pins the markers).
3. The PDD statements in AGENTS.md and docs/agent-stack/WORKFLOW.md are true with no edits to those files — the directory and the model now exist.
4. The pdd lint output, or its unavailability on the host, is recorded in the task Log; the tracked test passes with no host-only tooling.
5. tests/test_product_model.py pins criteria 1 and 2 mechanically and fails if the model directory is absent or stripped of the stub markers.

## Verify

```bash
uv run --frozen pytest tests/test_product_model.py -q
```

Heavy: no

## Log

- 2026-10-26 — created by planner
- 2026-10-26 — build_T005 (coder): implemented. Created `product-model/` (29 files): layout core README.md, .gitignore (build/, cache/), config.yaml (schema 11, sdd.paths: prd/), taxonomies.yaml (primary/validation/edge), product.md (id law-nexus, limitations as product facts), coverage.md (covered: ln-product-cli, ln-storage; exclusions: hc01–hc20 runner binaries as evidence tooling, src/ + scripts/ as control plane; unmapped: ln-decode/ln-consultant-parser/ln-kb-ontology/ln-query/ln-temporal behavior beyond CLI reports; limitation: registry-backed paths not executable here); interfaces/terminal (type cli, actor operator, 4 entryPoints, screens document-report + replay-report); entities operator (acts) and document (Path, Byte size, Content fingerprint, Source family); capabilities check-health, inspect-document, replay-edition, resolve-subordinates with 9 scenarios (primary/validation/edge incl. typed-failure, unsupported-family, explicit-zero, missing-arguments, no-date fail-closed); business rules runs-keep-nothing-between-runs, reports-carry-explicit-non-claims, failures-are-typed-and-atomic, retrieval-is-deterministic-non-semantic. Established behavior only per E4/N5: StubEmbedding named as the fail-closed stub (product.md limitation, inspect-document capability + scenario step, retrieval-rule Rationale), stores recorded in-memory, no RuVector/TEI/persistence/corpus claims anywhere under capabilities/. Granularity calls (no author available): punkt units omitted (not operator-addressable, printed as counts), runner belt excluded per Approach, actor named `operator`.
  - Lint (bundled pinned runner `pdd-map/scripts/run-pdd-kit.mjs`, pinned pdd-toolkit 0.37.1 from .pdd-kit-install.json): `lint --json` → `{"ok": true, "errors": [], "warnings": ["capabilities/replay-edition/capability.md: Capability id \"replay-edition\" reads as a noun phrase; a behavioral id starts with a verb"], counts: interfaces 1, screens 2, entities 2, capabilities 4, capabilityScenarios 9, businessRules 4}`. Warning assessed, kept: `replay` is the product's own command word and the id is verb-noun; the linter's fixed verb vocabulary lacks `replay`. Cross-checked with the host-pinned CLI (`/root/law-nexus/.ai/local/pdd/.../cli.js`, also 0.37.1) run against this worktree: ok: true, errors: [], same single warning. Note: the `scripts/ai/pdd` wrapper itself cannot run inside this isolated worktree (no `.ai/local/` runtime here); the pinned CLI it execs was run with cwd preserved.
  - Verify: `uv run --frozen pytest tests/test_product_model.py -q` → `4 passed in 0.27s` (real run). Negative-path checks: with product-model/ absent the layout test raises "product-model/ must exist in the tracked tree"; with StubEmbedding mentions stripped the stub test raises "the model must name StubEmbedding". Extra (not part of Verify): `uv run --frozen ruff check tests/test_product_model.py` and `ruff format --check` both clean.
  - Changed paths: `product-model/` (all files above), `tests/test_product_model.py`. No other path touched; no git commands that mutate state.
- 2026-10-26 — orchestrator Verify (isolate gsd-path-task/T005): pass, exit 0; output tail:
  ```
  ....                                                                     [100%]
  4 passed in 0.30s
  ```
