# Changelog

All notable changes to law-nexus are documented in this file.

## M146 (in progress)

### S01: Citation source shared port contract
- `ln-testkit`: `assert_citation_source_contract` for honest resolve/missing/authority preservation
- Negative suite: HostileMirrorRelabeler fails honest Mirror→Official preservation
- InMemoryCitationSource passes shared suite

### S02: Promotion store shared port contract
- `ln-testkit`: `assert_promotion_store_contract` for commit visibility, idempotent put, cancel clearing
- InMemoryPromotionStore passes shared suite
- Crate allowlist: 28 edges (`ln-testkit` → storage/citation/promote)

### S03: InMemory port-contract coverage inventory
- `scripts/verify-port-contract-coverage.py` report-only inventory
- Covered 4 / uncovered 16 / discovered 20 InMemory adapters
- `--strict` fails while debt remains; default does not block gates

## M145 (complete)

### S01: Executable crate dependency allowlist
- Added `prd/architecture/crate-dependency-allowlist.json` (26 workspace path edges)
- Added `scripts/verify-crate-dependency-allowlist.py` via `cargo metadata`
- Tests cover undeclared edges, stale edges, capability→HC runner and capability→CLI bans

### S02-S03: ln-testkit shared storage port contracts
- Added `crates/ln-testkit` with VectorStorePort and GraphStorePort contract helpers
- InMemory adapters exercise the shared suite from ln-testkit tests
- One-way dependency only: `ln-testkit -> ln-storage` (no reverse dev-dep)

### S04: Gate wiring and docs
- Preflight check `crate-dependency-allowlist`
- Pre-commit + CI + quality-gate inventory wired to allowlist script

## M144 (complete)

### S01: Write ADR-0015 verification architecture
- Added `doc/adr/0015-hexagonal-verification-architecture.md`
- Overlapping contours, port-contract policy, lifecycle honesty, anti-slop rules
- Explicit non-claims for unbuilt testkit/allowlist/real-adapter infrastructure
- ADR index updated

### S02: Align Rust verification matrix to ADR-0015
- Updated `.agents/skills/law-nexus-rust/references/verification-matrix.md`
- Contours, port-contract rules, lifecycle/non-claims, anti-slop checks

### S03: Bind concrete testing rules in AGENTS.md
- Local `AGENTS.md` testing contract (gitignored overlay by project policy)
- Always/never rules and change-class minimum proof table
- Corrected active architecture note: Python product is archived prior art
- Tracked skill entrypoint binds ADR-0015 in S04

### S04: Docs sync CHANGELOG and decision record
- Decision D140 recorded
- Tracked skill entrypoint cites ADR-0015
- CHANGELOG synchronized; gates clean after reindex

### S05: Validation and terminal closure
- Structured UAT PASS; M144 formally complete; terminal projections closed

## M143 (complete)

### S01: Archive orphan residual scripts
- Archived 19 residual scripts with zero active test or control-plane consumers
- Active scripts: 87; archived product scripts: 56
- Active pytest remains green: 1398 passed, 2 skipped

### S02: Remove dead import-linter dependency
- Removed unused `import-linter` from active dev dependencies after onion gate removal
- Refreshed `uv.lock`

### S03: Release build baseline and CLI smoke
- `cargo build -p ln-product-cli --release --offline` PASS
- Release health ok
- Consultant release inspect avg 11.7ms / 167 blocks; Garant avg 186.5ms / 5124 blocks
- Evidence: `prd/migration/rust-evidence/probes/m143-release-baseline.{json,md}` `[bounded]`
- No production packaging claim

### S04: Docs verification and CHANGELOG
- CHANGELOG synchronized; gates green after reindex

### S05: Validation and terminal closure
- Structured UAT PASS; M143 formally complete; terminal projections closed

## M142 (complete)

### S01: Repair active CI and quality gate contracts
- Removed dead `uv run lint-imports` and missing `verify-m112-adr-sync.py` CI steps
- Aligned pre-commit cargo path filters, gate inventory and quality-gate tests with harness-only control plane
- Rewrote ARCHITECTURE current layer: Rust product runtime + Python harness + `python_archive/product` prior art

### S02: Archive failing historical residual tests
- Archived 25 residual ACP/FalkorDB/retrieval/parser proof tests that failed on the active tree
- Active pytest: 1398 passed, 2 skipped, 0 failures

### S03: Archive orphan residual scripts
- Archived 8 residual scripts only consumed by archived historical tests
- Active scripts: 106; archived product scripts: 37

### S04: Active hygiene verification and docs
- CHANGELOG synchronized; gates green after reindex

### S05: Validation and terminal closure
- Structured UAT PASS; M142 formally complete; terminal projections closed

## M139 (complete)

### S01: Performance baseline and determinism proof
- CLI inspect latency: Consultant 30ms (167 blocks), Garant 657ms avg (5124 blocks)
- Output deterministic across 3 repeat runs (excluding variable duration_ms)
- Evidence: `prd/migration/rust-evidence/probes/m139-performance-baseline.{json,md}`

### S02: CLI security audit and hostile input tests
- Unsupported format (.txt) rejected as Parse/UnsupportedFamily
- Empty XML file produces zero blocks (not failure)
- Non-existent file rejected as Io/ReadFailure
- Directory as path rejected as Io/ReadFailure
- 4 new hostile tests, total 9 CLI integration tests

### S03: End-to-end acceptance evidence
- Both Consultant and Garant fixtures produce deterministic structured JSON
- Consultant: 167 blocks, 22 hierarchy, 69 refs, 1 temporal, 4 deontic, 29 unknown
- Garant: 5124 blocks, 140 hierarchy, 1882 refs, 36 temporal, 228 deontic, 2144 unknown
- KnowQL composition proven over in-memory adapters
- Evidence: `prd/migration/rust-evidence/probes/m139-end-to-end-acceptance.{json,md}`

### S04: Validation and terminal closure
- Structured UAT PASS (3 checks: CLI hostile tests, evidence portability, real CLI execution)
- M139 formally complete

## M141 (complete)

### S01: Harness boundary false positive fix
- CI harness suite failed because governor historical-only FalkorDB direction matched FORBIDDEN_SOURCE_TERMS
- Allow only historical-only FalkorDB vocabulary; keep product-domain bans
- CI process-only harness suite: 39 passed

### S02: Residual product-dependent tests archival
- Archived 32 residual active tests that hard-loaded M140-archived product scripts
- Active pytest collection: 1768 tests, 0 collection errors, 0 hard hits

### S03: Residual product-dependent scripts archival
- Archived hard-import/load dependency closure: 9 residual scripts + 9 cascading tests
- Active tree: 0 hard hits, 1695 tests collect cleanly, harness 39/39, governor 30/0
- Archived totals under python_archive/product: 29 scripts, 67 tests

### S04: Active collection hygiene and docs
- CHANGELOG and residual archival verified
- Governor 30/0, preflight 6/0 after reindex

### S05: Validation and terminal closure
- Structured UAT PASS; M141 formally complete; terminal projections closed

## M140 (complete)

### S01: Post-M139 debt audit
- Governor 30/0, preflight 6/0, dead code 0, unused 0, stale projections 0
- CHANGELOG corrected: M139 marked complete
- 157 test suites pass, 378 tests total, 23495 lines Rust code

### S02: Python product isolation verification
- Harness (src/law_nexus_harness/): zero imports from product — confirmed
- Tests: 26 files import from law_nexus.*
- Scripts: 20 files import from law_nexus.*
- pyproject.toml: import-linter contracts reference law_nexus.* modules

### S03: Python product archival cutover
- Moved src/law_nexus/ -> python_archive/product/law_nexus/ (62 files)
- Moved 26 dependent test files -> python_archive/product/tests/
- Moved 20 dependent scripts -> python_archive/product/scripts/
- Removed tool.importlinter contracts from pyproject.toml
- Added python_archive to basedpyright exclude
- Added *.egg-info/ to .gitignore
- Excluded python_archive/ from ruff pre-commit hooks
- Removed python-onion-dependencies hook (import-linter config removed)
- Harness (law_nexus_harness) and Rust workspace remain fully functional
- Governor 30/0 after archival

### S04: ADR promotion and docs synchronization
- ADR-0004 promoted to [validated]
- ADR-0005 promoted to [validated]
- Forward roadmap ADR matrix updated

### S05: Validation and terminal closure
- Structured UAT PASS; M140 formally complete; terminal projections closed

### S03: CLI failure state persistence
- Failure JSON now includes `attempt_count`, `fingerprint` (FNV1a64 of error message) and `duration_ms`
- Tests verify all three new fields on truncated-fixture failure path
- Success path contains no failure artifacts

- New crate `ln-product-cli` with binary `law-nexus-inspect`
- Subcommands: `health` (JSON status), `inspect <path>` (decode + extract + KnowQL composition)
- Inspect decodes Consultant XML or Garant ODT through ln-decode adapters
- Runs all four extractors + unknown-form census
- Composes KnowQL FindSimilar over in-memory storage adapters
- Structured JSON output with phase/status/duration_ms/source/result/non_claims
- Exit codes: 0 success, 1 parse failure, 2 usage error
- 5 integration tests

### S01: Tokenizer dedup and dead code audit
- Extracted shared `tokenizer.rs` module in `ln-decode` replacing 4 duplicate copies
- Removed `struct Token` + `fn tokens()` from `morphology.rs` (internal, behavior preserved)
- Removed `struct WordToken` + `fn words()` from `references.rs` (internal, behavior preserved)
- Removed `struct WordToken` + `fn words()` from `temporal.rs` (internal, behavior preserved)
- Removed `struct Token` + `fn tokens()` from `unknown_forms.rs` (internal, behavior preserved)
- All existing tests pass unchanged; zero external dependencies added
- Dead code audit: no warnings found
- Doc consistency: ADR-0014, ARCHITECTURE, roadmap all current

### S02: KnowQL typed AST
- Added `crates/ln-query/src/knowql.rs` with typed KnowQL AST over storage ports
- `KnowQLOp` enum: Embed, FindSimilar, FindByLabel
- `ValidatedOp` with construction-time validation
- `KnowQLResult` typed output
- `execute()` dispatcher over EmbeddingPort + VectorStorePort + GraphStorePort
- 8 hostile tests, ln-query depends on ln-storage for port traits

### S03: KnowQL integration proof
- Integration test decodes tracked Consultant fixture (167 blocks)
- Stores hierarchy annotations through InMemoryVectorStore and InMemoryGraphStore
- Queries back through KnowQL FindSimilar and FindByLabel operations
- Parser-to-storage-to-retrieval composition proven
- ln-query depends on both ln-storage and ln-decode

### S04: Validation and terminal closure
- Structured UAT PASS (3 checks: KnowQL contracts, integration, tokenizer regression)
- M137 formally complete

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
