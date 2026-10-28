# Intent — law-nexus

<!-- Written by $gsd-path-define (quick mode, supplied-spec: the owner-approved
     M004 scope = post-ship pointer refresh + external-review items 3-5). -->

Lane: quick   <!-- two deliverable-sized tasks, one wave, no RESEARCH/NEEDS-USER. -->

Review panel: off

Finding skeptics: off

Surfaces: terminal (native Path CLI: path-run.py status, governor, pytest, git), GitHub Actions (repository-quality migration job on main)

## Summary

M003 shipped and integrated cleanly, but the post-ship pointers trail: `roadmap.json`
`current_milestone` still names `post-ship-hardening` while STATE.md says `ci-honesty`
shipped/done; the DOCS-AUDIT queue rows for PDD/GitNexus still say `planned: no` despite
T005/T006 completing them; the crosswalk M225 row still says `pending-fill`; the cutover
readiness snapshot predates M003. M004 refreshes all live pointers to the current state
and writes a dated post-ship report so the next agent session starts without stale data.

## Problem

Every post-ship pointer a fresh agent reads describes an earlier world. The roadmap
marker names the wrong milestone; the audit queue offers already-done work; the crosswalk
says M225 is pending when it's closed; the cutover snapshot predates M002/M003.

## Users

The owner and AI agents reading the repo's live pointer documents.

## Success criteria

1. SC1 — `prd/project-state/roadmap.md` live marker names `ci-honesty` on gsd-path/M004
   (shipped); `roadmap.json` `current_milestone` matches; the three-way identity test
   passes.
2. SC2 — The DOCS-AUDIT queue rows closed by M001–M003 tasks reference their task ids
   (`planned` column); no stale `planned: no` rows for completed work; the crosswalk M225
   row links the rerun receipt.
3. SC3 — A dated post-ship report (`POST-SHIP-STATE-2026-10-28.md`) supersedes
   POST-SHIP-STATE-2026-10-27.md as the current-state document; AGENTS.md and
   AGENT_HANDOFF.md point at it.

## Edge coverage

| Edge | Criterion | Category | Disposition | Detail |
|------|-----------|----------|-------------|--------|
| E1 | SC1 | adjacency | criterion SC1 | The three-way identity is exact: STATE.md milestone ↔ roadmap.json ↔ live marker. |
| E2 | SC2 | empty | held-out | A grep test pins that no `planned: no` rows exist for T005/T006/T001–T011 ids. |
| E3 | SC3 | adjacency | criterion SC3 | The new report supersedes the old; the old file remains as a dated snapshot (N4 discipline). |

## Prohibitions

| Prohibition | Criterion | Must not | Disposition | Detail |
|-------------|-----------|----------|-------------|--------|
| N1 | SC1 | rewrite archived M001-M003 history while updating live pointers | criterion SC1 | Archived files untouched; only live documents change. |
| N2 | SC2 | reference task ids that don't exist in this milestone | criterion SC2 | Only ids from M001-M003 landings are used. |
| N3 | SC3 | claim the new report supersedes something it doesn't | criterion SC3 | The supersession statement names the exact file it replaces. |
| N4 | SC3 | mask a non-zero exit | criterion SC3 | No suppression anywhere. |
| N5 | SC3 | introduce milestone literals to make an assertion pass | criterion SC3 | No milestone literals in any test expectation. |
## Scope: in

- Roadmap marker refresh to `ci-honesty` shipped state.
- DOCS-AUDIT queue rows: reference task ids for completed work; remove stale entries.
- Crosswalk M225 row: link rerun receipt and mark the residual closed.
- Dated post-ship report: POST-SHIP-STATE-2026-10-28.md superseding POST-SHIP-STATE-2026-10-27.md.
- AGENTS.md and AGENT_HANDOFF.md pointing at the new report.

## Scope: out (vetoes)

- Strict corpus run, PDD wrapper bootstrap, Allspark identity pilot — M004+ deferral
  standing.
- Product feature work; cutover stays `false`.
- Any suppression masking a non-zero exit (standing N3).
- `git stash` in this repository (standing owner rule).

## Constraints

- Bound branch `gsd-path/M004` at base 7e200294; integration `direct`.
- Python through `uv run --frozen`; Conventional Commits, English subjects.

## Risks

- Minimal — this is a pointer refresh with no product changes.

## Open questions

- none.

## Corrections

- 2026-10-27: «продолжай» — owner approved the M004 scope (post-ship pointer refresh).
