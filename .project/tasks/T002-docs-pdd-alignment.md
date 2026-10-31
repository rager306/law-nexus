---
id: T002
title: Align front-door docs and PDD model with the shipped reference-package surface
wave: 1
deps: [T001]
status: done
agent: build_t002
base: cb7e3f6a0f38929c5dace055323f7ac7c0b4a318
worktree: null
task_branch: null
files:
  - README.md
  - AGENTS.md
  - docs/agent-stack/POST-SHIP-STATE-2026-10-28.md
  - prd/ARCHITECTURE.md
  - product-model/capabilities/reference-package/capability.md
  - product-model/capabilities/reference-package/scenarios/build-check-ok.md
  - product-model/capabilities/reference-package/scenarios/check-detects-drift.md
  - product-model/coverage.md
---

# T002 — Align front-door docs and PDD model with the shipped reference-package surface

## Context

The fresh docs audit (DOCS-AUDIT.md, rulings #20-#24) and codebase map fixed
the wording the repository's front door must carry: the quick-start command
works after T001's `default-run`; the status band must enumerate 47 workspace
members naming `ln-consultant-parser` and `ln-kb-ontology`; AGENTS.md must
point at an existing slice-writing guide (`.agents/skills/law-nexus-rust/`)
instead of the retired pointer it carries today (ruling #22); POST-SHIP-STATE-2026-10-28.md
must separate current state from dated history (its M004 chapter superseded,
the red-CI table dated as history — live CI is green); the ARCHITECTURE.md
ADR-0031 row must say the measurement-level module code exists while
corpus-wide D5/D4 execution is unproven, keeping ADR-0031 `[proposed]`.
The PDD product model gains the reference-package capability linked to the
measure-ed50 fixture, the landed test
`crates/ln-product-cli/tests/reference_package_cli.rs`, and the recorded check
result from T001's Log.

## Approach

- Rule `fix-doc` discipline: correct the wording to what the code does; do not
  raise any lifecycle tag; do not claim corpus-wide parity (INTENT N3/N4).
- Keep POST-SHIP-STATE's historical sections intact — separate, do not rewrite
  history (ruling #23).
- The new capability docs follow the existing `product-model/capabilities/*`
  shape; coverage.md lists the new capability; scenarios reference the fixture,
  the test path, and the recorded check result.
- The ADR-0031 wording must stay inside the tracked table row style
  (ruling #24): "module code exists at measurement level; corpus-wide D5/D4
  execution unproven".

## Interface contract

None

## Intent coverage

- SC8
- SC9

## Acceptance criteria

1. (SC8) README names 47 members including the two parser crates; AGENTS.md references `.agents/skills/law-nexus-rust/` and its retired pointer is gone (the Verify grep pins the absence by the slug `implement-rust-slice`); POST-SHIP-STATE marks the M004 chapter superseded and dates the red-CI table; ARCHITECTURE.md ADR-0031 row carries the honest module-code/unproven wording.
2. (SC9) `product-model/capabilities/reference-package/` documents the build/check capability with the fixture, the named test path, and the recorded check result; `product-model/coverage.md` lists it.

## Verify

```bash
grep -q 'ln-consultant-parser' README.md && grep -q 'ln-kb-ontology' README.md && ! grep -q 'implement-rust-slice' AGENTS.md && grep -q '.agents/skills/law-nexus-rust/' AGENTS.md && grep -q 'superseded' docs/agent-stack/POST-SHIP-STATE-2026-10-28.md && grep -q 'unproven' prd/ARCHITECTURE.md && test -f product-model/capabilities/reference-package/capability.md && grep -q 'measure-ed50' product-model/capabilities/reference-package/capability.md
```

Heavy: no

## Log

- 2026-10-31 — created by planner (quick mode)
- 2026-10-31 — implemented: README status band and repository map recount 47 members naming `ln-kb-ontology` and `ln-consultant-parser` (plus the matching "47-member inventory" phrase in the Architecture bullet); AGENTS.md slice pointer repointed to `.agents/skills/law-nexus-rust/` with the retired `workflows/` slug removed (ruling #22); POST-SHIP-STATE CI section retitled "through M003 (dated history)" with a green-state pointer and past-tense fixes, M004 chapter marked superseded with M004–M010 shipped / M011 active framing, and the red-CI Non-claims bullet rewritten to the recorded green state (runs 40805352394, 40822037565 — rulings #23/#34/#35); ARCHITECTURE.md ADR-0031 row now states module code exists at measurement level (reference_layer + `reference-package build|check`, 0/2/3/6) while corpus-wide D5/D4 execution stays unproven, tag `[proposed]` unchanged (ruling #24); new `product-model/capabilities/reference-package/` capability + two scenarios (build-check-ok primary, check-detects-drift validation) linked to the measure-ed50 fixture, `crates/ln-product-cli/tests/reference_package_cli.rs`, and the recorded T001 check result (8/8, exit 0, verify.json evidence); coverage.md lists the capability and corrects "four subcommands" to five. Verify passed exit 0 (run twice, verbatim command). Extra check beyond Verify: `npx -y pdd-toolkit@0.38.0 lint` exit 0 ("Product Model structure is sound"; one pre-existing replay-edition warning, untouched). Changed paths: the eight declared files only.
- 2026-10-31 — authoritative Verify (orchestrator finish): exit 0 in sidecar gsd-path-verify/task-t002-verify; evidence: .git/gsd-path/dispatch/gsd-path-M011/T002/attempt-1/verify.json (child exited without the machine-readable RESULT line; its work message: РЕЗУЛЬТАТ: T002 готов — verify exit 0, pdd lint exit 0)
