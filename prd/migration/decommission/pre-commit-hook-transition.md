# Pre-commit hook transition

**Status:** git-lex hook disconnected; standard pre-commit hook active.

## Before

- Owner: `git-lex`
- SHA-256: `2a2db210fb5262683d9b66d1c8d22905b245e2217cdc885bf2ed9a7af88f68bb`
- Invocation: `git-lex hook pre-commit`
- Effect observed before M108: commits regenerated `.lex/extract`.

## After

- Owner: `pre-commit`
- SHA-256: `37f0e1ff021f59a4a5827ed05e333dcbd29af0ce622d391feb0785bc3411724c`
- Config: `.pre-commit-config.yaml`
- `git-lex` invocation: absent
- Legacy local copy: removed by forced standard installation

Installed with:

```bash
uv run pre-commit install --install-hooks --overwrite
```

`--overwrite` is mandatory: ordinary migration mode preserves and executes the
legacy hook after standard checks. The forced generated hook directly executes
`pre_commit hook-impl` and cannot chain a `.legacy` file.

## Recovery

If the standard hook is missing or stale:

```bash
uv run pre-commit install --install-hooks --overwrite
```

Do not restore the git-lex hook. `.lex` remains present only until the later
archive wave; D1 proves it no longer changes during commits.
