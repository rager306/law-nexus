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
    detect_edition_relations, detect_this_ref, resolve_construction, AnalysisOverlay, BlockId,
    ConstructionAbstention, ConstructionOutcome, ConstructionRequest, Container, ContainerRole,
    ContextError, DocumentStructureIndex, DocumentVersion, Frame, FrameId, ReferenceConstruction,
    ScopedAliasDeclaration, SourceAnchor, SourceBlock, Terminal, TextSpan,
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

// ---------------------------------------------------------------------------
// RC28-F12 construction separation (T06).
//
// S03 scenario map owned by this file:
// `F12-antecedent-positive`, `F12-antecedent-unproven`,
// `F12-alias-declare-use`, `F12-alias-shadow-conflict`, `F12-alias-boundary`,
// `F12-edition-relation`.
// S04 scenario map owned by this file for RC28-F12:
// `F12-CONTEXT-SEPARATION`, `F12-NO-IR`.
// `F12-VERTICAL-POSITIVE`/`F12-VERTICAL-NEGATIVE` are the composed vertical and
// live in `crates/ln-testkit/tests/decode_port_contracts.rs`.
// ---------------------------------------------------------------------------

/// Three blocks in document order: block 0 is the earlier cited act, block 1
/// cites it, block 2 is an unrelated later section.
fn construction_fixture() -> (DocumentStructureIndex, AnalysisOverlay) {
    let blocks = vec![
        SourceBlock::new(BlockId::new(0), 0, "Федеральный закон от 01.01.2020 N 1-ФЗ"),
        SourceBlock::new(BlockId::new(1), 1, "Статья 5 применяется в отношении него"),
        SourceBlock::new(BlockId::new(2), 2, "Иной раздел документа"),
    ];
    let index = DocumentStructureIndex::build(
        DocumentVersion::new("doc-v1").unwrap(),
        blocks,
        vec![
            Container::new(0, ContainerRole::Document, None),
            Container::new(1, ContainerRole::Article, Some(0)),
            Container::new(2, ContainerRole::Article, Some(0)),
        ],
        BTreeMap::from([
            (BlockId::new(0), 1),
            (BlockId::new(1), 1),
            (BlockId::new(2), 2),
        ]),
    )
    .unwrap();
    let frames = vec![
        Frame::new(FrameId::new(0), BlockId::new(0), false, false),
        Frame::new(FrameId::new(1), BlockId::new(1), false, false),
        Frame::new(FrameId::new(2), BlockId::new(2), false, false),
    ];
    let overlay = AnalysisOverlay::new(frames, BTreeMap::new(), BTreeMap::new()).unwrap();
    (index, overlay)
}

/// The source-local anchor of `needle` inside `haystack`.
fn anchor_of(haystack: &str, needle: &str) -> TextSpan {
    let start = haystack
        .find(needle)
        .unwrap_or_else(|| panic!("fixture needle {needle:?} not found"));
    TextSpan::new(start, start + needle.len()).unwrap()
}

/// A block-bound source anchor: byte offsets are fragment-local, so the block
/// identity travels with the span.
fn source_anchor(block: usize, haystack: &str, needle: &str) -> SourceAnchor {
    SourceAnchor::new(BlockId::new(block), anchor_of(haystack, needle))
        .expect("fixture source anchor")
}

#[test]
fn rc28_f12_antecedent_positive_and_unproven_cited_act_stay_separate() {
    let (index, overlay) = construction_fixture();
    let earlier_text = index.blocks()[0].text();
    let anchor = source_anchor(0, earlier_text, "закон");
    let origin = FrameId::new(1);

    // F12-antecedent-positive: the earlier cited act is proven by source-block
    // document order plus its own source-local anchor.
    let positive = ConstructionRequest::new(ReferenceConstruction::EarlierCitedAct, origin, 1)
        .explicit_target(FrameId::new(0))
        .anchor(anchor);
    match resolve_construction(&positive, &index, &overlay, false) {
        ConstructionOutcome::Resolved {
            construction,
            target,
            evidence,
        } => {
            assert_eq!(
                construction,
                ReferenceConstruction::EarlierCitedAct,
                "F12-antecedent-positive: the construction is preserved on the outcome"
            );
            assert_eq!(target, FrameId::new(0));
            assert_eq!(evidence, vec![anchor.span()]);
            assert_eq!(evidence[0], anchor_of(earlier_text, "закон"));
        }
        other => {
            panic!("F12-antecedent-positive: expected a proven earlier cited act, got {other:?}")
        }
    }

    // F12-antecedent-unproven: every unproven path is typed and none of them
    // resolves.
    let cases: Vec<(ConstructionRequest, ConstructionAbstention, &str)> = vec![
        (
            ConstructionRequest::new(ReferenceConstruction::EarlierCitedAct, origin, 1),
            ConstructionAbstention::MissingAntecedent,
            "no antecedent was offered at all",
        ),
        (
            ConstructionRequest::new(ReferenceConstruction::EarlierCitedAct, origin, 1)
                .explicit_target(FrameId::new(9))
                .anchor(anchor),
            ConstructionAbstention::MissingAntecedent,
            "the offered antecedent frame is unknown",
        ),
        (
            ConstructionRequest::new(ReferenceConstruction::EarlierCitedAct, origin, 1)
                .explicit_target(FrameId::new(2))
                .anchor(source_anchor(2, index.blocks()[2].text(), "раздел")),
            ConstructionAbstention::AntecedentNotEarlier,
            "a later act is not an antecedent",
        ),
        (
            ConstructionRequest::new(ReferenceConstruction::EarlierCitedAct, origin, 1)
                .explicit_target(FrameId::new(0)),
            ConstructionAbstention::AnchorOutOfBlock,
            "an antecedent without its own source anchor is unproven",
        ),
        (
            ConstructionRequest::new(ReferenceConstruction::EarlierCitedAct, origin, 1)
                .explicit_target(FrameId::new(0))
                .anchor(source_anchor(1, index.blocks()[1].text(), "Статья")),
            ConstructionAbstention::AnchorOutOfBlock,
            "an anchor minted in another block must not prove the antecedent",
        ),
    ];
    for (request, expected, label) in cases {
        match resolve_construction(&request, &index, &overlay, false) {
            ConstructionOutcome::Unproven {
                reason,
                construction,
            } => {
                assert_eq!(construction, ReferenceConstruction::EarlierCitedAct);
                assert_eq!(
                    reason, expected,
                    "F12-antecedent-unproven: {label} must abstain with the typed reason"
                );
            }
            other => panic!("F12-antecedent-unproven: {label} must stay unproven, got {other:?}"),
        }
    }
}

fn alias(wording: &str, scope: usize, frame: usize, anchor: TextSpan) -> ScopedAliasDeclaration {
    ScopedAliasDeclaration::new(wording, scope, FrameId::new(frame), anchor)
        .expect("fixture alias declaration")
}

#[test]
fn rc28_f12_alias_declare_use_shadow_conflict_and_boundary() {
    let (index, overlay) = construction_fixture();
    let origin = FrameId::new(1);
    let declaration_anchor = anchor_of(index.blocks()[2].text(), "Иной");
    let declared = overlay
        .clone()
        .with_scoped_aliases(vec![alias("Закон", 1, 0, declaration_anchor)])
        .expect("alias declaration points at a known frame");

    // F12-alias-declare-use: a declare/use pair in the same structural scope.
    let use_request =
        ConstructionRequest::new(ReferenceConstruction::DeclaredScopedAlias, origin, 1)
            .key("Закон");
    match resolve_construction(&use_request, &index, &declared, false) {
        ConstructionOutcome::Resolved {
            construction,
            target,
            evidence,
        } => {
            assert_eq!(construction, ReferenceConstruction::DeclaredScopedAlias);
            assert_eq!(target, FrameId::new(0));
            assert_eq!(evidence, vec![declaration_anchor]);
        }
        other => panic!("F12-alias-declare-use: expected a resolved alias, got {other:?}"),
    }

    // F12-alias-boundary: the same wording used outside the declaring scope is
    // an out-of-scope crossing, never a resolved reference.
    let outside = ConstructionRequest::new(ReferenceConstruction::DeclaredScopedAlias, origin, 2)
        .key("Закон");
    match resolve_construction(&outside, &index, &declared, false) {
        ConstructionOutcome::OutOfScope {
            construction,
            wording,
        } => {
            assert_eq!(construction, ReferenceConstruction::DeclaredScopedAlias);
            assert_eq!(wording, "Закон");
        }
        other => panic!("F12-alias-boundary: expected an out-of-scope crossing, got {other:?}"),
    }
    assert_eq!(
        ConstructionOutcome::OutOfScope {
            construction: ReferenceConstruction::DeclaredScopedAlias,
            wording: "Закон".to_owned(),
        }
        .terminal(),
        Terminal::Unavailable,
        "F12-alias-boundary: a boundary crossing maps to Unavailable"
    );

    // F12-alias-shadow-conflict: two declarations of one wording inside the
    // same scope retain both candidate frames instead of picking one.
    let shadowed = overlay
        .clone()
        .with_scoped_aliases(vec![
            alias("Закон", 1, 0, declaration_anchor),
            alias("Закон", 1, 2, anchor_of(index.blocks()[2].text(), "раздел")),
        ])
        .expect("both declarations point at known frames");
    match resolve_construction(&use_request, &index, &shadowed, false) {
        ConstructionOutcome::Conflicting {
            construction,
            retained,
            evidence,
        } => {
            assert_eq!(construction, ReferenceConstruction::DeclaredScopedAlias);
            assert_eq!(retained, vec![FrameId::new(0), FrameId::new(2)]);
            assert_eq!(
                evidence.len(),
                2,
                "F12-alias-shadow-conflict: both anchors stay"
            );
        }
        other => {
            panic!("F12-alias-shadow-conflict: a shadowed declaration must conflict, got {other:?}")
        }
    }

    // The undeclared and wording-less paths are typed abstentions.
    let undeclared =
        ConstructionRequest::new(ReferenceConstruction::DeclaredScopedAlias, origin, 1)
            .key("Кодекс");
    assert!(matches!(
        resolve_construction(&undeclared, &index, &declared, false),
        ConstructionOutcome::Unproven {
            reason: ConstructionAbstention::UndeclaredAlias,
            ..
        }
    ));
    let wording_less =
        ConstructionRequest::new(ReferenceConstruction::DeclaredScopedAlias, origin, 1);
    assert!(matches!(
        resolve_construction(&wording_less, &index, &declared, false),
        ConstructionOutcome::Unproven {
            reason: ConstructionAbstention::MissingAliasWording,
            ..
        }
    ));

    // Declaration-time guards: an empty wording and a dangling frame are
    // refused before any request can see them.
    assert_eq!(
        ScopedAliasDeclaration::new("   ", 1, FrameId::new(0), declaration_anchor),
        Err(ContextError::EmptyAliasWording)
    );
    assert_eq!(
        ScopedAliasDeclaration::new("Закон", 1, FrameId::new(0), TextSpan::new(3, 3).unwrap()),
        Err(ContextError::InvalidSpan)
    );
    assert_eq!(
        SourceAnchor::new(BlockId::new(0), TextSpan::new(3, 3).unwrap()),
        Err(ContextError::InvalidSpan),
        "F12-alias-boundary: an empty source anchor is refused"
    );
    assert_eq!(
        overlay
            .clone()
            .with_scoped_aliases(vec![alias("Закон", 1, 9, declaration_anchor)]),
        Err(ContextError::UnknownFrame)
    );
}

#[test]
fn rc28_f12_construction_separation_keeps_authorizations_apart() {
    // S04 `F12-CONTEXT-SEPARATION`: self, antecedent, alias and coordinating
    // head keep independent authorizations. Recognizing one never authorizes
    // another, and no shared label merges them.
    let (index, overlay) = construction_fixture();
    let origin = FrameId::new(1);
    let declared = overlay
        .clone()
        .with_scoped_aliases(vec![alias(
            "Закон",
            1,
            0,
            anchor_of(index.blocks()[2].text(), "Иной"),
        )])
        .expect("alias declaration points at a known frame");

    // (a) a declared alias does not authorize self-reference: the `ThisRef`
    // evidence is a separate authorization input and stays empty here.
    let self_request =
        ConstructionRequest::new(ReferenceConstruction::CurrentDocumentSelf, origin, 1);
    assert!(matches!(
        resolve_construction(&self_request, &index, &declared, true),
        ConstructionOutcome::Unproven {
            reason: ConstructionAbstention::MissingSelfEvidence,
            ..
        }
    ));
    // ... and no requisites sidecar remains its own distinct refusal.
    assert!(matches!(
        resolve_construction(&self_request, &index, &declared, false),
        ConstructionOutcome::Unproven {
            reason: ConstructionAbstention::MissingRequisites,
            ..
        }
    ));

    // (b) resolving the alias does not create a coordinating head.
    assert!(matches!(
        resolve_construction(
            &ConstructionRequest::new(ReferenceConstruction::DeclaredScopedAlias, origin, 1)
                .key("Закон"),
            &index,
            &declared,
            true
        ),
        ConstructionOutcome::Resolved { .. }
    ));
    assert!(matches!(
        resolve_construction(
            &ConstructionRequest::new(ReferenceConstruction::CoordinatingHead, origin, 1),
            &index,
            &declared,
            true
        ),
        ConstructionOutcome::Unproven {
            reason: ConstructionAbstention::MissingAntecedent,
            ..
        }
    ));

    // (c) a coordinating head resolution does not authorize the alias outside
    // its declaring scope, and does not authorize an antecedent.
    let headed = declared
        .clone()
        .with_scoped_aliases(vec![alias(
            "Закон",
            1,
            0,
            anchor_of(index.blocks()[2].text(), "Иной"),
        )])
        .expect("alias declaration points at a known frame");
    let mut heads = BTreeMap::new();
    heads.insert(origin, vec![FrameId::new(0)]);
    let headed = AnalysisOverlay::new(headed.frames().to_vec(), BTreeMap::new(), heads)
        .expect("head map references known frames")
        .with_scoped_aliases(vec![alias(
            "Закон",
            1,
            0,
            anchor_of(index.blocks()[2].text(), "Иной"),
        )])
        .expect("alias declaration points at a known frame");
    assert!(matches!(
        resolve_construction(
            &ConstructionRequest::new(ReferenceConstruction::CoordinatingHead, origin, 1),
            &index,
            &headed,
            true
        ),
        ConstructionOutcome::Resolved {
            target,
            ..
        } if target == FrameId::new(0)
    ));
    assert!(matches!(
        resolve_construction(
            &ConstructionRequest::new(ReferenceConstruction::DeclaredScopedAlias, origin, 2)
                .key("Закон"),
            &index,
            &headed,
            true
        ),
        ConstructionOutcome::OutOfScope { .. }
    ));
    assert!(matches!(
        resolve_construction(
            &ConstructionRequest::new(ReferenceConstruction::EarlierCitedAct, origin, 1),
            &index,
            &headed,
            true
        ),
        ConstructionOutcome::Unproven {
            reason: ConstructionAbstention::MissingAntecedent,
            ..
        }
    ));

    // (d) the four constructions are distinct labels and each outcome reports
    // the construction it was asked about, so no shared label can merge them.
    let labels = [
        ReferenceConstruction::CurrentDocumentSelf,
        ReferenceConstruction::EarlierCitedAct,
        ReferenceConstruction::DeclaredScopedAlias,
        ReferenceConstruction::CoordinatingHead,
    ];
    let mut seen = std::collections::BTreeSet::new();
    for label in labels {
        assert!(
            seen.insert(label),
            "F12-CONTEXT-SEPARATION: labels are distinct"
        );
        let outcome = resolve_construction(
            &ConstructionRequest::new(label, origin, 1),
            &index,
            &headed,
            false,
        );
        assert_eq!(
            outcome.construction(),
            label,
            "F12-CONTEXT-SEPARATION: the outcome reports its own construction"
        );
    }
}

#[test]
fn rc28_f12_edition_relation_is_a_source_backed_candidate_not_identity() {
    // S03 `F12-edition-relation` + S04 `F12-NO-IR`: `в ред.` is preserved as a
    // source-backed relation candidate and never becomes Expression identity,
    // `edition_date`, CTV, force, or any legal IR.
    let text = "Статья 5 в ред. 01.01.2020 N 1-ФЗ и в редакции 02.02.2021";
    let candidates = detect_edition_relations(text);
    assert_eq!(
        candidates.len(),
        2,
        "F12-edition-relation: both written forms are preserved"
    );
    assert_eq!(candidates[0].surface(), "в ред.");
    assert_eq!(candidates[1].surface(), "в редакции");
    for candidate in &candidates {
        let span = candidate.anchor();
        assert!(
            text.is_char_boundary(span.start()) && text.is_char_boundary(span.end()),
            "F12-edition-relation: the anchor stays on UTF-8 character boundaries"
        );
        assert_eq!(
            &text[span.start()..span.end()],
            candidate.surface(),
            "F12-edition-relation: the anchor names the original source surface"
        );
        assert!(
            span.end() <= text.len(),
            "F12-edition-relation: the anchor is source-local"
        );
    }

    // Token-bound negatives: a substring inside a longer token is not the
    // construction, and the full form is not matched by the abbreviated one.
    for negative in [
        "ввиду редакции документа",
        "Петров ред. документа",
        "в редакциях документа",
        "согласно редакции",
    ] {
        assert!(
            detect_edition_relations(negative).is_empty(),
            "F12-edition-relation: {negative:?} must not mint a candidate"
        );
    }

    // F12-NO-IR: the candidate carries nothing but its surface and anchor, and
    // the wording never authorizes a reference construction.
    let debug = format!("{:?}", candidates[0]);
    for forbidden in ["force", "edition_date", "Force", "Status", "Applicability"] {
        assert!(
            !debug.contains(forbidden),
            "F12-NO-IR: an edition relation candidate must not carry {forbidden}"
        );
    }
    let (index, overlay) = construction_fixture();
    let origin = FrameId::new(1);
    for construction in [
        ReferenceConstruction::CurrentDocumentSelf,
        ReferenceConstruction::EarlierCitedAct,
        ReferenceConstruction::DeclaredScopedAlias,
        ReferenceConstruction::CoordinatingHead,
    ] {
        let request = ConstructionRequest::new(construction, origin, 1).key("в ред.");
        assert!(
            !resolve_construction(&request, &index, &overlay, true).is_resolved(),
            "F12-NO-IR: the edition wording must not authorize {construction:?}"
        );
    }

    // No legal IR: the cue surface still abstains on the normative slots.
    let (block, claims) = extract("Орган должен действовать в ред. 01.01.2020 N 1-ФЗ.", true);
    match project_norm_rule(claims, Terminal::Resolved) {
        ProjectionOutcome::Abstained(record) => assert!(
            record.reasons().contains(&AbstentionReason::MissingAction)
                && record.reasons().contains(&AbstentionReason::MissingObject),
            "F12-NO-IR: an edition relation must not complete a norm rule"
        ),
        ProjectionOutcome::Complete(_) => {
            panic!("F12-NO-IR: an edition relation must not mint Applicable/NormRule IR")
        }
    }
    assert!(!block.text().is_empty());
}
