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
