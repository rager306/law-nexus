# Historical noise vault (not active product truth)

Relocated ACP/git-lex/FalkorDB/MiniMax/PyO3-era agent skills, scripts, and tests
so they are not discovered as active guidance and are gitignored from the index.

| Path | Contents |
|------|----------|
| `agent-skills/` | FalkorDB skill pack + M001 LegalGraph routers |
| `scripts/` | Era prove/verify/smoke scripts (ACP, git-lex, FalkorDB, M002/M003, M048–M067, s09/s10) |
| `tests/` | Matching historical tests/fixtures |

**Active skills under** `.agents/skills/`:
- `law-nexus-rust`
- `russian-legal-evidence`
- `pi-skill-creator`

**Active truth:** `prd/ARCHITECTURE.md`, `doc/adr/**`, `crates/**`, `src/law_nexus_harness/**`.

Do not promote claims from this vault without re-validation (D098).
