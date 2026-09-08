use ln_temporal::document_context::{BlockId, Terminal, TextSpan};
use ln_temporal::identity_binding::*;

fn claim(field: FieldKind, value: &str, status: FieldStatus) -> IdentityFieldClaim {
    IdentityFieldClaim::new(
        field,
        BlockId::new(7),
        TextSpan::new(0, value.len()).unwrap(),
        FieldSource::ExplicitMember,
        status,
        value,
    )
    .unwrap()
}

#[test]
fn closed_dictionaries_and_anchors_are_exposed() {
    let c = claim(FieldKind::Org, "Роскомнадзор", FieldStatus::Explicit);
    assert_eq!(c.field(), FieldKind::Org);
    assert_eq!(c.source(), FieldSource::ExplicitMember);
    assert_eq!(c.status(), FieldStatus::Explicit);
    assert!(c.span().start() < c.span().end());
    assert_eq!(
        IdentityFieldClaim::new(
            FieldKind::Geo,
            BlockId::new(1),
            TextSpan::new(3, 3).unwrap(),
            FieldSource::PriorFrame,
            FieldStatus::Inherited,
            "x"
        ),
        Err(IdentityFieldClaimError::EmptySpan)
    );
}

#[test]
fn compatible_candidate_keeps_org_and_geo_separate() {
    let outcome = assemble_identifying_act(vec![
        claim(
            FieldKind::Type,
            "региональный приказ",
            FieldStatus::Explicit,
        ),
        claim(
            FieldKind::Org,
            "Министерство субъекта",
            FieldStatus::Explicit,
        ),
        claim(FieldKind::Geo, "Тверская область", FieldStatus::Explicit),
        claim(FieldKind::Date, "2024-01-01", FieldStatus::Explicit),
        claim(FieldKind::Number, "12", FieldStatus::Explicit),
    ]);
    let ActAssemblyOutcome::Compatible(candidate) = outcome else {
        panic!("expected compatible")
    };
    assert!(candidate.org().is_some());
    assert!(candidate.geo().is_some());
}

#[test]
fn conflicts_are_retained_and_not_resolved_by_proximity() {
    let outcome = assemble_identifying_act(vec![
        claim(FieldKind::Type, "федеральный закон", FieldStatus::Explicit),
        claim(FieldKind::Number, "1", FieldStatus::Explicit),
        claim(FieldKind::Org, "Минфин", FieldStatus::Conflicting),
        claim(FieldKind::Org, "Минюст", FieldStatus::Conflicting),
    ]);
    let ActAssemblyOutcome::Conflicting { retained } = outcome else {
        panic!("expected conflict")
    };
    assert_eq!(
        retained
            .iter()
            .filter(|x| x.field() == FieldKind::Org)
            .count(),
        2
    );
}

#[test]
fn incomplete_and_rejected_outcomes_are_typed() {
    let incomplete = assemble_identifying_act(vec![claim(
        FieldKind::Type,
        "федеральный закон",
        FieldStatus::Explicit,
    )]);
    assert!(
        matches!(incomplete, ActAssemblyOutcome::Incomplete { missing, .. } if missing == vec![FieldKind::Number])
    );

    let rejected = assemble_from_terminal(
        vec![claim(
            FieldKind::Type,
            "федеральный закон",
            FieldStatus::Explicit,
        )],
        Terminal::Unavailable,
    );
    assert!(matches!(
        rejected,
        ActAssemblyOutcome::Rejected {
            reason: AssemblyRejection::UnresolvedTerminal(Terminal::Unavailable),
            ..
        }
    ));
}

#[test]
fn collapsed_source_city_splits_org_and_geo_and_rejects_address_marker() {
    let (org, geo) = split_collapsed_source_city(
        BlockId::new(2),
        TextSpan::new(0, 4).unwrap(),
        TextSpan::new(5, 11).unwrap(),
        "Мэрия",
        "Казань",
    )
    .unwrap();
    assert_eq!(org.field(), FieldKind::Org);
    assert_eq!(geo.field(), FieldKind::Geo);
    assert_eq!(geo.compatibility_basis(), "Казань");
    let bad = assemble_identifying_act(vec![
        claim(
            FieldKind::Type,
            "региональный приказ",
            FieldStatus::Explicit,
        ),
        claim(FieldKind::Number, "1", FieldStatus::Explicit),
        claim(FieldKind::Org, "Мэрия", FieldStatus::Explicit),
        claim(FieldKind::Geo, "станция Казань", FieldStatus::Explicit),
    ]);
    assert!(matches!(
        bad,
        ActAssemblyOutcome::Rejected {
            reason: AssemblyRejection::InvalidGeoJurisdiction,
            ..
        }
    ));
}

#[test]
fn federal_default_geo_is_not_a_second_identity() {
    assert!(federal_default_geo("РФ"));
    let outcome = assemble_identifying_act(vec![
        claim(FieldKind::Type, "федеральный закон", FieldStatus::Explicit),
        claim(FieldKind::Number, "1", FieldStatus::Explicit),
        claim(FieldKind::Geo, "РФ", FieldStatus::Explicit),
    ]);
    assert!(
        matches!(outcome, ActAssemblyOutcome::Compatible(candidate) if candidate.geo().is_some())
    );
}

#[test]
fn claim_limit_preserves_allowed_claims_and_reports_limit() {
    let claims = vec![
        claim(FieldKind::Type, "федеральный закон", FieldStatus::Explicit),
        claim(FieldKind::Number, "1", FieldStatus::Explicit),
        claim(FieldKind::Name, "Название", FieldStatus::Explicit),
    ];
    let outcome = assemble_identifying_act_with_limit(claims, 2);
    assert!(
        matches!(outcome, ActAssemblyOutcome::Rejected { reason: AssemblyRejection::ClaimLimit { limit: 2 }, retained } if retained.len() == 2)
    );
}
