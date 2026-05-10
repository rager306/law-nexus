# Session Learning and Skill Maintenance

## Principle
Skills should improve from real development practice, but only through reviewed evidence. End-of-session analysis should surface candidates; it should not silently mutate skill files.

## Recommended loop
1. Inspect recent GSD execution evidence and git changes.
2. Identify repeated friction, failed commands, missing evals, and stale skill guidance.
3. Decide whether the lesson belongs in:
   - skill workflow/reference/eval;
   - agentmemory;
   - neither.
4. If a skill changes, add or update an eval that would catch the same issue.
5. Run the relevant verifier.

## Local helper
From the repository root:

```bash
uv run python scripts/analyze-session-learning.py --exec-limit 30
```

Outputs:

- `.gsd/session-learning-report.json`
- `.gsd/session-learning-report.md`

Optional reviewed memory save:

```bash
uv run python scripts/analyze-session-learning.py --save-memory
```

Use `--save-memory` only after confirming the generated candidates contain no secrets and describe durable reusable lessons.

## Agentmemory use
Agentmemory is best for cross-session project knowledge:

- recurring gotchas;
- environment facts;
- decisions not worth putting into a reusable skill;
- workflow constraints that future agents must remember.

Do not save secrets, raw logs, or one-off command failures.

## Skill update rule
A skill edit is justified when at least one of these is true:

- a failure repeats;
- an eval gap is exposed;
- a capability boundary was misunderstood;
- a verification command became canonical;
- user preference changed the expected workflow.

Every skill edit should be paired with verification. If the skill has evals, update them when the lesson is behaviorally testable.
