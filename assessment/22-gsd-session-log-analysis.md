# Assessment 22 — GSD session-log census and pattern inventory

- **Slice:** M195-mdvctn / S02. Task T01 produced the census + inventory with every row `status: proposed`; task T02 dispositioned all 49 rows (§ Disposition below). Inventory tables retain their original T01 `status: proposed` column values for audit; the authoritative per-row verdicts live in § Disposition.
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

**Date-range correction (T02 spot-check, `gsd_exec` runs `e4eefc52` / `2a46415a`):** the uniform `2026-05 → 2026-08` stamp above is a T01 whole-file range, not per-code. Finding-weighted month spreads: `artifact_file_missing` 2026-07 (48) + 2026-08 (279, 11 distinct days); `validation_source_revision_mismatch` 2026-08 only (209); `all_slices_done_missing_milestone_summary` 2026-06 (1) + 2026-08 (164); `task_done_must_haves_not_verified` 2026-05 (89) + 2026-06 (70); `env_git_remote` 2026-05 (24) / 06 (10) / 07 (1) / 08 (86); `artifact_user_content_missing` 2026-07 (1) + 2026-08 (92); `orphaned_slice_directory` 2026-05 (33) / 06 (35) / 08 (2); `delimiter_in_title` 2026-05 (4) / 06 (40) / 08 (9, 8 distinct days); `stale_crash_lock` 2026-05 (19) / 06 (3, 6 distinct days); `activity_log_bloat` 2026-05 (1) + 2026-08 (20); `unresolved_projection_evidence` 2026-08 only (19); `stale_uncommitted_changes` 2026-05→08 (4/5/5/5); `stranded_lock_directory` 2026-05 only (17, 4 distinct days); `checkbox_db_status_divergence` 2026-08 only (14); `invalid_preferences` 2026-06 only (10); `state_file_stale` 2026-08 only (9); `missing_roadmap` 2026-07 (2) + 2026-08 (6); `gitignore_missing_patterns` 2026-06 (4) + 2026-07 (3); `artifact_db_status_divergence` 2026-08 only (5); `active_requirement_missing_owner` 2026-08 only (4); `worktree_directory_orphaned` 2026-05 (3), `orphan_milestone_dir` / `orphan_milestone_db` 2026-08 (3 each), plus `orphaned_auto_worktree` 2026-05 (1) — a 1-finding code absent from the T01 grouping, assigned to the low-count tail; `missing_tasks_dir` / `db_locked` 2026-08 (2 each); `missing_slice_plan` 2026-05 (1). Per-code totals reproduce T01 exactly (1,367 findings). The § Disposition table carries these corrected ranges.

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

## Disposition

Disposition status: complete

**Method.** The accept rule was applied to all 49 inventory rows. A lesson is accepted only if ALL of: (a) recurs across two or more independent sessions/dates; (b) is not already covered by a standing rule (AGENTS.md) or an existing KNOWLEDGE row — timestamped forensic occurrence reports document instances, not rules, and therefore do not by themselves constitute coverage; (c) formulates as a reproducible agent rule, not a one-off; (d) is process-level, not product ontology (R038/R064). Message semantics for every accepted code and for the zero-coverage codes were spot-checked from raw doctor `issues[]` (`gsd_exec` runs `e4eefc52`, `2a46415a`), not assumed. Counts are T01 census values re-verified 1:1 by run `2a46415a`.

**Outcome: 5 of 49 rows accepted → 4 KNOWLEDGE landings (2 Lessons Learned + 2 Patterns; `stale_crash_lock` and `stranded_lock_directory` share one lesson). 44 rows declined.**

### Doctor-history dispositions (24 rows)

| Pattern (doctor code) | Count | Date range (corrected) | Decision | Reason |
|---|---|---|---|---|
| artifact_file_missing | 327 | 2026-07 → 2026-08 (11 days) | **accept** → Lesson 1 | Largest error cluster; multi-day/month recurrence; only occurrence-level forensic mentions, no standing rule. Sampled semantics: DB artifact rows with no file on disk, ~90% historical-milestone residue (M061-vtvuj0 ×91, M128-z37bqq ×46, M001 ×42, M008 ×31) re-reported on every doctor run — durable projection/tree drift that needs a repair rule. |
| validation_source_revision_mismatch | 209 | 2026-08 only | decline — covered | AGENTS.md validation↔completion ordering encodes the lawful re-validate path (M185-wuj4zf precedent); forensics `2026-08-30-gsd-health-repair.md`, `report-2026-08-24-*`, `report-2026-08-26-*`. |
| all_slices_done_missing_milestone_summary | 165 | 2026-06 + 2026-08 | decline — covered | AGENTS.md canonical closeout order (validate → commit → complete in the same session) is the standing prevention; occurrences in `report-2026-08-24-*` / `report-2026-08-26-*`; MEM945 overlay-skip adjacent; SUMMARY is rendered by `complete-milestone`. |
| task_done_must_haves_not_verified | 159 | 2026-05 + 2026-06 | decline — covered | Standing rule in AGENTS.md execution rules (verify must-haves with concrete commands before the closing call); occurrence `report-2026-05-17-*`. Era-concentrated (pre-July). |
| env_git_remote | 121 | 2026-05 → 2026-08 | decline — known false positive | Dedicated forensics `doctor-env-git-remote-false-positive-no-head-ref.md` + MEM943; fires in 100% of checked runs; no agent rule can fix a checker false positive. |
| artifact_user_content_missing | 93 | 2026-07 + 2026-08 | decline — folded | Same artifact-materialization family as accepted Lesson 1; no separate row (avoids double-landing). |
| orphaned_slice_directory | 70 | 2026-05/06 (+2 in 08) | decline — covered | AGENTS.md: the DB-backed tool is the canonical write path; hand-made/hand-removed phase directories are the named anti-pattern. Era-concentrated (overlay-skip era). |
| delimiter_in_title | 53 | 2026-05 / 06 / 08 (8 days) | **accept** → Pattern 1 | Multi-month, planning-input only, zero standing rule in tracked or planning surfaces. Sampled semantics: `/` in milestone/slice titles conflicts with GSD state-document delimiters (44 milestone-level, 9 slice-level). |
| stale_crash_lock | 22 | 2026-05 + 2026-06 (6 days) | **accept** → Lesson 2 (with stranded_lock_directory) | Stale auto-mode worker locks after crashes; multi-day recurrence; occurrence-only coverage (`report-2026-05-17-*`); a reproducible recovery rule exists. |
| activity_log_bloat | 21 | 2026-05 + 2026-08 | decline — engine maintenance | Activity-log compaction is engine state, not a repo agent rule; Non-claims (no engine/DB hand-edits). |
| unresolved_projection_evidence | 19 | 2026-08 only | decline — engine-resolved surface | Sampled: projection-recovery evidence with a built-in sanctioned resolve path (`gsd doctor resolve-evidence … --action=discard/preserve/restore`). Single month; engine-side; Non-claims. |
| stale_uncommitted_changes | 19 | 2026-05 → 2026-08 (4-5/mo, steady) | decline — covered | AGENTS.md closeout ordering step 4 (validate → commit tracked artifacts → complete in the same session); occurrence `report-2026-08-15-14-20-14`. |
| stranded_lock_directory | 17 | 2026-05 only (4 days) | **accept** → Lesson 2 (with stale_crash_lock) | Sampled: a stranded session-lock directory blocks new auto-mode sessions from starting; zero prior coverage; recurrence satisfied at family level (crash/lock family spans 10 distinct days over 2 months). |
| checkbox_db_status_divergence | 14 | 2026-08 only | decline — covered | AGENTS.md / execution contract: do not edit PLAN.md checkboxes — the tool renders state; drift is repaired via `/gsd rebuild markdown`. |
| invalid_preferences | 10 | 2026-06 only | decline — engine config, non-claim | Sampled: unknown preference key `project_policy` (8) + enum validation (2); preferences are engine-owned state; single month. |
| state_file_stale | 9 | 2026-08 only | decline — engine state | Session-state staleness handled by resume/recovery paths; no repo agent rule. |
| missing_roadmap | 8 | 2026-07 + 2026-08 | decline — bootstrap / engine | Roadmap creation is owned by plan tooling; findings cluster in repair episodes already covered by `2026-08-30-gsd-health-repair.md`. |
| gitignore_missing_patterns | 7 | 2026-06 + 2026-07 (2 days) | **accept** → Pattern 2 | Sampled: missing critical runtime patterns (`.gsd-worktrees/` ×4, `.gsd-backups/` ×3); two independent dates; zero coverage; reproducible pairing rule (unignored strays also pollute `git ls-files --others` source-revision hashing). |
| artifact_db_status_divergence | 5 | 2026-08 only | decline — covered | AGENTS.md names the artifact/DB drift and its repair (`/gsd rebuild markdown`) even though the doctor code string itself has zero verbatim hits. |
| active_requirement_missing_owner | 4 | 2026-08 only | decline — covered | 4 surface hits in requirement-governance docs; single month. |
| worktree_directory_orphaned / orphan_milestone_dir / orphan_milestone_db (+ orphaned_auto_worktree) | 3/3/3 (+1) | 2026-05 (3+1) / 2026-08 (6) | decline — low-count tail | No reproducible agent rule; adjacent to orphaned-active-unit forensics; monitor. |
| missing_tasks_dir / db_locked | 2 / 2 | 2026-08 only | decline — low-count tail | Transient engine state / bootstrapping artifacts. |
| missing_slice_plan | 1 | 2026-05 only | decline — one-off | Fails recurrence (a). |
| Zero-fire checks: all_slices_done_missing_milestone_validation, stale_replan_file, orphaned_running_attempt | 0 | 2026-05 → 2026-08 | decline — observation only | Upstream GSD checks; engine fixes belong on `open-gsd/gsd-pi` (KNOWLEDGE Rule 1). |

### Journal dispositions (15 rows)

| Pattern | Count | Decision | Reason |
|---|---|---|---|
| unit-end `data.status=no-artifact` | 75 | decline — folded | Runtime counterpart of accepted Lesson 1 family. |
| unit-end `data.status=cancelled` | 37 | decline | Normal lifecycle; no failure semantics. |
| unit-end `data.status=crash-recovered` | 10 | decline — folded | Supporting evidence inside accepted Lesson 2 (crash/lock family). |
| unit-end `data.artifactVerified=false` | 136 of 1,281 | decline — folded | Same Lesson 1 family (artifact-verification retry surface). |
| `data.errorContext` present | 37 | decline | Diagnostic field presence, not a standalone lesson. |
| post-unit-finalize-end `status=retry` | 109 | decline — covered | AGENTS.md two-strike rule + `run-uat-gate-persistence-finalize-retry-wedge.md` / `issue-run-uat-harnessabort-poisoning.md`. |
| post-unit-finalize-end `status=stopped` / `failed` | 12 / 1 | decline | Low count; lifecycle. |
| `data.error` payload | 13 | decline | Low count; diagnostic. |
| `data.blockerDiscovered=true` | 0 | decline | No signal in window. |
| subagent-completed `failureCount>0` | 27 of 456 | decline — covered | AGENTS.md subagent-dispatch verification rules (git status/log after dispatch, MEM695) already mandate the behavior; census only quantifies ~6% incidence. |
| artifact-verification-retry | 34 | decline — folded | Lesson 1 family retry surface. |
| pre-execution-retry | 20 (2026-08 only) | decline | Engine retry mechanics; fails multi-month recurrence; monitor. |
| auto-exit | 104 | decline — covered | Liveness/auto-stop forensics family (`orphaned-active-unit-idle-starves-liveness.md`, `auto-stop-s03-uat-workdir-mismatch.md`). |
| guard blocks | 48 | decline — covered | AGENTS.md tool contract (`HARD BLOCK` semantics are the rule). |
| dispatch-stop | 20 (2026-05 only) | decline | Single-month era artifact; fails (a). |

### Event-log dispositions (5 rows)

| Pattern | Count | Decision | Reason |
|---|---|---|---|
| complete-task | 1,792 (43.0%) | decline | Baseline command mix, not a failure pattern. |
| plan-slice / complete-slice | 770 / 746 | decline | Baseline mix. |
| plan-task / plan-milestone / complete-milestone | 219 / 206 / 159 | decline | Baseline mix. |
| reassess-roadmap | 214 (5.1%) | decline | Baseline mix. |
| replan-task / replan-slice / reopen-slice / reopen-task | 57 total | decline — covered | AGENTS.md replan / task-reopen contract rows. |

### Git-action-failure dispositions (5 rows)

| Pattern | Count | Decision | Reason |
|---|---|---|---|
| Rust workspace clippy | 7 | decline — covered | AGENTS.md format-before-complete; the log shows the rule re-learned at commit time. |
| ruff format --check | 5 | decline — covered | Same surface (Python-harness side). |
| cargo fmt | 4 | decline — covered | Same surface. |
| dependency allowlist | 3 | decline — covered | Harness dependency policy docs. |
| lifecycle tags / ADR references | 2 | decline — covered | ADR conformance script + KNOWLEDGE Rule 4. |

**Totals: 49 rows → 5 accept / 44 decline; 4 distinct KNOWLEDGE landings (2 Lessons Learned + 2 Patterns).**

## KNOWLEDGE landings

Rows actually appended to `.gsd/KNOWLEDGE.md` (canonical GSD planning path; the Rules table is untouched — still exactly 8 rows). Row text is Russian per KNOWLEDGE Rule 2 (local `.gsd` planning prose); doctor codes and paths are verbatim.

Lessons Learned — exact appended rows:

| # | What Happened | Root Cause | Fix | Scope |
|---|---|---|---|---|
| 1 | Doctor `artifact_file_missing` — крупнейший кластер census (327 находки, 2026-07→08, 11 дней; переотчёт при каждом прогоне doctor): строки артефактов в GSD DB указывают на файлы, которых нет на диске; ~90% — остаток исторических майлстоунов (M061-vtvuj0 ×91, M128-z37bqq ×46, M001 ×42, M008 ×31). | Phase-артефакты исчезали/удалялись вне санкционированных путей, а записи DB продолжали ссылаться на них; расхождение projection ↔ дерево воспроизводится на каждом прогоне. | Чинить расхождение artifact/DB только санкционированными путями (`/gsd rebuild markdown`, `gsd doctor` fix/resolve); никогда не создавать/писать/удалять phase-артефакты руками; исторический остаток диспозить явно. | GSD-процесс, все майлстоуны (census M195-mdvctn S02: assessment/22). |
| 2 | Крахи/kill auto-mode оставляли stale worker-локи (`stale_crash_lock`, 22 находки, 2026-05→06) и брошенные каталоги session-lock (`stranded_lock_directory`, 17 находок, 2026-05, 4 разных дня), блокирующие запуск новых auto-mode сессий; journal: 10 `crash-recovered` unit-end. | Попытки прерывались без recovery-settlement; локи переживают свои процессы. | После краха оседать через recovery-инструменты (`gsd_task_recovery_resume` / `gsd doctor`) до старта новых сессий; не удалять руками лок, который может держать живой процесс. | GSD-процесс (census M195-mdvctn S02: assessment/22). |

Patterns — exact appended rows:

| # | Pattern | Where | Notes |
|---|---|---|---|
| 1 | Не использовать `/` в названиях milestone/slice (а также `–`/`—`) | title в `gsd_plan_milestone` / `gsd_plan_slice` / `gsd_plan_task`; рендер ROADMAP/PLAN | doctor `delimiter_in_title`: 53 предупреждения (2026-05/06/08; 44 milestone-level, 9 slice-level) — слэш конфликтует с разделителями GSD state-документов. |
| 2 | Новые генерируемые runtime-локации добавлять в `.gitignore` тем же изменением | repo `.gitignore`; workflows/движок, начинающие генерировать новые локации (`.gsd-worktrees/`, `.gsd-backups/`) | doctor `gitignore_missing_patterns`: 7 предупреждений (2026-06/07); незамеченные файлы также попадают в `git ls-files --others` при хэшировании source-revision. |

## Non-claims

This slice does NOT close or touch:

- **R070 and any requirement rows** — requirement terminalization is explicitly out of scope; no `gsd_requirement_*` calls were made.
- **P2 Mention/Binding resolver / D313** planning items — untouched.
- **Engine/DB state** — `gsd.db`, projections, locks, preferences, doctor fixes: read-only census only; any engine-side fix belongs upstream on `open-gsd/gsd-pi` (KNOWLEDGE Rule 1).
- **Product/runtime** — `crates/`, `src/law_nexus_harness/`, `tests/` unchanged; no new governor `check_id`; the S01 governor line (pass 68 / warn 3) is deliberately not copied into the S02 CHANGELOG block, and no warn count is invented for S02.
- **AGENTS.md** — gitignored overlay, not repository authority; not written (MEM658).
- **S03 dead-code** scope — separate work.
- **Census durability** — counts are snapshots of growing logs (re-run date 2026-08-31); the durable anchor is this tracked file, never `.gsd/exec` stdout (KNOWLEDGE Rule 6).
- **Product ontology** — all landings are process-level (R038/R064 boundary respected).
