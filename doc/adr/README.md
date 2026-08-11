# ADRs — law-nexus architectural decisions

> **Format:** MADR-lite with YAML front matter. Retired Python-specific ADRs
> (M068–M106) are archive-only local archaeology and are intentionally absent
> from active links, default indexing and conformance scans.
>
> **D098 lifecycle tags** are mandatory on every architectural/state claim:
> `[bounded]` / `[smoke]` / `[validated]` / `[proposed]` / `[deferred]`.

## Current ADRs

### Direction & foundation

- **ADR-0004** — Full Rust product transition (measured baseline, parity-gated cutover) `[bounded]`
- **ADR-0005** — Rust target architecture (crate and port map; **crate map superseded by ADR-0011/D127**) `[bounded]`
- **ADR-0007** — Python repository control-plane harness (process orchestration only) `[validated]`
- **ADR-0008** — Promotion and publication authority ceiling (D116/D120 separate singular authorities) `[bounded]`
- **ADR-0009** — Five-clock event-anchored temporal model (D118) `[bounded]`
- **ADR-0010** — Evidence kernel gates (D119 C10/C12/C13) `[bounded]`
- **ADR-0011** — KOF-DA ownership — twenty exclusive capability owners (D123) `[bounded]`
- **ADR-0012** — Consequential evidence protocol (storage/ledger/workspace candidate assessment) `[bounded]`
- **ADR-0013** — Universal multi-source parser architecture (Consultant XML + Garant ODT, bounded morphology, sentence and lexical candidates) `[bounded]`
- **ADR-0014** — RuVector as primary graph+vector infrastructure (RVF + redb dual storage; FalkorDB historical-only) `[proposed]`
- **ADR-0015** — Hexagonal verification architecture (overlapping contours, port contracts, lifecycle honesty) `[bounded]`

### Temporal legal ontology and applicability boundary (all `[proposed]`)

A top-down ontology of what an agent needs to reason legally over time. Each
layer depends on the one below it; all are fail-closed (R068) and follow the
D046 adoption ladder (project-local evidence kernel is canon; Akoma/FRBR/ELI/
LKIF are compatibility references, not canon replacements).

- **ADR-0016 (L1/O1)** — FRBR structural legal identity (Work/Expression/Manifestation/Item; date+authority identity) `[proposed]`
- **ADR-0017 (L2/O2)** — Component Temporal Versioning (CTV) — component-level provenance & fail-closed resolver (R070) `[proposed]`
- **ADR-0018 (L3/O3)** — NormativeState(t) — normative status resolver (text ≠ status) `[proposed]`
- **ADR-0019 (L4/O4)** — Normative hierarchy and conflict resolution (lex superior/specialis/posterior; explainable) `[proposed]`
- **ADR-0020 (L5/O5)** — Judicial, FAS and control-organ practice overlay (EffectiveInterpretation; non-authoritative) `[proposed]`
- **ADR-0021 (L6/O6)** — Transitional provisions and risk assessment (derived, non-authoritative) `[proposed]`
- **ADR-0022 (L7/O7)** — Industry profiles architecture (budget/construction/medicine/general-control; adapter-isolated) `[proposed]`
- **ADR-0023** — Applicability protocol ownership: neutral core decision/abstention/trace with versioned profile inputs; runtime absent `[proposed]`

## Retired Python-era records

ADR-0001, ADR-0002 and ADR-0003 governed the retired Python product. ADR-0006
was a rejected PyO3 coexistence draft. Their local vault is gitignored,
untracked and excluded from active conformance/indexing. Historical IDs may be
named on living surfaces only with an explicit retired/archive qualifier.
