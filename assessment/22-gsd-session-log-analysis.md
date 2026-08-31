# Assessment 22 — GSD session-log census and pattern inventory

- **Slice:** M195-mdvctn / S02, task T01 (census + inventory). Disposition of every row below (accept/decline), KNOWLEDGE landings, and CHANGELOG are T02 scope: every row carries `status: proposed` here.
- **Census date:** 2026-08-31 (re-run at execution time; counts were **not** copied from the S02 research snapshot, which predicted the same leader set). Logs grow; these numbers are a snapshot.
- **Provenance:** census sections `J*`, `D*`, `E*`, `G*`, `X*`, `Y*` were produced by `gsd_exec` runs `25170840`, `f0eb5b12`, `35781648`, `e4fac511`, `637804c4`, `da173d0a` (bookkeeping stdout only). Per KNOWLEDGE Rule 6, the durable anchor is this tracked file; all numbers below were copied from those stdout files, never from truncated digests.

## Methodology

- **Sources scanned (read-only):** GSD session logs under the real `.gsd` tree. `.gsd` in the repo is a symlink (real target `/root/.gsd/projects/3495c0714df3`); scans used the resolved absolute path plus `find -L`, not bare `.gsd/journal/*.jsonl` globs (MEM1106 / AGENTS.md).
- **Excluded:** `.gsd/exec/` (`gsd_exec` bookkeeping, tens of thousands of transient stdout files — explicitly not a durable proof surface per KNOWLEDGE Rule 6). `.gsd/exec` stdout files are cited only as provenance for the counts inlined here. `audit-log.jsonl` and `activity/` are outside this slice's census list.
- **Payload discipline:** no raw journal payloads, `rawReason` strings, PII, or secrets were copied into this file — only counts, pattern names, date ranges, relative paths, and check/cmd codes.
- **Tooling:** single-pass `jq` streaming per source (no full-file loads, no enumeration of `.gsd/exec`). Journal parse health: 11,234 of 11,234 lines parsed as objects with `eventType`; 0 malformed.
- **Counting-method gotcha (observed, corrected):** counting via `jq 'select(...)' | wc -l` pretty-prints multi-line JSON and inflates counts (an initial event-log run reported `complete-task=26267` on a 4,163-line file). Correct counts come from per-field value histograms (`jq -r '.cmd' | sort | uniq -c`), where the same file yields `complete-task=1792`. All numbers below use the histogram form.
- **Error signals were mined inside event `data`, not in the top-level `eventType` mix:** the top event types are pure lifecycle noise (`iteration-start` 1,481, `iteration-end` 1,317, `unit-start` 1,288, `unit-end` 1,281, `post-unit-finalize-start/end` 1,056/1,055). Failure-ish facts live in `data.status`, `data.artifactVerified`, `data.errorContext`, `data.failureCount`, and `issues[]` of doctor runs.
- **Dedup base (read-only):** repo `AGENTS.md` overlay (gitignored, not repository authority), 13 files in `.gsd/forensics/`, `.gsd/KNOWLEDGE.md` (Rules table = exactly 8 rule rows, untouched), and `.gsd/session-learning-report.md` as the conservative-retrospective format precedent (MEM094: reviewed, not auto-edited).

## Source inventory

| Source | Format | Count | Date range | Path (relative to real `.gsd` tree) |
|---|---|---|---|---|
| journal | JSONL, one file per day; line keys `data,eventType,flowId,seq,ts` | 51 files / 11,234 events / 0 malformed | 2026-05-09 → 2026-08-31 | `journal/*.jsonl` |
| doctor-history | JSONL, one doctor run per line; keys `ts,ok,summary,codes,issues,errors,warnings,fixes,fixDescriptions` | 193 runs (111 `ok=false`, 82 `ok=true`) | 2026-05-09 → 2026-08-30 | `doctor-history.jsonl` |
| event-log | JSONL, one lifecycle command per line; keys `ts,v,actor,session_id,cmd,params,hash` | 4,163 entries | 2026-05-09 → 2026-08-31 | `event-log.jsonl` |
| git-action-failures | plain text; `[iso-ts] action=verb` header + raw pre-commit output | 18 entries / 2,198 lines | 2026-07-24 → 2026-08-28 | `git-action-failures.log` |
| forensics (dedup base) | markdown case files | 13 files / 4,113 lines | 2026-05-17 → 2026-08-30 | `forensics/*.md` |

- Journal events per month: 2026-05 = 3,495; 06 = 677; 07 = 362; 08 = 6,700.
- Doctor runs per month (`ok`/`fail`): 2026-05 = 5/22; 06 = 48/3; 07 = 0/6; 08 = 29/80. Overall 57.5% of runs report `ok=false`. June is the clean stretch; August is both the busiest and the worst month (73% failing runs).
- Doctor run shape: `codes[]` = check codes evaluated in the run (32 distinct codes; 35 runs evaluated none, 3 runs evaluated 11). `issues[]` = individual findings (1,367 records, each with `code/severity/message/unitId`). `errors[]`/`warnings[]` arrays were empty in every run — all findings live in `issues[]`.
- Event-log entries per month: 2026-05 = 1,408; 06 = 961; 07 = 1,343; 08 = 451.

## Pattern inventory

All rows `status: proposed` (T02 disposes). "Documented?" cites the covering surface; "—" means no hit in AGENTS.md, `.gsd/forensics/`, or KNOWLEDGE.md (grep-audited per code, runs `e4fac511`/`637804c4`).

### Doctor-history issues (1,367 findings across 193 runs)

| Pattern (doctor code) | Findings | Runs checked → fired | Date range | Severity | Documented? | Status |
|---|---|---|---|---|---|---|
| artifact_file_missing | 327 | 64 → 327 (~5.1/run) | 2026-05 → 2026-08 | error | Partially — occurrence-level mentions in `forensics/report-2026-08-15-*` (×2), `report-2026-08-16-*`; no standing rule | proposed |
| validation_source_revision_mismatch | 209 | 25 → 209 | 2026-05 → 2026-08 | error | Yes — AGENTS.md validation↔completion ordering (authorized re-validate, M185-wuj4zf); `forensics/2026-08-30-gsd-health-repair.md`, `report-2026-08-24-*`, `report-2026-08-26-*` | proposed |
| all_slices_done_missing_milestone_summary | 165 | 76 → 165 | 2026-05 → 2026-08 | warning | Partially — `report-2026-08-24-*`, `report-2026-08-26-*`; MEM945 overlay-skip pattern referenced in S02 plan | proposed |
| task_done_must_haves_not_verified | 159 | 30 → 159 | 2026-05 → 2026-08 | warning | Partially — `forensics/report-2026-05-17-*` only | proposed |
| env_git_remote | 121 | 121 → 121 (fires in 100% of checked runs) | 2026-05 → 2026-08 | warning | Yes — known false positive: `forensics/doctor-env-git-remote-false-positive-no-head-ref.md`, MEM943 | proposed |
| artifact_user_content_missing | 93 | 48 → 93 | 2026-05 → 2026-08 | warning | Partially — `report-2026-08-15-*` (×2), `report-2026-08-16-*` | proposed |
| orphaned_slice_directory | 70 | 63 → 70 | 2026-05 → 2026-08 | warning | Partially — `report-2026-08-15-*` (×2), `report-2026-08-16-*`, `report-2026-05-17-*` | proposed |
| delimiter_in_title | 53 | 75 → 53 | 2026-05 → 2026-08 | warning | Partially — same report family; planning-input issue, not runtime | proposed |
| stale_crash_lock | 22 | 22 → 22 | 2026-05 → 2026-08 | error | Partially — `report-2026-05-17-*` | proposed |
| activity_log_bloat | 21 | 21 → 21 | 2026-05 → 2026-08 | warning | Partially — `report-2026-08-24-*`, `report-2026-08-26-*` | proposed |
| unresolved_projection_evidence | 19 | 19 → 19 | 2026-05 → 2026-08 | error | **No — zero dedup-surface hits** | proposed |
| stale_uncommitted_changes | 19 | 19 → 19 | 2026-05 → 2026-08 | warning | Partially — `report-2026-08-15-14-20-14` | proposed |
| stranded_lock_directory | 17 | 17 → 17 | 2026-05 → 2026-08 | error | No — zero surface hits | proposed |
| checkbox_db_status_divergence | 14 | 42 → 14 | 2026-05 → 2026-08 | error | Partially — 3 surface hits | proposed |
| invalid_preferences | 10 | 8 → 10 | 2026-05 → 2026-08 | 8 warn / 2 error | No — zero surface hits | proposed |
| state_file_stale | 9 | 9 → 9 | 2026-05 → 2026-08 | warning | No — zero surface hits | proposed |
| missing_roadmap | 8 | 26 → 8 | 2026-05 → 2026-08 | error | Partially — 3 surface hits | proposed |
| gitignore_missing_patterns | 7 | 7 → 7 | 2026-05 → 2026-08 | warning | No — zero surface hits | proposed |
| artifact_db_status_divergence | 5 | 6 → 5 | 2026-05 → 2026-08 | error | No — zero surface hits | proposed |
| active_requirement_missing_owner | 4 | 46 → 4 | 2026-05 → 2026-08 | warning | Yes — 4 surface hits (requirement-governance docs) | proposed |
| worktree_directory_orphaned / orphan_milestone_dir / orphan_milestone_db | 3 / 3 / 3 | 3 → 3 each | 2026-05 → 2026-08 | warning | No dedicated surface (worktree/orphan family adjacent to orphaned-active-unit forensics) | proposed |
| missing_tasks_dir / db_locked | 2 / 2 | 8 → 2 / 2 → 2 | 2026-05 → 2026-08 | warn / error | No — zero surface hits | proposed |
| missing_slice_plan | 1 | 1 → 1 | 2026-05 → 2026-08 | warning | No — zero surface hits | proposed |
| Zero-fire checks: all_slices_done_missing_milestone_validation, stale_replan_file, orphaned_running_attempt | 0 findings | 75 / 35 / 1 checks → 0 fires | 2026-05 → 2026-08 | — | `all_slices_done_missing_milestone_validation` has 2 surface mentions; others none | proposed |

### Journal event-data signals (mined inside `data`, not top-level eventType)

| Pattern | Count | Date range | Documented? | Status |
|---|---|---|---|---|
| unit-end `data.status=no-artifact` | 75 (2026-05: 15, 06: 1, 08: 59) | 2026-05 → 2026-08 | Cross-corroborates doctor `artifact_file_missing` (error family); no dedicated surface | proposed |
| unit-end `data.status=cancelled` | 37 | 2026-05 → 2026-08 | — | proposed |
| unit-end `data.status=crash-recovered` | 10 | 2026-05 → 2026-08 | Correlates doctor `stale_crash_lock` (22, report-2026-05-17) | proposed |
| unit-end `data.artifactVerified=false` | 136 of 1,281 (10.6%) | 2026-05 → 2026-08 | Adjacent to artifact-verification-retry + artifact_file_missing family | proposed |
| `data.errorContext` present (all on unit-end) | 37 | 2026-05 → 2026-08 | — | proposed |
| post-unit-finalize-end `status=retry` | 109 (2026-05: 22, 06: 1, 08: 86) | 2026-05 → 2026-08 | Adjacent (not identical) to `forensics/run-uat-gate-persistence-finalize-retry-wedge.md`; no direct row | proposed |
| post-unit-finalize-end `status=stopped` / `failed` | 12 / 1 | 2026-05 → 2026-08 | — | proposed |
| `data.error` payload present | 13 (12 iteration-end, 1 finalize-end) | 2026-05 → 2026-08 | — | proposed |
| `data.blockerDiscovered=true` | 0 events in window | — | — | proposed |
| subagent-completed `failureCount>0` | 27 of 456 dispatches (429×0, 21×1, 3×2, 3×3) | 2026-05 → 2026-08 | Partially — AGENTS.md subagent-dispatch rules (rejected-dispatch detection); `forensics/subagent-stdio-mcp-trust-gate-token-bloat.md` covers trust-gate bloat, not per-agent failure | proposed |
| artifact-verification-retry events | 34 (8/1/25 by month) | 2026-05 → 2026-08 | — | proposed |
| pre-execution-retry events | 20 (2026-08 only) | 2026-08 | — | proposed |
| auto-exit events | 104 (11/2/91 by month) | 2026-05 → 2026-08 | Adjacent — `forensics/orphaned-active-unit-idle-starves-liveness.md`, `auto-stop-s03-uat-workdir-mismatch.md` cover liveness/auto-stop family | proposed |
| guard blocks (orchestrator-guard-block 36 in 2026-08 + guard-block 12 in 2026-05) | 48 | 2026-05, 2026-08 | AGENTS.md tool-contract blocks describe the mechanism | proposed |
| dispatch-stop events | 20 (2026-05 only) | 2026-05 | — | proposed |

### Event-log command mix (4,163 entries)

| Pattern | Count | Share | Documented? | Status |
|---|---|---|---|---|
| complete-task | 1,792 | 43.0% | — (baseline) | proposed |
| plan-slice / complete-slice | 770 / 746 | 18.5% / 17.9% | — | proposed |
| plan-task / plan-milestone / complete-milestone | 219 / 206 / 159 | 5.3% / 4.9% / 3.8% | — | proposed |
| reassess-roadmap | 214 | 5.1% | — | proposed |
| replan-task / replan-slice / reopen-slice / reopen-task | 37 / 10 / 6 / 4 (57 total = 3.2% of complete-task) | 1.4% | AGENTS.md replan/task-reopen contract rows | proposed |

### Git-action-failures (18 commit failures, 2026-07-24 → 2026-08-28)

| Pattern (failing pre-commit hook) | Count | Date range | Documented? | Status |
|---|---|---|---|---|
| Rust workspace clippy | 7 | 2026-07 → 2026-08 | Yes as rule — AGENTS.md "Format (`cargo fmt`) **before** complete"; hook still fired 7× | proposed |
| ruff format --check staged Python files | 5 | 2026-08 | Yes as rule — AGENTS.md format-before-complete (Python-harness side) | proposed |
| Rust workspace formatting (cargo fmt) | 4 | 2026-07 → 2026-08 | Same rule surface | proposed |
| workspace crate dependency allowlist | 3 | 2026-07 → 2026-08 | Partially — harness dependency policy docs | proposed |
| architecture lifecycle tags and ADR references | 2 | 2026-08 | Yes — ADR conformance script + Rule 4 lifecycle tagging | proposed |

All 18 entries are `action=commit` (2 in July, 16 in August); the file contains 21 `exit code: 1` lines; 2 raw diff lines containing the substring "Failed" were excluded as noise.

## Dedup against AGENTS and forensics

Coverage verdicts for every inventory row (grep-audited over repo `AGENTS.md`, 13 `.gsd/forensics/*.md`, `.gsd/KNOWLEDGE.md`):

1. **Covered — decline-as-known candidates (T02 will decide):**
   - `env_git_remote` (121/121) → dedicated forensics false-positive report + MEM943; fires in 100% of runs that check it.
   - `validation_source_revision_mismatch` (209) → AGENTS.md validation↔completion ordering already encodes the authorized re-validate path (M185-wuj4zf) vs. real drift; three forensics reports document occurrences.
   - Git hook failures (18) → AGENTS.md format-before-complete already states the rule; the log shows the rule being re-learned at commit time, not a new rule.
   - run-uat / zod wedge family → AGENTS.md Zod-payload discipline + two forensics files (`run-uat-gate-persistence-finalize-retry-wedge.md`, `issue-run-uat-harnessabort-poisoning.md`).
   - Guard blocks / subagent dispatch rejections → AGENTS.md tool-contract and subagent-dispatch sections.
2. **Partially covered — occurrence-documented, no standing rule:** `artifact_file_missing` (327, largest error cluster), `all_slices_done_missing_milestone_summary` (165), `task_done_must_haves_not_verified` (159), `artifact_user_content_missing` (93), `orphaned_slice_directory` (70), `delimiter_in_title` (53), `stale_crash_lock` (22), `activity_log_bloat` (21), `stale_uncommitted_changes` (19), `checkbox_db_status_divergence` (14), `missing_roadmap` (8), `active_requirement_missing_owner` (4). These appear inside timestamped forensic reports but have no reusable rule/pattern row anywhere.
3. **Not covered anywhere — strongest new-lesson candidates:** `unresolved_projection_evidence` (19, error), `stranded_lock_directory` (17, error), `invalid_preferences` (10), `state_file_stale` (9), `gitignore_missing_patterns` (7), `artifact_db_status_divergence` (5), plus the low-count orphan/worktree/db-locked tail; journal-side: unit-end `no-artifact` (75) as the runtime counterpart of `artifact_file_missing`, `post-unit-finalize-end retry` (109), `auto-exit` August spike (91), subagent `failureCount>0` (27/456).
4. **Engine-side zero-fire checks** (`all_slices_done_missing_milestone_validation` 75 checks/0 fires, `stale_replan_file` 35/0) are observations about upstream GSD checks; per KNOWLEDGE Rule 1 any engine fix belongs on `open-gsd/gsd-pi`, not in this repo's rules — T02 should at most record the observation.
5. **Method-level lessons already encoded** and therefore not re-candidates: symlink-aware scans (MEM1106/AGENTS.md), digest-vs-stdout_path evidence discipline (AGENTS.md; independently re-confirmed by the E4 counting artifact), conservative retrospective format (`.gsd/session-learning-report.md`, MEM094), durable-proof Rule 6.

All rows remain `status: proposed`; T02 performs the accept/decline pass with reasons, KNOWLEDGE landings (Patterns/Lessons Learned tables only — the 8-row Rules table stays untouched), and the CHANGELOG `[Unreleased]` entry.
