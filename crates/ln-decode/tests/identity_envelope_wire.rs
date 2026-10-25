//! Wire suite for the identity envelope (M224/S02/T03, ADR-0030 D1).
//!
//! Proves that a Consultant URI anchor survives render → read-back
//! **byte-for-byte**, that an unresolved document is a closed counted class,
//! and that a re-encoded, escaped, truncated or doubly-anchored token is
//! refused with a closed [`EnvelopeRefusalKind`] rather than normalized
//! silently.

use ln_decode::consultant_uri_anchor::ConsultantUriAnchor;
use ln_decode::identity_envelope::{
    EnvelopeRefusalKind, IDENTITY_ENVELOPE_SCHEMA, IdentityEnvelope,
};

/// A real offline token: uppercase hex body with a mixed-case tail (`a4RCK`).
const OFFLINE_TOKEN: &str = "consultantplus://offline/ref=235B1A968E4D59A97657E85BD86F6A71B8663B3F47605928A0B816F3C818983C064F496A1349154AB2FDE3A7CC220A36DABFB0FC2Ea4RCK";
const INTERNAL_TOKEN: &str = "consultantplus-internal://134/12345#P4294967295";
const SHA: &str = "sha256:0000000000000000000000000000000000000000000000000000000000000000";

fn anchor(token: &str) -> ConsultantUriAnchor {
    ConsultantUriAnchor::parse(token).expect("valid anchor fixture")
}

fn read_back_kind(line: &str) -> EnvelopeRefusalKind {
    IdentityEnvelope::read_back(line)
        .err()
        .unwrap_or_else(|| panic!("expected refusal for {line:?}"))
        .kind()
}

// ------------------------------------------------------ byte-exact survival #

#[test]
fn offline_envelope_renders_and_reads_back_byte_exact() {
    let envelope = IdentityEnvelope::anchored("npa/x.xml", SHA, 42, anchor(OFFLINE_TOKEN));
    let line = envelope.render_jsonl_line();

    assert!(line.ends_with('\n'), "one line, newline-terminated");
    assert_eq!(line.matches('\n').count(), 1, "compact single-line record");
    assert!(line.starts_with(&format!("{{\"schema\":\"{IDENTITY_ENVELOPE_SCHEMA}\"")));

    let read = IdentityEnvelope::byte_exact_round_trip(&line).expect("canonical round trip");
    assert_eq!(read, envelope);
    let carried = read.anchor.as_ref().expect("anchored").as_token();
    assert_eq!(carried.as_bytes(), OFFLINE_TOKEN.as_bytes());
    assert_eq!(read.verify_byte_exact(OFFLINE_TOKEN), Ok(()));
}

#[test]
fn internal_whole_document_envelope_round_trips() {
    let envelope = IdentityEnvelope::anchored("fas/y.xml", SHA, 7, anchor(INTERNAL_TOKEN));
    let line = envelope.render_jsonl_line();
    let read = IdentityEnvelope::byte_exact_round_trip(&line).expect("canonical round trip");
    assert_eq!(
        read.anchor.as_ref().expect("anchored").as_token(),
        INTERNAL_TOKEN
    );
    // Whole-document para is a plain value, never rewritten.
    match read.anchor {
        Some(ConsultantUriAnchor::Internal { para, .. }) => assert_eq!(para, 4294967295),
        other => panic!("expected internal anchor, got {other:?}"),
    }
}

#[test]
fn render_is_deterministic() {
    let envelope = IdentityEnvelope::anchored("npa/x.xml", SHA, 42, anchor(OFFLINE_TOKEN));
    assert_eq!(envelope.render_jsonl_line(), envelope.render_jsonl_line());
}

// ------------------------------------------------------- unresolved class #

#[test]
fn unresolved_envelope_carries_status_not_token() {
    let envelope = IdentityEnvelope::unresolved("xml/z.xml", SHA, 3);
    assert_eq!(envelope.anchor_status(), "anchor_unresolved");
    let line = envelope.render_jsonl_line();
    assert!(line.contains("\"anchor_status\":\"anchor_unresolved\""));
    assert!(
        !line.contains("consultant_uri"),
        "no token field on an unresolved line"
    );

    let read = IdentityEnvelope::byte_exact_round_trip(&line).expect("canonical round trip");
    assert_eq!(read, envelope);
    assert!(read.anchor.is_none());
    assert_eq!(read.anchor_status(), "anchor_unresolved");
    // No token to verify: an unresolved envelope cannot claim byte-exactness.
    assert_eq!(
        read.verify_byte_exact(OFFLINE_TOKEN),
        Err(ln_decode::identity_envelope::EnvelopeRefusal::new(
            EnvelopeRefusalKind::MissingAnchorFields,
            "envelope carries no consultant_uri to verify",
        ))
    );
}

// ----------------------------------------------------------- hostile input #

#[test]
fn reencoded_token_is_not_byte_exact() {
    let envelope = IdentityEnvelope::anchored("npa/x.xml", SHA, 42, anchor(OFFLINE_TOKEN));
    // `%3A` instead of `:` — same reader, different bytes.
    let reencoded = OFFLINE_TOKEN.replacen(':', "%3A", 1);
    assert_ne!(reencoded, OFFLINE_TOKEN);
    let refusal = envelope
        .verify_byte_exact(&reencoded)
        .expect_err("re-encoded token must be refused");
    assert_eq!(refusal.kind(), EnvelopeRefusalKind::TokenMismatch);
}

#[test]
fn escaped_unicode_token_is_not_silently_normalized() {
    let envelope = IdentityEnvelope::anchored("npa/x.xml", SHA, 42, anchor(OFFLINE_TOKEN));
    let canonical = envelope.render_jsonl_line();
    // Replace the literal `:` with a JSON `\u003a` escape: a parser that
    // decoded it would silently recover the original token. The canonical-form
    // gate refuses the line instead.
    let hostile = canonical.replace("consultantplus:", "consultantplus\\u003a");
    assert_ne!(hostile, canonical);
    assert_eq!(read_back_kind(&hostile), EnvelopeRefusalKind::TokenMismatch);
}

#[test]
fn truncated_token_is_not_byte_exact() {
    let envelope = IdentityEnvelope::anchored("npa/x.xml", SHA, 42, anchor(OFFLINE_TOKEN));
    let truncated = &OFFLINE_TOKEN[..OFFLINE_TOKEN.len() - 1];
    let refusal = envelope
        .verify_byte_exact(truncated)
        .expect_err("truncated token must be refused");
    assert_eq!(refusal.kind(), EnvelopeRefusalKind::TokenMismatch);
}

#[test]
fn both_anchor_and_status_is_refused() {
    let envelope = IdentityEnvelope::anchored("npa/x.xml", SHA, 42, anchor(OFFLINE_TOKEN));
    let body = envelope.render_jsonl_line();
    // Insert a second anchor field *inside* the object (strip the close brace
    // first), producing a genuinely doubly-anchored envelope.
    let inner = body
        .trim_end_matches('\n')
        .strip_suffix('}')
        .expect("close brace");
    let hostile = format!("{inner},\"anchor_status\":\"anchor_unresolved\"}}");
    assert_eq!(
        read_back_kind(&hostile),
        EnvelopeRefusalKind::BothAnchorAndStatus
    );
}

#[test]
fn non_ascii_payload_is_refused() {
    let envelope = IdentityEnvelope::unresolved("xml/z.xml", SHA, 3);
    let hostile = envelope
        .render_jsonl_line()
        .replace("xml/z.xml", "xml/ф.xml");
    assert_eq!(read_back_kind(&hostile), EnvelopeRefusalKind::NonAscii);
}

#[test]
fn missing_anchor_fields_is_refused() {
    let line = format!(
        "{{\"schema\":\"{IDENTITY_ENVELOPE_SCHEMA}\",\"relative_path\":\"x.xml\",\"source\":{{\"sha256\":\"{SHA}\",\"bytes\":5}},\"note\":\"x\"}}"
    );
    assert_eq!(
        read_back_kind(&line),
        EnvelopeRefusalKind::MissingAnchorFields
    );
}

#[test]
fn malformed_line_is_refused() {
    assert_eq!(read_back_kind("not json"), EnvelopeRefusalKind::Malformed);
    assert_eq!(
        read_back_kind("{\"schema\":\"wrong/v1\"}"),
        EnvelopeRefusalKind::Malformed
    );
}

// -------------------------------------------------------- redaction guard #

#[test]
fn rendered_payload_is_ascii_and_redacted() {
    let anchored = IdentityEnvelope::anchored("npa/x.xml", SHA, 42, anchor(OFFLINE_TOKEN));
    let unresolved = IdentityEnvelope::unresolved("xml/z.xml", SHA, 3);
    for line in [anchored.render_jsonl_line(), unresolved.render_jsonl_line()] {
        assert!(line.is_ascii(), "identity envelope payload must be ASCII");
        assert!(
            line.bytes().all(|b| b < 0x80),
            "no escaped/decoded corpus text may leak"
        );
    }
    // The anchor token is present verbatim, not decoded into corpus prose.
    assert!(anchored.render_jsonl_line().contains(OFFLINE_TOKEN));
}
