# Analyzer, Grader, and Comparator Rubrics

Use these rubrics when reviewing benchmark output. They adapt Anthropic's analyzer/comparator/grader roles to PI without requiring separate agent files.

## Grader rubric

For each expectation:

- Mark `passed=true` only when the output itself contains evidence.
- Record concrete evidence: file path, excerpt, command result, or absence.
- Prefer programmatic checks for exact/file/schema assertions.
- Mark missing outputs as failure, not unknown.

## Analyzer rubric

After aggregation, inspect:

- Expectations that pass for both with-skill and baseline; they may be non-discriminating.
- Expectations that fail in both; eval may be too hard or missing input context.
- With-skill regressions; skill may add wrong procedure or context bloat.
- Token/time cost if available.
- Flaky evals across iterations.
- Failures caused by bad eval wording rather than bad skill behavior.

## Comparator rubric

When comparing old vs new skill:

- Prefer the version with higher pass rate only if failures are comparable severity.
- Do not accept a version that improves easy expectations but regresses safety/guardrail expectations.
- Favor lower context and fewer steps when pass rates are equal.
- Keep current best unchanged on tie unless the new version is simpler and no safety regression exists.

## Improvement rule

Change the skill only for reusable failures. If an eval exposes a one-off issue, improve the eval or add a reference instead of bloating `SKILL.md`.
