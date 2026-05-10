# Skill Evaluation Method for PI/GSD

## Eval file

Store evals at:

```text
{skill-dir}/evals/evals.json
```

Minimal shape:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User task prompt",
      "expected_output": "Human-readable success description",
      "files": [],
      "expectations": [
        "The output does X",
        "The skill avoids Y"
      ]
    }
  ]
}
```

## Eval categories

A useful set includes:

- should-trigger prompt
- should-not-trigger or boundary prompt
- main workflow prompt
- gotcha prompt
- output-format prompt

## Baselines

- New skill: compare with no skill or existing agent behavior.
- Improved skill: compare with snapshot of previous skill.
- If full baseline execution is not possible, record `dry_review` and do not claim benchmark proof.

## Grading

Each expectation should produce:

```json
{
  "text": "Expectation statement",
  "passed": true,
  "evidence": "Where the output proves this"
}
```

Programmatic checks are preferred for files, JSON, schema, exact strings, commands, and forbidden content. Rubric checks are acceptable for design quality and reasoning.

For deterministic local grading, run:

```bash
python .agents/skills/pi-skill-creator/scripts/run_pi_skill_loop.py <skill-dir>
# Option A: execute generated prompts through real PI/GSD headless sessions
python .agents/skills/pi-skill-creator/scripts/run_pi_skill_loop.py <skill-dir> --no-prepare --iteration N --execute gsd-print
# Option B: execute generated EXECUTOR_PROMPT.md files manually/subagents and save outputs/answer.md
python .agents/skills/pi-skill-creator/scripts/run_pi_skill_loop.py <skill-dir> --no-prepare --iteration N
```

Or run individual steps:

```bash
python .agents/skills/pi-skill-creator/scripts/run_pi_skill_eval.py <skill-dir>
python .agents/skills/pi-skill-creator/scripts/execute_pi_skill_eval.py <skill-name>-workspace/iteration-N --backend gsd-print
python .agents/skills/pi-skill-creator/scripts/grade_pi_skill_eval.py <skill-name>-workspace/iteration-N
python .agents/skills/pi-skill-creator/scripts/aggregate_pi_skill_benchmark.py <skill-name>-workspace/iteration-N
python .agents/skills/pi-skill-creator/scripts/generate_pi_skill_report.py <skill-name>-workspace/iteration-N
python .agents/skills/pi-skill-creator/scripts/analyze_skill_triggers.py <skill-dir> --output <skill-name>-workspace/iteration-N/trigger-proxy.json
```

## Execution artifacts

Generated executor prompts include absolute run-local output paths. This matters for `gsd --print`: if the prompt only says `outputs/answer.md`, the headless session may write to the repository root and the harness may grade stdout summaries instead of the intended artifact.

`execute_pi_skill_eval.py` records `answer_source` in each `outputs/run.json`:

- `executor_created_file` — preferred; the model/tool wrote the requested run-local `outputs/answer.md`.
- `stdout_fallback` — acceptable for simple answer-only tasks; the harness created `outputs/answer.md` from stdout.

Before trusting a live benchmark, confirm execution summary and at least spot-check `answer_source`. Runtime activation telemetry is still separate and remains `actual_activation: unavailable` unless PI/GSD exposes skill-read/tool-call metadata.

Use optional structured assertions when substring/regex checks are needed:

```json
{
  "text": "The output names the dangerous operation",
  "kind": "contains",
  "pattern": "DROP TABLE"
}
```

Supported assertion kinds: `contains`, `not_contains`, `regex`.

## Trigger proxy

Use `scripts/analyze_skill_triggers.py` to check whether eval prompts align with the skill description. Each eval may include optional metadata:

```json
{
  "category": "should-trigger",
  "should_trigger": true
}
```

For boundary prompts, set `should_trigger` to `false` or use a category such as `boundary` / `should-not-trigger`. The analyzer reports `trigger_proxy_score`, `predicted_trigger`, false positives, and false negatives. It always reports `actual_activation: unavailable` because this local proxy does not inspect PI/GSD runtime tool-call telemetry.

## Iteration rule

Only change the skill when a failure reveals a reusable instruction gap. Do not overfit to a single eval prompt.
