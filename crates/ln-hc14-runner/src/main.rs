use std::env;
use std::process::ExitCode;

use ln_replay::adapters::{
    sample_checkpoint, HostileDuplicateEffectLedger, InMemoryCheckpointStore, InMemoryEffectLedger,
};
use ln_replay::application::CoordinateCheckpointAndReplay;
use ln_replay::domain::{
    CheckpointDigest, CheckpointId, EffectId, OperationId, ReplayOutcome, ReplayRequest, RequestId,
    RuleVersion, REPLAY_POLICY_VERSION,
};

struct ScenarioResult {
    outcome: ReplayOutcome,
    applied_count: usize,
    effect_suppressed: bool,
    lineage_rewritten: bool,
    publication_authority_present: bool,
    publication_authority_changed: bool,
    policy_version_ok: bool,
    pass: bool,
}

fn request(id: &str, digest: &str, rules: &str, operation: &str, effect: &str) -> ReplayRequest {
    ReplayRequest {
        request_id: RequestId::parse(id).expect("static id"),
        checkpoint_id: CheckpointId::parse("cp:1").expect("static id"),
        expected_digest: CheckpointDigest::parse(digest).expect("static id"),
        expected_rule_version: RuleVersion::parse(rules).expect("static id"),
        operation_id: OperationId::parse(operation).expect("static id"),
        effect_id: EffectId::parse(effect).expect("static id"),
    }
}

fn honest_store() -> InMemoryCheckpointStore {
    InMemoryCheckpointStore::new().insert(sample_checkpoint(
        "cp:1",
        "digest:abc",
        "rules:v1",
        "op:1",
        "effect:1",
        "history:h1",
    ))
}

fn run_first_apply_then_suppress() -> ScenarioResult {
    let mut svc = CoordinateCheckpointAndReplay::new(honest_store(), InMemoryEffectLedger::new());
    let req = request("req:ok", "digest:abc", "rules:v1", "op:1", "effect:1");
    let first = svc.replay(req.clone());
    let second = svc.replay(req);
    let pass = first.outcome == ReplayOutcome::Applied
        && first.applied_count == 1
        && !first.effect_suppressed
        && second.outcome == ReplayOutcome::Suppressed
        && second.effect_suppressed
        && second.applied_count == 1
        && !second.lineage_rewritten
        && second.publication_authority.is_none()
        && !second.publication_authority_changed
        && second.trace.policy_version == REPLAY_POLICY_VERSION;
    ScenarioResult {
        outcome: second.outcome,
        applied_count: second.applied_count,
        effect_suppressed: second.effect_suppressed,
        lineage_rewritten: second.lineage_rewritten,
        publication_authority_present: second.publication_authority.is_some(),
        publication_authority_changed: second.publication_authority_changed,
        policy_version_ok: second.trace.policy_version == REPLAY_POLICY_VERSION,
        pass,
    }
}

fn run_corrupt_fail_closed() -> ScenarioResult {
    let mut svc = CoordinateCheckpointAndReplay::new(honest_store(), InMemoryEffectLedger::new());
    let result = svc.replay(request(
        "req:corrupt",
        "digest:WRONG",
        "rules:v1",
        "op:1",
        "effect:1",
    ));
    let pass = result.outcome == ReplayOutcome::Corrupt
        && result.applied_count == 0
        && !result.lineage_rewritten
        && result.publication_authority.is_none()
        && !result.publication_authority_changed;
    ScenarioResult {
        outcome: result.outcome,
        applied_count: result.applied_count,
        effect_suppressed: result.effect_suppressed,
        lineage_rewritten: result.lineage_rewritten,
        publication_authority_present: result.publication_authority.is_some(),
        publication_authority_changed: result.publication_authority_changed,
        policy_version_ok: result.trace.policy_version == REPLAY_POLICY_VERSION,
        pass,
    }
}

fn run_incompatible_rule() -> ScenarioResult {
    let mut svc = CoordinateCheckpointAndReplay::new(honest_store(), InMemoryEffectLedger::new());
    let result = svc.replay(request(
        "req:skew",
        "digest:abc",
        "rules:v2",
        "op:1",
        "effect:1",
    ));
    let pass = result.outcome == ReplayOutcome::IncompatibleRule
        && result.applied_count == 0
        && !result.lineage_rewritten
        && result.publication_authority.is_none();
    ScenarioResult {
        outcome: result.outcome,
        applied_count: result.applied_count,
        effect_suppressed: result.effect_suppressed,
        lineage_rewritten: result.lineage_rewritten,
        publication_authority_present: result.publication_authority.is_some(),
        publication_authority_changed: result.publication_authority_changed,
        policy_version_ok: result.trace.policy_version == REPLAY_POLICY_VERSION,
        pass,
    }
}

fn run_incomplete_missing() -> ScenarioResult {
    let mut svc = CoordinateCheckpointAndReplay::new(
        InMemoryCheckpointStore::new(),
        InMemoryEffectLedger::new(),
    );
    let result = svc.replay(request(
        "req:missing",
        "digest:abc",
        "rules:v1",
        "op:1",
        "effect:1",
    ));
    let pass = result.outcome == ReplayOutcome::Incomplete
        && result.applied_count == 0
        && !result.lineage_rewritten
        && result.publication_authority.is_none();
    ScenarioResult {
        outcome: result.outcome,
        applied_count: result.applied_count,
        effect_suppressed: result.effect_suppressed,
        lineage_rewritten: result.lineage_rewritten,
        publication_authority_present: result.publication_authority.is_some(),
        publication_authority_changed: result.publication_authority_changed,
        policy_version_ok: result.trace.policy_version == REPLAY_POLICY_VERSION,
        pass,
    }
}

fn run_hostile_no_duplicate() -> ScenarioResult {
    let mut svc =
        CoordinateCheckpointAndReplay::new(honest_store(), HostileDuplicateEffectLedger::new());
    let req = request("req:hostile", "digest:abc", "rules:v1", "op:1", "effect:1");
    let first = svc.replay(req.clone());
    let second = svc.replay(req.clone());
    let third = svc.replay(req);
    let pass = first.outcome == ReplayOutcome::Applied
        && first.applied_count == 1
        && second.outcome == ReplayOutcome::Suppressed
        && second.applied_count == 1
        && third.outcome == ReplayOutcome::Suppressed
        && third.applied_count == 1
        && third.effect_suppressed
        && !third.lineage_rewritten
        && third.publication_authority.is_none()
        && !third.publication_authority_changed;
    ScenarioResult {
        outcome: third.outcome,
        applied_count: third.applied_count,
        effect_suppressed: third.effect_suppressed,
        lineage_rewritten: third.lineage_rewritten,
        publication_authority_present: third.publication_authority.is_some(),
        publication_authority_changed: third.publication_authority_changed,
        policy_version_ok: third.trace.policy_version == REPLAY_POLICY_VERSION,
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc14-receipt/v1\",\"case_id\":\"HC-14\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"applied_count\":{},\"effect_suppressed\":{},\"lineage_rewritten\":{},\"publication_authority_present\":{},\"publication_authority_changed\":{},\"policy_version_ok\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"checkpoint_store_selected\":false,\"exactly_once_infra_selected\":false}}",
        scenario,
        result.outcome.as_str(),
        result.applied_count,
        result.effect_suppressed,
        result.lineage_rewritten,
        result.publication_authority_present,
        result.publication_authority_changed,
        result.policy_version_ok,
        result.pass,
    )
}

fn render_verdict() -> String {
    let suppress = run_first_apply_then_suppress();
    let corrupt = run_corrupt_fail_closed();
    let skew = run_incompatible_rule();
    let incomplete = run_incomplete_missing();
    let hostile = run_hostile_no_duplicate();
    let pass = suppress.pass && corrupt.pass && skew.pass && incomplete.pass && hostile.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc14-verdict/v1\",\"evidence_id\":\"S10-HC-14-RT\",\"case_id\":\"HC-14\",\"verdict\":\"{verdict}\",\"scenario_count\":5,\"first_apply_then_suppress\":{},\"corrupt_fail_closed\":{},\"incompatible_rule\":{},\"incomplete_missing\":{},\"hostile_no_duplicate\":{},\"publication_authority_never_granted\":{},\"lineage_never_rewritten\":{},\"remaining_unsupported_cases\":6,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"checkpoint_store_selected\":false,\"exactly_once_infra_selected\":false}}",
        suppress.pass,
        corrupt.pass,
        skew.pass,
        incomplete.pass,
        hostile.pass,
        !suppress.publication_authority_present
            && !corrupt.publication_authority_present
            && !skew.publication_authority_present
            && !incomplete.publication_authority_present
            && !hostile.publication_authority_present
            && !suppress.publication_authority_changed
            && !corrupt.publication_authority_changed
            && !skew.publication_authority_changed
            && !incomplete.publication_authority_changed
            && !hostile.publication_authority_changed,
        !suppress.lineage_rewritten
            && !corrupt.lineage_rewritten
            && !skew.lineage_rewritten
            && !incomplete.lineage_rewritten
            && !hostile.lineage_rewritten,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc14_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "first-apply-then-suppress" => run_first_apply_then_suppress(),
        "corrupt-fail-closed" => run_corrupt_fail_closed(),
        "incompatible-rule" => run_incompatible_rule(),
        "incomplete-missing" => run_incomplete_missing(),
        "hostile-no-duplicate" => run_hostile_no_duplicate(),
        _ => {
            eprintln!("hc14_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
