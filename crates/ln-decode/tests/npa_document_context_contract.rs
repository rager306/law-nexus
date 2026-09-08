use ln_decode::document_context::{
    build_document_structure_index, BlockId, ContainerRole, ContextPhase, ContextRequestKind,
    ContextStatus, ContextTransition, DocumentVersionRef, IndexBuildError, MAX_LINKING_PASSES,
    PROPOSED_MAX_ADJACENT_RADIUS,
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
    assert_eq!(adjacent.len(), 2);
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
