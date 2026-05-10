# Description and Triggering Guidance

## Description job

The description is what PI/GSD surfaces in the available skills list. It must help the model decide when to invoke the skill.

Good descriptions include:

- what the skill does
- when to use it
- trigger phrases or contexts
- boundaries that distinguish it from nearby skills

## Rules

- Keep under 1024 characters.
- Avoid XML tags.
- Prefer third-person phrasing for PI/GSD consistency.
- Be a little pushy for important skills: "Use when...".
- Focus on user intent, not internal implementation details.
- Avoid long lists that bloat prompt context.

## Missed-trigger diagnosis

If relevant prompts do not trigger, add broader intent categories to the description.

## False-trigger diagnosis

If irrelevant prompts trigger, add boundary language or narrow the domain.

## Avoid overfitting

Do not paste all eval prompts into the description. Generalize from failures.
