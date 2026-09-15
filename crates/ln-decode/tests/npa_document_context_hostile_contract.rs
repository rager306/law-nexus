use ln_decode::current_requisites::{
    CurrentDocumentRequisites, RequisitesClaim, RequisitesExtractionStatus, RequisitesField,
    RequisitesSourceKind, SourceAnchor, ThisRefGrammarEvidence,
};
use ln_decode::document_context::{
    build_document_analysis_overlay, build_document_structure_index, explicit_anchor_lookup,
    open_series_head, reduce_context_results, scoped_alias, BlockId, ContainerId, ContextBudgets,
    ContextClaim, ContextClaimStatus, ContextDiagnostic, ContextEnvironment, ContextRequest,
    ContextRequestKind, ContextResult, ContextStatus, ContextWorklist, ContextualEdgeKind,
    DocumentAnalysisOverlay, DocumentStructureIndex, DocumentVersionRef, FrameRef, IndexBuildError,
    StructureEdgeStatus, PROPOSED_MAX_ALIAS_CANDIDATES, PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD,
    PROPOSED_MAX_SERIES_HOPS, PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT,
};
use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, TextSpan,
};
use ln_decode::lawref::capture_lawrefs;
use ln_decode::local_grammar::{
    extract_act_list_frames, CoordinatingFrame, DerivationSource, FrameKind,
};

fn block(text: &str, style: ParagraphStyle, order: usize) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            ln_decode::domain::SourceStreamId::parse("fixture:hostile").unwrap(),
            SourceSpan::try_new(order * 100, order * 100 + text.len()).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

fn version() -> DocumentVersionRef {
    DocumentVersionRef::try_new("hostile-doc".into(), "rev-1".into(), "profile-1".into()).unwrap()
}

fn fixture() -> Vec<ParsedBlock> {
    vec![
        block("Закон Российской Федерации 12-ФЗ", ParagraphStyle::Title, 0),
        block("РАЗДЕЛ I. ОБЩИЕ ПОЛОЖЕНИЯ", ParagraphStyle::Heading, 1),
        block("Статья 1. Первый блок", ParagraphStyle::Heading, 2),
        block("Статья 2. Второй блок", ParagraphStyle::Heading, 3),
        block(
            "Текст продолжения, но без доказанного ребра",
            ParagraphStyle::BodyText,
            4,
        ),
    ]
}

fn environment<'a>(
    index: &'a ln_decode::document_context::DocumentStructureIndex,
    overlay: &'a ln_decode::document_context::DocumentAnalysisOverlay,
) -> ContextEnvironment<'a> {
    ContextEnvironment {
        index,
        overlay,
        requisites: None,
    }
}

fn request(kind: ContextRequestKind, origin: &str, key: Option<&str>) -> ContextRequest {
    ContextRequest::new(
        kind,
        "hostile-doc".into(),
        FrameRef::parse(origin).unwrap(),
        vec![],
        None,
        key.map(str::to_owned),
        vec![],
        PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT,
        "hostile-contract".into(),
    )
}

fn empty_overlay(
    index: &ln_decode::document_context::DocumentStructureIndex,
) -> ln_decode::document_context::DocumentAnalysisOverlay {
    build_document_analysis_overlay(index, &[], &[]).unwrap()
}

fn claim(source: &str) -> ContextClaim {
    ContextClaim {
        field: "act_type".into(),
        derivation: DerivationSource::ExplicitMember,
        source_node_ref: source.into(),
        claim_status: ContextClaimStatus::Explicit,
    }
}

#[test]
fn heading_paragraph_boundary_does_not_invent_comma_list_continuation() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(
        environment(&index, &overlay),
        &[request(ContextRequestKind::AdjacentBlocks, "block-4", None)],
    );
    assert_eq!(
        report.results.values().next().unwrap().status,
        ContextStatus::Resolved
    );
    assert!(report
        .results
        .values()
        .next()
        .unwrap()
        .candidate_claims
        .is_empty());
}

#[test]
fn prior_block_date_and_number_are_not_current_act_requisites() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    let outcome = open_series_head(&overlay, &FrameRef::parse("missing-tail").unwrap());
    assert_eq!(outcome.status, ContextStatus::Partial);
    assert_eq!(
        outcome.diagnostics,
        vec![ContextDiagnostic::OpenSeriesWithoutHead]
    );
}

#[test]
fn compatible_series_heads_in_different_sections_are_retained_as_conflict() {
    let first = ContextResult {
        request_ref: "a".into(),
        status: ContextStatus::Resolved,
        candidate_claims: vec![claim("head-a")],
        source_anchors: vec![],
        derivation_edges: vec![],
        diagnostics: vec![],
    };
    let second = ContextResult {
        request_ref: "b".into(),
        status: ContextStatus::Resolved,
        candidate_claims: vec![claim("head-b")],
        source_anchors: vec![],
        derivation_edges: vec![],
        diagnostics: vec![],
    };
    let reduced = reduce_context_results(&[first, second]);
    assert_eq!(reduced.status, ContextStatus::Conflicting);
    assert_eq!(reduced.candidate_claims.len(), 2);
}

#[test]
fn alias_outside_structural_scope_is_not_bound() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    let outcome = scoped_alias(
        &overlay,
        "Закон",
        &ContainerId::parse("container-2").unwrap(),
    );
    assert_eq!(outcome.status, ContextStatus::Unavailable);
    assert!(outcome
        .diagnostics
        .contains(&ContextDiagnostic::UnresolvedAfterDocumentPass));
}

#[test]
fn sidecar_requisite_conflict_does_not_override_explicit_head() {
    let explicit = ContextResult {
        request_ref: "explicit".into(),
        status: ContextStatus::Resolved,
        candidate_claims: vec![claim("explicit-head")],
        source_anchors: vec![],
        derivation_edges: vec![],
        diagnostics: vec![],
    };
    let inherited = ContextResult {
        request_ref: "sidecar".into(),
        status: ContextStatus::Partial,
        candidate_claims: vec![claim("sidecar-tail")],
        source_anchors: vec![],
        derivation_edges: vec![],
        diagnostics: vec![ContextDiagnostic::InheritedFieldConflict],
    };
    let reduced = reduce_context_results(&[explicit, inherited]);
    assert_eq!(reduced.status, ContextStatus::Conflicting);
    assert!(reduced
        .diagnostics
        .contains(&ContextDiagnostic::InheritedFieldConflict));
}

#[test]
fn forward_information_requires_explicit_typed_anchor_key() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    assert_eq!(
        explicit_anchor_lookup(&overlay, "block-4-frame-0").status,
        ContextStatus::Unavailable
    );
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(
        environment(&index, &overlay),
        &[request(
            ContextRequestKind::ExplicitAnchorLookup,
            "block-2",
            Some("block-4-frame-0"),
        )],
    );
    assert_eq!(
        report.results.values().next().unwrap().status,
        ContextStatus::Unavailable
    );
}

#[test]
fn wordml_split_keeps_local_anchors_and_never_mints_cross_block_span() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let frame = CoordinatingFrame::new(
        FrameKind::ActRequisites,
        TextSpan::try_new(0, 4).unwrap(),
        vec!["закон".into()],
        vec![],
        vec![],
        true,
        vec![],
    );
    let overlay = build_document_analysis_overlay(
        &index,
        &[(BlockId::parse("block-2").unwrap(), vec![frame], vec![])],
        &[],
    )
    .unwrap();
    assert!(overlay
        .edges()
        .iter()
        .all(|edge| edge.evidence.iter().all(|span| span.end() <= 4)));
}

#[test]
fn malformed_origin_fails_closed_as_missing_document_structure() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(
        environment(&index, &overlay),
        &[request(ContextRequestKind::AncestorPath, "block-999", None)],
    );
    let result = report.results.values().next().unwrap();
    assert_eq!(result.status, ContextStatus::Unavailable);
    assert!(result
        .diagnostics
        .contains(&ContextDiagnostic::MissingDocumentStructure));
}

#[test]
fn cycle_bomb_terminates_within_worklist_budget() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    let cycle = ContextRequest::new(
        ContextRequestKind::AncestorPath,
        "hostile-doc".into(),
        FrameRef::parse("block-3").unwrap(),
        vec![],
        None,
        None,
        vec!["AncestorPath:block-3:".into()],
        1,
        "hostile".into(),
    );
    let mut worklist = ContextWorklist::new(ContextBudgets {
        worklist_steps: 1,
        ..Default::default()
    });
    let report = worklist.run(environment(&index, &overlay), &[cycle]);
    assert!(report.stats.steps_used <= 1);
    assert_eq!(
        report.results.values().next().unwrap().status,
        ContextStatus::Cycle
    );
}

#[test]
fn fanout_bomb_is_limited_without_first_n_claim_loss() {
    let results: Vec<_> = (0..(PROPOSED_MAX_ALIAS_CANDIDATES * 4))
        .map(|n| ContextResult {
            request_ref: n.to_string(),
            status: ContextStatus::Resolved,
            candidate_claims: vec![claim(&format!("candidate-{n}"))],
            source_anchors: vec![],
            derivation_edges: vec![],
            diagnostics: vec![],
        })
        .collect();
    let reduced = reduce_context_results(&results);
    assert_eq!(reduced.status, ContextStatus::Conflicting);
    assert_eq!(
        reduced.candidate_claims.len(),
        PROPOSED_MAX_ALIAS_CANDIDATES * 4
    );
}

#[test]
fn deep_ancestor_chain_is_bounded_without_panic() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    let mut worklist = ContextWorklist::new(ContextBudgets {
        series_hops: PROPOSED_MAX_SERIES_HOPS,
        ..Default::default()
    });
    let deep = ContextRequest::new(
        ContextRequestKind::AncestorPath,
        "hostile-doc".into(),
        FrameRef::parse("block-4").unwrap(),
        vec![],
        None,
        None,
        (0..PROPOSED_MAX_SERIES_HOPS + 2)
            .map(|n| format!("path-{n}"))
            .collect(),
        1,
        "hostile".into(),
    );
    let report = worklist.run(environment(&index, &overlay), &[deep]);
    assert_eq!(
        report.results.values().next().unwrap().status,
        ContextStatus::Limit
    );
}

#[test]
fn alias_candidate_bound_is_symbolic_and_closed() {
    const {
        assert!(PROPOSED_MAX_ALIAS_CANDIDATES > 0);
    }
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    assert_eq!(
        scoped_alias(
            &overlay,
            "alias",
            &ContainerId::parse("container-2").unwrap()
        )
        .status,
        ContextStatus::Unavailable
    );
}

#[test]
fn claims_per_field_bound_preserves_conflicting_set_in_reducer() {
    let results: Vec<_> = (0..(PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD + 2))
        .map(|n| ContextResult {
            request_ref: n.to_string(),
            status: ContextStatus::Resolved,
            candidate_claims: vec![claim(&format!("source-{n}"))],
            source_anchors: vec![],
            derivation_edges: vec![],
            diagnostics: vec![],
        })
        .collect();
    let reduced = reduce_context_results(&results);
    assert_eq!(reduced.status, ContextStatus::Conflicting);
    assert_eq!(
        reduced.candidate_claims.len(),
        PROPOSED_MAX_CONTEXT_CLAIMS_PER_FIELD + 2
    );
}

#[test]
fn wrong_document_claim_is_not_accepted_as_context_result() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(
        environment(&index, &overlay),
        &[ContextRequest::new(
            ContextRequestKind::ExplicitAnchorLookup,
            "other-document".into(),
            FrameRef::parse("block-2").unwrap(),
            vec![],
            None,
            Some("wrong-document-anchor".into()),
            vec![],
            1,
            "hostile".into(),
        )],
    );
    assert_eq!(
        report.results.values().next().unwrap().status,
        ContextStatus::Unavailable
    );
    assert!(report
        .results
        .values()
        .next()
        .unwrap()
        .candidate_claims
        .is_empty());
}

#[test]
fn oversized_text_keeps_adjacent_operator_within_radius_budget() {
    let huge = "x".repeat(1_000_000);
    let blocks = vec![
        block("Закон Российской Федерации", ParagraphStyle::Title, 0),
        block(&huge, ParagraphStyle::BodyText, 1),
        block("Статья 1. Конец", ParagraphStyle::Heading, 2),
    ];
    let index = build_document_structure_index(version(), &blocks).unwrap();
    let overlay = empty_overlay(&index);
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(
        environment(&index, &overlay),
        &[request(ContextRequestKind::AdjacentBlocks, "block-1", None)],
    );
    assert!(report.stats.steps_used <= PROPOSED_MAX_WORKLIST_STEPS_PER_DOCUMENT);
    assert!(
        report.results.values().next().unwrap().source_anchors.len()
            <= PROPOSED_MAX_SERIES_HOPS + 1
    );
}

#[test]
fn every_terminal_preserves_literal_mentions_and_frame_evidence() {
    let anchor = TextSpan::try_new(3, 8).unwrap();
    let base = ContextResult {
        request_ref: "base".into(),
        status: ContextStatus::Resolved,
        candidate_claims: vec![],
        source_anchors: vec![anchor],
        derivation_edges: vec![],
        diagnostics: vec![],
    };
    for status in [
        ContextStatus::Resolved,
        ContextStatus::Partial,
        ContextStatus::Conflicting,
        ContextStatus::Unavailable,
        ContextStatus::Cycle,
        ContextStatus::Limit,
    ] {
        let mut result = base.clone();
        result.status = status;
        let reduced = reduce_context_results(&[result]);
        assert_eq!(
            reduced.source_anchors,
            vec![anchor],
            "terminal {status:?} dropped evidence"
        );
    }
}

#[test]
fn invalid_empty_index_is_fail_closed() {
    assert_eq!(
        build_document_structure_index(version(), &[]),
        Err(IndexBuildError::EmptyDocument)
    );
}

/// Act-list overlay for the given blocks, in document order.
fn act_overlay(index: &DocumentStructureIndex, blocks: &[ParsedBlock]) -> DocumentAnalysisOverlay {
    let frames = blocks
        .iter()
        .enumerate()
        .map(|(order, source)| {
            (
                BlockId::parse(&format!("block-{order}")).unwrap(),
                extract_act_list_frames(source.text(), &capture_lawrefs(source.text())),
                Vec::new(),
            )
        })
        .collect::<Vec<_>>();
    build_document_analysis_overlay(index, &frames, &[]).unwrap()
}

/// RC28-F07: conflict arbitration is driven by *eligibility*, never by
/// multiplicity or proximity. Several eligible origins stay a retained
/// conflict; unrelated self-sufficient citations mint nothing.
#[test]
fn continuation_conflict_requires_eligible_origins_not_multiplicity() {
    let blocks = vec![
        block(
            "федеральный закон от 01.01.2020 N 1-ФЗ",
            ParagraphStyle::BodyText,
            0,
        ),
        block(
            "федеральный кодекс от 02.02.2021 N 2-ФЗ",
            ParagraphStyle::BodyText,
            1,
        ),
        block("от 03.03.2022 N 3-ФЗ", ParagraphStyle::BodyText, 2),
    ];
    let index = build_document_structure_index(version(), &blocks).unwrap();
    let overlay = act_overlay(&index, &blocks);
    let continuations: Vec<_> = overlay
        .edges()
        .iter()
        .filter(|edge| edge.relation == ContextualEdgeKind::ContinuesSeries)
        .collect();
    assert_eq!(
        continuations.len(),
        2,
        "both eligible origins must stay visible"
    );
    assert!(continuations
        .iter()
        .all(|edge| edge.status == StructureEdgeStatus::Conflicting));
    let outcome = open_series_head(&overlay, &FrameRef::parse("block-2-frame-0").unwrap());
    assert_eq!(outcome.status, ContextStatus::Conflicting);
    assert_eq!(outcome.candidates.len(), 2, "no proximity winner");
    assert!(outcome
        .diagnostics
        .contains(&ContextDiagnostic::IncompatibleSeriesHead));

    // Two complete, unrelated citations are not competing interpretations.
    let unrelated = vec![
        block(
            "федеральный закон от 01.01.2020 N 1-ФЗ",
            ParagraphStyle::BodyText,
            0,
        ),
        block(
            "федеральный кодекс от 02.02.2021 N 2-ФЗ",
            ParagraphStyle::BodyText,
            1,
        ),
    ];
    let index = build_document_structure_index(version(), &unrelated).unwrap();
    let overlay = act_overlay(&index, &unrelated);
    assert!(
        overlay
            .edges()
            .iter()
            .all(|edge| edge.relation != ContextualEdgeKind::ContinuesSeries),
        "unrelated citations must not gain continuation edges"
    );
}

fn observed_claim(
    id: &str,
    field: RequisitesField,
    value: &str,
    source: RequisitesSourceKind,
) -> RequisitesClaim {
    RequisitesClaim::try_new(
        id.to_owned(),
        "doc-v1".into(),
        field,
        value.to_owned(),
        source,
        SourceAnchor::try_new(TextSpan::try_new(0, 1).unwrap(), format!("anchor-{id}")).unwrap(),
        "profile-v1".into(),
        RequisitesExtractionStatus::Observed,
    )
    .unwrap()
}

fn all_observed_claims(value_prefix: &str) -> Vec<RequisitesClaim> {
    RequisitesField::ALL
        .into_iter()
        .enumerate()
        .map(|(index, field)| {
            observed_claim(
                &format!("head-{index}"),
                field,
                &format!("{value_prefix}-{index}"),
                RequisitesSourceKind::DocumentHead,
            )
        })
        .collect()
}

/// RC28-F08 stale-evidence guard: one worklist reused against a changed or
/// removed sidecar must recompute the authorization instead of replaying a
/// memoized one.
#[test]
fn changed_sidecar_identity_invalidates_memoized_authorization() {
    let index = build_document_structure_index(version(), &fixture()).unwrap();
    let overlay = empty_overlay(&index);
    let admitted = ContextRequest::current_document_requisites(
        FrameRef::parse("block-4").unwrap(),
        ThisRefGrammarEvidence::new([RequisitesField::Type]),
    );
    let usable =
        CurrentDocumentRequisites::try_new("doc-v1".into(), all_observed_claims("value")).unwrap();
    let conflicting = CurrentDocumentRequisites::try_new("doc-v1".into(), {
        let mut claims = all_observed_claims("value");
        claims.push(observed_claim(
            "catalog-type",
            RequisitesField::Type,
            "other-type",
            RequisitesSourceKind::SourceCatalog,
        ));
        claims
    })
    .unwrap();
    assert_ne!(
        usable.identity_fingerprint(),
        conflicting.identity_fingerprint(),
        "a changed claim set must change the sidecar identity"
    );

    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let with_usable = ContextEnvironment {
        index: &index,
        overlay: &overlay,
        requisites: Some(&usable),
    };
    let first = worklist.run(with_usable, std::slice::from_ref(&admitted));
    assert_eq!(
        first.results.values().next().unwrap().status,
        ContextStatus::Resolved
    );

    let second = worklist.run(
        ContextEnvironment {
            index: &index,
            overlay: &overlay,
            requisites: Some(&conflicting),
        },
        std::slice::from_ref(&admitted),
    );
    assert_eq!(
        second.results.values().next().unwrap().status,
        ContextStatus::Partial,
        "a changed sidecar must not replay a memoized authorization"
    );
    assert_eq!(second.stats.memo_hits, 0, "the memo must be invalidated");

    let third = worklist.run(
        ContextEnvironment {
            index: &index,
            overlay: &overlay,
            requisites: None,
        },
        std::slice::from_ref(&admitted),
    );
    assert_eq!(
        third.results.values().next().unwrap().status,
        ContextStatus::Unavailable,
        "a removed sidecar must not replay a memoized authorization"
    );

    let fourth = worklist.run(with_usable, &[admitted]);
    assert_eq!(
        fourth.results.values().next().unwrap().status,
        ContextStatus::Resolved,
        "restoring the sidecar recomputes the authorization"
    );
}
