# Changelog

All notable changes to law-nexus are documented in this file.

## M161 (complete)

### S01: Retrieval ranking semantic honesty
- Replaced the fake retrieval cascade with real cosine-similarity ranking
- `InMemoryVectorStore::query` now ranks by cosine similarity to the query vector (was: truncate-by-BTreeMap-key, ignoring the query vector)
- `RetrievalGate::retrieve` now assigns real per-result cosine scores and sorts results descending (was: constant `score = 1.0`)
- New pure `cosine_similarity` helper in ln-storage (scale-invariant, zero-norm=0, negative-clamped to [0,1] relevance)
- TDD: similarity contract (8), adapter ranking (3 incl. dimension-mismatch fail-closed), gate ranking (4 incl. hostile constant-score regression)
- VectorStorePort contract unchanged; blast radius LOW (RetrievalGate has 0 upstream callers)
- Lifecycle: `[bounded]` InMemory/vector-returning-adapter path; real ANN adapters (RuVector) need future scored-query port evolution

## M160 (complete)

### S01: Verify test CI coverage and governor test-coverage drift
- test_verify_adr_conformance and test_verify_repository_pre_commit_hook in CI
- Governor check `verify-test-coverage-drift` detects drift

### S02: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M159 (complete)

### S01: Architecture generator tests in CI
- 6 test files (159 tests) added to CI process suite and quality-gate inventory
- ci-quality-gate-drift stays green with process_suite=18

### S02: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M158 (complete)

### S01: Governor CI quality-gate drift anti-drift check
- Governor finding `ci-quality-gate-drift`
- Detects pre-commit hook / CI process suite / inventory script drift

### S02: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M157 (complete)

### S01: Live-adapter readiness governor and CI wiring
- Governor finding `live-adapter-readiness`
- CI process suite + inventory scripts include readiness

### S02: Cargo clippy quality-gate landing
- Pre-commit and CI: `cargo clippy --workspace --offline --all-targets -- -D warnings`
- Quality-gate inventory active checks include clippy; removed from future_additions

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M156 (complete)

### S01: CI process suite expansion and quality-gate honesty
- CI process-only suite includes preflight, quality-gate, inventory verifier tests
- Report-only inventory script steps in CI
- Quality-gate inventory `ci_process_suite` / `ci_inventory_scripts` honesty

### S02: Live adapter readiness report-only process surface
- `verify-live-adapter-readiness.py`: TEI `stub_transport_only`, RuVector `proposed`
- Overclaim scan; no live HTTP

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M155 (complete)

### S01: WordMLStreamingDecoder shared DecoderPort suite
- Fixture-aware honest DecoderPort contract entrypoint
- WordMLStreamingDecoder exercises shared suite on structural fixture

### S02: Multi-adapter real-port inventory and governor advisory
- `verify-multi-adapter-port-coverage.py` + governor `multi-adapter-port-coverage`
- Residual real multi-adapter gaps: 0 after WordML suite

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M154 (complete)

### S01: ADR-0015 stale non-claims honesty repair
- Critical ceiling and Non-claims no longer deny landed ln-testkit/allowlist
- TEI/RuVector/product non-claims preserved

### S02: BlockDecoderPort shared family-isolation suite
- Consultant WordML + Garant ODT pass shared own-family / foreign-family contract
- No cross-provider golden coupling; synthetic fixtures only

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M153 (complete)

### S01: Admission and closure residual hostile shared negatives
- BoundObservationPort honest + HostileVendorCapacity negative
- DependencyEvidencePort honest + HostileProgressCompleteness negative
- Allowlist 44 edges; hostile inventory gaps 4→2

### S02: Projection and work residual hostile shared negatives
- RebuildExecutorPort honest + HostileAuthoritativeExecutor negative
- DomainEvidencePort honest + HostileMutatingEvidence negative
- Allowlist 46 edges; hostile inventory 14/14 status ok; governor pass

### S03: Docs validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M152 (complete)

### S01: Hostile adapter inventory and governor advisory
- `scripts/verify-hostile-negative-suite-coverage.py` inventory (mention-based)
- Governor finding `hostile-negative-suite-coverage` (debt = non-blocking warn)

### S02: EmbeddingPort shared contract for TEI stub transport
- `assert_embedding_port_contract` + TeiEmbeddingAdapter stub transport suite
- Honest embed + model/dimension/non-finite/transport rejection (not live TEI)

### S03: Publish and relation hostile shared negatives
- HostileDualWriterLedger fails honest publication suite
- OpenRelationHostileRegistry illicit unknown-predicate storage surface
- Hostile inventory gaps shrink 6→4 remaining

## M151 (complete)

### S01: Governor-native port-contract coverage check
- Governor finding `port-contract-coverage` (debt = non-blocking warn; crash = error)
- Full coverage pass includes explicit bounded non-claim (not TEI/RuVector/product readiness)
- Preflight pass message matches the evidence ceiling

### S02: Strict-gate wording and evidence-ceiling docs refresh
- Quality-gate `future_additions` no longer implies remaining uncovered InMemory adapters
- ADR-0015 records governor-native coverage trajectory

### S03: Validation and terminal closure
- Structured UAT PASS; terminal projections closed

## M150 (complete)

### S01: Accelerate and conformance shared contracts
- AccelerationLedgerPort honest + HostileLabelMutator negative
- ConformanceOraclePort honest + HostileVerdictInflator negative
- Allowlist 39 edges

### S02: Dispose disposition and promotion gate shared contracts
- DispositionStorePort and PromotionGatePort suites
- Allowlist 40 edges

### S03: Relation and replay shared contracts
- RelationRegistryPort closed-registry suite
- CheckpointPort and EffectLedgerPort suites + HostileDuplicateEffectLedger negative
- Allowlist 42 edges; coverage inventory 22/22 covered (bounded port suites only)

## M149 (complete)

### S01: Inventory store and visibility shared contracts
- InventoryStorePort append-only history suite
- VisibilityPort inventory/review surface suite
- Allowlist 34 edges (`ln-testkit` → `ln-inventory`)

### S02: Gate and identity store shared contracts
- CandidateStorePort honest + InPlaceMutatingHostile negative
- IdentityStorePort honest + ErasingMergerHostile negative
- Allowlist 36 edges

### S03: Temporal clock evidence shared contract
- ClockEvidencePort present/missing anchor suite
- Allowlist 37 edges; coverage covered 15 / uncovered 7 / discovered 22

## M148 (complete)

### S01: Crate-qualified port-contract coverage identity
- Inventory schema v2 keys adapters as `crate::StructName`
- Same-named `InMemoryDiagnosticSink` across crates counted separately
- Discovered 22 / uncovered 16 after identity fix (was collapsed to 20/14)

### S02: Decode decoder and diagnostic shared contracts
- `ln-testkit`: honest DecoderPort suite + malicious decoder negative
- Decode `InMemoryDiagnosticSink` record/events suite
- Allowlist 31 edges (`ln-testkit` → `ln-decode`)

### S03: Observe and diagnostic sink shared contracts
- WorkStatePort + observe DiagnosticPort suites
- DiagnosticSinkPort honest allowlist + HostileCanary negative
- `DiagnosticCode::new` public for shared fixtures
- Allowlist 33 edges; coverage covered 10 / uncovered 12 / discovered 22

## M147 (complete)

### S01: Advisory preflight for port-contract coverage debt
- Preflight check `port-contract-coverage` runs inventory script
- Remaining InMemory debt yields warn (status ok); script crash fails closed
- Strict gate deferred to `future_additions`

### S02: Query state shared port contract
- `ln-testkit`: honest QueryStatePort suite + HostileGapInventor negative
- Allowlist 29 edges (`ln-testkit` → `ln-query`)
- Coverage covered set 5

### S03: Publication ledger shared port contract
- `ln-testkit`: PublicationLedgerPort store-level suite for InMemory
- Allowlist 30 edges (`ln-testkit` → `ln-publish`)
- Coverage covered 6 / uncovered 14 / discovered 20

### S04: Docs validation and terminal closure
- CHANGELOG and ADR-0015 updated; structured UAT PASS; terminal projections closed

## M146 (complete)

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

### S04: Docs CHANGELOG and ADR follow-on sync
- CHANGELOG and ADR-0015 follow-ons updated honestly

### S05: Validation and terminal closure
- Structured UAT PASS; M146 formally complete; terminal projections closed

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
