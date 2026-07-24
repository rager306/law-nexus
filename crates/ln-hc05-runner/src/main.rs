use std::env;
use std::process::ExitCode;

use ln_decode::adapters::{
    HonestSyntheticDecoder, InMemoryDiagnosticSink, MaliciousSyntheticDecoder,
};
use ln_decode::application::DecodeAndAnchor;
use ln_decode::domain::{DecodeRequest, FamilyFormat, PayloadRef};

const CANARY: &[u8] = b"CANARY::SYNTHETIC-LEGAL-TEXT-DO-NOT-LEAK";

struct ScenarioResult {
    candidate_count: usize,
    rejected_count: usize,
    verified_assertion_absent: bool,
    merged_identity_absent: bool,
    unregistered_relation_absent: bool,
    raw_payload_absent: bool,
    positive_control_present: bool,
    pass: bool,
}

fn request(label: &str) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse(&format!("payload:{label}")).expect("static id"),
        FamilyFormat::parse("family:synthetic").expect("static id"),
        CANARY,
    )
}

fn run_honest_structural_only() -> ScenarioResult {
    let mut use_case =
        DecodeAndAnchor::new(HonestSyntheticDecoder, InMemoryDiagnosticSink::default());
    let result = use_case.execute(request("honest"));
    let positive = result
        .diagnostics
        .iter()
        .any(|d| d.positive_control && d.category == "decode-positive-control");
    let pass = result.candidate_count_ok()
        && result.rejected_categories.is_empty()
        && result.verified_assertion_absent
        && result.merged_identity_absent
        && result.unregistered_relation_absent
        && result.raw_payload_absent
        && positive;
    ScenarioResult {
        candidate_count: result.candidates.len(),
        rejected_count: result.rejected_categories.len(),
        verified_assertion_absent: result.verified_assertion_absent,
        merged_identity_absent: result.merged_identity_absent,
        unregistered_relation_absent: result.unregistered_relation_absent,
        raw_payload_absent: result.raw_payload_absent,
        positive_control_present: positive,
        pass,
    }
}

trait CandidateCountOk {
    fn candidate_count_ok(&self) -> bool;
}

impl CandidateCountOk for ln_decode::domain::DecodeResult {
    fn candidate_count_ok(&self) -> bool {
        self.candidates.len() == 1
            && self.candidates[0].category == ln_decode::domain::DecodeCategory::StructuralCandidate
            && self.candidates[0].anchor.end_offset > self.candidates[0].anchor.start_offset
    }
}

fn run_malicious_reject_all() -> ScenarioResult {
    let mut use_case =
        DecodeAndAnchor::new(MaliciousSyntheticDecoder, InMemoryDiagnosticSink::default());
    let result = use_case.execute(request("malicious"));
    let positive = result
        .diagnostics
        .iter()
        .any(|d| d.positive_control && d.category == "decode-positive-control");
    let pass = result.candidates.is_empty()
        && result.rejected_categories.len() >= 4
        && result.verified_assertion_absent
        && result.merged_identity_absent
        && result.unregistered_relation_absent
        && result.raw_payload_absent
        && positive;
    ScenarioResult {
        candidate_count: result.candidates.len(),
        rejected_count: result.rejected_categories.len(),
        verified_assertion_absent: result.verified_assertion_absent,
        merged_identity_absent: result.merged_identity_absent,
        unregistered_relation_absent: result.unregistered_relation_absent,
        raw_payload_absent: result.raw_payload_absent,
        positive_control_present: positive,
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc05-receipt/v1\",\"case_id\":\"HC-05\",\"scenario\":\"{}\",\"candidate_count\":{},\"rejected_count\":{},\"verified_assertion_absent\":{},\"merged_identity_absent\":{},\"unregistered_relation_absent\":{},\"raw_payload_absent\":{},\"positive_control_present\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"parser_format_selected\":false}}",
        scenario,
        result.candidate_count,
        result.rejected_count,
        result.verified_assertion_absent,
        result.merged_identity_absent,
        result.unregistered_relation_absent,
        result.raw_payload_absent,
        result.positive_control_present,
        result.pass,
    )
}

fn render_verdict() -> String {
    let honest = run_honest_structural_only();
    let malicious = run_malicious_reject_all();
    let pass = honest.pass && malicious.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc05-verdict/v1\",\"evidence_id\":\"S10-HC-05-RT\",\"case_id\":\"HC-05\",\"verdict\":\"{verdict}\",\"scenario_count\":2,\"honest_structural_only\":{},\"malicious_reject_all\":{},\"gate_owned_claims_absent\":{},\"raw_payload_absent\":{},\"positive_control_present\":{},\"remaining_unsupported_cases\":15,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"parser_format_selected\":false}}",
        honest.pass,
        malicious.pass,
        honest.verified_assertion_absent
            && honest.merged_identity_absent
            && honest.unregistered_relation_absent
            && malicious.verified_assertion_absent
            && malicious.merged_identity_absent
            && malicious.unregistered_relation_absent,
        honest.raw_payload_absent && malicious.raw_payload_absent,
        honest.positive_control_present && malicious.positive_control_present,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc05_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "honest-structural-only" => run_honest_structural_only(),
        "malicious-reject-all" => run_malicious_reject_all(),
        _ => {
            eprintln!("hc05_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
