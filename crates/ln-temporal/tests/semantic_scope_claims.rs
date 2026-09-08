use ln_temporal::document_context::{AnalysisOverlay, BlockId, Frame, SourceBlock, TextSpan};
use ln_temporal::semantic_scope::{
    extract_semantic_claims, ClaimError, SemanticClaim, SemanticClaimKind,
};
use std::collections::BTreeMap;

fn overlay_for(block: BlockId) -> AnalysisOverlay {
    AnalysisOverlay::new(
        vec![Frame::new(
            ln_temporal::document_context::FrameId::new(0),
            block,
            true,
            false,
        )],
        BTreeMap::new(),
        BTreeMap::new(),
    )
    .unwrap()
}

#[test]
fn vocabulary_is_closed_and_claims_require_source_anchors() {
    let all = [
        SemanticClaimKind::Actor,
        SemanticClaimKind::Action,
        SemanticClaimKind::Object,
        SemanticClaimKind::Polarity,
        SemanticClaimKind::Condition,
        SemanticClaimKind::Exception,
        SemanticClaimKind::TemporalQualifier,
    ];
    assert_eq!(all.len(), 7);

    let span = TextSpan::new(0, 3).unwrap();
    assert_eq!(
        SemanticClaim::new(SemanticClaimKind::Action, BlockId::new(1), span, vec![]),
        Err(ClaimError::MissingEvidence)
    );
    assert_eq!(
        SemanticClaim::new(
            SemanticClaimKind::Action,
            BlockId::new(1),
            TextSpan::new(2, 2).unwrap(),
            vec![span]
        ),
        Err(ClaimError::EmptySpan)
    );
    let claim =
        SemanticClaim::new(SemanticClaimKind::Action, BlockId::new(1), span, vec![span]).unwrap();
    assert_eq!(claim.evidence(), &[span]);
}

#[test]
fn extractor_keeps_negative_polarity_and_source_anchors() {
    let block = SourceBlock::new(
        BlockId::new(4),
        0,
        "Организация не вправе действовать, если срок истёк, кроме случая после публикации.",
    );
    let refs = ln_temporal::document_context::detect_this_ref(block.text());
    let result = extract_semantic_claims(&block, &overlay_for(block.id()), &refs, 32);

    assert!(!result.was_limited());
    assert!(result
        .claims()
        .iter()
        .any(|claim| claim.kind() == SemanticClaimKind::Polarity
            && &block.text()[claim.span().start()..claim.span().end()] == "не вправе"));
    assert!(result
        .claims()
        .iter()
        .any(|claim| claim.kind() == SemanticClaimKind::Condition));
    assert!(result
        .claims()
        .iter()
        .any(|claim| claim.kind() == SemanticClaimKind::Exception));
    assert!(result
        .claims()
        .iter()
        .any(|claim| claim.kind() == SemanticClaimKind::TemporalQualifier));
    assert!(result
        .claims()
        .iter()
        .all(|claim| !claim.evidence().is_empty()
            && claim.block() == block.id()
            && claim.span().end() <= block.text().len()));
}

#[test]
fn limit_is_typed_and_preserves_admitted_claims() {
    let block = SourceBlock::new(
        BlockId::new(7),
        0,
        "Организация должна действовать если срок до даты, кроме исключения после события.",
    );
    let result = extract_semantic_claims(&block, &overlay_for(block.id()), &[], 2);

    assert_eq!(result.claims().len(), 2);
    assert!(result.was_limited());
    let limit = result.limit().unwrap();
    assert_eq!(limit.limit, 2);
    assert!(limit.attempted > limit.limit);
    assert!(result
        .claims()
        .iter()
        .all(|claim| !claim.evidence().is_empty()));
}

#[test]
fn extraction_is_deterministic() {
    let block = SourceBlock::new(
        BlockId::new(9),
        0,
        "The actor must not act after publication if permitted.",
    );
    let overlay = overlay_for(block.id());
    let first = extract_semantic_claims(&block, &overlay, &[], 20);
    let second = extract_semantic_claims(&block, &overlay, &[], 20);
    assert_eq!(first, second);
    assert!(first
        .claims()
        .windows(2)
        .all(|claims| claims[0] <= claims[1]));
}
