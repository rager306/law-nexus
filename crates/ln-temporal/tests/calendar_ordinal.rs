//! ISO legal_act_effect_day ↔ synthetic ordinal. Not a legal calendar.

use ln_temporal::calendar::{
    calendar_non_claims, legal_act_effect_day_to_ordinal, ordinal_to_legal_act_effect_day,
    CalendarError,
};
use ln_temporal::domain::ClockKind;

#[test]
fn epoch_is_ordinal_zero() {
    assert_eq!(
        legal_act_effect_day_to_ordinal("1800-01-01").expect("epoch"),
        0
    );
}

#[test]
fn next_day_is_one() {
    assert_eq!(
        legal_act_effect_day_to_ordinal("1800-01-02").expect("next"),
        1
    );
}

#[test]
fn leap_day_is_accepted_and_roundtrips() {
    let ordinal = legal_act_effect_day_to_ordinal("2012-02-29").expect("leap");
    assert_eq!(
        ordinal_to_legal_act_effect_day(ordinal).expect("back"),
        "2012-02-29"
    );
}

#[test]
fn february_30_is_rejected() {
    let err = legal_act_effect_day_to_ordinal("2014-02-30").expect_err("feb 30");
    assert_eq!(err, CalendarError::InvalidIsoDay);
}

#[test]
fn non_leap_february_29_is_rejected() {
    let err = legal_act_effect_day_to_ordinal("2014-02-29").expect_err("non-leap");
    assert_eq!(err, CalendarError::InvalidIsoDay);
}

#[test]
fn year_outside_yaml_bounds_is_rejected() {
    let err = legal_act_effect_day_to_ordinal("1799-12-31").expect_err("low");
    assert_eq!(err, CalendarError::OutOfBounds);
    let err = legal_act_effect_day_to_ordinal("2101-01-01").expect_err("high");
    assert_eq!(err, CalendarError::OutOfBounds);
}

#[test]
fn malformed_iso_is_rejected() {
    for day in ["2014", "2014/01/01", "2014-1-1", ""] {
        let err = legal_act_effect_day_to_ordinal(day).expect_err(day);
        assert_eq!(err, CalendarError::InvalidIsoDay);
    }
}

#[test]
fn known_gap_between_two_expressions_is_one_year() {
    let first = legal_act_effect_day_to_ordinal("2014-01-01").expect("2014");
    let later = legal_act_effect_day_to_ordinal("2015-01-01").expect("2015");
    assert_eq!(later - first, 365);
}

#[test]
fn clock_kind_remains_legal_act_effect() {
    assert_eq!(ClockKind::LegalActEffect.as_str(), "legal_act_effect");
    assert!(calendar_non_claims()
        .iter()
        .any(|claim| claim.contains("not a legal calendar")));
    assert!(calendar_non_claims()
        .iter()
        .any(|claim| claim.contains("InForce") || claim.contains("applicability")));
}
