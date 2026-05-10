# Workflow: Validate a PI/GSD Skill

<required_reading>
Read now:
1. `references/pi-skill-format.md`
2. `references/eval-method.md`
</required_reading>

<process>
## Step 1 — Locate skill
Confirm the skill directory contains `SKILL.md` and that the directory name matches frontmatter `name`.

## Step 2 — Run structural validator
Run:

```bash
python .agents/skills/pi-skill-creator/scripts/validate_pi_skill.py <skill-dir>
```

If a project-specific verifier exists, run it too.

## Step 3 — Inspect trigger description
Check that the description says what the skill does and when to use it, uses third person, avoids XML tags, and stays under 1024 characters.

## Step 4 — Inspect progressive disclosure
Ensure `SKILL.md` is compact and references existing workflow/reference/template files. Important rules that must never be skipped belong in `SKILL.md`; detailed content belongs outside.

## Step 5 — Validate evals
If `evals/evals.json` exists, validate it. If it does not exist, recommend adding evals before treating the skill as quality-validated.
</process>

<success_criteria>
- [ ] Structural validator passes.
- [ ] Description is trigger-oriented.
- [ ] References are present.
- [ ] SKILL.md is not bloated.
- [ ] Eval status is known.
</success_criteria>
