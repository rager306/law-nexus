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

// --- resolution port and fail-closed validator (T02) ---------------------

const VALID_OUTPUT_ID: &str = "RET-M012-VALID-001";
const FIXTURE_SCOPE_ID: &str = "SCOPE-M012-44FZ-2024-001";

fn fixture_scope() -> OutputScope {
    OutputScope::new(
        OutputScopeId::parse(FIXTURE_SCOPE_ID).expect("scope id"),
        QueryId::parse("Q-M012-VALID-001").expect("query id"),
        RetrievalRunId::parse("RUN-M012-001").expect("run id"),
        ScopeAsOfDate::parse("2024-01-01").expect("as-of date"),
        SourceCorpusId::parse("CORPUS-M012-FIXTURE").expect("corpus id"),
        ValidatorContractVersion::parse(VALIDATOR_CONTRACT_VERSION).expect("version"),
    )
}

fn citation(
    citation_key: &str,
    evidence_span_id: &str,
    source_block_id: &str,
    source_document_id: &str,
    legal_unit_id: &str,
    act_edition_id: &str,
) -> CitationBinding {
    CitationBinding {
        retrieval_output_id: FieldShape::Value(
            RetrievalOutputId::parse(VALID_OUTPUT_ID).expect("output id"),
        ),
        citation_key: FieldShape::Value(CitationKey::parse(citation_key).expect("citation key")),
        evidence_span_id: FieldShape::Value(
            EvidenceSpanId::parse(evidence_span_id).expect("evidence span id"),
        ),
        source_block_id: FieldShape::Value(
            SourceBlockId::parse(source_block_id).expect("source block id"),
        ),
        source_document_id: FieldShape::Value(
            SourceDocumentId::parse(source_document_id).expect("source document id"),
        ),
        legal_unit_id: FieldShape::Value(LegalUnitId::parse(legal_unit_id).expect("legal unit id")),
        act_edition_id: FieldShape::Value(
            ActEditionId::parse(act_edition_id).expect("act edition id"),
        ),
        answer_claim_id: FieldShape::Missing,
    }
}

fn valid_citation() -> CitationBinding {
    citation(
        "CIT-M012-001",
        "EV-M012-001",
        "SB-M012-001",
        "SD-M012-44FZ-CONSULTANT",
        "LU-M012-44FZ-ART-001",
        "ED-M012-44FZ-2024-01-01",
    )
}

fn envelope(
    output_kind: OutputKind,
    citations: Vec<CitationBinding>,
    answer_claims: Vec<AnswerClaim>,
) -> RetrievalOutputEnvelope {
    RetrievalOutputEnvelope {
        retrieval_output_id: FieldShape::Value(
            RetrievalOutputId::parse(VALID_OUTPUT_ID).expect("output id"),
        ),
        output_kind: FieldShape::Value(output_kind),
        scope: ScopeShape::Complete(fixture_scope()),
        citations: FieldShape::Value(citations),
        answer_claims: FieldShape::Value(answer_claims),
        extra_field_names: Vec::new(),
    }
}

fn answer_claim(claim_id: &str, supported_keys: &[&str]) -> AnswerClaim {
    AnswerClaim {
        answer_claim_id: FieldShape::Value(AnswerClaimId::parse(claim_id).expect("claim id")),
        retrieval_output_id: FieldShape::Value(
            RetrievalOutputId::parse(VALID_OUTPUT_ID).expect("output id"),
        ),
        claim_kind: FieldShape::Value(ClaimKind::NormReference),
        scope_id: FieldShape::Value(OutputScopeId::parse(FIXTURE_SCOPE_ID).expect("scope id")),
        supported_citation_keys: FieldShape::Value(
            supported_keys
                .iter()
                .map(|key| CitationKey::parse(key).expect("citation key"))
                .collect(),
        ),
    }
}

fn assert_single_error(outcome: &ValidationOutcome, expected: OutputDiagnosticCode) {
    assert_eq!(outcome.verdict(), OutputVerdict::Rejected);
    assert_eq!(
        outcome.diagnostics().len(),
        1,
        "rejected outcome carries exactly one primary diagnostic"
    );
    let diagnostic = &outcome.diagnostics()[0];
    assert_eq!(diagnostic.code(), expected);
    assert_eq!(diagnostic.severity(), DiagnosticSeverity::Error);
    assert_eq!(diagnostic.verdict(), OutputVerdict::Rejected);
    assert_eq!(outcome.primary_code(), Some(expected));
    assert!(
        BoundedToken::parse(diagnostic.field_path().as_str()).is_ok(),
        "diagnostic field path stays bounded"
    );
    for bounded in [
        diagnostic.safe_id_value(),
        diagnostic.expected_id(),
        diagnostic.resolved_id(),
    ]
    .into_iter()
    .flatten()
    {
        assert!(
            BoundedToken::parse(bounded.as_str()).is_ok(),
            "diagnostic id value stays bounded"
        );
    }
}

#[test]
fn validator_accepts_valid_retrieval_candidate() {
    let resolver = FixtureGraphResolver::m012();
    let envelope = envelope(
        OutputKind::RetrievalCandidate,
        vec![valid_citation()],
        Vec::new(),
    );
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_eq!(outcome.verdict(), OutputVerdict::Accepted);
    assert!(outcome.diagnostics().is_empty());
    assert_eq!(outcome.primary_code(), None);
}

#[test]
fn validator_accepts_valid_answer_claim() {
    let resolver = FixtureGraphResolver::m012();
    let envelope = envelope(
        OutputKind::AnswerClaim,
        vec![valid_citation()],
        vec![answer_claim("AC-M012-001", &["CIT-M012-001"])],
    );
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_eq!(outcome.verdict(), OutputVerdict::Accepted);
    assert!(outcome.diagnostics().is_empty());
}

#[test]
fn validator_accepts_scoped_no_answer() {
    let resolver = FixtureGraphResolver::m012();
    let envelope = envelope(OutputKind::ScopedNoAnswer, Vec::new(), Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_eq!(outcome.verdict(), OutputVerdict::AcceptedScopedNoAnswer);
    assert_eq!(
        outcome.primary_code(),
        Some(OutputDiagnosticCode::ScopedNoAnswer)
    );
    assert_eq!(outcome.diagnostics().len(), 1);
    assert_eq!(
        outcome.diagnostics()[0].severity(),
        DiagnosticSeverity::Info
    );
}

#[test]
fn validator_rejects_unresolved_citation_key() {
    let resolver = FixtureGraphResolver::m012();
    let mut binding = valid_citation();
    binding.citation_key =
        FieldShape::Value(CitationKey::parse("CIT-M012-DOES-NOT-EXIST").expect("key"));
    let envelope = envelope(OutputKind::RetrievalCandidate, vec![binding], Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_single_error(&outcome, OutputDiagnosticCode::UnresolvedCitationKey);
}

#[test]
fn validator_rejects_ambiguous_citation_key() {
    let resolver = FixtureGraphResolver::m012();
    let mut binding = valid_citation();
    binding.citation_key = FieldShape::Value(CitationKey::parse("CIT-M012-AMBIG").expect("key"));
    let envelope = envelope(OutputKind::RetrievalCandidate, vec![binding], Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_single_error(&outcome, OutputDiagnosticCode::AmbiguousCitationKey);
}

#[test]
fn validator_rejects_unresolved_evidence_span() {
    let resolver = FixtureGraphResolver::m012();
    let mut binding = valid_citation();
    binding.evidence_span_id = FieldShape::Value(
        EvidenceSpanId::parse("EV-M012-DOES-NOT-EXIST").expect("evidence span id"),
    );
    let envelope = envelope(OutputKind::RetrievalCandidate, vec![binding], Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_single_error(&outcome, OutputDiagnosticCode::UnresolvedEvidenceSpan);
}

#[test]
fn validator_rejects_orphaned_source_path() {
    let resolver = FixtureGraphResolver::m012();
    let binding = citation(
        "CIT-M012-ORPHAN-SOURCE",
        "EV-M012-ORPHAN-SOURCE",
        "SB-M012-ORPHAN",
        "SD-M012-MISSING-DOCUMENT",
        "LU-M012-44FZ-ART-001",
        "ED-M012-44FZ-2024-01-01",
    );
    let envelope = envelope(OutputKind::RetrievalCandidate, vec![binding], Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_single_error(&outcome, OutputDiagnosticCode::OrphanedSourcePath);
}

#[test]
fn validator_rejects_orphaned_legal_unit_path() {
    let resolver = FixtureGraphResolver::m012();
    let binding = citation(
        "CIT-M012-ORPHAN-LEGAL",
        "EV-M012-ORPHAN-LEGAL",
        "SB-M012-002",
        "SD-M012-44FZ-GARANT",
        "LU-M012-MISSING-UNIT",
        "ED-M012-44FZ-2024-01-01",
    );
    let envelope = envelope(OutputKind::RetrievalCandidate, vec![binding], Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_single_error(&outcome, OutputDiagnosticCode::OrphanedLegalUnitPath);
}

#[test]
fn validator_rejects_source_path_mismatch() {
    let resolver = FixtureGraphResolver::m012();
    // Explicit source block disagrees with the block reached from EV-M012-001.
    let binding = citation(
        "CIT-M012-001",
        "EV-M012-001",
        "SB-M012-002",
        "SD-M012-44FZ-GARANT",
        "LU-M012-44FZ-ART-001",
        "ED-M012-44FZ-2024-01-01",
    );
    let envelope = envelope(OutputKind::RetrievalCandidate, vec![binding], Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_single_error(&outcome, OutputDiagnosticCode::IdPathMismatch);
}

#[test]
fn validator_rejects_wrong_edition() {
    let resolver = FixtureGraphResolver::m012();
    let mut binding = valid_citation();
    binding.act_edition_id =
        FieldShape::Value(ActEditionId::parse("ED-M012-44FZ-2023-01-01").expect("edition id"));
    let envelope = envelope(OutputKind::RetrievalCandidate, vec![binding], Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_single_error(&outcome, OutputDiagnosticCode::WrongEdition);
}

#[test]
fn validator_rejects_superseded_evidence() {
    let resolver = FixtureGraphResolver::m012();
    let binding = citation(
        "CIT-M012-SUPERSEDED",
        "EV-M012-SUPERSEDED",
        "SB-M012-001",
        "SD-M012-44FZ-CONSULTANT",
        "LU-M012-44FZ-ART-001-OLD",
        "ED-M012-44FZ-2023-01-01",
    );
    let envelope = envelope(OutputKind::RetrievalCandidate, vec![binding], Vec::new());
    let outcome = validate_retrieval_output(&envelope, &resolver);
    assert_single_error(&outcome, OutputDiagnosticCode::SupersededEvidence);
}

#[test]
fn validator_does_not_mutate_the_envelope() {
    let resolver = FixtureGraphResolver::m012();
    let envelope = envelope(
        OutputKind::RetrievalCandidate,
        vec![valid_citation()],
        Vec::new(),
    );
    let snapshot = envelope.clone();
    let _ = validate_retrieval_output(&envelope, &resolver);
    assert_eq!(envelope, snapshot, "validation never repairs the envelope");
}
