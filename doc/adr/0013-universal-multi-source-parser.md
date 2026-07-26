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
│  │  ParagraphStyle + non-empty SourceSpan             │  │
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
/// Non-empty half-open byte range in the original source artifact.
pub struct SourceSpan { /* private start/end; try_new validates start < end */ }

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
    // Private validated level, number, optional title, text and SourceSpan.
}
```

These M131 types are `[bounded]` contract evidence only. They do not prove that
either source adapter emits correct offsets or hierarchy. Serialization is not
added until a concrete versioned boundary requires it.

### Format detection

```rust
pub enum SourceFormatId {
    ConsultantWordMl,
    GarantOdt,
}
```

Format detection is adapter-owned because paths, extensions, ZIP signatures and
XML roots are external concerns. A future port accepts bounded input and returns
`Result<Vec<ParsedBlock>, AdapterError>`; it must not silently return partial
records on malformed input. M131 intentionally defines no I/O trait before the
Consultant and Garant adapter contracts are planned.

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

## Russian language morphology strategy

Russian is highly inflected (6 cases, 3 genders, 2 numbers, aspectual verb
system). The parser must handle morphological variation at specific layers.

### Per-layer morphological requirements

| Layer | Linguistic need | Approach | Why not pymorphy2/razdel? |
|-------|----------------|----------|--------------------------|
| I/O adapter | None | N/A | Pure XML/text extraction |
| Hierarchy | Minimal | Pure regex | Markers ("\u0413\u043b\u0430\u0432\u0430 N", "\u0421\u0442\u0430\u0442\u044c\u044f N") are standardized, always nominative case |
| References | HIGH: 6 cases for "\u0441\u0442\u0430\u0442\u044c\u044f" | Stem-based regex | One pattern `\u0441\u0442\u0430\u0442\u044c[\u044c\u044f\u0435\u0439\u0451\u044e\u044c\u044e\u044e]` covers all case forms; no lemmatization needed |
| Temporal | Medium: verb forms + date parsing | Stem regex + date parser | Legal verbs are a closed set: "\u0432\u0441\u0442\u0443\u043f\u0430\u0435\u0442/\u0432\u0441\u0442\u0443\u043f\u0430\u044e\u0442/\u0432\u0441\u0442\u0443\u043f\u0438\u043b" |
| Deontic | MAXIMAL: modal verb morphology | Stem dictionary + negation context | Legal modality set is closed: "\u043e\u0431\u044f\u0437\u0430\u043d", "\u0432\u043f\u0440\u0430\u0432\u0435", "\u0437\u0430\u043f\u0440\u0435\u0449\u0430\u0435\u0442\u0441\u044f" + gender/number variants |
| Embedding | Implicit | Handled by USER-bge-m3 | Model trained on Russian corpus; morphology handled internally |

### Stem-based regex (primary approach)

Instead of full morphological analysis (pymorphy2) or rule-based tokenization
(razdel), the parser uses Unicode-aware regex patterns `[proposed]` that cover all
morphological variants of legal markers with single patterns:

```rust
// "\u0441\u0442\u0430\u0442\u044c\u044f" in all 6 cases:
// \u0441\u0442\u0430\u0442\u044c[\u044c\u044f\u0435\u0439\u0451\u044e] covers: \u0441\u0442\u0430\u0442\u044c\u044f, \u0441\u0442\u0430\u0442\u044c\u0438, \u0441\u0442\u0430\u0442\u044c\u0435, \u0441\u0442\u0430\u0442\u044c\u0439, \u0441\u0442\u0430\u0442\u044c\u0451\u0439, \u0441\u0442\u0430\u0442\u044c\u044e
static STATYA_RE: &str = r"(?i)\u0441\u0442\u0430\u0442\u044c[\u044c\u044f\u0435\u0439\u0451\u044e]\s+(\d+(?:\.\d+)*)";

// Modal verbs in all gender/number forms:
// \u043e\u0431\u044f\u0437\u0430\u043d, \u043e\u0431\u044f\u0437\u0430\u043d\u0430, \u043e\u0431\u044f\u0437\u0430\u043d\u043e, \u043e\u0431\u044f\u0437\u0430\u043d\u044b
static OBLIGATION_RE: &str = r"\u043e\u0431\u044f\u0437\u0430\u043d(?:\u0430|\u043e|\u044b)?";
```

### Sentence splitting: custom LegalSentenceSplitter

No razdel equivalent exists in Rust. A custom rule-based sentence splitter
handles the specific challenges of Russian legal text:

- Abbreviations that mimic sentence boundaries: \u0441\u0442., \u043f., \u0447., \u0440\u0435\u0434., \u0433., \u0420\u0424, \u0424\u0417
- Decimal numbers with periods: 5.1, 44-\u0424\u0417
- Nested numbering: 1), 1.1)
- Cyrillic quotation marks: \u00ab\u00bb

Implementation: ~50 lines of rule-based logic with a HashSet of legal
abbreviations. No external dependency. No neural model. razdel solves a broader
problem (literary text, dialogues, URLs) that legal documents do not need.

### Self-improvement of morphological coverage

The parser includes a feedback loop for morphological gaps:

1. **Unknown form collector:** when a deontic/reference regex fails to match a
   sentence that clearly contains a legal marker, the unmatched text is logged.
2. **Marker hit-rate metrics:** track match rate per regex per document.
3. **Periodic review:** logged unknown forms are reviewed; new stem patterns
   are added to the regex dictionary.
4. **Cross-format validation:** the same law parsed from both Consultant XML and
   Garant ODT must produce the same hierarchy tree; diffs reveal morphology gaps.

### Why morph-rs is excluded

**morph-rs** (v0.2.0, March 2024) is the closest Rust analog to pymorphy2.
It provides dictionary-based morphological analysis using OpenCorpora data.
However:

1. **License: Kribrum-NC** (Non-Commercial). Even as an optional dependency,
   this introduces license complexity incompatible with a potential future
   commercial use of law-nexus.
2. **Low activity:** no significant updates after the 0.2.0 release.
3. **Unnecessary for extraction:** stem-based regex covers the parser's actual
   need (pattern matching for legal markers), not full morphological analysis.
4. **OpenCorpora dictionary licensing:** the dictionary itself has separate
   LGPL-style terms that add complexity.

If morph-rs proves necessary in the future for graph node normalization
(lemmatization for deduplication), it can be added as an optional feature
flag `morphology` behind a separate license review. The default build must
remain dependency-light and NC-free.

### Module layout for morphology

```
crates/ln-decode/
\u2514\u2500\u2500 src/
    \u251c\u2500\u2500 morphology.rs         # Cyrillic morphology utilities
    \u2502   \u251c\u2500\u2500 stems.rs           # stem_match(word, stem) -> bool
    \u2502   \u251c\u2500\u2500 patterns.rs        # Pre-built regex for \u0441\u0442\u0430\u0442\u044c[\u044c\u044f\u0435\u0439\u0451\u044e], \u043f\u0443\u043d\u043a\u0442[\u0430\u0443\u043e\u043c\u044b], etc.
    \u2502   \u2514\u2500\u2500 negation.rs        # detect_negation(text, pos) -> bool
    \u251c\u2500\u2500 sentence_split.rs     # LegalSentenceSplitter
    \u2502   \u251c\u2500\u2500 abbreviations.rs   # HashSet of legal abbreviations
    \u2502   \u2514\u2500\u2500 rules.rs           # Rule-based boundary detection
    \u251c\u2500\u2500 hierarchy.rs           # Pure regex, no morphology
    \u251c\u2500\u2500 references.rs          # Stem patterns + sentence split
    \u251c\u2500\u2500 temporal.rs            # Verb-form regex + date parser
    \u2514\u2500\u2500 deontic.rs             # Modal stem dictionary + negation
```

Dependencies remain minimal:

```toml
[dependencies]
quick-xml = "0.36"
zip = "2.1"
regex = "1"
once_cell = "1"
```

No morph-rs. No pymorphy2. No natasha. No razdel. Full control.

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
