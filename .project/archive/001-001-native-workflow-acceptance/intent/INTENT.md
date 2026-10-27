# Intent — law-nexus

<!-- Written by $gsd-path-define (standard mode, brownfield + supplied-spec).
     Supplied spec: /root/law-nexus/.project/research/supplied-spec-2026-10-26.md
     Every downstream agent reads this first. Constraints and vetoes here
     override everything downstream. -->

Lane: standard   <!-- ~9 deliverable-sized tasks, cross-wave integration risk,
                      RESEARCH/NEEDS-USER items present — not quick. -->

Review panel: off   <!-- configured runtime preference (built-in default); no
                      CHARTER, no explicit owner choice. -->

Finding skeptics: off   <!-- default. -->

Surfaces: terminal (native Path CLI: path-run.py status, governor, pytest, git), GitHub (gsd-path/M001 branch, commit history, CI runs)

## Summary

The GSD Path bootstrap is merged (main@54a495cd) but the native delivery
workflow has zero practical proof: no milestone has ever been defined,
validated, reviewed and resumed through it, and cutover (C7) stays off until
that proof exists (supplied spec: `.project/research/supplied-spec-2026-10-26.md`, relocated by the owner-ruled pre-ship relocation).
Milestone M001 turns the standing pre-milestone fixes into landed tasks, binds
the milestone to the roadmap marker, closes the M225 validation residual
natively, creates the minimal PDD model, and runs one limited task through the
full native cycle — worker, native validators, independent review — plus a
session close/resume proof. Results are published and a written cutover
readiness assessment is produced; cutover itself is not flipped.

## Problem

The repository's delivery process was migrated on paper (bootstrap accepted,
CI green under the documented advisory policy), but every claim about the new
workflow is still unproven in practice: the milestone registry is empty, the
roadmap marker still names the frozen Pi milestone, five verified harness
fixes sit uncommitted because the guard correctly blocks product files outside
build, and the M225 validation battery has a `pending-fill-by-validate-unit`
revision hole. The owner cannot justify C7 (final cutover) without one
complete native cycle and a resume proof.

## Users

The owner (single human, reviews verdicts and rules on gates) and the AI
agents that operate this repository's delivery through native Path. They use
the terminal CLI (`path-run.py`, governor, pytest, git) and GitHub (branch,
history, CI runs).

## Success criteria

1. SC1 — The five pre-milestone fixes are landed as task commits on
   `gsd-path/M001`; `uv run --frozen pytest tests/test_harness_governor.py
   tests/test_phase_dispatch_adapter.py` reports 0 failures on the bound
   branch.
2. SC2 — The workflow marker in `prd/project-state/roadmap.md` names this
   Path milestone slug exactly; the governor reports 0 errors on the bound
   branch with the milestone set (no pre-milestone exception in play).
3. SC3 — The M225 validation residual is closed natively: the battery records
   a filled `tested_source_revision`, the source pin is re-bound to the exact
   validation HEAD, native validation is re-run and an honest verdict (with
   its measurement class) is recorded; S02 code is unchanged.
4. SC4 — `product-model/` exists with a minimal PDD model of the already
   established product behavior (stubs modeled as stubs, nothing aspirational);
   the PDD statements in AGENTS.md and docs/agent-stack/WORKFLOW.md are true
   (audit #6/#19).
5. SC5 — GitNexus is re-indexed and the tool block in AGENTS.md matches the
   live index (audit #9).
6. SC6 — One limited task runs the full native cycle: dispatch, worker,
   native validators, and an independent review (different evidence path or
   different model family; a same-family re-run does not count), with evidence
   recorded under `.project/` (task log, verify sidecar, review verdict).
7. SC7 — The session is closed with a handoff and a fresh session resumes
   from disk alone; the proof is the new session's recorded verification
   output.
8. SC8 — a written cutover readiness assessment exists recording the
   milestone's per-criterion evidence, the CI policy honesty (M207 advisory,
   corpus job skipped — green CI never proves corpus scenarios ran), the
   settled corpus-delivery direction (runner-only, pinned zstd snapshot
   shape, on-runner layout contract), and the CI/publication evidence status;
   the bound branch publishes through ship integration only (the repository's
   pre-push guard is the enforcing contract and CI runs on the integrated
   main surface), so publication and CI evidence are recorded as pending-ship,
   not produced inside this milestone; `cutover` remains `false`.
9. SC9 — Small package landed: the m207 schema check no longer runs under an
   unconditional `|| true`; the corpus job config matches its comment (or the
   comment states the actual setup); `workflow_state.py` rejects a present
   optional field of the wrong type while accepting missing/null, with a
   regression test; no new blanket suppression may be introduced.
10. SC10 — `a.txt`, `b.txt`, `c.txt` are deleted from the repository root.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | concurrency | held-out | An interrupted task landing recovers only through `isolation.py recover`; manual git repair is vetoed. Owner ruling delegated 2026-10-26 («реши все разумно…»), recommended option adopted; pinned by the isolation helper contract and its existing tests. |
| E2 | SC2 | empty | criterion SC2 | A missing or mismatched workflow marker is a governor blocking error (fail-closed); the marker must equal the milestone slug exactly. |
| E3 | SC3 | precision | held-out | `tested_source_revision` is the full 40-hex SHA of the exact HEAD the re-validation ran at; any mismatch invalidates the battery. Delegated ruling, recommended option. |
| E4 | SC4 | empty | criterion SC4 | "Minimal" means existing observable behavior only; stubs are modeled as stubs; no future or desired behavior enters the model. |
| E5 | SC5 | idempotency | held-out | If `analyze` fails: keep the previous AGENTS.md block, report the error, never hand-edit the block. Delegated ruling, recommended option. |
| E6 | SC6 | concurrency | criterion SC6 | Review independence = a different evidence path or a different model family; same-model agreement is one evidence path (operating rules). |
| E7 | SC7 | idempotency | dismissed | STATE.md is the single journaled source and resume is read-only validation; a repeated resume is harmless. |
| E8 | SC8 | concurrency | held-out | One rerun for a red CI run on the push; persistently red means SC8 is unmet — fix it or document the failure as advisory. Delegated ruling, recommended option. |
| E9 | SC9 | boundary | held-out | Known documented conflicts (frozen-token D466/D487, items in the migration record) stay advisory; any unknown blocking-check failure stops the job. Adapter rule: missing/null optional fields accepted, present wrong-typed values rejected (reviewer's wording). Delegated ruling, recommended option. |
| E10 | SC10 | empty | dismissed | The mapper found zero references to the files in scripts, CI, or tests; deletion is reversible through git history. |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC3 | record a corpus-absent hermetic green run as a byte-parity PASS | criterion SC3 | The recorded verdict must state its measurement class; hermetic-skip is observability, not parity proof (MEM2180/L003 precedent already in the battery). |
| N2 | SC8 | flip `cutover` to `true` inside this milestone | criterion SC8 | SC8 delivers a written readiness assessment only; C7 stays off. |
| N3 | SC9 | suppress unknown blocking-check failures (a new unconditional shell-truth fallback or `continue-on-error` without a documented advisory record) | criterion SC9 | SC9 states the rule; the reviewer checks the workflow diff for any new unconditional suppression. |
| N4 | SC2 | rewrite product roadmap history (M-numbers, completed milestone rows) to satisfy the marker sync | judgment | Only the workflow marker line changes; the final reviewer checks the diff touches nothing else in `prd/project-state/roadmap.md`. |
| N5 | SC4 | record desired or future behavior as established current behavior | criterion SC4 | The model maps only what exists; stubs stay stubs (same ruling as E4). |
| N6 | SC5 | present a stale or hand-edited index state as the live tool block | criterion SC5 | SC5 requires the block to match the live index; E5 pins the failure handling. |
| N7 | SC6 | let the coding worker accept its own task (self-review counted as independent review) | criterion SC6 | SC6 defines independence: a different evidence path or a different model family. |
| N8 | SC7 | count re-reading chat history as resume proof without the new session's recorded on-disk verification output | criterion SC7 | SC7 names the evidence: the fresh session's recorded verification output. |
| N9 | SC1 | none | dismissed | Internal engineering surface; no values/safety/privacy/fairness/transparency dimension beyond the mechanical criteria themselves. |
| N10 | SC10 | none | dismissed | Deleting three unreferenced 1-byte files affects no person directly and is reversible via git. |

## Scope: in

- Land the five pre-milestone patched files (copies:
  `/root/law-nexus-pre-milestone-fix/`) as the first build task(s).
- Sync the workflow marker in `prd/project-state/roadmap.md` to this
  milestone (audit #15 ride-along).
- Carry the M225 validation residual into a native task: fill
  `tested_source_revision`, re-bind the pin, re-run validation, record the
  honest verdict.
- Create the minimal PDD model under `product-model/` by mapping established
  behavior (audit #6/#19), keeping AGENTS.md/WORKFLOW.md claims true.
- Re-index GitNexus and regenerate the AGENTS.md block (audit #9).
- Land the small package: CI policy split (mandatory portable checks vs
  advisory), corpus job config/comment agreement, `workflow_state.py`
  type-check tightening with regression test.
- Run one limited task through the full native cycle with independent review
  (SC6), close the session and prove resume (SC7).
- Publish `gsd-path/M001` to origin, confirm CI within policy, write the
  cutover readiness assessment (SC8).
- Delete `a.txt`/`b.txt`/`c.txt` (SC10).

## Scope: out (vetoes)

- Re-implementation of M225/S02 — crosswalk: "Do NOT re-implement S02"; only
  the validation residual moves.
- Any work on the paused queue M208/M217/M218/M219/M220 — owner ruling
  2026-10-26 (round 1, item 7).
- Rewriting historical Pi hashes/receipts — standing ruling (`e1025e0`):
  historical evidence keeps its hash semantics; a new corpus run by those
  producers needs a versioned producer/receipt instead.
- Flipping `cutover` to `true` — this milestone assesses readiness only.
- `git stash` in this repository — standing owner rule (foreign Pi-history
  stash corrupted the tree once); baselines via `git worktree add`.
- Product feature work (corpus ingestion, retrieval stack, embeddings beyond
  `StubEmbedding`) — M001 is workflow acceptance; product direction is a
  later owner decision.

## Constraints

- Bound branch `gsd-path/M001`; integration mode `direct` (STATE.md); ship is
  the only path into `main`.
- Rust workspace posture: hand-rolled infra only — no tokio/clap/anyhow/thiserror/regex/chrono (Cargo.lock); versioned JSON verdict schemas; Conventional Commits, English subjects; tracked prose English.
- Python runs through `uv run --frozen` (as CI does); not `.venv/bin/python`,
  not bare `pytest`.
- Governor is branch-locked and fails closed away from the bound branch — by
  design.
- CI policy boundaries: M207 batteries are report-only (`continue-on-error`);
  the strict corpus job stays skipped until a runner/corpus delivery exists;
  green CI does not prove corpus scenarios ran.
- The five fixes are already applied in the working tree (guard blocks
  product-file commits outside build); canonical patches live in
  `/root/law-nexus-pre-milestone-fix/`.
- `.gsd` (symlink) and other vaults are read-only historical snapshots; not
  product truth.

## Current state (brownfield only)

- **What exists**: 47-crate Rust workspace (hexagonal leaf crates
  `domain/ports/adapters/application`, 33 shared port-contract suites, hostile
  runner belt HC-01…HC-20), thin Python control-plane harness
  (`law_nexus_harness`, ~17.6k LOC, 57 read-only governor checks), product CLI
  with in-memory stores and fail-closed `StubEmbedding`; no `[validated]`
  capability yet. Pipeline at `define/active` on `gsd-path/M001` (head
  `1b934188`, base `origin/main` `54a495cd`).
- **Must not break**: harness baselines (governor 248 passed / 0 failed,
  dispatcher 27 / 0 with `uv run --frozen`); governor fail-closed branch lock;
  the recorded historical Pi evidence chain.
- **Doc-vs-code rulings**: all 19 audit rows ruled 2026-10-26 — 15 fix-doc
  (alignment queue, `planned: no`), 4 fix-code (#6/#19 minimal PDD inside this
  milestone, #9 GitNexus re-index, #16 rides as fix-doc per round-1 item 5);
  recorded verbatim in `research/DOCS-AUDIT.md ## User rulings`.
- **Ground truth**: `.project/research/evidence-codebase.md`,
  `.project/research/DOCS-AUDIT.md`

## Risks

- The corpus is absent locally; strict corpus proof is impossible until a
  runner with data or reproducible delivery exists (kept out of M001;
  [RESEARCH] below).
- Making the schema check blocking may surface unknown failures — that is the
  intent, but it can add unplanned fix work into the wave.
- M225 re-validation may remain honestly inconclusive on parity without the
  corpus; SC3 requires the honest verdict, not a green one.
- Roadmap marker sync touches a tracked product doc; the change must stay
  inside the marker line (N4).

## Open questions

- [RESEARCH] Corpus delivery path for the strict corpus job: self-hosted runner with attached data vs reproducible delivery of a pinned corpus snapshot. Needed before any strict corpus claim; not blocking M001.
- [NEEDS-USER] Schedule the M208/D512 admission-contract decision (stays
  pending per round-1 item 7).
- [NEEDS-USER] Schedule the frozen-token ADR amendment (D466/D487) or a
  witness-relocation alternative.
- [NEEDS-USER] Product direction after M001: full-corpus ingestion vs live
  retrieval stack (mapper's open question; recent activity hints parser-first).

## Corrections

- 2026-10-26: «двигай {…}» — external review directive accepted as the
  supplied spec; saved verbatim at
  `.project/supplied-spec-2026-10-26.md`.
- 2026-10-26: «продолжаем - двигай проект» — owner accepted all round-1
  recommended rulings (milestone framing, small package inside M001, minimal
  PDD, GitNexus re-index, README reword, junk deletion, deferrals, fix-doc
  queue); recorded in `research/DOCS-AUDIT.md ## User rulings`.
- 2026-10-26: «реши все разумно,элегантно и оптимально для целей репозитория»
  — owner delegated the QA/E1–E10 edge rulings and the prohibition rulings to
  this session; the recommended option was adopted in every case and recorded
  in the tables above.
- 2026-10-26: «(a)» — owner ruling from the build-recovery correction (T009
  NEEDS-ORCHESTRATOR): publication+CI are ship-phase-gated — the repository's
  pre-push guard refuses moving `gsd-path/M001` to origin before its ship
  commit, and repository-quality CI triggers main-push/pull_request only.
  SC8 re-scoped: T009 writes the cutover readiness assessment now with
  publication and CI recorded as pending-ship (they execute at ship
  integration — the CI acceptance surface is the integrated main per the
  documented M207 policy); `cutover` remains `false`.
- 2026-10-26: «(a)» (second application, ship phase) — owner sanctioned one
  pre-ship relocation commit: the five tracked top-level `.project` artifacts
  (two session handoffs, the supplied spec, the T007 handoff, the T008 resume
  proof) moved into the allowlisted `research/` and `build/` directories
  (content byte-identical; landing proofs re-verified proven-landed in a probe
  worktree); current-location citations updated in this Summary, PLAN.md's
  Surface contract, and CUTOVER-READINESS-M001.md.
