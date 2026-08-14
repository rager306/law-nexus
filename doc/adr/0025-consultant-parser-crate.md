---
id: ADR-0025
title: Consultant parser — separate crate for provider-specific extraction
status: Accepted
lifecycle: "[bounded]"
date: 2026-08-14
supersedes: none
related: [ADR-0013, ADR-0015, ADR-0019]
---

# ADR-0025: Consultant parser — separate crate for provider-specific extraction

## Status

**Accepted [bounded]** — crate shipped with 9 functional modules plus `lib.rs`,
64 integration test functions and 4 source-unit tests covering
synthetic/tracked mechanics: hyperlink extraction, YAML-driven
contains+bounded-morph AND/OR classification, edge derivation, observation
store, a read-only SQLite adapter behind `CatalogPort`, and multi-edition
filename/delta helpers.
`consru_export` metrics (hyperlink/edge/observation counts; Review 7 local
inventory of 118 editions) are local `[smoke]`, skip-capable when the
gitignored corpus is absent, and are not a G1 corpus-size promotion or other
promotion proof (R082). The SQLite adapter has `[bounded]`
shared-contract and production-like temporary-schema proof; it is not legal or
corpus validation. No `[validated]` promotion.

## Context

`ln-decode` currently handles two providers (Consultant WordML, Garant ODT)
plus shared infrastructure (hierarchy extraction, prefix catalog, text
analysis). The crate is 2947 lines and growing.

The gitignored `consru_export` corpus (local `[smoke]` inventory: 43 785 XML,
561 MB) motivated Consultant-specific capabilities that do not belong in a
generic decode crate:

1. **Hyperlink extraction**: local `[smoke]` 44-ФЗ export has 1766 `w:hlink`
   elements pointing to other documents. Each link is a potential cross-act
   edge (`amends`, `cites`, `implements`). This is WordML/Consultant-specific.
2. **Catalog integration**: `consid` tokens (`consultantplus://offline/ref=...`)
   map to a SQLite catalog with sha256, edition metadata, and document
   identity. The read-only `SqliteCatalog` resolves locator → document →
   deterministic edition metadata and distinguishes a genuine miss from
   open/schema/decode failure. This is ConsultantPlus infrastructure, not
   domain law.
3. **Cross-act edge derivation**: link context classification ("в ред." →
   `amends`, "согласно закону" → `cites`, "в порядке" → `implements`) is
   Consultant-format-specific text analysis.
4. **Edition chain**: local `[smoke]` 118 editions of 44-ФЗ motivate
   multi-edition diff and replay. That count is not promotion proof.

ADR-0013 mandates provider isolation: Consultant ≠ Garant, shared fixture
forbidden. ADR-0015 requires hexagonal separation of concerns.

## Decision

Create a new crate `ln-consultant-parser` `[bounded]` for Consultant-specific
extraction capabilities that go beyond block decoding. Shipped proof is the
synthetic/tracked suite. A non-skipping 435-ФЗ system contract executes
hyperlink extraction → path-aware scored classification → edge derivation →
unknown observations twice with deterministic bounded anchors, plus an atomic
malformed-decode diagnostic at the owning `ln-decode` boundary.
`consru_export` runs stay local `[smoke]`.

### Crate boundary

```
ln-decode (unchanged — port + shared types + hierarchy + text analysis)
     │ depends on
     ▼
ln-consultant-parser (NEW)
     ├── hyperlink extraction: w:hlink → ClassifiedLink
     ├── catalog port: consid → CatalogRecord (title, kind, number, date)
     ├── cross-act edge derivation: context → CrossActEdge (ADR-0019)
     └── edition chain builder: multi-edition → diff → AmendmentEvent
     │ depends on
     ▼
ln-kb-ontology (CrossActEdge, diff_marker_sets, MarkerDiff)
```

### What stays in ln-decode

- `BlockDecoderPort` trait (port contract)
- `ConsultantWordMlBlockDecoder` (block-level WordML → ParsedBlock)
- `GarantOdtBlockDecoder` (block-level ODT → ParsedBlock)
- `extract_hierarchy` + `DecodePrefixCatalog` (YAML-driven, provider-neutral)
- `HierarchyLevel`, `ParsedBlock`, `SourceLocation` (shared domain types)
- Text analysis (references, temporal phrases, deontic lexemes)

### What moves to ln-consultant-parser

- `w:hlink` extraction and classification (Consultant-specific XML structure)
- `consid` token decoding and catalog lookup
- Cross-act edge derivation from link context
- Multi-edition chain management

### Why not split ln-decode entirely

1. Port + domain types (560 lines) are tightly coupled and provider-neutral.
2. Both adapters together are ~500 lines — small enough to coexist.
3. Text analysis is provider-neutral and reused by both adapters.
4. Full split (ln-decode-core + ln-consultant + ln-garant) would be a large
   refactor with limited benefit while the adapter code is small.

## Consequences

- Adds `ln-consultant-parser` to the workspace and allowlist.
- `ln-product-cli` gains a dependency on `ln-consultant-parser` for
  hyperlink-aware inspect.
- `ln-decode` remains stable — no breaking changes to existing consumers.
- Consultant-specific logic (catalog, hyperlinks, editions) can grow
  independently without bloating the generic decode crate.
- Future Garant-specific extensions (if any) would get `ln-garant-parser`
  following the same pattern.

## Non-claims

- `[bounded]` covers shipped synthetic/tracked mechanics only; not legal
  correctness, not citation authority, not G2/G3 corpus acceptance (D180).
- `consru_export` metrics and the 118-edition temporal graph are local
  `[smoke]`, skip-capable, gitignored, and not durable bounded or
  `[validated]` proof (R082).
- The read-only SQLite adapter is `[bounded]` by a shared InMemory/SQLite
  contract and production-like temporary schema. The gitignored local catalog
  remains optional `[smoke]`, not a durable proof anchor, domain law, legal
  correctness or catalog completeness proof.
- Hyperlink classification is text-pattern-based, not semantic NLP.
- No `[validated]` promotion from local smoke or InMemory catalog success.

## References

- ADR-0013 (universal multi-source parser; provider isolation)
- ADR-0015 (hexagonal verification architecture)
- ADR-0019 (normative hierarchy and conflict; cross-act edge kinds)
- Review 7 (`doc/review/review-16-08-2026.md`; C1 corpus integration plan)
