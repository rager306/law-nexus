use ln_temporal::document_context::{BlockId, Terminal, TextSpan};
use ln_temporal::semantic_scope::{
    project_norm_rule, render_scope_run_json, verify_zero_tolerance, AbstentionReason,
    ProjectionOutcome, SemanticClaim, SemanticClaimKind, SemanticScopeEvent, SemanticScopeRun,
    SemanticScopeViolation,
};

fn claim(kind: SemanticClaimKind, start: usize) -> SemanticClaim {
    let span = TextSpan::new(start, start + 2).unwrap();
    SemanticClaim::new(kind, BlockId::new(11), span, vec![span]).unwrap()
}

fn complete_claims() -> Vec<SemanticClaim> {
    vec![
        claim(SemanticClaimKind::Actor, 0),
        claim(SemanticClaimKind::Action, 2),
        claim(SemanticClaimKind::Object, 4),
        claim(SemanticClaimKind::Polarity, 6),
        claim(SemanticClaimKind::Condition, 8),
    ]
}

#[test]
fn clean_run_has_zero_semantic_loss_and_stable_json() {
    let complete = project_norm_rule(complete_claims(), Terminal::Resolved);
    let mut run = SemanticScopeRun::new();
    run.record_projection(&complete);

    assert_eq!(run.counters().critical_field_loss, 0);
    assert_eq!(run.counters().source_span_loss, 0);
    assert_eq!(run.counters().false_fact_mint, 0);
    assert_eq!(run.counters().unconditionalized_scope, 0);
    assert_eq!(run.counters().unexplained_abstention, 0);
    assert_eq!(run.counters().candidates_total, 1);
    assert_eq!(run.counters().abstained_total, 0);
    assert_eq!(verify_zero_tolerance(&run), Ok(()));

    let first = render_scope_run_json(&run);
    assert_eq!(first, render_scope_run_json(&run));
    assert!(first.contains("\"semantic_loss\""));
    assert!(first.contains("\"critical_field_loss\":0"));
    assert!(first.contains("\"source_span_loss\":0"));
    assert!(first.contains("\"false_fact_mint\":0"));
}

#[test]
fn hostile_conflict_and_multi_cue_inputs_abstain_without_semantic_loss() {
    let mut conflicting = complete_claims();
    conflicting.push(claim(SemanticClaimKind::Action, 20));
    let conflict = project_norm_rule(conflicting, Terminal::Resolved);
    let unresolved = project_norm_rule(complete_claims(), Terminal::Conflicting);
    let mut run = SemanticScopeRun::new();
    run.record_batch([&conflict, &unresolved]);

    assert!(matches!(conflict, ProjectionOutcome::Abstained(ref record)
        if record.reasons().contains(&AbstentionReason::ConflictingSlots)));
    assert!(matches!(unresolved, ProjectionOutcome::Abstained(_)));
    assert_eq!(run.counters().candidates_total, 2);
    assert_eq!(run.counters().abstained_total, 2);
    assert_eq!(run.counters().critical_field_loss, 0);
    assert_eq!(run.counters().source_span_loss, 0);
    assert_eq!(run.counters().false_fact_mint, 0);
    assert_eq!(run.counters().unconditionalized_scope, 0);
    assert_eq!(run.counters().unexplained_abstention, 0);
    assert_eq!(verify_zero_tolerance(&run), Ok(()));
}

#[test]
fn seeded_diagnostic_event_returns_typed_violation() {
    let mut run = SemanticScopeRun::new();
    run.record_event(SemanticScopeEvent::FalseFactMint);
    run.record_event(SemanticScopeEvent::UnconditionalizedScope);

    assert_eq!(
        verify_zero_tolerance(&run),
        Err(vec![
            SemanticScopeViolation::FalseFactMint,
            SemanticScopeViolation::UnconditionalizedScope,
        ])
    );
    let report = render_scope_run_json(&run);
    assert!(report.contains("\"false_fact_mint\":1"));
    assert!(report.contains("\"unconditionalized_scope\":1"));
}
