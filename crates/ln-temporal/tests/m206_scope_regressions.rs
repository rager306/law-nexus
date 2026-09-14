//! M206/S06 red reproduction oracle for RC28-F11..F12.
//! The assertions encode the admitted fail-closed semantic-scope boundary.

use ln_temporal::document_context::{
    detect_this_ref, AnalysisOverlay, BlockId, Container, ContainerRole, DocumentStructureIndex,
    DocumentVersion, Frame, FrameId, SourceBlock, Terminal, TextSpan,
};
use ln_temporal::semantic_scope::{extract_semantic_claims, project_norm_rule, SemanticClaimKind};
use std::collections::BTreeMap;

fn fixture(text: &str) -> (SourceBlock, AnalysisOverlay) {
    let block = SourceBlock::new(BlockId::new(0), 0, text);
    let frames = vec![Frame::new(FrameId::new(0), BlockId::new(0), true, false)];
    let overlay = AnalysisOverlay::new(frames, BTreeMap::new(), BTreeMap::new()).unwrap();
    (block, overlay)
}

fn index() -> DocumentStructureIndex {
    DocumentStructureIndex::build(
        DocumentVersion::new("doc-v1").unwrap(),
        vec![SourceBlock::new(BlockId::new(0), 0, "body")],
        vec![Container::new(0, ContainerRole::Document, None)],
        BTreeMap::from([(BlockId::new(0), 0)]),
    )
    .unwrap()
}

#[test]
fn rc28_f11_temporal_do_does_not_match_dolzhen() {
    let (block, overlay) = fixture("Орган должен действовать до срока.");
    let outcome = extract_semantic_claims(&block, &overlay, &[], 32);
    let temporal = outcome
        .claims()
        .iter()
        .filter(|claim| claim.kind() == SemanticClaimKind::TemporalQualifier)
        .collect::<Vec<_>>();
    assert_eq!(
        temporal.len(),
        1,
        "RC28-F11 case identifier: only standalone до is temporal"
    );
    let span = temporal[0].span();
    assert_eq!(
        &block.text()[span.start()..span.end()],
        "до",
        "RC28-F11 cue matching must be token-bound"
    );
}

#[test]
fn rc28_f11_actor_is_source_backed_and_not_the_whole_block() {
    let (block, overlay) = fixture("Орган должен представить отчет.");
    let outcome = extract_semantic_claims(&block, &overlay, &[], 32);
    let actors = outcome
        .claims()
        .iter()
        .filter(|claim| claim.kind() == SemanticClaimKind::Actor)
        .collect::<Vec<_>>();
    assert_eq!(
        actors.len(),
        1,
        "RC28-F11 case identifier: one actor candidate is expected"
    );
    let span = actors[0].span();
    assert!(
        span.end() - span.start() < block.text().len(),
        "RC28-F11 Actor must not cover the whole block"
    );
    assert_eq!(
        &block.text()[span.start()..span.end()],
        "Орган",
        "RC28-F11 actor origin must remain local"
    );
}

#[test]
fn rc28_f11_independent_sentences_keep_independent_cues() {
    let (block, overlay) = fixture("Орган должен действовать. Клиент вправе отказаться.");
    let outcome = extract_semantic_claims(&block, &overlay, &[], 32);
    let polarities = outcome
        .claims()
        .iter()
        .filter(|claim| claim.kind() == SemanticClaimKind::Polarity)
        .collect::<Vec<_>>();
    assert_eq!(
        polarities.len(),
        2,
        "RC28-F11 case identifier: independent sentences retain two polarity origins"
    );
    assert!(polarities
        .iter()
        .all(|claim| claim.span().start() < claim.span().end()));
}

#[test]
fn rc28_f12_self_antecedent_alias_and_edition_are_not_one_construction() {
    let index = index();
    let (block, overlay) =
        fixture("настоящего Закона и того же раздела (далее — Закон) в ред. 01.01.2020 N 1-ФЗ");
    let this_refs = detect_this_ref(block.text());
    let outcome = extract_semantic_claims(&block, &overlay, &this_refs, 64);
    let actors = outcome
        .claims()
        .iter()
        .filter(|claim| claim.kind() == SemanticClaimKind::Actor)
        .collect::<Vec<_>>();
    assert!(
        actors.iter().all(|claim| claim.span().end() - claim.span().start() < block.text().len()),
        "RC28-F12 case identifier: distinct reference constructions must not collapse into a whole-block Actor"
    );
    let result = project_norm_rule(outcome.claims().to_vec(), Terminal::Resolved);
    assert!(
        matches!(result, ln_temporal::semantic_scope::ProjectionOutcome::Abstained(_)),
        "RC28-F12 case identifier: references without complete semantic slots must not become a rule"
    );
    let _ = index;
}

#[test]
fn rc28_f12_utf8_origins_are_char_boundary_safe() {
    let text = "Настоящий Закон — должен действовать.";
    let (block, overlay) = fixture(text);
    let outcome = extract_semantic_claims(&block, &overlay, &[], 32);
    for claim in outcome.claims() {
        let span = claim.span();
        assert!(
            text.is_char_boundary(span.start()) && text.is_char_boundary(span.end()),
            "RC28-F12 case identifier: UTF-8 source origin must be char-boundary safe"
        );
    }
    let _ = TextSpan::new(0, text.len()).unwrap();
}
