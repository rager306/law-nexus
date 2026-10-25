//! Contract suite for the Consultant URI anchor (M224/S02/T01, ADR-0030 D1).
//!
//! Asserts the byte-exact survival of an offline token, the open internal
//! grammar, and the closed typed-refusal vocabulary. No decoding, no
//! normalization, no silent success.

use ln_decode::consultant_uri_anchor::{
    AnchorRefusal, AnchorRefusalKind, AnchorStatus, ConsultantUriAnchor,
};

/// A real offline token: uppercase hex body with a mixed-case tail (`a4RCK`).
const OFFLINE_TOKEN: &str = "consultantplus://offline/ref=235B1A968E4D59A97657E85BD86F6A71B8663B3F47605928A0B816F3C818983C064F496A1349154AB2FDE3A7CC220A36DABFB0FC2Ea4RCK";

fn refusal_kind(raw: &str) -> AnchorRefusalKind {
    ConsultantUriAnchor::parse(raw)
        .err()
        .unwrap_or_else(|| panic!("expected refusal for {raw:?}"))
        .kind()
}

// --------------------------------------------------------------- offline #

#[test]
fn offline_token_is_preserved_byte_exact() {
    let anchor = ConsultantUriAnchor::parse(OFFLINE_TOKEN).expect("valid offline anchor");
    match anchor {
        ConsultantUriAnchor::Offline { ref token } => {
            assert_eq!(token.as_bytes(), OFFLINE_TOKEN.as_bytes());
        }
        _ => panic!("expected offline anchor"),
    }
    // `as_token` borrows the original bytes; `token_string` clones them.
    assert_eq!(anchor.as_token().as_bytes(), OFFLINE_TOKEN.as_bytes());
    assert_eq!(anchor.token_string(), OFFLINE_TOKEN);
    assert_eq!(anchor.as_token().len(), OFFLINE_TOKEN.len());
}

#[test]
fn offline_token_mixed_case_is_not_normalized() {
    let upper = "consultantplus://offline/ref=ABCDEF";
    let mixed = "consultantplus://offline/ref=AbCdEf";
    assert_ne!(
        ConsultantUriAnchor::parse(upper).unwrap().as_token(),
        ConsultantUriAnchor::parse(mixed).unwrap().as_token()
    );
    assert_eq!(
        ConsultantUriAnchor::parse(mixed).unwrap().as_token(),
        "consultantplus://offline/ref=AbCdEf"
    );
}

#[test]
fn offline_ref_does_not_fall_through_to_internal() {
    let anchor = ConsultantUriAnchor::parse(OFFLINE_TOKEN).unwrap();
    assert!(matches!(anchor, ConsultantUriAnchor::Offline { .. }));
}

// -------------------------------------------------------------- internal #

#[test]
fn internal_anchor_decomposes_into_components() {
    let raw = "consultantplus-internal://134/12345#P7";
    let anchor = ConsultantUriAnchor::parse(raw).expect("valid internal anchor");
    match anchor {
        ConsultantUriAnchor::Internal {
            ref bank,
            ref document_key,
            para,
            ..
        } => {
            assert_eq!(bank, "134");
            assert_eq!(document_key, "12345");
            assert_eq!(para, 7);
        }
        _ => panic!("expected internal anchor"),
    }
    assert_eq!(anchor.as_token(), raw);
    assert_eq!(anchor.token_string(), raw);
}

#[test]
fn whole_document_para_is_a_plain_u64() {
    let raw = "consultantplus-internal://134/12345#P4294967295";
    let anchor = ConsultantUriAnchor::parse(raw).expect("valid whole-document anchor");
    match anchor {
        ConsultantUriAnchor::Internal { para, .. } => assert_eq!(para, 4294967295),
        _ => panic!("expected internal anchor"),
    }
    assert_eq!(anchor.as_token(), raw);
}

#[test]
fn fld_field_is_not_a_constant() {
    for fld in ["34646", "35946", "65535"] {
        let raw = format!("consultantplus-internal://{fld}/777#P1");
        let anchor = ConsultantUriAnchor::parse(&raw).expect("valid internal anchor");
        match anchor {
            ConsultantUriAnchor::Internal { ref bank, .. } => assert_eq!(bank, &fld),
            _ => panic!("expected internal anchor"),
        }
        assert_eq!(anchor.as_token(), raw);
    }
}

#[test]
fn zero_key_and_zero_para_parse() {
    let raw = "consultantplus-internal://134/0#P1";
    let anchor = ConsultantUriAnchor::parse(raw).expect("valid internal anchor");
    match anchor {
        ConsultantUriAnchor::Internal {
            ref document_key,
            para,
            ..
        } => {
            assert_eq!(document_key, "0");
            assert_eq!(para, 1);
        }
        _ => panic!("expected internal anchor"),
    }
}

// --------------------------------------------------------------- refusals #

#[test]
fn empty_anchor_is_refused() {
    assert_eq!(refusal_kind(""), AnchorRefusalKind::Empty);
}

#[test]
fn non_consultant_uri_is_refused() {
    for raw in [
        "http://x",
        "consultantplus://other/ref=x",
        "consultantplus://offline/",
        "consultantplus://offline/ref=",
        "consultantplus://offline/ref=x y",
        "consultantplus://offline/ref=ab-cd",
        "consultantplus://offline/ref=abc\n",
        "consultant-internal://134/1#P1",
    ] {
        assert_eq!(
            refusal_kind(raw),
            AnchorRefusalKind::NotConsultantUri,
            "raw={raw:?}"
        );
    }
}

#[test]
fn non_ascii_is_refused() {
    for raw in [
        "консультант",
        "consultantplus://offline/ref=АБВ",
        "consultantplus-internal://134/1#P7é",
    ] {
        assert_eq!(
            refusal_kind(raw),
            AnchorRefusalKind::NonAscii,
            "raw={raw:?}"
        );
    }
}

#[test]
fn malformed_internal_is_refused() {
    for raw in [
        // no `#P`
        "consultantplus-internal://134/12345",
        // missing key
        "consultantplus-internal://134#P7",
        // missing bank/key separator
        "consultantplus-internal://",
        // empty key
        "consultantplus-internal://134/#P7",
        // empty paragraph
        "consultantplus-internal://134/12345#P",
        // non-numeric paragraph
        "consultantplus-internal://134/12345#Pnotanumber",
        // trailing garbage after paragraph
        "consultantplus-internal://134/12345#P7extra",
        // negative paragraph
        "consultantplus-internal://134/12345#P-1",
        // lowercase separator
        "consultantplus-internal://134/12345#p7",
        // non-numeric bank
        "consultantplus-internal://abc/12345#P7",
        // non-numeric key
        "consultantplus-internal://134/abc#P7",
        // extra path segment
        "consultantplus-internal://134/12/34#P7",
        // paragraph overflow beyond u64
        "consultantplus-internal://134/12345#P99999999999999999999999999",
    ] {
        assert_eq!(
            refusal_kind(raw),
            AnchorRefusalKind::MalformedInternal,
            "raw={raw:?}"
        );
    }
}

#[test]
fn refusals_do_not_panic_and_carry_bounded_detail() {
    let refusal = ConsultantUriAnchor::parse("consultantplus-internal://134/1#Px").unwrap_err();
    assert_eq!(refusal.kind(), AnchorRefusalKind::MalformedInternal);
    assert!(!refusal.detail().is_empty());
    // Display + Error are implemented.
    let rendered = format!("{refusal}");
    assert!(rendered.contains("malformed_internal"));
    let _: &dyn std::error::Error = &refusal;

    let long = "x".repeat(10_000);
    let bounded = AnchorRefusal::new(AnchorRefusalKind::NotConsultantUri, long);
    assert!(bounded.detail().chars().count() <= 240);
}

// ---------------------------------------------------------------- status #

#[test]
fn anchor_status_strings_are_stable() {
    assert_eq!(AnchorStatus::Anchored.as_str(), "anchored");
    assert_eq!(
        AnchorStatus::UnresolvedNotInCatalog.as_str(),
        "anchor_unresolved"
    );
}
