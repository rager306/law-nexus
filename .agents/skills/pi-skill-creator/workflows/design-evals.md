# Workflow: Design Skill Evals

<required_reading>
Read now:
1. `references/eval-method.md`
2. `templates/evals.json`
</required_reading>

<process>
## Step 1 — Choose eval dimensions
Pick prompts that test:
- correct trigger/use case
- non-trigger or boundary case
- key workflow path
- output format
- domain gotcha the skill must prevent

## Step 2 — Write realistic prompts
Use the user's natural language, not artificial benchmark wording. Include only files/fixtures that a real task would have.

## Step 3 — Add expectations
Each eval needs objective expected behavior. Good expectations are checkable from the final output or changed files.

## Step 4 — Decide grading mode
Use programmatic checks for file/schema/substring/command outcomes. Use rubric grading for design, reasoning, or quality judgments.

## Step 5 — Store evals
Write `evals/evals.json` inside the skill directory. Include `skill_name`, `evals[].id`, `prompt`, `expected_output`, `files`, and `expectations`.
</process>

<success_criteria>
- [ ] At least 3 eval prompts exist.
- [ ] Expectations are specific and checkable.
- [ ] At least one eval catches over-triggering or wrong-domain behavior.
- [ ] Eval file validates with the PI validator.
</success_criteria>
