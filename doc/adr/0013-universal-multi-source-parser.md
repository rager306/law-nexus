---
id: ADR-0013
title: Universal multi-source parser architecture for Russian legal documents
status: Accepted
lifecycle: "[proposed]"
date: 2026-07-24
superseds: none
related: [ADR-0004, ADR-0005]
---

# ADR-0013: Universal multi-source parser architecture

## Status

**Accepted [proposed]** — architecture designed. Moves to `[bounded]` when both
Consultant XML and Garant ODT adapters parse real documents into the shared
domain types with passing tests.

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
│  │           SourceFormat trait (NEW)                  │  │
│  │  fn detect(path) -> Option<Self>                   │  │
│  │  fn decode(reader) -> Vec<ParsedBlock>             │  │
│  │  fn format_id() -> &'static str                   │  │
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
│  │  text: String                                      │  │
│  │  style_id: String                                  │  │
│  │  style_classification: ParagraphStyle              │  │
│  │  byte_offset: (start, end)                        │  │
│  │  source_format: SourceFormatId                     │  │
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

4. **Provider comments are filtered.** Garant embeds ГАРАНТ annotations in
   styled paragraphs. These must be classified as `ProviderComment` and excluded
   from legal text extraction.

5. **Regex-based hierarchy markers are the source of truth.** Russian legal
   documents follow standardized textual markers ("Глава N", "Статья N",
   "1.", "1)", "а)"). These markers are format-independent.

### Crate layout

```
crates/ln-decode/
├── src/
│   ├── lib.rs
│   ├── domain.rs           # ParsedBlock, ParagraphStyle, HierarchyNode, ...
│   ├── ports.rs            # SourceFormat trait
│   ├── application.rs      # DecodeAndAnchor (existing)
│   ├── adapters/
│   │   ├── mod.rs          # re-exports
│   │   ├── wordml.rs       # Consultant WordML adapter (existing, refactored)
│   │   ├── odt.rs          # Garant ODT adapter (new)
│   │   └── synthetic.rs    # Legacy synthetic adapters for HC-05 tests
│   ├── hierarchy.rs        # HierarchyExtractor (shared)
│   ├── references.rs       # ReferenceExtractor (shared)
│   ├── temporal.rs         # TemporalMarkerExtractor (shared)
│   └── deontic.rs          # DeonticLexemeDetector (shared)
└── tests/
    ├── hc05_decode_anchor.rs
    ├── hc05_hostile_decoder.rs
    ├── wordml_real_fixture.rs   # Real Consultant XML tests
    └── odt_real_fixture.rs      # Real Garant ODT tests
```

### Shared domain types

```rust
/// A parsed paragraph from any source format.
pub struct ParsedBlock {
    pub text: String,
    pub style_id: String,
    pub style: ParagraphStyle,
    pub byte_range: (usize, usize),
    pub source_format: SourceFormatId,
}

/// Shared paragraph style classification.
pub enum ParagraphStyle {
    Title,           // Document title
    BodyText,        // Normal legal text body
    Heading,         // Chapter/section heading
    JurTerm,         // Legal term definition
    ProviderComment, // ГАРАНТ/Consultant annotation (filtered)
    TableCell,       // Table content
    Unknown,
}

/// Hierarchy level in Russian legal acts.
pub enum HierarchyLevel {
    Razdel,     // Раздел
    Glava,      // Глава
    Paragraph,  // § Параграф (optional, only in some chapters)
    Statya,     // Статья
    Chast,      // Часть (numbered: "1.", "2.")
    Punkt,      // Пункт (numbered: "1)", "2)")
    Podpunkt,   // Подпункт (lettered: "а)", "б)")
}

pub struct HierarchyNode {
    pub level: HierarchyLevel,
    pub number: Option<String>,
    pub title: Option<String>,
    pub text: String,
    pub byte_range: (usize, usize),
}
```

### Format detection

```rust
pub enum SourceFormatId {
    ConsultantWordML,
    GarantODT,
}

pub trait SourceFormat: Send + Sync {
    /// Detect format from file extension or content signature.
    fn detect(path: &Path) -> Option<Self> where Self: Sized;

    /// Decode source into parsed blocks.
    fn decode(&self, source: &mut dyn BufRead) -> Vec<ParsedBlock>;

    /// Return the format identifier.
    fn format_id(&self) -> SourceFormatId;
}
```

### Hierarchy extraction (shared, format-independent)

Regex markers derived from `Old_project/structures/44fz.yaml` and validated
against real documents:

```rust
pub static CHAPTER_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^Глава\s+(\d+)\.?\s*(.*)$").unwrap()
});

pub static ARTICLE_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^Статья\s+(\d+(?:\.\d+)?)\.?\s*(.*)$").unwrap()
});

pub static PART_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^(\d+)\.\s").unwrap()
});

pub static ITEM_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^(\d+(?:\.\d+)*)\)\s").unwrap()
});

pub static SUBITEM_RE: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"^([а-яё])\)\s").unwrap()
});
```

### ODT adapter specifics

ODT files are ZIP archives. The adapter needs:

1. `zip` crate dependency for reading `content.xml` from the archive
2. `quick-xml` `NsReader` on the extracted `content.xml`
3. Parse ODF elements:
   - `<text:p>` → paragraph (like `<w:p>`)
   - `text:style-name` attribute → style classification
   - `<text:span>` → text runs (like `<w:r><w:t>`)
   - `<text:h>` → heading elements
4. Filter Garant provider comments (style names s9, s9header)

```toml
# Cargo.toml additions for ODT support
[dependencies]
quick-xml = "0.36"
zip = "2.1"
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

## References

- **ADR-0005** — crate structure proposal (this ADR refines the parser section)
- **ADR-0004** — Rust migration decision
- `Old_project/sources/consultant_word2003xml.yaml` — source format config prior art
- `Old_project/structures/44fz.yaml` — hierarchy markers prior art
- `Old_project/parsing_prompt.yaml` — extraction rules prior art
- Real source files: `law-source/consultant/*.xml`, `law-source/garant/*.odt`
- `crates/ln-decode/src/adapters.rs` — existing WordMLStreamingDecoder
