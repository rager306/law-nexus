use std::env;
use std::process::ExitCode;

use ln_dispose::adapters::{InMemoryDispositionStore, InMemoryPromotionGate};
use ln_dispose::application::DisposeReview;
use ln_dispose::domain::{
    DispositionReason, DispositionState, InventoryItemId, PromotionAttemptId, PromotionOutcome,
    PromotionRequestId, ReviewEvidenceId,
};

fn state_name(state: DispositionState) -> &'static str {
    match state {
        DispositionState::Pending => "pending",
        DispositionState::Quarantined => "quarantined",
        DispositionState::Accepted => "accepted",
        DispositionState::Rejected => "rejected",
    }
}

fn reason_name(reason: DispositionReason) -> &'static str {
    match reason {
        DispositionReason::Incomplete => "incomplete",
        DispositionReason::Conflict => "conflict",
        DispositionReason::Unauthorized => "unauthorized",
        DispositionReason::Accepted => "accepted",
        DispositionReason::RejectedReasonCoded => "rejected-reason-coded",
    }
}

fn outcome_name(outcome: PromotionOutcome) -> &'static str {
    match outcome {
        PromotionOutcome::Rejected => "rejected",
        PromotionOutcome::Committed => "committed",
    }
}

struct ScenarioResult {
    disposition_state: DispositionState,
    promotion_outcome: PromotionOutcome,
    promotion_reason: DispositionReason,
    commit_id_absent: bool,
    promotion_identity_absent: bool,
}

fn run_pending_rejects_promotion() -> ScenarioResult {
    let mut use_case =
        DisposeReview::new(InMemoryDispositionStore::default(), InMemoryPromotionGate);
    let item = InventoryItemId::parse("I1").expect("static item id is valid");
    use_case.set_pending(
        item.clone(),
        vec![ReviewEvidenceId::parse("E1").expect("valid")],
    );
    let promotion = use_case.attempt_promotion(
        item.clone(),
        PromotionRequestId::parse("P1").expect("valid"),
        PromotionAttemptId::parse("A1").expect("valid"),
    );
    ScenarioResult {
        disposition_state: use_case.disposition(&item).state,
        promotion_outcome: promotion.outcome,
        promotion_reason: promotion.reason,
        commit_id_absent: promotion.commit_id.is_none(),
        promotion_identity_absent: promotion.promotion_identity.is_none(),
    }
}

fn run_quarantined_rejects_promotion() -> ScenarioResult {
    let mut use_case =
        DisposeReview::new(InMemoryDispositionStore::default(), InMemoryPromotionGate);
    let item = InventoryItemId::parse("I2").expect("static item id is valid");
    use_case.set_quarantined(
        item.clone(),
        vec![ReviewEvidenceId::parse("E2").expect("valid")],
    );
    let promotion = use_case.attempt_promotion(
        item.clone(),
        PromotionRequestId::parse("P2").expect("valid"),
        PromotionAttemptId::parse("A2").expect("valid"),
    );
    ScenarioResult {
        disposition_state: use_case.disposition(&item).state,
        promotion_outcome: promotion.outcome,
        promotion_reason: promotion.reason,
        commit_id_absent: promotion.commit_id.is_none(),
        promotion_identity_absent: promotion.promotion_identity.is_none(),
    }
}

fn render_receipt(result: &ScenarioResult, disposition_label: &str) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc03-receipt/v1\",\"case_id\":\"HC-03\",\"disposition\":\"{}\",\"disposition_state\":\"{}\",\"promotion_outcome\":\"{}\",\"promotion_reason\":\"{}\",\"commit_id_absent\":{},\"promotion_identity_absent\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false}}",
        disposition_label,
        state_name(result.disposition_state),
        outcome_name(result.promotion_outcome),
        reason_name(result.promotion_reason),
        result.commit_id_absent,
        result.promotion_identity_absent,
    )
}

fn render_verdict() -> String {
    let pending = run_pending_rejects_promotion();
    let quarantined = run_quarantined_rejects_promotion();
    let pending_rejects = pending.promotion_outcome == PromotionOutcome::Rejected
        && pending.commit_id_absent
        && pending.promotion_identity_absent
        && pending.disposition_state == DispositionState::Pending;
    let quarantined_rejects = quarantined.promotion_outcome == PromotionOutcome::Rejected
        && quarantined.commit_id_absent
        && quarantined.promotion_identity_absent
        && quarantined.disposition_state == DispositionState::Quarantined;
    let pass = pending_rejects && quarantined_rejects;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc03-verdict/v1\",\"evidence_id\":\"S10-HC-03-RT\",\"case_id\":\"HC-03\",\"verdict\":\"{verdict}\",\"scenario_count\":2,\"pending_rejects_promotion\":{},\"quarantined_rejects_promotion\":{},\"no_curated_commit\":{},\"authority_absent\":{},\"remaining_unsupported_cases\":17,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false}}",
        pending_rejects,
        quarantined_rejects,
        pending.commit_id_absent && quarantined.commit_id_absent,
        pending.promotion_identity_absent && quarantined.promotion_identity_absent,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc03_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "pending-rejects" => run_pending_rejects_promotion(),
        "quarantined-rejects" => run_quarantined_rejects_promotion(),
        _ => {
            eprintln!("hc03_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(&result, scenario));
    ExitCode::SUCCESS
}
