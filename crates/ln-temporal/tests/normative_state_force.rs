//! Bounded force-status NormativeState resolver (TSG-004 S2/S3 / ADR-0018).
//!
//! Force dimension only. Not CTV join, not applicability, not legal corpus proof.

use ln_temporal::domain::{
    resolve_force_status_at, AmendingActId, ComponentConceptId, ForceStatusEvent,
    ForceStatusTimeline, NormativeState, NormativeStateError,
};

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn act(id: &str) -> AmendingActId {
    AmendingActId::parse(id).expect("act")
}

fn event(
    component: &str,
    status: NormativeState,
    effect_day: i64,
    provenance: &str,
) -> ForceStatusEvent {
    ForceStatusEvent::try_new(cc(component), status, effect_day, act(provenance)).expect("event")
}

#[test]
fn empty_timeline_is_unknown_not_in_force() {
    let timeline = ForceStatusTimeline::empty();
    let result = resolve_force_status_at(&timeline, &cc("cc:art-1"), 100).expect("resolve");
    assert_eq!(result.status, NormativeState::Unknown);
    assert!(result
        .non_claims
        .iter()
        .any(|c| c.contains("not") || c.contains("Force")));
}

#[test]
fn latest_prior_event_wins() {
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(event("cc:art-1", NormativeState::InForce, 10, "act:a"))
        .expect("e1");
    timeline
        .append(event("cc:art-1", NormativeState::Suspended, 20, "act:b"))
        .expect("e2");
    timeline
        .append(event("cc:art-1", NormativeState::InForce, 30, "act:c"))
        .expect("e3");

    assert_eq!(
        resolve_force_status_at(&timeline, &cc("cc:art-1"), 15)
            .expect("r")
            .status,
        NormativeState::InForce
    );
    assert_eq!(
        resolve_force_status_at(&timeline, &cc("cc:art-1"), 25)
            .expect("r")
            .status,
        NormativeState::Suspended
    );
    assert_eq!(
        resolve_force_status_at(&timeline, &cc("cc:art-1"), 30)
            .expect("r")
            .status,
        NormativeState::InForce
    );
}

#[test]
fn future_events_do_not_apply() {
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(event("cc:art-1", NormativeState::Repealed, 50, "act:r"))
        .expect("e");
    let result = resolve_force_status_at(&timeline, &cc("cc:art-1"), 40).expect("r");
    assert_eq!(result.status, NormativeState::Unknown);
}

#[test]
fn conflict_same_day_distinct_status_is_unknown() {
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(event("cc:art-1", NormativeState::InForce, 10, "act:a"))
        .expect("e1");
    timeline
        .append(event("cc:art-1", NormativeState::Repealed, 10, "act:b"))
        .expect("e2");
    let result = resolve_force_status_at(&timeline, &cc("cc:art-1"), 10).expect("r");
    assert_eq!(result.status, NormativeState::Unknown);
    assert!(result.conflict);
}

#[test]
fn same_day_same_status_is_not_conflict() {
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(event("cc:art-1", NormativeState::Suspended, 10, "act:a"))
        .expect("e1");
    timeline
        .append(event("cc:art-1", NormativeState::Suspended, 10, "act:b"))
        .expect("e2");
    let result = resolve_force_status_at(&timeline, &cc("cc:art-1"), 10).expect("r");
    assert_eq!(result.status, NormativeState::Suspended);
    assert!(!result.conflict);
}

#[test]
fn other_component_events_are_ignored() {
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(event("cc:art-2", NormativeState::InForce, 1, "act:x"))
        .expect("e");
    let result = resolve_force_status_at(&timeline, &cc("cc:art-1"), 10).expect("r");
    assert_eq!(result.status, NormativeState::Unknown);
}

#[test]
fn event_rejects_unknown_as_transition_status() {
    let err = ForceStatusEvent::try_new(cc("cc:art-1"), NormativeState::Unknown, 1, act("act:z"))
        .expect_err("unknown not a transition");
    assert!(matches!(err, NormativeStateError::UnknownNotTransition));
}

#[test]
fn event_requires_provenance() {
    let err = ForceStatusEvent::try_new(
        cc("cc:art-1"),
        NormativeState::InForce,
        1,
        AmendingActId::parse("act:x").expect("act"),
    );
    // empty provenance is rejected at parse; use empty string path via try with empty
    let empty = AmendingActId::parse("");
    assert!(empty.is_err());
    let _ = err; // valid event path still constructs
    let bad = ForceStatusEvent::try_new_raw("cc:art-1", NormativeState::InForce, 1, "");
    assert!(matches!(bad, Err(NormativeStateError::MissingProvenance)));
}

#[test]
fn force_resolution_does_not_claim_applicability_or_ctv() {
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(event("cc:art-1", NormativeState::InForce, 1, "act:a"))
        .expect("e");
    let result = resolve_force_status_at(&timeline, &cc("cc:art-1"), 2).expect("r");
    assert_eq!(result.status, NormativeState::InForce);
    assert!(result.non_claims.iter().any(|c| c.contains("Applicab")));
    assert!(result
        .non_claims
        .iter()
        .any(|c| c.contains("CTV") || c.contains("text")));
    assert_eq!(result.dimension.as_str(), "force_status");
}
