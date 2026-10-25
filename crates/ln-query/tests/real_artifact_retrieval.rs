//! Consuming, projection-derived proof of offline citation safety over ONE
//! pinned real Consultant WordML document.
//!
//! Unlike the component unit tests in `ln_query::retrieval_offline` (and unlike
//! the two synthetic reader fixtures in `retrieval_offline.rs`), this
//! integration test drives the full enabled M213 cleaned-projection pipeline
//! (`capture -> gate_reader(SupportedWordml) -> build_projection ->
//! export_cleaned_projection(Complete) -> read_cleaned_wire -> build_nav_index`)
//! over a real Consultant Plus export read from disk with `std::fs::read`, and
//! asserts fail-closed citation safety from the resulting projection, not from a
//! local constant.
//!
//! The document is pinned by content: a byte-length or sha256 drift fails the
//! pinned assertion with an explicit re-pin message instead of being silently
//! accepted.
//!
//! The resolution graph is origin-checked against the `NavIndex` segment
//! addresses, determinism is checked across two runs, and every declared case
//! class is covered. An unresolvable citation is always `rejected`: an accepted
//! answer without a resolvable citation is never emitted. No network, product
//! API, embedding, LLM, or new crate dependency is involved. The contract is
//! frozen in `prd/retrieval/rust_real_artifact_retrieval_proof.md`.

use std::collections::BTreeSet;
use std::path::PathBuf;

use ln_decode::cleaned_nav::{NavIndex, NodeAddress, build_nav_index};
use ln_decode::cleaned_wire::{
    CleanedProjection, WireCompletion, WireLimits, export_cleaned_projection, read_cleaned_wire,
};
use ln_decode::reader_gate::{ReaderSourceClass, gate_reader};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};

use ln_query::retrieval_offline::{
    OfflineCaseOutcome, OfflineExpectedResult, OfflineRetrievalCase, OfflineRetrievalProofSummary,
    OfflineSelectionReason, ProjectionGraphResolver, RetrievalQueryKind,
    run_offline_citation_retrieval_cases, run_offline_citation_retrieval_proof,
};
use ln_query::retrieval_output::*;

/// The single pinned real Consultant WordML document declared by the contract.
const DOC_FILE: &str = "federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";

/// The pinned content hash and byte length of that document.
const DOC_SHA256: &str = "62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d";
const DOC_BYTES: usize = 193726;

/// Sentinel fragments that provably appear in the pinned document's decoded
/// text. If any outcome, diagnostic or summary carries one, raw document text
/// leaked into the bounded evidence surface.
const DOC_SENTINELS: [&str; 4] = [
    "КонсультантПлюс",
    "Федеральный",
    "РОССИЙСКАЯ",
    "Государственной",
];

/// The pinned substrate, its cleaned-projection read-back and the segment
/// addresses of its `NavIndex`, all produced by the real enabled pipeline.
struct RealArtifact {
    projection: CleanedProjection,
    nav_segments: BTreeSet<String>,
}

impl RealArtifact {
    /// Read the pinned document with `std::fs::read` and drive the enabled
    /// pipeline. A byte-length or sha256 drift panics with an explicit re-pin
    /// message; it is never re-pinned silently.
    fn build() -> Self {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../law-source/consultant")
            .join(DOC_FILE);
        let raw = std::fs::read(&path).unwrap_or_else(|error| {
            panic!(
                "pinned real document must be readable at {}: {error}",
                path.display()
            )
        });
        assert_eq!(
            raw.len(),
            DOC_BYTES,
            "pinned real document byte-length drift; re-pin DOC_BYTES explicitly instead of silently accepting it"
        );
        // The sentinels are only meaningful if they really are in the document;
        // assert their presence so the redaction check cannot pass vacuously.
        let raw_text = String::from_utf8_lossy(&raw);
        for sentinel in DOC_SENTINELS {
            assert!(
                raw_text.contains(sentinel),
                "sentinel {sentinel:?} must be present in the pinned document"
            );
        }

        let package = capture(&raw, &Limits::default())
            .unwrap_or_else(|error| panic!("pinned real document must capture: {error:?}"));
        assert_eq!(
            package.manifest().source.sha256,
            DOC_SHA256,
            "pinned real document content drift; re-pin DOC_SHA256 explicitly instead of silently accepting a new hash"
        );
        let class = gate_reader(package.records())
            .unwrap_or_else(|error| panic!("pinned real document must gate: {error:?}"));
        assert_eq!(
            class,
            ReaderSourceClass::SupportedWordml,
            "the pinned real document must gate as a supported WordML reader source"
        );
        let reader_projection = build_projection(package.records())
            .unwrap_or_else(|error| panic!("pinned real document must project: {error:?}"));
        let artifact = export_cleaned_projection(
            &package,
            &reader_projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .unwrap_or_else(|error| {
            panic!("pinned real document must export a cleaned artifact: {error:?}")
        });
        let projection = read_cleaned_wire(&artifact)
            .unwrap_or_else(|error| panic!("cleaned artifact must read back: {error:?}"));
        let nav = build_nav_index(&projection, &package)
            .unwrap_or_else(|error| panic!("nav index must build: {error:?}"));
        let nav_segments = nav_segment_ids(&nav);
        assert!(
            !nav_segments.is_empty(),
            "the pinned real document must project at least one segment"
        );
        Self {
            projection,
            nav_segments,
        }
    }

    fn resolver(&self) -> ProjectionGraphResolver {
        ProjectionGraphResolver::new(&self.projection)
            .unwrap_or_else(|error| panic!("resolution graph must derive: {error:?}"))
    }
}

/// The segment addresses of a nav index, in source order.
fn nav_segment_ids(nav: &NavIndex) -> BTreeSet<String> {
    nav.nodes_in_source_order()
        .iter()
        .filter_map(|address| match address {
            NodeAddress::Segment(segment_id) => Some(segment_id.as_str().to_owned()),
            NodeAddress::View(_) | NodeAddress::Reference(_) => None,
        })
        .collect()
}

/// The segment ids reached by the resolver's evidence spans.
fn resolver_segment_ids(resolver: &ProjectionGraphResolver) -> BTreeSet<String> {
    resolver
        .evidence_span_ids()
        .filter_map(|id| resolver.segment_id_for_evidence_span(id).map(str::to_owned))
        .collect()
}

/// One authored case whose selection reason and validator verdict are known.
fn case(
    scope_id: &str,
    case_id: &str,
    query_kind: RetrievalQueryKind,
    selector: &str,
    expected_result: OfflineExpectedResult,
) -> OfflineRetrievalCase {
    OfflineRetrievalCase {
        case_id: case_id.to_owned(),
        query_id: format!("Q-{case_id}"),
        scope_id: scope_id.to_owned(),
        as_of_date: "2024-06-15".to_owned(),
        query_kind,
        selector: selector.to_owned(),
        expected_result,
    }
}

/// The deterministic corpus derived from the real projection. Every selector is
/// a closed token evaluated by the production walk, and every required class is
/// covered by at least one case; the corpus stays data-only.
///
/// The marker multiplicities below are properties of the pinned document:
/// `semantic:whitespace` projects exactly one segment, `reference:note_reference`
/// projects none, and `semantic:body` projects many.
fn corpus(resolver: &ProjectionGraphResolver) -> Vec<OfflineRetrievalCase> {
    let scope_id = resolver.scope_id().as_str().to_owned();
    let exact_segment = resolver
        .evidence_span_ids()
        .next()
        .and_then(|span| resolver.segment_id_for_evidence_span(span))
        .expect("the pinned real document must project at least one segment")
        .to_owned();
    // A projected *view* id, never a segment id: the citation is unresolvable.
    let unresolvable = "v3";
    assert!(
        resolver.binding_for_segment(unresolvable).is_none(),
        "the unresolved-span selector must not be a projected segment id"
    );
    vec![
        case(
            &scope_id,
            "t02-exact-node-address",
            RetrievalQueryKind::ExactNodeAddress,
            &exact_segment,
            OfflineExpectedResult::Selected,
        ),
        case(
            &scope_id,
            "t02-marker-kind-selected",
            RetrievalQueryKind::MarkerKind,
            "semantic:whitespace",
            OfflineExpectedResult::Selected,
        ),
        case(
            &scope_id,
            "t02-scoped-no-answer",
            RetrievalQueryKind::MarkerKind,
            "reference:note_reference",
            OfflineExpectedResult::ScopedNoAnswer,
        ),
        case(
            &scope_id,
            "t02-ambiguous-lookup",
            RetrievalQueryKind::MarkerKind,
            "semantic:body",
            OfflineExpectedResult::Rejected,
        ),
        case(
            &scope_id,
            "t02-invalid-candidate",
            RetrievalQueryKind::InvalidCandidate,
            "raw_legal_text",
            OfflineExpectedResult::Rejected,
        ),
        case(
            &scope_id,
            "t02-unresolved-span",
            RetrievalQueryKind::ExactNodeAddress,
            unresolvable,
            OfflineExpectedResult::Rejected,
        ),
        case(
            &scope_id,
            "t02-scoped-kind",
            RetrievalQueryKind::ScopedNoCandidate,
            "",
            OfflineExpectedResult::ScopedNoAnswer,
        ),
        case(
            &scope_id,
            "t02-ambiguous-kind",
            RetrievalQueryKind::AmbiguousLookup,
            "",
            OfflineExpectedResult::Rejected,
        ),
    ]
}

/// The outcome for a case id, panicking when the case was not authored.
fn outcome_by_id<'a>(outcomes: &'a [OfflineCaseOutcome], case_id: &str) -> &'a OfflineCaseOutcome {
    outcomes
        .iter()
        .find(|outcome| outcome.case_id == case_id)
        .unwrap_or_else(|| panic!("authored case {case_id} must have an outcome"))
}

/// The closed set of diagnostic codes the proof run may report.
fn allowed_diagnostic_codes() -> BTreeSet<&'static str> {
    OutputDiagnosticCode::ALL
        .iter()
        .map(|code| code.as_str())
        .chain([
            "scoped_no_candidate",
            "ambiguous_candidate_set",
            "unresolved_candidate_evidence",
            "unsafe_payload_rejected",
        ])
        .collect()
}

/// Print the bounded real-artifact proof summary (never raw document text).
fn print_bounded_summary(summary: &OfflineRetrievalProofSummary) {
    println!("real_artifact_retrieval_proof/v1");
    println!("pinned_sha256 = {DOC_SHA256}");
    println!("pinned_bytes = {DOC_BYTES}");
    println!("total = {}", summary.total_cases);
    println!("selected = {}", summary.selected_count);
    println!("scoped_no_answer = {}", summary.scoped_no_answer_count);
    println!("rejected = {}", summary.rejected_count);
    println!("validator_accepted = {}", summary.validator_accepted_count);
    println!("validator_rejected = {}", summary.validator_rejected_count);
    println!("mismatch_count = {}", summary.mismatch_count);
    println!(
        "diagnostic_code_inventory = {:?}",
        summary.diagnostic_code_inventory
    );
}

#[test]
fn pinned_real_document_builds_the_projection_and_resolver() {
    let artifact = RealArtifact::build();
    assert!(
        !artifact.projection.projection.segments.is_empty(),
        "the pinned real document must project at least one segment"
    );
    let resolver = artifact.resolver();
    // Every derived identifier is keyed on the pinned source hash.
    assert!(
        resolver.scope_id().as_str().contains(DOC_SHA256),
        "the proof-local scope id must be derived from the pinned source hash"
    );
    assert_eq!(
        resolver.source_document_id().as_str(),
        format!("SD-{DOC_SHA256}")
    );
}

#[test]
fn resolution_graph_span_set_matches_nav_segment_addresses() {
    let artifact = RealArtifact::build();
    let resolver = artifact.resolver();
    assert_eq!(
        resolver_segment_ids(&resolver),
        artifact.nav_segments,
        "the resolver evidence spans must equal the nav segment-address set"
    );
    assert_eq!(
        resolver.evidence_span_ids().count(),
        resolver.segment_ids().count(),
        "exactly one evidence span per segment node"
    );
    for span in resolver.evidence_span_ids() {
        let record = resolver
            .resolve_evidence_span(span)
            .expect("every minted span must resolve");
        assert_eq!(record.status, EvidenceSpanStatus::Active);
        assert_eq!(record.source_document_id, *resolver.source_document_id());
        assert_eq!(record.legal_unit_id, *resolver.legal_unit_id());
        assert_eq!(record.act_edition_id, *resolver.act_edition_id());
    }
    for segment_id in resolver.segment_ids() {
        let citation_key = resolver
            .citation_key_for_segment(segment_id)
            .expect("every segment must mint a citation key")
            .clone();
        match resolver.resolve_citation_key(resolver.scope_id(), &citation_key) {
            CitationKeyResolution::Unique(span) => assert_eq!(
                Some(&span),
                resolver.evidence_span_for_segment(segment_id),
                "the resolved span must be the segment's own span"
            ),
            other => panic!("segment {segment_id} must resolve uniquely, got {other:?}"),
        }
    }
}

#[test]
fn corpus_covers_every_class_and_is_mismatch_free() {
    let artifact = RealArtifact::build();
    let resolver = artifact.resolver();
    let cases = corpus(&resolver);
    let outcomes = run_offline_citation_retrieval_cases(&cases, &artifact.projection, &resolver);
    assert_eq!(outcomes.len(), cases.len());
    assert!(
        outcomes.iter().all(|outcome| outcome.matched),
        "every authored case must match its expected result"
    );

    // Required class 1: exact_node_address selected (one candidate).
    let exact = outcome_by_id(&outcomes, "t02-exact-node-address");
    assert_eq!(
        exact.selection_reason,
        OfflineSelectionReason::ExactNodeAddressMatch
    );
    assert_eq!(exact.validator_verdict, Some(OutputVerdict::Accepted));
    assert_eq!(exact.primary_code, None);

    // Required class 2: marker_kind selected (one candidate).
    let marker = outcome_by_id(&outcomes, "t02-marker-kind-selected");
    assert_eq!(
        marker.selection_reason,
        OfflineSelectionReason::MarkerKindMatch
    );
    assert_eq!(marker.validator_verdict, Some(OutputVerdict::Accepted));

    // Required class 3: scoped_no_answer (a closed token absent from the
    // projection).
    let scoped = outcome_by_id(&outcomes, "t02-scoped-no-answer");
    assert_eq!(
        scoped.selection_reason,
        OfflineSelectionReason::ScopedNoCandidate
    );
    assert_eq!(
        scoped.validator_verdict,
        Some(OutputVerdict::AcceptedScopedNoAnswer)
    );
    assert_eq!(
        scoped.primary_code,
        Some(OutputDiagnosticCode::ScopedNoAnswer)
    );

    // Required class 4: ambiguous_lookup (>1 candidate), derived from the
    // projection rather than assumed.
    let ambiguous = outcome_by_id(&outcomes, "t02-ambiguous-lookup");
    assert_eq!(
        ambiguous.selection_reason,
        OfflineSelectionReason::AmbiguousCandidateSet
    );
    assert_eq!(ambiguous.validator_verdict, None);

    // Required class 5: invalid_candidate carrying a forbidden payload field.
    let unsafe_case = outcome_by_id(&outcomes, "t02-invalid-candidate");
    assert_eq!(
        unsafe_case.selection_reason,
        OfflineSelectionReason::UnsafePayloadRejected
    );
    assert_eq!(unsafe_case.validator_verdict, None);

    // Required class 6: unresolved evidence-span rejection.
    let unresolved = outcome_by_id(&outcomes, "t02-unresolved-span");
    assert_eq!(
        unresolved.selection_reason,
        OfflineSelectionReason::UnresolvedCandidateEvidence
    );
    assert_eq!(unresolved.validator_verdict, Some(OutputVerdict::Rejected));
    assert_eq!(
        unresolved.primary_code,
        Some(OutputDiagnosticCode::UnresolvedEvidenceSpan)
    );

    // The closed query-kind and scoped-no-candidate kinds round out the corpus.
    let scoped_kind = outcome_by_id(&outcomes, "t02-scoped-kind");
    assert_eq!(
        scoped_kind.selection_reason,
        OfflineSelectionReason::ScopedNoCandidate
    );
    assert_eq!(
        scoped_kind.validator_verdict,
        Some(OutputVerdict::AcceptedScopedNoAnswer)
    );

    let ambiguous_kind = outcome_by_id(&outcomes, "t02-ambiguous-kind");
    assert_eq!(
        ambiguous_kind.selection_reason,
        OfflineSelectionReason::AmbiguousCandidateSet
    );
    assert_eq!(ambiguous_kind.validator_verdict, None);

    let summary = run_offline_citation_retrieval_proof(&cases, &artifact.projection, &resolver);
    assert_eq!(summary.total_cases, 8);
    assert_eq!(summary.selected_count, 2);
    assert_eq!(summary.scoped_no_answer_count, 2);
    assert_eq!(summary.rejected_count, 4);
    assert_eq!(summary.validator_accepted_count, 2);
    assert_eq!(summary.validator_rejected_count, 1);
    assert_eq!(
        summary.mismatch_count, 0,
        "the pinned real-artifact proof must be mismatch-free"
    );

    let allowed = allowed_diagnostic_codes();
    assert!(!summary.diagnostic_code_inventory.is_empty());
    for code in &summary.diagnostic_code_inventory {
        assert!(allowed.contains(code), "unexpected diagnostic code {code}");
    }
    let mut sorted = summary.diagnostic_code_inventory.clone();
    sorted.sort_unstable();
    sorted.dedup();
    assert_eq!(
        summary.diagnostic_code_inventory, sorted,
        "the code inventory must be sorted and de-duplicated"
    );
}

#[test]
fn demo_invariant_rejects_unresolvable_citation_and_accepts_only_safe_no_answer() {
    let artifact = RealArtifact::build();
    let resolver = artifact.resolver();
    let cases = corpus(&resolver);
    let outcomes = run_offline_citation_retrieval_cases(&cases, &artifact.projection, &resolver);

    // The key demo control: an unresolvable citation is rejected with the exact
    // fail-closed validator code.
    let unresolved = outcome_by_id(&outcomes, "t02-unresolved-span");
    assert_eq!(
        unresolved.validator_verdict,
        Some(OutputVerdict::Rejected),
        "an unresolvable citation must be rejected"
    );
    assert_eq!(
        unresolved.primary_code,
        Some(OutputDiagnosticCode::UnresolvedEvidenceSpan)
    );

    // A rejection reason never yields an accepted answer, and an accepted answer
    // is emitted only with a resolvable citation.
    for outcome in &outcomes {
        if matches!(
            outcome.selection_reason,
            OfflineSelectionReason::UnresolvedCandidateEvidence
                | OfflineSelectionReason::AmbiguousCandidateSet
                | OfflineSelectionReason::UnsafePayloadRejected
        ) {
            assert_eq!(outcome.expected_result, OfflineExpectedResult::Rejected);
            assert_ne!(
                outcome.validator_verdict,
                Some(OutputVerdict::Accepted),
                "a rejection must never emit an accepted answer"
            );
            assert_ne!(
                outcome.validator_verdict,
                Some(OutputVerdict::AcceptedScopedNoAnswer)
            );
        }
    }

    let scoped = outcome_by_id(&outcomes, "t02-scoped-no-answer");
    assert_eq!(
        scoped.validator_verdict,
        Some(OutputVerdict::AcceptedScopedNoAnswer),
        "a safe no-answer is accepted only as a scoped no-answer"
    );

    let summary = run_offline_citation_retrieval_proof(&cases, &artifact.projection, &resolver);
    assert_eq!(summary.mismatch_count, 0);
}

#[test]
fn proof_run_is_deterministic_and_does_not_mutate_the_projection() {
    let artifact = RealArtifact::build();
    let resolver = artifact.resolver();
    let before = artifact.projection.clone();
    let cases = corpus(&resolver);

    let first_outcomes =
        run_offline_citation_retrieval_cases(&cases, &artifact.projection, &resolver);
    let first_summary =
        run_offline_citation_retrieval_proof(&cases, &artifact.projection, &resolver);
    let second_outcomes =
        run_offline_citation_retrieval_cases(&cases, &artifact.projection, &resolver);
    let second_summary =
        run_offline_citation_retrieval_proof(&cases, &artifact.projection, &resolver);

    assert_eq!(
        first_outcomes, second_outcomes,
        "two runs must be identical"
    );
    assert_eq!(first_summary, second_summary, "two runs must be identical");
    assert_eq!(
        artifact.projection, before,
        "the proof run must not mutate the borrowed projection"
    );
}

#[test]
fn diagnostics_stay_bounded_and_carry_no_document_text() {
    let artifact = RealArtifact::build();
    let resolver = artifact.resolver();
    let cases = corpus(&resolver);
    let summary = run_offline_citation_retrieval_proof(&cases, &artifact.projection, &resolver);
    let outcomes = run_offline_citation_retrieval_cases(&cases, &artifact.projection, &resolver);

    for entry in &summary.diagnostic_code_inventory {
        for sentinel in DOC_SENTINELS {
            assert!(
                !entry.contains(sentinel),
                "a diagnostic code leaked document text: {entry}"
            );
        }
    }
    for outcome in &outcomes {
        for sentinel in DOC_SENTINELS {
            assert!(!outcome.case_id.contains(sentinel));
            assert!(!outcome.query_id.contains(sentinel));
            assert!(!outcome.selection_reason.as_str().contains(sentinel));
            if let Some(code) = outcome.primary_code {
                assert!(!code.as_str().contains(sentinel));
            }
        }
    }
}

#[test]
fn prints_bounded_real_artifact_summary() {
    let artifact = RealArtifact::build();
    let resolver = artifact.resolver();
    let cases = corpus(&resolver);
    let summary = run_offline_citation_retrieval_proof(&cases, &artifact.projection, &resolver);
    assert_eq!(summary.mismatch_count, 0);
    print_bounded_summary(&summary);
}
