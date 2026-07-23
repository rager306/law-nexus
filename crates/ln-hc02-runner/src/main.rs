use std::env;
use std::process::ExitCode;

use ln_inventory::adapters::{InMemoryInventoryStore, InMemoryVisibilityView};
use ln_inventory::application::InventoryImmutableIntake;
use ln_inventory::domain::{
    DropReference, InventoryDisposition, InventoryRequest, InventoryRequestId, InventoryResult,
    InventoryVisibility,
};

const RAW_CANARY: &[u8] = b"SYNTHETIC-IMMUTABLE-DROP-D1";

fn disposition_name(value: InventoryDisposition) -> &'static str {
    match value {
        InventoryDisposition::Pending => "pending",
        InventoryDisposition::ReviewRequired => "review-required",
        InventoryDisposition::IntegrityFailed => "integrity-failed",
        InventoryDisposition::MetadataMismatch => "metadata-mismatch",
        InventoryDisposition::AmbiguousIdentity => "ambiguous-identity",
    }
}

fn visibility_name(value: InventoryVisibility) -> &'static str {
    match value {
        InventoryVisibility::InventoryReview => "inventory-review",
    }
}

fn render_receipt(result: &InventoryResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc02-receipt/v1\",\"case_id\":\"HC-02\",\"item_id\":\"{}\",\"input_digest\":\"{}\",\"attempt_count\":{},\"disposition\":\"{}\",\"visibility\":\"{}\",\"curated_label_absent\":{},\"current_label_absent\":{},\"promotion_id_absent\":{},\"publication_id_absent\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false}}",
        result.item_id.as_str(),
        result.input_digest,
        result.observation_attempts.len(),
        disposition_name(result.disposition),
        visibility_name(result.visibility),
        result.curated_label.is_none(),
        result.current_label.is_none(),
        result.promotion_id.is_none(),
        result.publication_id.is_none(),
    )
}

fn run_inventory_once(request_id: &str) -> InventoryResult {
    let mut use_case =
        InventoryImmutableIntake::new(InMemoryInventoryStore::default(), InMemoryVisibilityView);
    use_case.inventory(InventoryRequest::new(
        InventoryRequestId::parse(request_id).expect("static request id is valid"),
        DropReference::parse("D1").expect("static drop id is valid"),
        RAW_CANARY,
    ))
}

fn run_re_inventory_pair() -> (InventoryResult, InventoryResult) {
    let mut use_case =
        InventoryImmutableIntake::new(InMemoryInventoryStore::default(), InMemoryVisibilityView);
    let request = InventoryRequest::new(
        InventoryRequestId::parse("INV-1").expect("static request id is valid"),
        DropReference::parse("D1").expect("static drop id is valid"),
        RAW_CANARY,
    );
    let first = use_case.inventory(request.clone());
    let second = use_case.inventory(request);
    (first, second)
}

fn run_re_inventory() -> InventoryResult {
    run_re_inventory_pair().1
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct VerdictChecks {
    stable_digest: bool,
    append_only_attempts: bool,
    staging_visibility_only: bool,
    authority_absent: bool,
    raw_canary_absent: bool,
}

impl VerdictChecks {
    fn pass(self) -> bool {
        self.stable_digest
            && self.append_only_attempts
            && self.staging_visibility_only
            && self.authority_absent
            && self.raw_canary_absent
    }
}

fn evaluate_pair(first: &InventoryResult, second: &InventoryResult) -> VerdictChecks {
    VerdictChecks {
        stable_digest: first.input_digest == second.input_digest
            && first.item_id == second.item_id
            && first.observation_attempts.len() == 1
            && second.observation_attempts.len() == 2,
        append_only_attempts: second.observation_attempts.len() == 2
            && second.observation_attempts[0].attempt_id.as_str() == "attempt:1"
            && second.observation_attempts[1].attempt_id.as_str() == "attempt:2"
            && second.observation_attempts[0].input_digest == second.input_digest
            && second.observation_attempts[1].input_digest == second.input_digest,
        staging_visibility_only: first.visibility == InventoryVisibility::InventoryReview
            && second.visibility == InventoryVisibility::InventoryReview
            && first.disposition == InventoryDisposition::Pending
            && second.disposition == InventoryDisposition::Pending,
        authority_absent: first.curated_label.is_none()
            && second.curated_label.is_none()
            && first.current_label.is_none()
            && second.current_label.is_none()
            && first.promotion_id.is_none()
            && second.promotion_id.is_none()
            && first.publication_id.is_none()
            && second.publication_id.is_none(),
        raw_canary_absent: !format!("{first:?}").contains("SYNTHETIC-IMMUTABLE-DROP")
            && !format!("{second:?}").contains("SYNTHETIC-IMMUTABLE-DROP")
            && !render_receipt(first).contains("SYNTHETIC-IMMUTABLE-DROP")
            && !render_receipt(second).contains("SYNTHETIC-IMMUTABLE-DROP"),
    }
}

fn render_verdict() -> String {
    let (first, second) = run_re_inventory_pair();
    let checks = evaluate_pair(&first, &second);
    let verdict = if checks.pass() { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc02-verdict/v1\",\"evidence_id\":\"S10-HC-02-RT\",\"case_id\":\"HC-02\",\"verdict\":\"{verdict}\",\"scenario_count\":2,\"stable_digest\":{},\"append_only_attempts\":{},\"staging_visibility_only\":{},\"authority_absent\":{},\"raw_canary_absent\":{},\"remaining_unsupported_cases\":18,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false}}",
        checks.stable_digest,
        checks.append_only_attempts,
        checks.staging_visibility_only,
        checks.authority_absent,
        checks.raw_canary_absent,
    )
}

fn main() -> ExitCode {
    let args = env::args().skip(1).collect::<Vec<_>>();
    let [scenario] = args.as_slice() else {
        eprintln!("hc02_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "inventory" => run_inventory_once("INV-1"),
        "re-inventory" => run_re_inventory(),
        _ => {
            eprintln!("hc02_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(&result));
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mismatched_digest_pair_cannot_pass() {
        let first = run_inventory_once("INV-1");
        let mut second = first.clone();
        second.input_digest = "fnv1a64:deadbeefdeadbeef".to_owned();
        let checks = evaluate_pair(&first, &second);
        assert!(!checks.stable_digest);
        assert!(!checks.pass());
    }
}
