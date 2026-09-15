use ln_decode::current_requisites::RequisitesClaim;
use ln_decode::current_requisites::{
    CurrentDocumentRequisites, DocumentHeadEllipsisEvidence, FieldResolutionStatus,
    RequisitesDiagnostic, RequisitesExtractionStatus, RequisitesField, RequisitesSourceKind,
    SidecarCompleteness, SourceAnchor, ThisRefGrammarEvidence,
};
use ln_decode::domain::TextSpan;

fn claim(
    id: &str,
    field: RequisitesField,
    value: &str,
    source: RequisitesSourceKind,
) -> RequisitesClaim {
    RequisitesClaim::try_new(
        id.into(),
        "doc-v1".into(),
        field,
        value.into(),
        source,
        SourceAnchor::try_new(TextSpan::try_new(0, 1).unwrap(), format!("anchor-{id}")).unwrap(),
        "profile-v1".into(),
        RequisitesExtractionStatus::Observed,
    )
    .unwrap()
}

fn full_claims() -> Vec<RequisitesClaim> {
    RequisitesField::ALL
        .into_iter()
        .enumerate()
        .map(|(i, field)| {
            claim(
                &format!("head-{i}"),
                field,
                "same-value",
                RequisitesSourceKind::DocumentHead,
            )
        })
        .collect()
}

#[test]
fn equal_claims_from_two_sources_are_agreed_without_selection_policy() {
    let mut claims = full_claims();
    for (i, field) in RequisitesField::ALL.into_iter().enumerate() {
        claims.push(claim(
            &format!("filename-{i}"),
            field,
            "same-value",
            RequisitesSourceKind::SourceFilename,
        ));
    }
    let sidecar = CurrentDocumentRequisites::try_new("doc-v1".into(), claims).unwrap();
    assert_eq!(sidecar.completeness(), SidecarCompleteness::CompleteAgreed);
    let number = sidecar
        .field_resolutions()
        .iter()
        .find(|r| r.field() == RequisitesField::Number)
        .unwrap();
    assert_eq!(number.status(), FieldResolutionStatus::Agreed);
    assert_eq!(number.selection_policy_ref(), None);
}

#[test]
fn head_and_filename_disagreement_is_conflicting_with_no_winner() {
    let mut claims = full_claims();
    claims.push(claim(
        "filename-number",
        RequisitesField::Number,
        "different",
        RequisitesSourceKind::SourceFilename,
    ));
    let sidecar = CurrentDocumentRequisites::try_new("doc-v1".into(), claims).unwrap();
    assert_eq!(sidecar.completeness(), SidecarCompleteness::Conflicting);
    let number = sidecar
        .field_resolutions()
        .iter()
        .find(|r| r.field() == RequisitesField::Number)
        .unwrap();
    assert_eq!(number.status(), FieldResolutionStatus::Conflicting);
    assert!(number.compatible_candidate_refs().is_empty());
    assert!(number.selection_policy_ref().is_none());
    assert!(sidecar
        .diagnostics()
        .contains(&RequisitesDiagnostic::HeadFilenameConflict));
}

#[test]
fn single_source_remains_visible_and_b_n_is_not_normalized() {
    let claims = full_claims();
    let sidecar = CurrentDocumentRequisites::try_new("doc-v1".into(), claims).unwrap();
    let number = sidecar
        .field_resolutions()
        .iter()
        .find(|r| r.field() == RequisitesField::Number)
        .unwrap();
    assert_eq!(number.status(), FieldResolutionStatus::SingleSource);

    let mut changed = full_claims();
    changed[RequisitesField::ALL
        .iter()
        .position(|f| *f == RequisitesField::Number)
        .unwrap()] = claim(
        "head-4",
        RequisitesField::Number,
        "б/н",
        RequisitesSourceKind::DocumentHead,
    );
    changed.push(claim(
        "filename-number",
        RequisitesField::Number,
        "12",
        RequisitesSourceKind::SourceFilename,
    ));
    let conflicting = CurrentDocumentRequisites::try_new("doc-v1".into(), changed).unwrap();
    assert_eq!(
        conflicting
            .field_resolutions()
            .iter()
            .find(|r| r.field() == RequisitesField::Number)
            .unwrap()
            .status(),
        FieldResolutionStatus::Conflicting
    );
}

#[test]
fn wrong_document_claim_is_excluded_and_association_fails_closed() {
    let mut claims = full_claims();
    claims[0] = RequisitesClaim::try_new(
        "wrong-type".into(),
        "doc-v1".into(),
        RequisitesField::Type,
        "other".into(),
        RequisitesSourceKind::SourceCatalog,
        SourceAnchor::try_new(TextSpan::try_new(0, 1).unwrap(), "catalog-row".into()).unwrap(),
        "profile-v1".into(),
        RequisitesExtractionStatus::WrongDocument,
    )
    .unwrap();
    let sidecar = CurrentDocumentRequisites::try_new("doc-v1".into(), claims).unwrap();
    let type_resolution = sidecar
        .field_resolutions()
        .iter()
        .find(|r| r.field() == RequisitesField::Type)
        .unwrap();
    assert_eq!(
        type_resolution.status(),
        FieldResolutionStatus::AssociationFailed
    );
    assert!(sidecar
        .diagnostics()
        .contains(&RequisitesDiagnostic::WrongDocumentAssociation));
    assert!(!sidecar
        .authorize_this_document_reference(ThisRefGrammarEvidence::new([RequisitesField::Type])));
}

#[test]
fn completeness_states_are_fail_closed() {
    assert_eq!(
        CurrentDocumentRequisites::try_new("doc-v1".into(), Vec::new())
            .unwrap()
            .completeness(),
        SidecarCompleteness::Unavailable
    );
    assert_eq!(
        CurrentDocumentRequisites::try_new(
            "doc-v1".into(),
            vec![claim(
                "date",
                RequisitesField::Date,
                "2026-01-01",
                RequisitesSourceKind::DocumentHead
            )]
        )
        .unwrap()
        .completeness(),
        SidecarCompleteness::UsablePartial
    );

    let mut malformed = full_claims();
    malformed[0] = RequisitesClaim::try_new(
        "bad-type".into(),
        "doc-v1".into(),
        RequisitesField::Type,
        "".into(),
        RequisitesSourceKind::DocumentHead,
        SourceAnchor::try_new(TextSpan::try_new(0, 1).unwrap(), "head".into()).unwrap(),
        "profile-v1".into(),
        RequisitesExtractionStatus::Malformed,
    )
    .unwrap();
    assert_eq!(
        CurrentDocumentRequisites::try_new("doc-v1".into(), malformed)
            .unwrap()
            .completeness(),
        SidecarCompleteness::UsablePartial
    );

    let mut conflicting = full_claims();
    conflicting.push(claim(
        "catalog-type",
        RequisitesField::Type,
        "other",
        RequisitesSourceKind::SourceCatalog,
    ));
    assert_eq!(
        CurrentDocumentRequisites::try_new("doc-v1".into(), conflicting)
            .unwrap()
            .completeness(),
        SidecarCompleteness::Conflicting
    );
}

#[test]
fn authorization_requires_explicit_grammar_and_non_conflicting_required_field() {
    let sidecar = CurrentDocumentRequisites::try_new("doc-v1".into(), full_claims()).unwrap();
    assert!(!sidecar.authorize_this_document_reference(ThisRefGrammarEvidence::new([])));
    assert!(
        sidecar.authorize_this_document_reference(ThisRefGrammarEvidence::new([
            RequisitesField::Type,
            RequisitesField::Number
        ]))
    );
    assert!(
        sidecar.authorize_document_head_ellipsis(DocumentHeadEllipsisEvidence::new(
            ThisRefGrammarEvidence::new([RequisitesField::Title])
        ))
    );

    let mut conflicting = full_claims();
    conflicting.push(claim(
        "filename-number",
        RequisitesField::Number,
        "different",
        RequisitesSourceKind::SourceFilename,
    ));
    let sidecar = CurrentDocumentRequisites::try_new("doc-v1".into(), conflicting).unwrap();
    assert!(!sidecar
        .authorize_this_document_reference(ThisRefGrammarEvidence::new([RequisitesField::Number])));
}

#[test]
fn diagnostics_have_exact_yaml_spelling() {
    assert_eq!(
        RequisitesDiagnostic::HeadFilenameConflict.as_str(),
        "head_filename_conflict"
    );
    assert_eq!(
        RequisitesDiagnostic::WrongDocumentAssociation.as_str(),
        "wrong_document_association"
    );
    assert_eq!(
        RequisitesDiagnostic::SourceAuthorityPolicyMissing.as_str(),
        "source_authority_policy_missing"
    );
    assert_eq!(
        RequisitesField::ALL
            .into_iter()
            .map(RequisitesField::as_str)
            .collect::<Vec<_>>(),
        vec!["type", "org", "geo", "date", "number", "title", "family"],
        "field spellings are the closed YAML vocabulary"
    );
}

/// RC28-F08: the memo identity of a requisites request is a closed fingerprint
/// over the admitted field set, so empty and non-empty evidence can never be
/// conflated and no source text can leak into the identity.
#[test]
fn grammar_evidence_fingerprint_is_closed_and_deterministic() {
    let empty = ThisRefGrammarEvidence::new([]);
    assert!(empty.is_empty());
    assert_eq!(empty.fingerprint(), "");
    assert_eq!(
        ThisRefGrammarEvidence::new([RequisitesField::Type]).fingerprint(),
        "type"
    );
    assert_eq!(
        ThisRefGrammarEvidence::new([
            RequisitesField::Family,
            RequisitesField::Type,
            RequisitesField::Date,
        ])
        .fingerprint(),
        "type|date|family",
        "the fingerprint is deterministic and order-independent"
    );
    assert!(!ThisRefGrammarEvidence::new([RequisitesField::Title]).is_empty());
}

/// RC28-F08 stale-evidence guard input: the sidecar identity is content-bound,
/// so a changed document version, completeness, or claim set changes it.
#[test]
fn sidecar_identity_fingerprint_is_content_bound() {
    let base = CurrentDocumentRequisites::try_new("doc-v1".into(), full_claims()).unwrap();
    let same = CurrentDocumentRequisites::try_new("doc-v1".into(), full_claims()).unwrap();
    assert_eq!(base.identity_fingerprint(), same.identity_fingerprint());
    assert!(!base.identity_fingerprint().is_empty());

    let changed_value = CurrentDocumentRequisites::try_new("doc-v1".into(), {
        let mut claims = full_claims();
        claims[0] = claim(
            "head-0",
            RequisitesField::Type,
            "different-type",
            RequisitesSourceKind::DocumentHead,
        );
        claims
    })
    .unwrap();
    assert_ne!(
        base.identity_fingerprint(),
        changed_value.identity_fingerprint(),
        "a changed raw value must change the identity"
    );

    let conflicting = CurrentDocumentRequisites::try_new("doc-v1".into(), {
        let mut claims = full_claims();
        claims.push(claim(
            "catalog-type",
            RequisitesField::Type,
            "other-type",
            RequisitesSourceKind::SourceCatalog,
        ));
        claims
    })
    .unwrap();
    assert_ne!(
        base.identity_fingerprint(),
        conflicting.identity_fingerprint(),
        "a changed completeness must change the identity"
    );
}
