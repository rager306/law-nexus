# ADRs — law-nexus architectural decisions

> **Format:** MADR-lite with YAML front matter. See `python_archive/adr/README.md`
> for the previous Python-specific ADRs (M068–M106).
>
> **D098 lifecycle tags** are mandatory on every architectural/state claim:
> `[bounded]` / `[smoke]` / `[validated]` / `[proposed]` / `[deferred]`.

## Current ADRs

- **ADR-0004** — Full Rust product transition (measured baseline, parity-gated cutover)
- **ADR-0005** — Rust target architecture (crate and port map)
- **ADR-0007** — Python repository control-plane harness (process orchestration only)

## Archived (Python-specific, M068–M106)

See `python_archive/adr/`. These ADRs governed the Python codebase; they are
preserved for historical context and inform the Rust migration plan.

## Rejected drafts

See `python_archive/adr/rejected/`. ADR-0006 proposed a PyO3 coexistence bridge
and was rejected by explicit human decision before implementation.
