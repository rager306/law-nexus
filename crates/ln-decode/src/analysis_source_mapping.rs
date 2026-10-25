//! Source-to-analysis mapping seam (M214 S01 / T02).
//!
//! Executable core of `prd/architecture/npa-analysis-jsonl-contract.md`: an
//! analysis coordinate is resolved to the exact UTF-8 slice of a pinned parent
//! fragment, and every invalid identity, coordinate, token view or envelope
//! shape is returned as a closed typed refusal rather than a silent success
//! (T01 §5, §7.1, §12).
//!
//! Scope is identity and coordinates only. This module mints **no** JSONL
//! record schema (S02), **no** read-back verifier (S03) and **no** temporal
//! semantics (T01 §9). The half-open span validators
//! ([`crate::npa_anchor::check_span`], [`crate::reader_contract::check_fragment_span`])
//! and the three token producers ([`crate::lexer::lex`],
//! [`crate::tokenizer::tokenize`], [`crate::tokenizer::words_from_covering`])
//! are reused, never rewritten (ADR-0028 dual tokenizer).

use std::collections::BTreeMap;
use std::fmt;

use crate::document_context::DocumentVersionRef;
use crate::npa_anchor::{LocalSpan, SpanError, check_span};
use crate::reader_contract::{
    ContractError, ContractErrorKind, FragmentRef, ReaderFragmentSpan, check_fragment_span,
};

// ----------------------------------------------------------------- refusals #

/// Closed refusal vocabulary of the source-mapping seam (T01 §7.1).
///
/// The three coordinate variants reuse the `npa_anchor::SpanError` /
/// `reader_contract::ContractErrorKind` vocabulary; the rest are the
/// identity, provenance and envelope refusals the seam owes S02–S04.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MappingRefusalKind {
    /// `start >= end` — the range is not a non-empty half-open interval.
    EmptyOrInverted,
    /// `end` is past the fragment's decoded byte length.
    OutOfBounds,
    /// `start` / `end` is not on a UTF-8 code point boundary.
    NotCharBoundary,
    /// The fragment is absent from the pinned parent catalog.
    UnknownFragment,
    /// The fragment belongs to a different document than the envelope pin.
    CrossDocument,
    /// The cited parent identity (sha / bytes / seals) differs from the pin.
    SourceIdentityMismatch,
    /// The record's `document_version_ref`/`source_revision`/`decoder_profile`
    /// triple differs from the envelope's.
    DocumentVersionMismatch,
    /// The declared token view is not the one the producing rule emits.
    TokenViewMismatch,
    /// The coordinate system or fragment kind is outside the supported set.
    UnsupportedMapping,
    /// The envelope or pinned catalog is structurally malformed.
    EnvelopeStructural,
    /// A temporal stop-sign field (T01 §9) is present.
    TemporalFieldForbidden,
    /// The envelope re-carries decoded corpus text instead of pinning the parent.
    CorpusTransferForbidden,
}

impl MappingRefusalKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            MappingRefusalKind::EmptyOrInverted => "empty_or_inverted",
            MappingRefusalKind::OutOfBounds => "out_of_bounds",
            MappingRefusalKind::NotCharBoundary => "not_char_boundary",
            MappingRefusalKind::UnknownFragment => "unknown_fragment",
            MappingRefusalKind::CrossDocument => "cross_document",
            MappingRefusalKind::SourceIdentityMismatch => "source_identity_mismatch",
            MappingRefusalKind::DocumentVersionMismatch => "document_version_mismatch",
            MappingRefusalKind::TokenViewMismatch => "token_view_mismatch",
            MappingRefusalKind::UnsupportedMapping => "unsupported_mapping",
            MappingRefusalKind::EnvelopeStructural => "envelope_structural",
            MappingRefusalKind::TemporalFieldForbidden => "temporal_field_forbidden",
            MappingRefusalKind::CorpusTransferForbidden => "corpus_transfer_forbidden",
        }
    }
}

impl fmt::Display for MappingRefusalKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// A closed mapping refusal: a kind from [`MappingRefusalKind`] plus a
/// human-readable detail. Never parsed; for diagnostics only.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MappingRefusal {
    kind: MappingRefusalKind,
    detail: String,
}

impl MappingRefusal {
    /// Builds a refusal from a closed kind and a diagnostic detail.
    pub fn new(kind: MappingRefusalKind, detail: impl Into<String>) -> Self {
        MappingRefusal {
            kind,
            detail: detail.into(),
        }
    }

    /// The closed refusal kind.
    pub const fn kind(&self) -> MappingRefusalKind {
        self.kind
    }

    /// The diagnostic detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for MappingRefusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for MappingRefusal {}

fn refuse(kind: MappingRefusalKind, detail: impl Into<String>) -> MappingRefusal {
    MappingRefusal::new(kind, detail)
}

fn span_refusal(err: SpanError, fragment: &FragmentRef, span: LocalSpan) -> MappingRefusal {
    let kind = match err {
        SpanError::EmptyOrInverted => MappingRefusalKind::EmptyOrInverted,
        SpanError::OutOfBounds => MappingRefusalKind::OutOfBounds,
        SpanError::NotCharBoundary => MappingRefusalKind::NotCharBoundary,
    };
    refuse(
        kind,
        format!(
            "block {} span [{}, {}) on fragment {fragment} is not a valid half-open UTF-8 range",
            span.block, span.start, span.end
        ),
    )
}

fn contract_refusal(err: &ContractError) -> MappingRefusal {
    let kind = match err.kind() {
        ContractErrorKind::EmptyOrInverted => MappingRefusalKind::EmptyOrInverted,
        ContractErrorKind::OutOfBounds => MappingRefusalKind::OutOfBounds,
        ContractErrorKind::NotCharBoundary => MappingRefusalKind::NotCharBoundary,
        _ => MappingRefusalKind::EnvelopeStructural,
    };
    refuse(kind, err.detail())
}

// ------------------------------------------------------------- identity #

/// True when `value` is exactly 64 lowercase hex characters.
fn is_lower_hex64(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

/// Pinned parent evidence identity (T01 §4.1).
///
/// `source_sha256` is copied from the parent manifest and is integrity
/// evidence, not authenticity. The seals are `None` for an unsealed parent.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct SourceIdentity {
    /// 64 lowercase hex digest of the original un-normalized input bytes.
    pub source_sha256: String,
    /// Original input byte count.
    pub source_bytes: u64,
    /// Parent envelope family tag, e.g. `law-nexus/cleaned-projection/v1`.
    pub parent_schema: String,
    /// Parent footer `records_seal_hash`, or `None` when the parent is unsealed.
    pub records_seal_hash: Option<String>,
    /// Parent footer `manifest_hash`, or `None` when the parent is unsealed.
    pub manifest_hash: Option<String>,
}

impl SourceIdentity {
    /// Builds a pinned identity, rejecting a malformed shape as a structural
    /// refusal (`EnvelopeStructural`).
    pub fn try_new(
        source_sha256: String,
        source_bytes: u64,
        parent_schema: String,
        records_seal_hash: Option<String>,
        manifest_hash: Option<String>,
    ) -> Result<Self, MappingRefusal> {
        if !is_lower_hex64(&source_sha256) {
            return Err(refuse(
                MappingRefusalKind::EnvelopeStructural,
                "source_sha256 must be 64 lowercase hex characters",
            ));
        }
        if parent_schema.trim().is_empty() {
            return Err(refuse(
                MappingRefusalKind::EnvelopeStructural,
                "parent_schema must be non-empty",
            ));
        }
        for (label, seal) in [
            ("records_seal_hash", &records_seal_hash),
            ("manifest_hash", &manifest_hash),
        ] {
            if let Some(value) = seal
                && !is_lower_hex64(value)
            {
                return Err(refuse(
                    MappingRefusalKind::EnvelopeStructural,
                    format!("{label} must be 64 lowercase hex characters or null"),
                ));
            }
        }
        Ok(SourceIdentity {
            source_sha256,
            source_bytes,
            parent_schema,
            records_seal_hash,
            manifest_hash,
        })
    }
}

/// A resolved source coordinate: the fragment plus its half-open UTF-8 byte
/// range. Only [`SourceMapping`] produces this type, so the range is valid by
/// construction.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ResolvedSpan {
    /// The fragment the coordinate indexes.
    pub fragment: FragmentRef,
    /// Half-open start byte.
    pub start: usize,
    /// Half-open end byte.
    pub end: usize,
}

impl ResolvedSpan {
    /// Builds a resolved span.
    pub const fn new(fragment: FragmentRef, start: usize, end: usize) -> Self {
        ResolvedSpan {
            fragment,
            start,
            end,
        }
    }
}

// --------------------------------------------------------- token views #

/// Closed token-view vocabulary (T01 §6). The three views are not aliases.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TokenView {
    /// `lexer::lex` — covering `NpaToken` stream.
    Covering,
    /// `tokenizer::tokenize` — private alphabetic splitter.
    Alphabetic,
    /// `tokenizer::words_from_covering` — covering `Word` projection.
    CoveringWord,
}

impl TokenView {
    /// Wire token form.
    pub const fn as_str(self) -> &'static str {
        match self {
            TokenView::Covering => "covering",
            TokenView::Alphabetic => "alphabetic",
            TokenView::CoveringWord => "covering_word",
        }
    }

    /// Fail-closed parse; an unknown token is never mapped to a default.
    pub fn from_wire(token: &str) -> Result<Self, MappingRefusal> {
        match token {
            "covering" => Ok(TokenView::Covering),
            "alphabetic" => Ok(TokenView::Alphabetic),
            "covering_word" => Ok(TokenView::CoveringWord),
            _ => Err(refuse(
                MappingRefusalKind::TokenViewMismatch,
                format!("unknown token view: {token:?}"),
            )),
        }
    }
}

/// Validates that an outcome's declared token view matches the producer's
/// view. Any cross-view substitution is refused (T01 §6 rule 2, §12 H7).
pub fn check_token_view(produced: TokenView, declared: TokenView) -> Result<(), MappingRefusal> {
    if produced == declared {
        Ok(())
    } else {
        Err(refuse(
            MappingRefusalKind::TokenViewMismatch,
            format!(
                "outcome declares token view {} but the producing rule emits {}",
                declared.as_str(),
                produced.as_str()
            ),
        ))
    }
}

/// Token spans emitted by `view` over `text`.
fn token_spans(text: &str, view: TokenView) -> Vec<(usize, usize)> {
    match view {
        TokenView::Covering => crate::lexer::lex(text)
            .into_iter()
            .map(|token| (token.span.start(), token.span.end()))
            .collect(),
        TokenView::Alphabetic => crate::tokenizer::tokenize(text)
            .into_iter()
            .map(|token| (token.start, token.end))
            .collect(),
        TokenView::CoveringWord => crate::tokenizer::words_from_covering(text)
            .into_iter()
            .map(|token| (token.start, token.end))
            .collect(),
    }
}

/// Validates that `[start, end)` is a whole token of `view` inside `text`.
///
/// The three views stay separate by construction: a span that is an
/// alphabetic stem (`ст`) is not a covering word, and an abbreviation lexeme
/// (`ст.`) is a covering token, not an alphabetic one. A mismatch is
/// `TokenViewMismatch`, never a partial or best-effort mapping.
pub fn check_token_span(
    text: &str,
    view: TokenView,
    start: usize,
    end: usize,
) -> Result<(), MappingRefusal> {
    if start >= end {
        return Err(refuse(
            MappingRefusalKind::EmptyOrInverted,
            "token span is empty or inverted",
        ));
    }
    if end > text.len() {
        return Err(refuse(
            MappingRefusalKind::OutOfBounds,
            "token span ends past the fragment text",
        ));
    }
    if !text.is_char_boundary(start) || !text.is_char_boundary(end) {
        return Err(refuse(
            MappingRefusalKind::NotCharBoundary,
            "token span is not on a UTF-8 code point boundary",
        ));
    }
    if token_spans(text, view)
        .into_iter()
        .any(|(token_start, token_end)| token_start == start && token_end == end)
    {
        Ok(())
    } else {
        Err(refuse(
            MappingRefusalKind::TokenViewMismatch,
            format!(
                "[{start}, {end}) is not a whole {} token of the fragment",
                view.as_str()
            ),
        ))
    }
}

// ------------------------------------------------------- coordinate kinds #

/// Coordinate systems a caller may ask the seam to map (T01 §5.3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CoordinateKind {
    /// `npa_anchor::LocalSpan` — block index plus decoded byte range.
    LocalBlockSpan,
    /// `reader_contract::ReaderFragmentSpan` — fragment id plus decoded byte range.
    FragmentSpan,
    /// XML/ODT artifact byte range (`SourceSpan` / `SourceLocation`).
    XmlArtifactSpan,
    /// Character offset (not a byte offset).
    CharacterOffset,
    /// Line offset.
    LineOffset,
}

impl CoordinateKind {
    /// Diagnostic name.
    pub const fn as_str(self) -> &'static str {
        match self {
            CoordinateKind::LocalBlockSpan => "local_block_span",
            CoordinateKind::FragmentSpan => "fragment_span",
            CoordinateKind::XmlArtifactSpan => "xml_artifact_span",
            CoordinateKind::CharacterOffset => "character_offset",
            CoordinateKind::LineOffset => "line_offset",
        }
    }
}

/// The seam supports only decoded half-open UTF-8 byte ranges. Artifact byte
/// ranges, character offsets and line offsets are `UnsupportedMapping`
/// (T01 §5.3).
pub fn check_coordinate_kind(kind: CoordinateKind) -> Result<(), MappingRefusal> {
    match kind {
        CoordinateKind::LocalBlockSpan | CoordinateKind::FragmentSpan => Ok(()),
        CoordinateKind::XmlArtifactSpan
        | CoordinateKind::CharacterOffset
        | CoordinateKind::LineOffset => Err(refuse(
            MappingRefusalKind::UnsupportedMapping,
            format!(
                "coordinate kind {} is not a decoded half-open UTF-8 byte range",
                kind.as_str()
            ),
        )),
    }
}

// ----------------------------------------------------------- envelope #

/// Envelope line family (T01 §8.1).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EnvelopeLineKind {
    /// `npa_analysis_manifest` at line 0.
    Manifest,
    /// `npa_analysis_policies` at line 1.
    Policies,
    /// An analysis record line.
    Record,
    /// `npa_analysis_footer` at the last line.
    Footer,
    /// A zero-length line.
    Empty,
    /// Any other family token.
    Other,
}

/// Minimal per-line shape used by the S01 structural predicate. The full
/// record schema is S02; this only fixes manifest/policies/footer order and
/// the LF-only, non-empty discipline.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EnvelopeLineShape {
    /// Line family.
    pub kind: EnvelopeLineKind,
    /// Raw byte length of the line (zero means empty).
    pub raw_len: usize,
    /// Whether the raw line embeds a carriage return.
    pub has_cr: bool,
}

impl EnvelopeLineShape {
    /// A line with no embedded carriage return.
    pub const fn new(kind: EnvelopeLineKind, raw_len: usize) -> Self {
        EnvelopeLineShape {
            kind,
            raw_len,
            has_cr: false,
        }
    }

    /// The same line with an embedded carriage return.
    pub const fn with_cr(mut self) -> Self {
        self.has_cr = true;
        self
    }
}

fn structural(detail: impl Into<String>) -> MappingRefusal {
    refuse(MappingRefusalKind::EnvelopeStructural, detail)
}

/// Validates the S01 envelope skeleton: a non-empty LF-only line list whose
/// first line is the manifest, second line policies, last line the footer and
/// whose interior is records only. A break is a closed refusal, never a
/// silent success (T01 §8.1, §12 H10).
pub fn check_envelope_shape(lines: &[EnvelopeLineShape]) -> Result<(), MappingRefusal> {
    if lines.len() < 3 {
        return Err(structural(
            "envelope needs at least a manifest, policies and footer line",
        ));
    }
    for (index, line) in lines.iter().enumerate() {
        if line.raw_len == 0 || line.kind == EnvelopeLineKind::Empty {
            return Err(structural(format!("envelope line {index} is empty")));
        }
        if line.has_cr {
            return Err(structural(format!(
                "envelope line {index} embeds a carriage return"
            )));
        }
    }
    if lines[0].kind != EnvelopeLineKind::Manifest {
        return Err(structural("line 0 must be the manifest"));
    }
    if lines[1].kind != EnvelopeLineKind::Policies {
        return Err(structural("line 1 must be policies"));
    }
    let last = lines.len() - 1;
    if lines[last].kind != EnvelopeLineKind::Footer {
        return Err(structural("the last line must be the footer"));
    }
    for (index, line) in lines.iter().enumerate().take(last).skip(2) {
        if line.kind != EnvelopeLineKind::Record {
            return Err(structural(format!("interior line {index} is not a record")));
        }
    }
    Ok(())
}

// -------------------------------------------- temporal + corpus guard #

/// Temporal stop-sign field names (T01 §9). These must not enter an
/// identity/coordinate envelope; the glossary rows stay `deferred-undefined`.
pub const TEMPORAL_FORBIDDEN_FIELDS: &[&str] = &[
    "edition_date",
    "effective_from",
    "effective_to",
    "text_change_event",
    "normative_effect_event",
    "component_membership_version",
    "norm_rule",
    "condition",
    "legal_effect",
    "exception",
    "defeater",
    "applicability_selector",
    "legal_list",
];

/// Refuses any temporal stop-sign field (T01 §9, §12 H11).
pub fn check_temporal_fields(fields: &[&str]) -> Result<(), MappingRefusal> {
    for field in fields {
        if TEMPORAL_FORBIDDEN_FIELDS.contains(field) {
            return Err(refuse(
                MappingRefusalKind::TemporalFieldForbidden,
                format!(
                    "field {field} is a temporal stop-sign and must not enter an identity/coordinate envelope"
                ),
            ));
        }
    }
    Ok(())
}

/// Refuses a fragment record that re-carries decoded corpus text. The
/// contracted v1 behavior is count/hash only; span resolution reads the
/// pinned parent (T01 §8.4, §12 H12).
pub fn check_no_corpus_transfer(inline_text: Option<&str>) -> Result<(), MappingRefusal> {
    match inline_text {
        None => Ok(()),
        Some(text) => Err(refuse(
            MappingRefusalKind::CorpusTransferForbidden,
            format!(
                "v1 envelope carries no inline decoded text ({} bytes supplied); resolve spans against the pinned parent",
                text.len()
            ),
        )),
    }
}

// --------------------------------------------------------------- mapping #

#[derive(Debug, Clone, PartialEq, Eq)]
struct PinnedFragment {
    text: String,
    source_sha256: String,
}

/// The source-to-analysis mapping of one envelope: a pinned parent identity,
/// one document-version triple, the parent's fragment catalog and the
/// caller-side block-to-fragment rule (T01 §4, D603).
#[derive(Debug, Clone)]
pub struct SourceMapping {
    envelope: SourceIdentity,
    version: DocumentVersionRef,
    fragments: BTreeMap<FragmentRef, PinnedFragment>,
    block_fragments: BTreeMap<usize, FragmentRef>,
}

impl SourceMapping {
    /// Builds a mapping over an already-validated envelope identity and
    /// document-version triple.
    pub fn new(envelope: SourceIdentity, version: DocumentVersionRef) -> Self {
        SourceMapping {
            envelope,
            version,
            fragments: BTreeMap::new(),
            block_fragments: BTreeMap::new(),
        }
    }

    /// The envelope's pinned parent identity.
    pub fn envelope(&self) -> &SourceIdentity {
        &self.envelope
    }

    /// The envelope's document-version triple.
    pub fn version(&self) -> &DocumentVersionRef {
        &self.version
    }

    /// Number of fragments in the pinned catalog.
    pub fn fragment_count(&self) -> usize {
        self.fragments.len()
    }

    /// Pins one parent fragment. A fragment that belongs to a different
    /// document is refused (`CrossDocument`), and a fragment declared twice is
    /// structurally refused (T01 §4.3, §4.4).
    pub fn pin_fragment(
        &mut self,
        fragment: FragmentRef,
        text: impl Into<String>,
        document: &SourceIdentity,
    ) -> Result<(), MappingRefusal> {
        if document.source_sha256 != self.envelope.source_sha256 {
            return Err(refuse(
                MappingRefusalKind::CrossDocument,
                format!(
                    "fragment {fragment} belongs to source {} but the envelope is pinned to {}",
                    document.source_sha256, self.envelope.source_sha256
                ),
            ));
        }
        if self.fragments.contains_key(&fragment) {
            return Err(structural(format!(
                "fragment {fragment} is declared more than once"
            )));
        }
        self.fragments.insert(
            fragment,
            PinnedFragment {
                text: text.into(),
                source_sha256: document.source_sha256.clone(),
            },
        );
        Ok(())
    }

    /// Declares the caller-side block-to-fragment rule (D603). A block cannot
    /// be remapped to a different fragment.
    pub fn map_block(&mut self, block: usize, fragment: FragmentRef) -> Result<(), MappingRefusal> {
        if let Some(existing) = self.block_fragments.get(&block)
            && existing != &fragment
        {
            return Err(structural(format!(
                "block {block} already maps to {existing}, cannot remap to {fragment}"
            )));
        }
        self.block_fragments.insert(block, fragment);
        Ok(())
    }

    /// Resolves a block-relative analysis coordinate through the
    /// block-to-fragment rule, then validates and indexes the fragment span.
    /// An unmapped block is `UnsupportedMapping`, never an invented fragment
    /// id (T01 §5.3).
    pub fn resolve_local_span(&self, span: LocalSpan) -> Result<ResolvedSpan, MappingRefusal> {
        let fragment = self
            .block_fragments
            .get(&span.block)
            .cloned()
            .ok_or_else(|| {
                refuse(
                    MappingRefusalKind::UnsupportedMapping,
                    format!("block {} has no fragment mapping", span.block),
                )
            })?;
        let entry = self.fragments.get(&fragment).ok_or_else(|| {
            refuse(
                MappingRefusalKind::UnknownFragment,
                format!("fragment {fragment} is absent from the pinned parent"),
            )
        })?;
        check_span(&entry.text, span).map_err(|err| span_refusal(err, &fragment, span))?;
        Ok(ResolvedSpan::new(fragment, span.start, span.end))
    }

    /// Resolves a fragment-qualified coordinate. The fragment must exist in
    /// the pinned parent and the half-open range must be a valid UTF-8
    /// sub-range of its decoded text (T01 §4.3, §5.2).
    pub fn resolve_fragment_span(
        &self,
        span: &ReaderFragmentSpan,
    ) -> Result<ResolvedSpan, MappingRefusal> {
        let entry = self.fragments.get(&span.fragment).ok_or_else(|| {
            refuse(
                MappingRefusalKind::UnknownFragment,
                format!(
                    "fragment {} is absent from the pinned parent",
                    span.fragment
                ),
            )
        })?;
        if entry.source_sha256 != self.envelope.source_sha256 {
            return Err(refuse(
                MappingRefusalKind::CrossDocument,
                format!(
                    "fragment {} belongs to a document other than the envelope pin",
                    span.fragment
                ),
            ));
        }
        check_fragment_span(&entry.text, span).map_err(|err| contract_refusal(&err))?;
        Ok(ResolvedSpan::new(
            span.fragment.clone(),
            span.start,
            span.end,
        ))
    }

    /// The exact UTF-8 slice a resolved span names. Resolution already
    /// validated the range; this only re-checks the fragment is still pinned.
    pub fn slice(&self, resolved: &ResolvedSpan) -> Result<&str, MappingRefusal> {
        let entry = self.fragments.get(&resolved.fragment).ok_or_else(|| {
            refuse(
                MappingRefusalKind::UnknownFragment,
                format!(
                    "fragment {} is absent from the pinned parent",
                    resolved.fragment
                ),
            )
        })?;
        if resolved.start >= resolved.end || resolved.end > entry.text.len() {
            return Err(refuse(
                MappingRefusalKind::OutOfBounds,
                "resolved span is not a non-empty range inside the fragment",
            ));
        }
        if !entry.text.is_char_boundary(resolved.start)
            || !entry.text.is_char_boundary(resolved.end)
        {
            return Err(refuse(
                MappingRefusalKind::NotCharBoundary,
                "resolved span is not on a UTF-8 code point boundary",
            ));
        }
        Ok(&entry.text[resolved.start..resolved.end])
    }

    /// Validates a record's document-version triple against the envelope's
    /// (T01 §4.2, §12 H8). All three fields must match.
    pub fn check_document_version(&self, claim: &DocumentVersionRef) -> Result<(), MappingRefusal> {
        if claim.document_version_ref() != self.version.document_version_ref()
            || claim.source_revision() != self.version.source_revision()
            || claim.decoder_profile() != self.version.decoder_profile()
        {
            return Err(refuse(
                MappingRefusalKind::DocumentVersionMismatch,
                format!(
                    "record version ({}, {}, {}) differs from envelope ({}, {}, {})",
                    claim.document_version_ref(),
                    claim.source_revision(),
                    claim.decoder_profile(),
                    self.version.document_version_ref(),
                    self.version.source_revision(),
                    self.version.decoder_profile()
                ),
            ));
        }
        Ok(())
    }

    /// Validates a cited parent identity against the envelope pin: the sha,
    /// byte count and schema must match, and the envelope must not claim a
    /// seal the parent does not carry (T01 §4.1, §12 H6/H9).
    pub fn check_parent_citation(&self, parent: &SourceIdentity) -> Result<(), MappingRefusal> {
        if parent.source_sha256 != self.envelope.source_sha256
            || parent.source_bytes != self.envelope.source_bytes
            || parent.parent_schema != self.envelope.parent_schema
        {
            return Err(refuse(
                MappingRefusalKind::SourceIdentityMismatch,
                "cited parent identity does not match the envelope pin",
            ));
        }
        if !seal_compatible(
            parent.records_seal_hash.as_deref(),
            self.envelope.records_seal_hash.as_deref(),
        ) || !seal_compatible(
            parent.manifest_hash.as_deref(),
            self.envelope.manifest_hash.as_deref(),
        ) {
            return Err(refuse(
                MappingRefusalKind::SourceIdentityMismatch,
                "the envelope pin claims a seal the cited parent does not carry",
            ));
        }
        Ok(())
    }
}

/// True when a pin may cite `claimed` against the parent's `pinned` seal. An
/// unsealed envelope (`pinned == None`) makes no seal claim; a sealed
/// envelope requires the parent to carry the same seal (T01 §12 H9).
fn seal_compatible(claimed: Option<&str>, pinned: Option<&str>) -> bool {
    match (pinned, claimed) {
        (None, _) => true,
        (Some(_), None) => false,
        (Some(pinned), Some(claimed)) => pinned == claimed,
    }
}
