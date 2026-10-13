//! Consultant URI anchor: first-class cross-system legal identity (ADR-0030 D1).
//!
//! The Consultant link surface provides exactly one cross-system legal-identity
//! anchor — the URI token family:
//!
//! - offline `consultantplus://offline/ref=…` — an **opaque token**. law-nexus
//!   cannot decode it (keying material lives in the external Consru project);
//!   the sanctioned join is an exact-token match against the catalog. The token
//!   is preserved **byte-exact**: never decoded, never re-derived, never
//!   normalized.
//! - internal `consultantplus-internal://<fld>/<key>#P<para>` — an open grammar
//!   that decomposes to `(bank, document_key, para)`. `<fld>` is **not** a
//!   constant (34646 / 35946 / 0xFFFF and others); `para == 4294967295` denotes
//!   the whole document.
//!
//! This module owns identity only. It mints no JSONL record schema (S02/T02),
//! performs no catalog join (S02/T03), and applies no pageindex resolution
//! (S03, after the edition timeline exists). `para == 4294967295` is retained
//! as an ordinary [`u64`] value: "whole document" is a *consumer*
//! interpretation, not a rewrite of the anchor.
//!
//! Every invalid anchor is returned as a closed typed refusal
//! ([`AnchorRefusal`]) rather than a silent success.

use std::error::Error;
use std::fmt;

/// Maximum characters retained in an [`AnchorRefusal`] detail.
///
/// Mirrors the bounded-detail discipline of
/// `crates/ln-consultant-parser/src/catalog.rs` so a refusal never carries an
/// unbounded payload.
const MAX_DETAIL_CHARS: usize = 240;

/// Offline anchor scheme prefix. Everything after `ref=` is opaque.
const OFFLINE_PREFIX: &str = "consultantplus://offline/ref=";
/// Internal anchor scheme prefix.
const INTERNAL_PREFIX: &str = "consultantplus-internal://";
/// Paragraph separator of the internal grammar.
const PARA_SEPARATOR: &str = "#P";

/// A parsed Consultant URI anchor.
///
/// On [`ConsultantUriAnchor::Offline`] the `token` field is the supplied bytes
/// unchanged. On [`ConsultantUriAnchor::Internal`] the `token` field is the
/// canonical reconstruction
/// `consultantplus-internal://<fld>/<key>#P<para>`; when the input was already
/// canonical it is byte-identical to it.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum ConsultantUriAnchor {
    /// `consultantplus://offline/ref=<opaque>` — byte-exact, never decoded.
    Offline {
        /// The full offline token, byte-for-byte as supplied (mixed case kept).
        token: String,
    },
    /// `consultantplus-internal://<fld>/<key>#P<para>` — open grammar.
    Internal {
        /// `<fld>` decimal bank field; **not** a constant.
        bank: String,
        /// `<key>` decimal document key within the bank.
        document_key: String,
        /// `<para>` paragraph number; `4294967295` means the whole document.
        para: u64,
        /// Canonical reconstruction of the anchor token.
        token: String,
    },
}

impl ConsultantUriAnchor {
    /// Parse a raw anchor string, fail-closed.
    ///
    /// Refusal order: [`AnchorRefusalKind::Empty`] → [`AnchorRefusalKind::NonAscii`]
    /// → offline parse → internal parse → [`AnchorRefusalKind::NotConsultantUri`].
    pub fn parse(raw: &str) -> Result<Self, AnchorRefusal> {
        if raw.is_empty() {
            return Err(AnchorRefusal::new(
                AnchorRefusalKind::Empty,
                "empty consultant uri anchor",
            ));
        }
        if !raw.is_ascii() {
            return Err(AnchorRefusal::new(
                AnchorRefusalKind::NonAscii,
                "consultant uri anchor is not ASCII",
            ));
        }
        if let Some(rest) = raw.strip_prefix(OFFLINE_PREFIX) {
            if rest.is_empty() || !rest.bytes().all(|b| b.is_ascii_alphanumeric()) {
                return Err(AnchorRefusal::new(
                    AnchorRefusalKind::NotConsultantUri,
                    "offline ref token is empty or not alphanumeric",
                ));
            }
            // Store the full original URI so `as_token` returns it byte-exact
            // and an exact-token join can match `editions.source_id` verbatim.
            return Ok(Self::Offline {
                token: raw.to_owned(),
            });
        }
        if let Some(rest) = raw.strip_prefix(INTERNAL_PREFIX) {
            return Self::parse_internal(rest);
        }
        Err(AnchorRefusal::new(
            AnchorRefusalKind::NotConsultantUri,
            "not a consultantplus uri anchor",
        ))
    }

    fn parse_internal(rest: &str) -> Result<Self, AnchorRefusal> {
        let malformed =
            |detail: &str| AnchorRefusal::new(AnchorRefusalKind::MalformedInternal, detail);
        let (bank, after_bank) = rest
            .split_once('/')
            .ok_or_else(|| malformed("internal anchor has no bank/key separator"))?;
        if bank.is_empty() || !bank.bytes().all(|b| b.is_ascii_digit()) {
            return Err(malformed("internal bank field is not decimal"));
        }
        let (document_key, after_key) = after_bank
            .split_once(PARA_SEPARATOR)
            .ok_or_else(|| malformed("internal anchor has no #P paragraph separator"))?;
        if document_key.is_empty() || !document_key.bytes().all(|b| b.is_ascii_digit()) {
            return Err(malformed("internal document key is not decimal"));
        }
        if after_key.is_empty() || !after_key.bytes().all(|b| b.is_ascii_digit()) {
            return Err(malformed("internal paragraph is not decimal"));
        }
        let para = after_key
            .parse::<u64>()
            .map_err(|_| malformed("internal paragraph overflows u64"))?;
        let token = format!("{INTERNAL_PREFIX}{bank}/{document_key}{PARA_SEPARATOR}{para}");
        Ok(Self::Internal {
            bank: bank.to_owned(),
            document_key: document_key.to_owned(),
            para,
            token,
        })
    }

    /// The anchor token as a borrowed string.
    ///
    /// For [`ConsultantUriAnchor::Offline`] this is the original supplied bytes
    /// unchanged (byte-exact). For [`ConsultantUriAnchor::Internal`] this is the
    /// canonical reconstruction from the parsed components.
    pub fn as_token(&self) -> &str {
        match self {
            Self::Offline { token } => token,
            Self::Internal { token, .. } => token,
        }
    }

    /// Owned form of [`Self::as_token`].
    pub fn token_string(&self) -> String {
        self.as_token().to_owned()
    }
}

/// Closed refusal vocabulary of the anchor parser.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AnchorRefusalKind {
    /// The raw anchor string was empty.
    Empty,
    /// The string is not a `consultantplus://` anchor of a known form.
    NotConsultantUri,
    /// The string contains a non-ASCII byte.
    NonAscii,
    /// The string matched the internal scheme but violated its grammar.
    MalformedInternal,
}

impl AnchorRefusalKind {
    /// Stable machine-readable identifier of the refusal kind.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Empty => "empty",
            Self::NotConsultantUri => "not_consultant_uri",
            Self::NonAscii => "non_ascii",
            Self::MalformedInternal => "malformed_internal",
        }
    }
}

/// A typed, bounded anchor parse refusal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnchorRefusal {
    kind: AnchorRefusalKind,
    detail: String,
}

impl AnchorRefusal {
    /// Build a refusal, bounding the detail to [`MAX_DETAIL_CHARS`] characters
    /// and dropping control characters.
    pub fn new(kind: AnchorRefusalKind, detail: impl Into<String>) -> Self {
        Self {
            kind,
            detail: bound_detail(detail.into()),
        }
    }

    /// The refusal kind.
    pub fn kind(&self) -> AnchorRefusalKind {
        self.kind
    }

    /// The bounded human-readable detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for AnchorRefusal {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "consultant uri anchor refused ({}): {}",
            self.kind.as_str(),
            self.detail
        )
    }
}

impl Error for AnchorRefusal {}

/// Resolution status of an anchor against the catalog (S02/T03 join outcome).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AnchorStatus {
    /// The anchor resolved to a catalog entry (exact-token match).
    Anchored,
    /// The anchor is well-formed but absent from the catalog.
    UnresolvedNotInCatalog,
}

impl AnchorStatus {
    /// Stable machine-readable identifier of the status.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Anchored => "anchored",
            Self::UnresolvedNotInCatalog => "anchor_unresolved",
        }
    }
}

impl fmt::Display for AnchorStatus {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

fn bound_detail(raw: String) -> String {
    let mut out = String::new();
    for ch in raw.chars() {
        if ch.is_control() {
            continue;
        }
        if out.chars().count() >= MAX_DETAIL_CHARS {
            break;
        }
        out.push(ch);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn offline_token_survives_byte_exact() {
        let raw = "consultantplus://offline/ref=235B1A968E4D59A97657E85BD86F6A71B8663B3F47605928A0B816F3C818983C064F496A1349154AB2FDE3A7CC220A36DABFB0FC2Ea4RCK";
        let anchor = ConsultantUriAnchor::parse(raw).expect("valid offline anchor");
        assert_eq!(anchor.as_token().as_bytes(), raw.as_bytes());
        assert_eq!(anchor.token_string(), raw);
        assert!(matches!(anchor, ConsultantUriAnchor::Offline { .. }));
    }

    #[test]
    fn internal_anchor_decomposes_and_reconstructs() {
        let anchor = ConsultantUriAnchor::parse("consultantplus-internal://134/12345#P7")
            .expect("valid internal anchor");
        match anchor {
            ConsultantUriAnchor::Internal {
                ref bank,
                ref document_key,
                para,
                ref token,
            } => {
                assert_eq!(bank, "134");
                assert_eq!(document_key, "12345");
                assert_eq!(para, 7);
                assert_eq!(token, "consultantplus-internal://134/12345#P7");
            }
            _ => panic!("expected internal anchor"),
        }
        assert_eq!(anchor.as_token(), "consultantplus-internal://134/12345#P7");
    }

    #[test]
    fn whole_document_para_is_plain_u64() {
        let anchor = ConsultantUriAnchor::parse("consultantplus-internal://134/12345#P4294967295")
            .expect("valid whole-document anchor");
        match anchor {
            ConsultantUriAnchor::Internal { para, .. } => assert_eq!(para, 4294967295),
            _ => panic!("expected internal anchor"),
        }
    }

    #[test]
    fn fld_fields_are_not_a_constant() {
        for fld in ["34646", "35946", "65535"] {
            let raw = format!("consultantplus-internal://{fld}/777#P1");
            let anchor = ConsultantUriAnchor::parse(&raw).expect("valid internal anchor");
            assert_eq!(anchor.as_token(), raw);
        }
    }

    #[test]
    fn anchor_status_strings_are_stable() {
        assert_eq!(AnchorStatus::Anchored.as_str(), "anchored");
        assert_eq!(
            AnchorStatus::UnresolvedNotInCatalog.as_str(),
            "anchor_unresolved"
        );
    }
}
