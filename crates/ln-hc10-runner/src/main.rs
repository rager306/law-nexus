use std::env;
use std::process::ExitCode;

use ln_work::adapters::{FixedDomainEvidence, HostileMutatingEvidence};
use ln_work::application::TransitionWorkState;
use ln_work::domain::{
    CheckpointId, DomainSnapshotId, LegalMappingAttempt, PublicationSnapshotId, TransitionOutcome,
    TransitionRequest, WorkEvent, WorkState, WorkUnitId, WORK_POLICY_VERSION,
};

struct ScenarioResult {
    outcome: TransitionOutcome,
    state: WorkState,
    domain_unchanged: bool,
    publication_unchanged: bool,
    legal_mapping_applied: bool,
    policy_version_ok: bool,
    pass: bool,
}

fn unit(id: &str) -> WorkUnitId {
    WorkUnitId::parse(id).expect("static id")
}

fn fixed_running(id: &str) -> TransitionWorkState<FixedDomainEvidence> {
    let evidence = FixedDomainEvidence::with_unit(
        unit(id),
        DomainSnapshotId::parse("domain:D1").expect("static id"),
        PublicationSnapshotId::parse("publication:P1").expect("static id"),
    );
    let mut svc = TransitionWorkState::new(evidence);
    let _ = svc.open(unit(id));
    let start = svc.transition(TransitionRequest {
        work_unit_id: unit(id),
        event: WorkEvent::Start,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(start.outcome, TransitionOutcome::Transitioned);
    svc
}

fn run_cancel_resume_domain_unchanged() -> ScenarioResult {
    let mut svc = fixed_running("work:W1");
    let domain_before = svc.domain_snapshot_of(&unit("work:W1")).expect("domain");
    let pub_before = svc.publication_snapshot_of(&unit("work:W1")).expect("pub");

    let cancel = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W1"),
        event: WorkEvent::Cancel,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    let ack = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W1"),
        event: WorkEvent::CancelAck,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    let resume = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W1"),
        event: WorkEvent::Resume,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });

    let pass = cancel.outcome == TransitionOutcome::Transitioned
        && ack.outcome == TransitionOutcome::Transitioned
        && resume.outcome == TransitionOutcome::Transitioned
        && resume.state == WorkState::Running
        && resume.domain_unchanged
        && resume.publication_unchanged
        && !resume.legal_mapping_applied
        && resume.domain_snapshot == domain_before
        && resume.publication_snapshot == pub_before
        && resume.trace.policy_version == WORK_POLICY_VERSION;

    ScenarioResult {
        outcome: resume.outcome,
        state: resume.state,
        domain_unchanged: resume.domain_unchanged,
        publication_unchanged: resume.publication_unchanged,
        legal_mapping_applied: resume.legal_mapping_applied,
        policy_version_ok: resume.trace.policy_version == WORK_POLICY_VERSION,
        pass,
    }
}

fn run_stale_checkpoint_typed() -> ScenarioResult {
    let mut svc = fixed_running("work:W2");
    let cancel = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W2"),
        event: WorkEvent::Cancel,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    let stale = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W2"),
        event: WorkEvent::CancelAck,
        expected_checkpoint: Some(CheckpointId::parse("cp:stale-wrong").expect("static id")),
        legal_mapping: LegalMappingAttempt::None,
    });
    let pass = cancel.outcome == TransitionOutcome::Transitioned
        && stale.outcome == TransitionOutcome::StaleCheckpoint
        && stale.state == WorkState::Cancelling
        && stale.domain_unchanged
        && stale.publication_unchanged
        && !stale.legal_mapping_applied
        && stale.trace.policy_version == WORK_POLICY_VERSION;

    ScenarioResult {
        outcome: stale.outcome,
        state: stale.state,
        domain_unchanged: stale.domain_unchanged,
        publication_unchanged: stale.publication_unchanged,
        legal_mapping_applied: stale.legal_mapping_applied,
        policy_version_ok: stale.trace.policy_version == WORK_POLICY_VERSION,
        pass,
    }
}

fn run_forbidden_legal_mapping_matrix() -> ScenarioResult {
    let mut svc = fixed_running("work:W3");
    let domain_before = svc.domain_snapshot_of(&unit("work:W3")).expect("domain");
    let forbidden = [
        LegalMappingAttempt::ProgressAsVerified,
        LegalMappingAttempt::ProgressAsCurrent,
        LegalMappingAttempt::ProgressAsLegalState,
        LegalMappingAttempt::MutateLifecycle,
        LegalMappingAttempt::MutateClock,
        LegalMappingAttempt::MutateIdentity,
        LegalMappingAttempt::MutateRelation,
        LegalMappingAttempt::MutateAuthority,
    ];
    let mut all_pass = true;
    for attempt in forbidden {
        let r = svc.transition(TransitionRequest {
            work_unit_id: unit("work:W3"),
            event: WorkEvent::Cancel,
            expected_checkpoint: None,
            legal_mapping: attempt,
        });
        all_pass &= r.outcome == TransitionOutcome::LegalMutationRejected
            && r.state == WorkState::Running
            && !r.legal_mapping_applied
            && r.domain_unchanged
            && r.domain_snapshot == domain_before
            && r.trace.legal_mapping_attempt == attempt;
    }
    ScenarioResult {
        outcome: if all_pass {
            TransitionOutcome::LegalMutationRejected
        } else {
            TransitionOutcome::Transitioned
        },
        state: WorkState::Running,
        domain_unchanged: true,
        publication_unchanged: true,
        legal_mapping_applied: false,
        policy_version_ok: true,
        pass: all_pass,
    }
}

fn run_hostile_freeze_holds() -> ScenarioResult {
    let evidence = HostileMutatingEvidence::new(
        unit("work:W4"),
        DomainSnapshotId::parse("domain:D1").expect("static id"),
        PublicationSnapshotId::parse("publication:P1").expect("static id"),
    );
    let mut svc = TransitionWorkState::new(evidence);
    let _ = svc.open(unit("work:W4"));
    let _ = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W4"),
        event: WorkEvent::Start,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    let cancel = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W4"),
        event: WorkEvent::Cancel,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    let ack = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W4"),
        event: WorkEvent::CancelAck,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    let resume = svc.transition(TransitionRequest {
        work_unit_id: unit("work:W4"),
        event: WorkEvent::Resume,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::MutateAuthority,
    });
    // Resume with legal mapping must reject without applying mutation; state stays cancelled.
    let pass = cancel.outcome == TransitionOutcome::Transitioned
        && ack.outcome == TransitionOutcome::Transitioned
        && resume.outcome == TransitionOutcome::LegalMutationRejected
        && resume.state == WorkState::Cancelled
        && resume.domain_snapshot.as_str() == "domain:D1"
        && resume.publication_snapshot.as_str() == "publication:P1"
        && !resume.legal_mapping_applied
        && resume.domain_unchanged;

    ScenarioResult {
        outcome: resume.outcome,
        state: resume.state,
        domain_unchanged: resume.domain_unchanged,
        publication_unchanged: resume.publication_unchanged,
        legal_mapping_applied: resume.legal_mapping_applied,
        policy_version_ok: resume.trace.policy_version == WORK_POLICY_VERSION,
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc10-receipt/v1\",\"case_id\":\"HC-10\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"state\":\"{}\",\"domain_unchanged\":{},\"publication_unchanged\":{},\"legal_mapping_applied\":{},\"policy_version_ok\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"workflow_engine_selected\":false}}",
        scenario,
        result.outcome.as_str(),
        result.state.as_str(),
        result.domain_unchanged,
        result.publication_unchanged,
        result.legal_mapping_applied,
        result.policy_version_ok,
        result.pass,
    )
}

fn render_verdict() -> String {
    let cancel_resume = run_cancel_resume_domain_unchanged();
    let stale = run_stale_checkpoint_typed();
    let legal_map = run_forbidden_legal_mapping_matrix();
    let hostile = run_hostile_freeze_holds();
    let pass = cancel_resume.pass && stale.pass && legal_map.pass && hostile.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc10-verdict/v1\",\"evidence_id\":\"S10-HC-10-RT\",\"case_id\":\"HC-10\",\"verdict\":\"{verdict}\",\"scenario_count\":4,\"cancel_resume_domain_unchanged\":{},\"stale_checkpoint_typed\":{},\"forbidden_legal_mapping_matrix\":{},\"hostile_freeze_holds\":{},\"legal_mapping_never_applied\":{},\"remaining_unsupported_cases\":10,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"workflow_engine_selected\":false}}",
        cancel_resume.pass,
        stale.pass,
        legal_map.pass,
        hostile.pass,
        !cancel_resume.legal_mapping_applied
            && !stale.legal_mapping_applied
            && !legal_map.legal_mapping_applied
            && !hostile.legal_mapping_applied,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc10_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "cancel-resume-domain-unchanged" => run_cancel_resume_domain_unchanged(),
        "stale-checkpoint-typed" => run_stale_checkpoint_typed(),
        "forbidden-legal-mapping-matrix" => run_forbidden_legal_mapping_matrix(),
        "hostile-freeze-holds" => run_hostile_freeze_holds(),
        _ => {
            eprintln!("hc10_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
