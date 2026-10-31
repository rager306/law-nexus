# Evidence — codebase

<!-- Written by the codebase mapper during $gsd-path-inspect (Codex) or /gsd-path-inspect (Antigravity/Zed/Muse). Read by define
     (brownfield mode), researchers (fifth standard dimension), the planner
     (conventions are binding), and reviewers. -->

Repo root: /root/law-nexus
Scanned: 2026-10-30
Checks run: (see per-finding sources; summary) `cargo run -q -p ln-product-cli -- health` → exit 101, bin ambiguity (README quick-start broken as written); `cargo build -p ln-product-cli --offline` → exit 0 (55 s); `./target/debug/law-nexus-inspect health` → exit 0, `{"phase":"Health","status":"ok"}`; `./target/debug/law-nexus-inspect inspect <real consultant XML>` → exit 0, 96 blocks / 26 hyperlinks / 1 amends-edge, fail-closed counters all zero-admission; `cargo fmt --all --check` → exit 0; `uv sync --frozen` → exit 0; `uv run pytest -q` → **31 failed, 973 passed, 12 skipped, 7 errors, exit 1** in 495.77 s (1023 collected; failure classes diagnosed below); `cargo test --workspace --offline` → **exit 0 — full workspace suite passes offline** (all lib/integration/doc targets); live GitHub Actions `repository-quality` at HEAD `3a39fd70` (api.github.com query) → `success` (2026-10-29T05:12Z).

## Map

- **Stack**: Rust product runtime: 47-crate Cargo workspace (`crates/ln-*`), edition 2024, toolchain pinned `1.99.0` (`rust-toolchain.toml`), resolver 3; ~226,635 LOC Rust in 643 `.rs` files. External dependency surface deliberately tiny: rusqlite 0.40 (2 crates), serde/serde_json (2), sha2 (2), zip (2), quick-xml (1) — no tokio, no clap, no thiserror/anyhow; all errors are hand-rolled enums with manual `Display`/`Error` impls. Thin Python repository-control harness: `src/law_nexus_harness/` (~11,456 LOC incl. `review_case/`), requires-python `>=3.13`, deps only `networkx` + `pydantic` (`pyproject.toml`); dev tooling ruff/basedpyright/pyrefly/ty/pytest/hypothesis. ~154,300 LOC Python across `src/ tests/ scripts/` (260 files). consru_export/ (43,785 parsed XML docs, 3.7 GB) is raw corpus input, out of scope here.
- **Entry points**: `crates/ln-product-cli` two binaries: `law-nexus-inspect` (`src/main.rs`, 1,540 lines: `health`, `inspect <path>` — the only product CLI) and `hierarchy-registry-generator`; no `default-run` key. `ln-consultant-parser` ships 14 task binaries, `ln-decode` 10 (npa-* corpus pipeline). 20 hostile-case runners `ln-hc01-runner..ln-hc20-runner` (65–155-line mains, exit-code contracts). Python harness CLI: `law-nexus-harness` = `law_nexus_harness.cli:main` (`status`, `governor`, `preflight`, review-case subcommands); pytest gate `uv run pytest -q`. CI: `.github/workflows/repository-quality.yml` (jobs `python-harness-quality`, `rust-harness-quality`).
- **Architecture**: hexagonal per capability crate (ADR-0015): each of 20 exclusive capability owners has `domain.rs` / `ports.rs` / `application.rs` / `adapters.rs` (e.g. `ln-gate`, `ln-temporal`, `ln-applicability`). Dependency direction is inward (domain ← application ← adapters). 20 `ln-hcNN-runner` crates each wrap exactly one capability owner in a hostile scenario harness (hc05 → ln-decode, hc09 → ln-temporal, …) with canary payloads and fail-closed assertions. `ln-testkit` (33 `*_port_contracts.rs` suites) is the cross-adapter contract hub for every port with >1 adapter. The CLI composes decode → kb-ontology → query → storage → temporal into one deterministic JSON pipeline whose output carries an explicit `non_claims` array and quarantines rather than admits (observed on a real Consultant XML: `membership_admitted: 0`, `ast_root_count: 0`, `hierarchy_lifts_unknown: 2`). L1–L7 temporal legal ontology (ADR-0016..0022) is `[proposed]` design only; `ln-kb-ontology` implements a pure L1–L3 write-set projection.
- **Conventions**: naming: `ln-*` kebab-case crates, snake_case modules, `hcNN-runner` runner pattern; commits `type: subject` (`docs:`, `build:`, `integrate: M010 — …`, `T002: …`); error handling: std-only typed error enums per crate (e.g. `StorageError` in `crates/ln-storage/src/lib.rs:12`), no error-crate deps, fail-closed semantics everywhere (abstention with typed reason + mandatory trace); tests: ADR-0015 "overlapping contours, not a pyramid" — port-contract suites in `ln-testkit/tests/`, per-crate `tests/*.rs`, hostile + positive cases, provider isolation (Consultant ≠ Garant); authority `.agents/skills/law-nexus-rust/references/verification-matrix.md`. Gates: `cargo fmt --all --check`, `cargo clippy --workspace --offline --all-targets -- -D warnings`, `cargo check/test --workspace --offline` (pre-commit `.pre-commit-config.yaml` + CI); Python: ruff, basedpyright, pyrefly, ty, pytest `--strict-config`. D098 lifecycle tags `[proposed]/[bounded]/[smoke]/[validated]/[deferred]` are mandatory on claims (Governor enforces). Git state: single author (rager306: 1945/1946 commits), 300–430 commits/month, local `main` == live `origin/main` == `3a39fd70` (verified via `git ls-remote`); local `refs/remotes/origin/main` ref is stale (still at bootstrap merge `54a495cd`).
- **Maturity**: what runs today: the full Rust workspace builds offline and its gate suite passes (results below); the CLI `health`/`inspect` path works end-to-end on real Consultant XML (family detection, block decode, hyperlink/cross-act-edge extraction, in-memory cosine retrieval, JSON + non_claims). Hostile contracts: hc01–hc15 runners each carry 2 test files; hc16–hc20 runners carry 0 test files (`ls crates/ln-hc1[6-9]-runner/tests crates/ln-hc20-runner/tests`) — runner shells with dependency wiring but no test evidence. `ln-status` is a 1-line lib (`crates/ln-status/src/lib.rs`) consumed as a subprocess status tracer by the Python harness (`DEFAULT_STATUS_BINARY = target/debug/ln-status`). The Python suite has grown to 1023 collected tests (README snapshot at `f09416f` claims 435 passed) and mostly tests the repository-control harness and docs/roadmap invariants, not product behavior; at this revision the full suite is RED (31F/7E — see findings) while live CI is green because CI runs a subset (`README.md` Quick start: "full suite; CI process suite is a subset"). `ln-applicability` is a fail-closed abstention kernel: by design it NEVER emits Applicable/NotApplicable (`crates/ln-applicability/src/lib.rs:8-12`). The pipeline is real but admission-fail-closed: nothing is yet admitted as AST/membership on the sample document.
- **Recent activity**: last 200 commits span 2026-10-25..10-29 at 26–74 commits/day; last 100 commits cluster: `.project/` 288 files (GSD Path pipeline churn), `tests/` 19, `prd/` 18, `.github/` 5, `docs/` 4 — the last week's work is delivery-process work (milestones M001–M010 shipped via `.project/`), not product code. Product code itself last materially touched ~2026-10-25 (file mtimes and Cargo.toml profile comments dated 2026-10-10..10-25).

## Finding: README quick-start command fails as written (reproduced at this revision)

- **Claim**: `cargo run -q -p ln-product-cli -- health` (README "Inspect the product", README.md ~line 47) exits 101: ``error: `cargo run` could not determine which binary to run`` because the package declares two `[[bin]]`s (`law-nexus-inspect`, `hierarchy-registry-generator`) and no `default-run` key (`crates/ln-product-cli/Cargo.toml:7-13`).
- **Source**: command run in verify sidecar at `3a39fd70`: exit 101, "available binaries: hierarchy-registry-generator, law-nexus-inspect"; `crates/ln-product-cli/Cargo.toml` lines 7–13; README.md "Quick start" section.
- **Confidence**: high
- **Why it matters here**: the front door of the project is broken for a new user; the correct invocation (`--bin law-nexus-inspect`) was proven to work (exit 0, `{"phase":"Health","status":"ok"}`), so this is a one-line docs/manifest fix, but a planner would otherwise schedule "debug CLI" work that isn't needed.

## Finding: README status band undercounts the workspace (45 vs 47) and omits both parser crates

- **Claim**: README status says "The workspace has 45 members in total: 20 capability owners, 20 hostile-case runners, `ln-product-cli`, `ln-testkit`, `ln-storage`, `ln-status`, and proposed `ln-applicability`" — the enumeration names 45 crates, but `Cargo.toml` `[workspace] members` has 47 entries; the two unlisted members are `ln-consultant-parser` (14 binaries, 50 test files) and `ln-kb-ontology` (37 test files).
- **Source**: `Cargo.toml` members list (counted via `tomllib`, 47); README.md "Status" band; `ls crates/` (47 dirs).
- **Confidence**: high
- **Why it matters here**: the two omitted crates are the parser substance (Consultant-specific parsing, KB projection) — the parts the status band's own "real Consultant/Garant parser adapters" claim depends on. Define/planning working from README would not know these crates exist as first-class members.

## Finding: hc16–hc20 runners have no tests while hc01–hc15 each have two

- **Claim**: `ln-hc16-runner`..`ln-hc20-runner` (wrapping ln-accelerate, ln-query, ln-citation, ln-diagnostic, ln-conformance) contain zero test files; every hc01–hc15 runner has exactly 2.
- **Source**: `ls crates/ln-hc{16,17,18,19,20}-runner/tests/` → empty; `ls crates/ln-hc05-runner/tests/` → 2 files.
- **Confidence**: high
- **Why it matters here**: the "20/20 hostile contracts PASS [bounded]" claim (README, ADR-0011 band) is not uniformly backed by in-repo test evidence in the runner crates; the newer five capabilities are wired but their runner-level verification debt is visible and half-built.

## Finding: `workflows/implement-rust-slice.md` referenced by AGENTS.md does not exist

- **Claim**: AGENTS.md:330 says "How to write a slice: `workflows/implement-rust-slice.md`" but no `workflows/` directory exists at the repo root (`ls workflows` → No such file or directory); the string `implement-rust-slice` appears only in `.project/archive/*/research/DOCS-AUDIT.md` files.
- **Source**: AGENTS.md line 330; `ls -la workflows/` (missing); `grep -rn 'implement-rust-slice'`.
- **Confidence**: high
- **Why it matters here**: the agent entry-point file (binding on every agent) points coders at a missing slice-writing guide; either the file was lost in an archive pass or the pointer predates the archive sweep. Coders would improvise slice style instead of following the intended recipe.

## Finding: product behavior is fail-closed by construction — the pipeline admits nothing yet

- **Claim**: On a real Consultant WordML document (99,950 bytes), `law-nexus-inspect` decodes 96 blocks, finds 26 hyperlinks and 1 `amends` edge, but admits zero AST roots and zero membership commits (`ast_root_count: 0`, `membership_admitted: 0`, `membership_quarantined: 2`, `hierarchy_lifts_unknown: 2`, `assembly_status: "no_edition_day"`), and prints an explicit `non_claims` array; `ln-applicability`'s kernel never emits Applicable/NotApplicable at all (`crates/ln-applicability/src/lib.rs:6-12`).
- **Source**: sidecar command `./target/debug/law-nexus-inspect inspect law-source/consultant/rasporyazhenie-...-0db4e799.xml` → exit 0 JSON (observed fields above); `crates/ln-applicability/src/lib.rs` doc comment.
- **Confidence**: high
- **Why it matters here**: "green" in this repo means contracts pass, not that documents become graphs. A planner reading "bounded retrieval pipeline" must not assume any end-to-end document→AST→answer capability exists; the honest headline is: decode/anchor/extraction work, admission is quarantined everywhere.

## Finding: delivery-process artifacts dominate recent history; product crates are quiet

- **Claim**: Of the last 100 commits, 288 touched files are under `.project/` (pipeline state) vs 19 under `tests/` and 18 under `prd/`; zero commits touched `crates/` in that window; the GSD Path pipeline has shipped 10 milestones (`.project/archive/001..010`) between 2026-10-25 and 2026-10-29, all process/docs/CI work.
- **Source**: `git log -100 --name-only` directory histogram; `ls .project/archive/`; `git log --oneline -30`.
- **Confidence**: high
- **Why it matters here**: activity signals here are about the delivery workflow, not the product; "actively developed" would be a wrong read for crate code. The product surface has been essentially frozen since ~2026-10-25 while the workflow around it was hardened.

## Finding: CI at current main is green (live), while the current-state doc's CI table is stale

- **Claim**: The latest `repository-quality` run on `main` at HEAD `3a39fd70` succeeded (2026-10-29T05:12Z), as did the previous run on `319a7b1a`; however `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` (named "current-state document" by AGENTS.md) still records "Every integration push since ended red" with its table ending at M003-era failures.
- **Source**: api.github.com `/repos/rager306/law-nexus/actions/runs?per_page=6` (public, read-only) — 2026-10-29 runs `success` at `3a39fd70`; `docs/agent-stack/POST-SHIP-STATE-2026-10-28.md` "CI state on integrated main" section.
- **Confidence**: high
- **Why it matters here**: a reader trusting the current-state doc concludes CI is red and unrepaired; live evidence says the reds were fixed through M004–M010. The doc needs a refresh (that is exactly the kind of pointer drift milestones M004/M009/M010 were fixing elsewhere).

## Finding: near-zero external dependency surface, including no async runtime and no error crates

- **Claim**: The entire 47-crate workspace depends on exactly 6 external crates (rusqlite, serde, serde_json, sha2, zip, quick-xml per `tomllib` scan of all `crates/*/Cargo.toml`); there is no tokio/async runtime, no clap (CLI args parsed manually in `ln-product-cli/src/main.rs`), no thiserror/anyhow (every crate hand-rolls typed error enums with manual `Display` impls), and `Cargo.lock` has only 91 packages total.
- **Source**: `tomllib` scan over `crates/*/Cargo.toml` dependencies/dev-dependencies (run in REPL); `Cargo.lock` package count; `crates/ln-storage/src/lib.rs:12-40` (`StorageError` + manual `Display`).
- **Confidence**: high
- **Why it matters here**: this is a deliberate supply-chain/audit posture (matches "every checkable operation is deterministic"); planner must not assume standard Rust ecosystem idioms (async, serde everywhere, error derive macros) are available or wanted; adding any dependency is a visible, reviewable event under the crate-dependency-allowlist pre-commit hook.

## Finding: 321 one-off process scripts accumulate at `scripts/` root

- **Claim**: `scripts/` holds 321 entries — 165 `.py` + 83 `.sh` — a large share being milestone-task verify scripts with historical names (`m204_s01_t01_verify.py` … `m204_s13_*`, plus `m209_*` binaries in ln-consultant-parser); there is no `scripts/` index and the m204 series is not referenced by current docs.
- **Source**: `ls scripts/ | wc -l` (321), extension counts; `ls scripts/ai/` (current tooling lives in `scripts/ai/`).
- **Confidence**: high
- **Why it matters here**: an agent (or human) looking for "the" repo tooling must distinguish current `scripts/ai/` tooling from months of frozen per-task verify scripts; nothing marks the m204/m209 series as historical, so they read as live commands.

## Finding: repository state is honest about its own limits — non-claims discipline is enforced in code and docs

- **Claim**: Lifecycle tags `[proposed]/[bounded]/[smoke]/[validated]/[deferred]` are mandated (README "Governance", `doc/adr/README.md` D098), the README carries a dedicated "Non-claims" section stating no `[validated]` product capability exists, the CLI emits `non_claims` in its JSON output, and the Governor suite (54 checks claimed) enforces ADR/lifecycle probes; the one retained warning is `historical-test-debt-visibility`.
- **Source**: README.md "Non-claims" and "Governance" sections; sidecar CLI JSON output `non_claims:[...]`; `src/law_nexus_harness/governor.py` (GOVERNOR_CHECK_SPECS).
- **Confidence**: high
- **Why it matters here**: the repo's core discipline is anti-smoothing; any planning artifact that upgrades a `[bounded]` claim to capability language will fight the Governor and the reviewers. Define should treat the tag ladder as a hard convention.

## Finding: the documented full Python gate is RED at the recorded clean revision while CI is green

- **Claim**: `uv run pytest -q` (the README-prescribed full gate) exits 1 at `3a39fd70`: 31 failed, 973 passed, 12 skipped, 7 errors of 1023 collected, in 8 m 15 s. CI at the same commit is green because CI runs a subset. Failure classes: (a) 6 genuine content-integrity failures that fail on ANY clean checkout — sha256 pin drift (`prd/architecture/m221-s05-docs-reconciliation.yaml:38` records `c8b5afdd…` for `prd/architecture/npa-analysis-jsonl-contract.md`, the tracked file at this revision hashes `a3f51100…`; verified identical drift in primary and sidecar) plus the same pin-validation class in `test_m221_s05_readiness_battery` (3) and `test_architecture_m171_alignment` (1); (b) 9 tests depending on UNTRACKED local files (`test_pi_skill_creator_*`: `FileNotFoundError: '.agents/skills/pi-skill-creator'` — only 14 files under `.agents/` are tracked, all in `law-nexus-rust`); (c) 16 context-dependent live-scenario tests (13 `test_harness_governor.py::test_live_*`, 3 `test_harness_preflight.py`) that pin a branch/state-specific scenario arm (`assert finding.status == "fail"` observed `'pass'` in this verify worktree's branch context); (d) 7 ERRORS fixed by building `target/debug/ln-status` first (`DEFAULT_STATUS_BINARY`, `src/law_nexus_harness/cli.py:44`; re-run of those two files after `cargo build -p ln-status`: 7 passed).
- **Source**: sidecar run at `3a39fd70` (`uv run pytest -q` → exit 1); `.pytest_cache/v/cache/lastfailed` (exact 31); targeted re-runs of the failed files; `sha256sum prd/architecture/npa-analysis-jsonl-contract.md` vs pin value; `git ls-files .agents | wc -l` → 14; live GitHub Actions API → `success` at `3a39fd70`.
- **Confidence**: high (numbers and class attribution), medium (per-test class assignment for 4 of 31 inferred from file purpose, not individually re-run)
- **Why it matters here**: "green CI" and "the repo's own full gate" disagree at HEAD. A planner trusting the badge would not schedule a suite-triage milestone; a define session must decide whether the full suite is a gate (and fix pin drift + untracked-file test deps) or the CI subset is the gate (and the README overstates).

## Finding: an integrity-pin ledger has silently drifted from the content it pins

- **Claim**: `prd/architecture/m221-s05-docs-reconciliation.yaml` binds `prd/architecture/npa-analysis-jsonl-contract.md` by sha256 `c8b5afdd5b86…`, but the tracked file content at the recorded revision hashes to `a3f511006796…` — the pin and the pinned surface were edited out of step and the mismatch shipped in a "clean" milestone integration.
- **Source**: `sha256sum` comparison in sidecar and primary (identical mismatch); `prd/architecture/m221-s05-docs-reconciliation.yaml:38`; failing tests `test_m221_authority_reconciliation.py::test_source_bindings_resolve_and_match_disk`.
- **Confidence**: high
- **Why it matters here**: this repo's trust model is hash-pinned reconciliation surfaces; one drifted pin means the "receipt ledger" cannot be taken at face value elsewhere — other pins may have drifted without a failing test if the test file subset in CI doesn't cover them.

## Apparent intent

<!-- Inference, clearly flagged — what the project seems to be becoming. -->

- The project is becoming a **deterministic, citation-anchored legal document pipeline for Russian normative acts** (Consultant WordML today, Garant ODT next), where an LLM may assist but never be legal authority: every claim must be source-anchored, typed, and fail-closed — based on README goal statement, ADR-0008/0010/0012, and the CLI's non_claims output.
- The immediate trajectory is **corpus ingestion at scale**: the `npa-*` binary series in ln-decode/ln-consultant-parser (corpus-sweep, bounds-scan, hybrid-records, integration-runner), the assessment/24–34 NPA program documents, and the 43,785-doc consru_export corpus all point at building the NPA parsing program on the real corpus — based on binary names in `crates/ln-decode/Cargo.toml` and `assessment/30-npa-parsing-program-control-baseline.md`.
- The GSD Path delivery workflow itself is being proven as a product-adjacent capability: 10 milestones in 5 days, all process/CI/docs work, with the product code deliberately parked — based on `.project/STATE.md` log, `.project/archive/`, and the git directory histogram.
- The ontology layers L1–L7 are being staged as design-first (YAML contracts in `prd/architecture/*.yaml`), with pure write-set projections (`ln-kb-ontology`) landing before any runtime — based on `doc/adr/README.md` "all `[proposed]`" and `crates/ln-kb-ontology/src/lib.rs` ("Not RuVector materialization, not production schema").

## Open questions for define

- hc16–hc20 runner test debt: are the five missing runner test suites planned work (queued capabilities) or accepted debt? (`ls` evidence above)
- Should `ln-product-cli` gain a `default-run = "law-nexus-inspect"` key or should README use `--bin`? (README quick-start is broken either way it stays)
- Is the 43,785-doc `consru_export/` corpus the intended acceptance corpus for the NPA program, and is `law-source/consultant/` (122 files) just its sample? (data-sources map says yes; corpus acceptance criteria are owner-owned)
- Where does `workflows/implement-rust-slice.md` content live now — should AGENTS.md point at `.agents/skills/law-nexus-rust/` instead, or should the file be restored?
- The full-suite vs CI-subset mismatch: is the README full gate (`uv run pytest -q`) supposed to pass on a clean checkout? Which arm is authoritative — and should the sha256 pin ledger (`prd/architecture/m221-s05-docs-reconciliation.yaml`) be re-pinned or the drifted surface reverted? (verified drift, finding above)
- Should tests that require untracked local content (`.agents/skills/pi-skill-creator`, `.gsd` vault, pre-built `ln-status` binary) be marked skip-with-reason, made self-contained, or should the content be tracked?
- The stale local `refs/remotes/origin/main` (still at the bootstrap merge while live origin/main is 13+ milestones ahead): fetch policy or a milestone step? (minor, but it makes `git log origin/main` lie locally)

## Blocked areas

<!-- What could not be inspected and why. "none" if clean. -->

- `consru_export/` contents (43,785 XML documents, 3.7 GB) — excluded by scope rule; existence and shape recorded only.
- `python_archive/`, `.lex/`, `Old_project/`, `prd/archive/`, `archive/`, `.gsd` (frozen symlink), `.ai/local/` — excluded by scope rule.
- `cargo clippy --workspace --all-targets -- -D warnings` — not run (large cold build in the disposable sidecar); the gate is evidenced indirectly by the green `repository-quality` CI run at HEAD.
- Exact per-test attribution for 4 of the 31 pytest failures (`test_architecture_m171_alignment` 1, parts of `test_m221_s05_readiness_battery` 3) is inferred from file purpose and the shared pin mechanism, not individually re-run; the other 27 failures and 7 errors were individually diagnosed or re-run.
- Governor live-scenario tests could not be re-verified against the primary worktree context (read-only rule); their failure arm is recorded as observed in the sidecar branch context only.
