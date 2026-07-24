use ln_temporal::{
    adapters::SubstitutingHostileEvidence,
    application::ResolveFiveClockState,
    domain::{ClockKind, RequestId, ResolutionOutcome, ResolutionRequest, SubstituteKind},
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
fn hostile_evidence_cannot_force_resolved_via_wall_clock_or_other_clocks() {
    for governing in ClockKind::all() {
        let evidence = SubstitutingHostileEvidence::missing(governing);
        let resolver = ResolveFiveClockState::new(evidence);
        let result = resolver.resolve(ResolutionRequest {
            request_id: RequestId::parse(&format!("hostile:{}", governing.as_str()))
                .expect("valid"),
            governing_clock: governing,
            attempted_substitutes: forbidden_substitutes(governing),
        });

        assert_ne!(result.outcome, ResolutionOutcome::Resolved);
        assert_eq!(result.outcome, ResolutionOutcome::SubstituteRejected);
        assert!(!result.substitution_used);
        assert!(result.resolved_anchor.is_none());
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
        assert!(result
            .trace
            .rejected_substitutes
            .iter()
            .any(|s| s == "lifecycle_type"));
        // At least one other-clock substitute was rejected.
        assert!(result
            .trace
            .rejected_substitutes
            .iter()
            .any(|s| s.starts_with("other_clock:")));
    }
}

#[test]
fn hostile_wall_clock_only_request_is_still_rejected() {
    let evidence = SubstitutingHostileEvidence::missing(ClockKind::Proceeding);
    let resolver = ResolveFiveClockState::new(evidence);
    let result = resolver.resolve(ResolutionRequest {
        request_id: RequestId::parse("hostile:wall-only").expect("valid"),
        governing_clock: ClockKind::Proceeding,
        attempted_substitutes: vec![SubstituteKind::WallClock],
    });
    assert_eq!(result.outcome, ResolutionOutcome::SubstituteRejected);
    assert_eq!(
        result.trace.rejected_substitutes,
        vec!["wall_clock".to_owned()]
    );
    assert!(!result.substitution_used);
}

#[test]
fn hostile_adapter_does_not_invent_governing_anchor() {
    let evidence = SubstitutingHostileEvidence::missing(ClockKind::SourcePublication);
    let resolver = ResolveFiveClockState::new(evidence);
    let result = resolver.resolve(ResolutionRequest {
        request_id: RequestId::parse("hostile:no-anchor").expect("valid"),
        governing_clock: ClockKind::SourcePublication,
        attempted_substitutes: Vec::new(),
    });
    assert_eq!(result.outcome, ResolutionOutcome::MissingAnchor);
    assert!(result.trace.governing_anchor.is_none());
}
