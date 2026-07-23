use crate::domain::{DiagnosticEvent, ObservationRequest, TransportObservation, WorkTransition};

/// Adapter failures are classified into `TransportObservation` before crossing
/// this port. The application layer therefore handles transport non-success as
/// data and can always complete its work and diagnostic transitions.
pub trait SourceObservationPort {
    fn observe(&mut self, request: &ObservationRequest) -> TransportObservation;
}

pub trait WorkStatePort {
    fn record_transition(&mut self, transition: WorkTransition);
    fn transitions(&self) -> &[WorkTransition];
}

pub trait DiagnosticPort {
    fn emit(&mut self, event: DiagnosticEvent);
    fn events(&self) -> &[DiagnosticEvent];
}
