//! YAML-backed civil-day ordinal for `ClockKind::LegalActEffect`.
//!
//! ISO `YYYY-MM-DD` maps to a synthetic ordinal relative to the catalog epoch.
//! This is not a legal calendar, not timezone math, not CTV text, and not InForce.

use crate::domain::ClockKind;

pub const EMBEDDED_ONTOLOGY_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CalendarBounds {
    pub min_year: i32,
    pub max_year: i32,
    pub epoch_year: i32,
    pub epoch_month: u8,
    pub epoch_day: u8,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CalendarError {
    CatalogMissing,
    InvalidIsoDay,
    OutOfBounds,
    ClockMismatch,
}

impl std::fmt::Display for CalendarError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::CatalogMissing => write!(formatter, "calendar catalog is missing or incomplete"),
            Self::InvalidIsoDay => write!(formatter, "ISO day is not a valid civil date"),
            Self::OutOfBounds => write!(formatter, "civil day is outside the YAML calendar bounds"),
            Self::ClockMismatch => {
                write!(formatter, "calendar clock is not legal_act_effect")
            }
        }
    }
}

impl std::error::Error for CalendarError {}

const CALENDAR_NON_CLAIMS: &[&str] = &[
    "Civil-day ordinal is not a legal calendar and not CTV text",
    "ISO-to-ordinal does not imply InForce or applicability",
    "Not timezone conversion, not publication clock, not system observation",
];

pub fn calendar_non_claims() -> &'static [&'static str] {
    CALENDAR_NON_CLAIMS
}

pub fn embedded_bounds() -> Result<CalendarBounds, CalendarError> {
    parse_calendar_bounds(EMBEDDED_ONTOLOGY_YAML)
}

pub fn legal_act_effect_day_to_ordinal(iso_day: &str) -> Result<i64, CalendarError> {
    let bounds = embedded_bounds()?;
    let (year, month, day) = parse_civil_day(iso_day, bounds)?;
    Ok(days_from_civil(year, month, day)
        - days_from_civil(bounds.epoch_year, bounds.epoch_month, bounds.epoch_day))
}

pub fn ordinal_to_legal_act_effect_day(ordinal: i64) -> Result<String, CalendarError> {
    let bounds = embedded_bounds()?;
    let epoch = days_from_civil(bounds.epoch_year, bounds.epoch_month, bounds.epoch_day);
    let (year, month, day) = civil_from_days(epoch + ordinal);
    if year < bounds.min_year || year > bounds.max_year {
        return Err(CalendarError::OutOfBounds);
    }
    if !is_valid_civil_day(year, month, day) {
        return Err(CalendarError::InvalidIsoDay);
    }
    Ok(format!("{year:04}-{month:02}-{day:02}"))
}

pub fn parse_calendar_bounds(text: &str) -> Result<CalendarBounds, CalendarError> {
    let clock = scalar_under(text, "calendar:", "clock:").ok_or(CalendarError::CatalogMissing)?;
    if clock != ClockKind::LegalActEffect.as_str() {
        return Err(CalendarError::ClockMismatch);
    }
    let epoch = scalar_under(text, "calendar:", "epoch:").ok_or(CalendarError::CatalogMissing)?;
    let min_year = scalar_under(text, "calendar:", "min_year:")
        .and_then(|value| value.parse().ok())
        .ok_or(CalendarError::CatalogMissing)?;
    let max_year = scalar_under(text, "calendar:", "max_year:")
        .and_then(|value| value.parse().ok())
        .ok_or(CalendarError::CatalogMissing)?;
    if min_year > max_year {
        return Err(CalendarError::CatalogMissing);
    }
    let (epoch_year, epoch_month, epoch_day) =
        parse_iso_parts(&epoch).ok_or(CalendarError::CatalogMissing)?;
    if epoch_year < min_year
        || epoch_year > max_year
        || !is_valid_civil_day(epoch_year, epoch_month, epoch_day)
    {
        return Err(CalendarError::CatalogMissing);
    }
    Ok(CalendarBounds {
        min_year,
        max_year,
        epoch_year,
        epoch_month,
        epoch_day,
    })
}

pub fn parse_civil_day(
    iso_day: &str,
    bounds: CalendarBounds,
) -> Result<(i32, u8, u8), CalendarError> {
    let (year, month, day) = parse_iso_parts(iso_day).ok_or(CalendarError::InvalidIsoDay)?;
    if year < bounds.min_year || year > bounds.max_year {
        return Err(CalendarError::OutOfBounds);
    }
    if !is_valid_civil_day(year, month, day) {
        return Err(CalendarError::InvalidIsoDay);
    }
    Ok((year, month, day))
}

fn parse_iso_parts(value: &str) -> Option<(i32, u8, u8)> {
    if value.len() != 10
        || value.as_bytes().get(4) != Some(&b'-')
        || value.as_bytes().get(7) != Some(&b'-')
    {
        return None;
    }
    let bytes = value.as_bytes();
    if !bytes.iter().enumerate().all(|(index, byte)| match index {
        4 | 7 => *byte == b'-',
        _ => byte.is_ascii_digit(),
    }) {
        return None;
    }
    let year = value[0..4].parse().ok()?;
    let month = value[5..7].parse().ok()?;
    let day = value[8..10].parse().ok()?;
    Some((year, month, day))
}

fn is_leap_year(year: i32) -> bool {
    year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
}

fn days_in_month(year: i32, month: u8) -> u8 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if is_leap_year(year) => 29,
        2 => 28,
        _ => 0,
    }
}

fn is_valid_civil_day(year: i32, month: u8, day: u8) -> bool {
    day >= 1 && day <= days_in_month(year, month)
}

/// Howard Hinnant's days-from-civil (proleptic Gregorian).
fn days_from_civil(year: i32, month: u8, day: u8) -> i64 {
    let mut year = i64::from(year);
    let month = i64::from(month);
    if month <= 2 {
        year -= 1;
    }
    let era = if year >= 0 { year } else { year - 399 } / 400;
    let year_of_era = year - era * 400;
    let month_prime = if month > 2 { month - 3 } else { month + 9 };
    let day_of_year = (153 * month_prime + 2) / 5 + i64::from(day) - 1;
    let day_of_era = year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    era * 146_097 + day_of_era - 719_468
}

fn civil_from_days(days: i64) -> (i32, u8, u8) {
    let days = days + 719_468;
    let era = if days >= 0 { days } else { days - 146_096 } / 146_097;
    let day_of_era = (days - era * 146_097) as u64;
    let year_of_era =
        (day_of_era - day_of_era / 1_460 + day_of_era / 36_524 - day_of_era / 146_096) / 365;
    let mut year = year_of_era as i64 + era * 400;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let month_prime = (5 * day_of_year + 2) / 153;
    let day = (day_of_year - (153 * month_prime + 2) / 5 + 1) as u8;
    let month = (if month_prime < 10 {
        month_prime + 3
    } else {
        month_prime - 9
    }) as u8;
    if month <= 2 {
        year += 1;
    }
    (year as i32, month, day)
}

fn scalar_under(text: &str, section: &str, key: &str) -> Option<String> {
    let mut in_section = false;
    let mut section_indent = 0usize;
    for raw in text.lines() {
        let trimmed = match raw.find('#') {
            Some(index) => raw[..index].trim_end(),
            None => raw.trim_end(),
        };
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == section {
            in_section = true;
            section_indent = indent;
            continue;
        }
        if in_section && indent <= section_indent && trimmed.trim().ends_with(':') {
            in_section = false;
        }
        if in_section {
            if let Some(rest) = trimmed.trim().strip_prefix(key) {
                let value = rest.trim().trim_matches('"');
                if !value.is_empty() {
                    return Some(value.to_owned());
                }
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_calendar_is_legal_act_effect_civil_day() {
        let bounds = embedded_bounds().expect("yaml");
        assert_eq!(bounds.min_year, 1800);
        assert_eq!(bounds.max_year, 2100);
        assert_eq!(bounds.epoch_year, 1800);
        assert_eq!(ClockKind::LegalActEffect.as_str(), "legal_act_effect");
    }
}
