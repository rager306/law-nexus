---
id: ADR-0025
title: Consultant parser — separate crate for provider-specific extraction
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-14
supersedes: none
related: [ADR-0013, ADR-0015, ADR-0019]
---

# ADR-0025: Consultant parser — separate crate for provider-specific extraction

## Status

**Accepted [proposed]** — architecture decision recorded. Moves to `[bounded]`
when `ln-consultant-parser` ships with hyperlink extraction + catalog port +
cross-act edge derivation, all TDD-covered.

## Context

`ln-decode` currently handles two providers (Consultant WordML, Garant ODT)
plus shared infrastructure (hierarchy extraction, prefix catalog, text
analysis). The crate is 2947 lines and growing.

The consru_export corpus (43 785 XML, 561 MB) introduced new
Consultant-specific capabilities that do not belong in a generic decode crate:

1. **Hyperlink extraction**: 44-ФЗ alone has 1766 `w:hlink` elements pointing
   to other documents. Each link is a potential cross-act edge (`amends`,
   `cites`, `implements`). This is WordML/Consultant-specific.
2. **Catalog integration**: `consid` tokens (`consultantplus://offline/ref=...`)
   map to a SQLite catalog with sha256, edition metadata, and document
   identity. This is ConsultantPlus infrastructure, not domain law.
3. **Cross-act edge derivation**: link context classification ("в ред." →
   `amends`, "согласно закону" → `cites`, "в порядке" → `implements`) is
   Consultant-format-specific text analysis.
4. **Edition chain**: 118 editions of 44-ФЗ require multi-edition diff and
   replay. This is corpus-management logic, not parsing.

ADR-0013 mandates provider isolation: Consultant ≠ Garant, shared fixture
forbidden. ADR-0015 requires hexagonal separation of concerns.

## Decision

Create a new crate `ln-consultant-parser` `[proposed]` for Consultant-specific
extraction capabilities that go beyond block decoding.

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

- This ADR does not implement the crate; it records the architectural decision.
- `ln-consultant-parser` is `[proposed]` until TDD-covered code ships.
- Catalog SQLite integration is ConsultantPlus infrastructure, not domain law
  or legal correctness proof.
- Hyperlink classification is text-pattern-based, not semantic NLP.

## References

- ADR-0013 (universal multi-source parser; provider isolation)
- ADR-0015 (hexagonal verification architecture)
- ADR-0019 (normative hierarchy and conflict; cross-act edge kinds)
- Review 7 (`doc/review/review-16-08-2026.md`; C1 corpus integration plan)
