# Code Review: Retire GSD-Pi, GSD-Path, and Allspark & Repository Cleanup

- **Date:** 2026-11-28
- **Target:** `chore/retire-gsd-and-repo-cleanup` vs `main` (`d4754035`)
- **Plan:** `.compound-engineering/artifacts/plans/2026-11-28-0014-chore-retire-gsd-and-repo-cleanup-plan.md`
- **Run ID:** `20261128-011746-a20c1bba`
- **Verdict:** Ready with fixes (all 6 confirmed findings applied in follow-up commit prior to PR)

---

## Code Review Results

**Scope:** `base:main` (`d4754035`) -> working tree on `chore/retire-gsd-and-repo-cleanup` (333 files: 19 modified, 314 deleted; +414 / -32,981 lines)
**Intent:** Retire legacy GSD-Pi, GSD-Path, and Allspark delivery-workflow trees from `main` behind archive tag `archive/gsd-path-final`, switch the repository harness and CI workflow to Compound Engineering, fix pre-existing M012 harness/ADR test failures, and verify zero regressions across Rust/ADR/allowlist/governor checks.
**Mode:** markdown report-only (explicit plan: `.compound-engineering/artifacts/plans/2026-11-28-0014-chore-retire-gsd-and-repo-cleanup-plan.md`, depth: full)

**Reviewers:** correctness, project-standards, testing, maintainability
- correctness -- always-on
- project-standards -- `AGENTS.md` governs all changed files (instruction-file fallback; no `CODING_STANDARDS.md`)
- testing -- 11 test files deleted and 6 test suites updated for Compound Engineering harness/CI contracts
- maintainability -- 281 executable non-test changed lines across harness modules and hook verifier

### Triage Groups

| Group | Findings | Context | Preferred Resolution | Why |
|-------|----------|---------|----------------------|-----|
| Governor Compound Engineering Routing & Metadata (apply-queue) | #2, #3 | Both affect the governor/workflow-state control plane switched to Compound Engineering in `src/law_nexus_harness/governor.py` and `src/law_nexus_harness/workflow_state.py` | Fix #3 first (`manual`, multi-branch routing) so broken Compound Engineering repos do not fall through to legacy `.gsd/STATE.md` errors in `check_roadmap_freshness`, then update `GOVERNOR_CHECK_SPECS` and companion docstrings in #2 (`gated_auto`) | Keeps runtime error routing, `--list-checks`/`--explain` metadata, and docstrings aligned with the active Compound Engineering backend |
| Post-Retirement Dead Code & Stale References (apply-queue) | #5, #7 | Both are P3 cleanup leftovers from deleting `.project/`, `docs/agent-stack/`, and `pi-skill-creator` | Update the top transition section of `prd/project-state/roadmap.md` (#5) and remove the dead `AGENT_SKILL_SCRIPT_PATHS` branch in `src/law_nexus_harness/preflight.py` (#7) while keeping the `ruff-format-explicit-python-paths` pass check | Eliminates a direct documentation contradiction and unreachable dead code left behind by the retirement |

### P2 -- Moderate

| # | File | Issue | Reviewer | Confidence |
|---|------|-------|----------|------------|
| 1 | `.github/workflows/repository-quality.yml:201` | CI governor diagnostic block is unreachable on errors | correctness | 100 |
| 2 | `src/law_nexus_harness/governor.py:8312` | Governor check spec and workflow-state docstrings cite deleted GSD Path inputs | correctness, maintainability | 100 |
| 3 | `src/law_nexus_harness/governor.py:924` | `check_roadmap_freshness` reads legacy surface first, misrouting broken CE | maintainability | 75 |
| 4 | `src/law_nexus_harness/subprocess_runner.py:17` | `_display_path` symlink and fallback branches lack test coverage | testing | 75 |

- **#1** -- When any governor check fails or hits a tool error in CI, operators never see the summary line, `workflow-state-surface` dump, or failing check-ID list in lines 206-233. GitHub Actions runs bash with `-e` and line 200 enables `set -o pipefail`, while `python -m law_nexus_harness.governor` exits `1` on `error_count > 0` and `2` on `tool_error_count > 0` (`src/law_nexus_harness/cli.py:423-427`, `src/law_nexus_harness/governor.py:8980`), aborting the step at line 201 before the inline Python script runs. **Response (mechanical fix):** Capture the pipeline exit code without masking failure (e.g., `gov_rc=0; uv run python -m law_nexus_harness.governor | tee governor.json || gov_rc=$?`), pass `GOV_RC="$gov_rc"` into the Python block (or exit `"$gov_rc"` afterward) so diagnostics print and any non-zero exit still fails the step. **Confidence:** 100 (`validation_status: confirmed`; `validation_reason`: GitHub Actions `-e` plus `set -o pipefail` at line 200 aborts line 201 on governor exit 1/2 before lines 206-233 execute; live CI failure incidence was not measured).
- **#2** -- Running `law-nexus-harness governor --explain workflow-state-surface` or `--list-checks` returns stale contract metadata (`src/law_nexus_harness/governor.py:8304-8316`) that omits `.compound-engineering/config.yaml` and names deleted `.gsd-path/runtime.json` and `.project/STATE.md`; on unexpected tool errors, `_run_spec_scoped` (`src/law_nexus_harness/governor.py:8923`) also attaches those deleted paths as evidence. Directly above the new `COMPOUND_ENGINEERING` branch, the `workflow_readiness` docstring (`src/law_nexus_harness/workflow_state.py:1090-1095`) still claims only native-helper-validated GSD Path states are operational, and docstrings/remediation strings in `workflow_state.py:6`, `governor.py:725,807`, and `preflight.py:305,373` still cite deleted `docs/agent-stack/*` files. **Response (mechanical fix):** Update `GOVERNOR_CHECK_SPECS` `authority_inputs` to `("prd/project-state/workflow-backend.json", COMPOUND_ENGINEERING_CONFIG_RELATIVE_PATH)` and update `purpose`, update the `workflow_readiness` docstring for `COMPOUND_ENGINEERING`, and remove or update the stale `docs/agent-stack/*` citations. **Confidence:** 100 (corroborated across `correctness` and `maintainability`; validated locally via `--explain workflow-state-surface`).
- **#3** -- When `workflow-backend.json` selects Compound Engineering, `check_roadmap_freshness` (`src/law_nexus_harness/governor.py:924-930`) calls `read_legacy_surface(root)` before `read_workflow_state(root)`, parsing the marker twice on healthy checkouts. When Compound Engineering is misconfigured (`cutover=false`, missing `.compound-engineering/config.yaml`, or resurrected `.project`/`.gsd-path`), `native.kind` is not `COMPOUND_ENGINEERING`, so execution falls through to `decision.blocks`/`_legacy_surface_skip` (`governor.py:1036-1070`) and emits misleading `.gsd/STATE.md` legacy-registry errors or skips instead of deferring to `workflow-state-surface`. **Response (mechanical fix, manual routing):** Move `decision = read_legacy_surface(root)` below `native = read_workflow_state(root)`, expose `backend: str | None = None` on `WorkflowStateReport` (or inspect `_read_cutover_marker`), and handle non-operational `compound-engineering` states without falling through to the `.gsd/STATE.md` path. **Confidence:** 75 (validated locally by reproducing `check_roadmap_freshness` with missing `.compound-engineering/config.yaml` and `cutover=false`).
- **#4** -- `_display_path` (`src/law_nexus_harness/subprocess_runner.py:17-26`) added lexical symlink-preserving and resolved-fallback branches so hosts with symlinked `target/` (such as `target -> /srv/rust-build/targets/law-nexus`) report workspace-relative `binary_path`. On CI runners where `target/` is a plain directory, `path.relative_to(resolved_root)` and `path.resolve().relative_to(resolved_root)` match, so reverting the order would pass CI undetected; neither `tests/test_harness_subprocess_failure_modes.py` nor `tests/test_harness_status_tracer.py` tests a symlinked `target/`, the second `resolve()` fallback, or the `path.as_posix()` external-path fallback. **Response (test gap):** Add unit tests in `tests/test_harness_subprocess_failure_modes.py` using `tmp_path` covering (1) a symlinked `target/` pointing outside `cwd`, (2) a non-normalized or symlink-prefixed path resolved by the second `try` block, and (3) a binary outside `cwd` falling back to `path.as_posix()`. **Confidence:** 75 (validated against existing `tests/`).

### P3 -- Low

| # | File | Issue | Reviewer | Confidence |
|---|------|-------|----------|------------|
| 5 | `prd/project-state/roadmap.md:12` | Roadmap header asserts retired GSD Path and deleted docs | correctness | 75 |
| 7 | `src/law_nexus_harness/preflight.py:603` | Dead `if skill_script_paths:` branch after emptying `AGENT_SKILL_SCRIPT_PATHS` | maintainability | 75 |

- **#5** -- `prd/project-state/roadmap.md:9-21` states in present tense that native GSD Path state lives under `.project/` and cites `docs/agent-stack/MIGRATION.md` and `docs/agent-stack/history/LEGACY_CROSSWALK.md` (all deleted in this diff), contradicting lines 54-59 of the same file. **Response (doc fix):** Rewrite lines 9-21 to mark the 2026-10-23 GSD Path transition as historical (archived read-only under `archive/gsd-path-final`) and point to Compound Engineering (`.compound-engineering/config.yaml`, `prd/project-state/workflow-backend.json`). **Confidence:** 75 (validated).
- **#7** -- Emptying `AGENT_SKILL_SCRIPT_PATHS` to `()` (`src/law_nexus_harness/preflight.py:30`) leaves `_present_agent_skill_script_paths` (lines 581-589) returning `()` and the `if skill_script_paths:` Ruff-formatting branch (lines 602-615) unreachable across `src/`, `tests/`, `scripts/`, and `.github/`. **Response (dead-code cleanup):** Delete `AGENT_SKILL_SCRIPT_PATHS`, `_present_agent_skill_script_paths`, and lines 602-615, leaving only the `_pass_check` for `ruff-format-explicit-python-paths` to preserve schema check-ID stability. **Confidence:** 75 (validated; zero external references or monkeypatches found).

### Requirements Completeness

Plan source: `explicit` (`.compound-engineering/artifacts/plans/2026-11-28-0014-chore-retire-gsd-and-repo-cleanup-plan.md`).

- **R1-R10:** All 10 requirements met.
- **U1-U6:** All 6 implementation units met.
- **Reverse check:** No unrequested user-facing behavior rules introduced (`subprocess_runner.py:17-26` is an internal host-compatibility fix for symlinked `target/`).

### Coverage

- **Applied:** N/A during review pass (`mode.apply_local` false); all 6 confirmed findings (`#1`, `#2`, `#3`, `#4`, `#5`, `#7`) plus reported testing gaps applied subsequently before PR submission.
- **Stage 5 reconciliation:** 9 raw findings across 4 local reviewers (`correctness`: 3, `project-standards`: 0, `testing`: 2, `maintainability`: 4); 1 semantic merge (into `#2`), 1 mode-aware demotion (`#6` -> `testing_gaps`), 1 rejected claim (`#8`).
- **Stage 5b validation:** 6 of 6 surviving primary findings validated in one batch (`confirmed: 6`, `rejected: 0`, `unresolved: 0`).
- **Conditional lenses:** `adversarial`, `security`, `performance`, `api-contract`, `data-migration`, `reliability`, `agent-native`, `learnings`, `frontend-races`, `previous-comments` not selected (control-plane cleanup only; no auth/money/DB migration/solutions corpus/PR comments).
- **Residual risks:**
  - Existing developer clones with the old GSD Path pre-commit wrapper must run `uv run pre-commit install --install-hooks --overwrite`.
  - Hosts retaining an untracked `.gsd/` symlink will see advisory `historical-only` warnings on legacy-surface checks (`cutover: true`).
  - Untouched files (`.pre-commit-config.yaml` excluding `^\.gsd-path/`, `scripts/analyze-session-learning.py`) still contain retired-path mentions.
- **Testing gaps (also addressed in follow-up fixes):**
  - Port `migration-layer-quality` governor diagnostics contract checks (`if: always()`, `if: failure()`, non-masking exit) into `tests/test_repository_quality_gate.py`.
  - Add non-object JSON root (`[]`) and broken Compound Engineering unit tests for `check_roadmap_freshness` plus live `check_roadmap_freshness(ROOT)` pass assertion in `tests/test_harness_governor.py`.

---

### Verdict

> **Verdict:** Ready with fixes
>
> **Fix order:** `#1` -> `#3` then `#2` -> `#4` -> `#5`, `#7`.

### Resolution Log (Applied Locally Before PR)

- `#1`: Updated `.github/workflows/repository-quality.yml` to capture governor exit code (`gov_rc`) before running the diagnostic Python block so failure summaries always print while still exiting non-zero on failure.
- `#2`: Updated `GOVERNOR_CHECK_SPECS` for `workflow-state-surface` (`authority_inputs` and `purpose`), `workflow_readiness` docstring, and removed stale `docs/agent-stack/*` citations in `workflow_state.py`, `governor.py`, and `preflight.py`.
- `#3`: Exposed `backend: str | None = None` on `WorkflowStateReport` and updated `check_roadmap_freshness` to check `read_workflow_state(root)` before `read_legacy_surface(root)` and handle broken Compound Engineering states without falling through to `.gsd/STATE.md`.
- `#4`: Added unit tests in `tests/test_harness_subprocess_failure_modes.py` covering symlinked `target/`, resolved fallback, and external-path fallback in `_display_path`.
- `#5`: Updated `prd/project-state/roadmap.md:9-21` to mark GSD Path as archived under `archive/gsd-path-final` and point to Compound Engineering.
- `#7`: Removed dead `AGENT_SKILL_SCRIPT_PATHS`, `_present_agent_skill_script_paths`, and unreachable `if skill_script_paths:` branch from `src/law_nexus_harness/preflight.py`.
- Testing gaps: Added `[]` JSON root + broken CE tests and live `check_roadmap_freshness(ROOT)` assertion in `tests/test_harness_governor.py`, and ported CI governor diagnostics contract assertions into `tests/test_repository_quality_gate.py`.
