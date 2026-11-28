---
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-plan-bootstrap
execution: code
created: 2026-11-28
title: "Architecture Grounding, Review Audit, Context Hygiene, and Governor AGY/CE Adaptation"
---

# Plan: Architecture Grounding, Review Audit, Context Hygiene, and Governor AGY/CE Adaptation

## Goal Capsule

- **Objective:** Give maintainers and coding agents a clean, accurate, noise-free architecture baseline and a working `governor` / `preflight` control plane adapted to Antigravity (AGY) and Compound Engineering (CE), aligned around proving the Temporal CST/AST + Tokenizer/Context + ChangeGrammar core before committing to downstream storage/UI plumbing.
- **Means:** Deliver in three focused, CI-verified PR waves — (PR1) adapt `governor`, `preflight`, `Justfile`, and `.agents/skills/` to AGY + CE; (PR2) reconcile living architecture/PRD/ADR/review-gap surfaces and prune legacy GSD context noise; (PR3) author the grounded core trajectory (ADR-0032 / vertical Temporal CST/AST + ChangeGrammar spike contract) that unifies `ln-decode`, `ln-temporal`, and Pullenti-derived patterns (`DecreeChange`, `local_grammar`, unified `DocumentContext`). (KTD1, KTD2, KTD3)
- **Authority Hierarchy:** `prd/ARCHITECTURE.md` + `doc/adr/**` remain durable authority; D098 lifecycle tags (`[proposed]` / `[bounded]` / `[smoke]` / `[validated]` / `[deferred]`) are never inflated; human disposition remains mandatory for Review Case packets (`RC-2026-09-10-001`) and ADR lifecycle promotion.
- **Stop Conditions:** Never forge human `actor_class: HUMAN` review-case events; never promote any `[proposed]`/`[bounded]` claim to `[validated]` from docs or governor checks alone; never break existing `governor` / `preflight` / `adr-conformance` CI suites; never import Pullenti code, dictionaries (`m_ru.dat`), or numeric thresholds.
- **Execution Profile:** Multi-PR (3 sequential PRs: PR1 -> PR2 -> PR3), each verified by `just gate` / `pytest` / `governor` + `ce-code-review`.

## Product Contract

### Summary

The repository completed post-M012 cleanup, cutover to Compound Engineering, SHA-pinned CI, and 0-CVE dependency upgrades (`main` @ `1fcb7849`). Live inspection of `governor`, `preflight`, `review-case status`, ADRs, and Rust source shows three concrete blockers to starting core Temporal CST/AST + ChangeGrammar work cleanly:

1. **Control-plane lag behind AGY + CE:** 5 of 51 `governor` checks are dead legacy `.gsd/` no-ops (`not-applicable`); `cli.py` help text and `.agents/skills/law-nexus-subagent/SKILL.md` still target retired `~/.gsd/agent/agents/*.md` and GSD-Pi roles; `governor` has no active checks for CE/AGY surfaces (`docs_root`, review archive convention, skill hygiene); `preflight` warns on stale GitNexus index (`0d30fd13` vs `HEAD`) with an outdated CLI command; `Justfile` has no `just governor` / `just preflight` targets.
2. **Stale living documents and high context noise:** `prd/ARCHITECTURE.md` stops its progress narrative at M174/EA-10; `prd/PRODUCT.md` and `prd/REQUIREMENTS.md` still reference `.gsd/REQUIREMENTS.md` and omit `reference-package` and CE; 7 active ADRs reference `.gsd/DECISIONS.md` without noting `archive/gsd-path-final`; `prd/architecture/` holds 135 files without a clean "living canon vs historical snapshot" entry map; `prd/ARCHITECTURE.md` (`graph_vector=ruvector`) and `ADR-0031` (`M217 store bake-off`) state unresolved competing storage paths.
3. **Ununified core trajectory:** Only 5 of 35 Review Case findings remain open (`RC11-F13`, `RC12-F19`, `RC28-F13`, `RC28-F16`, `RC28-F17`), and the single decisive missing bridge for the Temporal CST/AST core is `RC28-F13` (`ChangeGrammar` / Pullenti `DecreeChange` pattern -> `MicroOperation` candidates -> compiler fold -> `EditionOracle` check), alongside duplicated `document_context.rs` (`ln-decode` vs `ln-temporal`) and unexecuted `WALK-I/WALK-T` from `edition-0001`.

### Requirements

- **R1 (Governor AGY/CE adaptation):** `law-nexus-harness governor` and `preflight` validate active Compound Engineering and AGY surfaces (`.compound-engineering/config.yaml` `docs_root`, `.compound-engineering/reviews/` naming, `.agents/skills/` freedom from retired `~/.gsd/agent/agents` pointers), update CLI help/remediation hints, and expose `just governor` / `just preflight` without breaking existing `test_harness_*` contracts.
- **R2 (AGY/CE skill hygiene):** `.agents/skills/law-nexus-subagent/SKILL.md` and `.agents/skills/law-nexus-rust/SKILL.md` reflect Antigravity `invoke_subagent` + Compound Engineering conventions with zero live pointers to `~/.gsd/agent/agents/`.
- **R3 (Living truth-oracle grounding):** `prd/ARCHITECTURE.md`, `prd/PRODUCT.md`, `prd/REQUIREMENTS.md`, `doc/adr/README.md`, and affected active ADRs qualify historical `.gsd/*` references as archived under tag `archive/gsd-path-final`, update current-state facts through `1fcb7849` (M175–M225, `reference-package`, Compound Engineering cutover, 0-CVE baseline), and preserve all D098 lifecycle ceilings and non-claims.
- **R4 (Context noise reduction):** `prd/architecture/README.md` provides a concise top-of-file navigation table separating the ~10 living canonical architecture files from historical M001–M225 snapshots/receipts so agents do not ingest archaeological noise by default.
- **R5 (Review & gap reconciliation):** Produce a single concise tracked reconciliation of open review findings (`RC11-F13`, `RC12-F19`, `RC28-F13/F16/F17`, `assessment/34` `semantic_acceptance`/`garant`, `R29-F06`) verified against `HEAD` (distinguishing already-remediated `RC28-F06..F12` from truly missing core pieces), without forging human Review Case dispositions.
- **R6 (Core-first trajectory ADR):** Author `[proposed]` ADR-0032 defining the core-first Temporal CST/AST + Tokenizer/Context + `ChangeGrammar` vertical trajectory (reconciling ADR-0014/0017/0028/0029/0031, explicitly decoupling downstream storage/UI plumbing behind `ln-storage`/`ln-query` ports, and naming the executable vertical spike acceptance criteria on `44-ФЗ` + C1 amending laws + a non-44-ФЗ act).

### Scope Boundaries

- **In scope:** Python control-plane harness (`src/law_nexus_harness/`), `Justfile`, `.agents/skills/`, `prd/ARCHITECTURE.md`, `prd/PRODUCT.md`, `prd/REQUIREMENTS.md`, `prd/architecture/README.md`, `doc/adr/**`, and corresponding Python harness/doc/ADR tests.
- **Out of scope (deferred to subsequent implementation PRs):** Writing Rust `ChangeGrammar` / `MicroOperation` compiler code, merging the two `document_context.rs` modules in Rust, recording human `disposition_recorded` ledger events on `RC-2026-09-10-001`, or adopting a persistent database (RuVector / Oxigraph / SQLite).

## Planning Contract

### Key Technical Decisions

- **KTD1 — Keep legacy GSD checks as `not-applicable` shims while adding first-class `ce-agy-surface` checks:** `tests/test_harness_governor.py` (226 KB) and `tests/test_harness_workflow_state.py` (53 KB) thoroughly test the fail-closed `cutover=true` -> `not-applicable` contract for the 5 retired GSD checks. Rather than deleting them and destabilizing CI, keep them explicitly tagged as retired-legacy compatibility shims and add a new active `[docs]` / `[process]` check group (`ce-agy-surface`) that actively governs `.compound-engineering/config.yaml`, `.compound-engineering/reviews/`, and `.agents/skills/`.
- **KTD2 — Preserve `model-crystal.md` anchor quotes verbatim:** Governor check `model-crystal-anchors` verifies 19 verbatim quotes across 7 source files (`doc/review/review-25-08-2026.md`, `doc/adr/0016..0019`, `prd/temporal-legal-model.md`) and the L0 sha256 digest. Never edit anchored quote lines in those files; only append additive notes or update non-anchored historical `.gsd/DECISIONS.md` citations.
- **KTD3 — Core-first vertical spike as the single decision gate for storage and downstream layers:** ADR-0032 frames the core vertical (`source_package` CST -> `lex` + unified `DocumentContext` + `LocalGrammar` -> `ChangeGrammar` [`DecreeChange` pattern] -> `MicroOperation` -> compiler fold -> `EditionOracle` diff = 0) as the primary proving track. Storage choice (ADR-0014 RuVector vs ADR-0031 M217 bake-off) stays explicitly `[proposed]` behind `ln-storage` ports until the core event/projection shape is proven on real amending acts.

### Sequencing

1. **PR1 (Control plane first):** Adapt `governor`, `preflight`, `Justfile`, and `.agents/skills/` to AGY + CE. Having the upgraded `governor` in place ensures PR2 and PR3 are machine-checked by the updated control plane.
2. **PR2 (Architecture grounding & noise cleanup):** Reconcile living PRD/ADR/review surfaces and add the living-vs-historical index in `prd/architecture/README.md`.
3. **PR3 (Core trajectory ADR-0032):** Author `[proposed]` ADR-0032 + update `doc/adr/README.md` and `prd/ARCHITECTURE.md` ADR table so the next `ce-prototype` / `ce-work` wave can execute the vertical core spike directly against an unambiguous contract.

## Implementation Units

### PR1: Adapt Governor CLI, Preflight, Justfile, and Skills to AGY + CE
Waits on: none (starts directly from `main` @ `1fcb7849`).

#### U1. Add CE/AGY surface governance to `governor`, fix `preflight` & `cli.py`, wire `Justfile`
- **Goal:** Make `governor` and `preflight` actively verify the Compound Engineering + Antigravity workspace contract, fix outdated CLI help/remediation text, and expose `just governor` / `just preflight`.
- **Requirements:** R1
- **Files:** `src/law_nexus_harness/governor.py`, `src/law_nexus_harness/preflight.py`, `src/law_nexus_harness/cli.py`, `Justfile`, `tests/test_harness_governor.py`, `tests/test_harness_preflight.py`, `tests/test_harness_cli_entrypoints.py`
- **Approach:**
  - Add a `ce-agy-surface` check in `governor.py` verifying: (a) `.compound-engineering/config.yaml` parses and sets a repo-relative `docs_root` inside the repo (not `.git/`), (b) `.compound-engineering/reviews/` files follow `YYYY-MM-DD-*.md` naming, (c) active `.agents/skills/*/SKILL.md` files do not reference retired `~/.gsd/agent/agents` paths.
  - Update `cli.py` help strings for `governor` and `review-case` to reference Compound Engineering instead of GSD.
  - Update `preflight.py` `gitnexus-index-freshness` remediation to `node .gitnexus/run.cjs analyze --force --name law-nexus`.
  - Add `governor` and `preflight` recipes to `Justfile`.
- **Test Scenarios:**
  - Positive: `ce-agy-surface` passes on current checkout.
  - Negative/hostile: invalid `docs_root` (escaping repo or `.git/`), malformed review filename, or `~/.gsd/agent/agents` reintroduced into `.agents/skills/*/SKILL.md` fails closed with typed remediation.
  - CLI entrypoint & preflight tests pass with updated help/remediation strings.
- **Verification:** `uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py tests/test_harness_workflow_state.py tests/test_harness_cli_entrypoints.py tests/test_review_case_governor.py && just governor && just preflight`

#### U2. Migrate `.agents/skills/` from GSD-Pi to Antigravity + Compound Engineering
- **Goal:** Eliminate retired `~/.gsd/agent/agents/*.md` instructions from repo skills so AGY agents receive clean, accurate delegation and Rust-harness rules.
- **Requirements:** R2
- **Files:** `.agents/skills/law-nexus-subagent/SKILL.md`, `.agents/skills/law-nexus-subagent/workflows/parent-dispatch.md` (inspect & align), `.agents/skills/law-nexus-rust/SKILL.md`, `pyproject.toml` (keep `.gsd` only if needed for local gitignored scratch, otherwise document cleanly)
- **Approach:** Rewrite `law-nexus-subagent` to target AGY `invoke_subagent` / CE workflows while keeping all durable non-interactive / `BLOCKED` / GitNexus / edit-permission invariants intact; update `law-nexus-rust/SKILL.md` line 12 from "GSD" to "Compound Engineering harness".
- **Test Scenarios:** Verified by `ce-agy-surface` governor check and `tests/test_documentation_navigation.py`.
- **Verification:** `uv run --frozen python -m law_nexus_harness.governor --check ce-agy-surface`

---

### PR2: Ground Living Architecture/PRD/ADR Docs and Clear Context Noise
Waits on: PR1 merged to `main`.

#### U3. Reconcile `prd/ARCHITECTURE.md`, `prd/PRODUCT.md`, `prd/REQUIREMENTS.md`, and active ADRs
- **Goal:** Bring the living truth oracle and product/requirements/ADR references up to `HEAD` without breaking `model-crystal-anchors`, `adr-truth-oracle-sync`, or D098 ceilings.
- **Requirements:** R3
- **Files:** `prd/ARCHITECTURE.md`, `prd/PRODUCT.md`, `prd/REQUIREMENTS.md`, `doc/adr/0004-rust-migration-decision.md`, `doc/adr/0005-rust-target-architecture.md`, `doc/adr/0008-promotion-publication-authority.md`, `doc/adr/0009-five-clock-temporal-model.md`, `doc/adr/0010-evidence-kernel-gates.md`, `doc/adr/0011-kof-da-ownership.md`, `doc/adr/0014-ruvector-primary-infrastructure.md`
- **Approach:**
  - Update `prd/ARCHITECTURE.md` "Where we actually are" and "Current layer" to cover M175–M225, `reference-package`, Compound Engineering cutover, and 0-CVE baseline; replace stale `.gsd/**` prose with `archive/gsd-path-final` archival qualifiers.
  - Note the open storage-choice relationship between ADR-0014 (`RuVector [proposed]`) and ADR-0031 (`M217 store bake-off [proposed]`) explicitly as pending the Temporal CST/AST core proof.
  - Qualify `.gsd/DECISIONS.md` citations in active ADRs and `.gsd/REQUIREMENTS.md` in `prd/REQUIREMENTS.md` as historical records preserved under `archive/gsd-path-final`.
- **Test Scenarios:** `governor` (`adr-truth-oracle-sync`, `adr-link-integrity`, `model-crystal-anchors`, `published-trace-contract`, `temporal-vocabulary-*`), `verify-adr-conformance.py`, `test_verify_adr_conformance.py`, `test_documentation_navigation.py`.
- **Verification:** `uv run --frozen python -m law_nexus_harness.governor --fail-on-warn && uv run --frozen pytest tests/test_verify_adr_conformance.py tests/test_documentation_navigation.py`

#### U4. Curate `prd/architecture/README.md` living-vs-historical map & open-gaps reconciliation
- **Goal:** Cut agent context-loading noise across the 135 files in `prd/architecture/` and publish one verified open-gap table reconciling `RC11/12/28`, `assessment/34`, and `review-29` against `HEAD`.
- **Requirements:** R4, R5
- **Files:** `prd/architecture/README.md`, `prd/architecture/core-gaps-reconciliation.md` (new concise `[bounded]` diagnostic index)
- **Approach:**
  - Add a top-of-file navigation table in `prd/architecture/README.md` separating Living Core Canon (read first) from Historical M001–M225 Snapshots (read on demand).
  - Document the 5 truly open Review Case findings (`RC11-F13`, `RC12-F19`, `RC28-F13/F16/F17`), the 2 open `assessment/34` gaps (`semantic_acceptance`, `garant` corpus quota), `R29-F06`, and the 2 newly surfaced structural debts (duplicated `document_context.rs`, storage-direction fork ADR-0014 vs ADR-0031) with exact `file:line` pointers and non-claims.
- **Test Scenarios:** Full `governor` + `test_documentation_navigation.py`.
- **Verification:** `uv run --frozen python -m law_nexus_harness.governor --fail-on-warn`

---

### PR3: Author Core-First Trajectory ADR (ADR-0032)
Waits on: PR2 merged to `main`.

#### U5. Author `[proposed]` ADR-0032 — Temporal CST/AST Core, Unified Context, and ChangeGrammar Vertical Spike
- **Goal:** Establish the canonical, grounded design decision for proving the normative-act core model before downstream storage/UI investment.
- **Requirements:** R6
- **Files:** `doc/adr/0032-temporal-cst-ast-core-and-change-grammar.md`, `doc/adr/README.md`, `prd/ARCHITECTURE.md`, `prd/architecture/adr-matrix.json` (regenerated via `law-nexus-harness adr-verify --matrix generate --stdout`)
- **Approach:**
  - Define the end-to-end vertical core contract: `source_package` (lossless CST green) -> `lex()` + unified `DocumentContext` (consolidating `ln-decode` and `ln-temporal` duplicates) + `LocalGrammar` + explicit optional `MorphEvidenceSet` -> `ChangeGrammar` (Pullenti `DecreeChange` pattern: `OWNER / KIND / CHILD / VALUE / PARAM / LOCVALUE`, zero copied code/dicts) -> bounded `MicroOperation` subset (`ReplaceText`, `InsertText`, `DeleteText`, `Attach`, `Repeal`) -> deterministic `ThreeCanonEventLog` compiler fold -> `EditionOracle` verification (`drift = 0`).
  - Specify the proving corpus (`44-ФЗ` + C1 amending laws `138-ФЗ` / `333-ФЗ` / `484-ФЗ` + at least one non-44-ФЗ act), metamorphic invariants (`INV-01`, `INV-04`, `INV-06`, `INV-10`), and explicit kill/pivot criteria (e.g., fallback to oracle-diff + provenance if deterministic amendment parse coverage is insufficient).
  - Explicitly decouple downstream storage (ADR-0014 vs ADR-0031 M217) and UI/API work behind existing `ln-storage`/`ln-query` ports so parallel work cannot distort core semantics.
- **Test Scenarios:** `adr-verify --matrix check`, `verify-adr-conformance.py`, `governor --only adr`, full `governor --fail-on-warn`.
- **Verification:** `uv run --frozen python -m law_nexus_harness adr-verify --matrix check && uv run --frozen python -m law_nexus_harness.governor --fail-on-warn && just gate`

## Verification Contract

- **Control-plane & docs (every PR):**
  - `uv run --frozen python -m law_nexus_harness.governor --fail-on-warn` (must exit 0, `error_count=0`, `warn_count=0`)
  - `uv run --frozen python -m law_nexus_harness preflight`
  - `uv run --frozen pytest tests/test_harness_governor.py tests/test_harness_preflight.py tests/test_harness_workflow_state.py tests/test_harness_cli_entrypoints.py tests/test_review_case_governor.py tests/test_verify_adr_conformance.py tests/test_documentation_navigation.py`
- **Repository Tier-1 gate (before each PR merge):**
  - `just gate` (Rust fmt, clippy `-D warnings`, workspace nextest, `cargo deny`, `cargo shear`, `actionlint`, `zizmor`, crate allowlist, ADR conformance)
- **Review discipline (`AGENTS.md`):**
  - Run `ce-code-review` on each PR and archive the final report under `.compound-engineering/reviews/YYYY-MM-DD-<target-slug>.md`.

## Definition of Done

1. `governor` actively validates AGY + Compound Engineering surfaces (`ce-agy-surface`), CLI help/remediation strings are free of retired GSD instructions, and `just governor` / `just preflight` run cleanly.
2. Active `.agents/skills/*` contain zero live `~/.gsd/agent/agents` instructions.
3. `prd/ARCHITECTURE.md`, `prd/PRODUCT.md`, `prd/REQUIREMENTS.md`, `prd/architecture/README.md`, and active ADRs reflect `HEAD` accurately with D098 ceilings intact, `model-crystal-anchors` green, and a clear separation between living canon and historical snapshots.
4. Open review findings and core gaps are reconciled against `HEAD` in one concise tracked index without forging human Review Case events.
5. `[proposed]` ADR-0032 is merged with regenerated `adr-matrix.json`, defining the exact vertical Temporal CST/AST + `ChangeGrammar` proving spike ready for immediate execution via `ce-prototype` or `ce-work`.
