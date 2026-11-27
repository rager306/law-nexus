# Code Review: `chore/rust-standard-rollout`

- **Date:** 2026-11-27
- **Run ID:** `20261127-232838-137b88e8`
- **Branch:** `chore/rust-standard-rollout` (base `origin/main` @ `9afa26253bed1600768642b73a518292f9742195`)
- **Scope:** 60 files (52 modified, 8 added; 0 Rust `src/` executable lines changed; build/lint/CI/tooling + Compound Engineering config)
- **Depth:** `lite` (`exec_nontest_lines=0`, `hard_block_full=false`, no regression weakening an existing security/data boundary)
- **Verdict:** **Ready with fixes** -> **Applied locally** (all 3 findings fixed in `Justfile` and verified)

## Intent

Roll out the Unified Rust Standard (`1.99.1`, workspace lints with `unsafe_code = "forbid"` across all 47 crates, `Justfile` Tier 0-3 gates, `deny.toml`, `clippy.toml`, `rustfmt.toml`, `.config/nextest.toml`, `.deslop-please.allow`, `AGENTS.md` section) and configure Compound Engineering (`.compound-engineering/config.yaml` with `docs_root: .compound-engineering/artifacts`, `.gitignore` rules, and `AGENTS.md` review-report storage rule).

## Findings

| # | Severity | Location | Route | Summary | Status |
|---|----------|----------|-------|---------|--------|
| 1 | P2 | `Justfile:36-37`, `Justfile:51-52` | `gated_auto` / `downstream-resolver` | `uv run python` omits `--frozen`, risking lockfile mutation or network access during offline Tier 0/1 gates. | Applied |
| 2 | P2 | `Justfile:94-95` | `gated_auto` / `downstream-resolver` | `cargo audit --no-fetch bin ... \|\| true` silently suppresses all exit codes (missing DB, missing binary, new CVEs) even on clean `ln-status`. | Applied |
| 3 | P3 | `Justfile:49` | `gated_auto` / `downstream-resolver` | `zizmor .github/workflows \|\| true` lacks an explanatory comment linking the temporary suppression to the CI pinning follow-up (`tests/test_repository_quality_gate.py:138`). | Applied |

### Finding Details

1. **[P2] Offline lockfile safety in `Justfile` (`Justfile:36-37`, `Justfile:51-52`)**
   - **Evidence:** `uv run python scripts/verify-crate-dependency-allowlist.py` and `uv run python scripts/verify-adr-conformance.py` omit `--frozen`, unlike the repo's offline/frozen `uv run --frozen` convention (`docs/agent-stack/POST-SHIP-STATE-2026-10-28.md:222-230`).
   - **Fix applied:** Updated all 4 invocations to `uv run --frozen python ...`.

2. **[P2] Fail-open `|| true` on release binary audit (`Justfile:94-95`)**
   - **Evidence:** `cargo audit --no-fetch bin target/release/ln-status || true` and `cargo audit --no-fetch bin target/release/law-nexus-inspect || true` swallow non-zero exits unconditionally. `ln-status` already passes cleanly (exit 0, 1 dependency), and `law-nexus-inspect` passes with exit 0 when the 11 documented baseline advisories from `deny.toml` are passed via explicit `--ignore` flags.
   - **Fix applied:** Removed `|| true` from both commands; `ln-status` runs strictly without ignores, and `law-nexus-inspect` uses `AUDIT_BASELINE_IGNORES` matching `deny.toml:17-29`, so any 12th advisory or missing DB fails closed.

3. **[P3] Undocumented temporary `|| true` on `zizmor` (`Justfile:49`)**
   - **Evidence:** `if command -v zizmor >/dev/null 2>&1; then zizmor .github/workflows || true; fi;` had no comment explaining why failures are currently tolerated.
   - **Fix applied:** Added `# TODO(ci-hardening)` comment noting the lockstep constraint with `tests/test_repository_quality_gate.py:138`.

## Actionable Findings

All 3 findings (`#1`, `#2`, `#3`) were applied locally in `Justfile` and verified.

## Residual Risks and Pre-Existing Issues

- **11 baseline CVEs in `deny.toml:17-29` and `Justfile` `AUDIT_BASELINE_IGNORES`:** `zip = "=8.6.0"` (8 CVEs incl. CRITICAL 9.1 `RUSTSEC-2026-0369`), `quick-xml 0.36.2` (2 High), `libsqlite3-sys 0.38.2` via `rusqlite 0.40.2` (1 Medium). Pre-existing before this rollout; tracked for a dedicated major-upgrade PR.
- **CI Actions hardening (`zizmor`):** 13 High (`unpinned-uses`) + 5 Low (`persist-credentials`) in `.github/workflows/repository-quality.yml`, coupled to `tests/test_repository_quality_gate.py:138`; tracked for a dedicated PR.
- **Pre-existing pytest failures on `origin/main` (`9afa2625`, untouched by this branch):**
  - `tests/test_post_ship_pointers.py::test_roadmap_json_current_milestone_tracks_the_latest_archive` (`roadmap.json` still names `reference-front-door` after M012 archive);
  - `tests/test_gitnexus_block_receipt.py` (2 failures: M012 updated `AGENTS.md` GitNexus block to `43376` symbols while receipt still pins `43047`).

## Coverage

- **Depth:** `lite` path run in-context; no external reviewer subagents or cross-model peer dispatched (`exec_nontest_lines=0`, `hard_block_full=false`).
- **Criteria checked:** root `AGENTS.md` (instruction-file fallback; no `CODING_STANDARDS.md` present).
- **Review policy:** none at base ref `9afa26253bed1600768642b73a518292f9742195`.
- **Compound Packs:** none declared (`declared_packs: false`).
- **Plan verification:** no explicit or branch-matching plan in `.compound-engineering/artifacts/plans/`.
- **Mechanical checks run:** all 47 `crates/*/Cargo.toml` diffs verified (46 exact `[lints]\nworkspace = true` + `ln-testkit` dev-dep move), `tests/test_repository_quality_gate.py` (5 passed), `verify-crate-dependency-allowlist.py` (55 edges, 0 findings), `verify-adr-conformance.py` (29 files, 0 findings), `ce-setup/scripts/check-health` (healthy), `cargo audit --no-fetch bin` on both release binaries (exit 0).
- **Not assessed by lite path:** historical learnings corpus, agent-native parity, deployment notes.

## Verdict

**Ready to merge** (after applying findings `#1`-`#3` in `Justfile`).
