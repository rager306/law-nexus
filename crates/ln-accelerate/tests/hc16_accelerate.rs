use ln_accelerate::adapters::{HostileLabelMutatorLedger, InMemoryAccelerationLedger};
use ln_accelerate::application::PublishProvisionalAcceleration;
use ln_accelerate::domain::{
    AccelerationOutcome, AccelerationRequest, LabelId, ProvisionalId, ProvisionalTier, ScopeId,
    WriterId,
};

fn req(id: &str, label: &str, tier: ProvisionalTier) -> AccelerationRequest {
    AccelerationRequest {
        provisional_id: ProvisionalId::parse(id).unwrap(),
        scope_id: ScopeId::parse("scope:S1").unwrap(),
        writer_id: WriterId::parse("writer:A").unwrap(),
        label: LabelId::parse(label).unwrap(),
        tier,
        direct_promotion_attempt: false,
        label_mutation_attempt: false,
    }
}

#[test]
fn normal_acceleration_is_provisional_non_authoritative() {
    let mut svc = PublishProvisionalAcceleration::new(InMemoryAccelerationLedger::new());
    let result = svc.accelerate(req("prov:1", "label:v1", ProvisionalTier::Accelerated));
    assert_eq!(result.outcome, AccelerationOutcome::Accelerated);
    assert!(!result.authoritative);
    assert_eq!(svc.authoritative_count(), 0);
    assert_eq!(svc.provisional_count(), 1);
}

#[test]
fn direct_promotion_rejected() {
    let mut svc = PublishProvisionalAcceleration::new(InMemoryAccelerationLedger::new());
    let mut r = req("prov:1", "label:v1", ProvisionalTier::Normal);
    r.direct_promotion_attempt = true;
    let result = svc.accelerate(r);
    assert_eq!(result.outcome, AccelerationOutcome::DirectPromotionRejected);
    assert!(!result.authoritative);
    assert_eq!(svc.provisional_count(), 0);
}

#[test]
fn label_mutation_rejected() {
    let mut svc = PublishProvisionalAcceleration::new(InMemoryAccelerationLedger::new());
    let mut r = req("prov:1", "label:v1", ProvisionalTier::Normal);
    r.label_mutation_attempt = true;
    let result = svc.accelerate(r);
    assert_eq!(result.outcome, AccelerationOutcome::LabelMutationRejected);
    assert!(!result.authoritative);
}

#[test]
fn hostile_label_mutator_cannot_grant_authority() {
    let mut svc = PublishProvisionalAcceleration::new(HostileLabelMutatorLedger::new());
    let result = svc.accelerate(req("prov:1", "label:v1", ProvisionalTier::Accelerated));
    assert_eq!(result.outcome, AccelerationOutcome::Accelerated);
    assert!(!result.authoritative);
    assert_eq!(svc.authoritative_count(), 0);
}

#[test]
fn app_owned_label_not_mutated_by_hostile_adapter() {
    let mut svc = PublishProvisionalAcceleration::new(HostileLabelMutatorLedger::new());
    svc.accelerate(req("prov:1", "label:v1", ProvisionalTier::Accelerated));
    let app_label = svc.label_for(&ProvisionalId::parse("prov:1").unwrap());
    assert_eq!(app_label.as_deref(), Some("label:v1"));
}
