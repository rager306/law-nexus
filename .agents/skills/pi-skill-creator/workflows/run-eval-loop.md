# Workflow: Run an Eval/Iteration Loop

<required_reading>
Read now:
1. `references/eval-method.md`
2. `references/anthropic-skill-creator-adaptation.md`
3. `references/analyzer-grader-comparator.md`
</required_reading>

<process>
## Step 1 — Snapshot baseline
If improving an existing skill, copy it to a workspace snapshot before editing. If creating a new skill, baseline is "no skill" or the agent's current behavior.

## Step 2 — Run structural checks first
Do not spend model time on eval runs while the skill is structurally invalid.

```bash
python .agents/skills/pi-skill-creator/scripts/validate_pi_skill.py <skill-dir> --require-evals
```

## Step 3 — Prepare the eval workspace
Run the PI eval runner. It does not fake outputs; it creates the with-skill/baseline directories, snapshots the skill, and writes executor prompts.

```bash
python .agents/skills/pi-skill-creator/scripts/run_pi_skill_eval.py <skill-dir>
```

This creates:

```text
<skill-name>-workspace/iteration-N/eval-<id>-<slug>/with_skill/EXECUTOR_PROMPT.md
<skill-name>-workspace/iteration-N/eval-<id>-<slug>/baseline/EXECUTOR_PROMPT.md
```

## Step 4 — Execute runs
Preferred PI mode: use `execute_pi_skill_eval.py` with the `gsd-print` backend to run generated prompts through real PI/GSD headless sessions and save stdout/stderr/exit-code evidence.

```bash
python .agents/skills/pi-skill-creator/scripts/execute_pi_skill_eval.py <skill-name>-workspace/iteration-N --backend gsd-print
```

For tests or custom runners, use `--backend command --command "..."`; the prompt is appended as the final argv item unless the command contains `{prompt}`.

If full execution is not available, perform a dry rubric review and mark it as `dry_review`, not as benchmark proof. Manual/subagent execution is still valid if each final answer or artifact summary is saved to `outputs/answer.md`.

## Step 5 — Grade expectations
Run deterministic grading after outputs exist:

```bash
python .agents/skills/pi-skill-creator/scripts/grade_pi_skill_eval.py <skill-name>-workspace/iteration-N
```

The grader writes `grading.json` under each run directory and `grading-summary.json` at the iteration root. Use explicit `assertions` in `evals/evals.json` for stronger checks; otherwise the grader uses conservative keyword evidence from expectations.

## Step 6 — Aggregate benchmark

```bash
python .agents/skills/pi-skill-creator/scripts/aggregate_pi_skill_benchmark.py <skill-name>-workspace/iteration-N
```

This writes `benchmark.json` and `benchmark.md` with pass rates by configuration.

## Step 7 — Generate review report

```bash
python .agents/skills/pi-skill-creator/scripts/generate_pi_skill_report.py <skill-name>-workspace/iteration-N
```

This writes static `eval-report.md` and `eval-report.html` for review.

## Step 8 — Analyze trigger proxy
Run static trigger proxy analysis to catch description/eval mismatch. This does not prove actual PI/GSD skill activation; it reports `actual_activation: unavailable` until runtime telemetry exists.

```bash
python .agents/skills/pi-skill-creator/scripts/analyze_skill_triggers.py <skill-dir> --output <skill-name>-workspace/iteration-N/trigger-proxy.json
```

## Step 9 — Improve only from evidence
Summarize pass/fail by eval and by expectation. Improve the skill only where failures reveal reusable instruction gaps, not one-off prompt overfitting. If description triggering is the issue, run `scripts/suggest_description.py` and review the candidate before applying it.
</process>

<success_criteria>
- [ ] Baseline is defined.
- [ ] Eval outputs are saved or dry-review status is explicit.
- [ ] Expectations are graded with evidence.
- [ ] Skill changes are tied to observed failures.
- [ ] Next iteration plan is clear.
</success_criteria>
