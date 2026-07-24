use std::env;
use std::process::ExitCode;

use ln_identity::adapters::InMemoryIdentityStore;
use ln_identity::application::AssertIdentity;
use ln_identity::domain::{
    AssertRequest, ContributionId, EvidenceContribution, EvidenceSide, FamilyId, IdentityId,
    IdentityOutcome, IdentityReason, C12_GATE_VERSION,
};

struct ScenarioResult {
    outcome: IdentityOutcome,
    reason: IdentityReason,
    left_survives: bool,
    right_survives: bool,
    merge_performed: bool,
    no_merge_observation: bool,
    c12_version_ok: bool,
    digest_present: bool,
    method_scope_visible: bool,
    pass: bool,
}

fn seeded() -> (
    AssertIdentity<InMemoryIdentityStore>,
    IdentityId,
    IdentityId,
) {
    let mut use_case = AssertIdentity::new(InMemoryIdentityStore::default());
    let left = IdentityId::parse("ID-A").expect("static id");
    let right = IdentityId::parse("ID-B").expect("static id");
    use_case.seed(left.clone(), "left");
    use_case.seed(right.clone(), "right");
    (use_case, left, right)
}

fn run_one_sided_reject() -> ScenarioResult {
    let (mut use_case, left, right) = seeded();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: vec![EvidenceContribution {
            contribution_id: ContributionId::parse("contrib:L").expect("static id"),
            family_id: FamilyId::parse("family:consultant").expect("static id"),
            side: EvidenceSide::Left,
            evidence_ceiling: "family-local".to_owned(),
        }],
        claim_same: true,
        similarity_score: Some(95),
        method: "one-sided-family-claim".to_owned(),
        scope: "cross-family".to_owned(),
    });
    let pass = result.outcome == IdentityOutcome::Candidate
        && result.reason == IdentityReason::OneSidedEvidence
        && result.left_survives
        && result.right_survives
        && !result.merge_performed
        && result.no_merge_observation
        && result.c12_version.as_str() == C12_GATE_VERSION
        && result.input_chain_digest.as_str().starts_with("fnv1a64:")
        && use_case.contains(&left)
        && use_case.contains(&right);
    ScenarioResult {
        outcome: result.outcome,
        reason: result.reason,
        left_survives: result.left_survives,
        right_survives: result.right_survives,
        merge_performed: result.merge_performed,
        no_merge_observation: result.no_merge_observation,
        c12_version_ok: result.c12_version.as_str() == C12_GATE_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        method_scope_visible: !result.method.is_empty() && !result.scope.is_empty(),
        pass,
    }
}

fn run_similarity_only_reject() -> ScenarioResult {
    let (mut use_case, left, right) = seeded();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: Vec::new(),
        claim_same: true,
        similarity_score: Some(99),
        method: "filename-number-similarity".to_owned(),
        scope: "global".to_owned(),
    });
    let pass = result.outcome == IdentityOutcome::Ambiguous
        && result.reason == IdentityReason::SimilarityOnly
        && result.left_survives
        && result.right_survives
        && !result.merge_performed
        && result.no_merge_observation
        && use_case.contains(&left)
        && use_case.contains(&right);
    ScenarioResult {
        outcome: result.outcome,
        reason: result.reason,
        left_survives: result.left_survives,
        right_survives: result.right_survives,
        merge_performed: result.merge_performed,
        no_merge_observation: result.no_merge_observation,
        c12_version_ok: result.c12_version.as_str() == C12_GATE_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        method_scope_visible: !result.method.is_empty() && !result.scope.is_empty(),
        pass,
    }
}

fn run_bilateral_same_no_merge() -> ScenarioResult {
    let (mut use_case, left, right) = seeded();
    let result = use_case.assert_pair(AssertRequest {
        left_id: left.clone(),
        right_id: right.clone(),
        contributions: vec![
            EvidenceContribution {
                contribution_id: ContributionId::parse("contrib:L").expect("static id"),
                family_id: FamilyId::parse("family:official").expect("static id"),
                side: EvidenceSide::Left,
                evidence_ceiling: "official-bilateral".to_owned(),
            },
            EvidenceContribution {
                contribution_id: ContributionId::parse("contrib:R").expect("static id"),
                family_id: FamilyId::parse("family:official").expect("static id"),
                side: EvidenceSide::Right,
                evidence_ceiling: "official-bilateral".to_owned(),
            },
        ],
        claim_same: true,
        similarity_score: Some(80),
        method: "bilateral-official".to_owned(),
        scope: "official-family".to_owned(),
    });
    let pass = result.outcome == IdentityOutcome::Same
        && result.reason == IdentityReason::BilateralSameEvidence
        && result.left_survives
        && result.right_survives
        && !result.merge_performed
        && result.no_merge_observation
        && result.contribution_ids.len() == 2
        && use_case.contains(&left)
        && use_case.contains(&right);
    ScenarioResult {
        outcome: result.outcome,
        reason: result.reason,
        left_survives: result.left_survives,
        right_survives: result.right_survives,
        merge_performed: result.merge_performed,
        no_merge_observation: result.no_merge_observation,
        c12_version_ok: result.c12_version.as_str() == C12_GATE_VERSION,
        digest_present: result.input_chain_digest.as_str().starts_with("fnv1a64:"),
        method_scope_visible: !result.method.is_empty() && !result.scope.is_empty(),
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc07-receipt/v1\",\"case_id\":\"HC-07\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"reason\":\"{}\",\"left_survives\":{},\"right_survives\":{},\"merge_performed\":{},\"no_merge_observation\":{},\"c12_version_ok\":{},\"digest_present\":{},\"method_scope_visible\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"similarity_model_selected\":false}}",
        scenario,
        result.outcome.as_str(),
        result.reason.as_str(),
        result.left_survives,
        result.right_survives,
        result.merge_performed,
        result.no_merge_observation,
        result.c12_version_ok,
        result.digest_present,
        result.method_scope_visible,
        result.pass,
    )
}

fn render_verdict() -> String {
    let one_sided = run_one_sided_reject();
    let similarity = run_similarity_only_reject();
    let bilateral = run_bilateral_same_no_merge();
    let pass = one_sided.pass && similarity.pass && bilateral.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc07-verdict/v1\",\"evidence_id\":\"S10-HC-07-RT\",\"case_id\":\"HC-07\",\"verdict\":\"{verdict}\",\"scenario_count\":3,\"one_sided_reject\":{},\"similarity_only_reject\":{},\"bilateral_same_no_merge\":{},\"both_identities_survive\":{},\"no_merge_observation\":{},\"remaining_unsupported_cases\":13,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"similarity_model_selected\":false}}",
        one_sided.pass,
        similarity.pass,
        bilateral.pass,
        one_sided.left_survives
            && one_sided.right_survives
            && similarity.left_survives
            && similarity.right_survives
            && bilateral.left_survives
            && bilateral.right_survives,
        one_sided.no_merge_observation
            && similarity.no_merge_observation
            && bilateral.no_merge_observation,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc07_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "one-sided-reject" => run_one_sided_reject(),
        "similarity-only-reject" => run_similarity_only_reject(),
        "bilateral-same-no-merge" => run_bilateral_same_no_merge(),
        _ => {
            eprintln!("hc07_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
