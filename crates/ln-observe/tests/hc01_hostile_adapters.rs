use ln_observe::{
    adapters::{InMemoryDiagnosticSink, InMemoryWorkState, InterruptibleSourceAdapter},
    application::ObserveSource,
    domain::{
        ObservationRequest, ObservationRequestId, SourceChannelId, TransportOutcome, WorkPhase,
    },
};

#[test]
fn every_interrupted_outcome_stays_bounded_and_non_authoritative() {
    let cases: Vec<(
        &str,
        TransportOutcome,
        Box<dyn Fn(&[u8]) -> InterruptibleSourceAdapter>,
    )> = vec![
        (
            "timeout",
            TransportOutcome::Timeout,
            Box::new(InterruptibleSourceAdapter::timeout_after),
        ),
        (
            "cancelled",
            TransportOutcome::Cancelled,
            Box::new(InterruptibleSourceAdapter::cancelled_after),
        ),
        (
            "transport-or-tls-failure",
            TransportOutcome::TransportOrTlsFailure,
            Box::new(InterruptibleSourceAdapter::transport_failure_after),
        ),
        (
            "access-restricted",
            TransportOutcome::AccessRestricted,
            Box::new(InterruptibleSourceAdapter::access_restricted_after),
        ),
    ];

    for (index, (category, outcome, build_adapter)) in cases.into_iter().enumerate() {
        let canary = format!("HOSTILE-PARTIAL-CANARY-{index}-{category}");
        let mut use_case = ObserveSource::new(
            build_adapter(canary.as_bytes()),
            InMemoryWorkState::default(),
            InMemoryDiagnosticSink::default(),
        );
        let result = use_case.execute(ObservationRequest::new(
            ObservationRequestId::parse(&format!("O-hostile-{index}")).expect("valid request id"),
            SourceChannelId::parse("S1").expect("valid source id"),
        ));

        assert_eq!(result.transport_outcome, outcome);
        assert_eq!(result.work_trace[0].phase, WorkPhase::Started);
        assert_eq!(result.work_trace[1].phase, WorkPhase::ObservationFailed);
        assert_eq!(result.diagnostics.len(), 1);
        assert_eq!(result.diagnostics[0].category.as_str(), category);
        assert_eq!(result.diagnostics[0].partial_byte_count, canary.len());
        assert!(result.diagnostics[0]
            .partial_fingerprint
            .starts_with("fnv1a64:"));
        assert!(result.legal_clock_anchor.is_none());
        assert!(result.promotion_id.is_none());
        assert!(result.publication_id.is_none());
        assert!(!format!("{result:?}").contains(&canary));
    }
}

#[test]
fn repeated_execution_returns_only_current_operation_trace() {
    let mut use_case = ObserveSource::new(
        InterruptibleSourceAdapter::timeout_after(b"partial"),
        InMemoryWorkState::default(),
        InMemoryDiagnosticSink::default(),
    );

    for request_id in ["O-repeat-1", "O-repeat-2"] {
        let result = use_case.execute(ObservationRequest::new(
            ObservationRequestId::parse(request_id).expect("valid request id"),
            SourceChannelId::parse("S1").expect("valid source id"),
        ));
        assert_eq!(result.work_trace.len(), 2);
        assert_eq!(result.diagnostics.len(), 1);
        assert_eq!(result.work_trace[0].request_id.as_str(), request_id);
        assert_eq!(
            result.diagnostics[0].observation_id.as_str(),
            format!("observation:{request_id}")
        );
    }
}

#[test]
fn partial_summary_exposes_only_bounded_accessors() {
    let summary = ln_observe::domain::PartialObservationSummary::from_bytes(b"secret");

    assert_eq!(summary.byte_count(), 6);
    assert!(summary.fingerprint().starts_with("fnv1a64:"));
    assert!(!format!("{summary:?}").contains("secret"));
}
