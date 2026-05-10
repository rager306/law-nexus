---
name: pi-skill-creator
description: Create, adapt, validate, and improve PI/GSD skills. Use when the user wants to create a new skill, adapt an external skill such as Anthropic skill-creator for PI, add eval prompts/rubrics, validate skill structure, optimize skill descriptions, or test whether a skill triggers and produces useful outputs in PI/GSD.
---

<essential_principles>
## PI Skill Creator Operating Rules

### 1. Use PI/GSD format as the target
PI/GSD skills live in `~/.agents/skills/{name}/` or `.agents/skills/{name}/`, with `SKILL.md` frontmatter and optional `workflows/`, `references/`, `templates/`, and `scripts/`. Adapt external skill ideas to this format; do not copy Claude Code-specific assumptions blindly.

### 2. Treat skill quality as testable
A skill is not done when files exist. It needs structural validation, trigger/description review, realistic eval prompts, expected-behavior rubrics, and at least one real or dry-run exercise.

### 3. Keep SKILL.md small and unavoidable
Put essential rules, a compact retrieval index, and routing in `SKILL.md`. Move detailed procedures to `workflows/` and reusable knowledge to `references/`.

### 4. Compare against baseline when possible
When improving a skill, evaluate the new version against either no skill or a snapshot of the old skill. If full subagent evaluation is too expensive, at least run structural validation plus rubric-based dry review.

### 5. Optimize descriptions deliberately
The description is the trigger surface. It must say what the skill does and when to use it, in third person, under PI/GSD's 1024-character limit, without XML tags.
</essential_principles>

<quick_reference>
## PI Skill Creator Retrieval Index

- Create/adapt a skill → `workflows/create-or-adapt-skill.md`
- Add eval prompts/rubric → `workflows/design-evals.md`
- Validate structure → `workflows/validate-skill.md`, `scripts/validate_pi_skill.py`
- Improve triggering/description → `workflows/improve-description.md`, `scripts/analyze_skill_triggers.py`
- Run an iteration loop → `workflows/run-eval-loop.md`, `scripts/run_pi_skill_loop.py`, `scripts/run_pi_skill_eval.py`, `scripts/execute_pi_skill_eval.py`, `scripts/grade_pi_skill_eval.py`, `scripts/aggregate_pi_skill_benchmark.py`
- Run end-of-session learning → `workflows/end-session-learning.md`, `references/session-learning.md`, repository-level session learning script
- Analyze trigger proxy → `scripts/analyze_skill_triggers.py`
- Generate review report → `scripts/generate_pi_skill_report.py`
- Package/export a skill → `scripts/package_pi_skill.py`
- Improve description → `workflows/improve-description.md`, `scripts/suggest_description.py`
- PI/GSD format rules → `references/pi-skill-format.md`
- Anthropic adaptation notes → `references/anthropic-skill-creator-adaptation.md`
- Vercel AGENTS.md vs skills decision → `references/agents-md-vs-skills.md`
- Evaluation schema/rubric → `references/eval-method.md`, `references/analyzer-grader-comparator.md`, `templates/evals.json`, `templates/eval-report.md`, `templates/history.json`
</quick_reference>

<routing>
| User intent | Load and follow |
|---|---|
| Create a new PI/GSD skill or adapt an external skill | `workflows/create-or-adapt-skill.md` |
| Add tests/evals to a skill | `workflows/design-evals.md` |
| Validate an existing skill's structure | `workflows/validate-skill.md` |
| Improve a skill description / trigger behavior | `workflows/improve-description.md` |
| Run with-skill vs baseline iteration | `workflows/run-eval-loop.md` |
| Analyze a completed session for skill/memory improvements | `workflows/end-session-learning.md` |
| Package/export a validated skill | `workflows/validate-skill.md` then `scripts/package_pi_skill.py` |

If the user asks broadly to "fix skills" or "solve the skill issue", start with `workflows/validate-skill.md` for existing skills, then `workflows/design-evals.md` for the highest-priority one.
</routing>

<reference_index>
- `references/pi-skill-format.md` — PI/GSD skill directories, frontmatter, XML/router structure, discovery.
- `references/anthropic-skill-creator-adaptation.md` — what to keep/change/drop from Anthropic skill-creator.
- `references/agents-md-vs-skills.md` — Vercel-informed guidance on what belongs in always-loaded project context versus a skill.
- `references/eval-method.md` — eval prompt, rubric, baseline, grading, and iteration method.
- `references/analyzer-grader-comparator.md` — PI rubrics for analyzing benchmark results and comparing skill versions.
- `references/description-triggering.md` — description writing and trigger review guidance.
- `references/session-learning.md` — end-of-session retrospective loop, agentmemory use, and skill-update criteria.
</reference_index>

<workflows_index>
| Workflow | Purpose |
|---|---|
| `create-or-adapt-skill.md` | Build a PI skill from requirements or external prior art |
| `design-evals.md` | Create eval prompts and expected-behavior rubrics |
| `validate-skill.md` | Run structural validation and inspect references/workflows |
| `improve-description.md` | Improve trigger description without overfitting |
| `run-eval-loop.md` | Execute an Anthropic-style improvement loop adapted to PI |
| `end-session-learning.md` | Analyze session logs and decide whether to update skills or agentmemory |
</workflows_index>

<runtime_eval_limitations>
## Runtime Eval and Trigger Detection Limits

`pi-skill-creator` may run honest local eval loops only when execution evidence is real. It must not fabricate model outputs, trigger events, or skill activation telemetry.

### Feasible now
- Live answer generation can be added through PI/GSD headless execution, for example `gsd --print`, `gsd --mode text`, or `gsd --mode json`, saving stdout/stderr/exit code into eval `outputs/` before grading.
- Trigger quality can be approximated with static description analysis, should-trigger / should-not-trigger evals, and optional model-based trigger proxy prompts.

### Current limitation
- Trigger proxy results are not proof that PI/GSD actually auto-loaded a skill. They only show that a description or model selection prompt points toward the expected skill.
- Full automatic trigger detection requires PI/GSD runtime telemetry that exposes actual skill activation, such as a `Skill` tool call, a `read` call to `.../skills/{name}/SKILL.md`, or equivalent metadata from headless JSON transcripts.

### Needed runtime work
- Add or verify a PI/GSD headless transcript format that includes tool calls and skill reads.
- Wire skill-read events to durable telemetry for print/headless sessions, not only auto-mode metrics.
- Update eval scripts to mark `actual_activation: true|false|unavailable` separately from `trigger_proxy_score`.
</runtime_eval_limitations>

<success_criteria>
A PI/GSD skill-creator run is complete when:
- The skill follows PI/GSD structure and frontmatter rules.
- The description states what/when and is trigger-oriented.
- Required workflows/references/templates are referenced and present.
- Eval prompts and expected behavior exist for realistic user tasks.
- Structural validation passes.
- Any limitations of trigger/runtime evaluation are stated plainly.
</success_criteria>
