use std::env;
use std::process::ExitCode;

use ln_gate::adapters::InMemoryCandidateStore;
use ln_gate::application::GateLifecycle;
use ln_gate::domain::{
    CandidateId, EvidenceRef, GateOutcome, GateReason, GateRequest, LifecycleType, C10_GATE_VERSION,
};

struct ScenarioResult {
    outcome: GateOutcome,
    reason: GateReason,
    original_type: LifecycleType,
    resulting_type: LifecycleType,
    same_identity: bool,
    predecessor_present: bool,
    confidence_used_as_authority: bool,
    gate_version_ok: bool,
    digest_present: bool,
    pass: bool,
}

fn seed_gate() -> (GateLifecycle<InMemoryCandidateStore>, CandidateId) {
    let mut gate = GateLifecycle::new(InMemoryCandidateStore::default());
    let id = CandidateId::parse("C1").expect("static id");
    gate.seed_extracted(id.clone(), Vec::new());
    (gate, id)
}

fn run_confidence_only_reject() -> ScenarioResult {
    let (mut gate, id) = seed_gate();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 99,
        evidence_refs: Vec::new(),
        in_place: false,
    });
    let pass = result.outcome == GateOutcome::InsufficientEvidence
        && result.reason == GateReason::ConfidenceOnly
        && result.original_type == LifecycleType::ExtractedCandidate
        && result.resulting_type == LifecycleType::ExtractedCandidate
        && result.resulting_id == id
        && result.confidence_used_as_authority
        && result.gate_version.as_str() == C10_GATE_VERSION
        && result.input_chain_digest.as_str().starts_with("fnv1a64:");
    ScenarioResult {
        outcome: result.outcome,
        reason: result.reason,
        original_type: result.original_type,
        resulting_type: result.resulting_type,
        same_identity: result.resulting_id == id,
        predecessor_present: result.predecessor.is_some(),
        confidence_used_as_authority: result.confidence_used_as_authority,
        gate_version_ok: result.gate_version.as_str() == C10_GATE_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        pass,
    }
}

fn run_in_place_reject() -> ScenarioResult {
    let (mut gate, id) = seed_gate();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 10,
        evidence_refs: vec![EvidenceRef::parse("E1").expect("static id")],
        in_place: true,
    });
    let pass = result.outcome == GateOutcome::InvalidTransition
        && result.reason == GateReason::InPlaceMutation
        && result.original_type == LifecycleType::ExtractedCandidate
        && result.resulting_type == LifecycleType::ExtractedCandidate
        && result.resulting_id == id
        && !result.confidence_used_as_authority
        && result.gate_version.as_str() == C10_GATE_VERSION;
    ScenarioResult {
        outcome: result.outcome,
        reason: result.reason,
        original_type: result.original_type,
        resulting_type: result.resulting_type,
        same_identity: result.resulting_id == id,
        predecessor_present: result.predecessor.is_some(),
        confidence_used_as_authority: result.confidence_used_as_authority,
        gate_version_ok: result.gate_version.as_str() == C10_GATE_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        pass,
    }
}

fn run_accepted_new_outcome() -> ScenarioResult {
    let (mut gate, id) = seed_gate();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 10,
        evidence_refs: vec![
            EvidenceRef::parse("E1").expect("static id"),
            EvidenceRef::parse("E2").expect("static id"),
        ],
        in_place: false,
    });
    let original = gate.get(&id).expect("original remains");
    let pass = result.outcome == GateOutcome::AcceptedNewOutcome
        && result.reason == GateReason::EvidenceChainSatisfied
        && result.resulting_id != id
        && result.resulting_type == LifecycleType::VerifiedAssertion
        && result.predecessor.as_ref() == Some(&id)
        && original.lifecycle_type == LifecycleType::ExtractedCandidate
        && !result.confidence_used_as_authority
        && result.gate_version.as_str() == C10_GATE_VERSION
        && result.input_chain_digest.as_str().starts_with("fnv1a64:");
    ScenarioResult {
        outcome: result.outcome,
        reason: result.reason,
        original_type: result.original_type,
        resulting_type: result.resulting_type,
        same_identity: result.resulting_id == id,
        predecessor_present: result.predecessor.is_some(),
        confidence_used_as_authority: result.confidence_used_as_authority,
        gate_version_ok: result.gate_version.as_str() == C10_GATE_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        pass,
    }
}

fn outcome_name(outcome: GateOutcome) -> &'static str {
    outcome.as_str()
}

fn reason_name(reason: GateReason) -> &'static str {
    reason.as_str()
}

fn type_name(lifecycle_type: LifecycleType) -> &'static str {
    lifecycle_type.as_str()
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc06-receipt/v1\",\"case_id\":\"HC-06\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"reason\":\"{}\",\"original_type\":\"{}\",\"resulting_type\":\"{}\",\"same_identity\":{},\"predecessor_present\":{},\"confidence_used_as_authority\":{},\"gate_version_ok\":{},\"digest_present\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"confidence_threshold_selected\":false}}",
        scenario,
        outcome_name(result.outcome),
        reason_name(result.reason),
        type_name(result.original_type),
        type_name(result.resulting_type),
        result.same_identity,
        result.predecessor_present,
        result.confidence_used_as_authority,
        result.gate_version_ok,
        result.digest_present,
        result.pass,
    )
}

fn render_verdict() -> String {
    let confidence = run_confidence_only_reject();
    let in_place = run_in_place_reject();
    let accepted = run_accepted_new_outcome();
    let pass = confidence.pass && in_place.pass && accepted.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc06-verdict/v1\",\"evidence_id\":\"S10-HC-06-RT\",\"case_id\":\"HC-06\",\"verdict\":\"{verdict}\",\"scenario_count\":3,\"confidence_only_reject\":{},\"in_place_reject\":{},\"accepted_new_outcome\":{},\"original_type_preserved\":{},\"gate_version_ok\":{},\"remaining_unsupported_cases\":14,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"confidence_threshold_selected\":false}}",
        confidence.pass,
        in_place.pass,
        accepted.pass,
        confidence.pass && in_place.pass && accepted.pass,
        confidence.gate_version_ok && in_place.gate_version_ok && accepted.gate_version_ok,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc06_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "confidence-only-reject" => run_confidence_only_reject(),
        "in-place-reject" => run_in_place_reject(),
        "accepted-new-outcome" => run_accepted_new_outcome(),
        _ => {
            eprintln!("hc06_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
