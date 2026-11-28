use std::cell::Cell;

use ln_decode::document_context::{
    CONTEXT_PHASE_GRAPH_SPEC, ContextPhase, ContextPhaseFsm, ContextPhaseRefusal, ContextTransition,
};
use ln_decode::local_grammar::{
    ENUMERATION_GRAPH_SPEC, EnumerationFsm, EnumerationRefusal, EnumerationState,
    EnumerationTransition,
};
use ln_fsm::graph::{to_mermaid_state_diagram, validate_graph};
use ln_fsm::model_check::{ModelCheckConfig, run_deterministic_model_check};
use ln_fsm::{DeterministicFsm, RejectionKind};

const ALL_CONTEXT_STATES: [ContextPhase; 10] = [
    ContextPhase::NotEvaluated,
    ContextPhase::Requested,
    ContextPhase::Queued,
    ContextPhase::Resolving,
    ContextPhase::Resolved,
    ContextPhase::Partial,
    ContextPhase::Conflicting,
    ContextPhase::Unavailable,
    ContextPhase::Cycle,
    ContextPhase::Limit,
];

const ALL_CONTEXT_EVENTS: [ContextTransition; 9] = [
    ContextTransition::TypedContextRequestEmitted,
    ContextTransition::RequestSchemaAndBudgetPass,
    ContextTransition::DeterministicWorklistDispatch,
    ContextTransition::UniqueAuthorizedClaimSet,
    ContextTransition::MissingNoncriticalContext,
    ContextTransition::IncompatibleAuthorizedClaims,
    ContextTransition::IndexOrSidecarUnavailable,
    ContextTransition::RepeatedDerivationPath,
    ContextTransition::DeclaredBudgetReached,
];

fn assert_exhaustive_context_state(state: ContextPhase) {
    match state {
        ContextPhase::NotEvaluated
        | ContextPhase::Requested
        | ContextPhase::Queued
        | ContextPhase::Resolving
        | ContextPhase::Resolved
        | ContextPhase::Partial
        | ContextPhase::Conflicting
        | ContextPhase::Unavailable
        | ContextPhase::Cycle
        | ContextPhase::Limit => {}
    }
}

fn context_event_name(event: ContextTransition) -> &'static str {
    match event {
        ContextTransition::TypedContextRequestEmitted => "TypedContextRequestEmitted",
        ContextTransition::RequestSchemaAndBudgetPass => "RequestSchemaAndBudgetPass",
        ContextTransition::DeterministicWorklistDispatch => "DeterministicWorklistDispatch",
        ContextTransition::UniqueAuthorizedClaimSet => "UniqueAuthorizedClaimSet",
        ContextTransition::MissingNoncriticalContext => "MissingNoncriticalContext",
        ContextTransition::IncompatibleAuthorizedClaims => "IncompatibleAuthorizedClaims",
        ContextTransition::IndexOrSidecarUnavailable => "IndexOrSidecarUnavailable",
        ContextTransition::RepeatedDerivationPath => "RepeatedDerivationPath",
        ContextTransition::DeclaredBudgetReached => "DeclaredBudgetReached",
    }
}

const ALL_ENUM_STATES: [EnumerationState; 6] = [
    EnumerationState::NotEvaluated,
    EnumerationState::Candidate,
    EnumerationState::Compatible,
    EnumerationState::Conflicting,
    EnumerationState::Incomplete,
    EnumerationState::Rejected,
];

const ALL_ENUM_EVENTS: [EnumerationTransition; 5] = [
    EnumerationTransition::LocalRolesAndValuesCaptured,
    EnumerationTransition::AuthorizedFieldClaimsAgree,
    EnumerationTransition::ExplicitOrInheritedClaimsDisagree,
    EnumerationTransition::RequiredOwnerOrValueMissing,
    EnumerationTransition::GrammarOrBoundContractRefused,
];

fn assert_exhaustive_enum_state(state: EnumerationState) {
    match state {
        EnumerationState::NotEvaluated
        | EnumerationState::Candidate
        | EnumerationState::Compatible
        | EnumerationState::Conflicting
        | EnumerationState::Incomplete
        | EnumerationState::Rejected => {}
    }
}

fn enum_event_name(event: EnumerationTransition) -> &'static str {
    match event {
        EnumerationTransition::LocalRolesAndValuesCaptured => "LocalRolesAndValuesCaptured",
        EnumerationTransition::AuthorizedFieldClaimsAgree => "AuthorizedFieldClaimsAgree",
        EnumerationTransition::ExplicitOrInheritedClaimsDisagree => {
            "ExplicitOrInheritedClaimsDisagree"
        }
        EnumerationTransition::RequiredOwnerOrValueMissing => "RequiredOwnerOrValueMissing",
        EnumerationTransition::GrammarOrBoundContractRefused => "GrammarOrBoundContractRefused",
    }
}

#[test]
fn context_phase_graph_spec_is_valid_bijective_and_model_checked() {
    let report = validate_graph(&CONTEXT_PHASE_GRAPH_SPEC).expect("context graph must validate");
    assert_eq!(report.state_count, ALL_CONTEXT_STATES.len());
    assert_eq!(report.reachable_count, ALL_CONTEXT_STATES.len());
    assert_eq!(report.terminal_count, 6);

    let fsm = ContextPhaseFsm;
    let mut observed_edges = 0usize;
    for state in ALL_CONTEXT_STATES {
        assert_exhaustive_context_state(state);
        let declared_terminal = CONTEXT_PHASE_GRAPH_SPEC.terminals.contains(&state.as_str());
        assert_eq!(
            fsm.is_terminal(&state),
            declared_terminal,
            "ContextPhaseFsm::is_terminal drifted from CONTEXT_PHASE_GRAPH_SPEC for {:?}",
            state
        );
        for event in ALL_CONTEXT_EVENTS {
            let declared = CONTEXT_PHASE_GRAPH_SPEC.transitions.iter().find(|edge| {
                edge.from == state.as_str() && edge.event == context_event_name(event)
            });
            match (fsm.apply(state, event), declared) {
                (Ok(receipt), Some(edge)) => {
                    assert_eq!(receipt.next.as_str(), edge.to);
                    assert_eq!(receipt.trace.policy_version, fsm.policy_version());
                    assert!(receipt.trace.accepted);
                    observed_edges += 1;
                }
                (Err(rej), None) => {
                    assert_eq!(rej.trace.policy_version, fsm.policy_version());
                    assert!(!rej.trace.accepted);
                    if declared_terminal {
                        assert_eq!(rej.kind, RejectionKind::TerminalState);
                        assert_eq!(rej.reason, ContextPhaseRefusal::TerminalState);
                    } else {
                        assert_eq!(rej.kind, RejectionKind::InvalidTransition);
                        assert_eq!(rej.reason, ContextPhaseRefusal::InvalidTransition);
                    }
                }
                (Ok(receipt), None) => panic!(
                    "undeclared ContextPhase edge ({:?}, {:?}) -> {:?}",
                    state, event, receipt.next
                ),
                (Err(rej), Some(edge)) => panic!(
                    "declared ContextPhase edge ({:?}, {:?}) -> {} rejected: {:?}",
                    state, event, edge.to, rej.kind
                ),
            }
        }
    }
    assert_eq!(observed_edges, CONTEXT_PHASE_GRAPH_SPEC.transitions.len());

    let terminals_reached = Cell::new(0usize);
    let mc = run_deterministic_model_check(
        &fsm,
        ContextPhase::NotEvaluated,
        &ALL_CONTEXT_EVENTS,
        ModelCheckConfig {
            seed: 0x4C41_574E_4558_5553,
            sequences: 256,
            max_len: 64,
        },
        |prev, _event, outcome| {
            if let Ok(receipt) = outcome {
                if matches!(prev, ContextPhase::NotEvaluated | ContextPhase::Requested)
                    && receipt.next == ContextPhase::Resolved
                {
                    return Err("context skipped queued/resolving budget gate".to_owned());
                }
                if receipt.next.is_terminal() {
                    terminals_reached.set(terminals_reached.get() + 1);
                }
            }
            Ok(())
        },
    )
    .expect("context phase model check must pass");
    assert_eq!(mc.sequences_run, 256);
    assert!(mc.accepted_steps > 0);
    assert!(mc.rejected_steps > 0);
    assert!(
        terminals_reached.get() > 0,
        "model check must reach terminal ContextPhase states"
    );

    let mermaid = to_mermaid_state_diagram(&CONTEXT_PHASE_GRAPH_SPEC);
    assert!(mermaid.contains("[*] --> not_evaluated"));
    assert!(mermaid.contains("resolved --> [*]"));
}

#[test]
fn d384_enumeration_graph_spec_is_valid_bijective_and_model_checked() {
    let report = validate_graph(&ENUMERATION_GRAPH_SPEC).expect("enumeration graph must validate");
    assert_eq!(report.state_count, ALL_ENUM_STATES.len());
    assert_eq!(report.reachable_count, ALL_ENUM_STATES.len());
    assert_eq!(report.terminal_count, 4);

    let fsm = EnumerationFsm;
    let mut observed_edges = 0usize;
    for state in ALL_ENUM_STATES {
        assert_exhaustive_enum_state(state);
        let declared_terminal = ENUMERATION_GRAPH_SPEC.terminals.contains(&state.as_str());
        assert_eq!(
            fsm.is_terminal(&state),
            declared_terminal,
            "EnumerationFsm::is_terminal drifted from ENUMERATION_GRAPH_SPEC for {:?}",
            state
        );
        for event in ALL_ENUM_EVENTS {
            let declared = ENUMERATION_GRAPH_SPEC
                .transitions
                .iter()
                .find(|edge| edge.from == state.as_str() && edge.event == enum_event_name(event));
            match (fsm.apply(state, event), declared) {
                (Ok(receipt), Some(edge)) => {
                    assert_eq!(receipt.next.as_str(), edge.to);
                    assert_eq!(receipt.trace.policy_version, fsm.policy_version());
                    assert!(receipt.trace.accepted);
                    observed_edges += 1;
                }
                (Err(rej), None) => {
                    assert_eq!(rej.trace.policy_version, fsm.policy_version());
                    assert!(!rej.trace.accepted);
                    if declared_terminal {
                        assert_eq!(rej.kind, RejectionKind::TerminalState);
                        assert_eq!(rej.reason, EnumerationRefusal::TerminalState);
                    } else {
                        assert_eq!(rej.kind, RejectionKind::InvalidTransition);
                        assert_eq!(rej.reason, EnumerationRefusal::InvalidTransition);
                    }
                }
                (Ok(receipt), None) => panic!(
                    "undeclared EnumerationState edge ({:?}, {:?}) -> {:?}",
                    state, event, receipt.next
                ),
                (Err(rej), Some(edge)) => panic!(
                    "declared EnumerationState edge ({:?}, {:?}) -> {} rejected: {:?}",
                    state, event, edge.to, rej.kind
                ),
            }
        }
    }
    assert_eq!(observed_edges, ENUMERATION_GRAPH_SPEC.transitions.len());

    let terminals_reached = Cell::new(0usize);
    let mc = run_deterministic_model_check(
        &fsm,
        EnumerationState::NotEvaluated,
        &ALL_ENUM_EVENTS,
        ModelCheckConfig::default(),
        |prev, _event, outcome| {
            if let Ok(receipt) = outcome {
                if *prev == EnumerationState::NotEvaluated
                    && receipt.next == EnumerationState::Compatible
                {
                    return Err("enumeration skipped Candidate state".to_owned());
                }
                if receipt.next.is_terminal() {
                    terminals_reached.set(terminals_reached.get() + 1);
                }
            }
            Ok(())
        },
    )
    .expect("enumeration model check must pass");
    assert_eq!(mc.sequences_run, 256);
    assert!(mc.accepted_steps > 0);
    assert!(mc.rejected_steps > 0);
    assert!(
        terminals_reached.get() > 0,
        "model check must reach terminal EnumerationState states"
    );

    let mermaid = to_mermaid_state_diagram(&ENUMERATION_GRAPH_SPEC);
    assert!(mermaid.contains("[*] --> not_evaluated"));
    assert!(mermaid.contains("compatible --> [*]"));
}
