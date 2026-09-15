//! M206/S06 red reproduction oracle for RC28-F11..F12.
//! The assertions encode the admitted fail-closed semantic-scope boundary.
//!
//! S04 scenario map owned by this file for RC28-F11 (T05):
//! `F10-CUE-TOKEN`, `F10-CUE-POSITIVE`, `F10-ACTOR-ANCHORED`, `F10-ACTOR-NEGATIVE`.
//! The S04 rows are named after their F-number label, not after the RC28 finding
//! they belong to; these four are the RC28-F11 cue and participant scenarios.
//! `F11-ENDPOINTS`/`F11-MEMBERSHIP`/`F11-MISSING-MEMBER`/`F11-RANGE-INVALID`
//! stay with RC28-F10 in ln-decode and are not owned here.

use ln_temporal::document_context::{
    detect_this_ref, AnalysisOverlay, BlockId, Container, ContainerRole, DocumentStructureIndex,
    DocumentVersion, Frame, FrameId, SourceBlock, Terminal, TextSpan,
};
use ln_temporal::semantic_scope::{
    extract_semantic_claims, project_norm_rule, AbstentionReason, ProjectionOutcome, SemanticClaim,
    SemanticClaimKind,
};
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

/// Run the extractor over `text`, optionally with a structural act frame.
fn extract(text: &str, framed: bool) -> (SourceBlock, Vec<SemanticClaim>) {
    let block = SourceBlock::new(BlockId::new(0), 0, text);
    let frames = if framed {
        vec![Frame::new(FrameId::new(0), block.id(), true, false)]
    } else {
        Vec::new()
    };
    let overlay = AnalysisOverlay::new(frames, BTreeMap::new(), BTreeMap::new()).unwrap();
    let outcome = extract_semantic_claims(&block, &overlay, &[], 64);
    (block, outcome.claims().to_vec())
}

/// Exact original substrings of every claim of one kind. Slicing is itself the
/// char-boundary assertion: a non-boundary offset would panic here.
fn spans_of<'a>(
    block: &'a SourceBlock,
    claims: &[SemanticClaim],
    kind: SemanticClaimKind,
) -> Vec<&'a str> {
    claims
        .iter()
        .filter(|claim| claim.kind() == kind)
        .map(|claim| &block.text()[claim.span().start()..claim.span().end()])
        .collect()
}

#[test]
fn rc28_f11_s04_f10_cue_token_scoped_negation_stays_separate() {
    // S04 `F10-CUE-TOKEN` on RC28-F11: the negation particle belongs to the
    // polarity it scopes. A bare positive cue must never leak out of a negated
    // form, and the scope must be visible in the preserved source span.
    for (text, expected) in [
        ("Орган не обязан действовать.", "не обязан"),
        ("Орган не вправе отказать.", "не вправе"),
        ("Орган не должен бездействовать.", "не должен"),
        ("Орган обязан не разглашать.", "обязан не"),
        ("Орган вправе отказать.", "вправе"),
        ("Не вправе отказывать.", "Не вправе"),
        ("Орган обязан действовать.", "обязан"),
    ] {
        let (block, claims) = extract(text, true);
        assert_eq!(
            spans_of(&block, &claims, SemanticClaimKind::Polarity),
            vec![expected],
            "RC28-F11 S04 F10-CUE-TOKEN: scoped negation must not leak a bare cue ({text})"
        );
    }
}

#[test]
fn rc28_f11_s04_f10_cue_token_rejects_substring_tokens() {
    let (block, claims) = extract("Задолженность Органа до срока.", true);
    assert!(
        spans_of(&block, &claims, SemanticClaimKind::Polarity).is_empty(),
        "RC28-F11 S04 F10-CUE-TOKEN: обязан/должен inside a larger token is not a cue"
    );
    assert_eq!(
        spans_of(&block, &claims, SemanticClaimKind::TemporalQualifier),
        vec!["до"],
        "RC28-F11 S04 F10-CUE-TOKEN: the standalone temporals survive substring rejection"
    );

    let (block, claims) = extract("The actor mustered courage after all.", true);
    assert!(
        spans_of(&block, &claims, SemanticClaimKind::Polarity).is_empty(),
        "RC28-F11 S04 F10-CUE-TOKEN: must inside mustered is not a cue"
    );
    assert_eq!(
        spans_of(&block, &claims, SemanticClaimKind::TemporalQualifier),
        vec!["after"],
        "RC28-F11 S04 F10-CUE-TOKEN: after stays a standalone temporal cue"
    );
}

#[test]
fn rc28_f11_s04_f10_cue_positive_stays_a_candidate() {
    // S04 `F10-CUE-POSITIVE` on RC28-F11: a captured cue is candidate evidence.
    let (block, claims) = extract("Орган должен представить отчёт.", true);
    assert_eq!(
        spans_of(&block, &claims, SemanticClaimKind::Polarity),
        vec!["должен"],
        "RC28-F11 S04 F10-CUE-POSITIVE: the standalone cue is captured as a candidate"
    );
    assert!(
        claims
            .iter()
            .all(|claim| !claim.evidence().is_empty() && claim.block() == block.id()),
        "RC28-F11 S04 F10-CUE-POSITIVE: every candidate keeps its source anchor"
    );

    // No-IR negative assertion: cue extraction alone cannot reach a norm rule.
    // The closed cue vocabulary mints no Action and no Object, so the four-slot
    // candidate can never complete from this surface, and the single scoped
    // polarity is not a slot conflict.
    match project_norm_rule(claims.clone(), Terminal::Resolved) {
        ProjectionOutcome::Abstained(record) => {
            assert!(
                record.reasons().contains(&AbstentionReason::MissingAction)
                    && record.reasons().contains(&AbstentionReason::MissingObject),
                "RC28-F11 S04 F10-CUE-POSITIVE: cue-only scope must abstain on the missing slots"
            );
            assert!(
                !record
                    .reasons()
                    .contains(&AbstentionReason::ConflictingSlots),
                "RC28-F11 S04 F10-CUE-POSITIVE: one scoped polarity must not read as a conflict"
            );
        }
        ProjectionOutcome::Complete(_) => panic!(
            "RC28-F11 S04 F10-CUE-POSITIVE: cue extraction must not mint Applicable/NormRule IR"
        ),
    }
}

#[test]
fn rc28_f11_s04_f10_actor_anchored_span_is_exact() {
    // S04 `F10-ACTOR-ANCHORED` on RC28-F11: Actor is the proven participant span.
    let (block, claims) = extract(
        "Орган должен представить отчёт. Прокурор вправе обратиться в суд.",
        true,
    );
    let mut actors = spans_of(&block, &claims, SemanticClaimKind::Actor);
    actors.sort_unstable();
    assert_eq!(
        actors,
        vec!["Орган", "Прокурор"],
        "RC28-F11 S04 F10-ACTOR-ANCHORED: the actor span is the participant, never the block"
    );
}

#[test]
fn rc28_f11_s04_f10_actor_negative_is_typed_absence() {
    // S04 `F10-ACTOR-NEGATIVE` on RC28-F11: no Actor may be guessed from block
    // scope, from cue presence, or from an ambiguous prefix.
    for text in [
        // No polarity cue at all: there is no predicate to ground a participant.
        "Настоящий документ вступает в силу с момента опубликования.",
        // The cue opens the statement, so no proven participant span exists.
        "Должен действовать незамедлительно.",
        // A clause separator inside the prefix means the prefix is not one
        // grammatical participant; morphology is unavailable, so abstain.
        "Согласно статье 5, орган должен действовать.",
        // Another cue owns the prefix, so the prefix is not participant material.
        "Если орган должен действовать, срок истёк.",
    ] {
        let (block, claims) = extract(text, true);
        assert!(
            spans_of(&block, &claims, SemanticClaimKind::Actor).is_empty(),
            "RC28-F11 S04 F10-ACTOR-NEGATIVE: no actor may be guessed for {text}"
        );
    }

    // A proven participant span without structural act scope stays unminted: the
    // frame is a necessary precondition, never sufficient on its own.
    let (block, claims) = extract("Орган должен представить отчёт.", false);
    assert!(
        spans_of(&block, &claims, SemanticClaimKind::Actor).is_empty(),
        "RC28-F11 S04 F10-ACTOR-NEGATIVE: block participation alone is not actor proof"
    );
}

#[test]
fn rc28_f11_cue_scope_does_not_cross_a_statement_boundary() {
    let (block, claims) = extract("Орган не действует. Вправе отказать.", true);
    assert_eq!(
        spans_of(&block, &claims, SemanticClaimKind::Polarity),
        vec!["Вправе"],
        "RC28-F11: a negation from the previous statement must not attach"
    );

    let (block, claims) = extract("Орган действует. Не вправе отказать.", true);
    assert_eq!(
        spans_of(&block, &claims, SemanticClaimKind::Polarity),
        vec!["Не вправе"],
        "RC28-F11: a statement-initial negation still scopes its own cue"
    );

    let (block, claims) = extract("the actor must. not act.", true);
    assert_eq!(
        spans_of(&block, &claims, SemanticClaimKind::Polarity),
        vec!["must"],
        "RC28-F11: a multiword cue must not span two statements"
    );
}

#[test]
fn rc28_f11_cue_phrases_require_unpunctuated_adjacency() {
    let (block, claims) = extract("The actor must,not act after all.", true);
    assert_eq!(
        spans_of(&block, &claims, SemanticClaimKind::Polarity),
        vec!["must"],
        "RC28-F11: punctuation inside a cue phrase or before a particle breaks the scope"
    );

    // A multiword cue keeps the original whitespace of its source span.
    let (block, claims) = extract("Орган действует в  течение года.", true);
    assert_eq!(
        spans_of(&block, &claims, SemanticClaimKind::TemporalQualifier),
        vec!["в  течение"],
        "RC28-F11: a cue span preserves the original UTF-8 text exactly"
    );
}

#[test]
fn rc28_f11_blocks_without_tokens_mint_nothing() {
    for text in ["", "   \n\t ", "...", "—"] {
        let (block, claims) = extract(text, true);
        assert!(
            claims.is_empty(),
            "RC28-F11: a block without tokens cannot offer evidence ({text:?})"
        );
        assert_eq!(block.text(), text);
    }
}

#[test]
fn rc28_f11_scale_stays_bounded_and_truncation_is_typed() {
    // Q6 evidence: the candidate count is exactly one Actor plus one cue per
    // statement, so the scan has no cross-statement product and no accidental
    // quadratic term. Truncation stays typed through the existing budget.
    let repetitions = 2_000usize;
    let text = "Орган должен действовать. Клиент не вправе отказать. ".repeat(repetitions);
    let block = SourceBlock::new(BlockId::new(0), 0, text);
    let overlay = AnalysisOverlay::new(
        vec![Frame::new(FrameId::new(0), block.id(), true, false)],
        BTreeMap::new(),
        BTreeMap::new(),
    )
    .unwrap();
    let outcome = extract_semantic_claims(&block, &overlay, &[], 64);
    assert_eq!(
        outcome.claims().len(),
        64,
        "RC28-F11: the per-block claim budget truncates the admitted candidates"
    );
    let limit = outcome.limit().expect("RC28-F11: truncation is typed");
    assert_eq!(limit.limit, 64);
    assert_eq!(
        limit.attempted,
        repetitions * 4,
        "RC28-F11: exactly one Actor and one cue per statement, no cross-products"
    );
    assert!(outcome
        .claims()
        .iter()
        .all(|claim| claim.span().end() <= block.text().len()));
}
