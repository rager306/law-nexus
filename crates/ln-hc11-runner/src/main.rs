use std::env;
use std::process::ExitCode;

use ln_closure::adapters::{FixedDependencyEvidence, HostileProgressCompleteness};
use ln_closure::application::ComputeDependencyClosure;
use ln_closure::domain::{
    ClosureRequest, ClosureStatus, CompletenessClaim, NodeId, PublicationEligibility, RequestId,
    RuleVersion, CLOSURE_POLICY_VERSION,
};

struct ScenarioResult {
    status: ClosureStatus,
    publication_blocked: bool,
    progress_used: bool,
    claim_applied: bool,
    policy_version_ok: bool,
    pass: bool,
}

fn n(id: &str) -> NodeId {
    NodeId::parse(id).expect("static id")
}

fn rv(id: &str) -> RuleVersion {
    RuleVersion::parse(id).expect("static id")
}

fn rid(id: &str) -> RequestId {
    RequestId::parse(id).expect("static id")
}

fn base_graph() -> FixedDependencyEvidence {
    FixedDependencyEvidence::new(rv("rules:v1"))
        .with_node(n("node:A"), vec![n("node:B")])
        .with_node(n("node:B"), vec![n("node:C")])
        .with_node(n("node:C"), vec![])
}

fn run_complete_eligible() -> ScenarioResult {
    let svc = ComputeDependencyClosure::new(base_graph());
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:ok"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    let pass = result.status == ClosureStatus::Complete
        && result.publication_eligibility == PublicationEligibility::Eligible
        && !result.progress_used_as_completeness
        && !result.completeness_claim_applied
        && result.trace.policy_version == CLOSURE_POLICY_VERSION;
    ScenarioResult {
        status: result.status,
        publication_blocked: result.publication_eligibility.is_blocked(),
        progress_used: result.progress_used_as_completeness,
        claim_applied: result.completeness_claim_applied,
        policy_version_ok: result.trace.policy_version == CLOSURE_POLICY_VERSION,
        pass,
    }
}

fn run_incomplete_missing() -> ScenarioResult {
    let evidence = FixedDependencyEvidence::new(rv("rules:v1"))
        .with_node(n("node:A"), vec![n("node:MISSING")]);
    let svc = ComputeDependencyClosure::new(evidence);
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:missing"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    let pass = result.status == ClosureStatus::Incomplete
        && result.publication_eligibility == PublicationEligibility::Blocked
        && result.missing.iter().any(|x| x.as_str() == "node:MISSING");
    ScenarioResult {
        status: result.status,
        publication_blocked: result.publication_eligibility.is_blocked(),
        progress_used: result.progress_used_as_completeness,
        claim_applied: result.completeness_claim_applied,
        policy_version_ok: result.trace.policy_version == CLOSURE_POLICY_VERSION,
        pass,
    }
}

fn run_unknown_seed() -> ScenarioResult {
    let svc = ComputeDependencyClosure::new(FixedDependencyEvidence::new(rv("rules:v1")));
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:unknown"),
        changed: vec![n("node:GHOST")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    let pass = result.status == ClosureStatus::Unknown
        && result.publication_eligibility == PublicationEligibility::Blocked;
    ScenarioResult {
        status: result.status,
        publication_blocked: result.publication_eligibility.is_blocked(),
        progress_used: result.progress_used_as_completeness,
        claim_applied: result.completeness_claim_applied,
        policy_version_ok: result.trace.policy_version == CLOSURE_POLICY_VERSION,
        pass,
    }
}

fn run_unbounded_fanout() -> ScenarioResult {
    let mut evidence = FixedDependencyEvidence::new(rv("rules:v1"));
    for i in 0..12 {
        evidence = evidence.with_node(
            n(&format!("node:N{i}")),
            vec![n(&format!("node:N{}", i + 1))],
        );
    }
    evidence = evidence.with_node(n("node:N12"), vec![]);
    let svc = ComputeDependencyClosure::new(evidence);
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:unbounded"),
        changed: vec![n("node:N0")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    let pass = result.status == ClosureStatus::Unbounded
        && result.publication_eligibility == PublicationEligibility::Blocked;
    ScenarioResult {
        status: result.status,
        publication_blocked: result.publication_eligibility.is_blocked(),
        progress_used: result.progress_used_as_completeness,
        claim_applied: result.completeness_claim_applied,
        policy_version_ok: result.trace.policy_version == CLOSURE_POLICY_VERSION,
        pass,
    }
}

fn run_rule_version_mismatch() -> ScenarioResult {
    let svc = ComputeDependencyClosure::new(base_graph());
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:skew"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v2"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    let pass = result.status == ClosureStatus::RuleVersionMismatch
        && result.publication_eligibility == PublicationEligibility::Blocked;
    ScenarioResult {
        status: result.status,
        publication_blocked: result.publication_eligibility.is_blocked(),
        progress_used: result.progress_used_as_completeness,
        claim_applied: result.completeness_claim_applied,
        policy_version_ok: result.trace.policy_version == CLOSURE_POLICY_VERSION,
        pass,
    }
}

fn run_forbidden_claim_matrix() -> ScenarioResult {
    let svc = ComputeDependencyClosure::new(base_graph());
    let mut all_pass = true;
    for claim in [
        CompletenessClaim::ProgressAsComplete,
        CompletenessClaim::QueueDepthAsComplete,
        CompletenessClaim::InventedAffectedSet,
    ] {
        let result = svc.compute(ClosureRequest {
            request_id: rid("req:claim"),
            changed: vec![n("node:A")],
            expected_rule_version: rv("rules:v1"),
            completeness_claim: claim,
            request_incremental_publication: true,
        });
        all_pass &= result.status == ClosureStatus::Incomplete
            && result.publication_eligibility == PublicationEligibility::Blocked
            && !result.completeness_claim_applied
            && !result.progress_used_as_completeness;
    }
    ScenarioResult {
        status: if all_pass {
            ClosureStatus::Incomplete
        } else {
            ClosureStatus::Complete
        },
        publication_blocked: all_pass,
        progress_used: false,
        claim_applied: false,
        policy_version_ok: true,
        pass: all_pass,
    }
}

fn run_hostile_freeze_holds() -> ScenarioResult {
    let empty = FixedDependencyEvidence::new(rv("rules:v1"));
    let svc = ComputeDependencyClosure::new(HostileProgressCompleteness::wrapping(empty));
    let ghost = svc.compute(ClosureRequest {
        request_id: rid("req:hostile-ghost"),
        changed: vec![n("node:GHOST")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    let incomplete_inner = FixedDependencyEvidence::new(rv("rules:v1"))
        .with_node(n("node:A"), vec![n("node:MISSING")]);
    let svc2 =
        ComputeDependencyClosure::new(HostileProgressCompleteness::wrapping(incomplete_inner));
    let missing = svc2.compute(ClosureRequest {
        request_id: rid("req:hostile-missing"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    let pass = ghost.status == ClosureStatus::Unknown
        && ghost.publication_eligibility == PublicationEligibility::Blocked
        && missing.status == ClosureStatus::Incomplete
        && missing.publication_eligibility == PublicationEligibility::Blocked
        && !ghost.progress_used_as_completeness
        && !missing.progress_used_as_completeness;
    ScenarioResult {
        status: ghost.status,
        publication_blocked: pass,
        progress_used: false,
        claim_applied: false,
        policy_version_ok: ghost.trace.policy_version == CLOSURE_POLICY_VERSION,
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc11-receipt/v1\",\"case_id\":\"HC-11\",\"scenario\":\"{}\",\"status\":\"{}\",\"publication_blocked\":{},\"progress_used_as_completeness\":{},\"completeness_claim_applied\":{},\"policy_version_ok\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"dependency_index_selected\":false}}",
        scenario,
        result.status.as_str(),
        result.publication_blocked,
        result.progress_used,
        result.claim_applied,
        result.policy_version_ok,
        result.pass,
    )
}

fn render_verdict() -> String {
    let complete = run_complete_eligible();
    let incomplete = run_incomplete_missing();
    let unknown = run_unknown_seed();
    let unbounded = run_unbounded_fanout();
    let skew = run_rule_version_mismatch();
    let claims = run_forbidden_claim_matrix();
    let hostile = run_hostile_freeze_holds();
    let pass = complete.pass
        && incomplete.pass
        && unknown.pass
        && unbounded.pass
        && skew.pass
        && claims.pass
        && hostile.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc11-verdict/v1\",\"evidence_id\":\"S10-HC-11-RT\",\"case_id\":\"HC-11\",\"verdict\":\"{verdict}\",\"scenario_count\":7,\"complete_eligible\":{},\"incomplete_missing_blocks\":{},\"unknown_seed_blocks\":{},\"unbounded_fanout_blocks\":{},\"rule_version_mismatch_blocks\":{},\"forbidden_claim_matrix\":{},\"hostile_freeze_holds\":{},\"progress_never_completeness\":{},\"remaining_unsupported_cases\":9,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"dependency_index_selected\":false}}",
        complete.pass,
        incomplete.pass,
        unknown.pass,
        unbounded.pass,
        skew.pass,
        claims.pass,
        hostile.pass,
        !complete.progress_used
            && !incomplete.progress_used
            && !unknown.progress_used
            && !unbounded.progress_used
            && !skew.progress_used
            && !claims.progress_used
            && !hostile.progress_used,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc11_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "complete-eligible" => run_complete_eligible(),
        "incomplete-missing" => run_incomplete_missing(),
        "unknown-seed" => run_unknown_seed(),
        "unbounded-fanout" => run_unbounded_fanout(),
        "rule-version-mismatch" => run_rule_version_mismatch(),
        "forbidden-claim-matrix" => run_forbidden_claim_matrix(),
        "hostile-freeze-holds" => run_hostile_freeze_holds(),
        _ => {
            eprintln!("hc11_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
