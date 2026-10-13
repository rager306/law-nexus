//! Non-normative structural class contract (M224 S04 T02, ADR-0030 D2).
//!
//! `document_groups` gained an explicit `non_normative` class for practice
//! text banks whose file names carry no *specific* court_practice needle. The
//! ln-decode parser is generic over groups and must stay byte-consistent with
//! the ln-kb-ontology catalog parser on this new group.
//!
//! Non-normativity here is *structural coverage*, declared by `text_only`
//! (ADR-0020: practice text is not an AST); it is never a legal normativity
//! claim. The legal bank axis lives in `ln_kb_ontology::bank_normativity`
//! (D667) — this file only locks the structural side.

use ln_decode::structural_profile::{
    DetectionFactor, GroupDetection, ProbeVerdict, StructuralProfile,
};

fn profile() -> StructuralProfile {
    StructuralProfile::embedded().expect("embedded kb-ontology.yaml")
}

// ─── the explicit non-normative structural class ───────────────────────────

#[test]
fn non_normative_group_exists_and_is_text_only() {
    let profile = profile();
    let group = profile
        .group("non_normative")
        .expect("non_normative group is declared");
    assert!(group.text_only, "non_normative is text-only (ADR-0020)");
    assert!(
        group.ladder.is_empty(),
        "non_normative declares no normative ladder"
    );
    assert!(
        !group.needles.is_empty(),
        "non_normative must declare bank-wide needles"
    );
}

#[test]
fn non_normative_bank_wide_needles_are_declared() {
    // The bank-wide needles `courts/` and `fas/` are what cover practice whose
    // names carry no specific court_practice needle. Rank 40 is coarser than
    // the specific court_practice needles (rank 10-15).
    let profile = profile();
    let group = profile.group("non_normative").expect("non_normative");
    let needles: Vec<(&str, u32)> = group
        .needles
        .iter()
        .map(|needle| (needle.needle.as_str(), needle.rank))
        .collect();
    assert!(
        needles.contains(&("courts/", 40)),
        "expected courts/ rank 40, got {needles:?}"
    );
    assert!(
        needles.contains(&("fas/", 40)),
        "expected fas/ rank 40, got {needles:?}"
    );
    assert!(
        group.needles.iter().all(|needle| needle.field == "path"),
        "bank-wide needles are path needles"
    );
}

#[test]
fn court_practice_still_exists_and_is_text_only() {
    // The new class is additive: court_practice keeps its narrower needles and
    // its text-only declaration.
    let profile = profile();
    let group = profile
        .group("court_practice")
        .expect("court_practice still declared");
    assert!(group.text_only, "court_practice stays text-only");
    assert!(group.ladder.is_empty());
}

// ─── two-factor detection: text-only binds on the needle alone ─────────────

#[test]
fn detect_fas_determination_binds_non_normative_without_probe() {
    // `fas/determination_*` carries no specific court_practice needle — the
    // bank-wide `fas/` needle binds it, and being text-only the probe adds no
    // confirmatory signal (factor = Needle).
    let profile = profile();
    assert_eq!(
        profile.detect(Some("exports/fas/determination_2026.xml"), None, None, &[]),
        GroupDetection::Bound {
            group: "non_normative".to_owned(),
            factor: DetectionFactor::Needle,
        }
    );
}

#[test]
fn detect_courts_acn_binds_non_normative_without_probe() {
    // `courts/acn/*` likewise: only the bank-wide `courts/` needle matches.
    let profile = profile();
    assert_eq!(
        profile.detect(Some("exports/courts/acn/x.xml"), None, None, &[]),
        GroupDetection::Bound {
            group: "non_normative".to_owned(),
            factor: DetectionFactor::Needle,
        }
    );
}

#[test]
fn specific_court_practice_needle_wins_over_bank_wide_non_normative() {
    // Rank 40 (non_normative) is coarser than rank 12 (court_practice); the
    // specific needle must keep binding court_practice with no same-rank
    // Conflict.
    let profile = profile();
    assert_eq!(
        profile.detect(Some("exports/fas/decision_2025.xml"), None, None, &[]),
        GroupDetection::Bound {
            group: "court_practice".to_owned(),
            factor: DetectionFactor::Needle,
        }
    );
    assert_eq!(
        profile.detect(Some("exports/courts/court_2025.xml"), None, None, &[]),
        GroupDetection::Bound {
            group: "court_practice".to_owned(),
            factor: DetectionFactor::Needle,
        }
    );
}

#[test]
fn probe_non_normative_is_no_structure() {
    // Text-only profile: the probe is trivially NoStructure, so numbered lists
    // never mint a structural group (R8-05).
    let profile = profile();
    assert_eq!(
        profile.probe("non_normative", &[]),
        ProbeVerdict::NoStructure
    );
}
