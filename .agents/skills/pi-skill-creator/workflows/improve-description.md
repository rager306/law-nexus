# Workflow: Improve Skill Description

<required_reading>
Read now:
1. `references/description-triggering.md`
2. `references/eval-method.md`
</required_reading>

<process>
## Step 1 — Read current description
Extract frontmatter `description`. Check whether it states both task and trigger contexts.

## Step 2 — Compare against eval prompts
For each eval prompt, mark whether the skill should trigger. Identify missed trigger categories and false-trigger categories.

## Step 3 — Rewrite without overfitting
Improve the description by naming broader user intents, not by listing every eval prompt. Keep under 1024 characters and avoid XML tags.

## Step 4 — Revalidate
Run structural validation. Then run the trigger proxy analyzer; treat it as description/eval evidence, not proof that PI/GSD actually loaded the skill at runtime.

```bash
python .agents/skills/pi-skill-creator/scripts/analyze_skill_triggers.py <skill-dir> --output <skill-dir>-trigger-proxy.json
```

## Step 5 — Preserve history
If this is iterative work, store old and new descriptions with the reason for change in the skill's eval workspace or notes.
</process>

<success_criteria>
- [ ] Description is under 1024 characters.
- [ ] It contains both what and when-to-use signals.
- [ ] It improves missed trigger categories without broad false-trigger language.
- [ ] Validation passes after edit.
</success_criteria>
