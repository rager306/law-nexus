use ln_admission::adapters::HostileVendorCapacity;
use ln_admission::application::DecideAdmission;
use ln_admission::domain::{
    AdmissionDecision, AdmissionReason, AdmissionRequest, BoundId, CapacityState,
    ForbiddenInference, RequestId, WorkClassId,
};

fn req(retry: u32) -> AdmissionRequest {
    AdmissionRequest {
        request_id: RequestId::parse("req:hostile").expect("id"),
        work_class: WorkClassId::parse("work:class1").expect("id"),
        retry_count: retry,
        forbidden_inference: ForbiddenInference::None,
    }
}

#[test]
fn hostile_vendor_unknown_cannot_force_admit() {
    let svc = DecideAdmission::new(HostileVendorCapacity {
        pretend_measured: false,
        bound_id: None,
    });
    let result = svc.decide(req(0));
    assert_eq!(result.decision, AdmissionDecision::Rejected);
    assert_eq!(result.reason, AdmissionReason::VendorCapacityRejected);
    assert_eq!(result.capacity, CapacityState::Unknown);
    assert!(!result.vendor_number_used);
    assert!(result.bound_id.is_none());
}

#[test]
fn hostile_pretend_measured_with_vendor_numbers_still_rejects() {
    let svc = DecideAdmission::new(HostileVendorCapacity {
        pretend_measured: true,
        bound_id: Some(BoundId::parse("bound:fake").expect("id")),
    });
    let result = svc.decide(req(0));
    assert_eq!(result.decision, AdmissionDecision::Rejected);
    assert_eq!(result.reason, AdmissionReason::VendorCapacityRejected);
    assert_eq!(result.capacity, CapacityState::Unknown);
    assert!(!result.vendor_number_used);
    // Vendor provenance wins over pretended measured bound.
    assert!(result.bound_id.is_none());
}

#[test]
fn hostile_vendor_inferences_are_rejected() {
    let svc = DecideAdmission::new(HostileVendorCapacity {
        pretend_measured: true,
        bound_id: Some(BoundId::parse("bound:fake").expect("id")),
    });
    for inference in [
        ForbiddenInference::VendorThroughput,
        ForbiddenInference::VendorLatency,
        ForbiddenInference::VendorStoragePrecision,
        ForbiddenInference::LegalDelay,
        ForbiddenInference::Completeness,
    ] {
        let mut request = req(0);
        request.forbidden_inference = inference;
        let result = svc.decide(request);
        assert_eq!(
            result.decision,
            AdmissionDecision::Rejected,
            "{inference:?}"
        );
        assert!(!result.vendor_number_used);
        assert!(!result.legal_delay_inferred);
        assert!(!result.completeness_inferred);
        assert_eq!(result.capacity, CapacityState::Unknown);
    }
}

#[test]
fn hostile_retry_amplification_still_rejects_first() {
    let svc = DecideAdmission::new(HostileVendorCapacity {
        pretend_measured: true,
        bound_id: Some(BoundId::parse("bound:fake").expect("id")),
    });
    let result = svc.decide(req(3));
    assert_eq!(result.decision, AdmissionDecision::Rejected);
    assert_eq!(result.reason, AdmissionReason::RetryAmplification);
    assert!(!result.vendor_number_used);
    assert_eq!(result.capacity, CapacityState::Unknown);
}
