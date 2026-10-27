## Session context

- Bound branch: `gsd-path/M001`
- Milestone: `001-native-workflow-acceptance`
- Handoff commit SHA: `7791ca6c125005a2d03c1a46b8ffdb8eb9814028`

## State on disk

`.project/STATE.md` is the single journaled source of workflow state.
Nothing is carried in conversation history; everything needed to resume is
in the repository on disk. Resume read-only from this file and the repository.

## Resume verification commands

Run in order from the repository root:

```bash
python3 scripts/ai/path-run.py status
uv run --frozen python -m law_nexus_harness.governor
uv run --frozen pytest tests/test_project_state_roadmap_freshness.py -q
test -z "$(git ls-files a.txt b.txt c.txt)"
```

## Recording path

Record the resume proof at `.project/M001-RESUME-PROOF.md`.
