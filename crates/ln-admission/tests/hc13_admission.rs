use ln_admission::adapters::HonestBoundObservation;
use ln_admission::application::DecideAdmission;
use ln_admission::domain::{
    AdmissionDecision, AdmissionReason, AdmissionRequest, BoundId, CapacityState,
    ForbiddenInference, RequestId, WorkClassId, ADMISSION_POLICY_VERSION,
    RETRY_AMPLIFICATION_THRESHOLD,
};

fn req(retry: u32) -> AdmissionRequest {
    AdmissionRequest {
        request_id: RequestId::parse("req:A1").expect("id"),
        work_class: WorkClassId::parse("work:class1").expect("id"),
        retry_count: retry,
        forbidden_inference: ForbiddenInference::None,
    }
}

#[test]
fn bound_unknown_pauses_with_capacity_unknown() {
    let svc = DecideAdmission::new(HonestBoundObservation::unknown());
    let result = svc.decide(req(0));
    assert_eq!(result.decision, AdmissionDecision::Paused);
    assert_eq!(result.reason, AdmissionReason::BoundUnknown);
    assert_eq!(result.capacity, CapacityState::Unknown);
    assert!(result.bound_id.is_none());
    assert!(!result.vendor_number_used);
    assert!(!result.legal_delay_inferred);
    assert!(!result.completeness_inferred);
    assert_eq!(result.trace.policy_version, ADMISSION_POLICY_VERSION);
}

#[test]
fn saturated_rejects_with_capacity_unknown() {
    let svc = DecideAdmission::new(HonestBoundObservation::saturated());
    let result = svc.decide(req(0));
    assert_eq!(result.decision, AdmissionDecision::Rejected);
    assert_eq!(result.reason, AdmissionReason::Saturated);
    assert_eq!(result.capacity, CapacityState::Unknown);
    assert!(!result.vendor_number_used);
}

#[test]
fn retry_amplification_rejects() {
    let svc = DecideAdmission::new(HonestBoundObservation::measured(
        BoundId::parse("bound:local1").expect("id"),
    ));
    let result = svc.decide(req(RETRY_AMPLIFICATION_THRESHOLD));
    assert_eq!(result.decision, AdmissionDecision::Rejected);
    assert_eq!(result.reason, AdmissionReason::RetryAmplification);
    assert_eq!(result.capacity, CapacityState::Unknown);
    assert!(result.bound_id.is_none());
}

#[test]
fn measured_local_bound_can_admit() {
    let svc = DecideAdmission::new(HonestBoundObservation::measured(
        BoundId::parse("bound:local1").expect("id"),
    ));
    let result = svc.decide(req(0));
    assert_eq!(result.decision, AdmissionDecision::Admitted);
    assert_eq!(result.reason, AdmissionReason::MeasuredBound);
    assert_eq!(result.capacity, CapacityState::BoundedLocal);
    assert_eq!(result.bound_id.as_ref().map(|b| b.as_str()), Some("bound:local1"));
    assert!(!result.vendor_number_used);
    assert!(!result.legal_delay_inferred);
    assert!(!result.completeness_inferred);
}

#[test]
fn legal_delay_and_completeness_claims_are_rejected() {
    let svc = DecideAdmission::new(HonestBoundObservation::measured(
        BoundId::parse("bound:local1").expect("id"),
    ));
    for inference in [ForbiddenInference::LegalDelay, ForbiddenInference::Completeness] {
        let mut request = req(0);
        request.forbidden_inference = inference;
        let result = svc.decide(request);
        assert_eq!(result.decision, AdmissionDecision::Rejected, "{inference:?}");
        assert!(!result.legal_delay_inferred);
        assert!(!result.completeness_inferred);
        assert_eq!(result.capacity, CapacityState::Unknown);
    }
}
