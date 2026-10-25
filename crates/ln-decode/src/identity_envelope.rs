//! Identity envelope JSONL wire: the Consultant URI anchor travels byte-exact
//! alongside the per-document integrity identity (M224/S02/T03, ADR-0030 D1,
//! DP1/D742).
//!
//! Every corpus document gets exactly one identity envelope line. The envelope
//! pins the structural identity (`relative_path` + `source.sha256` +
//! `source.bytes`) and carries the Consultant URI anchor as a first-class legal
//! identity. The anchor is emitted **verbatim** and must survive every
//! transformation byte-for-byte — the same discipline as
//! `assert_no_raw_text`, scoped to the opaque token.
//!
//! Exactly one of two anchor shapes is present:
//!
//! - `consultant_uri` — a well-formed anchor (offline opaque token or internal
//!   grammar), preserved byte-exact;
//! - `anchor_status` — the closed class `anchor_unresolved` for a document the
//!   catalog cannot resolve (honest, counted, never a silent skip).
//!
//! `render_jsonl_line` → `read_back` is the wire; `byte_exact_round_trip`
//! additionally proves the line is in canonical form, and
//! `verify_byte_exact` compares the carried token against a known source token
//! by raw bytes. A re-encoded, escaped, truncated or otherwise non-canonical
//! token is refused with a closed [`EnvelopeRefusalKind`] — never normalized
//! silently. Stdlib only: this module mints no serde schema and performs no
//! catalog join (S02/T04 does the join and coverage accounting).

use std::error::Error;
use std::fmt;
use std::fmt::Write as _;

use crate::consultant_uri_anchor::{AnchorStatus, ConsultantUriAnchor};

/// Closed JSONL schema id of an identity envelope line.
pub const IDENTITY_ENVELOPE_SCHEMA: &str = "m224-s02-identity-envelope/v1";

/// Maximum characters retained in an [`EnvelopeRefusal`] detail. Mirrors the
/// bounded-detail discipline of `consultant_uri_anchor`.
const MAX_DETAIL_CHARS: usize = 240;

/// The single closed `anchor_status` token this schema admits.
const ANCHOR_UNRESOLVED: &str = "anchor_unresolved";

/// One document identity envelope.
///
/// The invariant is structural: `anchor: Some(_)` renders as `consultant_uri`
/// and `anchor: None` renders as `anchor_status == "anchor_unresolved"`, so a
/// rendered line always carries **exactly one** anchor field.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityEnvelope {
    /// Corpus-relative path (manifest key), `/`-joined.
    pub relative_path: String,
    /// `sha256:<64 lowercase hex>` over the raw document bytes.
    pub source_sha256: String,
    /// Raw document byte length.
    pub source_bytes: u64,
    /// The Consultant URI anchor, or `None` for the unresolved class.
    pub anchor: Option<ConsultantUriAnchor>,
}

impl IdentityEnvelope {
    /// Construct an anchored envelope.
    pub fn anchored(
        relative_path: impl Into<String>,
        source_sha256: impl Into<String>,
        source_bytes: u64,
        anchor: ConsultantUriAnchor,
    ) -> Self {
        Self {
            relative_path: relative_path.into(),
            source_sha256: source_sha256.into(),
            source_bytes,
            anchor: Some(anchor),
        }
    }

    /// Construct an unresolved envelope (`anchor_status == "anchor_unresolved"`).
    pub fn unresolved(
        relative_path: impl Into<String>,
        source_sha256: impl Into<String>,
        source_bytes: u64,
    ) -> Self {
        Self {
            relative_path: relative_path.into(),
            source_sha256: source_sha256.into(),
            source_bytes,
            anchor: None,
        }
    }

    /// The closed anchor-status string of this envelope: either the resolved
    /// class of the carried anchor, or [`AnchorStatus::UnresolvedNotInCatalog`].
    pub fn anchor_status(&self) -> &'static str {
        match self.anchor {
            Some(_) => AnchorStatus::Anchored.as_str(),
            None => AnchorStatus::UnresolvedNotInCatalog.as_str(),
        }
    }

    /// Render the canonical single-line JSON record, terminated by `\n`.
    ///
    /// Key order is fixed: `schema`, `relative_path`, `source{sha256,bytes}`,
    /// then `consultant_uri` **or** `anchor_status`. The anchor token is written
    /// verbatim (never decoded, never normalized).
    pub fn render_jsonl_line(&self) -> String {
        let mut out = self.render_body();
        out.push('\n');
        out
    }

    /// Canonical body without the trailing newline (used for form comparison).
    fn render_body(&self) -> String {
        let mut out = String::with_capacity(self.relative_path.len() + 192);
        out.push_str("{\"schema\":");
        out.push_str(&quote(IDENTITY_ENVELOPE_SCHEMA));
        out.push_str(",\"relative_path\":");
        out.push_str(&quote(&self.relative_path));
        out.push_str(",\"source\":{\"sha256\":");
        out.push_str(&quote(&self.source_sha256));
        out.push_str(",\"bytes\":");
        let _ = write!(out, "{}", self.source_bytes);
        out.push('}');
        match &self.anchor {
            Some(anchor) => {
                out.push_str(",\"consultant_uri\":");
                out.push_str(&quote(anchor.as_token()));
            }
            None => {
                out.push_str(",\"anchor_status\":");
                out.push_str(&quote(ANCHOR_UNRESOLVED));
            }
        }
        out.push('}');
        out
    }

    /// Parse a line rendered by [`Self::render_jsonl_line`] back into an
    /// envelope. Fail-closed and canonical: the input must be the unique
    /// canonical encoding of the returned envelope, so a re-encoded, escaped,
    /// re-ordered or malformed line is refused rather than normalized.
    pub fn read_back(line: &str) -> Result<IdentityEnvelope, EnvelopeRefusal> {
        if !line.is_ascii() {
            return Err(EnvelopeRefusal::new(
                EnvelopeRefusalKind::NonAscii,
                "identity envelope line is not ASCII",
            ));
        }
        let body = line.strip_suffix('\n').unwrap_or(line);
        let mut scanner = Scanner::new(body);

        scanner.expect("{\"schema\":")?;
        let schema = scanner.read_string()?;
        if schema != IDENTITY_ENVELOPE_SCHEMA {
            return Err(malformed("unexpected schema id"));
        }
        scanner.expect(",\"relative_path\":")?;
        let relative_path = scanner.read_string()?;
        scanner.expect(",\"source\":{\"sha256\":")?;
        let source_sha256 = scanner.read_string()?;
        scanner.expect(",\"bytes\":")?;
        let source_bytes = scanner.read_u64()?;
        scanner.expect("}")?;

        let mut anchor: Option<ConsultantUriAnchor> = None;
        match scanner.peek() {
            Some(b',') => {
                scanner.advance(1);
                let key = scanner.read_string()?;
                match key.as_str() {
                    "consultant_uri" => {
                        scanner.expect(":")?;
                        let token = scanner.read_string()?;
                        if scanner.peek() == Some(b',') {
                            scanner.advance(1);
                            let extra = scanner.read_string()?;
                            if extra == "anchor_status" {
                                return Err(EnvelopeRefusal::new(
                                    EnvelopeRefusalKind::BothAnchorAndStatus,
                                    "envelope carries both consultant_uri and anchor_status",
                                ));
                            }
                            return Err(malformed("unexpected field after consultant_uri"));
                        }
                        let parsed = ConsultantUriAnchor::parse(&token).map_err(|refusal| {
                            malformed(&format!(
                                "consultant_uri refused: {}",
                                refusal.kind().as_str()
                            ))
                        })?;
                        anchor = Some(parsed);
                    }
                    "anchor_status" => {
                        scanner.expect(":")?;
                        let status = scanner.read_string()?;
                        if status != ANCHOR_UNRESOLVED {
                            return Err(malformed("unknown anchor_status class"));
                        }
                    }
                    _ => {
                        return Err(EnvelopeRefusal::new(
                            EnvelopeRefusalKind::MissingAnchorFields,
                            "envelope carries neither consultant_uri nor anchor_status",
                        ));
                    }
                }
            }
            Some(b'}') => {
                return Err(EnvelopeRefusal::new(
                    EnvelopeRefusalKind::MissingAnchorFields,
                    "envelope carries neither consultant_uri nor anchor_status",
                ));
            }
            _ => return Err(malformed("malformed source object")),
        }
        scanner.expect("}")?;
        if !scanner.is_at_end() {
            return Err(malformed("trailing bytes after envelope"));
        }

        let envelope = IdentityEnvelope {
            relative_path,
            source_sha256,
            source_bytes,
            anchor,
        };
        // Canonical-form gate: a line that decodes to an envelope but is not
        // that envelope's unique canonical rendering (e.g. a `\u003a` escape
        // standing in for `:`) is refused, so no token is silently normalized.
        if envelope.render_body() != body {
            return Err(EnvelopeRefusal::new(
                EnvelopeRefusalKind::TokenMismatch,
                "identity envelope line is not in canonical byte form",
            ));
        }
        Ok(envelope)
    }

    /// Integral invariant: the carried anchor token must equal `source_token`
    /// byte-for-byte. An unresolved envelope carries no token, so it cannot be
    /// verified.
    pub fn verify_byte_exact(&self, source_token: &str) -> Result<(), EnvelopeRefusal> {
        match &self.anchor {
            Some(anchor) => {
                if anchor.as_token().as_bytes() == source_token.as_bytes() {
                    Ok(())
                } else {
                    Err(EnvelopeRefusal::new(
                        EnvelopeRefusalKind::TokenMismatch,
                        "carried anchor token differs from the source token",
                    ))
                }
            }
            None => Err(EnvelopeRefusal::new(
                EnvelopeRefusalKind::MissingAnchorFields,
                "envelope carries no consultant_uri to verify",
            )),
        }
    }

    /// Render → read-back integral round trip: parse a canonical line and
    /// re-assert that the anchor token appears byte-exact in it.
    pub fn byte_exact_round_trip(line: &str) -> Result<IdentityEnvelope, EnvelopeRefusal> {
        let envelope = Self::read_back(line)?;
        if let Some(anchor) = &envelope.anchor {
            let token = anchor.as_token();
            // Canonical tokens are escape-free ASCII, so a byte-exact
            // substring check is exact.
            if !line.contains(token) {
                return Err(EnvelopeRefusal::new(
                    EnvelopeRefusalKind::TokenMismatch,
                    "anchor token is not present byte-exact in the line",
                ));
            }
        }
        Ok(envelope)
    }
}

/// Closed refusal vocabulary of the identity envelope wire.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EnvelopeRefusalKind {
    /// The line violates the envelope's fixed structural shape.
    Malformed,
    /// Neither `consultant_uri` nor `anchor_status` is present.
    MissingAnchorFields,
    /// Both `consultant_uri` and `anchor_status` are present.
    BothAnchorAndStatus,
    /// The line contains a non-ASCII byte.
    NonAscii,
    /// The carried token is not byte-equal / not in canonical byte form.
    TokenMismatch,
}

impl EnvelopeRefusalKind {
    /// Stable machine-readable identifier of the refusal kind.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Malformed => "malformed",
            Self::MissingAnchorFields => "missing_anchor_fields",
            Self::BothAnchorAndStatus => "both_anchor_and_status",
            Self::NonAscii => "non_ascii",
            Self::TokenMismatch => "token_mismatch",
        }
    }
}

impl fmt::Display for EnvelopeRefusalKind {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

/// A typed, bounded identity-envelope refusal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnvelopeRefusal {
    kind: EnvelopeRefusalKind,
    detail: String,
}

impl EnvelopeRefusal {
    /// Build a refusal, bounding the detail and dropping control characters.
    pub fn new(kind: EnvelopeRefusalKind, detail: impl Into<String>) -> Self {
        Self {
            kind,
            detail: bound_detail(detail.into()),
        }
    }

    /// The refusal kind.
    pub fn kind(&self) -> EnvelopeRefusalKind {
        self.kind
    }

    /// The bounded human-readable detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for EnvelopeRefusal {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "identity envelope refused ({}): {}",
            self.kind.as_str(),
            self.detail
        )
    }
}

impl Error for EnvelopeRefusal {}

fn malformed(detail: &str) -> EnvelopeRefusal {
    EnvelopeRefusal::new(EnvelopeRefusalKind::Malformed, detail)
}

/// Minimal strict scanner over the fixed envelope shape. Only the canonical
/// structural literals and JSON string/number values are accepted; anything
/// else is a [`EnvelopeRefusalKind::Malformed`] refusal.
struct Scanner<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> Scanner<'a> {
    fn new(text: &'a str) -> Self {
        Self {
            bytes: text.as_bytes(),
            pos: 0,
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.pos).copied()
    }

    fn advance(&mut self, count: usize) {
        self.pos += count;
    }

    fn is_at_end(&self) -> bool {
        self.pos == self.bytes.len()
    }

    fn expect(&mut self, literal: &str) -> Result<(), EnvelopeRefusal> {
        let end = self.pos + literal.len();
        if end <= self.bytes.len() && &self.bytes[self.pos..end] == literal.as_bytes() {
            self.pos = end;
            Ok(())
        } else {
            Err(malformed("unexpected structural literal"))
        }
    }

    /// Read a JSON string value, decoding the standard escapes. The opening and
    /// closing quotes are consumed.
    fn read_string(&mut self) -> Result<String, EnvelopeRefusal> {
        if self.peek() != Some(b'"') {
            return Err(malformed("expected string value"));
        }
        self.pos += 1;
        let mut out = String::new();
        loop {
            let byte = self
                .peek()
                .ok_or_else(|| malformed("unterminated string value"))?;
            match byte {
                b'"' => {
                    self.pos += 1;
                    return Ok(out);
                }
                b'\\' => {
                    self.pos += 1;
                    let escape = self
                        .peek()
                        .ok_or_else(|| malformed("unterminated string escape"))?;
                    self.pos += 1;
                    match escape {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000c}'),
                        b'u' => out.push(self.read_unicode_escape()?),
                        _ => return Err(malformed("unknown string escape")),
                    }
                }
                b if b < 0x20 => return Err(malformed("raw control character in string")),
                b => {
                    // Whole-line ASCII was verified before scanning.
                    out.push(b as char);
                    self.pos += 1;
                }
            }
        }
    }

    fn read_unicode_escape(&mut self) -> Result<char, EnvelopeRefusal> {
        let end = self.pos + 4;
        if end > self.bytes.len() {
            return Err(malformed("truncated unicode escape"));
        }
        let hex = std::str::from_utf8(&self.bytes[self.pos..end])
            .map_err(|_| malformed("unicode escape is not ASCII"))?;
        let code = u32::from_str_radix(hex, 16)
            .map_err(|_| malformed("unicode escape is not four hex digits"))?;
        self.pos = end;
        char::from_u32(code).ok_or_else(|| malformed("unicode escape is not a scalar value"))
    }

    fn read_u64(&mut self) -> Result<u64, EnvelopeRefusal> {
        let start = self.pos;
        while matches!(self.peek(), Some(b) if b.is_ascii_digit()) {
            self.pos += 1;
        }
        if self.pos == start {
            return Err(malformed("expected decimal byte count"));
        }
        let digits = std::str::from_utf8(&self.bytes[start..self.pos])
            .map_err(|_| malformed("byte count is not ASCII"))?;
        digits
            .parse::<u64>()
            .map_err(|_| malformed("byte count overflows u64"))
    }
}

/// Minimal JSON string escaper, matching the `corpus_inventory` renderer:
/// quotes, backslashes, and control characters are the only escapes emitted.
fn quote(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if (ch as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", ch as u32);
            }
            ch => out.push(ch),
        }
    }
    out.push('"');
    out
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
