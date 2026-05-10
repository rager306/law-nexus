# Workflow: Create or Adapt a PI/GSD Skill

<required_reading>
Read now:
1. `references/pi-skill-format.md`
2. `references/anthropic-skill-creator-adaptation.md`
3. `references/eval-method.md`
4. `references/agents-md-vs-skills.md`
</required_reading>

<process>
## Step 1 — Capture intent
Extract from the conversation first. Only ask about gaps that matter:
- What should the skill enable?
- When should it trigger?
- What output should it produce?
- Is it global (`~/.agents/skills`) or project-local (`.agents/skills`)?
- What should count as a passing eval?

## Step 2 — Research prior art
If adapting an external skill, separate:
- portable process ideas
- format assumptions to replace with PI/GSD conventions
- scripts that can be reused safely
- scripts that depend on another runtime and should be rewritten

## Step 3 — Choose structure
Use a single `SKILL.md` only for small one-workflow skills. Use router pattern when there are multiple intents, repeated references, or expected future growth. Apply the AGENTS.md decision guide: broad, always-needed indexes or guardrails may belong in `AGENTS.md`; action-specific procedures belong in the skill.

## Step 4 — Draft files
Create:
- `SKILL.md` with frontmatter, essential principles, quick reference, routing, and success criteria
- `workflows/` for procedures
- `references/` for reusable knowledge
- `templates/` for output shapes
- `scripts/` only for deterministic reusable checks

## Step 5 — Add evals before declaring done
Create `evals/evals.json` from `templates/evals.json`. Add 3-5 realistic prompts with expectations. Prefer prompts that catch the failure modes the skill is meant to prevent.

## Step 6 — Validate and iterate
Run `scripts/validate_pi_skill.py <skill-dir>` or the project-specific verifier. Fix structure, description, missing references, and bloated SKILL.md before doing content polish.
</process>

<success_criteria>
- [ ] Intent and trigger conditions are explicit.
- [ ] PI/GSD structure is used.
- [ ] External prior art has been adapted, not blindly copied.
- [ ] Eval prompts exist.
- [ ] Structural validation passes.
</success_criteria>
