---
id: T005
title: Create the minimal PDD product model
wave: 2
deps: []
status: pending     # orchestrator-owned: pending | in-progress | done | failed | blocked
agent: null         # orchestrator-owned: set at dispatch
base: null          # orchestrator-owned: clean layer SHA for isolated Verify
worktree: null      # orchestrator-owned: isolated task worktree while active
task_branch: null   # orchestrator-owned: gsd-path-task/<id> while parallel; null when serial
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
