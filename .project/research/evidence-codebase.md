# Evidence — codebase

<!-- Written by the codebase mapper during $gsd-path-inspect (Codex) or /gsd-path-inspect (Antigravity/Zed/Muse). Read by define
     (brownfield mode), researchers (fifth standard dimension), the planner
     (conventions are binding), and reviewers. -->

Repo root: /root/law-nexus
Scanned: 2026-10-25
Checks run: `cargo fmt --all -- --check` → exit 0, clean · `cargo test -p ln-status --offline` → 3 passed / 0 failed · `cargo check -p ln-consultant-parser --offline` → clean (also compiled ln-decode + deps, 23.8 s) · `cargo build -p ln-status --offline` → ok (2.7 s) · `uv sync --frozen` → ok (Python 3.13.12 env) · `uv run pytest -q tests/test_harness_cli_entrypoints.py tests/test_harness_status_tracer.py` → first run 2 passed + 2 errors (missing prebuilt `target/debug/ln-status`); after `cargo build -p ln-status` → 4 passed / 0 failed · `uv run python -m law_nexus_harness.governor` (JSON to /tmp) → exit 1: 71 pass, 0 warn, 1 fail (`workflow-state-surface.blocking`, branch-ownership conflict — see Finding 5) · static: git log/ls-files/lockfile/manifest analysis. Full `cargo test --workspace` battery and corpus-dependent suites NOT run here (scope/time; the corpus is absent in a cold clone) — last recorded full battery is historical evidence in commit ee49f458 (2026-10-23 docs: "465 suites, 3264 passed, 0 failed"), not re-verified in this scan.

## Map

- **Stack**: Rust 1.99.0 (exact channel pin, `rust-toolchain.toml:12`, edition 2024) — 47-crate Cargo workspace (`Cargo.toml:2`), 91 lockfile packages (`Cargo.lock`), serde/serde_json/quick-xml 0.36/rusqlite 0.40 are the notable externals. Python 3.13 (uv, `.python-version`) — thin control-plane harness `law_nexus_harness` (22 modules, ~17.6k LOC under `src/`, deps: networkx, pydantic ≥2). Node 22 appears only in CI for one `.mjs` admission-contract test. `scripts/` adds 328 files (169 `.py`, 84 `.sh`, 69 `.mjs`, ~110k LOC), 232 of them milestone verify batteries (`m204…m224`). Dev toolchain: pytest, hypothesis, ruff + three type checkers (basedpyright, ty, pyrefly), pre-commit.
- **Entry points**: product binary `law-nexus-inspect` (`crates/ln-product-cli/src/main.rs:1540` lines, subcommands `health | inspect <path> | replay <seed> <target> | subordinates <kind> <path>`, hand-rolled `env::args` dispatch at main.rs:620). 48 Rust binaries total: 20 hard-case runners `ln-hc01…hc20-runner`, 25 corpus tool bins in `ln-consultant-parser` (14) and `ln-decode` (11), `ln-status` tracer, `hierarchy-registry-generator`. Python CLI `law-nexus-harness` (`pyproject.toml` script → `src/law_nexus_harness/cli.py`) with subcommands `status`, `governor`, `adr-verify`, `preflight`, `review-case {register,validate,status,inventory}`.
- **Architecture**: hexagonal, one level deep and strictly layered. 24 leaf crates with zero internal dependencies each carry `src/{domain,ports,adapters,application}.rs` (e.g. `crates/ln-observe/src/`); each of the 20 hc-runners wires exactly one leaf crate into an executable scenario verdict; composition exists only upward: `ln-kb-ontology → ln-identity + ln-temporal`, `ln-query → ln-decode + ln-storage`, `ln-consultant-parser → ln-decode + ln-kb-ontology + ln-temporal`, `ln-product-cli → consultant-parser, decode, kb-ontology, query, storage, temporal` (crate Cargo.toml dependency edges). `ln-testkit` holds 33 shared `*_port_contracts.rs` suites covering 22 crates. The Python harness is a repository control plane beside the product: it shells out to `target/debug/ln-status` (default `DEFAULT_STATUS_BINARY`, cli.py:50) and runs 57 read-only governor checks over repo state, ADRs, hostile-proof chains, roadmap freshness, and workflow state.
- **Conventions** (binding on the planner): hand-rolled over crates.io — no tokio, clap, anyhow, thiserror, regex, rayon, or chrono anywhere in `Cargo.lock`; arg parsing is manual `match` on `env::args`, errors are typed enums/results, every binary emits a versioned JSON verdict schema (`law-nexus-rust-status/v1`, `law-nexus-hc20-verdict/v1`). Tests are named for the hostile case they prove (`tests/hc01_hostile_adapters.rs` injects `InterruptibleSourceAdapter` + canary bytes and asserts bounded, non-authoritative outcomes); port contracts are shared in `ln-testkit`. Python: ruff `select=["E","F","I"]`, double quotes, LF, py3.13 target, four concurrent checkers must all pass in CI; pytest is strict-config/strict-markers with a declared (currently unused) `slow` marker. Lifecycle tags `[proposed]/[bounded]/[validated]` gate every status claim; commits are Conventional (last 400: 264 feat / 45 chore / 27 fix / 25 docs / 25 test / 4 ci, English subjects); tracked ADR/PRD prose is English, changelog and local planning prose may be Russian.
- **Maturity**: README declares honestly: no `[validated]` product capability; 20/20 hostile contracts `[bounded]` (README status block). ~6,159 Rust `#[test]` functions (3,273 inline + 2,886 in 363 `crates/*/tests/*.rs` files) and 1,801 Python test functions in 59 files. Corpus behavior is deliberately skip-visible on cold clones and hard-fails under `LAW_NEXUS_REQUIRE_CORPUS=1` (CI `corpus-integration` job); `consru_export/` (43,785 XML, 3.7 GB) is gitignored and absent here. Product storage is in-memory only (`InMemoryGraphStore`, `InMemoryVectorStore`, fail-closed `StubEmbedding` in `ln-product-cli/src/main.rs:60-70`); the hc16–hc20 runners are 36–67-line single files versus hc01's 192 lines/3 files — later lifecycle stages have thinner executable surface. `a.txt`/`b.txt`/`c.txt` (1 byte each) are tracked at the repo root.
- **Recent activity**: 1,774 commits since 2026-05-09; the last 60 cluster on `crates/ln-consultant-parser` (61 files touched), `prd/architecture` (59), `docs/agent-stack` (25), `src/law_nexus_harness` (16), the M217 reference-JSONLD line (`scripts/m217_reference_jsonld.py` + schema + parity tests), and `doc/adr` (6). The repo is mid-cutover to the GSD Path delivery workflow: `.project/STATE.md` records `phase: inspect`, milestone M001, branch `gsd-path/M001`.

## Finding: README member count is stale — 45 declared, 47 actual, and the two omitted crates are the heaviest recent work

- **Claim**: The README says "The workspace has 45 members in total: 20 capability owners, 20 hostile-case runners, `ln-product-cli`, `ln-testkit`, `ln-storage`, `ln-status`, and proposed `ln-applicability`". `Cargo.toml` declares 47 members; the two not in the README enumeration are `ln-kb-ontology` (44 rs files) and `ln-consultant-parser` (95 rs files, 14 bins) — the two largest active areas of the last 60 commits.
- **Source**: README.md status block vs `Cargo.toml:2` (47 member paths) and `git log -60 --name-only` clustering.
- **Confidence**: high
- **Why it matters here**: a planner trusting the README's capability inventory would omit the parser and the knowledge-base ontology — currently where the work is — from scope estimates and architecture views.

## Finding: there is no Python product in the tracked tree at all — only the harness, scripts, and tests

- **Claim**: AGENTS.md says "Python product is archive-only (`python_archive/product/`)", but `git ls-files python_archive/` returns 0 files, the directory does not exist in a fresh clone, and `.gitignore` lists `python_archive/` under "Historical vaults … must not be git-tracked". The only tracked Python is the harness (`src/`, ~17.6k LOC), governance/verification scripts (`scripts/`, ~110k LOC), and tests.
- **Source**: `git ls-files python_archive/` → empty; `.gitignore` ("python_archive/" entry with vault comment); sidecar directory listing.
- **Confidence**: high
- **Why it matters here**: "thin harness" is accurate for `src/`, but a planner could misread the 110k-LOC `scripts/` tree as product logic or as disposable; it is a governed verification layer (its own verify-tests are wired into CI's process suite), not the product runtime.

## Finding: zero async runtime, zero argument parser, zero error-crate dependencies in the entire Rust workspace

- **Claim**: `Cargo.lock` (91 packages) contains none of tokio, clap, anyhow, thiserror, async-std, rayon, regex, or chrono. Argument parsing, error types, and date handling are hand-rolled (e.g. `ln-status/src/main.rs` parse_command; `ln-decode` hand-rolled scanners noted in CHANGELOG as "D328 без serde").
- **Source**: regex scan of `Cargo.lock` names; `crates/ln-status/src/main.rs:23-45`.
- **Confidence**: high
- **Why it matters here**: new code that reaches for a common crate (clap, chrono, tokio) would violate the workspace's load-bearing dependency posture; the planner must budget for hand-rolled implementations instead.

## Finding: the workflow-state gate is branch-locked and fails closed away from the bound branch

- **Claim**: `.project/STATE.md` pins `branch: gsd-path/M001`; running `law-nexus-harness governor` from the verify sidecar at the same HEAD but on branch `gsd-path-verify/inspect-codebase` fails with exactly one error: `workflow-state-surface.blocking`, observed `kind=conflicting-ownership; … current branch gsd-path-verify/inspect-codebase != STATE.branch gsd-path/M001`, remediation "Follow the native Path recovery flow … do not repair STATE.md by hand". The other 71 checks pass (0 warnings, 0 tool errors).
- **Source**: `uv run python -m law_nexus_harness.governor` in this sidecar (JSON: findings[0]); `src/law_nexus_harness/workflow_state.py` (typed adapter, ADR-0007); `.project/STATE.md:10`.
- **Confidence**: high
- **Why it matters here**: pipeline-readiness checks are environment-sensitive by design (fail-closed, not silently green); any task that runs governor/status checks from a linked worktree branch will see this exact failure, and it is a routing fact, not a product defect.

## Finding: the tracked repo contains three 1-byte junk files at the root

- **Claim**: `a.txt`, `b.txt`, `c.txt` (each containing a single letter) are tracked at the repository root.
- **Source**: `git ls-files a.txt b.txt c.txt` → all three; file contents "a", "b", "c".
- **Confidence**: high
- **Why it matters here**: trivial, but it is exactly the kind of residue a hygiene-focused inspection would flag, and removal is a one-commit fix.

## Finding: CI encodes its own known-debt history and report-only boundaries — red product jobs once masked harness checks

- **Claim**: The CI workflow documents that "the default branch's Rust tests have failed since 2026-08-22, which silently skipped every harness check below them", and now isolates the migration layer into an independent job. Two M207 batteries and the M208 admission contract are `continue-on-error: true` (report-only) because three inputs cannot exist on CI (gitignored corpus, gitignored attempt logs, non-vendored quick-xml), and a documented frozen-token conflict (scanner ban vs absence-witness paths in `amendment_provenance.rs:3086-3120`, `npa_wire.rs:4`) is explicitly deferred to an ADR-level decision (D466/D487), not a CI edit.
- **Source**: `.github/workflows/repository-quality.yml` — `migration-layer-quality` comment, `corpus-integration` job (`if: vars.LAW_NEXUS_CORPUS_AVAILABLE == '1'`), `offline-contract-verifiers` comments and steps.
- **Confidence**: high
- **Why it matters here**: a green CI run does not mean the corpus batteries ran, and a red report-only step is a documented boundary, not a regression. Planners and reviewers must read the job boundaries before interpreting CI color.

## Finding: corpus maturity is unverifiable on a cold clone by design — and the pytest `slow` marker is declared but unused

- **Claim**: All corpus-dependent Rust tests skip (visibly) when `consru_export/` is absent; `pyproject.toml` declares a `slow` marker ("tests that rebuild full corpus artifacts") but zero Python tests in `tests/` use it (0 occurrences).
- **Source**: `.github/workflows/repository-quality.yml` corpus-integration comment; `pyproject.toml [tool.pytest.ini_options] markers`; regex count over `tests/*.py` → 0 `pytest.mark.slow`.
- **Confidence**: high
- **Why it matters here**: "tests pass" on a cold clone proves the portable surface only; any maturity claim about corpus parsing/retrieval must cite a corpus-present run (`LAW_NEXUS_REQUIRE_CORPUS=1`), which this scan could not perform.

## Finding: half-built surface — hc16–hc20 runners and the storage layer are minimal, in-memory, fail-closed stubs

- **Claim**: The last five hard-case runners are single 36–67-line `main.rs` files wiring one use case each (hc01: 192 lines/3 files), and the product CLI's storage ports are backed only by `InMemoryGraphStore`, `InMemoryVectorStore`, and a `StubEmbedding` that returns a typed error instead of a fake vector ("fail closed … never a silent all-zero vector", MEM676 note).
- **Source**: `crates/ln-hc16-runner/src/main.rs` (65 lines), `ln-hc20-runner/src/main.rs` (36), `ln-hc01-runner/src/main.rs` (192); `crates/ln-product-cli/src/main.rs:60-70`.
- **Confidence**: high
- **Why it matters here**: the lifecycle runner belt is executable evidence, not a product surface; nothing here persists or embeds yet. Reading hc-runner "green" as product readiness would be wrong.

<!-- Record every load-bearing surprise or half-built area observed. There is
     no minimum finding quota; explain an empty section if none were found. -->

## Apparent intent

<!-- Inference, clearly flagged — what the project seems to be becoming. -->

- Becoming a deterministic, citation-safe Russian legal act pipeline (decode → KB ontology → temporal → bounded query/retrieval), where every checkable step is source-anchored and the LLM is never legal authority — based on the README's goal statement, the composition edges into `ln-product-cli` (decode/kb-ontology/temporal/query), and the hostile-contract runner belt.
- The hard-case runners exist as permanent executable evidence of fail-closed contracts, not as user-facing features — based on their shape: one scenario table per lifecycle stage (HC-01…HC-20), verdict JSON per run, hostile adapters with canaries, and governor checks that assert the tracked proof chain stays coherent ("HC-01 tracked proof is coherent" … ×20 in the governor run).
- The delivery workflow itself is being migrated to GSD Path and is currently at its first brownfield milestone (M001, inspect) — based on `.project/STATE.md`, `docs/agent-stack/MIGRATION.md`/`MIGRATION-RECORD-2026-10-23.md`, `src/law_nexus_harness/workflow_state.py` (typed adapter over `.project/`), and the last day of commits (workflow-state adapter, phase dispatch adapter, cutover policy fixes).
- The near-term product frontier is the reference/citation layer (M217 JSONLD) and full-corpus parser acceptance — based on recent commit clustering (`ln-consultant-parser` is the most-touched code area; `scripts/m217_reference_jsonld.py` + schema + parity tests are new) and the README's `[bounded]`/no-`[validated]` status.

## Open questions for define

<!-- What only the user can settle about this codebase. -->

- Is the next product milestone full-corpus ingestion (parser acceptance over the 43,785-XML corpus) or the live retrieval stack (embeddings beyond `StubEmbedding`, RuVector per ADR-0014 `[proposed]`)? The recent activity hints parser-first, but the choice is a scope ruling.
- The frozen-token scanner conflict (M207 ban vs absence-witness paths in product code) is documented as needing an ADR amendment (D466/D487). Should that amendment be scheduled, or should the ban be enforced by changing the witnesses' location instead?
- The README's member inventory (45) is stale versus the manifest (47). Should doc drift like this be repaired during the current inspect/define phases, or does it wait for a docs-focused task?
- Should `a.txt`/`b.txt`/`c.txt` be deleted, or are they load-bearing for some check? (No reference found in scripts, CI, or tests during this scan.)
- M208/S04's admission contract remains wired-out pending an owner scope decision (D512 route, pinned ADR-0028 bytes). Does the pending decision stay pending, or is M208 in scope for the current milestone?

## Blocked areas

<!-- What could not be inspected and why. "none" if clean. -->

- Full Rust battery (`cargo test --workspace`, clippy, build of all 47 crates) — not run here (scope/time in a disposable sidecar; a full check of the ln-consultant-parser subtree alone took ~24 s cold). Recorded historical result (commit ee49f458) was not re-verified.
- Corpus-dependent behavior (`consru_export/`, 43,785 XML, 3.7 GB) — the corpus is gitignored and absent in this clone; all corpus claims are skip-visible by design, and `LAW_NEXUS_REQUIRE_CORPUS=1` runs were impossible here.
- `python_archive/`, `.lex/`, `Old_project/`, `prd/archive/` deep trees — gitignored historical vaults, absent or excluded by the brief; not inspected (per policy they are not product truth).
- `.ai/local/` (Allspark runtime caches, sessions) — ignored runtime payloads, out of scope for codebase mapping.
- `.project/archive/` — did not exist in this clone (excluded per brief; nothing to skip).
