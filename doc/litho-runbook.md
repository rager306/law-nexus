# Litho (deepwiki-rs) runbook — law-nexus

**Status:** process helper, `[bounded]` adoption config only.
**Tool:** [deepwiki-rs / Litho](https://github.com/sopaco/deepwiki-rs) (crates.io `deepwiki-rs`).
**Config:** local gitignored `litho.toml` at repository root (not a published artifact).

## Authority (fail-closed)

| Surface | Role |
|---------|------|
| `prd/ARCHITECTURE.md` | Living truth oracle — **read first** |
| `doc/adr/**` | Architectural substance (MADR + D098 lifecycle tags) |
| `.gsd/REQUIREMENTS.md`, `.gsd/DECISIONS.md` | GSD requirements / decisions |
| `crates/**`, tests, harness | Product / control-plane proof |
| `litho.docs/**`, `.litho/**` | **Derived only** — onboarding / C4 wiki / drift input |

**Rules**

1. Litho output is **never** legal authority and never source of truth (D098).
2. Do **not** auto-merge `litho.docs/` into `prd/ARCHITECTURE.md`, `doc/adr/**`, claims ledger, or architecture registry JSONL.
3. Do **not** promote lifecycle tags: a Litho sentence that sounds “validated” does not change ADR/README tags.
4. Do **not** feed vaults: `archive/`, `python_archive/`, `prd/archive/**`, `law-source/`, `.lex/`, `Old_project/`, `probes/` (config uses `git_tracked_only` + explicit excludes).
5. Human review is required before any oracle edit suggested by a Litho vs-code drift pass.
6. After intentional oracle edits, run governor ADR probes and `scripts/verify-adr-conformance.py` as usual.

## What Litho is for here

- Generate a fresh **C4-style / repo-wiki** snapshot from the **active** tree (`crates/`, harness, tracked docs via knowledge).
- Surface **structural drift** (crate map, boundaries, workflows) against the living oracle.
- Onboarding aid for humans/agents — **secondary** to ARCHITECTURE + ADRs + GitNexus.

What it is **not**: product proof, citation safety, ontology validation, or a replacement for GitNexus / governor / ADR matrix.

## Prerequisites

- Rust toolchain + `cargo install deepwiki-rs` (or build from upstream).
- LLM credentials for the chosen provider (`LITHO_LLM_API_KEY` recommended; never commit keys).
- Network access to the provider (or local Ollama if `provider = "ollama"`).

Install:

```bash
cargo install deepwiki-rs
deepwiki-rs --help
```

Optional viewer (separate project): [litho-book](https://github.com/sopaco/litho-book).
Optional Mermaid repair: [mermaid-fixer](https://github.com/sopaco/mermaid-fixer).

## Configuration map

Local root `litho.toml` (gitignored; create/maintain from this runbook and local deepwiki-rs configuration requirements):

- **Scan:** `git_tracked_only = true`; excludes build/vault/legal-corpus paths; `*.md` excluded from code scan.
- **Knowledge (read-only inject):**
  - `architecture` → `prd/ARCHITECTURE.md`, architecture README, root README
  - `adr` → `doc/adr/**`, cross-matrix
  - `workflow` → active migration/project-state roadmaps only
  - `general` → thin `prd/parser/README.md`
- **Output:** `./litho.docs` (gitignored)
- **Cache / workdir:** `./.litho` (gitignored)
- **Boundary caps:** reduced for monorepo timeout risk

Default `[llm]` points at a **local OpenAI-compatible gateway**:
`http://127.0.0.1:20128/v1`, model `deepseek-v4-flash` (efficient + powerful).
Key via `LITHO_LLM_API_KEY` only (never commit). Override base URL/models in
`litho.toml` or CLI when the gateway changes.

## Commands

```bash
# From repository root
export LITHO_LLM_API_KEY="..."   # local gateway key; never commit
# or: set -a && source .env && set +a

# Optional: refresh knowledge cache from local docs
deepwiki-rs sync-knowledge
# deepwiki-rs sync-knowledge --force

# Full generation (uses litho.toml when present)
deepwiki-rs -p . -o ./litho.docs --target-language en

# Force ignore cache
deepwiki-rs -p . -o ./litho.docs --force-regenerate

# Explicit CLI override (matches current litho.toml defaults)
# deepwiki-rs -p . -o ./litho.docs \
#   --llm-api-base-url http://127.0.0.1:20128/v1 \
#   --model-efficient deepseek-v4-flash \
#   --model-powerful deepseek-v4-flash
```

Typical output tree:

```text
litho.docs/
├── 1. Overview / Project Overview
├── 2. Architecture
├── 3. Workflow
├── 4. Deep Dive / Deep-Exploration/...
├── 5. Boundary-Interfaces
└── (optional) 6. Database-Overview
```

Banner recommendation for any published copy: mark pages as
`derived / non-authoritative / D098 — not prd/ARCHITECTURE.md`.

## Actualization loop (recommended)

1. **Regen** after material changes to `crates/`, harness composition, or oracle docs.
2. **Diff mentally or with review tools:** Litho crate/boundary map vs `prd/ARCHITECTURE.md` + ADR-0011 crate ownership.
3. **Patch the oracle** (ARCHITECTURE/ADR) only with human judgment + evidence; keep lifecycle tags honest.
4. **Gates:** `uv run python -m law_nexus_harness.governor`, `uv run python scripts/verify-adr-conformance.py` when ADR/oracle surfaces change.
5. **Do not** CI-fail PRs solely because Litho text ≠ README.

## CI policy

- Optional manual/nightly artifact generation is fine.
- Do **not** gate merges on Litho equality with living docs.
- Do **not** commit API keys or raw `.litho/cache` blobs with secrets.

## Security / privacy

- `.env` and secrets are excluded; still avoid pasting keys into prompts or committing `litho.toml` with real keys.
- Legal source trees (`law-source/`) are excluded — do not re-enable casually (corpus + license + noise).
- Generated prose may paraphrase ADRs incorrectly; verify consequential claims against primary files.

## Failure modes

| Symptom | Likely cause | Mitigation |
|---------|----------------|------------|
| Auth errors | Missing/invalid `LITHO_LLM_API_KEY` | Set env; check provider |
| Timeouts on boundary phase | Monorepo size / slow model | Keep `[boundary_analysis]` caps; smaller models |
| Hallucinated stack (FalkorDB as live, Python product, etc.) | Model ignored knowledge / stale training | Knowledge inject + human reject; re-read ARCHITECTURE |
| Lifecycle smoothing | Model prose | Never copy tags from Litho into ADR |
| Scanned archive noise | `git_tracked_only` off or exclude missing | Keep config as-is |

## Related project surfaces

- Living oracle: [`prd/ARCHITECTURE.md`](../prd/ARCHITECTURE.md)
- ADR index: [`doc/adr/README.md`](adr/README.md)
- Cross matrix: [`doc/adr-architecture-cross-matrix.md`](adr-architecture-cross-matrix.md)
- Code navigation: GitNexus repo name `law-nexus`
- Process gates: `law_nexus_harness.governor` / preflight

## Non-claims

Adopting this runbook does **not** claim:

- that Litho docs are complete, correct, or citation-safe;
- that any product capability is `[validated]`;
- that ontology ADRs (0016–0022) are implemented;
- that derived architecture registry views are replaced or superseded by Litho.
