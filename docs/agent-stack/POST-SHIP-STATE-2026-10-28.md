# Post-ship state — 2026-10-28

- Date: 2026-10-28.
- Role: current-state document for the `law-nexus` repository.
- Supersedes: `docs/agent-stack/POST-SHIP-STATE-2026-10-27.md` as the current-state
  document. That file remains untouched as the dated M001–M003-era snapshot
  (2026-10-27); its CI section records the pre-M003 world, which the live CI
  section below re-records with the runs since.
- Written by: build_T002 (coder, milestone `pointer-refresh-m003` — the fourth
  milestone, bound branch `gsd-path/M004`). Records delivery and workflow state
  only; it is not a legal or product authority.

## Shipped milestones (recorded facts)

Three milestones shipped, archived and integrated since the 2026-10-25
bootstrap PR merge (`54a495cd`):

| Milestone | Ship commit | Integration merge | Tag | Archive |
|---|---|---|---|---|
| M001 `001-native-workflow-acceptance` | `886a36a8` | `4e0cd4db` | `milestone/001-001-native-workflow-acceptance` | `.project/archive/001-001-native-workflow-acceptance` |
| M002 `post-ship-hardening` | `ba31ffb8` | `f9061889` | `milestone/002-post-ship-hardening` | `.project/archive/002-post-ship-hardening` |
| M003 `ci-honesty` | `7786d5d3` | `7e200294` | `milestone/003-ci-honesty` | `.project/archive/003-ci-honesty` |

Archives are read-only; each `MANIFEST.md` carries the ship-time criterion
verdicts. Cutover stays `false` (a later owner decision; standing deferral).

What each milestone proved and delivered (recorded facts):

- M001: the native GSD Path delivery workflow executed end to end on bound
  branch `gsd-path/M001`; the M225 validation residual closed with an honest
  re-run (`prd/migration/rust-evidence/m225-validation-rerun-m001.json`,
  verdict `hermetic-pass-parity-unproven` — corpus parity explicitly
  unproven); the minimal PDD model landed in `product-model/`; the GitNexus
  index was regenerated; the fresh-session resume proof was recorded on disk.
- M002: CI restores the pinned GSD Path runtime from the vendored archive
  (`.ai/vendor/gsd-path-1.6.2.tgz`, digest-verified against
  `.gsd-path/runtime.json`: `1.6.2@6f95a31e…`) before any operational check;
  the governor classifies integrated main honestly (`kind=shipped-integrated;`,
  exit 0); the governor/preflight suites became context-independent (five
  scenario groups, the fail-closed branch-ownership contract pinned per the
  M001 owner ruling); the post-ship pointers were refreshed and
  POST-SHIP-STATE-2026-10-27.md superseded the pre-ship cutover snapshot; the
  fresh-session acceptance proof was recorded
  (`.project/archive/002-post-ship-hardening/build/M002-ACCEPTANCE-PROOF.md`).
- M003: the live governor/preflight expectations key on STATE.md phase
  semantics (`build/active`, `shipped/done`) instead of milestone-branch
  literals, with a grep pin test enforcing the ban; the governor-diagnostics
  artifact publishes on any migration-job failure (including the pytest steps
  that precede the governor step) with the job exit preserved non-zero; the
  roadmap three-way identity (STATE.md ↔ roadmap.json ↔ live marker) stayed
  consistent at the reviewed HEAD.

## CI state on integrated main through M003 (dated history)

This section is the dated pre-M005 record (2026-10-25 .. 2026-10-28). The
live state is green: see "M005–M009: red CI cleared" below — run 40805352394
at `319a7b1a` success, re-confirmed by the newest main run 40822037565 at
`3a39fd70` success (recorded by the 2026-10-30 docs audit).

The last green `repository-quality` run on `main` then was run 40203533977
(2026-10-25, on the bootstrap merge `54a495cd`). Every integration push in
that window ended red:

| Run | Push | Conclusion | Failed step(s) |
|---|---|---|---|
| 40446077586 | `4e0cd4db` (M001) | failure | migration governor step exited 1 `runtime-unavailable` (pinned runtime not restorable in CI; fixed by M002's vendored restore) |
| 40533158703 | `f9061889` (M002) | failure | migration `Harness status and preflight contracts`; Rust `Product and architecture harness tests` |
| 40632991938 | `7e200294` (M003; current `origin/main`) | failure | migration `Governor report is honest about bootstrap mode`; Rust `Product and architecture harness tests` |

The M003-integration run (40632991938, 2026-10-28) is the live evidence, and
its two failures differ in kind:

- The migration job's governor output is honest. The diagnostics step printed
  the full report: `kind=shipped-integrated;` naming
  `archive .project/archive/003-ci-honesty`, `pass_count=72`, `error_count=0`,
  and the `governor-diagnostics` artifact published as designed (the M003
  publish-on-failure behavior). The step then failed its own expectation: the
  expected-fact list (`.github/workflows/repository-quality.yml` lines 264–265
  at `7e200294`) still requires the observed fact to contain the M001 archive
  path `.project/archive/001-001-native-workflow-acceptance` — a milestone
  literal written when M001 was the latest archive, stale since the M002 ship
  moved it.
- The Rust job's live governor/preflight suites failed 16 tests (520 passed,
  2 skipped). Every failure is a shipped/done arm expecting a green
  SHIPPED_MAIN surface: `workflow-state-surface` expected pass, observed
  fail; preflight exit expected 0, observed 1; live governor `error_count`
  expected 0, observed 1. A structural asymmetry in the workflow matches the
  observed behavior: the `Prepare shipped-main integration proof inputs` step
  (`git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main`,
  lines 214–219) exists only in the migration job, so in the Rust job's
  checkout the pinned runtime cannot prove the integration landing. The
  failing assertions and the asymmetry are recorded here as facts; a
  runtime-level reproduction is not part of this report.

This red state was the live signal the next milestone started from. Fixing it
was outside M004's approved scope (a pointer refresh with no product or workflow
changes); nothing in this milestone suppresses, skips, or reinterprets a
failing run (standing prohibition: no masking of a non-zero exit).

## M004 continuation (superseded)

This section is dated history. M004–M010 shipped and integrated (see the
M005–M009 section below and the roadmap marker; M010 shipped/archived/
integrated 2026-10-29), and at the 2026-10-30 docs audit the workflow state
is shipped/done M010 with M011 inspect active — workflow truth lives in
`.project/STATE.md`. The M004 record below is kept verbatim.

Milestone `pointer-refresh-m003` (the fourth milestone; branch
`gsd-path/M004`, base `7e200294`) was active at the time; workflow truth
lives in `.project/STATE.md`. Owner-approved scope (2026-10-27): post-ship
pointer refresh —

- task T001 refreshes the roadmap marker to the shipped `ci-honesty` state
  (`prd/project-state/roadmap.md` + `prd/project-state/data/roadmap.json`),
  the DOCS-AUDIT queue rows closed by M001–M003 tasks
  (`.project/research/DOCS-AUDIT.md`), and the crosswalk M225 row
  (`docs/agent-stack/history/LEGACY_CROSSWALK.md`: rerun-receipt link,
  residual closed);
- task T002 writes this report and repoints the agent entry documents
  (`AGENTS.md`, `docs/agent-stack/AGENT_HANDOFF.md`) at it.

Scope-out (standing): strict corpus run, PDD wrapper bootstrap, Allspark
identity pilot, product feature work; cutover stays `false`.

## M005–M009: red CI cleared (recorded facts)

The CI section above records the pre-M005 world. Every cause it names was fixed,
and the integrated `main` is green:

| Run | Push | Conclusion |
|---|---|---|
| 40805352394 | `319a7b1a` (M009) | success — all four jobs; the corpus job is skipped without the corpus |

What each milestone changed, in order:

| Milestone | Ship | Integration | Change |
|---|---|---|---|
| M005 `ci-fixture-fix` | `e890831e` | `121a2006` | The roadmap-freshness fixture derives its milestone from the tracked `roadmap.json`; the bound-branch surface pins accept `build/active` and `shipped/done`. |
| M006 `red-ci-clear` | `7d1c62c2` | `3e047fe8` | The governor honesty step asserts the `kind=shipped-integrated;` shape and a `.project/archive/` path instead of the M001 archive literal; the projection was refreshed. |
| M007 `ci-proof-inputs` | `e311f0ed` | `50386e26` | The Rust job checks out the full history and tags and prepares `origin/HEAD`, so the pinned runtime proves the shipped integration; the governor step prints the observed surface and the proof inputs. |
| M008 `pointer-in-ci` | `63c7d07d` | `4dd35d25` | Both post-ship pointer suites run in CI, so a stale projection fails a job instead of reaching `main`. |
| M009 `projection-at-ship` | `5e5fdaee` | `319a7b1a` | The projection names the milestone being shipped, refreshed in a `docs:` commit before the `.project`-only ship commit; the rule is recorded in `docs/agent-stack/SHIP-TIME-PROJECTION-REFRESH.md` and pinned. |

What M005–M009 did not change: `prd/project-state/workflow-backend.json`
`cutover` stays `false` — the owner's decision — and no failing run is
suppressed, skipped, or reinterpreted. The M003-era red rows above stay as the
dated record of what the failures were.

## Fresh-session bootstrap

Given only this repository and this section, a fresh session bootstraps from
disk alone. Run the commands in a terminal at the repository root, in this
order, and record every command with its real output in the working
milestone's proof file under the pipeline `.project/build/` workspace. A
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

2. Read the workflow status — on the active bound branch expect branch
   `gsd-path/M004` and milestone `pointer-refresh-m003` in its recorded phase,
   with M001–M003 shipped/archived/integrated; on integrated `main` expect the
   shipped/done state instead — the observed fact names the archive path
   recorded in that checkout's `STATE.md` (the archive moves every milestone,
   so no fixed archive literal is asserted here):

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
- The roadmap projection (`prd/project-state/roadmap.md` +
  `prd/project-state/data/roadmap.json`) is a non-authoritative cold-reader
  summary; durable authority stays with `prd/ARCHITECTURE.md` and
  `doc/adr/**`.
- Integrated `main` is green on `repository-quality` since the M009
  integration (run 40805352394 at `319a7b1a`; re-confirmed by main run
  40822037565 at `3a39fd70`, recorded 2026-10-30) — the pre-M005 red rows in
  the CI section above stay as dated history; a shipped milestone is a
  delivery record, not itself a green-CI claim.
- Workflow and delivery completion is not product readiness; product readiness
  remains unproven. Cutover stays `false`.
