//! ISO legal_act_effect_day ↔ synthetic ordinal. Not a legal calendar.

use ln_temporal::calendar::{
    CalendarError, calendar_non_claims, legal_act_effect_day_to_ordinal,
    ordinal_to_legal_act_effect_day,
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
fn max_year_boundary_is_accepted_and_roundtrips() {
    let ordinal = legal_act_effect_day_to_ordinal("2100-12-31").expect("max year");
    assert_eq!(
        ordinal_to_legal_act_effect_day(ordinal).expect("roundtrip"),
        "2100-12-31"
    );
}

#[test]
fn century_leap_year_rules_distinguish_divisible_by_100_and_400() {
    assert_eq!(
        legal_act_effect_day_to_ordinal("1900-02-29").expect_err("1900 not leap"),
        CalendarError::InvalidIsoDay
    );
    assert_eq!(
        legal_act_effect_day_to_ordinal("2100-02-29").expect_err("2100 not leap"),
        CalendarError::InvalidIsoDay
    );
    let ordinal = legal_act_effect_day_to_ordinal("2000-02-29").expect("2000 is leap");
    assert_eq!(
        ordinal_to_legal_act_effect_day(ordinal).expect("roundtrip 2000"),
        "2000-02-29"
    );
}

#[test]
fn malformed_iso_is_rejected() {
    for day in [
        "2014",
        "2014/01/01",
        "2014/01-01",
        "2014-01/01",
        "2014-1-1",
        "",
    ] {
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
    assert!(
        calendar_non_claims()
            .iter()
            .any(|claim| claim.contains("not a legal calendar"))
    );
    assert!(
        calendar_non_claims()
            .iter()
            .any(|claim| claim.contains("InForce") || claim.contains("applicability"))
    );
}

#[test]
fn ordinal_to_day_rejects_out_of_bounds_and_roundtrips_december_and_non_leap_feb28() {
    assert_eq!(
        ordinal_to_legal_act_effect_day(-1).expect_err("below min_year"),
        CalendarError::OutOfBounds
    );
    assert_eq!(
        ordinal_to_legal_act_effect_day(0).expect("min_year epoch"),
        "1800-01-01"
    );
    let max_ordinal = legal_act_effect_day_to_ordinal("2100-12-31").expect("max");
    assert_eq!(
        ordinal_to_legal_act_effect_day(max_ordinal + 1).expect_err("above max_year"),
        CalendarError::OutOfBounds
    );
    for day in ["2014-02-28", "2024-12-31", "2024-03-01", "2024-01-01"] {
        let ord = legal_act_effect_day_to_ordinal(day).expect(day);
        assert_eq!(ordinal_to_legal_act_effect_day(ord).expect(day), day);
    }
}

#[test]
fn calendar_error_display_messages_are_non_empty() {
    for err in [
        CalendarError::CatalogMissing,
        CalendarError::InvalidIsoDay,
        CalendarError::OutOfBounds,
        CalendarError::ClockMismatch,
    ] {
        assert!(!err.to_string().is_empty());
    }
}

#[test]
fn parse_calendar_bounds_validates_bounds_and_ignores_sibling_sections() {
    use ln_temporal::calendar::parse_calendar_bounds;

    let valid_equal = "calendar:\n  clock: legal_act_effect\n  epoch: \"2020-01-01\"\n  min_year: 2020\n  max_year: 2020\nother:\n  max_year: 1999\n";
    let bounds = parse_calendar_bounds(valid_equal).expect("equal bounds");
    assert_eq!(bounds.min_year, 2020);
    assert_eq!(bounds.max_year, 2020);

    let inverted = "calendar:\n  clock: legal_act_effect\n  epoch: \"2020-01-01\"\n  min_year: 2021\n  max_year: 2020\n";
    assert_eq!(
        parse_calendar_bounds(inverted).expect_err("min > max"),
        CalendarError::CatalogMissing
    );

    let epoch_low = "calendar:\n  clock: legal_act_effect\n  epoch: \"2019-12-31\"\n  min_year: 2020\n  max_year: 2025\n";
    assert_eq!(
        parse_calendar_bounds(epoch_low).expect_err("epoch < min"),
        CalendarError::CatalogMissing
    );

    let epoch_high = "calendar:\n  clock: legal_act_effect\n  epoch: \"2026-01-01\"\n  min_year: 2020\n  max_year: 2025\n";
    assert_eq!(
        parse_calendar_bounds(epoch_high).expect_err("epoch > max"),
        CalendarError::CatalogMissing
    );

    let bad_epoch_day = "calendar:\n  clock: legal_act_effect\n  epoch: \"2021-02-29\"\n  min_year: 2020\n  max_year: 2025\n";
    assert_eq!(
        parse_calendar_bounds(bad_epoch_day).expect_err("invalid epoch day"),
        CalendarError::CatalogMissing
    );
}
