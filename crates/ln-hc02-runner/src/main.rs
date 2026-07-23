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

fn run_re_inventory() -> InventoryResult {
    let mut use_case =
        InventoryImmutableIntake::new(InMemoryInventoryStore::default(), InMemoryVisibilityView);
    let request = InventoryRequest::new(
        InventoryRequestId::parse("INV-1").expect("static request id is valid"),
        DropReference::parse("D1").expect("static drop id is valid"),
        RAW_CANARY,
    );
    let _first = use_case.inventory(request.clone());
    use_case.inventory(request)
}

fn main() -> ExitCode {
    let args = env::args().skip(1).collect::<Vec<_>>();
    let [scenario] = args.as_slice() else {
        eprintln!("hc02_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

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
