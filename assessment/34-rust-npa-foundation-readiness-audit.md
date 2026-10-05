# Rust NPA foundation readiness audit

Status: [bounded] code audit and synthetic executable probes, not corpus semantic acceptance.
Reviewed base: `24b8872`. Product source was not changed. No parked milestone was released.

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

### F02 HIGH: reader-to-analysis bridge deletes control separators

`crates/ln-decode/src/npa_analysis_records.rs:298-360` skips every non-SourceFragment segment and concatenates fragment values. Reader projection preserves controls as DerivedSeparator segments (`reader_projection.rs:902-930`).

Executable WordML probe with `статья<TAB>5<BR>часть<TAB>2` yields analysis text `статья5часть2`. The legal-marker/token context receives a different lexical stream from the visible reader text. The bridge therefore can change meaning before the analyzer runs. This is broader than tokenizer implementation quality.

Required fix: preserve a mapped analysis separator plane (or explicit typed boundaries), without pretending a derived separator has a source-fragment span. Add metamorphic equivalence tests for tab/space/break and run splitting; preserve explicit refusal where a span genuinely cannot be represented. The documented choice to exclude derived segments does not make lexical concatenation semantically safe.

### F03 HIGH readiness gap: context family is not full context resolution

`npa_context_records.rs:291-390` always supplies `requisites: None`. `build_requests` (466 onward) emits OpenSeriesHead, ExplicitAnchorLookup and CurrentDocumentRequisites, not all six enum kinds. The synthetic document in the probe emits 5 requests: 2 resolved, 2 partial, 1 unavailable (MissingCurrentRequisites). This is an honest bounded adapter but not evidence of a completed context model.

`analyze_document` runs typed/link/classification before and separately from build_context_records (`npa_analysis_records.rs:977-1004`, `npa_corpus_acceptance.rs:1808 onward`). The new context family is an additional derived output, not demonstrated feedback into final typed/linked/classified decisions. Define the intended consumer semantics before presenting serialized context as analysis completeness.

Required work: authorized current-document requisites path, deliberate trigger policy for each required request kind, expected resolved/partial/unavailable outcomes, and end-to-end tests showing which analysis decisions consume context. Do not enqueue every possible request merely to improve counts.

### F04 HIGH evidence gap: verified_ok does not mean correct legal analysis

`npa_analysis_verify.rs:864-891` reuses analyze_document, build_context_records and render_npa_analysis_with_context. This is independent of the received artifact, not an independent semantic oracle. A shared deterministic producer defect survives re-derivation.

`npa_corpus_acceptance.rs:1837-1857` marks an entry VerifiedOk on verifier Ok; an honestly incomplete/refused-context envelope can therefore be verified_ok. This is reasonable for integrity but insufficient as semantic readiness evidence. The report explicitly has semantic_reference_status=absent, adjudication_status=not_attempted, adjudicated_entries=0 and promotion=false (`prd/migration/rust-evidence/m214-s04-corpus-acceptance.json`).

Required work: split transport_integrity, analysis_completion and semantic_acceptance verdicts. Add per-family extraction counts, refusal reasons, context result distributions and annotated expected outcomes; a parser returning too few correct-looking records must fail recall/coverage acceptance rather than pass consistency checks.

### F05 MEDIUM: declared providers are not sampled provider coverage

The tracked m214-s04-corpus-sample.json declares Consultant and Garant roots, but all 400 entries have provider=consultant_export. No Garant acceptance claim follows from this sample. The provider-independent render_entry path must be tested per actual supported source format before broadening claims.

Required work: minimum nonzero quotas or an explicit uncovered-provider verdict; separate format coverage from source-provider labels. Sample across legal structure and known failure features, not only file/work-family identities.

### F06 MEDIUM: workflow documentation lags runtime

`prd/ARCHITECTURE.md` ADR-0029 row says no Rust engine code has landed, while M211/M214 Rust runtime and their declared receipts exist. The mandatory living oracle and completed-work narrative conflict. Synchronizing a workflow roadmap alone does not reconcile architecture authority.

Required work: reconcile the owning ADR/architecture/contract claims with actual scope and residuals, without promoting bounded runtime to semantic acceptance.

## Tokenizer assessment

The two token views in tokenizer.rs are deliberate and non-interchangeable: private alphabetic splitter versus covering lexer projection. This audit found no evidence that merging them is necessary. The reproduced separator loss is upstream of tokenization. Review tokenization quality with segmentation/metamorphic and legal-reference gold tests instead of adding a third tokenizer or treating dual views as an automatic defect.

## Recommended sequence and release gate

1. Freeze downstream execution; preserve M214 completion history but record these findings as new remediation input.
2. Fix F01 and F02 with failing regression tests first, then contract/hostile/metamorphic verification.
3. Specify and complete the bounded context-consumer/requisites path (F03); expose unresolved and limited outcomes to consumers.
4. Build a small independently adjudicated legal corpus with exact source spans and expected typed/link/classification/context outputs; include negative, ambiguous, split-run, tab/break, table/footnote, list and cross-block cases. Then expand by observed failure classes.
5. Repeat bounded corpus acceptance with actual provider/format quotas, per-family yields, context completeness and semantic error metrics. Keep integrity and semantic verdicts separate.
6. Reconcile authority docs (F06), review future milestone input contracts, and only then decide whether to release temporal/retrieval/graph work.

Do not use 400/400 verified_ok, green clippy, governor status, or completed milestone counts as substitutes for this release gate. No percentage of overall readiness is justified by the current evidence.
