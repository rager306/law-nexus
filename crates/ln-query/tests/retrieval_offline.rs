//! Consuming, projection-derived proof of offline citation safety over the
//! pinned M213 cleaned-projection slice.
//!
//! Unlike the component unit tests in `ln_query::retrieval_offline`, this
//! integration test drives the full enabled pipeline
//! (`capture -> gate_reader(SupportedWordml) -> build_projection ->
//! export_cleaned_projection(Complete) -> read_cleaned_wire ->
//! build_nav_index`) over two pinned reader fixtures and asserts fail-closed
//! citation safety from the resulting projection, not from a local constant.
//!
//! The fixtures are pinned by content sha256: a drift fails the pinned
//! assertion with an explicit message instead of being silently accepted.
//!
//! The resolution graph is origin-checked against the `NavIndex` segment
//! addresses, and a marker selector that matches on one fixture produces a safe
//! scoped no-answer on the other, proving the graph is derived from the
//! projection. An unresolvable citation is always `rejected`: an accepted answer
//! without a resolvable citation is never emitted. No network, product API,
//! embedding, LLM, or new crate dependency is involved.

use std::collections::BTreeSet;

use ln_decode::cleaned_nav::{NavIndex, NodeAddress, build_nav_index};
use ln_decode::cleaned_wire::{
    CleanedProjection, WireCompletion, WireLimits, export_cleaned_projection, read_cleaned_wire,
};
use ln_decode::reader_gate::{ReaderSourceClass, gate_reader};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};

use ln_query::domain::QueryId;
use ln_query::retrieval_offline::{
    OfflineCaseOutcome, OfflineExpectedResult, OfflineRetrievalCase, OfflineSelectionReason,
    ProjectionGraphResolver, RetrievalQueryKind, run_offline_citation_retrieval_cases,
    run_offline_citation_retrieval_proof,
};
use ln_query::retrieval_output::*;

/// The pinned synthetic, non-legal reader fixture `mixed-wordml.xml`.
const MIXED_XML: &str = include_str!("../../ln-decode/tests/fixtures/reader/mixed-wordml.xml");
const MIXED_SHA256: &str = "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db";

/// The pinned synthetic, non-legal navigation-demo reader fixture.
const NAVDEMO_XML: &str =
    include_str!("../../ln-decode/tests/fixtures/reader/diverse/navigation-demo.xml");
const NAVDEMO_SHA256: &str = "b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0";

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

/// The pinned substrate, its cleaned-projection read-back and the segment
/// addresses of its `NavIndex`, all produced by the real enabled pipeline.
struct Fixture {
    name: &'static str,
    projection: CleanedProjection,
    nav_segments: BTreeSet<String>,
    sentinels: &'static [&'static str],
}

impl Fixture {
    /// Drive the enabled pipeline over a pinned fixture and verify its content
    /// hash. A drift panics with an explicit message; it is never re-pinned
    /// silently.
    fn build(
        name: &'static str,
        xml: &str,
        pinned_sha: &str,
        sentinels: &'static [&'static str],
    ) -> Self {
        let package = capture(xml.as_bytes(), &Limits::default())
            .unwrap_or_else(|error| panic!("{name}: fixture must capture: {error:?}"));
        assert_eq!(
            package.manifest().source.sha256,
            pinned_sha,
            "{name}: pinned fixture content drift; re-pin the sha256 oracle instead of silently accepting it"
        );
        let class = gate_reader(package.records())
            .unwrap_or_else(|error| panic!("{name}: fixture must gate: {error:?}"));
        assert_eq!(
            class,
            ReaderSourceClass::SupportedWordml,
            "{name}: fixture must gate as a supported WordML reader source"
        );
        let reader_projection = build_projection(package.records())
            .unwrap_or_else(|error| panic!("{name}: fixture must project: {error:?}"));
        let artifact = export_cleaned_projection(
            &package,
            &reader_projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .unwrap_or_else(|error| {
            panic!("{name}: fixture must export a cleaned artifact: {error:?}")
        });
        let projection = read_cleaned_wire(&artifact)
            .unwrap_or_else(|error| panic!("{name}: cleaned artifact must read back: {error:?}"));
        let nav = build_nav_index(&projection, &package)
            .unwrap_or_else(|error| panic!("{name}: nav index must build: {error:?}"));
        let nav_segments = nav_segment_ids(&nav);
        assert!(
            !nav_segments.is_empty(),
            "{name}: the pinned fixture must project at least one segment"
        );
        Self {
            name,
            projection,
            nav_segments,
            sentinels,
        }
    }

    fn resolver(&self) -> ProjectionGraphResolver {
        ProjectionGraphResolver::new(&self.projection).unwrap_or_else(|error| {
            panic!("{}: resolution graph must derive: {error:?}", self.name)
        })
    }
}

/// The deterministic per-fixture case corpus shape: marker selectors with
/// fixture-specific match multiplicity. The selectors are closed `marker_kind`
/// tokens evaluated by the production walk, so the corpus stays data-only.
struct CorpusSpec {
    /// A marker with exactly one matching segment on this fixture.
    selected_marker: &'static str,
    /// A marker with no matching segment on this fixture.
    scoped_marker: &'static str,
    /// A marker with more than one matching segment on this fixture.
    ambiguous_marker: &'static str,
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

/// Build both pinned fixtures with their corpus specs.
fn pinned_fixtures() -> Vec<(Fixture, CorpusSpec)> {
    vec![
        (
            Fixture::build("mixed-wordml", MIXED_XML, MIXED_SHA256, &MIXED_SENTINELS),
            CorpusSpec {
                // `mixed-wordml` projects exactly one Whitespace segment.
                selected_marker: "semantic:whitespace",
                // Neither fixture declares an endnote reference.
                scoped_marker: "reference:endnote_reference",
                // Both fixtures project many Body segments.
                ambiguous_marker: "semantic:body",
            },
        ),
        (
            Fixture::build(
                "navigation-demo",
                NAVDEMO_XML,
                NAVDEMO_SHA256,
                &NAVDEMO_SENTINELS,
            ),
            CorpusSpec {
                // `navigation-demo` projects exactly one FieldCode segment.
                selected_marker: "semantic:field_code",
                scoped_marker: "reference:endnote_reference",
                ambiguous_marker: "semantic:body",
            },
        ),
    ]
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

/// A deterministic corpus covering every case class on one fixture.
fn corpus(resolver: &ProjectionGraphResolver, spec: &CorpusSpec) -> Vec<OfflineRetrievalCase> {
    let scope_id = resolver.scope_id().as_str().to_owned();
    let exact_segment = resolver
        .evidence_span_ids()
        .next()
        .and_then(|span| resolver.segment_id_for_evidence_span(span))
        .expect("the pinned fixture must project at least one segment")
        .to_owned();
    vec![
        case(
            &scope_id,
            "t03-exact",
            RetrievalQueryKind::ExactNodeAddress,
            &exact_segment,
            OfflineExpectedResult::Selected,
        ),
        case(
            &scope_id,
            "t03-marker-selected",
            RetrievalQueryKind::MarkerKind,
            spec.selected_marker,
            OfflineExpectedResult::Selected,
        ),
        case(
            &scope_id,
            "t03-marker-scoped",
            RetrievalQueryKind::MarkerKind,
            spec.scoped_marker,
            OfflineExpectedResult::ScopedNoAnswer,
        ),
        case(
            &scope_id,
            "t03-marker-ambiguous",
            RetrievalQueryKind::MarkerKind,
            spec.ambiguous_marker,
            OfflineExpectedResult::Rejected,
        ),
        case(
            &scope_id,
            "t03-unresolved",
            RetrievalQueryKind::ExactNodeAddress,
            // A projected view id, not a segment id: the citation is unresolvable.
            "v3",
            OfflineExpectedResult::Rejected,
        ),
        case(
            &scope_id,
            "t03-unsafe",
            RetrievalQueryKind::InvalidCandidate,
            "raw_legal_text",
            OfflineExpectedResult::Rejected,
        ),
        case(
            &scope_id,
            "t03-scoped-kind",
            RetrievalQueryKind::ScopedNoCandidate,
            "",
            OfflineExpectedResult::ScopedNoAnswer,
        ),
        case(
            &scope_id,
            "t03-ambiguous-kind",
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
        .expect("every authored case must have an outcome")
}

/// Run a single authored case and return its outcome.
fn run_single(
    fixture: &Fixture,
    resolver: &ProjectionGraphResolver,
    query_kind: RetrievalQueryKind,
    selector: &str,
    expected_result: OfflineExpectedResult,
) -> OfflineCaseOutcome {
    let cases = vec![case(
        resolver.scope_id().as_str(),
        "origin-control",
        query_kind,
        selector,
        expected_result,
    )];
    run_offline_citation_retrieval_cases(&cases, &fixture.projection, resolver)
        .into_iter()
        .next()
        .expect("one outcome per authored case")
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

#[test]
fn resolution_graph_span_set_matches_nav_segment_addresses_for_every_pinned_fixture() {
    for (fixture, _spec) in pinned_fixtures() {
        let resolver = fixture.resolver();
        assert_eq!(
            resolver_segment_ids(&resolver),
            fixture.nav_segments,
            "{}: resolver evidence spans must equal the nav segment-address set",
            fixture.name
        );
        assert_eq!(
            resolver.evidence_span_ids().count(),
            resolver.segment_ids().count(),
            "{}: exactly one evidence span per segment node",
            fixture.name
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
                    "{}: the resolved span must be the segment's own span",
                    fixture.name
                ),
                other => panic!(
                    "{}: segment {segment_id} must resolve uniquely, got {other:?}",
                    fixture.name
                ),
            }
        }
    }
}

#[test]
fn corpus_covers_every_case_class_and_is_mismatch_free() {
    for (fixture, spec) in pinned_fixtures() {
        let resolver = fixture.resolver();
        let cases = corpus(&resolver, &spec);
        let outcomes = run_offline_citation_retrieval_cases(&cases, &fixture.projection, &resolver);
        assert_eq!(outcomes.len(), cases.len());
        assert!(
            outcomes.iter().all(|outcome| outcome.matched),
            "{}: every authored case must match its expected result",
            fixture.name
        );

        let exact = outcome_by_id(&outcomes, "t03-exact");
        assert_eq!(
            exact.selection_reason,
            OfflineSelectionReason::ExactNodeAddressMatch
        );
        assert_eq!(exact.validator_verdict, Some(OutputVerdict::Accepted));
        assert_eq!(exact.primary_code, None);

        let marker = outcome_by_id(&outcomes, "t03-marker-selected");
        assert_eq!(
            marker.selection_reason,
            OfflineSelectionReason::MarkerKindMatch
        );
        assert_eq!(marker.validator_verdict, Some(OutputVerdict::Accepted));

        let marker_scoped = outcome_by_id(&outcomes, "t03-marker-scoped");
        assert_eq!(
            marker_scoped.selection_reason,
            OfflineSelectionReason::ScopedNoCandidate
        );
        assert_eq!(
            marker_scoped.validator_verdict,
            Some(OutputVerdict::AcceptedScopedNoAnswer)
        );

        let marker_ambiguous = outcome_by_id(&outcomes, "t03-marker-ambiguous");
        assert_eq!(
            marker_ambiguous.selection_reason,
            OfflineSelectionReason::AmbiguousCandidateSet
        );
        assert_eq!(marker_ambiguous.validator_verdict, None);

        let unresolved = outcome_by_id(&outcomes, "t03-unresolved");
        assert_eq!(
            unresolved.selection_reason,
            OfflineSelectionReason::UnresolvedCandidateEvidence
        );
        assert_eq!(unresolved.validator_verdict, Some(OutputVerdict::Rejected));
        assert_eq!(
            unresolved.primary_code,
            Some(OutputDiagnosticCode::UnresolvedEvidenceSpan)
        );

        let unsafe_case = outcome_by_id(&outcomes, "t03-unsafe");
        assert_eq!(
            unsafe_case.selection_reason,
            OfflineSelectionReason::UnsafePayloadRejected
        );
        assert_eq!(unsafe_case.validator_verdict, None);

        let scoped_kind = outcome_by_id(&outcomes, "t03-scoped-kind");
        assert_eq!(
            scoped_kind.selection_reason,
            OfflineSelectionReason::ScopedNoCandidate
        );
        assert_eq!(
            scoped_kind.validator_verdict,
            Some(OutputVerdict::AcceptedScopedNoAnswer)
        );

        let ambiguous_kind = outcome_by_id(&outcomes, "t03-ambiguous-kind");
        assert_eq!(
            ambiguous_kind.selection_reason,
            OfflineSelectionReason::AmbiguousCandidateSet
        );
        assert_eq!(ambiguous_kind.validator_verdict, None);

        let summary = run_offline_citation_retrieval_proof(&cases, &fixture.projection, &resolver);
        assert_eq!(summary.total_cases, 8, "{}", fixture.name);
        assert_eq!(summary.selected_count, 2, "{}", fixture.name);
        assert_eq!(summary.scoped_no_answer_count, 2, "{}", fixture.name);
        assert_eq!(summary.rejected_count, 4, "{}", fixture.name);
        assert_eq!(summary.validator_accepted_count, 2, "{}", fixture.name);
        assert_eq!(summary.validator_rejected_count, 1, "{}", fixture.name);
        assert_eq!(summary.mismatch_count, 0, "{}", fixture.name);

        let allowed = allowed_diagnostic_codes();
        assert!(!summary.diagnostic_code_inventory.is_empty());
        for code in &summary.diagnostic_code_inventory {
            assert!(
                allowed.contains(code),
                "{}: unexpected diagnostic code {code}",
                fixture.name
            );
        }
        let mut sorted = summary.diagnostic_code_inventory.clone();
        sorted.sort_unstable();
        sorted.dedup();
        assert_eq!(
            summary.diagnostic_code_inventory, sorted,
            "{}: the code inventory must be sorted and de-duplicated",
            fixture.name
        );
    }
}

#[test]
fn demo_rejects_unresolvable_citation_and_accepts_only_safe_scoped_no_answer() {
    for (fixture, spec) in pinned_fixtures() {
        let resolver = fixture.resolver();
        let cases = corpus(&resolver, &spec);
        let outcomes = run_offline_citation_retrieval_cases(&cases, &fixture.projection, &resolver);

        // The key demo control: an unresolvable citation/id is rejected with the
        // exact fail-closed validator code.
        let unresolved = outcome_by_id(&outcomes, "t03-unresolved");
        assert_eq!(
            unresolved.validator_verdict,
            Some(OutputVerdict::Rejected),
            "{}: an unresolvable citation must be rejected",
            fixture.name
        );
        assert_eq!(
            unresolved.primary_code,
            Some(OutputDiagnosticCode::UnresolvedEvidenceSpan),
            "{}",
            fixture.name
        );

        // A rejection reason never yields an accepted answer, and a safe
        // no-answer is accepted only in the scoped-no-answer shape.
        for outcome in &outcomes {
            if matches!(
                outcome.selection_reason,
                OfflineSelectionReason::UnresolvedCandidateEvidence
                    | OfflineSelectionReason::AmbiguousCandidateSet
                    | OfflineSelectionReason::UnsafePayloadRejected
            ) {
                assert_eq!(
                    outcome.expected_result,
                    OfflineExpectedResult::Rejected,
                    "{}",
                    fixture.name
                );
                assert_ne!(
                    outcome.validator_verdict,
                    Some(OutputVerdict::Accepted),
                    "{}: a rejection must never emit an accepted answer",
                    fixture.name
                );
                assert_ne!(
                    outcome.validator_verdict,
                    Some(OutputVerdict::AcceptedScopedNoAnswer),
                    "{}",
                    fixture.name
                );
            }
        }

        let scoped = outcome_by_id(&outcomes, "t03-marker-scoped");
        assert_eq!(
            scoped.validator_verdict,
            Some(OutputVerdict::AcceptedScopedNoAnswer),
            "{}: a safe scoped no-answer is accepted only as a scoped no-answer",
            fixture.name
        );
        assert_eq!(
            scoped.primary_code,
            Some(OutputDiagnosticCode::ScopedNoAnswer),
            "{}",
            fixture.name
        );

        let summary = run_offline_citation_retrieval_proof(&cases, &fixture.projection, &resolver);
        assert_eq!(summary.mismatch_count, 0, "{}", fixture.name);
    }
}

#[test]
fn origin_control_marker_differentiates_the_pinned_fixtures() {
    let mixed = Fixture::build("mixed-wordml", MIXED_XML, MIXED_SHA256, &MIXED_SENTINELS);
    let mixed_resolver = mixed.resolver();
    let navdemo = Fixture::build(
        "navigation-demo",
        NAVDEMO_XML,
        NAVDEMO_SHA256,
        &NAVDEMO_SENTINELS,
    );
    let navdemo_resolver = navdemo.resolver();

    // `reference:note_reference` matches on `mixed-wordml` (more than one
    // candidate, so the set is ambiguous) and has no match at all on
    // `navigation-demo`, which therefore yields a safe scoped no-answer.
    let mixed_note = run_single(
        &mixed,
        &mixed_resolver,
        RetrievalQueryKind::MarkerKind,
        "reference:note_reference",
        OfflineExpectedResult::Rejected,
    );
    assert_eq!(
        mixed_note.selection_reason,
        OfflineSelectionReason::AmbiguousCandidateSet,
        "mixed-wordml must match the note_reference marker on more than one candidate"
    );
    assert_eq!(mixed_note.validator_verdict, None);

    let navdemo_note = run_single(
        &navdemo,
        &navdemo_resolver,
        RetrievalQueryKind::MarkerKind,
        "reference:note_reference",
        OfflineExpectedResult::ScopedNoAnswer,
    );
    assert_eq!(
        navdemo_note.selection_reason,
        OfflineSelectionReason::ScopedNoCandidate,
        "navigation-demo must have no note_reference candidate"
    );
    assert_eq!(
        navdemo_note.validator_verdict,
        Some(OutputVerdict::AcceptedScopedNoAnswer)
    );

    // `semantic:whitespace` selects exactly one candidate on `mixed-wordml` and
    // none on `navigation-demo`.
    let mixed_ws = run_single(
        &mixed,
        &mixed_resolver,
        RetrievalQueryKind::MarkerKind,
        "semantic:whitespace",
        OfflineExpectedResult::Selected,
    );
    assert_eq!(
        mixed_ws.selection_reason,
        OfflineSelectionReason::MarkerKindMatch
    );
    assert_eq!(mixed_ws.validator_verdict, Some(OutputVerdict::Accepted));

    let navdemo_ws = run_single(
        &navdemo,
        &navdemo_resolver,
        RetrievalQueryKind::MarkerKind,
        "semantic:whitespace",
        OfflineExpectedResult::ScopedNoAnswer,
    );
    assert_eq!(
        navdemo_ws.selection_reason,
        OfflineSelectionReason::ScopedNoCandidate
    );

    // Determinism on a single input is preserved across runs.
    let mixed_ws_again = run_single(
        &mixed,
        &mixed_resolver,
        RetrievalQueryKind::MarkerKind,
        "semantic:whitespace",
        OfflineExpectedResult::Selected,
    );
    assert_eq!(mixed_ws, mixed_ws_again);
}

#[test]
fn proof_run_is_deterministic_and_does_not_mutate_the_projection() {
    for (fixture, spec) in pinned_fixtures() {
        let resolver = fixture.resolver();
        let before = fixture.projection.clone();
        let cases = corpus(&resolver, &spec);

        let first_outcomes =
            run_offline_citation_retrieval_cases(&cases, &fixture.projection, &resolver);
        let first_summary =
            run_offline_citation_retrieval_proof(&cases, &fixture.projection, &resolver);
        let second_outcomes =
            run_offline_citation_retrieval_cases(&cases, &fixture.projection, &resolver);
        let second_summary =
            run_offline_citation_retrieval_proof(&cases, &fixture.projection, &resolver);

        assert_eq!(first_outcomes, second_outcomes, "{}", fixture.name);
        assert_eq!(first_summary, second_summary, "{}", fixture.name);
        assert_eq!(
            fixture.projection, before,
            "{}: the proof run must not mutate the borrowed projection",
            fixture.name
        );
    }
}

#[test]
fn diagnostics_stay_bounded_and_carry_no_fixture_text() {
    for (fixture, spec) in pinned_fixtures() {
        let resolver = fixture.resolver();
        let cases = corpus(&resolver, &spec);
        let summary = run_offline_citation_retrieval_proof(&cases, &fixture.projection, &resolver);
        let outcomes = run_offline_citation_retrieval_cases(&cases, &fixture.projection, &resolver);

        for entry in &summary.diagnostic_code_inventory {
            for sentinel in fixture.sentinels {
                assert!(
                    !entry.contains(sentinel),
                    "{}: a diagnostic code leaked fixture text: {entry}",
                    fixture.name
                );
            }
        }
        for outcome in &outcomes {
            for sentinel in fixture.sentinels {
                assert!(!outcome.case_id.contains(sentinel), "{}", fixture.name);
                assert!(!outcome.query_id.contains(sentinel), "{}", fixture.name);
                assert!(
                    !outcome.selection_reason.as_str().contains(sentinel),
                    "{}",
                    fixture.name
                );
                if let Some(code) = outcome.primary_code {
                    assert!(!code.as_str().contains(sentinel), "{}", fixture.name);
                }
            }
        }
    }
}

#[test]
fn validator_still_rejects_forbidden_payload_and_unknown_namespace() {
    for (fixture, _spec) in pinned_fixtures() {
        let resolver = fixture.resolver();
        let scope = OutputScope::new(
            resolver.scope_id().clone(),
            QueryId::parse("Q-neg").expect("a valid query id"),
            RetrievalRunId::parse("RUN-neg").expect("a valid run id"),
            ScopeAsOfDate::parse("2024-06-15").expect("a valid as-of date"),
            resolver.source_corpus_id().clone(),
            ValidatorContractVersion::parse(VALIDATOR_CONTRACT_VERSION)
                .expect("the frozen contract version token"),
        );

        let forbidden = RetrievalOutputEnvelope {
            retrieval_output_id: FieldShape::Value(
                RetrievalOutputId::parse("RET-neg").expect("a valid output id"),
            ),
            output_kind: FieldShape::Value(OutputKind::RetrievalCandidate),
            scope: ScopeShape::Complete(scope.clone()),
            citations: FieldShape::Value(Vec::new()),
            answer_claims: FieldShape::Value(Vec::new()),
            extra_field_names: vec![
                BoundedToken::parse("raw_legal_text").expect("a bounded token"),
            ],
        };
        let outcome = validate_retrieval_output(&forbidden, &resolver);
        assert_eq!(
            outcome.verdict(),
            OutputVerdict::Rejected,
            "{}",
            fixture.name
        );
        assert_eq!(
            outcome.primary_code(),
            Some(OutputDiagnosticCode::ForbiddenPayloadField),
            "{}",
            fixture.name
        );

        let unknown_namespace = RetrievalOutputEnvelope {
            retrieval_output_id: FieldShape::Value(
                RetrievalOutputId::parse("NOPE-neg").expect("a bounded id token"),
            ),
            output_kind: FieldShape::Value(OutputKind::RetrievalCandidate),
            scope: ScopeShape::Complete(scope),
            citations: FieldShape::Value(Vec::new()),
            answer_claims: FieldShape::Value(Vec::new()),
            extra_field_names: Vec::new(),
        };
        let outcome = validate_retrieval_output(&unknown_namespace, &resolver);
        assert_eq!(
            outcome.verdict(),
            OutputVerdict::Rejected,
            "{}",
            fixture.name
        );
        assert_eq!(
            outcome.primary_code(),
            Some(OutputDiagnosticCode::UnknownIdNamespace),
            "{}",
            fixture.name
        );
    }
}
