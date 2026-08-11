# ADRs — law-nexus architectural decisions

> **Format:** MADR-lite with YAML front matter. See `python_archive/adr/README.md`
> for the previous Python-specific ADRs (M068–M106).
>
> **D098 lifecycle tags** are mandatory on every architectural/state claim:
> `[bounded]` / `[smoke]` / `[validated]` / `[proposed]` / `[deferred]`.

## Current ADRs

### Direction & foundation

- **ADR-0004** — Full Rust product transition (measured baseline, parity-gated cutover) `[bounded]`
- **ADR-0005** — Rust target architecture (crate and port map; **crate map superseded by ADR-0011/D127**) `[bounded]`
- **ADR-0007** — Python repository control-plane harness (process orchestration only) `[validated]`
- **ADR-0008** — Promotion and publication authority ceiling (D116/D120 separate singular authorities)
- **ADR-0009** — Five-clock event-anchored temporal model (D118)
- **ADR-0010** — Evidence kernel gates (D119 C10/C12/C13)
- **ADR-0011** — KOF-DA ownership — twenty exclusive capability owners (D123)
- **ADR-0012** — Consequential evidence protocol (storage/ledger/workspace candidate assessment)
- **ADR-0013** — Universal multi-source parser architecture (Consultant XML + Garant ODT, bounded morphology, sentence and lexical candidates)
- **ADR-0014** — RuVector as primary graph+vector infrastructure (RVF + redb dual storage, replacing FalkorDB)
- **ADR-0015** — Hexagonal verification architecture (overlapping contours, port contracts, lifecycle honesty)

### Temporal legal ontology and applicability boundary (all `[proposed]`)

A top-down ontology of what an agent needs to reason legally over time. Each
layer depends on the one below it; all are fail-closed (R068) and follow the
D046 adoption ladder (project-local evidence kernel is canon; Akoma/FRBR/ELI/
LKIF are compatibility references, not canon replacements).

- **ADR-0016 (L1)** — FRBR structural legal identity (Work/Expression/Manifestation/Item; date+authority identity)
- **ADR-0017 (L2)** — Component Temporal Versioning (CTV) — component-level provenance & fail-closed resolver (R070)
- **ADR-0018 (L3)** — NormativeState(t) — normative status resolver (text ≠ status)
- **ADR-0019 (L4)** — Normative hierarchy and conflict resolution (lex superior/specialis/posterior; explainable)
- **ADR-0020 (L5)** — Judicial, FAS and control-organ practice overlay (EffectiveInterpretation; non-authoritative)
- **ADR-0021 (L6)** — Transitional provisions and risk assessment (derived, non-authoritative)
- **ADR-0022 (L7)** — Industry profiles architecture (budget/construction/medicine/general-control; adapter-isolated)
- **ADR-0023** — Applicability protocol ownership: neutral core decision/abstention/trace with versioned profile inputs; runtime absent

## Archived (Python-specific, M068–M106)

See `python_archive/adr/`. These ADRs governed the Python codebase; they are
preserved for historical context and inform the Rust migration plan.

## Rejected drafts

See `python_archive/adr/rejected/`. ADR-0006 proposed a PyO3 coexistence bridge
and was rejected by explicit human decision before implementation.
