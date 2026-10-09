//! Consuming, projection-derived proof of bounded slice-level retrieval
//! **quality** and **runtime** metrics over the declared M216 retrieval slice.
//!
//! This integration test drives the full enabled M213 cleaned-projection
//! pipeline (`capture -> gate_reader(SupportedWordml) -> build_projection ->
//! export_cleaned_projection(Complete) -> read_cleaned_wire -> build_nav_index`)
//! over exactly THREE tracked documents -- one pinned real Consultant Plus
//! WordML export read with `std::fs::read`, and two pinned reader fixtures --
//! then runs the S02 offline citation-safe retrieval surface over a
//! deterministic per-document corpus covering every declared case class, and
//! computes the six closed quality metrics plus the structural runtime profile
//! with [`ln_query::retrieval_metrics`].
//!
//! Honest boundaries (frozen in `prd/retrieval/rust_retrieval_metrics_contract.md`,
//! `retrieval-metrics/rust-v1`):
//!
//! - The metrics are **slice-level**: three declared documents, not the corpus.
//!   They are not product retrieval quality and not legal-answer correctness.
//! - The runtime profile is **structural and reproducible** (counters only).
//!   Host-boundary wall-clock is measured with `std::time::Instant` by this
//!   caller and recorded with `reproducible: false` / `asserted: false`; it is
//!   **never asserted** and never a runtime/FalkorDB readiness claim.
//! - Every document is pinned by content: a byte-length or sha256 drift panics
//!   with an explicit re-pin message instead of being silently accepted.
//! - Emitted values are counters, ratios, and closed strings only. No raw
//!   decoded legal text, prompt, vector, secret, or generated answer prose can
//!   appear in the report or any diagnostic (sentinel-checked).
//!
//! No network, product API, embedding, LLM, service, or new crate dependency is
//! involved. The proof artifact is `prd/retrieval/rust_retrieval_metrics_proof.md`.

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::time::Instant;

use ln_decode::cleaned_nav::{build_nav_index, NavIndex, NodeAddress};
use ln_decode::cleaned_wire::{
    export_cleaned_projection, read_cleaned_wire, CleanedProjection, WireCompletion, WireLimits,
};
use ln_decode::reader_gate::{gate_reader, ReaderSourceClass};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{capture, Limits};

use ln_query::retrieval_metrics::{
    compute_retrieval_quality_metrics, RetrievalMetricBoundary, RetrievalMetricKind,
    RetrievalMetricReproducibility, RetrievalMetricThreshold, RetrievalMetricsReport,
    RetrievalObservedTiming, RetrievalQualityMetricId, RetrievalRuntimeProfile,
    RETRIEVAL_METRICS_NON_CLAIMS, RETRIEVAL_METRICS_SCHEMA_VERSION,
};
use ln_query::retrieval_offline::{
    run_offline_citation_retrieval_cases, run_offline_citation_retrieval_proof, OfflineCaseOutcome,
    OfflineExpectedResult, OfflineRetrievalCase, OfflineSelectionReason, ProjectionGraphResolver,
    RetrievalQueryKind,
};
use ln_query::retrieval_output::*;

// --- the declared, pinned slice of three tracked documents -----------------

/// The single pinned real Consultant WordML document declared by the contract.
const DOC_FILE: &str =
    "federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";
/// Pinned content hash and byte length of that document.
const DOC_SHA256: &str = "62810fd14c12ca5b239178385d0fc53b3377c05da6a1ff9a834acd2e46fafb9d";
const DOC_BYTES: usize = 193726;

/// The pinned synthetic, non-legal reader fixture `mixed-wordml.xml`.
const MIXED_XML: &str = include_str!("../../ln-decode/tests/fixtures/reader/mixed-wordml.xml");
const MIXED_SHA256: &str = "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db";

/// The pinned synthetic, non-legal navigation-demo reader fixture.
const NAVDEMO_XML: &str =
    include_str!("../../ln-decode/tests/fixtures/reader/diverse/navigation-demo.xml");
const NAVDEMO_SHA256: &str = "b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0";

/// Sentinel fragments that provably appear in the pinned real document. If any
/// report or diagnostic carries one, raw document text leaked into the bounded
/// evidence surface.
const DOC_SENTINELS: [&str; 4] = [
    "КонсультантПлюс",
    "Федеральный",
    "РОССИЙСКАЯ",
    "Государственной",
];

/// Neutral sentinel words from `mixed-wordml.xml`.
const MIXED_SENTINELS: [&str; 14] = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa",
    "Lambda", "Mu", "Nu", "NBSP",
];

/// Neutral sentinel words from `navigation-demo.xml`.
const NAVDEMO_SENTINELS: [&str; 8] = [
    "Начало",
    "Ячейка",
    "Сноска",
    "Таблица",
    "Вложенная",
    "Привет",
    "Остаточный",
    "Неизвестная",
];

/// Number of host-boundary timing iterations (measured, never asserted).
const TIMING_ITERATIONS: usize = 5;

/// The per-document marker multiplicities of the deterministic case corpus.
///
/// The selectors are closed `marker_kind` tokens evaluated by the production
/// walk; the corpus stays data-only. Multiplicities are properties of the
/// pinned documents: the selected marker matches exactly one segment, the scoped
/// marker matches none, and the ambiguous marker matches many.
struct CorpusSpec {
    /// A marker with exactly one matching segment on this document.
    selected_marker: &'static str,
    /// A marker with no matching segment on this document.
    scoped_marker: &'static str,
    /// A marker with more than one matching segment on this document.
    ambiguous_marker: &'static str,
}

/// One declared document: its cleaned-projection read-back, its derived
/// resolution graph, the segment addresses of its `NavIndex`, and its corpus
/// spec -- all produced by the real enabled pipeline.
struct SliceDoc {
    name: &'static str,
    projection: CleanedProjection,
    resolver: ProjectionGraphResolver,
    nav_segments: BTreeSet<String>,
    sentinels: &'static [&'static str],
    spec: CorpusSpec,
}

/// Drive the enabled pipeline over one pinned document and verify its content
/// hash. A byte-length or sha256 drift panics with an explicit re-pin message;
/// it is never re-pinned silently.
fn build_document(
    name: &'static str,
    raw: &[u8],
    pinned_sha: &str,
    pinned_bytes: Option<usize>,
    sentinels: &'static [&'static str],
    spec: CorpusSpec,
) -> SliceDoc {
    if let Some(bytes) = pinned_bytes {
        assert_eq!(
            raw.len(),
            bytes,
            "{name}: pinned document byte-length drift; re-pin the byte length explicitly instead of silently accepting it"
        );
    }
    // The sentinels are only meaningful if they really are in the document;
    // assert their presence so the redaction check cannot pass vacuously.
    let raw_text = String::from_utf8_lossy(raw);
    for sentinel in sentinels {
        assert!(
            raw_text.contains(sentinel),
            "{name}: sentinel {sentinel:?} must be present in the pinned document"
        );
    }

    let package = capture(raw, &Limits::default())
        .unwrap_or_else(|error| panic!("{name}: pinned document must capture: {error:?}"));
    assert_eq!(
        package.manifest().source.sha256,
        pinned_sha,
        "{name}: pinned document content drift; re-pin the sha256 oracle explicitly instead of silently accepting a new hash"
    );
    let class = gate_reader(package.records())
        .unwrap_or_else(|error| panic!("{name}: pinned document must gate: {error:?}"));
    assert_eq!(
        class,
        ReaderSourceClass::SupportedWordml,
        "{name}: pinned document must gate as a supported WordML reader source"
    );
    let reader_projection = build_projection(package.records())
        .unwrap_or_else(|error| panic!("{name}: pinned document must project: {error:?}"));
    let artifact = export_cleaned_projection(
        &package,
        &reader_projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .unwrap_or_else(|error| {
        panic!("{name}: pinned document must export a cleaned artifact: {error:?}")
    });
    let projection = read_cleaned_wire(&artifact)
        .unwrap_or_else(|error| panic!("{name}: cleaned artifact must read back: {error:?}"));
    let nav = build_nav_index(&projection, &package)
        .unwrap_or_else(|error| panic!("{name}: nav index must build: {error:?}"));
    let nav_segments = nav_segment_ids(&nav);
    assert!(
        !nav_segments.is_empty(),
        "{name}: the pinned document must project at least one segment"
    );
    let resolver = ProjectionGraphResolver::new(&projection)
        .unwrap_or_else(|error| panic!("{name}: resolution graph must derive: {error:?}"));
    SliceDoc {
        name,
        projection,
        resolver,
        nav_segments,
        sentinels,
        spec,
    }
}

/// Build the declared, pinned slice of three tracked documents.
fn build_slice() -> Vec<SliceDoc> {
    let real_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../law-source/consultant")
        .join(DOC_FILE);
    let real_raw = std::fs::read(&real_path).unwrap_or_else(|error| {
        panic!(
            "pinned real document must be readable at {}: {error}",
            real_path.display()
        )
    });
    vec![
        build_document(
            "real-consultant",
            &real_raw,
            DOC_SHA256,
            Some(DOC_BYTES),
            &DOC_SENTINELS,
            CorpusSpec {
                selected_marker: "semantic:whitespace",
                scoped_marker: "reference:note_reference",
                ambiguous_marker: "semantic:body",
            },
        ),
        build_document(
            "mixed-wordml",
            MIXED_XML.as_bytes(),
            MIXED_SHA256,
            None,
            &MIXED_SENTINELS,
            CorpusSpec {
                selected_marker: "semantic:whitespace",
                scoped_marker: "reference:endnote_reference",
                ambiguous_marker: "semantic:body",
            },
        ),
        build_document(
            "navigation-demo",
            NAVDEMO_XML.as_bytes(),
            NAVDEMO_SHA256,
            None,
            &NAVDEMO_SENTINELS,
            CorpusSpec {
                selected_marker: "semantic:field_code",
                scoped_marker: "reference:endnote_reference",
                ambiguous_marker: "semantic:body",
            },
        ),
    ]
}

// --- helpers ---------------------------------------------------------------

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

/// One authored case with a unique per-document case id.
fn doc_case(
    doc_name: &str,
    scope_id: &str,
    suffix: &str,
    query_kind: RetrievalQueryKind,
    selector: &str,
    expected_result: OfflineExpectedResult,
) -> OfflineRetrievalCase {
    OfflineRetrievalCase {
        case_id: format!("s04-{doc_name}-{suffix}"),
        query_id: format!("Q-s04-{doc_name}-{suffix}"),
        scope_id: scope_id.to_owned(),
        as_of_date: "2024-06-15".to_owned(),
        query_kind,
        selector: selector.to_owned(),
        expected_result,
    }
}

/// A deterministic corpus covering every declared case class on one document.
fn doc_cases(doc: &SliceDoc) -> Vec<OfflineRetrievalCase> {
    let scope_id = doc.resolver.scope_id().as_str().to_owned();
    let exact_segment = doc
        .resolver
        .evidence_span_ids()
        .next()
        .and_then(|span| doc.resolver.segment_id_for_evidence_span(span))
        .expect("the pinned document must project at least one segment")
        .to_owned();
    // A projected *view* id, never a segment id: the citation is unresolvable.
    let unresolvable = "v3";
    assert!(
        doc.resolver.binding_for_segment(unresolvable).is_none(),
        "{}: the unresolved-span selector must not be a projected segment id",
        doc.name
    );
    vec![
        doc_case(
            doc.name,
            &scope_id,
            "exact",
            RetrievalQueryKind::ExactNodeAddress,
            &exact_segment,
            OfflineExpectedResult::Selected,
        ),
        doc_case(
            doc.name,
            &scope_id,
            "marker-selected",
            RetrievalQueryKind::MarkerKind,
            doc.spec.selected_marker,
            OfflineExpectedResult::Selected,
        ),
        doc_case(
            doc.name,
            &scope_id,
            "marker-scoped",
            RetrievalQueryKind::MarkerKind,
            doc.spec.scoped_marker,
            OfflineExpectedResult::ScopedNoAnswer,
        ),
        doc_case(
            doc.name,
            &scope_id,
            "marker-ambiguous",
            RetrievalQueryKind::MarkerKind,
            doc.spec.ambiguous_marker,
            OfflineExpectedResult::Rejected,
        ),
        doc_case(
            doc.name,
            &scope_id,
            "unresolved",
            RetrievalQueryKind::ExactNodeAddress,
            unresolvable,
            OfflineExpectedResult::Rejected,
        ),
        doc_case(
            doc.name,
            &scope_id,
            "unsafe",
            RetrievalQueryKind::InvalidCandidate,
            "raw_legal_text",
            OfflineExpectedResult::Rejected,
        ),
        doc_case(
            doc.name,
            &scope_id,
            "scoped-kind",
            RetrievalQueryKind::ScopedNoCandidate,
            "",
            OfflineExpectedResult::ScopedNoAnswer,
        ),
        doc_case(
            doc.name,
            &scope_id,
            "ambiguous-kind",
            RetrievalQueryKind::AmbiguousLookup,
            "",
            OfflineExpectedResult::Rejected,
        ),
    ]
}

/// Run the declared slice: per document, build its cases and run them against
/// its own projection and resolver; aggregate cases and outcomes in slice order.
fn run_slice(slice: &[SliceDoc]) -> (Vec<OfflineRetrievalCase>, Vec<OfflineCaseOutcome>) {
    let mut cases = Vec::new();
    let mut outcomes = Vec::new();
    for doc in slice {
        let doc_cases = doc_cases(doc);
        let doc_outcomes =
            run_offline_citation_retrieval_cases(&doc_cases, &doc.projection, &doc.resolver);
        cases.extend(doc_cases);
        outcomes.extend(doc_outcomes);
    }
    (cases, outcomes)
}

/// Build the reproducible structural runtime profile from the declared slice.
fn slice_profile(slice: &[SliceDoc], cases_run: usize) -> RetrievalRuntimeProfile {
    RetrievalRuntimeProfile::from_documents(
        slice.iter().map(|doc| (&doc.projection, &doc.resolver)),
        cases_run,
    )
}

/// The outcome for a case id, panicking when the case was not authored.
fn outcome_by_id<'a>(outcomes: &'a [OfflineCaseOutcome], case_id: &str) -> &'a OfflineCaseOutcome {
    outcomes
        .iter()
        .find(|outcome| outcome.case_id == case_id)
        .unwrap_or_else(|| panic!("authored case {case_id} must have an outcome"))
}

/// The median of a sorted duration list.
fn median(sorted: &[u64]) -> u64 {
    sorted[sorted.len() / 2]
}

/// Measure host-boundary wall-clock over the declared slice. Environment
/// dependent, reported, never asserted.
fn measure_host_boundary_timing(slice: &[SliceDoc]) -> RetrievalObservedTiming {
    let mut durations: Vec<u64> = Vec::with_capacity(TIMING_ITERATIONS);
    for _ in 0..TIMING_ITERATIONS {
        let start = Instant::now();
        let (cases, outcomes) = run_slice(slice);
        std::hint::black_box(&cases);
        std::hint::black_box(&outcomes);
        durations.push(start.elapsed().as_millis() as u64);
    }
    durations.sort_unstable();
    let min = *durations.first().expect("at least one timing iteration");
    let med = median(&durations);
    RetrievalObservedTiming::new(TIMING_ITERATIONS, min, med)
}

// --- tests -----------------------------------------------------------------

#[test]
fn declared_slice_builds_the_projection_and_origins_match_nav() {
    let slice = build_slice();
    assert_eq!(
        slice.len(),
        3,
        "the declared slice is exactly three documents"
    );
    for doc in &slice {
        let resolver = &doc.resolver;
        assert_eq!(
            resolver_segment_ids(resolver),
            doc.nav_segments,
            "{}: resolver evidence spans must equal the nav segment-address set",
            doc.name
        );
        assert_eq!(
            resolver.evidence_span_ids().count(),
            resolver.segment_ids().count(),
            "{}: exactly one evidence span per segment node",
            doc.name
        );
        for span in resolver.evidence_span_ids() {
            let record = resolver
                .resolve_evidence_span(span)
                .expect("every minted span must resolve");
            assert_eq!(record.status, EvidenceSpanStatus::Active, "{}", doc.name);
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
                    "{}: the resolved span must be the segment's own span",
                    doc.name
                ),
                other => panic!(
                    "{}: segment {segment_id} must resolve uniquely, got {other:?}",
                    doc.name
                ),
            }
        }
    }
}

#[test]
fn quality_metrics_meet_every_threshold_over_the_declared_slice() {
    let slice = build_slice();
    let (cases, outcomes) = run_slice(&slice);

    // Every authored case must match its expected result, and the closed proof
    // surface must agree per document.
    assert_eq!(cases.len(), outcomes.len());
    assert!(
        outcomes.iter().all(|outcome| outcome.matched),
        "every authored case must match its expected result"
    );
    for doc in &slice {
        let doc_cases = doc_cases(doc);
        let summary =
            run_offline_citation_retrieval_proof(&doc_cases, &doc.projection, &doc.resolver);
        assert_eq!(summary.total_cases, 8, "{}", doc.name);
        assert_eq!(summary.mismatch_count, 0, "{}", doc.name);
    }

    let metrics = compute_retrieval_quality_metrics(&cases, &outcomes);

    // Complete declared classification coverage: no denominator is empty.
    assert_eq!(metrics.total_cases, 24);
    assert_eq!(metrics.positive_cases, 6);
    assert_eq!(metrics.scoped_cases, 6);
    assert_eq!(metrics.ambiguous_cases, 3);
    assert_eq!(metrics.unsafe_cases, 3);
    assert_eq!(metrics.unresolvable_cases, 3);
    assert_eq!(metrics.mismatch_count, 0);

    for metric in RetrievalQualityMetricId::ALL {
        assert_eq!(
            metrics.value(metric),
            1.0,
            "metric {} must be 1.0 on the declared slice",
            metric.as_str()
        );
    }
    assert!(
        RetrievalMetricThreshold::SLICE
            .breaches(&metrics)
            .is_empty(),
        "no quality metric may breach its threshold: {:?}",
        RetrievalMetricThreshold::SLICE.breaches(&metrics)
    );

    // Every declared class is exercised somewhere on the slice.
    let mut saw_selected = false;
    let mut saw_scoped = false;
    let mut saw_rejected = false;
    for outcome in &outcomes {
        match outcome.validator_verdict {
            Some(OutputVerdict::Accepted) => saw_selected = true,
            Some(OutputVerdict::AcceptedScopedNoAnswer) => saw_scoped = true,
            _ => saw_rejected = true,
        }
    }
    assert!(
        saw_selected && saw_scoped && saw_rejected,
        "all result classes covered"
    );

    // Demo invariant: an unresolvable citation is always rejected, and a
    // rejection reason never emits an accepted answer.
    for outcome in &outcomes {
        if outcome.selection_reason == OfflineSelectionReason::UnresolvedCandidateEvidence {
            assert_eq!(outcome.validator_verdict, Some(OutputVerdict::Rejected));
        }
        if matches!(
            outcome.selection_reason,
            OfflineSelectionReason::UnresolvedCandidateEvidence
                | OfflineSelectionReason::AmbiguousCandidateSet
                | OfflineSelectionReason::UnsafePayloadRejected
        ) {
            assert_ne!(outcome.validator_verdict, Some(OutputVerdict::Accepted));
            assert_ne!(
                outcome.validator_verdict,
                Some(OutputVerdict::AcceptedScopedNoAnswer)
            );
        }
    }
    let unresolved = outcome_by_id(&outcomes, "s04-real-consultant-unresolved");
    assert_eq!(
        unresolved.primary_code,
        Some(OutputDiagnosticCode::UnresolvedEvidenceSpan)
    );
}

#[test]
fn structural_runtime_profile_is_reproducible() {
    let slice = build_slice();
    let (cases, _outcomes) = run_slice(&slice);
    let cases_run = cases.len();
    let first = slice_profile(&slice, cases_run);

    // A second, independent pipeline build over the same declared slice.
    let second_slice = build_slice();
    let (second_cases, _) = run_slice(&second_slice);
    let second = slice_profile(&second_slice, second_cases.len());

    assert_eq!(
        first, second,
        "two independent runs over the declared slice must produce an equal structural profile"
    );
    assert_eq!(first.documents_processed, 3);
    assert_eq!(first.cases_run, 24);
    assert!(first.projected_views > 0, "the slice must project views");
    assert!(
        first.projected_segments > 0,
        "the slice must project segments"
    );
    assert_eq!(
        first.resolver_evidence_spans, first.projected_segments,
        "exactly one resolver evidence span per projected segment"
    );
    assert_eq!(
        first.reproducibility(),
        RetrievalMetricReproducibility::Reproducible
    );
}

#[test]
fn host_boundary_timing_is_observed_but_never_asserted() {
    let slice = build_slice();
    let timing = measure_host_boundary_timing(&slice);

    // Reported as an observation only: never reproducible, never asserted.
    assert_eq!(timing.iterations, TIMING_ITERATIONS);
    assert!(timing.elapsed_ms_median >= timing.elapsed_ms_min);
    assert!(!timing.reproducible());
    assert!(!timing.asserted());
    assert_eq!(
        timing.reproducibility(),
        RetrievalMetricReproducibility::HostBoundaryObservedUnasserted
    );
    assert_eq!(
        timing.reproducibility().as_str(),
        "host_boundary_observed_unasserted"
    );
    // The timing is never compared to any threshold; the structural profile is
    // the only reproducible runtime surface. Nothing here asserts a duration.
}

#[test]
fn bounded_report_carries_no_document_text() {
    let slice = build_slice();
    let (cases, outcomes) = run_slice(&slice);
    let metrics = compute_retrieval_quality_metrics(&cases, &outcomes);
    let profile = slice_profile(&slice, cases.len());
    let timing = measure_host_boundary_timing(&slice);
    let report = RetrievalMetricsReport::new(
        RetrievalMetricKind::Quality,
        metrics,
        profile,
        Some(timing.clone()),
    );

    assert_eq!(report.schema_version, RETRIEVAL_METRICS_SCHEMA_VERSION);
    assert_eq!(report.schema_version, "retrieval-metrics/rust-v1");
    assert_eq!(report.kind, RetrievalMetricKind::Quality);
    assert_eq!(report.kind.as_str(), "quality");
    assert_eq!(report.boundary, RetrievalMetricBoundary::Slice);
    assert_eq!(report.boundary.as_str(), "slice");
    assert_eq!(report.non_claims, RETRIEVAL_METRICS_NON_CLAIMS);
    assert!(!report.non_claims.is_empty());

    // No raw document text may appear in the report's only observable surface.
    let mut sentinels: BTreeSet<&'static str> = BTreeSet::new();
    for doc in &slice {
        sentinels.extend(doc.sentinels);
    }
    let rendered = format!("{:?}", report);
    let rendered_metrics = format!("{:?}", report.quality);
    let rendered_profile = format!("{:?}", report.runtime_profile);
    for sentinel in &sentinels {
        assert!(
            !rendered.contains(sentinel),
            "the report leaked raw document text: {sentinel}"
        );
        assert!(
            !rendered_metrics.contains(sentinel),
            "the quality metrics leaked raw document text: {sentinel}"
        );
        assert!(
            !rendered_profile.contains(sentinel),
            "the runtime profile leaked raw document text: {sentinel}"
        );
    }
    for claim in report.non_claims {
        assert!(!claim.is_empty());
        for sentinel in &sentinels {
            assert!(
                !claim.contains(sentinel),
                "a non-claim leaked text: {claim}"
            );
        }
    }
}

#[test]
fn proof_run_is_deterministic_and_does_not_mutate_the_projections() {
    let slice = build_slice();
    let before: Vec<CleanedProjection> = slice.iter().map(|doc| doc.projection.clone()).collect();

    let (first_cases, first_outcomes) = run_slice(&slice);
    let first_metrics = compute_retrieval_quality_metrics(&first_cases, &first_outcomes);
    let first_profile = slice_profile(&slice, first_cases.len());

    let (second_cases, second_outcomes) = run_slice(&slice);
    let second_metrics = compute_retrieval_quality_metrics(&second_cases, &second_outcomes);
    let second_profile = slice_profile(&slice, second_cases.len());

    assert_eq!(
        first_cases, second_cases,
        "two runs must author equal cases"
    );
    assert_eq!(
        first_outcomes, second_outcomes,
        "two runs must be identical"
    );
    assert_eq!(first_metrics, second_metrics, "two runs must be identical");
    assert_eq!(first_profile, second_profile, "two runs must be identical");

    for (doc, original) in slice.iter().zip(before.iter()) {
        assert_eq!(
            &doc.projection, original,
            "{}: the proof run must not mutate the borrowed projection",
            doc.name
        );
    }
}

#[test]
fn prints_bounded_metrics_report() {
    let slice = build_slice();
    let (cases, outcomes) = run_slice(&slice);
    let metrics = compute_retrieval_quality_metrics(&cases, &outcomes);
    let profile = slice_profile(&slice, cases.len());
    let timing = measure_host_boundary_timing(&slice);
    let report =
        RetrievalMetricsReport::new(RetrievalMetricKind::Quality, metrics, profile, Some(timing));

    assert_eq!(report.quality.mismatch_count, 0);
    assert!(RetrievalMetricThreshold::SLICE
        .breaches(&report.quality)
        .is_empty());

    // Bounded report: counters and ratios only, plus the closed non-claims.
    println!("retrieval_metrics_report/rust-v1");
    println!("schema_version = {}", report.schema_version);
    println!("kind = {}", report.kind.as_str());
    println!("boundary = {}", report.boundary.as_str());
    println!(
        "documents_processed = {}",
        report.runtime_profile.documents_processed
    );
    println!(
        "projected_views = {}",
        report.runtime_profile.projected_views
    );
    println!(
        "projected_segments = {}",
        report.runtime_profile.projected_segments
    );
    println!(
        "resolver_evidence_spans = {}",
        report.runtime_profile.resolver_evidence_spans
    );
    println!("cases_run = {}", report.runtime_profile.cases_run);
    println!("quality.total_cases = {}", report.quality.total_cases);
    println!("quality.positive_cases = {}", report.quality.positive_cases);
    println!("quality.scoped_cases = {}", report.quality.scoped_cases);
    println!(
        "quality.ambiguous_cases = {}",
        report.quality.ambiguous_cases
    );
    println!("quality.unsafe_cases = {}", report.quality.unsafe_cases);
    println!(
        "quality.unresolvable_cases = {}",
        report.quality.unresolvable_cases
    );
    println!("quality.mismatch_count = {}", report.quality.mismatch_count);
    for metric in RetrievalQualityMetricId::ALL {
        println!(
            "quality.{} = {:.6}",
            metric.as_str(),
            report.quality.value(metric)
        );
    }
    println!(
        "quality.threshold_breaches = {}",
        RetrievalMetricThreshold::SLICE
            .breaches(&report.quality)
            .len()
    );
    println!("refused_as_product_claim = true");
    if let Some(timing) = &report.observed_timing {
        println!("observed_timing.iterations = {}", timing.iterations);
        println!("observed_timing.elapsed_ms_min = {}", timing.elapsed_ms_min);
        println!(
            "observed_timing.elapsed_ms_median = {}",
            timing.elapsed_ms_median
        );
        println!("observed_timing.reproducible = {}", timing.reproducible());
        println!("observed_timing.asserted = {}", timing.asserted());
    }
    println!("non_claims = {:?}", report.non_claims);
}
