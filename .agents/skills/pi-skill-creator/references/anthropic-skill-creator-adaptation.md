# Adapting Anthropic `skill-creator` to PI/GSD

## What to keep

Anthropic's skill-creator contributes a strong quality loop:

1. Capture intent and trigger conditions.
2. Draft the skill.
3. Create realistic test prompts.
4. Run with-skill and baseline/old-skill comparisons.
5. Grade expectations with evidence.
6. Aggregate pass rates, timing, tokens, and qualitative feedback.
7. Rewrite the skill from observed failures.
8. Improve trigger description without overfitting.

Keep this loop.

## What to change for PI/GSD

Anthropic's implementation assumes Claude Code-specific mechanics such as `.claude/commands`, `claude -p`, stream-json events, and bundled eval viewer scripts. PI/GSD has different mechanics:

- Skills live in `.agents/skills/` or `~/.agents/skills/`.
- Skills use PI/GSD discovery and `/reload`.
- Subagents are available through the PI harness, not through `claude -p` shelling by default.
- GSD artifacts and verifiers should be repo-local and auditable.
- Use `gsd_exec` for noisy validation commands.

## Adapted PI strategy

- Structural validation: local Python script checks PI/GSD frontmatter, directory shape, references, and eval schema.
- Eval prompts: store in `evals/evals.json` using a simplified Anthropic-compatible schema.
- Runtime evaluation: use `run_pi_skill_eval.py` to prepare with-skill/baseline workspaces, execute generated prompts through PI/GSD headless sessions with `execute_pi_skill_eval.py --backend gsd-print` or through manual/subagent runs, then use `grade_pi_skill_eval.py` and `aggregate_pi_skill_benchmark.py` to produce local benchmark artifacts. If model execution is unavailable, mark dry rubric review explicitly.
- Trigger proxy: use `analyze_skill_triggers.py` for deterministic static description/eval alignment checks. Treat its `trigger_proxy_score` as a proxy only; it is not proof of actual PI/GSD skill activation.
- Description tuning: use missed-trigger/false-trigger categories from evals; keep description under PI/GSD's 1024 char limit.
- Viewer: optional future work. Do not require browser UI to validate the skill.

## What not to copy blindly

- `claude -p` subprocess runner.
- `.claude/commands` injection.
- Browser eval viewer as a required step.
- Anthropic-specific tone or format if it conflicts with PI/GSD XML/router guidance.
