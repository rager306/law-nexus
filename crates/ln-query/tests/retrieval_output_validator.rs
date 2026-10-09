//! Closed-vocabulary tests for the Rust retrieval output validator contract.
//!
//! These tests freeze the contract published in
//! `prd/retrieval/rust_retrieval_output_validator_contract.md`
//! (`retrieval-output-validator/rust-v1`): the sixteen-code diagnostic taxonomy
//! with stable strings, severity, and verdict; fail-closed identifier parsing;
//! scope resolution rejecting missing fields; and the `ValidationOutcome`
//! invariants. Behavioural validator tests over the fixture graph are added in
//! this slice's later tasks.

use std::collections::BTreeSet;

use ln_query::domain::QueryId;
use ln_query::retrieval_output::*;

#[test]
fn contract_version_is_frozen() {
    assert_eq!(
        VALIDATOR_CONTRACT_VERSION,
        "retrieval-output-validator/rust-v1"
    );
    assert!(
        ValidatorContractVersion::parse(VALIDATOR_CONTRACT_VERSION).is_ok(),
        "the frozen contract version must parse"
    );
}

#[test]
fn diagnostic_taxonomy_is_closed_to_sixteen_codes() {
    assert_eq!(OutputDiagnosticCode::ALL.len(), 16);
    let mut seen = BTreeSet::new();
    for code in OutputDiagnosticCode::ALL {
        assert!(
            seen.insert(code.as_str()),
            "duplicate code {}",
            code.as_str()
        );
    }
    assert_eq!(seen.len(), 16, "the dictionary must be closed and distinct");
}

#[test]
fn diagnostic_code_strings_severity_and_verdict_are_stable() {
    let expected: [(OutputDiagnosticCode, &str, &str, &str); 16] = [
        (
            OutputDiagnosticCode::MalformedOutputShape,
            "malformed_output_shape",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::MissingRequiredField,
            "missing_required_field",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::UnknownIdNamespace,
            "unknown_id_namespace",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::UnresolvedCitationKey,
            "unresolved_citation_key",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::AmbiguousCitationKey,
            "ambiguous_citation_key",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::UnresolvedEvidenceSpan,
            "unresolved_evidence_span",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::OrphanedSourcePath,
            "orphaned_source_path",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::OrphanedLegalUnitPath,
            "orphaned_legal_unit_path",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::IdPathMismatch,
            "id_path_mismatch",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::SupersededEvidence,
            "superseded_evidence",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::WrongEdition,
            "wrong_edition",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::AnswerClaimWithoutEvidence,
            "answer_claim_without_evidence",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::CitationWithoutEvidence,
            "citation_without_evidence",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::UnsafeNoAnswerShape,
            "unsafe_no_answer_shape",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::ForbiddenPayloadField,
            "forbidden_payload_field",
            "error",
            "rejected",
        ),
        (
            OutputDiagnosticCode::ScopedNoAnswer,
            "scoped_no_answer",
            "info",
            "accepted_scoped_no_answer",
        ),
    ];
    assert_eq!(expected.len(), 16);
    for (code, wire, severity, verdict) in expected {
        assert_eq!(code.as_str(), wire);
        assert_eq!(code.severity().as_str(), severity);
        assert_eq!(code.verdict().as_str(), verdict);
    }
}

#[test]
fn output_kind_and_verdict_vocabularies_are_closed() {
    assert_eq!(OutputKind::ALL.len(), 3);
    assert_eq!(
        OutputKind::RetrievalCandidate.as_str(),
        "retrieval_candidate"
    );
    assert_eq!(OutputKind::AnswerClaim.as_str(), "answer_claim");
    assert_eq!(OutputKind::ScopedNoAnswer.as_str(), "scoped_no_answer");

    assert_eq!(OutputVerdict::Accepted.as_str(), "accepted");
    assert_eq!(
        OutputVerdict::AcceptedScopedNoAnswer.as_str(),
        "accepted_scoped_no_answer"
    );
    assert_eq!(OutputVerdict::Rejected.as_str(), "rejected");

    assert_eq!(ClaimKind::ALL.len(), 4);
    assert_eq!(ClaimKind::NormReference.as_str(), "norm_reference");
    assert_eq!(ClaimKind::Condition.as_str(), "condition");
}

#[test]
fn id_parse_fails_closed_on_empty_over_long_and_unsupported_input() {
    assert_eq!(RetrievalOutputId::parse("").unwrap_err().reason(), "empty");

    let too_long = "A".repeat(129);
    assert_eq!(
        CitationKey::parse(&too_long).unwrap_err().reason(),
        "too long"
    );

    assert_eq!(
        EvidenceSpanId::parse("EV 001").unwrap_err().reason(),
        "unsupported character"
    );
    assert_eq!(
        LegalUnitId::parse("LU#ART").unwrap_err().reason(),
        "unsupported character"
    );

    let ok = SourceBlockId::parse("SB-M012-001").expect("fixture block id parses");
    assert_eq!(ok.as_str(), "SB-M012-001");
}

#[test]
fn bounded_token_rejects_raw_payload_alphabet() {
    assert!(BoundedToken::parse("citations[0].evidence_span_id").is_ok());
    assert!(BoundedToken::parse("raw legal text with spaces").is_err());
    assert!(BoundedToken::parse("Юридический текст").is_err());
    assert_eq!(BoundedToken::missing().as_str(), "<missing>");
}

#[test]
fn forbidden_payload_denylist_is_closed_and_case_insensitive() {
    assert!(is_forbidden_payload_field("raw_legal_text"));
    assert!(is_forbidden_payload_field("RAW_LEGAL_TEXT"));
    assert!(is_forbidden_payload_field("provider-payload"));
    assert!(is_forbidden_payload_field("falkordb_row"));
    assert!(!is_forbidden_payload_field("citation_key"));
    assert!(!is_forbidden_payload_field("citations"));
}

fn complete_observed_scope() -> ObservedScope {
    ObservedScope {
        scope_id: FieldShape::Value(
            OutputScopeId::parse("SCOPE-M012-44FZ-2024-001").expect("scope id"),
        ),
        query_id: FieldShape::Value(QueryId::parse("Q-M012-VALID-001").expect("query id")),
        retrieval_run_id: FieldShape::Value(RetrievalRunId::parse("RUN-M012-001").expect("run id")),
        as_of_date: FieldShape::Value(ScopeAsOfDate::parse("2024-01-01").expect("as-of date")),
        source_corpus_id: FieldShape::Value(
            SourceCorpusId::parse("CORPUS-M012-FIXTURE").expect("corpus id"),
        ),
        validator_contract_version: FieldShape::Value(
            ValidatorContractVersion::parse(VALIDATOR_CONTRACT_VERSION).expect("version"),
        ),
    }
}

#[test]
fn scope_resolution_accepts_the_complete_scope() {
    let scope = complete_observed_scope()
        .resolve()
        .expect("complete scope resolves");
    assert_eq!(scope.scope_id().as_str(), "SCOPE-M012-44FZ-2024-001");
    assert_eq!(scope.retrieval_run_id.as_str(), "RUN-M012-001");
    assert_eq!(scope.as_of_date.as_str(), "2024-01-01");
}

#[test]
fn scope_resolution_rejects_missing_and_null_fields() {
    let mut missing = complete_observed_scope();
    missing.retrieval_run_id = FieldShape::Missing;
    let err = missing.resolve().unwrap_err();
    assert_eq!(err.field(), ScopeField::RetrievalRunId);
    assert_eq!(err.field_path(), "scope.retrieval_run_id");

    let mut explicit_null = complete_observed_scope();
    explicit_null.as_of_date = FieldShape::ExplicitNull;
    let err = explicit_null.resolve().unwrap_err();
    assert_eq!(err.field(), ScopeField::AsOfDate);

    let mut wrong_shape = complete_observed_scope();
    wrong_shape.source_corpus_id = FieldShape::WrongShape;
    assert!(wrong_shape.resolve().is_err());

    assert_eq!(ScopeField::ALL.len(), 6);
}

#[test]
fn field_shape_distinguishes_missing_from_explicit_null() {
    let missing: FieldShape<EvidenceSpanId> = FieldShape::Missing;
    let explicit_null: FieldShape<EvidenceSpanId> = FieldShape::ExplicitNull;
    let present = FieldShape::Value(EvidenceSpanId::parse("EV-M012-001").expect("evidence id"));

    assert!(missing.is_missing());
    assert!(!missing.is_explicit_null());
    assert!(explicit_null.is_explicit_null());
    assert!(!explicit_null.is_missing());
    assert!(!present.is_absent_or_null());
    assert_eq!(
        present.value().map(EvidenceSpanId::as_str),
        Some("EV-M012-001")
    );
}

#[test]
fn outcome_invariants_enforce_rejected_and_accepted_pairings() {
    let info = OutputDiagnostic::new(
        OutputDiagnosticCode::ScopedNoAnswer,
        BoundedToken::parse("citations").expect("path"),
    );
    let error = OutputDiagnostic::new(
        OutputDiagnosticCode::MissingRequiredField,
        BoundedToken::parse("citations[0].evidence_span_id").expect("path"),
    );

    // Accepted with no diagnostics is valid.
    let accepted = ValidationOutcome::checked(OutputVerdict::Accepted, vec![])
        .expect("accepted without diagnostics");
    assert!(!accepted.has_error_diagnostics());
    assert_eq!(accepted.primary_code(), None);

    // A scoped no-answer with an info diagnostic is valid and carries no error.
    let scoped = ValidationOutcome::checked(OutputVerdict::AcceptedScopedNoAnswer, vec![info])
        .expect("scoped no-answer with info");
    assert!(!scoped.has_error_diagnostics());
    assert_eq!(
        scoped.primary_code(),
        Some(OutputDiagnosticCode::ScopedNoAnswer)
    );

    // Rejected without an error diagnostic violates the invariant.
    assert!(ValidationOutcome::checked(OutputVerdict::Rejected, vec![]).is_err());

    // Accepted with an error diagnostic violates the invariant.
    assert!(ValidationOutcome::checked(OutputVerdict::Accepted, vec![error.clone()]).is_err());

    // Rejected with an error diagnostic is valid, and the primary code is it.
    let rejected = ValidationOutcome::checked(OutputVerdict::Rejected, vec![error])
        .expect("rejected with error diagnostic");
    assert!(rejected.has_error_diagnostics());
    assert_eq!(
        rejected.primary_code(),
        Some(OutputDiagnosticCode::MissingRequiredField)
    );
}

#[test]
fn diagnostic_derives_severity_and_verdict_from_code() {
    let error = OutputDiagnostic::new(
        OutputDiagnosticCode::WrongEdition,
        BoundedToken::parse("citations[0].act_edition_id").expect("path"),
    )
    .with_safe_id_value(BoundedToken::parse("ED-M012-44FZ-2023-01-01").expect("id"))
    .with_expected_id(BoundedToken::parse("ED-M012-44FZ-2024-01-01").expect("id"));

    assert_eq!(error.code(), OutputDiagnosticCode::WrongEdition);
    assert_eq!(error.severity(), DiagnosticSeverity::Error);
    assert_eq!(error.verdict(), OutputVerdict::Rejected);
    assert_eq!(
        error.safe_id_value().map(BoundedToken::as_str),
        Some("ED-M012-44FZ-2023-01-01")
    );
    assert_eq!(
        error.expected_id().map(BoundedToken::as_str),
        Some("ED-M012-44FZ-2024-01-01")
    );
    assert_eq!(error.retrieval_output_id().as_str(), "<missing>");
}
