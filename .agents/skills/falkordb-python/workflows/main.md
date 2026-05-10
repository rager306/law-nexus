# Workflow: Use falkordb-py Safely

<required_reading>
Read now:
1. `references/main.md`
2. `.agents/skills/falkordb-capability-evidence/SKILL.md` when support certainty matters
</required_reading>

<process>
## Step 1 — Scope the task
Identify FalkorDB version, runtime mode, graph name/data shape, and whether the task is design, implementation, verification, or debugging.

## Step 2 — Classify evidence needs
Mark relevant claims as runtime-confirmed, source-backed, docs-backed, smoke-needed, blocked-environment, neo4j-only, redisgraph-legacy, or unknown.

## Step 3 — Produce the focused answer
Use the reference guidance for this skill. Keep examples small, parameterized, and runnable where possible.

## Step 4 — Verify
Provide a command, query, fixture, or review checklist that proves the answer. If verification cannot be run, state the blocker and next proof.
</process>

<success_criteria>
- [ ] The answer is scoped to FalkorDB, not Neo4j by copy.
- [ ] Important claims have evidence classes.
- [ ] The implementation or design includes verification steps.
- [ ] Any unsupported or unknown behavior is routed to capability evidence instead of guessed.
</success_criteria>
