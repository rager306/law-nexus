# Changelog

All notable changes to law-nexus are documented in this file.

## M137 (in progress)

### S01: Tokenizer dedup and dead code audit
- Extracted shared `tokenizer.rs` module in `ln-decode` replacing 4 duplicate copies
- Removed `struct Token` + `fn tokens()` from `morphology.rs` (internal, behavior preserved)
- Removed `struct WordToken` + `fn words()` from `references.rs` (internal, behavior preserved)
- Removed `struct WordToken` + `fn words()` from `temporal.rs` (internal, behavior preserved)
- Removed `struct Token` + `fn tokens()` from `unknown_forms.rs` (internal, behavior preserved)
- All existing tests pass unchanged; zero external dependencies added
- Dead code audit: no warnings found
- Doc consistency: ADR-0014, ARCHITECTURE, roadmap all current

## M136 (complete)

### S01: Storage port contract boundaries
- D139 authority ceiling: storage ports are law-nexus-owned trait definitions
- ADR-0014 M136 storage port contracts section added
- External dependencies gated on port proof and license verification

### S02: Storage port trait contracts
- New crate `ln-storage` with zero external dependencies
- `EmbeddingPort`, `VectorStorePort`, `GraphStorePort` trait definitions
- Validated request/response types with construction-time validation
- 10 hostile tests

### S03: TEI embedding adapter
- `TeiEmbeddingAdapter` behind `EmbeddingPort` with injectable `EmbeddingTransport`
- Model identity, dimension and finiteness fail-closed boundaries
- 8 hostile tests, zero external dependencies

### S04: In-memory adapters with operation journal
- `InMemoryVectorStore` and `InMemoryGraphStore` implementing storage ports
- `OperationJournal` with deterministic replay after simulated crash
- 7 hostile tests, zero external dependencies

### S05: Retrieval/citation gate composition
- `RetrievalGate` composing all three storage ports
- `Citation` with traceable source spans and tamper detection
- Graph store metadata enrichment via `evidence_labels`
- 6 hostile tests, zero external dependencies

### S06: Validation and terminal closure
- Structured UAT PASS (4 checks, 31 tests total)
- ADR-0014 remains `[proposed]`; real TEI/RVF/redb gates unproven
- M136 formally complete, terminal projections closed

## M135 (complete)

### S01-S06: Rust golden pipeline
- `GoldenFixture`, `GoldenSource`, `GoldenAnnotation` manifest types
- `GoldenEvaluator` with per-layer precision/recall/F1
- `UnknownFormCollector` with bounded near-miss dictionaries
- Tracked real fixture enrichment evidence
- Self-consistent P=R=F1=1.0 pipeline composition proof
- ADR-0013 remains `[bounded]`; human-reviewed golden annotations deferred

## M134 (complete)

### S01-S06: Shared lexical extractors
- `ReferenceMention` extractor (статья/пункт + decimal/dotted numbers)
- `TemporalPhrase` extractor (вступает/утрачивает силу)
- `DeonticLexeme` projection (обязан/вправе/запрещается)
- Cross-provider integration and tracked real census evidence
- D137 lexical candidate authority ceiling
- ADR-0013 promoted to `[bounded]`

## M133 (complete)

### S01-S06: Garant ODT adapter
- Bounded in-memory ODT package intake (`zip = "=8.6.0"`)
- Independent `GarantOdtBlockDecoder` behind `BlockDecoderPort`
- `SourceStreamId` and `SourceLocation` coordinate authority
- Real Garant ODT tracer with deterministic 5124-block census

## M132 (complete)

### S01-S05: Consultant WordML adapter
- `ConsultantWordMlBlockDecoder` behind `BlockDecoderPort`
- Shared bounded hierarchy extraction (Раздел, Глава, §, Статья)
- Real Consultant XML tracer with deterministic 167-block census

## M131 (complete)

### S01-S03: Parser domain foundation
- `ParsedBlock`, `TextSpan`, `SourceSpan`, `SourceLocation` domain types
- `BlockDecoderPort` and `DecodeRequest`/`BlockDecodeError`
- Bounded morphology (`find_legal_markers`) and sentence splitting
