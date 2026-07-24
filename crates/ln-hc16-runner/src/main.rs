use std::env;
use std::process::ExitCode;

use ln_accelerate::adapters::{HostileLabelMutatorLedger, InMemoryAccelerationLedger};
use ln_accelerate::application::PublishProvisionalAcceleration;
use ln_accelerate::domain::{
    AccelerationOutcome, AccelerationRequest, LabelId, ProvisionalId, ProvisionalTier, ScopeId,
    WriterId, ACCELERATION_POLICY_VERSION,
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

fn render_verdict() -> String {
    let mut svc = PublishProvisionalAcceleration::new(InMemoryAccelerationLedger::new());
    let first = svc.accelerate(req("prov:1", "label:v1", ProvisionalTier::Accelerated));
    let mut direct = req("prov:2", "label:v2", ProvisionalTier::Normal);
    direct.direct_promotion_attempt = true;
    let direct_result = svc.accelerate(direct);
    let mut mutate = req("prov:3", "label:v3", ProvisionalTier::Normal);
    mutate.label_mutation_attempt = true;
    let mutate_result = svc.accelerate(mutate);
    let mut hostile = PublishProvisionalAcceleration::new(HostileLabelMutatorLedger::new());
    let hostile_result =
        hostile.accelerate(req("prov:4", "label:v4", ProvisionalTier::Accelerated));

    let pass = first.outcome == AccelerationOutcome::Accelerated
        && !first.authoritative
        && direct_result.outcome == AccelerationOutcome::DirectPromotionRejected
        && mutate_result.outcome == AccelerationOutcome::LabelMutationRejected
        && hostile_result.outcome == AccelerationOutcome::Accelerated
        && !hostile_result.authoritative;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc16-verdict/v1\",\"evidence_id\":\"S10-HC-16-RT\",\"case_id\":\"HC-16\",\"verdict\":\"{verdict}\",\"scenario_count\":5,\"normal_acceleration\":{},\"direct_promotion_rejected\":{},\"label_mutation_rejected\":{},\"hostile_no_authority\":{},\"provisional_never_authoritative\":{},\"remaining_unsupported_cases\":4,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false}}",
        first.outcome == AccelerationOutcome::Accelerated,
        direct_result.outcome == AccelerationOutcome::DirectPromotionRejected,
        mutate_result.outcome == AccelerationOutcome::LabelMutationRejected,
        !hostile_result.authoritative,
        !first.authoritative,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.as_slice() {
        [s] if s == "verdict" => {
            println!("{}", render_verdict());
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("hc16_runner_error:unknown_scenario");
            ExitCode::from(2)
        }
    }
}
