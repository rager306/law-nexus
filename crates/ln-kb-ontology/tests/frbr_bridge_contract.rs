//! T01 contract: pure FRBR-ELI bridge over the embedded `works:` registry.
//!
//! Hermetic (no gitignored corpus): the 44-ФЗ / 402-ФЗ points come from the
//! compiled-in registry via `include_str!` inside `ln-kb-ontology::registry`.
//! The suite proves Work identity + Expression ELI form byte-exact and that
//! every refusal branch really returns an error (non-vacuous negatives).

use ln_kb_ontology::frbr_bridge::{
    FRBR_BRIDGE_NON_CLAIMS, FrbrBridgeRefusal, render_pair_ascii, resolve_frbr_pair,
    resolve_frbr_pair_iso,
};

const WORK_44FZ: &str = "work:ru:federal:zakon:2013-04-05:44-fz";
const ELI_44FZ: &str = "urn:lex:ru:federal:zakon:2013-04-05;44-fz";
const ORDINAL_ENACTMENT_44FZ: i64 = 77891; // 2013-04-05
const ORDINAL_EDITION_118: i64 = 82726; // 2026-07-01

const WORK_402FZ: &str = "work:ru:federal:zakon:2011-12-06:402-fz";
const ELI_402FZ: &str = "urn:lex:ru:federal:zakon:2011-12-06;402-fz";
const ORDINAL_ENACTMENT_402FZ: i64 = 77405; // 2011-12-06

#[test]
fn corpus_points_resolve_byte_exact() {
    let pair = resolve_frbr_pair("44-fz", ORDINAL_ENACTMENT_44FZ).expect("44-fz enactment");
    assert_eq!(pair.work_id, WORK_44FZ);
    assert_eq!(pair.work_eli_urn, ELI_44FZ);
    assert_eq!(pair.effect_iso, "2013-04-05");
    assert_eq!(
        pair.expression_id,
        "expr:ru:federal:zakon:2013-04-05:44-fz:2013-04-05"
    );
    assert_eq!(
        pair.expression_eli_urn,
        "urn:lex:ru:federal:zakon:2013-04-05;44-fz@2013-04-05"
    );

    // Both ELI strings are byte-exact (non-vacuous: not merely non-empty).
    assert!(!pair.work_eli_urn.is_empty());
    assert_eq!(
        pair.expression_eli_urn,
        format!("{}@{}", pair.work_eli_urn, pair.effect_iso)
    );

    // Second dated edition of the same Work: ordinal 82726 -> @2026-07-01.
    let edition = resolve_frbr_pair("44-fz", ORDINAL_EDITION_118).expect("44-fz edition 118");
    assert_eq!(edition.work_id, WORK_44FZ);
    assert_eq!(edition.effect_iso, "2026-07-01");
    assert_eq!(edition.expression_eli_urn, format!("{ELI_44FZ}@2026-07-01"));
    assert_ne!(pair.expression_eli_urn, edition.expression_eli_urn);
}

#[test]
fn second_act_402fz_is_grounded() {
    let pair = resolve_frbr_pair("402-fz", ORDINAL_ENACTMENT_402FZ).expect("402-fz enactment");
    assert_eq!(pair.work_id, WORK_402FZ);
    assert_eq!(pair.work_eli_urn, ELI_402FZ);
    assert_eq!(pair.effect_iso, "2011-12-06");
    assert_eq!(pair.expression_eli_urn, format!("{ELI_402FZ}@2011-12-06"));
}

#[test]
fn unknown_act_refuses() {
    assert_eq!(
        resolve_frbr_pair("999-fz", ORDINAL_ENACTMENT_44FZ),
        Err(FrbrBridgeRefusal::UnknownAct)
    );
    // A Cyrillic act number is rejected by the registry lookup (no catalogue
    // `number` column fallback), never silently grounded.
    assert_eq!(
        resolve_frbr_pair("44-ФЗ", ORDINAL_ENACTMENT_44FZ),
        Err(FrbrBridgeRefusal::UnknownAct)
    );
}

#[test]
fn ordinal_out_of_bounds_refuses() {
    // Boundary legitimacy first: 0 -> 1800-01-01 (min year) resolves.
    let low = resolve_frbr_pair("44-fz", 0).expect("min bound ordinal");
    assert_eq!(low.effect_iso, "1800-01-01");
    let high = resolve_frbr_pair("44-fz", 109_937).expect("max bound ordinal");
    assert_eq!(high.effect_iso, "2100-12-31");

    // Outside 1800..2100 -> refusal, not an empty success.
    assert_eq!(
        resolve_frbr_pair("44-fz", -1),
        Err(FrbrBridgeRefusal::InvalidOrdinal)
    );
    assert_eq!(
        resolve_frbr_pair("44-fz", 109_938),
        Err(FrbrBridgeRefusal::InvalidOrdinal)
    );
}

#[test]
fn invalid_iso_refuses() {
    assert_eq!(
        resolve_frbr_pair_iso("44-fz", "2013-13-45"),
        Err(FrbrBridgeRefusal::InvalidEffectDay)
    );
    assert_eq!(
        resolve_frbr_pair_iso("44-fz", "not-a-date"),
        Err(FrbrBridgeRefusal::InvalidEffectDay)
    );
    // Unknown act is checked before the ISO on this entry point too.
    assert_eq!(
        resolve_frbr_pair_iso("999-fz", "2013-04-05"),
        Err(FrbrBridgeRefusal::UnknownAct)
    );
    // Valid ISO path stays byte-identical to the ordinal path.
    let via_iso = resolve_frbr_pair_iso("44-fz", "2013-04-05").expect("iso path");
    let via_ordinal = resolve_frbr_pair("44-fz", ORDINAL_ENACTMENT_44FZ).expect("ordinal path");
    assert_eq!(via_iso, via_ordinal);
}

#[test]
fn render_is_deterministic() {
    let first = render_pair_ascii(&resolve_frbr_pair("44-fz", ORDINAL_EDITION_118).expect("pair"));
    let second = render_pair_ascii(&resolve_frbr_pair("44-fz", ORDINAL_EDITION_118).expect("pair"));
    assert_eq!(first, second);
    assert!(first.contains(ELI_44FZ));
    assert!(first.contains("@2026-07-01"));
    assert!(first.is_ascii());
}

#[test]
fn non_claims_are_pinned() {
    assert!(FRBR_BRIDGE_NON_CLAIMS.len() >= 5);
    assert!(
        FRBR_BRIDGE_NON_CLAIMS
            .contains(&"eli_urn_is_a_compatibility_projection_not_project_local_canon")
    );
    assert!(
        FRBR_BRIDGE_NON_CLAIMS
            .contains(&"expression_day_is_the_timeline_effect_day_not_the_registry_rev_date")
    );
    assert_eq!(FrbrBridgeRefusal::UnknownAct.as_str(), "unknown_act");
    assert_eq!(
        FrbrBridgeRefusal::InvalidOrdinal.as_str(),
        "invalid_ordinal"
    );
}
