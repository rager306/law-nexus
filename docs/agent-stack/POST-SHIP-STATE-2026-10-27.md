# Post-ship state — 2026-10-27

- Date: 2026-10-27.
- Role: current-state document for the `law-nexus` repository.
- Supersedes: `docs/agent-stack/CUTOVER-READINESS-M001.md` as the current-state
  document. That file remains untouched as the dated pre-ship snapshot
  (2026-10-26); its `ci_runs` entries deliberately record the pending-ship
  form, which the M001 ship resolved.
- Written by: build_T004 (coder, milestone `post-ship-hardening`). Records
  delivery and workflow state only; it is not a legal or product authority.

## Shipped M001 (recorded fact)

Milestone `001-native-workflow-acceptance` shipped and archived on 2026-10-27:

- Ship commit `886a36a8` ("ship: M001 — 001-native-workflow-acceptance").
- Integration merge `4e0cd4db` into `main`; tag
  `milestone/001-001-native-workflow-acceptance`.
- Archive `.project/archive/001-001-native-workflow-acceptance` (read-only;
  manifest inside).

What M001 proved and delivered: the native GSD Path delivery workflow executed
end to end on bound branch `gsd-path/M001`; the M225 validation residual closed
with an honest re-run (`prd/migration/rust-evidence/m225-validation-rerun-m001.json`,
verdict `hermetic-pass-parity-unproven` — corpus parity explicitly unproven);
the minimal PDD model landed in `product-model/`; the GitNexus index was
regenerated with a receipt-pinned `AGENTS.md` tool block; the fresh-session
resume proof was recorded on disk.

Cutover stays `false` (C7 is a later owner decision); the pre-ship snapshot's
pin (`tests/test_m001_cutover_readiness.py`) still holds unmodified.

## CI state and its fix

The failure (CI run 40446077586 on `main`@`4e0cd4db`): the `repository-quality`
migration job's real governor step exited 1 `runtime-unavailable` — the pinned
GSD Path runtime (`1.6.2@6f95a31e…`, per `.gsd-path/runtime.json`) is
machine-local by design and CI never restored it, and the step's stdout went
into an unparsed `governor.json`, so the only visible signal was a bare
non-zero exit.

The fix, landed by M002 wave 1:

- The pinned runtime is vendored at `.ai/vendor/gsd-path-1.6.2.tgz`, digest-
  verified against `.gsd-path/runtime.json`
  (`{"version": "1.6.2", "digest": "6f95a31e4b8a434672421a604bdce71e5179409eb19496097219cd6cdb5d9f6f"}`).
  Both `migration-layer-quality` and `rust-harness-quality` restore it from the
  vendored archive before any operational check; a missing archive or digest
  mismatch fails the job loudly naming the recorded version+digest pair, and an
  already-valid store is reused untouched (idempotent).
- On governor failure the report JSON is printed to the job log and published
  as the `governor-diagnostics` artifact; the job exit stays non-zero (no
  suppression anywhere). A passing run publishes no artifact.
- On integrated `main` the governor reports the shipped/done state honestly
  (`kind=shipped-integrated;` with the archive path) and exits 0 — the typed
  `shipped-integrated` classification, not a suppressed failure.
- PR-triggered runs check out a detached merge ref where the documented
  fail-closed branch ownership fires: a red PR run with published diagnostics
  is documented honest behavior, not a defect.

## M002 continuation (current)

Milestone `post-ship-hardening` is active on `gsd-path/M002` (base `4e0cd4db`).
Workflow truth lives in `.project/STATE.md`; `prd/project-state/roadmap.md` +
`prd/project-state/data/roadmap.json` carry the matching projection marker.
Wave 1 landed the vendored-runtime restore and the honest `shipped-integrated`
classification (T001, T002); still in flight in this milestone: the
context-independent governor/preflight test matrix (T003 — five documented
scenarios: active milestone on its bound branch, foreign branch, detached
checkout, verify sidecar, shipped integrated main, behind one shared branch
predicate, with the fail-closed branch-ownership contract pinned where the
governor cannot be operational), the post-ship pointer refresh (T004, this
document), and the fresh-session acceptance walkthrough (T005, on-disk proof).

Post-ship pointers refreshed by task T004 (this milestone):

- `prd/project-state/roadmap.md`: the live marker names `post-ship-hardening`
  on `gsd-path/M002`; a dated superseded bullet records the shipped/archived/
  integrated M001 (ship `886a36a8`, integration `4e0cd4db`).
- `docs/agent-stack/history/LEGACY_CROSSWALK.md`: the M225 row records the
  residual closed by T004 of M001, links the rerun receipt with verdict
  `hermetic-pass-parity-unproven`, and states corpus parity remains unproven.
- `.project/research/DOCS-AUDIT.md`: queue rows #6/#19 reference T005 (minimal
  PDD model) and row #9 references T006 (GitNexus re-index) of M001.

## Fresh-session bootstrap

Given only this repository and this section, a fresh session bootstraps from
disk alone. Run the commands in a terminal at the repository root, in this
order, and record every command with its real output at the proof file
`M002-ACCEPTANCE-PROOF.md` in the pipeline `.project/build/` workspace. A
failing command is recorded verbatim and blocks — it is never smoothed over.
Chat history is not proof.

1. Restore/verify the pinned GSD Path runtime from the vendored archive
   (idempotent: an already-valid store is reused untouched; a digest mismatch
   or a missing archive fails loudly naming the pinned version+digest pair):

   ```bash
   tar -xzf .ai/vendor/gsd-path-1.6.2.tgz -C <temporary-dir>
   python3 <temporary-dir>/gsd-path/scripts/install.py --runtime-restore --project <repo-root> --source-root <temporary-dir>/gsd-path
   ```

   `<temporary-dir>` is any throwaway directory outside the repository — the
   extraction target is never a tracked path; `<repo-root>` is this checkout's
   root.

2. Read the workflow status — on the M002 bound branch expect branch
   `gsd-path/M002`, milestone `post-ship-hardening`, and the shipped/archived
   M001 (ship `886a36a8`, integration `4e0cd4db`); on integrated `main` expect
   the shipped/done state instead:

   ```bash
   python3 scripts/ai/path-run.py status
   ```

3. Run the real governor — expect exit 0 in both operational contexts:

   ```bash
   uv run --frozen python -m law_nexus_harness.governor
   ```

4. Run the roadmap freshness guard — expect all tests to pass:

   ```bash
   uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
   ```

If the pinned bootstrap is missing or ambiguous (archive absent, digest
mismatch, status not recognizing the recorded state), record the failure
verbatim in the proof file and stop — do not improvise a different restore
path.

## Non-claims

- Corpus parity for the Rust reference layer (M225/ADR-0031) remains unproven;
  the closed residual's verdict is `hermetic-pass-parity-unproven`.
- The roadmap projection is a non-authoritative cold-reader summary; durable
  authority stays with `prd/ARCHITECTURE.md` and `doc/adr/**`.
- Workflow and delivery completion is not product readiness; product readiness
  remains unproven.
