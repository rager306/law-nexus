# Intent — law-nexus

<!-- Written by $gsd-path-define (standard mode, supplied-spec) for milestone M002.
     Supplied spec: the owner-circulated post-ship external review, 2026-10-27
     (verbatim in the define conversation; key claims verified locally — CI run
     40446077586 failure, BOUND_BRANCH regression, stale pointers). -->

Lane: standard   <!-- multiple files across CI/tests/docs, cross-wave risk, no
                      quick-lane fit. -->

Review panel: off   <!-- configured runtime preference (built-in default). -->

Finding skeptics: off   <!-- default. -->

Surfaces: terminal (native Path CLI: path-run.py status, governor, pytest, git), GitHub Actions (repository-quality run on main: job result, governor diagnostics)

## Summary

After shipping M001 the integrated `main` is red: the migration CI job runs the
real governor, which fails closed with `runtime-unavailable` because the pinned
GSD Path runtime (1.6.2@6f95a31e) is machine-local and CI never restores it; the
governor/preflight test suites are pinned to `gsd-path/M001` (owner ruling (a)
during M001) and their `startswith("kind=")` expectation is satisfied even by
the missing-runtime failure; and the post-ship pointers (roadmap phase, audit
queue, crosswalk M225 row, cutover snapshot) still describe the pre-ship world.
M002 makes the integrated main honestly green — CI restores the exact pinned
runtime from the vendored archive with digest verification and the governor
reports the shipped/done state on main — the test suites become
context-independent (five documented scenarios, fail-closed contract pinned
where the governor cannot be operational, full assertions everywhere it can),
the failure diagnostics are published without masking the non-zero exit, and
the post-ship pointers are updated. Acceptance is a fresh-session walkthrough
that restores the pinned tools, recognizes the shipped M001, and starts the
next milestone flow.

## Problem

The owner's goal is "hand the repository to an agent and continue": after M001
the next agent hits a red CI whose only visible signal is a non-zero exit with
the diagnostics hidden in an unparsed file, test suites that assert the wrong
thing on every branch except one, and docs that would make it re-plan already
finished work. Each blocker was verified locally on 2026-10-27 (CI run
40446077586; probe worktrees; tracked file greps).

## Users

The owner and the AI agents operating the repository's delivery through native
Path. They read the GitHub Actions run page, run the terminal CLI, and expect a
fresh session to bootstrap from disk alone.

## Success criteria

1. SC1 — On a fresh checkout of integrated `main` the `repository-quality`
   migration job restores the pinned GSD Path runtime (version and sha256
   digest recorded in `.gsd-path/runtime.json`, installed from the vendored
   archive in the repository) before any operational check, and the real
   governor run on integrated `main` exits 0 reporting `shipped/done` with the
   archive path; a digest mismatch or missing archive fails loudly.
2. SC2 — The governor and preflight test suites are context-independent: five
   scenario groups (active milestone on its bound branch, foreign branch,
   detached checkout, verify sidecar, shipped integrated main) each pin their
   documented contract; on `gsd-path/M001`-class branches the fail-closed
   branch-ownership contract itself is pinned (per owner ruling (a), M001);
   substantive product assertions run in every context where the governor is
   operational; nothing is skipped or suppressed without a loud recorded
   reason.
3. SC3 — When the governor fails in CI its diagnostic JSON is published as a
   workflow artifact and printed to the job log, and the job exit stays
   non-zero (no suppression; N3).
4. SC4 — Post-ship pointers are truthful at the shipped state: `roadmap.md`
   records M001 shipped/archived and the M002 continuation; the DOCS-AUDIT
   queue rows closed by T005/T006 reference their task ids; the crosswalk M225
   row links the T004 rerun receipt (`hermetic-pass-parity-unproven`, corpus
   parity explicitly unproven); a dated post-ship report supersedes the
   pre-ship cutover snapshot as the current-state document (the pre-ship file
   remains as a dated snapshot).
5. SC5 — A fresh session, given only the repository and a minimal pointer,
   executes the M002 acceptance walkthrough: restores the pinned runtime per
   the documented bootstrap, runs the status/governor/freshness commands
   recognizing the shipped M001 and the M002 continuation, and records the
   proof on disk (same recording discipline as M001's resume proof, N8).

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | encoding | held-out | The runtime installer verifies the extracted store against the sha256 digest recorded in `.gsd-path/runtime.json`; a mismatch aborts the job with the recorded digest pair. |
| E2 | SC1 | empty | criterion SC1 | A fresh checkout has no runtime store: the restore step must create it from the vendored archive; an existing valid store is reused untouched (idempotent). |
| E3 | SC2 | adjacency | criterion SC2 | The five scenario groups are pinned as separate test scenarios; a foreign bound branch (`gsd-path/M002` while M001 rules) and a shipped main are distinct expectations, never collapsed into one `startswith("kind=")`. |
| E4 | SC2 | idempotency | held-out | The context detection (live branch of the checkout) is a single shared predicate in the test modules; every scenario asserts through it — one predicate, no per-test divergent logic. |
| E5 | SC3 | boundary | criterion SC3 | Diagnostics are published only when the governor fails; a passing run publishes nothing extra and the job stays green. |
| E6 | SC4 | adjacency | held-out | Crosswalk M225 row: the residual closed by T004 (rerun receipt `hermetic-pass-parity-unproven`) is linked, and the row records that corpus parity remains unproven — the row is updated, never deleted. |
| E7 | SC5 | empty | criterion SC5 | The walkthrough assumes only the repository on disk and a minimal pointer; if the pinned bootstrap is missing or ambiguous the walkthrough records the failure on disk instead of improvising (same discipline as M001's resume proof). |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | install or resolve a GSD Path runtime whose version/digest does not match `.gsd-path/runtime.json` | criterion SC1 | The restore step is pinned-only; a silent fallback to any unpinned source fails the job. |
| N2 | SC2 | weaken or remove the fail-closed branch-ownership pinning introduced in M001 (owner ruling (a)) | criterion SC2 | The ruling (a) semantics are preserved and extended by the scenario matrix; nothing is skipped silently (N3). |
| N3 | SC3 | add any suppression that masks a non-zero exit or a diagnostic | criterion SC3 | CI exit stays non-zero on failure; SC2's skip discipline carries loud recorded reasons only. |
| N4 | SC4 | rewrite archived M001 history or dated snapshots while updating pointers | criterion SC4 | Pointer updates change only live documents; `docs/agent-stack/CUTOVER-READINESS-M001.md` remains as the dated pre-ship snapshot; archived files untouched. |
| N5 | SC5 | count chat-history re-reading as resume proof | criterion SC5 | SC5 proof is recorded on disk by the fresh session (N8 discipline carried from M001). |

## Scope: in

- CI runtime restore step (vendored archive + digest verification) before the
  migration job's operational checks; shipped-main governor contract; failure
  diagnostics artifact.
- Context-independent governor/preflight tests with the five-scenario matrix.
- Post-ship pointer updates: roadmap phase/status, DOCS-AUDIT queue rows for
  the closed items, crosswalk M225 link, dated post-ship report.
- Fresh-session acceptance walkthrough with on-disk proof.

## Scope: out (vetoes)

- Strict corpus run and corpus runner provisioning — M003 (owner ruling, M002
  define round 1 item 1).
- PDD wrapper reproducibility bootstrap and Allspark identity pilot — M003
  (same ruling).
- Product feature work; cutover stays `false` (C7 is a later owner decision).
- Any suppression masking a non-zero exit or diagnostic (standing, N3).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M002` at base 4e0cd4db; integration `direct`; ship is
  the only path into `main`.
- The pinned runtime is machine-local by design; the vendored
  `gsd-path-1.6.2` archive in the repository is the reproduction source; the
  digest lives in `.gsd-path/runtime.json`.
- CI workflow triggers: repository-quality runs on main-push/PR (documented).
- Python through `uv run --frozen`; Rust `--offline`; Conventional Commits,
  English subjects; tracked prose English.
- The governor's fail-closed branch ownership away from the bound branch is
  expected behavior (documented), not a defect.

## Risks

- The vendored archive may drift from the digest recorded in
  `.gsd-path/runtime.json` if the runtime upgrades mid-milestone — the digest
  check fails loudly by design; the upgrade then becomes an explicit task.
- Context-independent tests grow more complex; the shared single-predicate
  helper (E4) keeps the matrix reviewable.
- CI timing: the restored-runtime step adds minutes to the migration job.

## Open questions

- [RESEARCH] none — the supplied spec and M001 evidence settle the direction.
- [NEEDS-USER] none at define time; the M003 split (PDD wrapper + Allspark
  identity pilot, strict corpus) is recorded and re-offered at M003 define.

## Corrections

- 2026-10-27: «продолжай» after the four ruling items — owner accepted the
  proposed scope split (items 1–3 + fresh-agent acceptance in M002; PDD
  wrapper/Allspark pilot and strict corpus deferred to M003), the vendored-tgz
  digest-verified runtime restore, the shipped-main governor contract, and the
  failure-diagnostics artifact.
