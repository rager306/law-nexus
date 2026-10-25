//! Pure FRBR-ELI bridge: one `works:` act row -> Work + Expression pair.
//!
//! Bounded compatibility projection only (ADR-0016 dec.2, ADR-0017 §6):
//! the registry `works:` table carries authority + enactment date + act
//! number; the civil-day ordinal is converted through
//! `ln_temporal::calendar` (never home-made calendar math) and minted via
//! `ln_identity::domain` (never a second identity constructor). The ELI
//! form is `work.eli_projection()` for the Work and `<work>@<iso>` for the
//! dated Expression.
//!
//! Zero I/O, zero decoding: no corpus file, catalogue row, or URI anchor
//! is read here. Unknown acts and non-convertible ordinals fail closed.

use std::fmt;

use ln_identity::domain::{FrbrExpression, FrbrWork, mint_expression, mint_work};
use ln_temporal::calendar::{CalendarError, ordinal_to_legal_act_effect_day};

use crate::registry::works_entry_for_act;

/// Canonical non-claims for the pure bridge (also pinned by the contract
/// suite). Kept snake_case so downstream artifacts can reuse the tokens.
pub const FRBR_BRIDGE_NON_CLAIMS: &[&str] = &[
    "eli_urn_is_a_compatibility_projection_not_project_local_canon",
    "cc_component_concept_canon_is_not_replaced_or_rekeyed",
    "one_work_per_act_dated_editions_are_expressions",
    "uri_anchor_is_never_decoded_normalized_or_re_derived",
    "expression_day_is_the_timeline_effect_day_not_the_registry_rev_date",
    "not_r1000_closure",
    "not_r035_promotion_bounded_mapping_evidence_only",
];

/// Closed refusal set. Every branch is an explicit error; there is no
/// "empty success" for an unmapped act or an unconvertible day.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FrbrBridgeRefusal {
    /// Act number is absent from the registry `works:` table.
    UnknownAct,
    /// Ordinal maps outside the embedded civil-day calendar bounds.
    InvalidOrdinal,
    /// ISO day is not a valid legal-act-effect civil day.
    InvalidEffectDay,
    /// Embedded calendar catalog is missing or has the wrong clock.
    CalendarUnavailable,
    /// Work minting rejected the registry row (fail closed, not masked).
    WorkMintFailed,
    /// Expression minting rejected the converted ISO day.
    ExpressionMintFailed,
}

impl FrbrBridgeRefusal {
    /// Stable ASCII token (used by CLI exit-code mapping in later tasks).
    pub fn as_str(self) -> &'static str {
        match self {
            Self::UnknownAct => "unknown_act",
            Self::InvalidOrdinal => "invalid_ordinal",
            Self::InvalidEffectDay => "invalid_effect_day",
            Self::CalendarUnavailable => "calendar_unavailable",
            Self::WorkMintFailed => "work_mint_failed",
            Self::ExpressionMintFailed => "expression_mint_failed",
        }
    }
}

impl fmt::Display for FrbrBridgeRefusal {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "frbr bridge refused: {}", self.as_str())
    }
}

impl std::error::Error for FrbrBridgeRefusal {}

/// Resolved URI-anchored pair for one dated edition of one act.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrbrPairRef {
    pub work_id: String,
    pub work_eli_urn: String,
    pub expression_id: String,
    pub expression_eli_urn: String,
    pub effect_iso: String,
}

/// Expression ELI form: Work ELI projection, `@`, ISO effect day
/// (ADR-0016 dec.2 / ADR-0017 §6).
pub fn expression_eli_urn(work: &FrbrWork, expression: &FrbrExpression) -> String {
    format!(
        "{}@{}",
        work.eli_projection(),
        expression.legal_act_effect_day
    )
}

fn resolve_pair_from_iso(
    entry: &crate::registry::WorkEntry,
    effect_iso: &str,
) -> Result<FrbrPairRef, FrbrBridgeRefusal> {
    let work = mint_work(&entry.authority, &entry.enactment_date, &entry.act_number)
        .map_err(|_| FrbrBridgeRefusal::WorkMintFailed)?;
    let expression =
        mint_expression(&work, effect_iso).map_err(|_| FrbrBridgeRefusal::ExpressionMintFailed)?;
    Ok(FrbrPairRef {
        work_id: work.work_id.as_str().to_owned(),
        work_eli_urn: work.eli_projection(),
        expression_id: expression.expression_id.as_str().to_owned(),
        expression_eli_urn: expression_eli_urn(&work, &expression),
        effect_iso: expression.legal_act_effect_day.clone(),
    })
}

fn map_calendar_error(error: CalendarError) -> FrbrBridgeRefusal {
    match error {
        CalendarError::OutOfBounds => FrbrBridgeRefusal::InvalidOrdinal,
        CalendarError::InvalidIsoDay => FrbrBridgeRefusal::InvalidEffectDay,
        CalendarError::CatalogMissing | CalendarError::ClockMismatch => {
            FrbrBridgeRefusal::CalendarUnavailable
        }
    }
}

/// Resolve one act + civil-day ordinal into a Work/Expression URI pair.
///
/// Work identity comes strictly from the registry `works:` table; the
/// ordinal is converted only through `ln_temporal::calendar`.
pub fn resolve_frbr_pair(
    act_number: &str,
    effect_day_ordinal: i64,
) -> Result<FrbrPairRef, FrbrBridgeRefusal> {
    let entry = works_entry_for_act(act_number).ok_or(FrbrBridgeRefusal::UnknownAct)?;
    let effect_iso =
        ordinal_to_legal_act_effect_day(effect_day_ordinal).map_err(map_calendar_error)?;
    resolve_pair_from_iso(&entry, &effect_iso)
}

/// Resolve one act + ISO effect day into a Work/Expression URI pair.
/// The ISO day is validated through the embedded calendar (fail closed).
pub fn resolve_frbr_pair_iso(
    act_number: &str,
    effect_iso: &str,
) -> Result<FrbrPairRef, FrbrBridgeRefusal> {
    let entry = works_entry_for_act(act_number).ok_or(FrbrBridgeRefusal::UnknownAct)?;
    ln_temporal::calendar::legal_act_effect_day_to_ordinal(effect_iso)
        .map_err(|_| FrbrBridgeRefusal::InvalidEffectDay)?;
    resolve_pair_from_iso(&entry, effect_iso)
}

/// Deterministic ASCII one-line render of a pair (no timestamps, no paths).
pub fn render_pair_ascii(pair: &FrbrPairRef) -> String {
    format!(
        "work_id={} work_eli_urn={} expression_id={} expression_eli_urn={} effect_iso={}",
        pair.work_id,
        pair.work_eli_urn,
        pair.expression_id,
        pair.expression_eli_urn,
        pair.effect_iso
    )
}
