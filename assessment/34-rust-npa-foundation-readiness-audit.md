# Rust NPA foundation readiness audit

Status: [bounded] code audit and synthetic executable probes, not corpus semantic acceptance.
Reviewed base: `24b8872`. Product source was not changed by the audit. No parked milestone was released.

Remediation update (M221-wbslul S01 T01, S02 T01–T04, S03 T01–T04, S04 T01–T05): F01 is fixed under the new closed code `manifest_identity_mismatch`. F02 is fixed under the new typed `DerivedBoundary` plane and the closed code `derived_separator`. F03's bounded context-consumer/requisites path is closed under S03 (see the F03 closure pointer). F04 and F05 are closed **bounded** under S04 (see the bounded closure pointers below); F06 is closed bounded under S05 (see the F06 closure pointer); this milestone does not release M208/M215–M220.

## Verdict

M214 integrates an executable source-to-analysis/context JSONL path. It does not establish semantic readiness for downstream temporal/retrieval/graph work. Keep M208 and M215-M220 parked pending a foundation remediation and semantic acceptance gate. Milestone completion is not capability acceptance.

## Method and coverage

GitNexus was force-reindexed (`node .gitnexus/run.cjs analyze --force --name law-nexus`); query/context used to trace analysis/verifier flows. codebase-memory-mcp was reindexed for ln-decode (moderate: 6,270 nodes / 37,196 edges) and ln-consultant-parser (full: 1,816 / 7,718), with search and argument-aware data-flow tracing of run_acceptance_with. Decode moderate mode excludes src/bin and tests/fixtures: those are not claimed graph-covered. Graph edges are navigation, not proof: GitNexus reported a suspicious verifier-to-test repo_path edge, so cited findings were checked against source.

Direct execution of existing test binaries: npa_analysis_verify_hostile 11 passed; npa_analysis_context_contract 8 passed; npa_corpus_acceptance_run_contract 14 passed; npa_analysis_export_integration 13 passed. Cargo invocations returned success but captured output only showed Finished; counts above come from direct test-binary execution, not inferred Cargo output.

Probe: `scripts/m214_readiness_probe.rs`. Compile against the matching current ln_decode and serde_json rlibs with rustc --edition=2021, -L dependency=target/debug/deps and explicit --extern paths. Artifact suffixes are environment-dependent. It uses synthetic WordML only. Observed baseline verifier result: true.

## Findings

### F01 HIGH: resealed manifest identity substitution passes verification

`crates/ln-decode/src/npa_analysis_verify.rs:821-1098` recomputes seals and re-derives canonical records but does not compare manifest identity against the supplied pinned parent. `record_map` (751-762) compares record lines, not the manifest. The manifest writer exposes source, source_revision, document_version_ref and parent (`npa_analysis_wire.rs:754-810`).

Executable probe independently changes each of manifest source.sha256, source_revision, document_version_ref and parent.manifest_hash, then recomputes seals. All four modified artifacts return Ok from verify_npa_analysis_wire against the original parent. This permits contradictory provenance between manifest and document record and defeats the claimed source-binding guarantee at the envelope boundary.

Required fix: compare authoritative manifest identity/profile/version/parent fields with the supplied pinned parent; define which policy fields are caller-controlled. Add separate resealed hostile tests for each field and cross-field inconsistencies. Do not accept self-consistent hashes as identity proof.

**Closure pointer (M221-wbslul S01 T01, `manifest_identity_mismatch`).**
- Verifier: `crates/ln-decode/src/npa_analysis_verify.rs` now compares
  `source.sha256`, `source.bytes`, `parent` schema/both seals,
  `document_version_ref`, `source_revision`, `decoder_profile`, `profile` and
  `model` against `SourceMapping::envelope()` / `version()` and the analysis
  frame constants; a resealed substitution is `manifest_identity_mismatch`,
  never `seal_mismatch`. The `document` record family maps to the same code.
- Contract: `prd/architecture/npa-analysis-jsonl-contract.md` §8B.4 adds the
  verifier step and the `manifest_identity_mismatch` row; §12 adds H21/H22.
- Portable proof: `cargo test -p ln-decode --offline --test
  npa_analysis_verify_hostile --test npa_analysis_verify_contract --test
  npa_analysis_export_integration` → 23 + 9 + 13 passed. The F01 probe
  (`scripts/m214_readiness_probe.rs`) now reports `baseline_pass=true` and
  `tamper_source_accepted=false`, `tamper_source_revision_accepted=false`,
  `tamper_document_version_ref_accepted=false`, `tamper_parent_accepted=false`
  (all four as `manifest_identity_mismatch`).
- Acceptance run-contract: `cargo test -p ln-consultant-parser --offline
  --test npa_corpus_acceptance_run_contract --test
  npa_corpus_acceptance_report_contract --test npa_corpus_acceptance_contract
  --test npa_corpus_acceptance_sample_contract` → 11 + 7 + 14 + 9 passed; the
  `VerifyCodeToken` mirror carries the new token.
- Positive control preserved: `untouched_context_envelope_verifies_ok`.

### F02 HIGH: reader-to-analysis bridge deletes control separators

`crates/ln-decode/src/npa_analysis_records.rs:298-360` skips every non-SourceFragment segment and concatenates fragment values. Reader projection preserves controls as DerivedSeparator segments (`reader_projection.rs:902-930`).

Executable WordML probe with `статья<TAB>5<BR>часть<TAB>2` yields analysis text `статья5часть2`. The legal-marker/token context receives a different lexical stream from the visible reader text. The bridge therefore can change meaning before the analyzer runs. This is broader than tokenizer implementation quality.

Required fix: preserve a mapped analysis separator plane (or explicit typed boundaries), without pretending a derived separator has a source-fragment span. Add metamorphic equivalence tests for tab/space/break and run splitting; preserve explicit refusal where a span genuinely cannot be represented. The documented choice to exclude derived segments does not make lexical concatenation semantically safe.

**Closure pointer (M221-wbslul S02 T01–T04, `DerivedBoundary` / `derived_separator`).**
- Blocks: `crates/ln-decode/src/npa_analysis_records.rs` now builds
  `AnalysisBlock::text` as the full ordered concatenation of source-fragment
  segments **and** derived separator literals; derived separators are recorded
  as ordered `DerivedBoundary { kind, block_start, block_end }` values with no
  fragment and no source span. A derived-only view is not a block, so
  `empty_primary_view_is_not_an_analysis_block` is preserved.
- Refusal: `AnalysisBlockLayout::localize` refuses a span that crosses a
  derived boundary as the new closed token `derived_separator`
  (`AnalysisRefusalKind::DerivedSeparator`), checked after
  `unmapped_block`/`invalid_span`/`out_of_bounds` and **before**
  `cross_fragment`; the path is never rebased, never dropped and never promoted
  to a fragment span. `cross_fragment` still fires for a boundary-free
  multi-fragment block.
- Contract: `prd/architecture/npa-analysis-jsonl-contract.md` §8A.3 documents
  the full block text plus typed boundaries and the refusal order; the
  S02-local `AnalysisRefusalKind` list carries `derived_separator`; §12 hostile
  row H23 covers a span crossing a derived separator.
- Tests: `crates/ln-decode/tests/npa_analysis_records_contract.rs` (flip,
  boundary offsets, derived-only negative) and
  `crates/ln-decode/tests/npa_analysis_separator_contract.rs` (metamorphic
  run-splitting, tab/space/br equivalence, mixed-control ordering,
  closed-boundary refusal).
- Portable proof: `cargo test -p ln-decode --offline --test
  npa_analysis_records_contract --test npa_analysis_records_link_classify
  --test npa_analysis_context_contract --test npa_analysis_separator_contract
  --test npa_analysis_verify_hostile --test npa_analysis_verify_contract
  --test npa_analysis_export_integration --test npa_analysis_wire_contract
  --test npa_analysis_wire_context --test npa_analysis_wire_hostile` →
  14 + 9 + 8 + 7 + 23 + 9 + 13 + 9 + 11 + 13 passed, 0 failed;
  `cargo test -p ln-consultant-parser --offline --test
  npa_corpus_acceptance_run_contract --test
  npa_corpus_acceptance_report_contract` → 14 + 7 passed, 0 failed;
  `cargo fmt --all --check` and `cargo check --workspace --offline` exit 0.
- Operator probe: `scripts/m214_readiness_probe.rs` now asserts
  `control_analysis_texts == ["статья\t5\nчасть\t2"]`.
- Non-claims: this is a lexical-boundary fix, not semantic acceptance. Source
  refs stay verifiable, F01 stays closed, F03–F06 stayed open at S02 close (the
  bounded F03 path is closed under S03; F04–F06 remain open), and R1000 stays
  active and unclosed.

### F03 HIGH readiness gap: context family is not full context resolution

`npa_context_records.rs:291-390` always supplies `requisites: None`. `build_requests` (466 onward) emits OpenSeriesHead, ExplicitAnchorLookup and CurrentDocumentRequisites, not all six enum kinds. The synthetic document in the probe emits 5 requests: 2 resolved, 2 partial, 1 unavailable (MissingCurrentRequisites). This is an honest bounded adapter but not evidence of a completed context model.

`analyze_document` runs typed/link/classification before and separately from build_context_records (`npa_analysis_records.rs:977-1004`, `npa_corpus_acceptance.rs:1808 onward`). The new context family is an additional derived output, not demonstrated feedback into final typed/linked/classified decisions. Define the intended consumer semantics before presenting serialized context as analysis completeness.

Required work: authorized current-document requisites path, deliberate trigger policy for each required request kind, expected resolved/partial/unavailable outcomes, and end-to-end tests showing which analysis decisions consume context. Do not enqueue every possible request merely to improve counts.

**Closure pointer (M221-wbslul S03 T01–T04, bounded context-consumer/requisites path, §8C).**
- Contract: `prd/architecture/npa-analysis-jsonl-contract.md` §8C (successor revision,
  `[bounded]`) fixes the producer/consumer boundary, the requisites source and the
  trigger policy per emitted `ContextRequestKind`, plus the closed
  `ThisDocumentReferenceOutcome` token table. §14 lists the S03 verification
  suites. This is a bounded consumer contract: not feedback into
  typed/link/classify, and not legal-semantic acceptance.
- Requisites source: `crates/ln-decode/src/npa_context_records.rs` now derives a
  deterministic `CurrentDocumentRequisites` from the pinned parent's leading
  letterhead (`npa_link::recognize_letterhead` over layout block texts); no
  external sidecar is accepted, and `build_context_records(layout, mapping)` keeps
  its signature, so the verifier re-derivation matches by construction.
- Trigger policy: `current_document_requisites` is emitted once per document and
  only when a this-ref surface exists (`document_context::detect_this_ref_grammar`
  non-empty, evidence `ThisRefGrammarEvidence`); `open_series_head` only for
  proven continuation tails (non-rejected incoming `ContinuesSeries` edge);
  `explicit_anchor_lookup` only for frames whose block has a captured mention;
  `ancestor_path`/`adjacent_blocks`/`scoped_alias` are not emitted. A missing
  surfaced requisites request yields `Unavailable(missing_current_requisites)`; a
  conflicting sidecar yields `partial`/`inherited_field_conflict`; neither is
  promoted to `resolved`.
- Consumer: `crates/ln-decode/src/npa_context_consumer.rs` exposes the closed
  `ThisDocumentReferenceOutcome { Authorized { claim_ref }, Conflicting,
  Unavailable, NotRequested }` and the pure
  `consume_this_document_reference`; mapping is fail-closed (a `Resolved` result
  without a bound, inherited `authorized_current_document_requisites` claim
  degrades to `Conflicting`; worst outcome wins). No variant carries decoded
  text and the consumer does not change the producer stream.
- Tests: `crates/ln-decode/tests/npa_analysis_context_requisites_contract.rs`
  (real pipeline: authorized letterhead + this-ref → `Resolved` with
  `authorized_current_document_requisites`/`Inherited` and exact-substrate anchor;
  surfaced without letterhead → `Unavailable`; no surface → no request;
  continuation tail → exactly one `OpenSeriesHead`; double-call byte-equal;
  missing/conflicting sidecar → `partial`/`inherited_field_conflict`),
  `crates/ln-decode/tests/npa_context_consumer_contract.rs` (authorized,
  missing, not-requested, conflicting, hand-built fail-closed and closed-token
  cases), plus updated `npa_analysis_context_contract.rs`,
  `npa_analysis_wire_context.rs` and `npa_analysis_export_integration.rs`.
- Re-emitted receipt: `prd/migration/rust-evidence/m214-s03-context-verify.json`
  was regenerated from the live pipeline; `write_portable_receipt_s03_json`
  followed by the ordinary run makes
  `portable_receipt_s03_valid_and_matches_live_pipeline` green.
- S03 battery (all exit 0, 0 failed): `npa_analysis_context_contract` 8,
  `npa_analysis_context_requisites_contract` 7, `npa_context_consumer_contract`
  11, `npa_analysis_wire_context` 11, `npa_analysis_wire_contract` 9,
  `npa_analysis_wire_hostile` 13, `npa_analysis_verify_contract` 9,
  `npa_analysis_verify_hostile` 23, `npa_analysis_export_integration` 13,
  `npa_analysis_records_contract` 14, `npa_analysis_separator_contract` 7,
  `npa_analysis_records_link_classify` 9, `m206_grammar_context_regressions` 19,
  `npa_current_requisites_contract` 9, `npa_document_context_contract` 11,
  `npa_document_context_hostile_contract` 19; parser acceptance
  `npa_corpus_acceptance_run_contract` 14, `npa_corpus_acceptance_report_contract`
  7; `cargo fmt --all --check`, `cargo check --workspace --offline` and
  `verify-adr-conformance.py` on the contract all exit 0.
- S02 byte-stability preserved: `empty_context_is_byte_identical_to_s02` and
  `portable_receipt_valid_and_matches_live_pipeline` are green and
  `prd/migration/rust-evidence/m214-s02-analysis-export.json` is unchanged.
- Non-claims: F04–F06 stay open; R1000 stays active and unclosed
  (D638/D656 carry-forward); downstream M208/M215–M220 stay parked; integrity,
  completeness and semantic acceptance remain separate verdicts. This closes only
  the bounded F03 producer/consumer path, not the context model as semantic
  acceptance.

### F04 HIGH evidence gap: verified_ok does not mean correct legal analysis

`npa_analysis_verify.rs:864-891` reuses analyze_document, build_context_records and render_npa_analysis_with_context. This is independent of the received artifact, not an independent semantic oracle. A shared deterministic producer defect survives re-derivation.

`npa_corpus_acceptance.rs:1837-1857` marks an entry VerifiedOk on verifier Ok; an honestly incomplete/refused-context envelope can therefore be verified_ok. This is reasonable for integrity but insufficient as semantic readiness evidence. The report explicitly has semantic_reference_status=absent, adjudication_status=not_attempted, adjudicated_entries=0 and promotion=false (`prd/migration/rust-evidence/m214-s04-corpus-acceptance.json`).

Required work: split transport_integrity, analysis_completion and semantic_acceptance verdicts. Add per-family extraction counts, refusal reasons, context result distributions and annotated expected outcomes; a parser returning too few correct-looking records must fail recall/coverage acceptance rather than pass consistency checks.

### F05 MEDIUM: declared providers are not sampled provider coverage

The tracked m214-s04-corpus-sample.json declares Consultant and Garant roots, but all 400 entries have provider=consultant_export. No Garant acceptance claim follows from this sample. The provider-independent render_entry path must be tested per actual supported source format before broadening claims.

Required work: minimum nonzero quotas or an explicit uncovered-provider verdict; separate format coverage from source-provider labels. Sample across legal structure and known failure features, not only file/work-family identities.

### Bounded closure pointers (M221-wbslul S04, T01–T05)

F04 and F05 are closed **bounded** — at fixture/contract scope, not corpus-wide:

- **Split verdicts (F04):** `crates/ln-consultant-parser/src/npa_corpus_acceptance_v2.rs` separates `transport_integrity` / `analysis_completion` / `semantic_acceptance` in `law-nexus/npa-analysis-corpus-acceptance/v2`; `npa_acceptance_split_report_contract` asserts the three coexist and that a transport pass never implies completion or semantic acceptance.
- **Per-entry completion capture (F04):** `npa_corpus_acceptance.rs` records per-entry `completion` / `completion_basis` / `incomplete_reasons` / `family_yields`; `npa_corpus_acceptance_completion_contract` proves complete/incomplete capture over the real pipeline.
- **Declared-before-run recall/coverage gate (F04):** `DeclaredExpectations` snapshots the `DECLARED_MIN_COMPLETION_RATIO_PPM` / `DECLARED_MIN_FAMILY_YIELDS` minima before the run and re-derives `expectation_gate` in `validate`; `npa_acceptance_expectations_contract` shows a below-declared producer fails the gate rather than passing consistency checks.
- **Provider coverage / uncovered (F05):** the v2 report lists every declared provider as `covered` or `uncovered` with a closed `uncovered_reason`; `garant` surfaces `uncovered` / `no_candidates` (0 supported-format XML under `law-source/garant`).
- **Bounded evidence artifact + suites:** the `npa-corpus-acceptance-v2` CLI emits tracked `prd/migration/rust-evidence/m221-s04-acceptance.json` (+ `.jsonl`); `npa_acceptance_bounded_run_contract` loads and cross-checks them. The tracked artifact carries all three verdicts at once (`transport_integrity=pass`, `analysis_completion=incomplete`, `semantic_acceptance=not_attempted`) with `expectation_gate=below_declared`.

Explicit non-claims (these remain open):

- **F06 is closed bounded under S05** — authority surfaces reconciled with the bounded M211 runtime; corpus-wide/semantic acceptance remains unclaimed.
- **R1000 stays active/unclosed** (D638/D656 carry-forward); M221 adds no DB requirement binding.
- `semantic_acceptance` is **always `not_attempted`** (D667) — no independent legal-semantic oracle exists.
- Downstream **M208-wrz6fg and M215–M220 stay parked**.
- F04/F05 are closed **bounded** (fixture-first), **not** a corpus-wide accuracy or breadth claim; no C5 promotion. The frozen M214 v1 artifacts are untouched.

### F06 closure pointer

F06 is closed **bounded** under M221-wbslul S05 — design-only reconciliation of the
cold authority surfaces with the already-landed bounded M211 Rust runtime:

- **Design-only pin (authoritative:false, human_adoption:pending):** `prd/architecture/m221-s05-docs-reconciliation.yaml` is the machine-checkable spine; it records the four cold surfaces that were reconciled and the non-claims below. It pins (by sha256) only artifacts this slice does not edit.
- **Re-acceptance battery:** `prd/migration/rust-evidence/m221-s05-readiness-battery.json` is a count/hash-only receipt replaying the S01–S04 suites (all exit 0) and carrying the three frozen S04 verdicts unchanged.
- **Reconciled surfaces:** ADR-0029 Status (`doc/adr/0029-requisites-anchored-member-assembly-fsm.md`), the `prd/ARCHITECTURE.md` ADR-0029 row, the `doc/adr/README.md` index row, the `README.md` lineage block, and the `doc/adr-architecture-cross-matrix.md` companion.

F06 non-claims:

- **Not a lifecycle promotion:** ADR-0029 stays `[proposed]`; the bounded runtime is described as bounded and is **not** promoted to semantic acceptance or C5.
- **Not a runtime fix:** no product Rust code changed; this is a documentation/authority reconciliation only.
- **Not corpus-wide/semantic acceptance:** `semantic_acceptance` remains `not_attempted` (D667).
- **R1000 stays active/unclosed** (D638/D656 carry-forward); M221 adds no DB requirement binding.
- Downstream **M208-wrz6fg and M215–M220 stay parked**.

### F06 MEDIUM: workflow documentation lags runtime

`prd/ARCHITECTURE.md` ADR-0029 row says no Rust engine code has landed, while M211/M214 Rust runtime and their declared receipts exist. The mandatory living oracle and completed-work narrative conflict. Synchronizing a workflow roadmap alone does not reconcile architecture authority.

Required work: reconcile the owning ADR/architecture/contract claims with actual scope and residuals, without promoting bounded runtime to semantic acceptance.

## Tokenizer assessment

The two token views in tokenizer.rs are deliberate and non-interchangeable: private alphabetic splitter versus covering lexer projection. This audit found no evidence that merging them is necessary. The reproduced separator loss is upstream of tokenization. Review tokenization quality with segmentation/metamorphic and legal-reference gold tests instead of adding a third tokenizer or treating dual views as an automatic defect.

## Recommended sequence and release gate

1. Freeze downstream execution; preserve M214 completion history but record these findings as new remediation input.
2. Fix F01 and F02 with failing regression tests first, then contract/hostile/metamorphic verification.
3. (Completed M221-wbslul S03) Bounded context-consumer/requisites path (F03): deterministic requisites source from the pinned parent, proven trigger policy and closed `ThisDocumentReferenceOutcome` consumer outcomes; see the F03 closure pointer.
4. Build a small independently adjudicated legal corpus with exact source spans and expected typed/link/classification/context outputs; include negative, ambiguous, split-run, tab/break, table/footnote, list and cross-block cases. Then expand by observed failure classes.
5. Repeat bounded corpus acceptance with actual provider/format quotas, per-family yields, context completeness and semantic error metrics. Keep integrity and semantic verdicts separate.
6. (Completed M221-wbslul S05) Reconcile authority docs (F06) — see the F06 closure pointer; review future milestone input contracts, and only then decide whether to release temporal/retrieval/graph work.

Do not use 400/400 verified_ok, green clippy, governor status, or completed milestone counts as substitutes for this release gate. No percentage of overall readiness is justified by the current evidence.
