use std::env;
use std::process::ExitCode;

use ln_promote::adapters::InMemoryPromotionStore;
use ln_promote::application::CommitCuratedPromotion;
use ln_promote::domain::{AcceptedSetId, InputDigest, PromotionOpId, PromotionOutcome};

fn outcome_name(outcome: PromotionOutcome) -> &'static str {
    match outcome {
        PromotionOutcome::Cancelled => "cancelled",
        PromotionOutcome::Committed => "committed",
        PromotionOutcome::AlreadyCommitted => "already-committed",
        PromotionOutcome::RejectedMismatch => "rejected-mismatch",
        PromotionOutcome::Incomplete => "incomplete",
    }
}

struct ScenarioResult {
    outcome: PromotionOutcome,
    commit_id: Option<String>,
    commit_digest: Option<String>,
    committed_count: usize,
    curated_effect: bool,
    publication_authority_absent: bool,
}

fn run_cancel_no_effect() -> ScenarioResult {
    let mut use_case = CommitCuratedPromotion::new(InMemoryPromotionStore::default());
    let op = PromotionOpId::parse("P1").expect("static op");
    let set = AcceptedSetId::parse("I1").expect("static set");
    let digest = InputDigest::parse("D1").expect("static digest");
    let _ = use_case.begin(op.clone(), set, digest);
    let cancelled = use_case.cancel(op.clone());
    ScenarioResult {
        outcome: cancelled.outcome,
        commit_id: cancelled.commit_id.as_ref().map(|c| c.as_str().to_owned()),
        commit_digest: cancelled
            .commit_digest
            .as_ref()
            .map(|d| d.as_str().to_owned()),
        committed_count: use_case.committed_count(),
        curated_effect: use_case.has_curated_effect_for(&op),
        publication_authority_absent: !cancelled.has_publication_authority(),
    }
}

fn run_identical_retry_one_commit() -> ScenarioResult {
    let mut use_case = CommitCuratedPromotion::new(InMemoryPromotionStore::default());
    let op = PromotionOpId::parse("P1").expect("static op");
    let set = AcceptedSetId::parse("I1").expect("static set");
    let digest = InputDigest::parse("D1").expect("static digest");
    let _ = use_case.begin(op.clone(), set.clone(), digest.clone());
    let _ = use_case.cancel(op.clone());
    let first = use_case.commit(op.clone(), set.clone(), digest.clone());
    let retry = use_case.commit(op.clone(), set, digest);
    let same_id = first.commit_id == retry.commit_id;
    let same_digest = first.commit_digest == retry.commit_digest;
    let ok = first.outcome == PromotionOutcome::Committed
        && retry.outcome == PromotionOutcome::AlreadyCommitted
        && same_id
        && same_digest
        && use_case.committed_count() == 1
        && !retry.has_publication_authority();
    ScenarioResult {
        outcome: if ok {
            PromotionOutcome::AlreadyCommitted
        } else {
            PromotionOutcome::Incomplete
        },
        commit_id: retry.commit_id.as_ref().map(|c| c.as_str().to_owned()),
        commit_digest: retry.commit_digest.as_ref().map(|d| d.as_str().to_owned()),
        committed_count: use_case.committed_count(),
        curated_effect: use_case.has_curated_effect_for(&op),
        publication_authority_absent: !first.has_publication_authority()
            && !retry.has_publication_authority(),
    }
}

fn run_mismatch_reject() -> ScenarioResult {
    let mut use_case = CommitCuratedPromotion::new(InMemoryPromotionStore::default());
    let op = PromotionOpId::parse("P1").expect("static op");
    let set = AcceptedSetId::parse("I1").expect("static set");
    let digest = InputDigest::parse("D1").expect("static digest");
    let other = InputDigest::parse("D2").expect("static digest");
    let first = use_case.commit(op.clone(), set.clone(), digest);
    let mismatch = use_case.commit(op.clone(), set, other);
    let ok = first.outcome == PromotionOutcome::Committed
        && mismatch.outcome == PromotionOutcome::RejectedMismatch
        && mismatch.commit_id.is_none()
        && use_case.committed_count() == 1
        && !mismatch.has_publication_authority();
    ScenarioResult {
        outcome: if ok {
            PromotionOutcome::RejectedMismatch
        } else {
            PromotionOutcome::Incomplete
        },
        commit_id: mismatch.commit_id.as_ref().map(|c| c.as_str().to_owned()),
        commit_digest: mismatch
            .commit_digest
            .as_ref()
            .map(|d| d.as_str().to_owned()),
        committed_count: use_case.committed_count(),
        curated_effect: use_case.has_curated_effect_for(&op),
        publication_authority_absent: !mismatch.has_publication_authority(),
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc04-receipt/v1\",\"case_id\":\"HC-04\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"commit_id_present\":{},\"commit_digest_present\":{},\"committed_count\":{},\"curated_effect\":{},\"publication_authority_absent\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false}}",
        scenario,
        outcome_name(result.outcome),
        result.commit_id.is_some(),
        result.commit_digest.is_some(),
        result.committed_count,
        result.curated_effect,
        result.publication_authority_absent,
    )
}

fn render_verdict() -> String {
    let cancel = run_cancel_no_effect();
    let retry = run_identical_retry_one_commit();
    let mismatch = run_mismatch_reject();

    let cancel_ok = cancel.outcome == PromotionOutcome::Cancelled
        && cancel.commit_id.is_none()
        && cancel.committed_count == 0
        && !cancel.curated_effect
        && cancel.publication_authority_absent;
    let retry_ok = retry.outcome == PromotionOutcome::AlreadyCommitted
        && retry.committed_count == 1
        && retry.curated_effect
        && retry.publication_authority_absent
        && retry.commit_id.is_some()
        && retry.commit_digest.as_deref() == Some("D1");
    let mismatch_ok = mismatch.outcome == PromotionOutcome::RejectedMismatch
        && mismatch.commit_id.is_none()
        && mismatch.committed_count == 1
        && mismatch.publication_authority_absent;
    let pass = cancel_ok && retry_ok && mismatch_ok;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc04-verdict/v1\",\"evidence_id\":\"S10-HC-04-RT\",\"case_id\":\"HC-04\",\"verdict\":\"{verdict}\",\"scenario_count\":3,\"cancel_no_effect\":{},\"identical_retry_one_commit\":{},\"mismatch_reject\":{},\"one_d116_effect\":{},\"publication_authority_absent\":{},\"remaining_unsupported_cases\":16,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false}}",
        cancel_ok,
        retry_ok,
        mismatch_ok,
        retry_ok && mismatch_ok,
        cancel.publication_authority_absent
            && retry.publication_authority_absent
            && mismatch.publication_authority_absent,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc04_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "cancel-no-effect" => run_cancel_no_effect(),
        "identical-retry-one-commit" => run_identical_retry_one_commit(),
        "mismatch-reject" => run_mismatch_reject(),
        _ => {
            eprintln!("hc04_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
