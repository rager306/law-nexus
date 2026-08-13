//! FRBR Work/Expression structural identity spine (ADR-0016 / KBO-R011).
//! Distinct from C12 digest identity: number alone is never Work identity.

use ln_identity::domain::{
    compare_work_identities, mint_expression, mint_work, FrbrCompareOutcome, FrbrIdentityError,
    IssuingAuthority, LegalActNumber,
};

#[test]
fn work_requires_authority_date_and_number() {
    let err = mint_work("", "2013-04-05", "44-fz").expect_err("empty authority");
    assert!(matches!(err, FrbrIdentityError::MissingAuthority));

    let err = mint_work("federal", "", "44-fz").expect_err("empty date");
    assert!(matches!(err, FrbrIdentityError::MissingEnactmentDate));

    let err = mint_work("federal", "2013-04-05", "").expect_err("empty number");
    assert!(matches!(err, FrbrIdentityError::MissingActNumber));
}

#[test]
fn number_alone_is_rejected() {
    let err = LegalActNumber::parse("44-fz")
        .ok()
        .and_then(|_| mint_work("", "", "44-fz").err())
        .expect("number alone");
    assert!(matches!(
        err,
        FrbrIdentityError::MissingAuthority | FrbrIdentityError::MissingEnactmentDate
    ));
}

#[test]
fn enactment_date_must_be_iso_day() {
    let err = mint_work("federal", "05.04.2013", "44-fz").expect_err("not iso");
    assert!(matches!(err, FrbrIdentityError::InvalidEnactmentDate));
}

#[test]
fn same_complete_keys_compare_same() {
    let left = mint_work("federal", "2013-04-05", "44-fz").expect("l");
    let right = mint_work("federal", "2013-04-05", "44-fz").expect("r");
    let result = compare_work_identities(&left, &right);
    assert_eq!(result.outcome, FrbrCompareOutcome::Same);
    assert_eq!(left.work_id.as_str(), right.work_id.as_str());
    assert!(!result.used_c12_digest);
}

#[test]
fn same_number_divergent_authority_is_conflict() {
    let left = mint_work("federal", "2013-04-05", "188-fz").expect("l");
    let right = mint_work("regional", "2013-04-05", "188-fz").expect("r");
    let result = compare_work_identities(&left, &right);
    assert_eq!(result.outcome, FrbrCompareOutcome::Conflict);
    assert_ne!(left.work_id.as_str(), right.work_id.as_str());
}

#[test]
fn same_number_divergent_year_is_conflict() {
    let left = mint_work("federal", "2013-04-05", "188-fz").expect("l");
    let right = mint_work("federal", "2015-06-01", "188-fz").expect("r");
    let result = compare_work_identities(&left, &right);
    assert_eq!(result.outcome, FrbrCompareOutcome::Conflict);
}

#[test]
fn distinct_acts_are_different_not_conflict() {
    let left = mint_work("federal", "2013-04-05", "44-fz").expect("l");
    let right = mint_work("federal", "2011-07-18", "223-fz").expect("r");
    let result = compare_work_identities(&left, &right);
    assert_eq!(result.outcome, FrbrCompareOutcome::Different);
}

#[test]
fn expression_requires_work_and_effect_day() {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("w");
    let expr = mint_expression(&work, "2014-01-01").expect("e");
    assert_eq!(expr.work_id.as_str(), work.work_id.as_str());
    assert!(expr.expression_id.as_str().contains("2014-01-01"));
    assert_ne!(expr.expression_id.as_str(), work.work_id.as_str());
}

#[test]
fn expression_rejects_bad_effect_day() {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("w");
    let err = mint_expression(&work, "2014").expect_err("bad day");
    assert!(matches!(err, FrbrIdentityError::InvalidEffectDay));
}

#[test]
fn expression_rejects_impossible_civil_day() {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("w");
    let err = mint_expression(&work, "2014-02-30").expect_err("feb 30");
    assert!(matches!(err, FrbrIdentityError::InvalidEffectDay));
}

#[test]
fn work_does_not_imply_force_or_applicability() {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("w");
    assert!(work
        .non_claims
        .iter()
        .any(|c| c.contains("Force") || c.contains("InForce")));
    assert!(work.non_claims.iter().any(|c| c.contains("Applicab")));
    assert!(IssuingAuthority::parse("federal").is_ok());
}

#[test]
fn eli_projection_is_compatibility_not_canon() {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("w");
    let eli = work.eli_projection();
    assert!(eli.starts_with("urn:lex:ru:"));
    assert_ne!(eli, work.work_id.as_str());
    assert!(work
        .non_claims
        .iter()
        .any(|c| c.contains("ELI") || c.contains("compatibility")));
}
