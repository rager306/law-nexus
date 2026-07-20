# Archived ACP/git-lex project-local history

**Status:** archive-only. These files are not active law-nexus runtime,
architecture, skills, CI, requirements or product dependencies.

This archive preserves project-local ACP/git-lex work after D104/R066 rejected
it as a target architecture. The archive is retained for history and recovery,
not execution or guidance.

## Boundaries

- Do not import, execute, install, sync or regenerate files from this tree.
- Do not add this tree to active skill discovery or test collection.
- Do not use archived projections as product/legal/architecture proof.
- The external `/root/git-lex-kit-acp/` repository is separate and was not
  modified by this archive operation.
- Active product requirements live in `.gsd/REQUIREMENTS.md`; current
  architecture lives in `prd/ARCHITECTURE.md` and current ADRs.

## Contents

- `skills/` — former project-local ACP and git-lex skills.
- `kits/` — former project-local reusable/profile semantic kits.
- Later decommission waves add scripts, tests, `.lex` state and architecture
  history under sibling directories with manifest-backed integrity records.

Source-to-archive mappings and SHA-256 values are tracked in
`prd/migration/decommission/acp-git-lex-manifest.json`. D3a execution result is
`prd/migration/decommission/d3a-skills-kits-result.json`.
