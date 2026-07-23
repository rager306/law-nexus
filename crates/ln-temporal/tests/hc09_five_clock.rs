use ln_temporal::{
    adapters::InMemoryClockEvidence,
    application::ResolveFiveClockState,
    domain::{
        ClockKind, RequestId, ResolutionOutcome, ResolutionRequest, SubstituteKind,
        D118_POLICY_VERSION,
    },
};

fn forbidden_substitutes(missing: ClockKind) -> Vec<SubstituteKind> {
    let mut out = vec![
        SubstituteKind::WallClock,
        SubstituteKind::EditionOrder,
        SubstituteKind::LifecycleType,
    ];
    for clock in ClockKind::all() {
        if clock != missing {
            out.push(SubstituteKind::OtherClock(clock));
        }
    }
    out
}

#[test]
fn each_missing_governing_clock_rejects_all_substitutions() {
    for governing in ClockKind::all() {
        let evidence = InMemoryClockEvidence::with_all_except(governing);
        let resolver = ResolveFiveClockState::new(evidence);
        let substitutes = forbidden_substitutes(governing);
        let result = resolver.resolve(ResolutionRequest {
            request_id: RequestId::parse(&format!("req:{}", governing.as_str())).expect("valid"),
            governing_clock: governing,
            attempted_substitutes: substitutes.clone(),
        });

        assert!(
            result.outcome.is_fail_closed(),
            "governing {} must not resolve via substitution",
            governing.as_str()
        );
        assert_eq!(result.outcome, ResolutionOutcome::SubstituteRejected);
        assert!(!result.substitution_used);
        assert!(result.resolved_anchor.is_none());
        assert_eq!(result.governing_clock, governing);
        assert_eq!(result.trace.governing_clock, governing);
        assert!(result.trace.governing_anchor.is_none());
        assert_eq!(result.trace.policy_version, D118_POLICY_VERSION);
        assert_eq!(
            result.trace.rejected_substitutes.len(),
            substitutes.len(),
            "all attempted substitutes must be rejected for {}",
            governing.as_str()
        );
        assert!(result
            .trace
            .rejected_substitutes
            .iter()
            .any(|s| s == "wall_clock"));
        assert!(result
            .trace
            .rejected_substitutes
            .iter()
            .any(|s| s == "edition_order"));
    }
}

#[test]
fn missing_anchor_without_substitutes_is_missing_anchor() {
    let evidence = InMemoryClockEvidence::with_all_except(ClockKind::LegalActEffect);
    let resolver = ResolveFiveClockState::new(evidence);
    let result = resolver.resolve(ResolutionRequest {
        request_id: RequestId::parse("req:no-sub").expect("valid"),
        governing_clock: ClockKind::LegalActEffect,
        attempted_substitutes: Vec::new(),
    });
    assert_eq!(result.outcome, ResolutionOutcome::MissingAnchor);
    assert!(!result.substitution_used);
    assert!(result.trace.rejected_substitutes.is_empty());
    assert!(result.trace.considered_substitutes.is_empty());
}

#[test]
fn present_governing_anchor_resolves_without_substitution() {
    let evidence = InMemoryClockEvidence::with_only(
        ClockKind::FactualEvent,
        ln_temporal::domain::AnchorId::parse("anchor:factual_event").expect("valid"),
    );
    let resolver = ResolveFiveClockState::new(evidence);
    let result = resolver.resolve(ResolutionRequest {
        request_id: RequestId::parse("req:ok").expect("valid"),
        governing_clock: ClockKind::FactualEvent,
        attempted_substitutes: vec![SubstituteKind::WallClock, SubstituteKind::EditionOrder],
    });
    assert_eq!(result.outcome, ResolutionOutcome::Resolved);
    assert!(!result.substitution_used);
    assert_eq!(
        result.resolved_anchor.as_ref().map(|a| a.as_str()),
        Some("anchor:factual_event")
    );
    assert!(result.trace.rejected_substitutes.is_empty());
    assert_eq!(result.trace.considered_substitutes.len(), 2);
}
