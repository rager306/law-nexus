use crate::domain::{
    AuthorityAbsence, DiagnosticCode, DiagnosticEvent, DiagnosticId, ObservationId,
    ObservationRequest, ObserveSourceResult, TransportOutcome, WorkPhase, WorkTransition,
};
use crate::ports::{DiagnosticPort, SourceObservationPort, WorkStatePort};

pub struct ObserveSource<S, W, D> {
    source: S,
    work_state: W,
    diagnostics: D,
}

impl<S, W, D> ObserveSource<S, W, D> {
    pub fn new(source: S, work_state: W, diagnostics: D) -> Self {
        Self {
            source,
            work_state,
            diagnostics,
        }
    }
}

impl<S, W, D> ObserveSource<S, W, D>
where
    S: SourceObservationPort,
    W: WorkStatePort,
    D: DiagnosticPort,
{
    pub fn execute(&mut self, request: ObservationRequest) -> ObserveSourceResult {
        // Request IDs are capped at 64 bytes and generated IDs have an 80-byte
        // namespace budget, so these conversions are total by construction.
        let observation_id =
            ObservationId::parse(&format!("observation:{}", request.request_id.as_str()))
                .expect("validated request id must fit observation namespace");
        let diagnostic_id =
            DiagnosticId::parse(&format!("diagnostic:{}", request.request_id.as_str()))
                .expect("validated request id must fit diagnostic namespace");

        self.work_state.record_transition(WorkTransition {
            request_id: request.request_id.clone(),
            phase: WorkPhase::Started,
        });

        let mut observation = self.source.observe(&request);
        if observation.outcome == TransportOutcome::Completed && observation.partial.byte_count > 0
        {
            // A completed observation may not carry partial-byte state. Treat an
            // adapter contract violation as a transport failure so work and
            // diagnostic transitions still complete fail-closed.
            observation.outcome = TransportOutcome::TransportOrTlsFailure;
        }

        let final_phase = if observation.outcome == TransportOutcome::Completed {
            WorkPhase::ObservationCompleted
        } else {
            WorkPhase::ObservationFailed
        };
        self.work_state.record_transition(WorkTransition {
            request_id: request.request_id.clone(),
            phase: final_phase,
        });

        let event = DiagnosticEvent {
            diagnostic_id,
            observation_id: observation_id.clone(),
            source_channel_id: request.source_channel_id,
            phase: DiagnosticCode::new("observe-source"),
            category: DiagnosticCode::new(observation.outcome.diagnostic_category()),
            retryable: observation.outcome.retryable(),
            partial_byte_count: observation.partial.byte_count,
            partial_fingerprint: observation.partial.fingerprint,
        };
        self.diagnostics.emit(event);

        ObserveSourceResult {
            observation_id,
            transport_outcome: observation.outcome,
            work_trace: self.work_state.transitions().to_vec(),
            diagnostics: self.diagnostics.events().to_vec(),
            authority: AuthorityAbsence::default(),
            legal_clock_anchor: None,
            promotion_id: None,
            publication_id: None,
        }
    }
}
