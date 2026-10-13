//! Ladder-bound hierarchy lift over `document_groups` profiles (M224 S05 T02).
//!
//! This module is the *marker → ladder* half of the S05 lift: it takes the
//! first-wins [`HierarchyCandidateReport`] produced by
//! [`crate::hierarchy::extract_hierarchy_candidates`] and places each
//! candidate token onto the ladder declared by a [`GroupProfile`]. It is the
//! corpus-facing counterpart of the fixture-bound registry lift in
//! `ln-product-cli` (MEM730); unlike that path it must never guess a
//! `statya` default when the document group is unknown (KBO-R029).
//!
//! Two entry points:
//!
//! - [`detect_and_lift`] runs the two-factor
//!   [`StructuralProfile::detect`] on the decoded blocks, then lifts onto the
//!   detected group (or fails the whole document closed when detection is
//!   `Unknown`/`Conflict`).
//! - [`lift_hierarchy_over_group`] lifts onto an explicitly named group id.
//!
//! Boundary decided here and deliberately *not* crossed (S05 scope):
//!
//! - The lift is a **structural ladder placement**, not a `StructuralAst`
//!   fold and not an assembly FSM / edition timeline step — those stay in S06.
//! - A `Bound` placement is a `system_observation` heuristic. It mints **no**
//!   `ComponentConcept`; this crate does not depend on `ln-kb-ontology`
//!   (MEM832) and never writes YAML.
//! - A marker that does not land on a declared ladder entry is
//!   [`LiftDisposition::Unknown`] (fail-closed). Silently defaulting an
//!   undeclared level (notably `razdel` in a federal law, R8-08) is forbidden.
//! - A `text_only` profile (court_practice / non_normative) never receives a
//!   normative ladder placement: practice text is not an AST (ADR-0020,
//!   ADR-0030 D2). The marker stream is still counted, but as
//!   [`LiftDisposition::NonNormative`] — the ladder is not consulted at all.

use std::collections::BTreeMap;

use crate::domain::ParsedBlock;
use crate::hierarchy::{HierarchyCandidate, HierarchyCandidateReport};
use crate::structural_profile::{
    DetectionFactor, GroupDetection, StructuralProfile, UnknownReason,
};

/// Type-level non-claims of the lift report (D185 sibling: what this is NOT).
pub const HIERARCHY_LIFT_NON_CLAIMS: &[&str] = &[
    "Lift placements are a structural ladder binding, not a ComponentConcept; the lift never mints a ComponentConcept identifier.",
    "A Bound placement is a system_observation heuristic, not legal hierarchy truth: not InForce, not Applicable, not authority.",
    "An unmapped marker is Unknown (fail-closed); this lift never invents a statya default for an undeclared level (KBO-R029, R8-08).",
    "A text_only profile never receives a normative ladder placement; practice text is not an AST (ADR-0020, ADR-0030 D2).",
];

/// Per-candidate placement outcome. One value per unique candidate, in
/// document order; the reason a marker stays empty is deliberate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LiftDisposition {
    /// The candidate token matched a non-surface ladder entry; `token` is the
    /// canonical ladder token and `role` its declared structural role.
    Bound { token: String, role: String },
    /// No normative ladder placement (fail-closed). Never a guessed default.
    Unknown { reason: LiftUnknownReason },
    /// The document group is `text_only`: the normative ladder is not applied.
    NonNormative,
}

/// Why a candidate (or the whole document) stayed `Unknown` — fail-closed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LiftUnknownReason {
    /// No document group could be detected (no metadata / no needle).
    GroupUnknown,
    /// Detection conflicted: either metadata conflict or a bound metadata
    /// group whose structural probe found no unit markers (do not guess).
    GroupConflict,
    /// The group is known, but the candidate token is absent from its ladder.
    TokenNotInLadder,
    /// The explicitly requested group id has no profile in the catalog.
    NoGroupProfile,
}

/// Counts-only lift report for one document. Carries no decoded text: only
/// group identity, the detection provenance, token/role counts and the
/// declared non-claims.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyLiftReport {
    /// Detected group id, or the explicitly requested id, or `""` when no
    /// group was named and none was detected.
    pub group: String,
    /// The authoritative two-factor detection outcome (for the explicit
    /// entry point this records the caller-asserted binding — see
    /// [`lift_hierarchy_over_group`]).
    pub detection: GroupDetection,
    /// Unique first-wins candidates considered (`candidates.unique_count()`).
    pub markers_total: usize,
    /// Candidates placed on a normative ladder role.
    pub bound: usize,
    /// Candidates that failed a normative placement (any reason).
    pub unknown: usize,
    /// True when the profile is `text_only`: no normative ladder was applied.
    pub non_normative: bool,
    /// Bound placements by ladder role (`unit`, `subunit`, `container`, ...).
    pub per_role: BTreeMap<String, usize>,
    /// Token accounting for every candidate that failed a normative
    /// placement (any [`LiftUnknownReason`]); empty for `text_only` groups.
    pub unmapped_tokens: BTreeMap<String, usize>,
    /// Per-candidate dispositions in document order (observability).
    pub placements: Vec<LiftDisposition>,
    /// Declared non-claims; mirrors [`HIERARCHY_LIFT_NON_CLAIMS`].
    pub non_claims: Vec<&'static str>,
}

/// Lift candidates onto an explicitly named group's ladder.
///
/// - A missing group id is fail-closed: every candidate is
///   `Unknown { NoGroupProfile }` (`group` echoes the requested id).
/// - A `text_only` group is [`LiftDisposition::NonNormative`] for every
///   candidate; its ladder (usually empty) is never consulted.
/// - Otherwise each candidate token is compared case-insensitively against
///   non-surface ladder entries. Surface-only structural tokens
///   (primechanie/prilozhenie) are skipped — they are not decode-level
///   candidates. A token present → `Bound`; absent → `Unknown {
///   TokenNotInLadder }`.
///
/// The explicit entry point records detection as a caller-asserted
/// `Bound { factor }`; call [`detect_and_lift`] when the authoritative
/// two-factor provenance matters.
pub fn lift_hierarchy_over_group(
    profile: &StructuralProfile,
    group_id: &str,
    candidates: &HierarchyCandidateReport,
) -> HierarchyLiftReport {
    let Some(group) = profile.group(group_id) else {
        return all_unknown_report(
            group_id.to_owned(),
            GroupDetection::Unknown {
                reason: UnknownReason::NoMetadata,
            },
            candidates,
            LiftUnknownReason::NoGroupProfile,
        );
    };

    if group.text_only {
        // Barrier (S04, ADR-0020 / ADR-0030 D2): the normative ladder is not
        // applied to a text_only profile, so numbered lists stay text.
        return HierarchyLiftReport {
            group: group.id.clone(),
            detection: GroupDetection::Bound {
                group: group.id.clone(),
                factor: DetectionFactor::Needle,
            },
            markers_total: candidates.unique_count(),
            bound: 0,
            unknown: 0,
            non_normative: true,
            per_role: BTreeMap::new(),
            unmapped_tokens: BTreeMap::new(),
            placements: vec![LiftDisposition::NonNormative; candidates.unique_count()],
            non_claims: HIERARCHY_LIFT_NON_CLAIMS.to_vec(),
        };
    }

    let mut bound = 0usize;
    let mut unknown = 0usize;
    let mut per_role: BTreeMap<String, usize> = BTreeMap::new();
    let mut unmapped_tokens: BTreeMap<String, usize> = BTreeMap::new();
    let mut placements = Vec::with_capacity(candidates.unique_count());
    for candidate in candidates.candidates() {
        match ladder_role(group, candidate) {
            Some((token, role)) => {
                bound += 1;
                *per_role.entry(role.clone()).or_insert(0) += 1;
                placements.push(LiftDisposition::Bound { token, role });
            }
            None => {
                unknown += 1;
                *unmapped_tokens
                    .entry(candidate.catalog_token().to_owned())
                    .or_insert(0) += 1;
                placements.push(LiftDisposition::Unknown {
                    reason: LiftUnknownReason::TokenNotInLadder,
                });
            }
        }
    }

    HierarchyLiftReport {
        group: group.id.clone(),
        detection: GroupDetection::Bound {
            group: group.id.clone(),
            factor: DetectionFactor::NeedleAndProbe,
        },
        markers_total: candidates.unique_count(),
        bound,
        unknown,
        non_normative: false,
        per_role,
        unmapped_tokens,
        placements,
        non_claims: HIERARCHY_LIFT_NON_CLAIMS.to_vec(),
    }
}

/// Detect the document group by the two-factor profile, then lift.
///
/// Detection outcomes map as follows (all fail-closed):
/// - `Bound` → lift onto the detected group; detection is preserved verbatim
///   so the caller sees the true factor provenance.
/// - `Unknown { NoMetadata }` → every candidate `Unknown { GroupUnknown }`.
/// - `Unknown { ProbeConflict }` → every candidate `Unknown { GroupConflict }`.
/// - `Conflict { .. }` → every candidate `Unknown { GroupConflict }`.
pub fn detect_and_lift(
    profile: &StructuralProfile,
    path: Option<&str>,
    kind: Option<&str>,
    doc_type: Option<&str>,
    blocks: &[ParsedBlock],
    candidates: &HierarchyCandidateReport,
) -> HierarchyLiftReport {
    let detection = profile.detect(path, kind, doc_type, blocks);
    match &detection {
        GroupDetection::Bound { group, .. } => {
            let mut report = lift_hierarchy_over_group(profile, group, candidates);
            report.detection = detection;
            report
        }
        GroupDetection::Unknown { reason } => {
            let (group, lift_reason) = match reason {
                UnknownReason::NoMetadata => (String::new(), LiftUnknownReason::GroupUnknown),
                UnknownReason::ProbeConflict { metadata_group } => {
                    (metadata_group.clone(), LiftUnknownReason::GroupConflict)
                }
            };
            all_unknown_report(group, detection, candidates, lift_reason)
        }
        GroupDetection::Conflict { groups } => {
            let group = groups.join(",");
            all_unknown_report(
                group,
                detection,
                candidates,
                LiftUnknownReason::GroupConflict,
            )
        }
    }
}

/// Case-insensitive lookup of a candidate's decode token on the group's
/// non-surface ladder. Returns the canonical `(token, role)` of the first
/// match in catalog order.
fn ladder_role(
    group: &crate::structural_profile::GroupProfile,
    candidate: &HierarchyCandidate,
) -> Option<(String, String)> {
    let token = candidate.catalog_token();
    group
        .ladder
        .iter()
        .filter(|entry| entry.surface.is_none())
        .find(|entry| entry.token.eq_ignore_ascii_case(token))
        .map(|entry| (entry.token.clone(), entry.role.clone()))
}

/// Build the fail-closed report where every candidate is `Unknown { reason }`.
fn all_unknown_report(
    group: String,
    detection: GroupDetection,
    candidates: &HierarchyCandidateReport,
    reason: LiftUnknownReason,
) -> HierarchyLiftReport {
    let mut unmapped_tokens: BTreeMap<String, usize> = BTreeMap::new();
    let mut placements = Vec::with_capacity(candidates.unique_count());
    for candidate in candidates.candidates() {
        *unmapped_tokens
            .entry(candidate.catalog_token().to_owned())
            .or_insert(0) += 1;
        placements.push(LiftDisposition::Unknown { reason });
    }
    let unknown = placements.len();
    HierarchyLiftReport {
        group,
        detection,
        markers_total: candidates.unique_count(),
        bound: 0,
        unknown,
        non_normative: false,
        per_role: BTreeMap::new(),
        unmapped_tokens,
        placements,
        non_claims: HIERARCHY_LIFT_NON_CLAIMS.to_vec(),
    }
}
