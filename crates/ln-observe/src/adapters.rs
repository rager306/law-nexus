use crate::domain::{
    DiagnosticEvent, ObservationRequest, PartialObservationSummary, TransportObservation,
    TransportOutcome, WorkTransition,
};
use crate::ports::{DiagnosticPort, SourceObservationPort, WorkStatePort};

#[derive(Debug, Clone)]
pub struct InterruptibleSourceAdapter {
    observation: TransportObservation,
}

impl InterruptibleSourceAdapter {
    pub fn timeout_after(partial_bytes: &[u8]) -> Self {
        Self::interrupted(TransportOutcome::Timeout, partial_bytes)
    }

    pub fn cancelled_after(partial_bytes: &[u8]) -> Self {
        Self::interrupted(TransportOutcome::Cancelled, partial_bytes)
    }

    pub fn transport_failure_after(partial_bytes: &[u8]) -> Self {
        Self::interrupted(TransportOutcome::TransportOrTlsFailure, partial_bytes)
    }

    pub fn access_restricted_after(partial_bytes: &[u8]) -> Self {
        Self::interrupted(TransportOutcome::AccessRestricted, partial_bytes)
    }

    fn interrupted(outcome: TransportOutcome, partial_bytes: &[u8]) -> Self {
        Self {
            observation: TransportObservation {
                outcome,
                partial: PartialObservationSummary::from_bytes(partial_bytes),
            },
        }
    }
}

impl SourceObservationPort for InterruptibleSourceAdapter {
    fn observe(&mut self, _request: &ObservationRequest) -> TransportObservation {
        self.observation.clone()
    }
}

#[derive(Debug, Default)]
pub struct InMemoryWorkState {
    transitions: Vec<WorkTransition>,
}

impl WorkStatePort for InMemoryWorkState {
    fn record_transition(&mut self, transition: WorkTransition) {
        self.transitions.push(transition);
    }

    fn transitions(&self) -> &[WorkTransition] {
        &self.transitions
    }
}

#[derive(Debug, Default)]
pub struct InMemoryDiagnosticSink {
    events: Vec<DiagnosticEvent>,
}

impl DiagnosticPort for InMemoryDiagnosticSink {
    fn emit(&mut self, event: DiagnosticEvent) {
        self.events.push(event);
    }

    fn events(&self) -> &[DiagnosticEvent] {
        &self.events
    }
}
