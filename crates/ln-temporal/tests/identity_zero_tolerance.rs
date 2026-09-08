use ln_temporal::document_context::{BlockId, TextSpan};
use ln_temporal::identity_binding::*;

fn span(start: usize, end: usize) -> TextSpan {
    TextSpan::new(start, end).expect("fixture span")
}

fn claim(field: FieldKind, value: &str) -> IdentityFieldClaim {
    IdentityFieldClaim::new(
        field,
        BlockId::new(7),
        span(0, value.len()),
        FieldSource::ExplicitMember,
        FieldStatus::Explicit,
        value,
    )
    .expect("fixture claim")
}

#[test]
fn clean_run_counts_candidates_and_has_zero_tolerance_violations() {
    let act = assemble_identifying_act(vec![
        claim(FieldKind::Type, "региональный приказ"),
        claim(FieldKind::Org, "Мэрия"),
        claim(FieldKind::Geo, "Казань"),
        claim(FieldKind::Date, "2024-01-01"),
        claim(FieldKind::Number, "3"),
    ]);
    let ActAssemblyOutcome::Compatible(act_candidate) = &act else {
        panic!("expected compatible act")
    };
    let identity = build_official_identity_claim(act_candidate);
    let IdentityClaimOutcome::Proposed(identity_candidate) = &identity else {
        panic!("expected proposed identity claim")
    };
    let pair = expand_range_to_endpoints(
        ReferenceEndpoint::new("7.29", span(10, 14)).unwrap(),
        ReferenceEndpoint::new("7.32", span(15, 19)).unwrap(),
        4,
    )
    .unwrap();
    let binding = BindingOutcome::Candidate(
        ReferenceBindingCandidate::new(
            span(10, 19),
            identity_candidate.claim_id(),
            BoundTarget::Claim(identity_candidate.claim_id().to_owned()),
            BindingEndpoints::Pair(pair),
        )
        .unwrap(),
    );

    let mut run = IdentityBindingRun::new();
    run.record_act_outcome(&act);
    run.record_identity_claim_outcome(&identity);
    run.record_binding_outcome(&binding);

    assert_eq!(run.counters().false_identity_mint, 0);
    assert_eq!(run.counters().false_link, 0);
    assert_eq!(run.counters().claims_total, 5);
    assert_eq!(run.counters().acts_total, 1);
    assert_eq!(run.counters().identity_claims_total, 1);
    assert_eq!(run.counters().bindings_total, 1);
    assert_eq!(run.counters().endpoint_pairs_total, 1);
    assert_eq!(verify_identity_zero_tolerance(&run), Ok(()));
}

#[test]
fn hostile_events_are_reported_as_typed_violations() {
    let mut run = IdentityBindingRun::new();
    run.record_event(IdentityBindingEvent::FalseIdentityMint);
    run.record_event(IdentityBindingEvent::FalseLink);

    assert_eq!(
        verify_identity_zero_tolerance(&run),
        Err(vec![
            IdentityBindingViolation::FalseIdentityMint,
            IdentityBindingViolation::FalseLink,
        ])
    );
}

#[test]
fn diagnostic_json_is_byte_stable_and_has_no_promotion_keys() {
    let mut run = IdentityBindingRun::new();
    run.record_event(IdentityBindingEvent::FalseLink);
    let first = render_identity_run_json(&run);
    let second = render_identity_run_json(&run);

    assert_eq!(first, second);
    assert!(first.contains("\"false_link\":1"));
    for forbidden in ["promotion", "readiness", "lifecycle"] {
        assert!(!first.contains(forbidden), "unexpected key: {forbidden}");
    }
}

#[test]
fn unresolved_and_expansion_limit_are_counted_without_smoothing() {
    let incomplete = IdentityClaimOutcome::Incomplete {
        missing: vec![FieldKind::Geo],
        reason: "missing authorized geo".into(),
    };
    let unresolved = BindingOutcome::Unresolved {
        reason: BindingUnresolvedReason::MissingTargetClaim,
    };
    let limit = BindingOutcome::ExpansionLimit(
        expand_range_to_endpoints(
            ReferenceEndpoint::new("1", span(0, 1)).unwrap(),
            ReferenceEndpoint::new("100", span(2, 5)).unwrap(),
            MAX_EXPANDED_CANDIDATES + 1,
        )
        .expect_err("budget must remain typed"),
    );

    let mut run = IdentityBindingRun::new();
    run.record_identity_claim_outcome(&incomplete);
    run.record_binding_outcome(&unresolved);
    run.record_binding_outcome(&limit);

    assert_eq!(run.counters().unresolved_total, 2);
    assert_eq!(run.counters().expansion_limit_total, 1);
    assert_eq!(run.counters().bindings_total, 2);
}
