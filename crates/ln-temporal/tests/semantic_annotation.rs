use ln_temporal::document_context::{BlockId, TextSpan};
use ln_temporal::semantic_annotation::{
    agreement, render_json, validate, validate_pair, AnnotationClaim, AnnotationRecord,
    AnnotationValidationError, CandidateSlotVerdict,
};
use ln_temporal::semantic_scope::{CandidateSlot, SemanticClaimKind};

fn span(start: usize) -> TextSpan {
    TextSpan::new(start, start + 3).unwrap()
}

fn record(coder: &str, action_label: &str) -> AnnotationRecord {
    AnnotationRecord::new(
        "doc-v1",
        coder,
        vec![
            AnnotationClaim::new(
                SemanticClaimKind::Actor,
                BlockId::new(2),
                span(0),
                "organization",
            ),
            AnnotationClaim::new(
                SemanticClaimKind::Action,
                BlockId::new(2),
                span(4),
                action_label,
            ),
            AnnotationClaim::new(SemanticClaimKind::Condition, BlockId::new(2), span(8), "if"),
        ],
        vec![CandidateSlotVerdict::new(
            "candidate-2:0-3",
            CandidateSlot::Actor,
            "supported",
        )],
    )
}

#[test]
fn valid_independent_pair_passes_and_acceptance_is_not_minted() {
    let first = record("coder-a", "act");
    let second = record("coder-b", "act");
    assert_eq!(validate_pair(&first, &second), Ok(()));
    assert_eq!(
        agreement(&first, &second)
            .unwrap()
            .kind(SemanticClaimKind::Action)
            .unwrap()
            .agreed(),
        1
    );
    assert!(!render_json(&first).contains("acceptance"));
}

#[test]
fn duplicate_coder_id_is_rejected_fail_closed() {
    let first = record("same", "act");
    let second = record("same", "act");
    assert_eq!(
        validate_pair(&first, &second),
        Err(AnnotationValidationError::DuplicateCoderId)
    );
}

#[test]
fn unknown_kind_is_rejected() {
    let record = AnnotationRecord::new(
        "doc-v1",
        "coder-a",
        vec![AnnotationClaim::with_kind_name(
            "InventedKind",
            BlockId::new(1),
            span(0),
            "x",
        )],
        vec![],
    );
    assert_eq!(
        validate(&record),
        Err(AnnotationValidationError::UnknownClaimKind)
    );
}

#[test]
fn label_without_non_empty_anchor_is_rejected() {
    let empty = TextSpan::new(5, 5).unwrap();
    let record = AnnotationRecord::new(
        "doc-v1",
        "coder-a",
        vec![AnnotationClaim::new(
            SemanticClaimKind::Action,
            BlockId::new(1),
            empty,
            "act",
        )],
        vec![],
    );
    assert_eq!(
        validate(&record),
        Err(AnnotationValidationError::EmptyClaimSpan)
    );
}

#[test]
fn agreement_is_exact_per_kind_by_block_and_span() {
    let first = record("coder-a", "act");
    let second = record("coder-b", "do");
    let summary = agreement(&first, &second).unwrap();
    let actor = summary.kind(SemanticClaimKind::Actor).unwrap();
    assert_eq!(
        (actor.total(), actor.agreed(), actor.disagreements()),
        (1, 1, 0)
    );
    let action = summary.kind(SemanticClaimKind::Action).unwrap();
    assert_eq!(
        (action.total(), action.agreed(), action.disagreements()),
        (1, 0, 1)
    );
    assert_eq!(
        summary.kind(SemanticClaimKind::Condition).unwrap().total(),
        1
    );
}

#[test]
fn json_render_is_byte_stable_and_sorts_records() {
    let first = record("coder-a", "act");
    let mut reordered = AnnotationRecord::new(
        "doc-v1",
        "coder-a",
        vec![
            AnnotationClaim::new(SemanticClaimKind::Condition, BlockId::new(2), span(8), "if"),
            AnnotationClaim::new(
                SemanticClaimKind::Actor,
                BlockId::new(2),
                span(0),
                "organization",
            ),
            AnnotationClaim::new(SemanticClaimKind::Action, BlockId::new(2), span(4), "act"),
        ],
        vec![CandidateSlotVerdict::with_slot_name(
            "candidate-2:0-3",
            "Actor",
            "supported",
        )],
    );
    assert_eq!(render_json(&first), render_json(&reordered));
    reordered = reordered.with_schema_version("law-nexus-semantic-annotation/v1");
    assert_eq!(render_json(&reordered), render_json(&first));
}
