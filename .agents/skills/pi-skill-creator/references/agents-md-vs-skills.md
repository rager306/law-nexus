# AGENTS.md vs Skills Decision Guide

Vercel's evals showed that broad framework knowledge can perform better as a compressed `AGENTS.md` index than as an on-demand skill, because passive context removes trigger and ordering failure modes.

## Use AGENTS.md when

- The knowledge should influence nearly every task in a project.
- The agent often forgets to invoke the skill.
- The content is a compact index pointing to retrievable files.
- The goal is retrieval-led reasoning over stale model memory.

## Use a skill when

- The work is a vertical action-specific workflow.
- The user intent is recognizable from a description.
- The workflow needs procedures, templates, scripts, or evals.
- The content would bloat every prompt if always loaded.

## Use both when

- A compact index or hard guardrail must always be visible.
- Detailed procedures should load on demand.

Pattern:

```text
AGENTS.md: compressed index + "prefer retrieval-led reasoning"
Skill SKILL.md: compact router + essential guardrails
Skill references/workflows: deep procedures
```

## PI skill-creator rule

When creating a skill, explicitly decide whether any part belongs in `AGENTS.md` instead. Do not force broad framework documentation into a skill just because skills exist.
