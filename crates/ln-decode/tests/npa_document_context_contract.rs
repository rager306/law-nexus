use ln_decode::document_context::{
    build_document_analysis_overlay, build_document_structure_index, reduce_context_results,
    BlockId, ContainerRole, ContextBudgets, ContextEnvironment, ContextPhase, ContextRequest,
    ContextRequestKind, ContextStatus, ContextTransition, ContextWorklist, DocumentVersionRef,
    FrameRef, IndexBuildError, MAX_LINKING_PASSES, PROPOSED_MAX_ADJACENT_RADIUS,
};
use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};

fn block(text: &str, style: ParagraphStyle, order: usize) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:context").unwrap(),
            SourceSpan::try_new(order * 100, order * 100 + text.len()).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

fn fixture() -> Vec<ParsedBlock> {
    vec![
        block("Закон Российской Федерации 12-ФЗ", ParagraphStyle::Title, 0),
        block("РАЗДЕЛ I. ОБЩИЕ ПОЛОЖЕНИЯ", ParagraphStyle::Heading, 1),
        block(
            "Статья 1. Предмет регулирования",
            ParagraphStyle::Heading,
            2,
        ),
        block(
            "Настоящий закон устанавливает правила.",
            ParagraphStyle::BodyText,
            3,
        ),
    ]
}

#[test]
fn index_has_source_and_structural_nodes_with_closed_roles_and_edges() {
    let version =
        DocumentVersionRef::try_new("doc-v1".into(), "rev-1".into(), "profile-1".into()).unwrap();
    let index = build_document_structure_index(version, &fixture()).unwrap();
    assert_eq!(index.source_blocks().len(), 4);
    assert_eq!(index.containers().len(), 4); // document, requisites, division, article
    assert!(index
        .containers()
        .iter()
        .all(|n| ContainerRole::ALL.contains(&n.role())));
    assert!(index
        .edges()
        .iter()
        .any(|e| e.from() == "block-3" && e.to() == "container-2"));
    assert!(index
        .edges()
        .iter()
        .any(|e| e.relation()
            == ln_decode::document_context::StructureEdgeRelation::ImmediatelyPrecedes));
}

#[test]
fn ancestor_path_is_nearest_first_and_adjacent_is_bounded() {
    let version =
        DocumentVersionRef::try_new("doc-v1".into(), "rev-1".into(), "profile-1".into()).unwrap();
    let index = build_document_structure_index(version, &fixture()).unwrap();
    let path = index
        .ancestor_path(&BlockId::parse("block-3").unwrap())
        .unwrap();
    assert_eq!(path[0].role(), ContainerRole::Article);
    assert_eq!(path.last().unwrap().role(), ContainerRole::Document);
    let adjacent = index.adjacent_blocks(
        &BlockId::parse("block-3").unwrap(),
        PROPOSED_MAX_ADJACENT_RADIUS,
    );
    assert_eq!(
        adjacent.len(),
        3usize.min(PROPOSED_MAX_ADJACENT_RADIUS),
        "fixture cardinality is bounded by the proposed radius"
    );
    assert!(adjacent.iter().all(|b| b.order() < 3));
}

#[test]
fn empty_and_conflicting_structure_fail_closed() {
    let version =
        DocumentVersionRef::try_new("doc-v1".into(), "rev-1".into(), "profile-1".into()).unwrap();
    assert_eq!(
        build_document_structure_index(version.clone(), &[]),
        Err(IndexBuildError::EmptyDocument)
    );
    let conflict = vec![block(
        "РАЗДЕЛ I. Статья 1. Спор",
        ParagraphStyle::Heading,
        0,
    )];
    assert_eq!(
        build_document_structure_index(version, &conflict),
        Err(IndexBuildError::ConflictingRoleEvidence)
    );
}

#[test]
fn context_fsm_accepts_all_contract_transitions_and_rejects_invalid_ones() {
    let cases = [
        (
            ContextPhase::NotEvaluated,
            ContextTransition::TypedContextRequestEmitted,
            ContextPhase::Requested,
        ),
        (
            ContextPhase::Requested,
            ContextTransition::RequestSchemaAndBudgetPass,
            ContextPhase::Queued,
        ),
        (
            ContextPhase::Queued,
            ContextTransition::DeterministicWorklistDispatch,
            ContextPhase::Resolving,
        ),
        (
            ContextPhase::Resolving,
            ContextTransition::UniqueAuthorizedClaimSet,
            ContextPhase::Resolved,
        ),
        (
            ContextPhase::Resolving,
            ContextTransition::MissingNoncriticalContext,
            ContextPhase::Partial,
        ),
        (
            ContextPhase::Resolving,
            ContextTransition::IncompatibleAuthorizedClaims,
            ContextPhase::Conflicting,
        ),
        (
            ContextPhase::Resolving,
            ContextTransition::IndexOrSidecarUnavailable,
            ContextPhase::Unavailable,
        ),
        (
            ContextPhase::Resolving,
            ContextTransition::RepeatedDerivationPath,
            ContextPhase::Cycle,
        ),
        (
            ContextPhase::Resolving,
            ContextTransition::DeclaredBudgetReached,
            ContextPhase::Limit,
        ),
    ];
    for (from, transition, expected) in cases {
        assert_eq!(from.transition(transition), Some(expected));
        assert_eq!(
            expected.transition(ContextTransition::TypedContextRequestEmitted),
            None
        );
    }
    assert_eq!(
        ContextPhase::Resolving.transition(ContextTransition::TypedContextRequestEmitted),
        None
    );
}

#[test]
fn this_ref_grammar_is_exact_and_returns_local_spans() {
    let spans = ln_decode::document_context::detect_this_ref_grammar(
        "Ссылка на настоящего Закона; настоящий закон не подходит.",
    );
    assert_eq!(spans.len(), 1);
    assert_eq!(spans[0].start(), 18);
    assert_eq!(spans[0].end(), 51);
}

#[test]
fn aliases_use_closed_markers_and_preserve_scope() {
    let scope = ln_decode::document_context::ContainerId::parse("container-2").unwrap();
    let aliases = ln_decode::document_context::detect_declared_aliases(
        "Федеральный закон (далее — Закон) действует.",
        scope.clone(),
    );
    assert_eq!(aliases.len(), 1);
    assert_eq!(aliases[0].wording, "Закон");
    assert_eq!(aliases[0].declaration_anchor.start(), 34);
    assert_eq!(aliases[0].declaration_anchor.end(), 61);
    assert_eq!(aliases[0].scope_container_id, scope);
    assert!(ln_decode::document_context::detect_declared_aliases(
        "Федеральный закон (далее: Закон) действует.",
        aliases[0].scope_container_id.clone(),
    )
    .is_empty());
}

#[test]
fn worklist_is_deterministic_and_replays_memoized_results_without_mutating_inputs() {
    let version =
        DocumentVersionRef::try_new("doc-v1".into(), "rev-1".into(), "profile-1".into()).unwrap();
    let index = build_document_structure_index(version, &fixture()).unwrap();
    let overlay = build_document_analysis_overlay(&index, &[], &[]).unwrap();
    let before_index = index.clone();
    let before_overlay = overlay.clone();
    let requests = vec![
        ContextRequest::new(
            ContextRequestKind::AdjacentBlocks,
            "doc-v1".into(),
            ln_decode::document_context::FrameRef::parse("block-3").unwrap(),
            vec!["adjacent".into()],
            None,
            None,
            vec![],
            2,
            "structural".into(),
        ),
        ContextRequest::new(
            ContextRequestKind::AncestorPath,
            "doc-v1".into(),
            ln_decode::document_context::FrameRef::parse("block-3").unwrap(),
            vec!["article".into()],
            None,
            None,
            vec![],
            2,
            "structural".into(),
        ),
    ];
    let environment = ContextEnvironment {
        index: &index,
        overlay: &overlay,
        requisites: None,
    };
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let first = worklist.run(environment, &requests);
    let second = worklist.run(environment, &requests);
    assert_eq!(first.results, second.results);
    assert_eq!(
        first.results.keys().collect::<Vec<_>>(),
        second.results.keys().collect::<Vec<_>>()
    );
    assert_eq!(second.stats.memo_hits, requests.len());
    assert_eq!(index, before_index);
    assert_eq!(overlay, before_overlay);
    assert_eq!(
        first.stats.terminal_distribution[&ContextStatus::Resolved],
        2
    );
}

#[test]
fn worklist_cycle_and_global_limit_are_typed_and_bounded() {
    let version =
        DocumentVersionRef::try_new("doc-v1".into(), "rev-1".into(), "profile-1".into()).unwrap();
    let index = build_document_structure_index(version, &fixture()).unwrap();
    let overlay = build_document_analysis_overlay(&index, &[], &[]).unwrap();
    let cycle = ContextRequest::new(
        ContextRequestKind::AncestorPath,
        "doc-v1".into(),
        ln_decode::document_context::FrameRef::parse("block-3").unwrap(),
        vec![],
        None,
        None,
        vec!["AncestorPath:block-3:".into()],
        1,
        "structural".into(),
    );
    let limited = ContextRequest::new(
        ContextRequestKind::AdjacentBlocks,
        "doc-v1".into(),
        ln_decode::document_context::FrameRef::parse("block-3").unwrap(),
        vec![],
        None,
        None,
        vec![],
        1,
        "structural".into(),
    );
    let environment = ContextEnvironment {
        index: &index,
        overlay: &overlay,
        requisites: None,
    };
    let mut cycle_worklist = ContextWorklist::new(ContextBudgets {
        worklist_steps: 4,
        ..Default::default()
    });
    let cycle_report = cycle_worklist.run(environment, &[cycle]);
    assert_eq!(
        cycle_report.results.values().next().unwrap().status,
        ContextStatus::Cycle
    );
    let mut limited_worklist = ContextWorklist::new(ContextBudgets {
        worklist_steps: 0,
        ..Default::default()
    });
    let limited_report = limited_worklist.run(environment, &[limited]);
    let limited_result = limited_report.results.values().next().unwrap();
    assert_eq!(limited_result.status, ContextStatus::Limit);
    assert!(limited_result
        .diagnostics
        .contains(&ln_decode::document_context::ContextDiagnostic::ContextQueryLimitReached));
}

#[test]
fn reducer_collapses_equal_claims_and_retains_conflicting_alternatives() {
    use ln_decode::document_context::{ContextClaim, ContextClaimStatus, ContextResult};
    use ln_decode::local_grammar::DerivationSource;
    let claim = ContextClaim {
        field: "type".into(),
        derivation: DerivationSource::SameSeriesHead,
        source_node_ref: "head-a".into(),
        claim_status: ContextClaimStatus::Inherited,
    };
    let equal = ContextResult {
        request_ref: "a".into(),
        status: ContextStatus::Resolved,
        candidate_claims: vec![claim.clone()],
        source_anchors: vec![],
        derivation_edges: vec![],
        diagnostics: vec![],
    };
    assert_eq!(
        reduce_context_results(&[equal.clone(), equal.clone()]).status,
        ContextStatus::Resolved
    );
    let conflict = ContextResult {
        request_ref: "b".into(),
        status: ContextStatus::Resolved,
        candidate_claims: vec![ContextClaim {
            source_node_ref: "head-b".into(),
            ..claim
        }],
        source_anchors: vec![],
        derivation_edges: vec![],
        diagnostics: vec![],
    };
    let reduced = reduce_context_results(std::slice::from_ref(&conflict));
    assert_eq!(reduced.status, ContextStatus::Resolved);
    let reduced = reduce_context_results(&[equal, conflict]);
    assert_eq!(reduced.status, ContextStatus::Conflicting);
    assert_eq!(reduced.candidate_claims.len(), 2);
}

#[test]
fn typed_request_and_terminal_status_are_closed() {
    let evidence = ln_decode::current_requisites::ThisRefGrammarEvidence::new([]);
    let request = ln_decode::document_context::ContextRequest::current_document_requisites(
        ln_decode::document_context::FrameRef::parse("frame-1").unwrap(),
        evidence,
    );
    assert_eq!(
        request.kind(),
        ContextRequestKind::CurrentDocumentRequisites
    );
    assert_eq!(MAX_LINKING_PASSES, 1);
    const TERMINALS: [ContextStatus; 6] = [
        ContextStatus::Resolved,
        ContextStatus::Partial,
        ContextStatus::Conflicting,
        ContextStatus::Unavailable,
        ContextStatus::Cycle,
        ContextStatus::Limit,
    ];
    assert!(TERMINALS.contains(&ContextStatus::Cycle));
}

/// RC28-F08 port contract: the legacy `evidence_requirement` label is an
/// opaque label, never an authorization. Only typed evidence persisted on the
/// request can authorize, and that evidence is part of the memo identity, so
/// two different authorizations can never collapse into one memoized result.
#[test]
fn typed_request_evidence_is_the_only_authorization_route() {
    use ln_decode::current_requisites::{
        CurrentDocumentRequisites, RequisitesClaim, RequisitesExtractionStatus, RequisitesField,
        RequisitesSourceKind, SourceAnchor, ThisRefGrammarEvidence,
    };
    use ln_decode::domain::TextSpan;

    let version =
        DocumentVersionRef::try_new("doc-v1".into(), "rev-1".into(), "profile-1".into()).unwrap();
    let index = build_document_structure_index(version, &fixture()).unwrap();
    let overlay = build_document_analysis_overlay(&index, &[], &[]).unwrap();
    let claims: Vec<_> = RequisitesField::ALL
        .into_iter()
        .enumerate()
        .map(|(index, field)| {
            RequisitesClaim::try_new(
                format!("head-{index}"),
                "doc-v1".into(),
                field,
                format!("value-{index}"),
                RequisitesSourceKind::DocumentHead,
                SourceAnchor::try_new(
                    TextSpan::try_new(index, index + 1).unwrap(),
                    format!("anchor-{index}"),
                )
                .unwrap(),
                "profile-v1".into(),
                RequisitesExtractionStatus::Observed,
            )
            .unwrap()
        })
        .collect();
    let sidecar = CurrentDocumentRequisites::try_new("doc-v1".into(), claims).unwrap();
    let environment = ContextEnvironment {
        index: &index,
        overlay: &overlay,
        requisites: Some(&sidecar),
    };

    // A request whose only "evidence" is the opaque legacy label carries no
    // typed evidence and therefore stays a refusal.
    let labelled = ContextRequest::new(
        ContextRequestKind::CurrentDocumentRequisites,
        "doc-v1".into(),
        FrameRef::parse("block-3").unwrap(),
        Vec::new(),
        None,
        None,
        Vec::new(),
        1,
        "authorized-fields".into(),
    );
    assert!(labelled.this_ref_evidence().is_none());
    assert_eq!(labelled.memo_key().authorization_evidence, None);
    let mut worklist = ContextWorklist::new(ContextBudgets::default());
    let report = worklist.run(environment, &[labelled]);
    assert_eq!(
        report.results.values().next().unwrap().status,
        ContextStatus::Partial,
        "an evidence label is not an authorization proof"
    );

    // Persisted typed evidence resolves through the same dispatch path, and
    // the two requests keep distinct memo identities on one worklist.
    let admitted = ContextRequest::current_document_requisites(
        FrameRef::parse("block-3").unwrap(),
        ThisRefGrammarEvidence::new([RequisitesField::Type]),
    );
    assert_eq!(
        admitted.memo_key().authorization_evidence.as_deref(),
        Some("type")
    );
    let report = worklist.run(environment, &[admitted]);
    assert_eq!(
        report.results.values().next().unwrap().status,
        ContextStatus::Resolved
    );
}
