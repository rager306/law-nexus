use ln_temporal::document_context::{BlockId, Terminal, TextSpan};
use ln_temporal::semantic_scope::{
    project_norm_rule, AbstentionReason, CandidateSlot, ProjectionOutcome, SemanticClaim,
    SemanticClaimKind,
};

fn claim(kind: SemanticClaimKind, start: usize) -> SemanticClaim {
    let span = TextSpan::new(start, start + 2).unwrap();
    SemanticClaim::new(kind, BlockId::new(7), span, vec![span]).unwrap()
}

fn complete_claims() -> Vec<SemanticClaim> {
    vec![
        claim(SemanticClaimKind::Actor, 0),
        claim(SemanticClaimKind::Action, 2),
        claim(SemanticClaimKind::Object, 4),
        claim(SemanticClaimKind::Polarity, 6),
        claim(SemanticClaimKind::Condition, 8),
        claim(SemanticClaimKind::Exception, 10),
        claim(SemanticClaimKind::TemporalQualifier, 12),
    ]
}

#[test]
fn resolved_complete_projection_keeps_all_semantic_slots_and_anchors() {
    let outcome = project_norm_rule(complete_claims(), Terminal::Resolved);
    let ProjectionOutcome::Complete(candidate) = outcome else {
        panic!("expected complete")
    };

    assert!(!candidate.candidate_id().contains("WorkId"));
    assert_eq!(candidate.actor().kind(), SemanticClaimKind::Actor);
    assert_eq!(candidate.action().kind(), SemanticClaimKind::Action);
    assert_eq!(candidate.object().kind(), SemanticClaimKind::Object);
    assert_eq!(candidate.polarity().kind(), SemanticClaimKind::Polarity);
    assert_eq!(candidate.conditions().len(), 1);
    assert_eq!(candidate.exceptions().len(), 1);
    assert_eq!(candidate.temporal_qualifier().len(), 1);
    assert_eq!(candidate.anchors().len(), 7);
}

#[test]
fn every_missing_required_slot_abstains_with_typed_reason() {
    let required = [
        (
            SemanticClaimKind::Actor,
            CandidateSlot::Actor,
            AbstentionReason::MissingActor,
        ),
        (
            SemanticClaimKind::Action,
            CandidateSlot::Action,
            AbstentionReason::MissingAction,
        ),
        (
            SemanticClaimKind::Object,
            CandidateSlot::Object,
            AbstentionReason::MissingObject,
        ),
        (
            SemanticClaimKind::Polarity,
            CandidateSlot::Polarity,
            AbstentionReason::MissingPolarity,
        ),
    ];
    for (kind, slot, reason) in required {
        let claims = complete_claims()
            .into_iter()
            .filter(|c| c.kind() != kind)
            .collect::<Vec<_>>();
        let ProjectionOutcome::Abstained(record) = project_norm_rule(claims, Terminal::Resolved)
        else {
            panic!("expected abstention")
        };
        assert!(record.reasons().contains(&reason));
        assert!(record.missing().contains(&slot));
    }
}

#[test]
fn all_unresolved_context_terminals_are_preserved_as_abstention() {
    for terminal in [
        Terminal::Partial,
        Terminal::Conflicting,
        Terminal::Unavailable,
        Terminal::Cycle,
        Terminal::Limit,
    ] {
        let ProjectionOutcome::Abstained(record) = project_norm_rule(complete_claims(), terminal)
        else {
            panic!("expected abstention")
        };
        assert_eq!(
            record.reasons(),
            &[AbstentionReason::ContextTerminal(terminal)]
        );
        assert_eq!(record.claims().len(), 7);
        assert_eq!(record.anchors().len(), 7);
    }
}

#[test]
fn conflicting_same_slot_abstains_without_precedence_winner() {
    let mut claims = complete_claims();
    claims.push(claim(SemanticClaimKind::Action, 20));
    let ProjectionOutcome::Abstained(record) = project_norm_rule(claims, Terminal::Resolved) else {
        panic!("expected abstention")
    };
    assert!(record
        .reasons()
        .contains(&AbstentionReason::ConflictingSlots));
    assert_eq!(record.claims().len(), 8);
    assert!(
        record
            .claims()
            .iter()
            .filter(|c| c.kind() == SemanticClaimKind::Action)
            .count()
            == 2
    );
}

#[test]
fn partial_scope_cannot_be_unconditionalized() {
    let claims = vec![
        claim(SemanticClaimKind::Actor, 0),
        claim(SemanticClaimKind::Action, 2),
        claim(SemanticClaimKind::Object, 4),
        claim(SemanticClaimKind::Polarity, 6),
        claim(SemanticClaimKind::Condition, 8),
    ];
    let ProjectionOutcome::Complete(_) = project_norm_rule(claims.clone(), Terminal::Partial)
    else {
        let ProjectionOutcome::Abstained(record) = project_norm_rule(claims, Terminal::Partial)
        else {
            panic!("expected abstention")
        };
        assert!(record
            .reasons()
            .contains(&AbstentionReason::ContextTerminal(Terminal::Partial)));
        assert_eq!(record.claims().len(), 5);
        return;
    };
    panic!("partial context must never become an unconditional candidate");
}
