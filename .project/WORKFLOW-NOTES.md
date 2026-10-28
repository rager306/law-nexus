# Ship-time projection refresh

The roadmap projection in `prd/project-state/` must name the milestone being
shipped. Refresh it in a `docs:` commit immediately before the
`.project`-only ship commit:

1. Set `prd/project-state/data/roadmap.json` `current_milestone` to the
   milestone recorded in `.project/STATE.md`, with `status: "active"`.
2. Rewrite the live `- **Local GSD workflow marker:**` bullet in
   `prd/project-state/roadmap.md` so its slug matches, and fold the previous
   shipment into a dated superseded record.
3. Commit with a `docs:` subject, then create the ship commit.

Why: the ship commit may only change `.project/`, so a refresh made during
build lands one milestone behind. The pointer suites
(`tests/test_post_ship_pointers.py`, `tests/test_project_state_roadmap_freshness.py`)
run in CI and fail on the shipped tree when this is skipped.
