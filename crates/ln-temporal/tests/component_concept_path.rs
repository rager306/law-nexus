//! ComponentConceptId path segments (D191 / review R8-11).
//!
//! `cc:work:statya-93/punkt-4/punkt-4.2` must parse; the slash is allowed
//! only for ComponentConceptId. Other id_type! parsers (CtvId, AmendingActId,
//! IndustrialOpId) keep rejecting slash. MAX_ID_LEN stays 64; empty path
//! segments are IdError (fail-closed, no silent normalization).

use ln_temporal::domain::{AmendingActId, ComponentConceptId, CtvId, IdError, IndustrialOpId};

fn cc(id: &str) -> Result<ComponentConceptId, IdError> {
    ComponentConceptId::parse(id)
}

#[test]
fn deep_path_cc_parses() {
    let parsed = cc("cc:work:statya-93/punkt-4/punkt-4.2").expect("deep path");
    assert_eq!(parsed.as_str(), "cc:work:statya-93/punkt-4/punkt-4.2");
}

#[test]
fn flat_cc_still_parses() {
    // Backward compatibility: existing flat CCs (D191 keeps the charset).
    let parsed = cc("cc:44fz:art-93").expect("flat");
    assert_eq!(parsed.as_str(), "cc:44fz:art-93");
    let parsed = cc("cc:435fz:statya-1").expect("flat fixture");
    assert_eq!(parsed.as_str(), "cc:435fz:statya-1");
}

#[test]
fn two_level_path_parses() {
    let parsed = cc("cc:work:statya-93/punkt-4").expect("two levels");
    assert_eq!(parsed.as_str(), "cc:work:statya-93/punkt-4");
}

#[test]
fn double_slash_is_rejected() {
    let err = cc("cc:work:statya-93//punkt-4").expect_err("double slash");
    assert!(err.to_string().contains("empty path segment"));
}

#[test]
fn leading_slash_is_rejected() {
    let err = cc("/cc:work:statya-93").expect_err("leading slash");
    assert!(err.to_string().contains("empty path segment"));
}

#[test]
fn trailing_slash_is_rejected() {
    let err = cc("cc:work:statya-93/punkt-4/").expect_err("trailing slash");
    assert!(err.to_string().contains("empty path segment"));
}

#[test]
fn too_long_path_is_rejected() {
    // MAX_ID_LEN stays 64 (D191); deeper paths quarantine, no charset widening.
    let long =
        "cc:work:statya-93/punkt-4/punkt-4.1.2.3.4.5.6.7.8.9.10.11.12.13.14.15.16.17.18".to_owned();
    assert!(
        long.len() > 64,
        "fixture must exceed 64: len={}",
        long.len()
    );
    let err = cc(&long).expect_err("too long");
    assert!(err.to_string().contains("too long"));
}

#[test]
fn empty_is_rejected() {
    assert!(cc("").is_err());
}

#[test]
fn non_ascii_is_rejected() {
    let err = cc("cc:work:статья-1").expect_err("cyrillic");
    assert!(err.to_string().contains("unsupported character"));
}

#[test]
fn space_is_rejected() {
    let err = cc("cc:work:statya-93 punkt-4").expect_err("space");
    assert!(err.to_string().contains("unsupported character"));
}

#[test]
fn other_id_types_still_reject_slash() {
    // D191: slash only in the dedicated ComponentConceptId parse.
    assert!(CtvId::parse("cc:work:a/b").is_err());
    assert!(AmendingActId::parse("cc:work:a/b").is_err());
    assert!(IndustrialOpId::parse("cc:work:a/b").is_err());
    // And they still accept flat values.
    assert!(CtvId::parse("ctv:work:statya-93").is_ok());
}

#[test]
fn path_roundtrip_preserves_segments() {
    let path = "cc:work:statya-93/punkt-4/punkt-4.2";
    let parsed = cc(path).expect("parse");
    assert_eq!(parsed.as_str(), path);
    assert_eq!(parsed, ComponentConceptId::parse(path).expect("reparse"));
}
