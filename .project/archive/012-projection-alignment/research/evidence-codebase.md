# Evidence — codebase

<!-- Written by the codebase mapper during $gsd-path-inspect. Read by define
     (brownfield mode), researchers (fifth standard dimension), the planner
     (conventions are binding), and reviewers. -->

Repo root: /root/law-nexus
Scanned: 2026-10-31
Checks run:
- `git rev-parse HEAD` (sidecar worktree) -> `ef17106b96e22b01719fc12a28576d226a36d1b8`, branch `gsd-path-verify/inspect-codebase`, clean
- `git log --oneline -25` and date/area census since 2026-09-15 -> recorded below
- `cargo metadata --offline --no-deps --format-version 1` (sidecar) -> exit 0, 47 workspace members resolved, 48 bin targets across 24 packages, all crates edition 2024
- structural file reads: workspace `Cargo.toml`, `rust-toolchain.toml`, per-crate manifests, `src/` listings, `.github/workflows/repository-quality.yml`, `.pre-commit-config.yaml`, `.project/STATE.md` header, sample sources
- `cargo run -q -p ln-product-cli -- health` (sidecar, warm prebuilt `target/debug`, no compilation) -> `{"phase":"Health","status":"ok","binary":"law-nexus-inspect","runtime":"rust","duration_ms":0}`, exit 0, 0.4 s
- No build of unbuilt targets and no test/lint suite was run (dispatch time discipline); suite pass/fail status is therefore not evidenced here.

## Map

- **Stack**: Rust workspace, 47 crates (`crates/ln-*`), all edition 2024, pinned toolchain 1.99.0 (`rust-toolchain.toml`, exact channel with rustfmt+clippy). External dependencies are minimal and non-async: serde, serde_json, sha2, zip, rusqlite (2 members), quick-xml. No HTTP framework, no async runtime, no ORM. A thin Python 3.13 control-plane harness (`src/law_nexus_harness/`, uv-managed, ruff/basedpyright/ty/pyrefly) exists for repository checks only; Python product code is archived (`python_archive/`) and excluded from active lint. Infra: GitNexus index (`.gitnexus`), GSD Path pipeline state (`.project/`, `.gsd-path/`), pre-commit hook chain mirroring CI.
- **Entry points**: product CLI binary `law-nexus-inspect` (`crates/ln-product-cli/src/main.rs`, 1665 lines) with commands `health | inspect <path> | replay <seed> <target> | subordinates <resolution|order> <path> | reference-package <build|check> --corpus-dir --catalog --out-dir`; second bin `hierarchy-registry-generator`. Plus 20 scenario binaries `ln-hc01-runner`..`ln-hc20-runner` (one `main.rs` each) and tracer binary `ln-status` (`status|--fail|sleep|bytes`). 48 bin targets total; `default-run = "law-nexus-inspect"`.
- **Architecture**: hexagonal per crate (ADR-0015): each domain crate exposes `domain / application / ports / adapters` modules; composition happens only at the edges. Dependency flow (from `cargo metadata`): `ln-decode` (parsing foundation, 0 internal deps) <- `ln-consultant-parser` (which also uses `ln-kb-ontology`, `ln-temporal`); `ln-kb-ontology` -> `ln-identity` + `ln-temporal`; `ln-query` -> `ln-decode` + `ln-storage`; `ln-product-cli` is the sole composition root wiring decode + ontology + temporal + storage + query. `ln-storage` ports (`VectorStorePort`, `GraphStorePort`, `EmbeddingPort`) default to in-memory adapters; a TEI HTTP adapter exists (`crates/ln-storage/src/adapters/tei_http.rs`) but the CLI currently injects a hash-derived `StubEmbedding`. `ln-testkit` depends on 22 crates and holds the shared port-contract suites. A request flows: corpus XML/ODT -> decode (blocks, hierarchy, references, temporal phrases) -> ontology lift via registry maps -> temporal fold / query -> JSON report on stdout.
- **Conventions** (binding on the planner): crates `ln-<domain>`; module quartet `domain/application/ports/adapters`; typed errors and fail-closed constructors (e.g. `EmbeddingResponse::try_new` rejects all-zero vectors, `crates/ln-product-cli/src/main.rs:63-70`), numeric exit-code constants (e.g. `EXIT_ARGV`, `EXIT_INPUT` in `ln_consultant_parser::reference_layer`); tests are integration-heavy under `crates/*/tests/*.rs` plus shared `ln-testkit/tests/*_port_contracts.rs` (33 files); lifecycle tags `[bounded]` and explicit "Bounded non-claim" doc comments on scenario code; commit subjects use `type: subject` prefixes in English (`integrate: M011 - ...`, `ship: M011`, `build:`, `T003:`, `docs:`); verification authority is ADR-0015 + `.agents/skills/law-nexus-rust/references/verification-matrix.md` (not restated in overlays); quality gates: `cargo fmt --all --check`, `cargo check --workspace --offline`, `cargo clippy --workspace --offline --all-targets -- -D warnings`, plus a crate-dependency allowlist script and an ADR-conformance script wired into both pre-commit and CI.
- **Maturity**: the workspace resolves offline and CI (`.github/workflows/repository-quality.yml`, 6 jobs) runs the full `cargo test --workspace --offline` on every PR, plus corpus-integration and offline-contract-verifier jobs — so a complete suite exists but was not executed for this Map. Test mass is concentrated where the code is: `ln-decode` 117 test files (~53.2k test LOC vs ~54.6k src LOC), `ln-consultant-parser` 50 files (~14.0k vs ~27.3k), `ln-temporal` 38 files, `ln-kb-ontology` 37 files; the 20 small domain crates carry 1-7 test files each. The Python harness has ~70 pytest files under `tests/` at the repo root. Scaffolding / stubs: CLI embedding is hash-stubbed; storage adapters are in-memory by default; hc16-hc20 runners have no tests directory.
- **Recent activity**: 2026-10-05 through 2026-10-31 (350+ commits in the window); heaviest days 10-25..10-31 (M010 `doc-consistency` and M011 `reference-front-door` shipped and integrated; HEAD is the M011 integration commit). Changed-path census since 2026-10-01: `crates/ln-decode` (345 paths: 188 tests + 157 src), `.project/` pipeline state (~330 across tasks/research/review/build/plan/archive), `crates/ln-consultant-parser` (111), `prd/` architecture evidence (~133), `tests/` (75). Work is concentrated on the parser front-door (decode/consultant-parser) and reference knowledge layer (ADR-0031).

## Finding: Two parser crates hold ~70% of all product code

- **Claim**: `ln-decode` (80 src files, 54,616 LOC) and `ln-consultant-parser` (45 src files, 27,267 LOC) contain 81,883 of 116,581 total workspace src LOC (~70%); the remaining 45 crates average well under 1,000 LOC of src each.
- **Source**: recursive `.rs` line census over `crates/*/src` (python os.walk, this session); counts also visible from `cargo metadata` member list.
- **Confidence**: high
- **Why it matters here**: a planner reading the crate list would assume 47 comparable units; effort, review time, and risk are actually concentrated in two crates, and any milestone touching "the parser" is touching a ~82k-LOC surface.

## Finding: ln-decode is a zero-internal-dependency foundation crate

- **Claim**: `ln-decode` depends on no other workspace crate; its only external deps are quick-xml, serde, serde_json, sha2, zip. `ln-consultant-parser` depends on ln-decode, ln-kb-ontology, ln-temporal (plus rusqlite); `ln-query` on ln-decode + ln-storage; nothing depends on `ln-consultant-parser` except `ln-product-cli`.
- **Source**: `cargo metadata --offline --no-deps` dependency edges (sidecar run, exit 0).
- **Confidence**: high
- **Why it matters here**: the layering rule "parser below ontology" is enforced by Cargo, not by convention; new work that wants decode-level primitives must go through the existing crates or break the allowlist gate (`scripts/verify-crate-dependency-allowlist.py` runs in CI and pre-commit).

## Finding: Semantic embedding is stubbed in the product CLI; TEI adapter exists but is not the wired default

- **Claim**: `law-nexus-inspect` injects `StubEmbedding`, producing deterministic hash-derived f32 vectors; its doc comment states "Real semantic embedding requires TEI infrastructure (not available). Lifecycle [bounded]." `ln-storage` ships `adapters/tei.rs` and `adapters/tei_http.rs`, but the CLI wires `InMemoryVectorStore`/`InMemoryGraphStore` plus the stub.
- **Source**: `crates/ln-product-cli/src/main.rs:51-104` (StubEmbedding, deterministic_vector, [bounded] comment); `crates/ln-storage/src/adapters/` listing.
- **Confidence**: high
- **Why it matters here**: any milestone assuming working retrieval/semantic search would be wrong; ranking runs over pseudo-vectors. Real embedding is gated on external TEI infrastructure and possibly RuVector (ADR-0014, marked [proposed] in AGENTS.md).

## Finding: hc16-hc20 runner crates have no tests directory

- **Claim**: `ln-hc01-runner`..`ln-hc15-runner` each carry `tests/verdict_contract.rs` + `tests/cli_contract.rs`; `ln-hc16-runner`..`ln-hc20-runner` have no `tests/` directory at all.
- **Claim source**: directory listings of `crates/ln-hcNN-runner/tests` (this session).
- **Confidence**: high
- **Why it matters here**: a half-built tail: five scenario binaries exist and compile (cargo metadata includes their bins) but have no contract tests, which contradicts the repo's own "port contracts for >1-adapter ports" contour and may be either deliberate scope-cut or unfinished work — worth one define question.

## Finding: 20 single-scenario binaries mirror 20 small domain crates one-to-one

- **Claim**: each `ln-hcNN-runner` depends on exactly one domain crate (hc01->ln-observe, hc02->ln-inventory, ... hc20->ln-conformance, per cargo metadata edges), and each is a self-contained `main.rs` running hard-case scenarios over in-memory adapters (e.g. hc04 exercises `CommitCuratedPromotion` with `InMemoryPromotionStore`).
- **Source**: `cargo metadata` internal-dep edges; `crates/ln-hc04-runner/src/main.rs`.
- **Confidence**: high
- **Why it matters here**: these are verification/demonstration harnesses per architectural case, not product features; the planner should not treat 20 binaries as 20 shipping surfaces, and new domain crates appear to follow the pattern crate + runner + testkit contract.

## Finding: Python is a control-plane harness with an enforced boundary

- **Claim**: active Python (`src/law_nexus_harness/`, entry `law-nexus-harness` console script) provides review-case FSM/ledger, governor checks, preflight, ADR-matrix tooling; a dedicated test (`tests/test_harness_no_forbidden_imports.py`) and CI job structure enforce that no product logic lives in Python; `python_archive/` is excluded from lint as archived prior art.
- **Source**: `src/law_nexus_harness/cli.py` imports; `tests/test_harness_no_forbidden_imports.py` exists; `.pre-commit-config.yaml` comments and excludes; `.github/workflows/repository-quality.yml` job names/comments.
- **Confidence**: high
- **Why it matters here**: milestones must not add Python product behavior; the boundary is tested, so violating it fails CI rather than merely breaching a doc.

## Finding: repository scripts are dominated by milestone evidence batteries

- **Claim**: `scripts/` holds 319 files, of which ~238 are milestone-prefixed verify/battery scripts (m204: 113, m210: 34, m207: 30, m209: 23, m205: 8, m206: 6, m223: 6, others) plus ~67 `test_m*` unit scripts and a small set of standing verifiers (`verify-*.py`).
- **Source**: `os.listdir('scripts')` prefix census (this session).
- **Confidence**: high
- **Why it matters here**: this is the repo's evidence convention — each milestone/step lands a `mNNN_sTT_*_verify` script referenced from CI; a new milestone should follow or explicitly change this pattern rather than invent a new evidence layout.

## Finding: CI is a single 6-job quality gate including full workspace tests and corpus integration

- **Claim**: `.github/workflows/repository-quality.yml` defines jobs: python-harness-quality, rust-harness-quality (fmt + offline check + clippy -D warnings + build + `cargo test --workspace --offline`), migration-layer-quality, corpus-integration (corpus-dependent contract tests, guarded), offline-contract-verifiers (m207 frozen batteries, documented exit 0/3). CI restores a pinned, digest-verified GSD Path runtime archive (`.ai/vendor/gsd-path-1.6.2.tgz`) and full git history/tags for shipped-main proofs.
- **Source**: `.github/workflows/repository-quality.yml` (20,708 bytes; job/step listing this session).
- **Confidence**: high
- **Why it matters here**: the real execution authority lives here; per-diff "tiny edit" runs must respect INTENT limits on not running the full suite, while the gate itself expects the full offline suite to pass on main.

## Finding: pipeline state confirms this inspect phase is the active step

- **Claim**: `.project/STATE.md` frontmatter reads `pipeline: gsd-path/v2`, `phase: inspect`, `branch: gsd-path/M012`, `milestone: null`, `status: active`, with log entries from 2026-10-25..10-26; the working tree HEAD is the M011 integration commit on main history.
- **Source**: `.project/STATE.md` head (this session); `git log` at HEAD `ef17106b`.
- **Confidence**: high
- **Why it matters here**: the brownfield rescan target is a repo that just shipped M011 ("reference-front-door") and M010 ("doc-consistency"); M012 intent will be defined against that fresh state.

## Finding: conventions encode fail-closed evidence discipline in comments and types

- **Claim**: sources repeatedly pair typed constructors with fail-closed rationale comments referencing prior incident classes (e.g. "never a silent all-zero vector (MEM676 fake-cascade class)" in `ln-product-cli/src/main.rs:63-66`) and declare scope with `[bounded]` / "Bounded non-claim" markers (e.g. `replay` doc comment, `main.rs:117-121`).
- **Source**: direct reads of `crates/ln-product-cli/src/main.rs` and `crates/ln-hc04-runner/src/main.rs` this session.
- **Confidence**: high
- **Why it matters here**: reviewers and coders are expected to preserve these markers; silently widening a "bounded non-claim" is a review finding, and the pattern is the repo's honesty mechanism.

<!-- Record every load-bearing surprise or half-built area observed. There is
     no minimum finding quota; explain an empty section if none were found. -->

## Apparent intent

<!-- Inference, clearly flagged - what the project seems to be becoming. -->

- <inference> The project is becoming an offline-first, hexagonally verified Rust legal-analytics pipeline over the Consultant XML corpus: parse (ln-decode, ln-consultant-parser) -> identity/temporal/ontology modeling (ln-identity, ln-temporal, ln-kb-ontology) -> retrieval/query (ln-storage, ln-query) -> one CLI composition surface (law-nexus-inspect), with all external infrastructure (TEI embeddings, vector/graph stores) currently in-memory or stubbed and fail-closed — based on dependency edges, the StubEmbedding comment, in-memory default adapters, and the near-zero external dep census.
- <inference> Capability expansion is evidence-driven and case-by-case: hard cases mint a small domain crate + hcNN runner + testkit port contract + milestone verify scripts, rather than growing a monolith — based on the 1:1 crate/runner mapping, testkit's 33 contract suites, and the 238-script milestone battery convention.
- <inference> The near-term direction is the reference knowledge layer ("reference front-door", ADR-0031 + M011 + reference-package CLI subcommand + m224 pageindex/FRBR scripts), i.e. consolidating how references/anchors/page indexes enter the knowledge base — based on the two most recent shipped milestones and the newest CLI surface (`reference-package build|check` added in T001 of M011 per commit log).

## Open questions for define

<!-- What only the user can settle about this codebase. -->

- What should milestone M012 deliver — continuation of the reference knowledge layer (ADR-0031), or a different capability? (define owns intent; the codebase only shows where the last milestones landed.)
- Is the testless hc16-hc20 runner tail intended to gain `verdict_contract.rs`/`cli_contract.rs` like hc01-hc15, or are those scenarios complete as-is?
- When do real semantic embeddings / persistent stores (TEI, RuVector per ADR-0014) come in scope, and is SQLite (rusqlite, already used by `catalog_sqlite.rs` in ln-consultant-parser) the sanctioned persistence step toward that, or a local-only catalog detail?
- Should the 20-crate + 20-runner pattern continue for new capability areas, or is consolidation desired?

## Blocked areas

<!-- What could not be inspected and why. "none" if clean. -->

- Test/execution status of the Rust and Python suites — not run by dispatch time discipline; only `cargo metadata --offline` and the one-command `law-nexus-inspect health` smoke (exit 0) were executed in the sidecar. The orchestrator's verify sidecar owns any fuller execution evidence.
- Corpus data directories (`consru_export/` 43,785 files, `law-source/`) — data, not code; scanned only at listing level per the repo data-sources map (full corpus lives in `consru_export/exports/`, not `law-source/`).
- `.project/` pipeline internals beyond STATE.md, `python_archive/`, `.lex/`, `Old_project/`, archives — excluded by dispatch rule / docs auditor's domain.
