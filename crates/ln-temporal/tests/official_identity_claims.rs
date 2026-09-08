use ln_temporal::document_context::{BlockId, TextSpan};
use ln_temporal::identity_binding::*;

fn claim(field: FieldKind, value: &str, status: FieldStatus) -> IdentityFieldClaim {
    IdentityFieldClaim::new(
        field,
        BlockId::new(4),
        TextSpan::new(0, value.len()).unwrap(),
        FieldSource::ExplicitMember,
        status,
        value,
    )
    .unwrap()
}

fn act(
    kind: &str,
    org: Option<&str>,
    geo: Option<&str>,
    date: Option<&str>,
    number: Option<&str>,
) -> IdentifyingActCandidate {
    IdentifyingActCandidate::new(
        if kind.contains("федераль") {
            ActType::Federal
        } else if kind.contains("президент") {
            ActType::PresidentialAgency
        } else {
            ActType::RegionalMunicipal
        },
        claim(FieldKind::Type, kind, FieldStatus::Explicit),
        org.map(|value| claim(FieldKind::Org, value, FieldStatus::Explicit)),
        geo.map(|value| claim(FieldKind::Geo, value, FieldStatus::Explicit)),
        date.map(|value| claim(FieldKind::Date, value, FieldStatus::Explicit)),
        number.map(|value| claim(FieldKind::Number, value, FieldStatus::Explicit)),
        None,
    )
}

#[test]
fn class_specific_keys_match_contract() {
    let federal =
        build_official_identity_claim(&act("федеральный закон", None, Some("РФ"), None, Some("1")));
    let agency = build_official_identity_claim(&act(
        "указ президентского агентства",
        Some("Агентство"),
        None,
        Some("2024-01-01"),
        Some("2"),
    ));
    let regional = build_official_identity_claim(&act(
        "региональный приказ",
        Some("Мэрия"),
        Some("Казань"),
        Some("2024-01-01"),
        Some("3"),
    ));
    assert!(
        matches!(federal, IdentityClaimOutcome::Proposed(c) if c.class() == IdentityClass::Federal && c.required_key().fields() == [FieldKind::Type, FieldKind::Number] && c.geo_role() == GeoRole::Default)
    );
    assert!(
        matches!(agency, IdentityClaimOutcome::Proposed(c) if c.class() == IdentityClass::PresidentialAgency && c.required_key().fields() == [FieldKind::Type, FieldKind::Org, FieldKind::Date, FieldKind::Number])
    );
    assert!(
        matches!(regional, IdentityClaimOutcome::Proposed(c) if c.class() == IdentityClass::RegionalMunicipal && c.required_key().fields() == [FieldKind::Type, FieldKind::Org, FieldKind::Geo, FieldKind::Date, FieldKind::Number] && c.geo_role() == GeoRole::LoadBearing)
    );
}

#[test]
fn missing_required_provenance_is_incomplete() {
    let regional = build_official_identity_claim(&act(
        "региональный приказ",
        Some("Мэрия"),
        None,
        Some("2024"),
        Some("1"),
    ));
    let agency = build_official_identity_claim(&act(
        "указ президентского агентства",
        None,
        None,
        Some("2024"),
        Some("2"),
    ));
    let federal = build_official_identity_claim(&act("федеральный закон", None, None, None, None));
    assert!(
        matches!(regional, IdentityClaimOutcome::Incomplete { missing, .. } if missing == [FieldKind::Geo])
    );
    assert!(
        matches!(agency, IdentityClaimOutcome::Incomplete { missing, .. } if missing == [FieldKind::Org])
    );
    assert!(
        matches!(federal, IdentityClaimOutcome::Incomplete { missing, .. } if missing == [FieldKind::Number])
    );
}

#[test]
fn claim_id_is_anchor_deterministic_and_not_work_id() {
    let first =
        build_official_identity_claim(&act("федеральный закон", None, None, None, Some("1")));
    let second =
        build_official_identity_claim(&act("федеральный закон", None, None, None, Some("1")));
    let (IdentityClaimOutcome::Proposed(a), IdentityClaimOutcome::Proposed(b)) = (first, second)
    else {
        panic!("expected proposals")
    };
    assert_eq!(a.claim_id(), b.claim_id());
    assert!(a.claim_id().contains("4:0-"));
    assert!(!a.claim_id().to_lowercase().contains("workid"));
    assert_eq!(a.lifecycle(), ProposedLifecycle::Proposed);
}

#[test]
fn unresolved_required_field_never_becomes_a_claim() {
    let outcome = assemble_identifying_act(vec![
        claim(
            FieldKind::Type,
            "региональный приказ",
            FieldStatus::Explicit,
        ),
        claim(FieldKind::Org, "Мэрия", FieldStatus::Explicit),
        claim(FieldKind::Geo, "Казань", FieldStatus::Unresolved),
        claim(FieldKind::Date, "2024", FieldStatus::Explicit),
        claim(FieldKind::Number, "1", FieldStatus::Explicit),
    ]);
    assert!(matches!(
        outcome,
        ActAssemblyOutcome::Incomplete { missing, .. } if missing == [FieldKind::Geo]
    ));
}
