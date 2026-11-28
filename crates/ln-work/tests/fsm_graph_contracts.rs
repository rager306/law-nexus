use ln_fsm::graph::{to_mermaid_state_diagram, validate_graph};
use ln_fsm::model_check::{ModelCheckConfig, run_deterministic_model_check};
use ln_fsm::{DeterministicFsm, RejectionKind};
use ln_work::domain::{
    TransitionOutcome, WORK_POLICY_VERSION, WORK_STATE_GRAPH_SPEC, WorkEvent, WorkState,
    WorkStateMachine,
};

const ALL_STATES: [WorkState; 7] = [
    WorkState::Requested,
    WorkState::Running,
    WorkState::Cancelling,
    WorkState::Cancelled,
    WorkState::Failed,
    WorkState::Committed,
    WorkState::Stale,
];

const ALL_EVENTS: [WorkEvent; 7] = [
    WorkEvent::Start,
    WorkEvent::Cancel,
    WorkEvent::CancelAck,
    WorkEvent::Resume,
    WorkEvent::Fail,
    WorkEvent::Commit,
    WorkEvent::MarkStale,
];

/// Compile-time exhaustiveness guard: adding a new WorkState or WorkEvent
/// forces updating `ALL_STATES` / `ALL_EVENTS` and `WORK_STATE_GRAPH_SPEC`.
fn assert_exhaustive_work_enums(state: WorkState, event: WorkEvent) {
    match state {
        WorkState::Requested
        | WorkState::Running
        | WorkState::Cancelling
        | WorkState::Cancelled
        | WorkState::Failed
        | WorkState::Committed
        | WorkState::Stale => {}
    }
    match event {
        WorkEvent::Start
        | WorkEvent::Cancel
        | WorkEvent::CancelAck
        | WorkEvent::Resume
        | WorkEvent::Fail
        | WorkEvent::Commit
        | WorkEvent::MarkStale => {}
    }
}

#[test]
fn work_state_graph_spec_is_valid_and_bijective_with_runtime_machine() {
    let report = validate_graph(&WORK_STATE_GRAPH_SPEC).expect("work state graph must validate");
    assert_eq!(report.state_count, ALL_STATES.len());
    assert_eq!(report.reachable_count, ALL_STATES.len());
    assert_eq!(report.terminal_count, 0);

    let fsm = WorkStateMachine;
    let mut observed_edges = 0usize;
    for state in ALL_STATES {
        assert_eq!(
            fsm.is_terminal(&state),
            WORK_STATE_GRAPH_SPEC.terminals.contains(&state.as_str())
        );
        for event in ALL_EVENTS {
            assert_exhaustive_work_enums(state, event);
            let declared = WORK_STATE_GRAPH_SPEC
                .transitions
                .iter()
                .find(|edge| edge.from == state.as_str() && edge.event == event.as_str());
            match (fsm.apply(state, event), declared) {
                (Ok(receipt), Some(edge)) => {
                    assert_eq!(receipt.next.as_str(), edge.to);
                    assert_eq!(receipt.trace.policy_version, WORK_POLICY_VERSION);
                    assert!(receipt.trace.accepted);
                    observed_edges += 1;
                }
                (Err(rej), None) => {
                    assert_eq!(rej.kind, RejectionKind::InvalidTransition);
                    assert_eq!(rej.reason, TransitionOutcome::InvalidTransition);
                    assert_eq!(rej.trace.policy_version, WORK_POLICY_VERSION);
                    assert!(!rej.trace.accepted);
                }
                (Ok(receipt), None) => {
                    panic!(
                        "runtime accepted undeclared edge ({:?}, {:?}) -> {:?}",
                        state, event, receipt.next
                    );
                }
                (Err(rej), Some(edge)) => {
                    panic!(
                        "runtime rejected declared edge ({:?}, {:?}) -> {} with {:?}",
                        state, event, edge.to, rej.kind
                    );
                }
            }
        }
    }
    assert_eq!(observed_edges, WORK_STATE_GRAPH_SPEC.transitions.len());

    let mermaid = to_mermaid_state_diagram(&WORK_STATE_GRAPH_SPEC);
    assert!(mermaid.contains("[*] --> requested"));
    assert!(mermaid.contains("running --> committed: commit"));
}

#[test]
fn work_state_deterministic_model_check_enforces_domain_invariants() {
    let fsm = WorkStateMachine;
    let report = run_deterministic_model_check(
        &fsm,
        WorkState::Requested,
        &ALL_EVENTS,
        ModelCheckConfig::default(),
        |prev, _event, outcome| {
            if let Ok(receipt) = outcome {
                if *prev == WorkState::Requested && receipt.next == WorkState::Committed {
                    return Err("Requested must never jump straight to Committed".to_owned());
                }
                if *prev == WorkState::Committed && receipt.next == WorkState::Running {
                    return Err("Committed must never jump straight to Running".to_owned());
                }
            }
            Ok(())
        },
    )
    .expect("work state model check must pass");
    assert_eq!(report.sequences_run, 256);
    assert!(report.accepted_steps > 0);
    assert!(report.rejected_steps > 0);
}
