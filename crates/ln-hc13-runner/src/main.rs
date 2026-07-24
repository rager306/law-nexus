use std::env;
use std::process::ExitCode;

use ln_admission::adapters::{HonestBoundObservation, HostileVendorCapacity};
use ln_admission::application::DecideAdmission;
use ln_admission::domain::{
    AdmissionDecision, AdmissionReason, AdmissionRequest, BoundId, CapacityState,
    ForbiddenInference, RequestId, WorkClassId, ADMISSION_POLICY_VERSION,
    RETRY_AMPLIFICATION_THRESHOLD,
};

struct ScenarioResult {
    decision: AdmissionDecision,
    reason: AdmissionReason,
    capacity_unknown: bool,
    vendor_number_used: bool,
    legal_delay_inferred: bool,
    completeness_inferred: bool,
    policy_version_ok: bool,
    pass: bool,
}

fn req(id: &str, retry: u32, inference: ForbiddenInference) -> AdmissionRequest {
    AdmissionRequest {
        request_id: RequestId::parse(id).expect("static id"),
        work_class: WorkClassId::parse("work:class1").expect("static id"),
        retry_count: retry,
        forbidden_inference: inference,
    }
}

fn run_bound_unknown_pauses() -> ScenarioResult {
    let svc = DecideAdmission::new(HonestBoundObservation::unknown());
    let result = svc.decide(req("req:unknown", 0, ForbiddenInference::None));
    let pass = result.decision == AdmissionDecision::Paused
        && result.reason == AdmissionReason::BoundUnknown
        && result.capacity == CapacityState::Unknown
        && !result.vendor_number_used
        && !result.legal_delay_inferred
        && !result.completeness_inferred
        && result.trace.policy_version == ADMISSION_POLICY_VERSION;
    ScenarioResult {
        decision: result.decision,
        reason: result.reason,
        capacity_unknown: result.capacity.is_unknown(),
        vendor_number_used: result.vendor_number_used,
        legal_delay_inferred: result.legal_delay_inferred,
        completeness_inferred: result.completeness_inferred,
        policy_version_ok: result.trace.policy_version == ADMISSION_POLICY_VERSION,
        pass,
    }
}

fn run_saturated_rejects() -> ScenarioResult {
    let svc = DecideAdmission::new(HonestBoundObservation::saturated());
    let result = svc.decide(req("req:sat", 0, ForbiddenInference::None));
    let pass = result.decision == AdmissionDecision::Rejected
        && result.reason == AdmissionReason::Saturated
        && result.capacity == CapacityState::Unknown
        && !result.vendor_number_used;
    ScenarioResult {
        decision: result.decision,
        reason: result.reason,
        capacity_unknown: result.capacity.is_unknown(),
        vendor_number_used: result.vendor_number_used,
        legal_delay_inferred: result.legal_delay_inferred,
        completeness_inferred: result.completeness_inferred,
        policy_version_ok: result.trace.policy_version == ADMISSION_POLICY_VERSION,
        pass,
    }
}

fn run_retry_amplification_rejects() -> ScenarioResult {
    let svc = DecideAdmission::new(HonestBoundObservation::measured(
        BoundId::parse("bound:local1").expect("static id"),
    ));
    let result = svc.decide(req(
        "req:retry",
        RETRY_AMPLIFICATION_THRESHOLD,
        ForbiddenInference::None,
    ));
    let pass = result.decision == AdmissionDecision::Rejected
        && result.reason == AdmissionReason::RetryAmplification
        && result.capacity == CapacityState::Unknown
        && !result.vendor_number_used;
    ScenarioResult {
        decision: result.decision,
        reason: result.reason,
        capacity_unknown: result.capacity.is_unknown(),
        vendor_number_used: result.vendor_number_used,
        legal_delay_inferred: result.legal_delay_inferred,
        completeness_inferred: result.completeness_inferred,
        policy_version_ok: result.trace.policy_version == ADMISSION_POLICY_VERSION,
        pass,
    }
}

fn run_measured_bound_admits() -> ScenarioResult {
    let svc = DecideAdmission::new(HonestBoundObservation::measured(
        BoundId::parse("bound:local1").expect("static id"),
    ));
    let result = svc.decide(req("req:ok", 0, ForbiddenInference::None));
    let pass = result.decision == AdmissionDecision::Admitted
        && result.reason == AdmissionReason::MeasuredBound
        && result.capacity == CapacityState::BoundedLocal
        && result.bound_id.as_ref().map(|b| b.as_str()) == Some("bound:local1")
        && !result.vendor_number_used
        && !result.legal_delay_inferred
        && !result.completeness_inferred;
    ScenarioResult {
        decision: result.decision,
        reason: result.reason,
        capacity_unknown: result.capacity.is_unknown(),
        vendor_number_used: result.vendor_number_used,
        legal_delay_inferred: result.legal_delay_inferred,
        completeness_inferred: result.completeness_inferred,
        policy_version_ok: result.trace.policy_version == ADMISSION_POLICY_VERSION,
        pass,
    }
}

fn run_hostile_vendor_rejects() -> ScenarioResult {
    let svc = DecideAdmission::new(HostileVendorCapacity {
        pretend_measured: true,
        bound_id: Some(BoundId::parse("bound:fake").expect("static id")),
    });
    let result = svc.decide(req("req:vendor", 0, ForbiddenInference::None));
    let pass = result.decision == AdmissionDecision::Rejected
        && result.reason == AdmissionReason::VendorCapacityRejected
        && result.capacity == CapacityState::Unknown
        && !result.vendor_number_used
        && result.bound_id.is_none();
    ScenarioResult {
        decision: result.decision,
        reason: result.reason,
        capacity_unknown: result.capacity.is_unknown(),
        vendor_number_used: result.vendor_number_used,
        legal_delay_inferred: result.legal_delay_inferred,
        completeness_inferred: result.completeness_inferred,
        policy_version_ok: result.trace.policy_version == ADMISSION_POLICY_VERSION,
        pass,
    }
}

fn run_forbidden_inference_matrix() -> ScenarioResult {
    let svc = DecideAdmission::new(HonestBoundObservation::measured(
        BoundId::parse("bound:local1").expect("static id"),
    ));
    let mut all_pass = true;
    for inference in [
        ForbiddenInference::LegalDelay,
        ForbiddenInference::Completeness,
        ForbiddenInference::VendorThroughput,
        ForbiddenInference::VendorLatency,
        ForbiddenInference::VendorStoragePrecision,
    ] {
        let result = svc.decide(req("req:infer", 0, inference));
        all_pass &= result.decision == AdmissionDecision::Rejected
            && result.capacity == CapacityState::Unknown
            && !result.vendor_number_used
            && !result.legal_delay_inferred
            && !result.completeness_inferred;
    }
    ScenarioResult {
        decision: if all_pass {
            AdmissionDecision::Rejected
        } else {
            AdmissionDecision::Admitted
        },
        reason: AdmissionReason::CompletenessClaimRejected,
        capacity_unknown: all_pass,
        vendor_number_used: false,
        legal_delay_inferred: false,
        completeness_inferred: false,
        policy_version_ok: true,
        pass: all_pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc13-receipt/v1\",\"case_id\":\"HC-13\",\"scenario\":\"{}\",\"decision\":\"{}\",\"reason\":\"{}\",\"capacity_unknown\":{},\"vendor_number_used\":{},\"legal_delay_inferred\":{},\"completeness_inferred\":{},\"policy_version_ok\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"queue_selected\":false,\"hardware_selected\":false,\"throughput_selected\":false}}",
        scenario,
        result.decision.as_str(),
        result.reason.as_str(),
        result.capacity_unknown,
        result.vendor_number_used,
        result.legal_delay_inferred,
        result.completeness_inferred,
        result.policy_version_ok,
        result.pass,
    )
}

fn render_verdict() -> String {
    let unknown = run_bound_unknown_pauses();
    let saturated = run_saturated_rejects();
    let retry = run_retry_amplification_rejects();
    let measured = run_measured_bound_admits();
    let vendor = run_hostile_vendor_rejects();
    let inferences = run_forbidden_inference_matrix();
    let pass = unknown.pass
        && saturated.pass
        && retry.pass
        && measured.pass
        && vendor.pass
        && inferences.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc13-verdict/v1\",\"evidence_id\":\"S10-HC-13-RT\",\"case_id\":\"HC-13\",\"verdict\":\"{verdict}\",\"scenario_count\":6,\"bound_unknown_pauses\":{},\"saturated_rejects\":{},\"retry_amplification_rejects\":{},\"measured_bound_admits\":{},\"hostile_vendor_rejects\":{},\"forbidden_inference_matrix\":{},\"vendor_number_never_used\":{},\"capacity_unknown_on_reject\":{},\"remaining_unsupported_cases\":7,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"queue_selected\":false,\"hardware_selected\":false,\"throughput_selected\":false}}",
        unknown.pass,
        saturated.pass,
        retry.pass,
        measured.pass,
        vendor.pass,
        inferences.pass,
        !unknown.vendor_number_used
            && !saturated.vendor_number_used
            && !retry.vendor_number_used
            && !measured.vendor_number_used
            && !vendor.vendor_number_used
            && !inferences.vendor_number_used,
        unknown.capacity_unknown
            && saturated.capacity_unknown
            && retry.capacity_unknown
            && vendor.capacity_unknown
            && inferences.capacity_unknown,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc13_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "bound-unknown-pauses" => run_bound_unknown_pauses(),
        "saturated-rejects" => run_saturated_rejects(),
        "retry-amplification-rejects" => run_retry_amplification_rejects(),
        "measured-bound-admits" => run_measured_bound_admits(),
        "hostile-vendor-rejects" => run_hostile_vendor_rejects(),
        "forbidden-inference-matrix" => run_forbidden_inference_matrix(),
        _ => {
            eprintln!("hc13_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
