# Synthesis

<!-- Written by the research/decide recovery path for milestone M002
     (post-ship-hardening). The define round ran with the owner in session:
     research and decide were settled directly by the owner's four rulings
     (recorded verbatim in INTENT.md ## Corrections) rather than by dispatched
     researchers — the only open question the external review raised was
     answered by the pinned-runtime restore decision (ruling 2), and the
     shipped-main contract by ruling 3. This file records the settled
     decisions for the planner and the archive. -->

Phase: research
Status: complete
Intent: `.project/intent/INTENT.md`

## Decisions

### Pinned runtime restore for CI

- **Decision**: The migration job restores the pinned GSD Path runtime from the
  vendored archive (`.ai/vendor/gsd-path-1.6.2.tgz`) with sha256 digest
  verification against `.gsd-path/runtime.json` before any operational check.
- **Runner-up**: Downloading a published fork release — lost because the
  Allspark fork release pipeline was red at decision time; the vendored archive
  is in-repo and offline-reproducible.
- **Evidence**: INTENT.md SC1 and N1; verified locally: the vendored archive
  content reproduces the pinned store (owner ruling 2, define round M002).
- **Confidence**: high

### Shipped-integrated main is an honest non-failing workflow state

- **Decision**: The governor on integrated `main` (STATE shipped/done with
  archive) classifies as `shipped-integrated` and exits 0 — the fifth scenario
  in the branch-context matrix, not a fail-closed case.
- **Runner-up**: Treating shipped main as non-operational — lost: it would
  contradict the owner's item 3 ("корректно распознаёт завершённый M001").
- **Evidence**: INTENT.md SC1/SC2; M002 T002 landing 50ff97b6 (WorkflowStateKind.
  SHIPPED_INTEGRATED + narrow verified shipped/done predicate, fail-closed on
  absent/mistyped completion and archive fields).
- **Confidence**: high

### Branch-context matrix replaces the single-branch pin

- **Decision**: The governor/preflight live suites classify through the shared
  single-predicate `tests/branch_context.py` into five documented scenarios;
  full assertions run only where the governor is operational; non-operational
  contexts pin the fail-closed contract itself.
- **Runner-up**: Keeping the single BOUND_BRANCH literal — lost: it satisfied
  missing-runtime failures (the M001 startswith defect) and would break on
  M002/M003 branches.
- **Evidence**: INTENT.md SC2, E3/E4; PATCH-FINDINGS P001; M001 T011 (069c2ba8).
- **Confidence**: high

### Post-ship pointers and dated supersession

- **Decision**: Roadmap marker moves to the M002 continuation; DOCS-AUDIT queue
  rows closed by M001 tasks reference their task ids; the crosswalk M225 row
  links the rerun receipt and keeps the corpus-parity-unproven disclaimer; a
  dated POST-SHIP-STATE report supersedes the pre-ship cutover snapshot (which
  remains untouched).
- **Runner-up**: Editing the pre-ship snapshot in place — lost: N4 forbids
  rewriting dated snapshots.
- **Evidence**: INTENT.md SC4, E6, N4; M002 T004 landing c0694593.
- **Confidence**: high

## For the planner

- **Wave-1 blockers**: the CI runtime restore step must land before the
  shipped-main governor scenario is meaningful (the governor cannot resolve the
  runtime on CI without it); the branch-context predicate must land before the
  routed live tests (they depend on its classification).
- **Walking skeleton**: T002's shipped-integrated classification + fixture test
  is the thinnest proof that the matrix works; T001's digest pin is the
  thinnest proof that the restore is honest.
- **Pitfall-to-task**: the M001 startswith("kind=") defect maps to T003's
  no-startswith assertion; the corpus-absent skip-visible pattern maps to the
  loud recorded-reason requirement for any skip.

## User rulings

- 2026-10-27 — «продолжай» on the four ruling items (scope split, vendored-tgz
  digest-verified restore, shipped-main contract, failure diagnostics) — all
  recommended options accepted; recorded verbatim in INTENT.md ## Corrections.

## Still unknown

- [NEEDS-USER, M003] PDD wrapper reproducibility bootstrap + Allspark identity
  pilot; strict corpus run (deferred by owner ruling 1, M002 define round).
