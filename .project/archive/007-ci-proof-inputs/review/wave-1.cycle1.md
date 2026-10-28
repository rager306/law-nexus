# Review — wave 1, cycle 1

<!-- Reviewer role, wave mode (full). Sidecar HEAD requested by the brief:
     3b2e1e4c49a7e08ab24c82f41adebdd2bbd8efac. The supplied sidecar worktree is
     checked out at 3fffeaba43862969a5f9867f09653bf717f0bd05 (branch
     gsd-path-verify/wave-1-cycle-1, gitdir
     /root/law-nexus/.git/worktrees/wave-1-cycle-1), which is T001's landing
     plus T002's later landing on the same two files. T001 evidence therefore
     comes from the recorded base ae5ed705145942f4af869f1a9950d369d9f9d5a0 plus
     only the T001 patch, reconstructed outside the sidecar, so the T002 change
     to the same files cannot be read as T001's product.

     METHOD. Diff inspected: `git diff ae5ed705..3b2e1e4c` = 3 files (workflow,
     T001 task file, pin test). Recorded orchestrator Verify reused as-is,
     never re-run: T001 Log — sidecar gsd-path-verify/task-t001-verify, exit 0,
     `2 passed, 14 deselected in 1.48s` (and again `1.53s`).

     Independent re-runs of my own, only where the recorded output plus the
     isolated diff could not check the criterion (E1, E3/N3, SC1, SC3):
       1. Isolated T001 product (git archive of the base plus the T001 patch
          only, applied with `patch -p1`): `uv run --frozen pytest
          tests/test_ci_runtime_restore.py -q` = 16 passed; `-k 'checkout or
          rust'` = 2 passed, 14 deselected, matching the recorded Verify.
       2. Clean-room origin (bare repo holding only refs/heads/main at
          3e047fe8 and the six annotated refs/tags/milestone/*), cloned five
          ways, each fed to the pinned helper and to the harness adapter:
            full history + tags + origin/HEAD -> completion verified,
              adapter kind=shipped-integrated
            depth-1 --no-tags -> unverified ("task landing proof failed: does
              not resolve to a commit"), adapter kind=conflicting-ownership
            full history, --no-tags -> unverified ("missing milestone tag:
              milestone/006-red-ci-clear")
            full history + tags, origin/HEAD unset -> unverified ("origin/HEAD
              is unresolved; fetch before validating integration")
            depth-1 with tags fetched -> still unverified (the landing commit
              is not in a shallow history)
       3. The real governor and the landed honesty-step body run against those
          clones: full -> governor exit 0, pass_count 72, surface
          workflow-state-surface.shipped, body exit 0; shallow -> governor
          exit 1, surface workflow-state-surface.blocking fail, body exit 1.
       4. Live suites on the same clones: full 267 passed / 2 skipped; shallow
          16 failed / 251 passed / 2 skipped with `assert 'fail' == 'pass'` at
          tests/test_harness_governor.py:175.
       5. Five mutations of the landed workflow, each re-running the pin test:
          fetch-depth dropped / fetch-depth: 1 / fetch-tags dropped /
          fetch-tags: false / git symbolic-ref line dropped — every one fails
          the new test. The same test file against the base workflow fails with
          `KeyError: 'with'`, so the pin is load-bearing. -->

Wave verdict: pass
Cycle: 1
Depth: full
Tasks reviewed: 1

## T001 — Give the rust job the full history and tags the integration proof needs: pass

- ✅ The rust job checks out the full history and tags, so the integration proof resolves and the governor reports shipped-integrated (E1). — `.github/workflows/repository-quality.yml:77-83` adds `fetch-depth: 0` and `fetch-tags: true` to the `rust-harness-quality` checkout, and `:122-127` adds the `Prepare shipped-main integration proof inputs` step that writes `refs/remotes/origin/HEAD` to `refs/remotes/origin/main`. Reproduced end to end on a clean-room clone of a bare origin holding only `refs/heads/main` and the six `refs/tags/milestone/*` refs: `python3 -B .gsd-path/status_runtime.py --repo <clone>` reports `completion.status=verified` with proof `tag=milestone/006-red-ci-clear, landing=3e047fe8`; the harness adapter returns `kind=shipped-integrated`; `python -m law_nexus_harness.governor` exits 0 with `pass_count 72` and finding `workflow-state-surface` status `pass`, rule `workflow-state-surface.shipped`; the migration job's landed honesty body exits 0 under `GITHUB_REF=refs/heads/main`. The rust job's own live surface test passes on that clone (267 passed, 2 skipped) and on the isolated T001 product (283 passed, 2 skipped including the pin file). Held-out boundary E1 reproduced as a fail, never a silent pass: a depth-1 `--no-tags` clone of the same origin yields `completion.status=unverified` (`task landing proof failed: does not resolve to a commit`), adapter `kind=conflicting-ownership`, governor exit 1 with `workflow-state-surface` status `fail` rule `workflow-state-surface.blocking`, the live suite failing at `tests/test_harness_governor.py:175` with `assert 'fail' == 'pass'` (16 failed, 251 passed), and the landed honesty body exiting 1. Three further shapes fail the same way: full history without tags (`missing milestone tag: milestone/006-red-ci-clear`), full history with tags but `origin/HEAD` unset (`origin/HEAD is unresolved`), and depth-1 with the tags fetched (the landing commit is absent from a shallow history), so each input the commit supplies is individually necessary.
- ✅ The suite pins both checkout inputs and fails if either is dropped (N3). — `tests/test_ci_runtime_restore.py:273-290` adds `test_rust_checkout_supplies_the_same_integration_proof_inputs`, asserting `checkout["with"]["fetch-depth"] == 0`, `checkout["with"]["fetch-tags"] is True`, and the `git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main` line inside the named proof step. Five mutations of the landed workflow each fail that test: dropping `fetch-depth` (`KeyError: 'fetch-depth'`), `fetch-depth: 1` (`assert 1 == 0`), dropping `fetch-tags` (`KeyError: 'fetch-tags'`), `fetch-tags: false` (`assert False is True`), and removing the `git symbolic-ref` line (the step's run text no longer carries it). The pin is load-bearing, not vacuous: the same test file against the base workflow fails with `KeyError: 'with'`. The pre-existing migration-job pins still fail when mutated too (dropping its `fetch-depth` gives a `TypeError`, removing its proof step gives `assert 0 == 1`), so no input in the file was loosened.
- ✅ Prohibition N1 — no test weakened or skipped: `git diff ae5ed705..3b2e1e4c -- tests/test_ci_runtime_restore.py` removes zero lines (filtering `^-` outside the `---` header returns nothing), so the 18 added lines are pure addition; the isolated product runs the whole file green (16 passed) and the new test fails only when a real input is removed.

Warnings (non-blocking):
- The E1 boundary is proven by clean-room reproduction, not pinned by an automated test: nothing in the repository builds a shallow or tagless clone, so a future change that made the adapter tolerant of an unresolvable landing would be caught only by the live surface suite. Acceptable here because E1's disposition is `criterion SC1` (judged, not `held-out`), and the live suite does fail on every shallow shape I built.
- `checkout["with"]["fetch-depth"]` raises `KeyError` instead of an assertion when the `with:` block is absent entirely (observed against the base workflow). It still fails, only with a less readable message.

Contract violations (blocking):
- none — the commit touches `.github/workflows/repository-quality.yml` and `tests/test_ci_runtime_restore.py` (both in the task `files` list) plus its own task file, where only the orchestrator-owned `status`/`agent`/`base` fields and append-only `## Log` entries changed; the Context, Approach, Interface contract, Intent coverage, Acceptance criteria and Verify bodies are byte-identical.

## Intent coverage

### SC1 — SC1 — The rust workspace job checks out the full history and tags, so the pinned native status helper can prove the shipped integration on main and the governor reports the shipped-integrated surface.: pass
- ✅ `.github/workflows/repository-quality.yml:77-83` (`fetch-depth: 0`, `fetch-tags: true`) and `:122-127` (the `refs/remotes/origin/HEAD` symref) are exactly the two facts the pinned helper needs, proven on a clean-room full clone: `completion.status=verified`, adapter `kind=shipped-integrated`, governor exit 0 with `pass_count 72` and `workflow-state-surface` status `pass` rule `workflow-state-surface.shipped`, honesty body exit 0 under `GITHUB_REF=refs/heads/main`. Held-out boundary E1 — "A shallow checkout that cannot see the milestone tag must fail the governor step, not pass silently." — held on all four non-qualifying shapes: depth-1 `--no-tags` (unverified, adapter `conflicting-ownership`, governor exit 1, surface `fail`/`workflow-state-surface.blocking`, live suite `assert 'fail' == 'pass'`, honesty body exit 1), full history without tags, full history with tags and no `origin/HEAD`, and depth-1 with tags fetched. No shallow shape passed silently.

### SC3 — SC3 — `uv run --frozen pytest tests/test_ci_runtime_restore.py -q` passes and pins both job shapes.: pass
- ✅ On the isolated T001 product (base `ae5ed705` plus only the T001 patch): `uv run --frozen pytest tests/test_ci_runtime_restore.py -q` = `16 passed`, exit 0. Both job shapes are pinned and both pins bite: the rust shape (`tests/test_ci_runtime_restore.py:273-290`) fails under all five mutations above, and the migration shape (`:258-271`, pre-existing) fails when its `fetch-depth` or its proof step is removed. Held-out boundary E3 — "A pin that drops either checkout input fails the suite rather than passing quietly." — held for all four inputs across the two jobs.

## Summary for orchestrator

- blocked findings: none
- repeat offenders: none (cycle 1)
- warnings worth a human eye: the shallow-checkout boundary E1 is reproduced by hand rather than pinned by an automated test that builds a shallow clone; a future adapter tolerant of an unresolvable landing would surface only through the live surface suite.
