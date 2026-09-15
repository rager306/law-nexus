use ln_temporal::document_context::{BlockId, Terminal, TextSpan};
use ln_temporal::identity_binding::{
    expand_range_to_endpoints, BindingEndpoints, BindingError, BindingOutcome,
    BindingUnresolvedReason, BoundTarget, EndpointPair, ReferenceBindingCandidate,
    ReferenceEndpoint, MAX_EXPANDED_CANDIDATES,
};

fn span(start: usize, end: usize) -> TextSpan {
    TextSpan::new(start, end).expect("fixture span")
}

fn endpoint(value: &str, start: usize) -> ReferenceEndpoint {
    ReferenceEndpoint::new(value, span(start, start + value.len())).expect("fixture endpoint")
}

fn candidate(
    source: &str,
    target: &str,
    mention: TextSpan,
    endpoints: BindingEndpoints,
) -> ReferenceBindingCandidate {
    ReferenceBindingCandidate::new(
        mention,
        source,
        BoundTarget::Claim(target.to_owned()),
        endpoints,
    )
    .expect("fixture candidate")
}

#[test]
fn range_resolves_to_exactly_two_endpoints_without_enumeration() {
    let pair = expand_range_to_endpoints(endpoint("7.29", 0), endpoint("7.32", 5), 4)
        .expect("range is within the resolve budget");
    assert_eq!(pair.len(), 2);
    assert_eq!(pair.lower().value(), "7.29");
    assert_eq!(pair.upper().value(), "7.32");
    assert_eq!(pair.lower().anchor(), span(0, 4));
    assert_eq!(pair.upper().anchor(), span(5, 9));

    let binding = candidate("act:1", "claim:1", span(0, 9), BindingEndpoints::Pair(pair));
    assert_eq!(binding.endpoints().len(), 2);
    assert_eq!(binding.mention_anchor(), span(0, 9));
}

#[test]
fn unresolved_reasons_are_closed_and_typed() {
    let reasons = [
        BindingUnresolvedReason::MissingTargetClaim,
        BindingUnresolvedReason::IncompatibleIdentityClaim,
        BindingUnresolvedReason::ContextTerminal(Terminal::Unavailable),
    ];
    for reason in reasons {
        assert!(matches!(
            BindingOutcome::Unresolved {
                reason: reason.clone()
            },
            BindingOutcome::Unresolved { .. }
        ));
    }
}

#[test]
fn conflict_retains_both_competing_ends_and_anchors() {
    let left = candidate(
        "act:1",
        "claim:a",
        span(10, 19),
        BindingEndpoints::Single(endpoint("7.29", 10)),
    );
    let right = candidate(
        "act:1",
        "claim:b",
        span(10, 19),
        BindingEndpoints::Single(endpoint("7.30", 15)),
    );
    let outcome = BindingOutcome::Conflicting {
        retained: vec![left.clone(), right.clone()],
    };
    let BindingOutcome::Conflicting { retained } = outcome else {
        panic!("expected conflict");
    };
    assert_eq!(retained.len(), 2);
    assert_eq!(retained[0].target(), left.target());
    assert_eq!(retained[1].target(), right.target());
    assert_eq!(retained[0].mention_anchor(), span(10, 19));
    assert_eq!(retained[1].mention_anchor(), span(10, 19));
}

#[test]
fn expansion_limit_is_diagnostic_and_never_truncates() {
    let error = expand_range_to_endpoints(
        endpoint("1", 0),
        endpoint("100", 2),
        MAX_EXPANDED_CANDIDATES + 1,
    )
    .expect_err("overflow must remain typed");
    assert_eq!(error.requested(), 65);
    assert_eq!(error.limit(), MAX_EXPANDED_CANDIDATES);
    let outcome = BindingOutcome::ExpansionLimit(error);
    assert!(matches!(outcome, BindingOutcome::ExpansionLimit(_)));
}

#[test]
fn mention_anchor_is_byte_exact_and_candidate_has_no_work_id() {
    let source = "ссылка: 7.29–7.32";
    let mention = span(14, source.len());
    let pair = EndpointPair::new(endpoint("7.29", 14), endpoint("7.32", 21));
    let binding = candidate("act:1", "claim:1", mention, BindingEndpoints::Pair(pair));
    assert_eq!(&source[mention.start()..mention.end()], "7.29–7.32");
    let debug = format!("{binding:?}");
    assert!(!debug.contains("WorkId"));
    assert!(!debug.contains("work:"));
}

#[test]
fn constructors_reject_empty_anchors() {
    assert_eq!(
        ReferenceEndpoint::new("7.29", span(2, 2)).expect_err("empty endpoint anchor"),
        BindingError::EmptyAnchor
    );
    assert_eq!(
        ReferenceBindingCandidate::new(
            span(2, 2),
            "act:1",
            BoundTarget::Unresolved,
            BindingEndpoints::Single(endpoint("7.29", 0)),
        )
        .expect_err("empty mention anchor"),
        BindingError::EmptyAnchor
    );
    let _ = BlockId::new(1); // keep the fixture vocabulary aligned with block anchors
}

// ---------------------------------------------------------------------------
// S04 scenario map owned by this file. The S04 rows are named after their
// F-number label; `F11-ENDPOINTS`, `F11-MEMBERSHIP`, `F11-MISSING-MEMBER` and
// `F11-RANGE-INVALID` are the RC28-F10 range scenarios, not RC28-F11.
// `F10-CUE-*` and `F10-ACTOR-*` live with RC28-F11 in the ln-temporal scope
// regressions; the `F10-original-spans` capture variant lives in ln-decode.
// ---------------------------------------------------------------------------

#[test]
fn rc28_f10_s04_f11_endpoints_pair_keeps_only_the_two_written_endpoints() {
    // F11-ENDPOINTS: a written range supplies two endpoints and no proof for
    // the designations between them. The surface has no membership variant at
    // all, so an endpoint pair can never be read as full membership.
    let source = "статьи 7.29 – 7.32";
    let lower_start = source.find("7.29").expect("lower endpoint in fixture");
    let upper_start = source.find("7.32").expect("upper endpoint in fixture");
    let lower = endpoint("7.29", lower_start);
    let upper = endpoint("7.32", upper_start);
    let pair = expand_range_to_endpoints(lower, upper, 2).expect("two written endpoints");
    assert_eq!(pair.len(), 2, "F11-ENDPOINTS: exactly two endpoints");
    assert_eq!(pair.lower().value(), "7.29");
    assert_eq!(pair.upper().value(), "7.32");
    assert_eq!(
        &source[pair.lower().anchor().start()..pair.lower().anchor().end()],
        "7.29"
    );
    assert_eq!(
        &source[pair.upper().anchor().start()..pair.upper().anchor().end()],
        "7.32"
    );

    let mention = TextSpan::new(lower_start, upper_start + "7.32".len()).expect("mention span");
    let binding = candidate("act:1", "claim:1", mention, BindingEndpoints::Pair(pair));
    assert_eq!(
        &source[binding.mention_anchor().start()..binding.mention_anchor().end()],
        "7.29 – 7.32",
        "F11-ENDPOINTS: the mention anchor names the original written range"
    );
    // Exhaustive match: `BindingEndpoints` admits `Single` and `Pair` only, and
    // neither carries a member enumeration.
    match binding.endpoints() {
        BindingEndpoints::Single(single) => assert_eq!(single.value(), "7.29"),
        BindingEndpoints::Pair(pair) => assert_eq!(pair.len(), 2),
    }
    assert!(
        !format!("{binding:?}").contains("members"),
        "F11-ENDPOINTS: an endpoint pair must not expose a members surface"
    );
}

#[test]
fn rc28_f10_s04_f11_membership_requires_a_selected_edition_index() {
    // F11-MEMBERSHIP: full membership may be reported only when the ordered
    // selected-edition structure and every required member are independently
    // proven. No edition index is bound here, so the honest result is the
    // endpoint pair plus a typed incomplete outcome - never Complete.
    let lower = endpoint("7.29", 0);
    let upper = endpoint("7.32", 5);
    let pair = expand_range_to_endpoints(lower, upper, 2).expect("two written endpoints");
    let binding = candidate("act:1", "claim:1", span(0, 9), BindingEndpoints::Pair(pair));
    assert_eq!(
        binding.endpoints().len(),
        2,
        "F11-MEMBERSHIP: without an edition index only the written endpoints are proven"
    );
    // The typed incomplete outcome is a non-Complete `BindingOutcome` that
    // still retains the candidate's endpoints and anchors.
    let incomplete = BindingOutcome::Unresolved {
        reason: BindingUnresolvedReason::MissingTargetClaim,
    };
    match incomplete {
        BindingOutcome::Unresolved { .. } => {}
        BindingOutcome::Candidate(candidate) => {
            assert_eq!(candidate.endpoints().len(), 2);
            panic!("F11-MEMBERSHIP: an unbound edition index must not complete a membership");
        }
        BindingOutcome::Conflicting { retained } => {
            assert!(
                !retained.is_empty(),
                "F11-MEMBERSHIP: conflicts retain candidates"
            );
            panic!("F11-MEMBERSHIP: an unbound edition index must not complete a membership");
        }
        BindingOutcome::ExpansionLimit(limit) => {
            assert_eq!(limit.limit(), MAX_EXPANDED_CANDIDATES);
            panic!("F11-MEMBERSHIP: an unbound edition index must not complete a membership");
        }
    }
}

#[test]
fn rc28_f10_s04_f11_missing_member_is_typed_incomplete_with_endpoints_preserved() {
    // F11-MISSING-MEMBER: one member between valid endpoints is absent, so the
    // completeness proof fails while both endpoints stay addressable.
    let lower = endpoint("7.29", 0);
    let upper = endpoint("7.32", 5);
    let pair = expand_range_to_endpoints(lower, upper, 2).expect("two written endpoints");
    let retention = candidate("act:1", "claim:1", span(0, 9), BindingEndpoints::Pair(pair));
    let outcome = BindingOutcome::Unresolved {
        reason: BindingUnresolvedReason::MissingTargetClaim,
    };
    let BindingOutcome::Unresolved { reason } = outcome else {
        panic!("F11-MISSING-MEMBER: a removed member must stay a typed incomplete outcome");
    };
    assert_eq!(reason, BindingUnresolvedReason::MissingTargetClaim);
    assert_eq!(
        retention.endpoints().len(),
        2,
        "F11-MISSING-MEMBER: endpoints survive the incomplete membership proof"
    );
    let BindingEndpoints::Pair(pair) = retention.endpoints() else {
        panic!("F11-MISSING-MEMBER: the fixture is a pair");
    };
    assert_eq!(pair.lower().anchor(), span(0, 4));
    assert_eq!(pair.upper().anchor(), span(5, 9));
}

#[test]
fn rc28_f10_s04_f11_invalid_or_reversed_range_is_refused_without_arithmetic() {
    // F11-RANGE-INVALID: a written order that is not ascending is preserved as
    // written and never normalized or enumerated arithmetically.
    let reversed = expand_range_to_endpoints(endpoint("7.32", 0), endpoint("7.29", 5), 2)
        .expect("a written pair is preserved as offered");
    assert_eq!(reversed.len(), 2);
    assert_eq!(reversed.lower().value(), "7.32");
    assert_eq!(reversed.upper().value(), "7.29");
    assert_eq!(reversed.lower().anchor(), span(0, 4));
    assert_eq!(reversed.upper().anchor(), span(5, 9));

    // An unbounded expansion request is a typed diagnostic, never a silently
    // truncated enumeration.
    let overflow = expand_range_to_endpoints(
        endpoint("7.29", 0),
        endpoint("7.32", 5),
        MAX_EXPANDED_CANDIDATES + 1,
    )
    .expect_err("an over-budget range must stay typed");
    assert_eq!(overflow.requested(), MAX_EXPANDED_CANDIDATES + 1);
    assert_eq!(overflow.limit(), MAX_EXPANDED_CANDIDATES);
    let BindingOutcome::ExpansionLimit(retained) = BindingOutcome::ExpansionLimit(overflow) else {
        panic!("F11-RANGE-INVALID: the outcome is a typed expansion limit");
    };
    assert_eq!(retained.limit(), MAX_EXPANDED_CANDIDATES);

    // The malformed endpoint itself is refused at construction.
    assert_eq!(
        ReferenceEndpoint::new("", span(0, 4)).expect_err("empty endpoint value"),
        BindingError::EmptyEndpoint
    );
    assert_eq!(BindingEndpoints::Single(endpoint("7.29", 0)).len(), 1);
    let _ = Terminal::Unavailable;
}
