use ln_observe::{
    adapters::{InMemoryDiagnosticSink, InMemoryWorkState, InterruptibleSourceAdapter},
    application::ObserveSource,
    domain::{
        AuthorityAbsence, ObservationRequest, ObservationRequestId, PartialObservationSummary,
        SourceChannelId, TransportObservation, TransportOutcome, WorkPhase,
    },
    ports::SourceObservationPort,
};

struct ContractViolatingCompletedSource;

impl SourceObservationPort for ContractViolatingCompletedSource {
    fn observe(&mut self, _request: &ObservationRequest) -> TransportObservation {
        TransportObservation {
            outcome: TransportOutcome::Completed,
            partial: PartialObservationSummary::from_bytes(b"partial-not-complete"),
        }
    }
}

#[test]
fn interrupted_partial_source_stays_transport_failure_without_authority() {
    let canary = b"PARTIAL-SECRET-LEGAL-TEXT";
    let source = InterruptibleSourceAdapter::timeout_after(canary);
    let work = InMemoryWorkState::default();
    let diagnostics = InMemoryDiagnosticSink::default();
    let mut use_case = ObserveSource::new(source, work, diagnostics);

    let request = ObservationRequest::new(
        ObservationRequestId::parse("O1").expect("valid request id"),
        SourceChannelId::parse("S1").expect("valid source id"),
    );
    let result = use_case.execute(request);

    assert_eq!(result.transport_outcome, TransportOutcome::Timeout);
    assert_eq!(
        result
            .work_trace
            .iter()
            .map(|step| step.phase)
            .collect::<Vec<_>>(),
        vec![WorkPhase::Started, WorkPhase::ObservationFailed]
    );
    assert_eq!(result.authority, AuthorityAbsence::default());
    assert!(result.legal_clock_anchor.is_none());
    assert!(result.promotion_id.is_none());
    assert!(result.publication_id.is_none());

    assert_eq!(result.diagnostics.len(), 1);
    let event = &result.diagnostics[0];
    assert_eq!(event.category.as_str(), "timeout");
    assert_eq!(event.phase.as_str(), "observe-source");
    assert!(event.retryable);
    assert_eq!(event.partial_byte_count, canary.len());
    assert!(!event.partial_fingerprint.is_empty());

    let rendered = format!("{result:?}");
    assert!(!rendered.contains("PARTIAL-SECRET-LEGAL-TEXT"));
}

#[test]
fn completed_with_partial_state_fails_closed_and_still_emits_diagnostics() {
    let mut use_case = ObserveSource::new(
        ContractViolatingCompletedSource,
        InMemoryWorkState::default(),
        InMemoryDiagnosticSink::default(),
    );

    let result = use_case.execute(ObservationRequest::new(
        ObservationRequestId::parse("O-contract-violation").expect("valid request id"),
        SourceChannelId::parse("S1").expect("valid source id"),
    ));

    assert_eq!(
        result.transport_outcome,
        TransportOutcome::TransportOrTlsFailure
    );
    assert_eq!(result.work_trace[1].phase, WorkPhase::ObservationFailed);
    assert_eq!(
        result.diagnostics[0].category.as_str(),
        "transport-or-tls-failure"
    );
    assert!(result.diagnostics[0].retryable);
    assert!(result.legal_clock_anchor.is_none());
}

#[test]
fn maximum_valid_request_id_still_derives_bounded_result_ids() {
    let request_id = "r".repeat(64);
    let source = InterruptibleSourceAdapter::cancelled_after(b"partial");
    let mut use_case = ObserveSource::new(
        source,
        InMemoryWorkState::default(),
        InMemoryDiagnosticSink::default(),
    );

    let result = use_case.execute(ObservationRequest::new(
        ObservationRequestId::parse(&request_id).expect("maximum valid request id"),
        SourceChannelId::parse("S1").expect("valid source id"),
    ));

    assert_eq!(result.transport_outcome, TransportOutcome::Cancelled);
    assert!(result.observation_id.as_str().len() <= 80);
    assert!(result.diagnostics[0].diagnostic_id.as_str().len() <= 80);
}
