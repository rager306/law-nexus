# Synthesis

<!-- Written by the decider role, milestone M001 (single-milestone flow, no
     CHARTER.md). The planner treats Decisions as settled. Settled lines are
     closed by their cited sources and carry no runner-ups. The corpus
     exposure fork is a true values call and is held as NEEDS-USER, not
     decided here. -->

## Settled

- Branch and integration — all M001 work lands on the bound branch `gsd-path/M001`, integration mode `direct`, ship is the only path into `main` (INTENT.md Constraints; STATE.md).
- Commands and runtime — Python runs only through `uv run --frozen`; the Rust workspace keeps its hand-rolled-infra posture (no tokio/clap/anyhow/thiserror/regex/chrono) (INTENT.md Constraints; evidence-codebase.md Map, Conventions).
- Cutover — stays `false`; M001 produces only the written readiness assessment (INTENT.md Scope out, prohibition N2).
- M225/S02 — no re-implementation; only the validation residual moves into SC3 (INTENT.md Scope out; crosswalk ruling).
- Paused queue M208/M217/M218/M219/M220 — out of M001 (owner ruling 2026-10-26, round 1 item 7; INTENT.md Scope out).
- Historical Pi hashes and receipts — never rewritten; any new corpus run by those producers needs a versioned producer/receipt (standing ruling `e1025e0`; INTENT.md Scope out).
- `git stash` — banned in this repository; baselines via `git worktree add` (standing owner rule; INTENT.md Scope out).
- Product features — corpus ingestion, retrieval stack, embeddings beyond `StubEmbedding` are out of M001 (INTENT.md Scope out).
- Five pre-milestone fixes — land as the first build task(s) from the canonical patches in `/root/law-nexus-pre-milestone-fix/`; they are already applied in the working tree and guard-blocked from committing outside build (INTENT.md Scope in + Constraints).
- CI policy boundary — M207 batteries stay report-only `continue-on-error`; the strict corpus job stays skipped in M001; green CI never proves corpus scenarios ran (INTENT.md Constraints).
- M225 verdict honesty — the recorded verdict states its measurement class; a corpus-absent hermetic green run is never recorded as a byte-parity PASS (INTENT.md prohibition N1).
- Marker sync shape — only the workflow-marker line in `prd/project-state/roadmap.md` changes; roadmap history is not rewritten (INTENT.md prohibition N4).
- Schema-check tightening — the m207 schema check stops running under an unconditional `|| true`; known documented conflicts (frozen-token D466/D487, migration-record items) stay advisory, unknown blocking-check failures stop the job, no new blanket suppression (INTENT.md SC9, E9, N3).
- workflow_state.py type rule — a present optional field of the wrong type is rejected while missing/null is accepted, with a regression test (INTENT.md E9, SC9).
- SC6 review independence — a different evidence path or a different model family; a same-family re-run or the worker's own acceptance does not count (INTENT.md E6, N7).
- SC7 resume proof — STATE.md is the single journaled source; the proof is the fresh session's recorded on-disk verification output, not re-reading chat history (INTENT.md E7, N8).
- SC10 — `a.txt`, `b.txt`, `c.txt` are deleted; the mapper found zero references in scripts, CI, or tests, and deletion is reversible through git history (INTENT.md E10; evidence-codebase.md Map, Maturity).
- GitNexus re-index — `node .gitnexus/run.cjs analyze --force --name law-nexus`; on failure keep the previous AGENTS.md tool block and report the error, never hand-edit (AGENTS.md GitNexus section; INTENT.md E5).
- Minimal PDD model — maps only established observable behavior; stubs modeled as stubs, nothing aspirational (INTENT.md E4, N5; audit #6/#19 fix-code rulings in DOCS-AUDIT.md).
- Corpus absence — strict corpus proof is impossible locally until a runner with data or reproducible delivery exists; kept out of M001 (INTENT.md Risks; evidence-codebase.md Map, Maturity).
- Lane and review config — standard lane, review panel off, finding skeptics off (INTENT.md frontmatter).
- Edge and prohibition rulings — E1-E10 and N1-N10 stand exactly as recorded, adopted under the owner's delegated ruling of 2026-10-26 (INTENT.md Corrections: «реши все разумно,элегантно и оптимально для целей репозитория»).

## Decisions

### Strict corpus job in M001 — SC9 fix shape

- **Decision**: The `corpus-integration` job keeps `runs-on: ubuntu-latest` and stays skipped; the SC9 fix aligns the workflow comment with the actual setup (a GitHub-hosted label where the corpus is absent, so the job must stay skipped and no `LAW_NEXUS_CORPUS_AVAILABLE` value is set). The exposure ruling landed 2026-10-26 as **runner-only**, so the deferred routing rework now has a settled direction for any future strict job: an explicit restricted self-hosted runner label (never `ubuntu-latest`, protected branches only, ephemeral secret-free runner), and hosted snapshot-fetch routing is ruled out.
- **Runner-up**: Retarget the job now to an explicit self-hosted label — lost because GitHub's hardening guidance makes that the dangerous default on this public repo unless restricted, the exposure ruling decides which target is actually correct, INTENT marks the question "not blocking M001", and SC9 explicitly allows "or the comment states the actual setup".
- **Evidence**: .project/research/evidence-stack.md, findings "the current job cannot route to a self-hosted runner at all — `ubuntu-latest` is a GitHub-hosted label" and "the corpus is deliberately kept off GitHub's surface, and every hosted delivery surface would publish it on a public repo"; INTENT.md SC9 and Open questions.
- **Confidence**: high

### Corpus delivery artifact shape (holds under any exposure ruling)

- **Decision**: Any future snapshot-based corpus delivery is a single pinned zstd tarball of `consru_export/consru_export/exports/` (measured 0.30 GiB, 11.9x compression) with a recorded sha256 that the consuming job verifies before strict tests run; workflow artifacts are never the delivery channel.
- **Runner-up**: Per-file delivery — tracking all 43,785 XML files individually (for example one Git LFS pointer each) — lost as impractical, and as public-repo LFS objects it would inherit the exposure problem; workflow artifacts additionally fail quantitatively (a 318 MB snapshot against a 500 MB Free-plan shared quota with 90-day expiry), so they cannot be reproducible delivery.
- **Evidence**: .project/research/evidence-stack.md, findings "the corpus is measured, not assumed — 3.53 GiB uncompressed, 0.30 GiB compressed", "a pinned snapshot fits every GitHub-hosted channel with measured headroom — release assets, cache, and container layers", "Git LFS is workable only as a single archive blob, and its free quotas are community-documented", "artifacts are quantitatively disqualified as the corpus channel on a Free plan".
- **Confidence**: high — load-bearing inputs are the measured sizes and the primary-documentation per-file limits; the community-documented LFS quota figures are not load-bearing.
- **Ruling note (2026-10-26)**: under the runner-only exposure ruling no snapshot is published today; this shape governs any future upload if that ruling is ever revisited.

### Actions cache role for any strict corpus job

- **Decision**: The Actions cache is a best-effort accelerator only: a strict corpus job restores best-effort, verifies the recorded snapshot checksum after restore, and turns cache absence into a visible skip or failure; a cache hit never substitutes for the pinned delivery channel in a strict claim.
- **Runner-up**: Cache as the primary delivery channel — lost because entries are evicted LRU over the 10 GB repo limit, deleted after 7 days untouched, and `restore-keys` prefixes can silently deliver a different snapshot version than the one a strict claim assumes — exactly INTENT's N1 green-but-unproven pattern.
- **Evidence**: .project/research/evidence-stack.md, finding "a cache is an evictable accelerator, not a reproducible delivery channel"; INTENT.md prohibition N1.
- **Confidence**: high

## For the planner

- **Wave-1 blockers**: (1) Five-fix landing integrity — apply/confirm the canonical patches from `/root/law-nexus-pre-milestone-fix/` on `gsd-path/M001` and run SC1's exact command (`uv run --frozen pytest tests/test_harness_governor.py tests/test_phase_dispatch_adapter.py`) before anything builds on the fixes; the working tree already carries the edits, so tree-vs-patch drift is the assumption to burn first. (2) The de-suppressed m207 schema check must run green early or surface its unknown failures while fix capacity remains in the wave — INTENT flags this as the unplanned-fix-work risk. (3) Marker sync (SC2) with the governor reporting 0 errors and the milestone set — the branch-locked, fail-closed governor gates every later native claim on the bound branch.
- **Walking skeleton**: The thinnest end-to-end proof is SC6 + SC7 carried by a deliberately trivial task — SC10 junk-file deletion is the natural carrier (zero product risk, zero dependencies): dispatch, worker, native validators, independent review per E6, evidence recorded under `.project/`, then session close and a fresh session's recorded on-disk verification. A risk-ordered shape (the planner owns the exact split): wave 1 = SC1 + SC2 + SC9 + SC10; wave 2 = the independent SC3, SC4, SC5; final wave = SC6 cycle proof, SC7 resume, SC8 publish plus the readiness assessment.
- **Pitfalls → tasks**: each known trap mapped to the task that must dodge it:
  - Guard blocks product-file commits outside build → SC1 lands the five fixes only as build tasks from the canonical patches.
  - `ubuntu-latest` is a hosted label; setting `LAW_NEXUS_CORPUS_AVAILABLE=1` turns the corpus job red on hosted runners → SC9 rewrites the comment to state the actual setup and touches no routing (decision above).
  - N1 green-but-unproven pattern → SC3 records the measurement class; SC8's readiness assessment states that green CI does not prove corpus scenarios ran.
  - N4 marker-only diff → SC2's change touches only the marker line; the final reviewer checks nothing else moved in `prd/project-state/roadmap.md`.
  - E5 analyze-failure handling → SC5 keeps the previous AGENTS.md tool block and reports the error; never hand-edit the block.
  - E9/N3 suppression boundary → SC9's regression test pins missing/null accepted vs present-wrong-typed rejected; no new unconditional `|| true` and no undocumented `continue-on-error`.
  - Corpus layout contract (future task, recorded in the readiness assessment, not built in M001): strict tests resolve `consru_export/consru_export/exports/` under the repo root (or `CONSULTANT_EXPORT_DIR`) and hard-fail under `LAW_NEXUS_REQUIRE_CORPUS=1`, so whichever channel the user picks must materialize that exact path and let the tests' own hard-fail prove delivery (evidence-stack.md, finding "the strict tests pin the exact on-runner layout any delivery must produce").
  - Cache restore-keys silent drift → any future corpus job verifies the recorded sha256 after a cache restore (decision above).
  - Every task Verify command runs Python through `uv run --frozen` (INTENT constraint).

## User rulings

- 2026-10-26, corpus exposure: **runner-only** — owner reply verbatim: «1: runner-only». The corpus never lands on any GitHub surface; any future strict corpus job runs only on a restricted self-hosted surface (protected branches only, ephemeral secret-free runner, explicit runner label — never `ubuntu-latest`); hosted delivery channels (release asset, public/private package, LFS) are ruled out unless the owner revisits this ruling.
- 2026-10-26, M208/D512 admission-contract scheduling: **reaffirmed pending** — standing round-1 ruling (INTENT round-1 item 7), uncontested in this round.
- 2026-10-26, frozen-token ADR amendment (D466/D487) vs witness relocation: **reaffirmed pending** — standing round-1 ruling, uncontested in this round.
- 2026-10-26, product direction after M001: **decide after M001 ships** — standing round-1 ruling, uncontested in this round.

## Still unknown

- Resolved 2026-10-26 — corpus exposure on the public repo `rager306/law-nexus`: owner ruled **runner-only** (see `## User rulings`); the corpus job stays skipped in M001 and the future target is a restricted self-hosted surface.
- Resolved 2026-10-26 — M208/D512 admission-contract scheduling: owner reaffirmed **pending**; carried out of M001.
- Resolved 2026-10-26 — frozen-token ADR amendment (D466/D487) vs witness relocation: owner reaffirmed **pending**; carried out of M001.
- Resolved 2026-10-26 — product direction after M001 (full-corpus ingestion vs live retrieval stack): owner ruled **decide after M001 ships**.
- Accept risk — Actions pricing moved twice in late 2025/2026 (a self-hosted per-minute charge for private repos was announced for 2026-03-01, then postponed); re-check pricing before building any cost claim into a future corpus decision (evidence-stack.md, finding "hosted-minutes cost is neutral in both directions; a self-hosted per-minute charge was announced for private repos only and postponed").
