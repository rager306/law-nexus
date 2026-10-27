# M002 Acceptance Proof — T005

- Recording date: 2026-10-27
- Recorded by: build_T005 — a fresh session given only the repository and the task
  pointer (`docs/agent-stack/POST-SHIP-STATE-2026-10-27.md`, section "Fresh-session
  bootstrap"); no chat history; this proof is disk-only (N5).
- Branch at recording time: `gsd-path/M002`, HEAD `878518aa17725616996d7bd39ca9db2a457ab5b3`
- Milestone: `post-ship-hardening` (M002 continuation on top of the shipped/archived M001)

## Step 1 — bootstrap: pinned runtime restore from the vendored archive

Commands (temporary dir outside the repository; the extraction target is never a
tracked path):

```bash
TMPDIR=$(mktemp -d /tmp/gsd-restore-T005-XXXXXX)   # resolved to /tmp/gsd-restore-T005-gJUhCS
tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C "$TMPDIR"
python3 "$TMPDIR/gsd-path/scripts/install.py" --runtime-restore --project /root/law-nexus --source-root "$TMPDIR/gsd-path"
```

- `tar` exit status: 0. Extracted a single top-level `gsd-path/`. stderr carried only
  `time stamp 2026-11-05 20:20:00 is ... in the future` warnings for the vendored
  file mtimes — benign, exit 0.
- Installer exit status: 0. Real output (verbatim):

```
runtime: restore 1.6.2 (6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f)
```

- The printed version+digest pair matches `.gsd-path/runtime.json`
  (`{"digest": "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f", "schema": "gsd-path/runtime/v1", "version": "1.6.2"}`).
- E2 idempotency observed: exit 0 per contract means "the pinned runtime is
  installed or reused idempotently"; the already-valid store was reused untouched —
  the restored installer's reuse path validates the existing store and returns
  without rewriting (installer source lines 130–136), and `git status` shows no
  tracked-path change from the restore (same three pre-existing entries before and
  after: this task file, its dispatch record, and the dispatch-record lock).

## Step 2 — status

- Command: `python3 scripts/ai/path-run.py status`
- Exit status: 0
- Real output (verbatim):

```json
{"advance": false, "completion": {"status": "not-shipped"}, "default_branch": "main", "git": {"ancestor_of_origin_main": false, "branch": "gsd-path/M002", "dirty": [".project/research/.dispatch-record-build-T005-2026-10-27.json.lock", ".project/research/dispatch-record-build-T005-2026-10-27.json", ".project/tasks/T005-fresh-session-acceptance-walkthrough.md"], "head": "878518aa17725616996d7bd39ca9db2a457ab5b3", "origin_branch": null, "origin_main": "4e0cd4dba087b3a0dfaacb4cc6a443f1bc5d495f", "published": false, "subject": "T003: Make the governor and preflight suites context-independent with the five-scenario matrix"}, "handoff": {"next": "Invoke $gsd-path to continue with build.", "outcome": "build/active", "phase_next": "Invoke $gsd-path to continue with build.", "review": "/root/law-nexus/.project/STATE.md", "router_next": "Continue with build; honor its input and approval gates."}, "journals": {"abandon": null, "bind_next": null, "checkpoint": null, "collect_artifact": null, "promotion": null, "shipment": null, "undo": null}, "lookahead": false, "next_skill": "gsd-path-build", "path": "/root/law-nexus/.project/STATE.md", "pending_answers": [], "pending_error": null, "route": {"action": "run-phase", "mode": "recovery", "phase": "build", "reason": "state is build/active"}, "schema": "gsd-path/status/v1", "state": {"archive": null, "branch": "gsd-path/M002", "integration": "direct", "integration_default": "direct", "integration_source": "default", "milestone": "post-ship-hardening", "phase": "build", "pipeline": "gsd-path/v2", "project": "law-nexus", "status": "active"}}
```

Output names branch `gsd-path/M002` and milestone `post-ship-hardening`, and shows
`origin_main` = `4e0cd4dba087b3a0dfaacb4cc6a443f1bc5d495f` — the recorded M001
integration commit (`4e0cd4db` "integrate: M001 — merge gsd-path/M001 into main").
The M001 ship commit (`886a36a8` "ship: M001 — 001-native-workflow-acceptance",
full SHA `886a36a8f9ed77ad315f4b16fee0cdbc68bf4d02`) is the direct parent of that
integration commit on `main` (verified read-only: `git merge-base --is-ancestor
886a36a8 4e0cd4db` → yes). The shipped milestone is archived at
`.project/archive/001-001-native-workflow-acceptance/` with `MANIFEST.md`
recording "Shipped: 2026-10-27; Final verdict: all criteria met; project verify passed".

## Step 3 — governor

- Command: `uv run --frozen python -m law_nexus_harness.governor`
- Exit status: 0
- Material output (verbatim summary fields of the JSON report; 75 findings, all
  `"status":"pass"`):

```json
{"error_count": 0, "pass_count": 75, "root": "/root/law-nexus", "schema_version": "law-nexus-governor-report/v1", "status": "ok", "tool_error_count": 0, "warn_count": 0}
```

- Acceptance-relevant findings (verbatim `observed`):
  - `workflow-state-surface`: `backend=gsd-path; runtime=1.6.2@6f95a31e4b8a; legacy_gsd=present; GSD Path workflow state is valid; native status validated STATE.md and routes run-phase.`
  - `roadmap-current-tracks-path`: `native_state=operational-valid; native_phase=build; roadmap_current=post-ship-hardening; comparison=path`

Governor errors: 0 (expected 0).

## Step 4 — roadmap freshness guard

- Command: `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q`
- Exit status: 0
- Real output (verbatim):

```
sssss..                                                                  [100%]
2 passed, 5 skipped in 5.48s
```

## Diagnostics familiarity (read-only; per the task contract)

- On a failed migration-job governor step, CI publishes a workflow artifact named
  `governor-diagnostics` containing `governor.json`, prints the report JSON to the
  job log, and the job exit stays non-zero; a passing run publishes no artifact.
  Confirmed read-only in `.github/workflows/repository-quality.yml` (step "Publish
  governor diagnostics on failure", `if: failure()`, uploads `governor.json` under
  name `governor-diagnostics`; the governor step `tee`s the report to `governor.json`).
- Shipped-main CI assertion: on a push-to-main run (`GITHUB_REF == refs/heads/main`)
  the governor step requires governor exit 0 and the `workflow-state-surface`
  observed text to contain `"kind=shipped-integrated;"` and
  `".project/archive/001-001-native-workflow-acceptance"`
  (`.github/workflows/repository-quality.yml`, step "Governor report is honest about
  bootstrap mode"). This walkthrough ran on `gsd-path/M002`, not `main`, so this
  assertion did not apply to this run; the recorded status instead names the
  `post-ship-hardening` continuation.

## Result

All bootstrap and verification commands exited 0:

| # | Command | Exit status |
|---|---------|-------------|
| 1a | `tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C <temporary-dir>` | 0 |
| 1b | `python3 <temporary-dir>/gsd-path/scripts/install.py --runtime-restore --project /root/law-nexus --source-root <temporary-dir>/gsd-path` | 0 |
| 2 | `python3 scripts/ai/path-run.py status` | 0 |
| 3 | `uv run --frozen python -m law_nexus_harness.governor` | 0 |
| 4 | `uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q` | 0 |

- Restore: pinned pair `1.6.2@6f95a31e…` re-validated, store reused untouched (E2).
- Status: branch `gsd-path/M002`, milestone `post-ship-hardening`, `origin_main` =
  integration `4e0cd4db` over ship `886a36a8`; M001 archived
  (`.project/archive/001-001-native-workflow-acceptance/`).
- Governor: exit 0, `status: ok`, 75/75 pass, 0 errors, 0 warnings; roadmap current
  milestone tracks the live native Path state (`comparison=path`).
- Freshness pytest: 2 passed, 5 skipped.

No bootstrap ambiguity, no failing command; nothing blocked.
