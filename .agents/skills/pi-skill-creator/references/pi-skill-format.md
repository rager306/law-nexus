# PI/GSD Skill Format

## Directories

PI/GSD discovers skills from:

- User/global: `~/.agents/skills/{skill-name}/`
- Project-local: `.agents/skills/{skill-name}/`

Project-local skills are versioned with the repository. Global skills are available across projects.

## Required file

Every skill requires:

```text
{skill-name}/SKILL.md
```

The directory name must match frontmatter `name`.

## Frontmatter

Required:

```yaml
---
name: lowercase-hyphen-name
description: What it does and when to use it.
---
```

Rules:

- `name`: lowercase letters, digits, hyphens; max 64 chars.
- `description`: non-empty, max 1024 chars, no XML tags, third person preferred.
- Description is the trigger surface; include both task and trigger contexts.

## Recommended router structure

Use XML tags in the body:

```xml
<essential_principles>...</essential_principles>
<quick_reference>...</quick_reference>
<routing>...</routing>
<reference_index>...</reference_index>
<workflows_index>...</workflows_index>
<success_criteria>...</success_criteria>
```

## Progressive disclosure

- `SKILL.md`: unavoidable principles and compact retrieval/routing index.
- `workflows/`: step-by-step procedures.
- `references/`: reusable domain knowledge.
- `templates/`: output shapes or eval schemas.
- `scripts/`: deterministic reusable checks.

## Activation

After adding a skill, run `/reload` in the current PI/GSD session or start a new session. Auto-mode discovers new skills at unit boundaries.
