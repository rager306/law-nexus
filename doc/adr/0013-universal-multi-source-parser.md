---
id: ADR-0013
title: Universal multi-source parser architecture for Russian legal documents
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-24
supersedes: none
related: [ADR-0004, ADR-0005]
---

# ADR-0013: Universal multi-source parser architecture

## Status

**Accepted [bounded]** — independent Consultant XML and Garant ODT adapters
parse one tracked real document per provider into shared domain types with
hostile, integration and deterministic tracer tests. Parser/corpus completeness,
full provider semantics, references, temporal facts, NormStatement extraction
and citation mapping remain open.

**Critical boundary:** ConsultantPlus WordML/XML extraction assumptions are
incompatible with the Garant ODT parser direction. The two adapters are
independent risk profiles: WordML assumptions (style IDs, paragraph structure)
MUST NOT be inherited by the ODT adapter. Each adapter must be verified
against its own real source documents independently.

## Context

law-nexus ingests Russian normative legal acts from two providers with
fundamentally different file formats:

| Aspect | Consultant (ConsultantPlus) | Garant |
|--------|---------------------------|--------|
| Format | Word 2003 XML (WordML) | ODF 1.2 (OpenDocument .odt) |
| Container | Single XML file | ZIP archive (content.xml inside) |
| Paragraph | `<w:p>` with `<w:pStyle w:val="N"/>` | `<text:p text:style-name="sN">` |
| Text runs | `<w:r><w:t>` | `<text:span>` inside `<text:p>` |
| Binary data | `<w:binData>` (base64 inline) | `Pictures/` in ZIP |
| Style taxonomy | ConsPlusTitle, ConsPlusNormal, ConsPlusJurTerm... | s1, s9, s10, s52... |
| Known annotations | ГАРАНТ comment blocks in s9/s9header | N/A (Consultant doesn't embed provider comments in WordML) |
| Encoding | UTF-8 | UTF-8 |

Both providers deliver the **same legal content** (federal laws, government
decrees, etc.) but with different formatting, provider annotations, and XML
vocabularies. The hierarchy of Russian legal acts is **format-independent**:

```
Раздел → Глава → [§ Параграф] → Статья → Часть → Пункт → Подпункт
```

ADR-0005 proposed a single `law-nexus-parser` crate with `consultant_wordml.rs`
and `garant_odt.rs` modules. That was pre-implementation planning. Now that we
have a working `WordMLStreamingDecoder` and have examined real ODT structure,
we can design the universal architecture properly.

**Old project prior art** (in `Old_project/`, NOT trusted as implementation):
- `parsing_prompt.yaml`: YAML-based extraction rules with regex markers
- `sources/consultant_word2003xml.yaml`: source format config (preprocessing rules, namespace mappings, element rules)
- `structures/44fz.yaml`: document-specific hierarchy config with structure markers
- These are **good ideas** to adapt, not code to port

## Decision

### Universal parser architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    ln-decode (existing crate)            │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │       Source adapter ports (future slices)          │  │
│  │  detect belongs to adapters, not domain            │  │
│  │  decode(input) -> Result<Vec<ParsedBlock>, Error>  │  │
│  │  format_id() -> SourceFormatId                     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────────────────┐  │
│  │ WordMLAdapter    │  │ ODTAdapter                   │  │
│  │ (Consultant XML) │  │ (Garant .odt)                │  │
│  │                  │  │                               │  │
│  │ quick-xml        │  │ zip + quick-xml              │  │
│  │ NsReader         │  │ NsReader on content.xml      │  │
│  │ w:p/w:pStyle/w:t │  │ text:p/@style-name/text:span │  │
│  └──────────────────┘  └──────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │           ParsedBlock (SHARED domain type)          │  │
│  │  private validated fields                          │  │
│  │  text + optional provider_style_id                 │  │
│  │  ParagraphStyle + non-empty SourceLocation         │  │
│  │  SourceFormatId                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │       HierarchyExtractor (SHARED post-processor)    │  │
│  │  Input:  Vec<ParsedBlock>                          │  │
│  │  Output: Vec<HierarchyNode> with levels:            │  │
│  │    Razdel, Glava, Paragraph, Statya, Chast,         │  │
│  │    Punkt, Podpunkt                                 │  │
│  │  Method: regex markers applied to block text        │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │       ReferenceExtractor (SHARED post-processor)    │  │
│  │  Input:  Vec<ParsedBlock>                          │  │
│  │  Output: Vec<Reference> (internal + external)       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │       TemporalMarkerExtractor (SHARED)              │  │
│  │  Input:  Vec<ParsedBlock>                          │  │
│  │  Output: Vec<TemporalMarker>                       │  │
│  │  (entry_into_force, invalidity, secrecy)           │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Key design principles

1. **Format adapters are thin.** Each adapter does ONE thing: read the source
   format and emit `ParsedBlock` records. No hierarchy, no references, no
   temporal markers in adapters. All post-processing is format-independent.

2. **Post-processors are shared.** Hierarchy extraction, reference extraction,
   temporal marker detection, and deontic lexeme detection all operate on
   `ParsedBlock` text content, not on XML. They are identical for all sources.

3. **Style classification is adapter-specific, but maps to a shared enum.**
   Each adapter maps its provider-specific style IDs to the shared
   `ParagraphStyle` enum (Title, BodyText, JurTerm, ProviderComment, etc.).

4. **Provider comments remain classified, not silently deleted.** Adapters emit
   `ProviderComment` blocks so provenance is not lost. Shared legal-text
   post-processors introduced after M133 return no candidates for those blocks.

5. **Bounded Rust rules are the implementation truth.** The shared hierarchy
   extractor supports only `Раздел`, `Глава`, `§` and `Статья` start markers.
   Lexical post-processors use explicit token/phrase grammars and exact decoded
   `TextSpan` values; prior-art regexes and provider topology are not normative.

6. **Candidate outputs do not imply legal conclusions.** A reference mention is
   not a resolved relation or citation, a temporal phrase is not a five-clock
   assignment or applicability fact, and a deontic lexeme is not a
   `NormStatement` or legal effect. Those fields are absent by type.

### Crate layout

```
crates/ln-decode/
├── src/
│   ├── lib.rs
│   ├── domain.rs           # ParsedBlock, SourceLocation, TextSpan, hierarchy types
│   ├── ports.rs            # BlockDecoderPort and legacy HC-05 ports
│   ├── application.rs      # DecodeBlocks and legacy DecodeAndAnchor
│   ├── adapters.rs         # Consultant adapter and legacy synthetic adapters
│   ├── adapters/
│   │   ├── garant_odt_package.rs
│   │   └── garant_odt.rs
│   ├── hierarchy.rs        # shared bounded hierarchy extraction
│   ├── morphology.rs       # shared bounded lexical marker scan
│   ├── sentence.rs         # shared bounded sentence spans
│   ├── references.rs       # article/point mentions without target resolution
│   ├── temporal.rs         # entry/loss-of-force phrases without clock facts
│   └── deontic.rs          # morphology projection without NormStatement
└── tests/                  # hostile, integration and tracked real tracers

M134 proves all three candidate modules independently and composes them across
synthetic Consultant/Garant identities plus one tracked real source per
provider. The modules remain shared, import no provider adapters and return no
candidates for `ProviderComment` blocks. The tracked sources are different
legal documents, so their aggregate counts do not prove cross-format parity.
```

### Shared domain types

```rust
/// Non-empty half-open byte range in an explicitly named source byte stream.
pub struct SourceSpan { /* private start/end; try_new validates start < end */ }

/// Validated identity of the byte stream indexed by SourceSpan.
pub struct SourceStreamId { /* e.g. artifact:whole or package-member:content.xml */ }

/// An indivisible source stream identity and byte span.
pub struct SourceLocation { /* private stream/span; no bare ParsedBlock span getter */ }

/// Non-empty half-open byte range in decoded block text.
pub struct TextSpan { /* distinct coordinate system from SourceSpan */ }

/// A parsed paragraph from any source format.
pub struct ParsedBlock {
    // Private fields. `try_new` rejects empty text and invalid provider style IDs.
    // Accessors expose text, optional provider style, shared style, span and format.
}

pub enum ParagraphStyle {
    Title,
    BodyText,
    Heading,
    JurTerm,
    ProviderComment,
    TableCell,
    Unknown,
}

pub enum HierarchyLevel {
    Razdel,
    Glava,
    Paragraph,
    Statya,
    Chast,
    Punkt,
    Podpunkt,
}

pub struct HierarchyNode {
    // Private validated level, number, optional title, text and marker TextSpan.
}
```

These types are `[bounded]` contract evidence only. They do not prove that
either source adapter emits correct offsets or hierarchy. `ParsedBlock` keeps a
`SourceLocation`: Consultant uses `artifact:whole`, while Garant ODT uses
`package-member:content.xml` because decompressed member offsets are not
compressed package offsets. Morphology, sentence and hierarchy markers return
`TextSpan` relative to decoded block text. No automatic cross-stream or
source-to-decoded translation exists. Each adapter must separately prove any
mapping before citation or any future-schema `EvidenceSpan` use; that term remains
`deferred-undefined`. Serialization is not added until a
concrete versioned boundary requires it.

### Format detection

```rust
pub enum SourceFormatId {
    ConsultantWordMl,
    GarantOdt,
}
```

Format validation is adapter-owned because family identity, ZIP signatures and
XML roots are external concerns. `BlockDecoderPort` accepts a bounded
`DecodeRequest` and returns `Result<Vec<ParsedBlock>, BlockDecodeError>`.
`ConsultantWordMlBlockDecoder` and `GarantOdtBlockDecoder` implement it and fail
atomically: malformed input never returns previously collected blocks.

### Hierarchy extraction (shared, format-independent)

The Rust extractor is dependency-free and provider-neutral. It accepts only
bounded start markers `Раздел`, `Глава`, `§` and `Статья`, with decimal numbers
for `§`/`Статья` and decimal or Roman numbers for `Раздел`/`Глава`. `Часть`,
`пункт` and `подпункт` remain unsupported rather than inferred from generic
numbered prose. It returns a decoded-text `TextSpan`; the owning `ParsedBlock`
retains the separate source-stream `SourceLocation`.

Synthetic Consultant and Garant adapter integration contracts feed their
`ParsedBlock` values directly to the same `extract_hierarchy` function. This is
`[bounded]` cross-adapter evidence only: real Consultant marker counts are
fixture-specific, and real Garant hierarchy behavior remains unproven until the
tracked ODT tracer.

### ODT adapter specifics

ODT files are ZIP archives. The bounded adapter contract is:

1. pinned `zip` 8.6.0 with defaults disabled and only Deflate support;
   in-memory intake rejects packages above 16 MiB, more than 16 entries,
   unsafe/duplicate/missing members and `content.xml` above 8 MiB
2. `quick-xml` `NsReader` on bounded in-memory `content.xml` bytes; no
   filesystem extraction
3. Parse only a namespace-verified ODF subset independently of WordML:
   - `<text:p>` → paragraph
   - `text:style-name` attribute → bounded style classification
   - `<text:span>` → nested text
   - `<text:h>` → heading
   - empty `<text:s>` → one to 64 spaces, with a 1 MiB decoded-block cap
4. Reject DTD/entity declarations, malformed or multiple roots, nested blocks,
   unknown `text:*` semantics and non-whitespace text outside a block atomically
5. Preserve evidence-required inline `text:a` content and ignore only empty
   `text:bookmark` anchors; non-empty bookmarks, mismatched inline topology and
   unknown `text:*` semantics remain fail-closed
6. Classify Garant provider-comment styles `s9` and `s9header` as
   `ProviderComment`; do not silently discard them in the adapter

The tracked `law-source/garant/44-fz.odt` tracer is `[bounded]`: two Rust decodes
produce 5,124 identical non-empty blocks and 140 supported hierarchy markers.
This proves one fixture and the required ODF subset only, not full ODF/provider
style coverage, corpus completeness, legal correctness or citation mapping.

```toml
# Cargo.toml additions for ODT support
[dependencies]
quick-xml = "0.36"
zip = { version = "=8.6.0", default-features = false, features = ["deflate-flate2-zlib-rs"] }
```

## Consequences

- **Easier — format independence.** Adding a new source format (e.g., direct
  XML from a government portal) requires only a new adapter that emits
  `ParsedBlock`. All downstream processing is reused.

- **Easier — testable hierarchy.** Regex markers are tested independently of
  XML parsing. Hierarchy tests use plain text strings, not XML fixtures.

- **Easier — provider comment filtering.** Both Consultant and Garant embed
  provider annotations. The shared `ProviderComment` style lets downstream
  processing skip them uniformly.

- **Harder — more types.** `ParsedBlock` and `HierarchyNode` are new domain
  types. The existing `StructuralCandidate` and `EvidenceAnchor` from the
  hostile-case contracts remain as the evidence-bounded output.

- **Harder — ZIP dependency.** ODT support requires the `zip` crate, adding
  a transitive dependency (`flate2`, `miniz_oxide`). This is acceptable for
  a parser crate.

## Russian language morphology strategy

Russian is highly inflected (6 cases, 3 genders, 2 numbers, aspectual verb
system). The parser must handle morphological variation at specific layers.

### Per-layer morphological requirements

| Layer | Linguistic need | Approach | Why not pymorphy2/razdel? |
|-------|----------------|----------|--------------------------|
| I/O adapter | None | N/A | Pure XML/text extraction |
| Hierarchy | Minimal | Dependency-free bounded start-marker grammar | Only `Раздел`, `Глава`, `§`, `Статья` are implemented; broader hierarchy remains open |
| References | HIGH: case forms for structural terms | Explicit bounded token/number grammar | M134 emits article/point mentions and exact decoded spans without target resolution |
| Temporal | Medium: bounded phrase forms | Explicit token-sequence grammar | M134 emits entry/loss-of-force phrases only; dates, five clocks and legal applicability remain future work |
| Deontic | High: modal verb forms and local negation | Existing bounded token dictionary + lexical negation context | M134 emits obligation/permission/prohibition lexemes only; legal modality and `NormStatement` remain future application work |
| Embedding | Implicit | Handled by USER-bge-m3 | Model trained on Russian corpus; morphology handled internally |

### Bounded token scan (implemented contract)

M131 uses a dependency-free Unicode token scan rather than regex or a morphology
library. Exact supported inflection lists classify lexical markers for `статья`,
`пункт`, `обязан`, `вправе` and bounded `запрещ*` forms. Results preserve source
order and exact UTF-8 `TextSpan` offsets within decoded input.

The immediate preceding whitespace-separated token `не` sets a `negated` flag.
Punctuation or distant negation does not. This flag is lexical context only: the
primitive does not infer permission, prohibition, obligation, legal effect or
confidence. Prefix words such as `обязанность` and `пунктуация` do not match.

This is `[bounded]` contract evidence for the primitive only. It does not validate
Russian morphology coverage, NormStatement extraction or real-corpus legal facts.

### Bounded legal sentence spans (implemented contract)

M131 implements a dependency-free source-span splitter with a small explicit
abbreviation list: `ст.`, `п.`, `ч.`, `ред.` and `г.`. It preserves decimal
points and a numeric list marker at the start of the current segment, joins
consecutive terminal punctuation, includes directly adjacent closing quotes or
brackets, trims external whitespace and retains trailing unpunctuated text.

The output contains ordered non-empty decoded-text `TextSpan` values only; it
does not copy or normalize sentence text and makes no original-artifact mapping
claim. This is `[bounded]` rule evidence, not general
Russian sentence segmentation. URLs, initials, broader abbreviations, malformed
punctuation and provider-specific layout require later evidence before adding
rules. No razdel, regex, neural model or external dependency is used.

### Future morphology coverage feedback

Unknown-form collection, hit-rate metrics and cross-format comparison remain
`[proposed]`. They are not implemented in M131 and must not log raw legal text.
Any future feedback surface needs bounded fingerprints/counts, tracked review
fixtures and separate proof before adding forms to the explicit dictionary.

### Why morph-rs is excluded

**morph-rs** (v0.2.0, March 2024) is the closest Rust analog to pymorphy2.
It provides dictionary-based morphological analysis using OpenCorpora data.
However:

1. **License: Kribrum-NC** (Non-Commercial). Even as an optional dependency,
   this introduces license complexity incompatible with a potential future
   commercial use of law-nexus.
2. **Low activity:** no significant updates after the 0.2.0 release.
3. **Unnecessary for the bounded primitive:** explicit token forms cover the
   current marker contract; full morphological analysis is not yet justified.
4. **OpenCorpora dictionary licensing:** the dictionary itself has separate
   LGPL-style terms that add complexity.

If morph-rs proves necessary in the future for graph node normalization
(lemmatization for deduplication), it can be added as an optional feature
flag `morphology` behind a separate license review. The default build must
remain dependency-light and NC-free.

### Current morphology module

```text
crates/ln-decode/
├── src/morphology.rs
└── tests/morphology_contract.rs
```

The module uses only the Rust standard library and the decoded-text `TextSpan`
domain type. No regex, once_cell, morph-rs, pymorphy2, natasha or razdel
dependency is introduced. Sentence splitting and hierarchy extraction are
already separate bounded modules. M134 keeps references, temporal phrases and
deontic lexemes in separate modules so one taxonomy cannot silently authorize
another. Synthetic cross-provider equality and tracked aggregate censuses prove
composition mechanics only; M135 delivers bounded golden pipeline mechanics below.

### Golden pipeline boundary (M135)

M135 adds a Rust-only golden pipeline that evaluates parser output against
human-reviewed structural annotations. The boundary is explicit:

1. **Golden fixtures are structural annotations, not legal interpretation.**
   A fixture carries provider, source identity and expected decoded
   `TextSpan` values for hierarchy markers, reference mentions, temporal
   phrases and deontic lexemes. It contains no resolved target identity,
   five-clock fact, `NormStatement`, citation authority or legal effect.

2. **GoldenEvaluator metrics are parser quality, not legal correctness.**
   Per-layer precision, recall and F1 measure exact decoded `TextSpan`
   agreement between parser output and fixture annotations. They do not
   validate legal meaning, citation mapping or corpus coverage.

3. **Unknown-form collector is bounded discovery, not completeness.**
   It emits typed unknown-form kinds, counts and deterministic fingerprints
   over tracked fixtures without persisting raw legal text. It is coverage
   gap evidence, not exhaustive corpus proof.

4. **ADR-0013 `[bounded]`→`[validated]` promotion is gated on representative
   real corpus end-to-end evidence.** Synthetic metrics alone cannot promote
   the lifecycle. Promotion requires multiple tracked fixtures per provider,
   deterministic quality metrics and explicit unknown-form reporting.

Golden pipeline modules consume `ParsedBlock` and validated structural
annotations. They import no provider adapters, storage, graph, retrieval,
citation modules or Python product logic. `ProviderComment` blocks produce no
golden annotations or unknown-form candidates.

## Alternatives Considered

### Option A: Separate crates per format (`ln-consultant`, `ln-garant`)

**Pros:** maximum isolation.
**Cons:** duplicates `ParsedBlock`, `HierarchyNode`, and all shared
post-processing. Violates DRY for shared hierarchy/reference/temporal logic.

### Option B: Serde deserialization with typed structs per format

**Pros:** type-safe, declarative.
**Cons:** WordML and ODF are complex schemas with hundreds of element types.
Full serde structs would be over-engineered for extracting paragraphs and
text. Manual streaming is faster and simpler for our use case.

### Option C: Preprocess to a common XML format, then parse once

**Pros:** single parser path.
**Cons:** adds a transformation step, doubles memory for large files, and
the transformation is just as complex as parsing directly. Not worth it.

## Parser Enhancement Amendments (2026-08-14)

### YAML-driven sub-article markers

The decoder now extracts numbered-list patterns as hierarchy markers
alongside explicit prefixes. YAML `decode_numbered_markers` config:
Chast=digit+".", Punkt=digit+")", Podpunkt=letter_cyrillic+")".
Compound numbers (4.1, 4.1.2) supported via YAML `allow_compound: true`.
435-ФЗ: 22→119 markers (97 sub-article candidates filtered by registry).

### XML entity decoding

`&#167;` (§) correctly decodes to U+00A7 via quick_xml `unescape()`.
Paragraph markers (`§ 1. Общие положения`) extracted via `Paragraph: ["§"]`
prefix rule. 44-ФЗ Chapter 3 has 9 paragraph markers, all correctly decoded.

### HierarchyMarker.title accessor

`HierarchyMarker` now exposes `title()` for TextVersionEvent construction.
Enables `build_text_log_from_markers` → `resolve_ctv` pipeline.

## Non-claims

- `HierarchyMarker` / `map_hierarchy_marker` is a **fail-closed candidate lift**:
  unmapped markers are `Unknown`; number+level does not mint ComponentConcept,
  force, Expression presence, or legal fact. Parser output remains a candidate.

- **EditionSnapshot ≠ AST (Review 4 R4-06).** Decode emits blocks, hierarchy
  markers, reference mentions and temporal phrases. That observation is not
  `StructuralAst`, not membership attach, and not `resolve_CTV`. Marker
  prefixes and number styles live in YAML (`DecodePrefixCatalog`); decode
  must not depend on `ln-kb-ontology`.
- **Consultant WordML and Garant ODT remain independent oracles.** A fixture,
  style map or failure expectation from one provider must not close Unknown
  on the other. A change-overview / «обзор изменений» is C2hint inventory,
  not an amending-act event log.

- Bounded adapters and lexical candidates are not legal facts or complete parser quality.
- Consultant/Garant parity and corpus completeness are not claimed.
- NormStatement/deontic candidates are not validated normative content.

## References

- **ADR-0005** — crate structure proposal (this ADR refines the parser section)
- **ADR-0004** — Rust migration decision
- `Old_project/sources/consultant_word2003xml.yaml` — source format config prior art
- `Old_project/structures/44fz.yaml` — hierarchy markers prior art
- `Old_project/parsing_prompt.yaml` — extraction rules prior art
- Real source files: `law-source/consultant/*.xml`, `law-source/garant/*.odt`
- `crates/ln-decode/src/adapters.rs` — existing WordMLStreamingDecoder
