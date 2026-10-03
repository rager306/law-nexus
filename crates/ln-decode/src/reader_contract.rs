//! Serde-free reader-view contract types over the frozen `source_package`.
//!
//! This module is the typed half of `prd/architecture/reader-view-contract.md`
//! (pinned provider profile [`READER_PROFILE`]). It fixes the closed reader
//! vocabularies, the decoded-fragment coordinate base (`FragmentRef`,
//! `ElementRef`, `ReaderFragmentSpan`, `ReaderViewKey`) and the half-open
//! UTF-8 byte span validation that mirrors D603 / `npa_anchor::check_span`.
//!
//! It is **not** a serialization model: nothing here imports `serde` /
//! `serde_json` (D602/D328 keep serde module-scoped to `source_package`). It
//! carries no XML byte coordinates and no iteration-13 `locator`; a
//! [`ReaderFragmentSpan`] indexes only the decoded `value` of a text record.
//!
//! S02 owns these types, the ownership map and the coverage partition. Building
//! the view forest, segment records, serialization, the independent verifier,
//! metrics and the tamper battery belong to S03/S04.

use std::fmt;

/// Pinned reader provider profile.
///
/// Raw decoded text, no character normalization. Provider-bounded to Consultant
/// WordML (not Garant).
pub const READER_PROFILE: &str = "reader_wordml_profile/v1";

/// WordML namespaces recognised by the reader.
///
/// A local name is a WordML local only when its Clark namespace is one of these
/// three and its local name is in the relevant dictionary. A foreign-namespaced
/// `tab` is not a control.
pub const WORDML_NAMESPACES: [&str; 3] = [
    "http://schemas.microsoft.com/office/word/2003/wordml",
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
];

/// Note-definition local names (`footnote`, `endnote`).
pub const NOTE_DEF_LOCALS: &[&str] = &["footnote", "endnote"];

/// Note-reference local names.
pub const NOTE_REFERENCE_LOCALS: &[&str] = &[
    "footnoteReference",
    "endnoteReference",
    "commentReference",
    "annotationRef",
];

/// Field local names.
pub const FIELD_LOCALS: &[&str] = &["fldChar", "instrText", "fldSimple"];

/// Documented control local names.
pub const CONTROL_LOCALS: &[&str] = &["tab", "br", "cr"];

/// Known structural container local names.
pub const CONTAINER_LOCALS: &[&str] = &["wordDocument", "body", "tblGrid", "styles"];

// ------------------------------------------------------------------- errors #

/// Failure class of the reader contract.
///
/// The three span variants mirror `npa_anchor::SpanError` (D603); [`Self::UnknownToken`]
/// is the fail-closed class for an unknown wire token.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ContractErrorKind {
    /// `start >= end` — the range is not a non-empty half-open interval.
    EmptyOrInverted,
    /// `end` is past the decoded byte length.
    OutOfBounds,
    /// `start` / `end` is not on a UTF-8 code point boundary.
    NotCharBoundary,
    /// A wire token is outside the closed vocabulary.
    UnknownToken,
}

impl ContractErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            ContractErrorKind::EmptyOrInverted => "empty_or_inverted",
            ContractErrorKind::OutOfBounds => "out_of_bounds",
            ContractErrorKind::NotCharBoundary => "not_char_boundary",
            ContractErrorKind::UnknownToken => "unknown_token",
        }
    }
}

impl fmt::Display for ContractErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed reader-contract error. No serde.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContractError {
    kind: ContractErrorKind,
    detail: String,
}

impl ContractError {
    /// Builds an error from a class and a human-readable detail.
    pub fn new(kind: ContractErrorKind, detail: impl Into<String>) -> Self {
        ContractError {
            kind,
            detail: detail.into(),
        }
    }

    /// Error class.
    pub const fn kind(&self) -> ContractErrorKind {
        self.kind
    }

    /// Human-readable detail (never parsed; for diagnostics only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for ContractError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for ContractError {}

fn unknown_token(dictionary: &str, token: &str) -> ContractError {
    ContractError::new(
        ContractErrorKind::UnknownToken,
        format!("unknown {dictionary} token: {token:?}"),
    )
}

// ---------------------------------------------------------------- view kind #

/// Closed reader view vocabulary (`view_kind`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReaderViewKind {
    Paragraph,
    Residual,
    Table,
    Row,
    Cell,
    Note,
}

impl ReaderViewKind {
    /// Wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            ReaderViewKind::Paragraph => "paragraph",
            ReaderViewKind::Residual => "residual",
            ReaderViewKind::Table => "table",
            ReaderViewKind::Row => "row",
            ReaderViewKind::Cell => "cell",
            ReaderViewKind::Note => "note",
        }
    }

    /// Fail-closed parse; an unknown token is never mapped to a default.
    pub fn from_wire(token: &str) -> Result<Self, ContractError> {
        match token {
            "paragraph" => Ok(ReaderViewKind::Paragraph),
            "residual" => Ok(ReaderViewKind::Residual),
            "table" => Ok(ReaderViewKind::Table),
            "row" => Ok(ReaderViewKind::Row),
            "cell" => Ok(ReaderViewKind::Cell),
            "note" => Ok(ReaderViewKind::Note),
            _ => Err(unknown_token("view_kind", token)),
        }
    }

    /// Primary views are text-owning and must not carry `children`.
    pub const fn is_primary(self) -> bool {
        matches!(self, ReaderViewKind::Paragraph | ReaderViewKind::Residual)
    }

    /// Navigation views are structure-only and must not carry `segment_refs`.
    pub const fn is_navigation(self) -> bool {
        matches!(
            self,
            ReaderViewKind::Table
                | ReaderViewKind::Row
                | ReaderViewKind::Cell
                | ReaderViewKind::Note
        )
    }
}

// ------------------------------------------------------------- segment kind #

/// Closed `segment_kind` vocabulary.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReaderSegmentKind {
    /// Source-backed segment; names one fragment.
    Text,
    /// Generated segment from a documented control; no source span.
    Derived,
}

impl ReaderSegmentKind {
    /// Wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            ReaderSegmentKind::Text => "text",
            ReaderSegmentKind::Derived => "derived",
        }
    }

    /// Fail-closed parse.
    pub fn from_wire(token: &str) -> Result<Self, ContractError> {
        match token {
            "text" => Ok(ReaderSegmentKind::Text),
            "derived" => Ok(ReaderSegmentKind::Derived),
            _ => Err(unknown_token("segment_kind", token)),
        }
    }
}

// ------------------------------------------------------------- derived kind #

/// Closed `origin` vocabulary for generated segments.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReaderDerivedKind {
    /// `w:tab` -> TAB.
    Tab,
    /// `w:br` / `w:cr` -> LF.
    LineBreak,
    /// `w:br w:type="page"` -> LF.
    PageBreak,
}

impl ReaderDerivedKind {
    /// Wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            ReaderDerivedKind::Tab => "tab",
            ReaderDerivedKind::LineBreak => "line_break",
            ReaderDerivedKind::PageBreak => "page_break",
        }
    }

    /// Fail-closed parse.
    pub fn from_wire(token: &str) -> Result<Self, ContractError> {
        match token {
            "tab" => Ok(ReaderDerivedKind::Tab),
            "line_break" => Ok(ReaderDerivedKind::LineBreak),
            "page_break" => Ok(ReaderDerivedKind::PageBreak),
            _ => Err(unknown_token("origin", token)),
        }
    }

    /// Generated literal text. A page break is an LF, not a separate element.
    pub const fn literal(self) -> &'static str {
        match self {
            ReaderDerivedKind::Tab => "\t",
            ReaderDerivedKind::LineBreak => "\n",
            ReaderDerivedKind::PageBreak => "\n",
        }
    }
}

// ---------------------------------------------------------------- semantics #

/// Closed `semantic` vocabulary. No value asserts legal authority.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReaderSemantic {
    Body,
    Whitespace,
    FieldCode,
    RevisionInsertion,
    RevisionDeletion,
    DerivedSeparator,
    Empty,
}

impl ReaderSemantic {
    /// Wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            ReaderSemantic::Body => "body",
            ReaderSemantic::Whitespace => "whitespace",
            ReaderSemantic::FieldCode => "field_code",
            ReaderSemantic::RevisionInsertion => "revision_insertion",
            ReaderSemantic::RevisionDeletion => "revision_deletion",
            ReaderSemantic::DerivedSeparator => "derived_separator",
            ReaderSemantic::Empty => "empty",
        }
    }

    /// Fail-closed parse.
    pub fn from_wire(token: &str) -> Result<Self, ContractError> {
        match token {
            "body" => Ok(ReaderSemantic::Body),
            "whitespace" => Ok(ReaderSemantic::Whitespace),
            "field_code" => Ok(ReaderSemantic::FieldCode),
            "revision_insertion" => Ok(ReaderSemantic::RevisionInsertion),
            "revision_deletion" => Ok(ReaderSemantic::RevisionDeletion),
            "derived_separator" => Ok(ReaderSemantic::DerivedSeparator),
            "empty" => Ok(ReaderSemantic::Empty),
            _ => Err(unknown_token("semantic", token)),
        }
    }
}

// ----------------------------------------------------------------- ref types #

/// Closed `reference_type` vocabulary. `inert_payload` is deliberately absent:
/// the substrate retains all decoded text and has no exclusion records.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReaderReferenceType {
    NoteReference,
    EndnoteReference,
    CommentReference,
    AnnotationReference,
    Field,
    UnknownWordmlElement,
    ForeignElement,
}

impl ReaderReferenceType {
    /// Wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            ReaderReferenceType::NoteReference => "note_reference",
            ReaderReferenceType::EndnoteReference => "endnote_reference",
            ReaderReferenceType::CommentReference => "comment_reference",
            ReaderReferenceType::AnnotationReference => "annotation_reference",
            ReaderReferenceType::Field => "field",
            ReaderReferenceType::UnknownWordmlElement => "unknown_wordml_element",
            ReaderReferenceType::ForeignElement => "foreign_element",
        }
    }

    /// Fail-closed parse.
    pub fn from_wire(token: &str) -> Result<Self, ContractError> {
        match token {
            "note_reference" => Ok(ReaderReferenceType::NoteReference),
            "endnote_reference" => Ok(ReaderReferenceType::EndnoteReference),
            "comment_reference" => Ok(ReaderReferenceType::CommentReference),
            "annotation_reference" => Ok(ReaderReferenceType::AnnotationReference),
            "field" => Ok(ReaderReferenceType::Field),
            "unknown_wordml_element" => Ok(ReaderReferenceType::UnknownWordmlElement),
            "foreign_element" => Ok(ReaderReferenceType::ForeignElement),
            _ => Err(unknown_token("reference_type", token)),
        }
    }
}

// ------------------------------------------------------------- coordinates #

/// A substrate text record id, `tN`, in document order.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct FragmentRef(String);

impl FragmentRef {
    /// Builds a fragment reference from an id.
    pub fn new(id: impl Into<String>) -> Self {
        FragmentRef(id.into())
    }

    /// The raw record id.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl From<&str> for FragmentRef {
    fn from(id: &str) -> Self {
        FragmentRef(id.to_string())
    }
}

impl fmt::Display for FragmentRef {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// A substrate element record id, `eN`, in pre-order.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ElementRef(String);

impl ElementRef {
    /// Builds an element reference from an id.
    pub fn new(id: impl Into<String>) -> Self {
        ElementRef(id.into())
    }

    /// The raw record id.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl From<&str> for ElementRef {
    fn from(id: &str) -> Self {
        ElementRef(id.to_string())
    }
}

impl fmt::Display for ElementRef {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// Half-open UTF-8 byte range `[start, end)` inside a decoded text record's
/// `value`. Mirrors D603 / `npa_anchor::check_span`. It is **not** an XML byte
/// coordinate.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ReaderFragmentSpan {
    pub fragment: FragmentRef,
    pub start: usize,
    pub end: usize,
}

impl ReaderFragmentSpan {
    /// Builds a span over the referenced fragment.
    pub fn new(fragment: FragmentRef, start: usize, end: usize) -> Self {
        ReaderFragmentSpan {
            fragment,
            start,
            end,
        }
    }
}

/// Primary owner of a reader view: a kind plus the anchoring element id.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ReaderViewKey {
    pub kind: ReaderViewKind,
    pub element_ref: ElementRef,
}

impl ReaderViewKey {
    /// Builds a view key.
    pub fn new(kind: ReaderViewKind, element_ref: ElementRef) -> Self {
        ReaderViewKey { kind, element_ref }
    }
}

/// Validates that `span` is a non-empty half-open UTF-8 byte range of `value`,
/// with both bounds on code point boundaries.
///
/// Check order (mirrors `npa_anchor::check_span`): `EmptyOrInverted`,
/// `OutOfBounds`, `NotCharBoundary`.
pub fn check_fragment_span(value: &str, span: &ReaderFragmentSpan) -> Result<(), ContractError> {
    if span.start >= span.end {
        return Err(ContractError::new(
            ContractErrorKind::EmptyOrInverted,
            format!(
                "span on {} is empty or inverted: start {} >= end {}",
                span.fragment, span.start, span.end
            ),
        ));
    }
    if span.end > value.len() {
        return Err(ContractError::new(
            ContractErrorKind::OutOfBounds,
            format!(
                "span on {} ends at {} beyond decoded length {}",
                span.fragment,
                span.end,
                value.len()
            ),
        ));
    }
    if !value.is_char_boundary(span.start) || !value.is_char_boundary(span.end) {
        return Err(ContractError::new(
            ContractErrorKind::NotCharBoundary,
            format!(
                "span on {} [{}, {}) is not on a UTF-8 code point boundary",
                span.fragment, span.start, span.end
            ),
        ));
    }
    Ok(())
}

/// The whole-fragment span: `0..value.len()`. A text segment in S02 covers the
/// whole fragment.
pub fn whole_fragment_span(fragment: &FragmentRef, value: &str) -> ReaderFragmentSpan {
    ReaderFragmentSpan {
        fragment: fragment.clone(),
        start: 0,
        end: value.len(),
    }
}

// -------------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn view_kind_round_trips_and_rejects_unknown() {
        let kinds = [
            ReaderViewKind::Paragraph,
            ReaderViewKind::Residual,
            ReaderViewKind::Table,
            ReaderViewKind::Row,
            ReaderViewKind::Cell,
            ReaderViewKind::Note,
        ];
        for kind in kinds {
            assert_eq!(ReaderViewKind::from_wire(kind.as_str()).unwrap(), kind);
        }
        let err = ReaderViewKind::from_wire("Paragraph").unwrap_err();
        assert_eq!(err.kind(), ContractErrorKind::UnknownToken);
        assert!(err.detail().contains("Paragraph"));
    }

    #[test]
    fn view_kind_primary_and_navigation_partition() {
        for kind in [ReaderViewKind::Paragraph, ReaderViewKind::Residual] {
            assert!(kind.is_primary());
            assert!(!kind.is_navigation());
        }
        for kind in [
            ReaderViewKind::Table,
            ReaderViewKind::Row,
            ReaderViewKind::Cell,
            ReaderViewKind::Note,
        ] {
            assert!(kind.is_navigation());
            assert!(!kind.is_primary());
        }
    }

    #[test]
    fn segment_kind_round_trips_and_rejects_unknown() {
        for kind in [ReaderSegmentKind::Text, ReaderSegmentKind::Derived] {
            assert_eq!(ReaderSegmentKind::from_wire(kind.as_str()).unwrap(), kind);
        }
        assert_eq!(
            ReaderSegmentKind::from_wire("source").unwrap_err().kind(),
            ContractErrorKind::UnknownToken
        );
    }

    #[test]
    fn derived_kind_round_trips_literals_and_rejects_unknown() {
        let cases = [
            (ReaderDerivedKind::Tab, "\t"),
            (ReaderDerivedKind::LineBreak, "\n"),
            (ReaderDerivedKind::PageBreak, "\n"),
        ];
        for (kind, literal) in cases {
            assert_eq!(ReaderDerivedKind::from_wire(kind.as_str()).unwrap(), kind);
            assert_eq!(kind.literal(), literal);
        }
        assert_eq!(
            ReaderDerivedKind::from_wire("pageBreak")
                .unwrap_err()
                .kind(),
            ContractErrorKind::UnknownToken
        );
    }

    #[test]
    fn semantic_round_trips_and_rejects_unknown() {
        let semantics = [
            ReaderSemantic::Body,
            ReaderSemantic::Whitespace,
            ReaderSemantic::FieldCode,
            ReaderSemantic::RevisionInsertion,
            ReaderSemantic::RevisionDeletion,
            ReaderSemantic::DerivedSeparator,
            ReaderSemantic::Empty,
        ];
        for semantic in semantics {
            assert_eq!(
                ReaderSemantic::from_wire(semantic.as_str()).unwrap(),
                semantic
            );
        }
        assert_eq!(
            ReaderSemantic::from_wire("sep").unwrap_err().kind(),
            ContractErrorKind::UnknownToken
        );
    }

    #[test]
    fn reference_type_round_trips_and_rejects_unknown() {
        let references = [
            ReaderReferenceType::NoteReference,
            ReaderReferenceType::EndnoteReference,
            ReaderReferenceType::CommentReference,
            ReaderReferenceType::AnnotationReference,
            ReaderReferenceType::Field,
            ReaderReferenceType::UnknownWordmlElement,
            ReaderReferenceType::ForeignElement,
        ];
        for reference in references {
            assert_eq!(
                ReaderReferenceType::from_wire(reference.as_str()).unwrap(),
                reference
            );
        }
        let err = ReaderReferenceType::from_wire("inert_payload").unwrap_err();
        assert_eq!(err.kind(), ContractErrorKind::UnknownToken);
    }

    #[test]
    fn check_fragment_span_accepts_valid_multibyte_boundaries() {
        // "Привет": 6 Cyrillic code points, 12 UTF-8 bytes.
        let value = "Привет";
        let fragment = FragmentRef::new("t0");
        assert!(
            check_fragment_span(value, &ReaderFragmentSpan::new(fragment.clone(), 0, 12)).is_ok()
        );
        assert!(
            check_fragment_span(value, &ReaderFragmentSpan::new(fragment.clone(), 2, 4)).is_ok()
        );
        assert!(check_fragment_span(value, &ReaderFragmentSpan::new(fragment, 0, 2)).is_ok());
    }

    #[test]
    fn check_fragment_span_rejects_empty_or_inverted() {
        let value = "abc";
        let fragment = FragmentRef::new("t1");
        let equal = ReaderFragmentSpan::new(fragment.clone(), 2, 2);
        assert_eq!(
            check_fragment_span(value, &equal).unwrap_err().kind(),
            ContractErrorKind::EmptyOrInverted
        );
        let inverted = ReaderFragmentSpan::new(fragment, 3, 1);
        assert_eq!(
            check_fragment_span(value, &inverted).unwrap_err().kind(),
            ContractErrorKind::EmptyOrInverted
        );
    }

    #[test]
    fn check_fragment_span_rejects_out_of_bounds() {
        let value = "abc";
        let span = ReaderFragmentSpan::new(FragmentRef::new("t2"), 0, 4);
        assert_eq!(
            check_fragment_span(value, &span).unwrap_err().kind(),
            ContractErrorKind::OutOfBounds
        );
    }

    #[test]
    fn check_fragment_span_rejects_non_char_boundary() {
        let value = "Привет";
        let fragment = FragmentRef::new("t3");
        // Byte 1 is inside "П"; byte 3 is inside "р".
        for (start, end) in [(1, 3), (3, 5)] {
            let span = ReaderFragmentSpan::new(fragment.clone(), start, end);
            assert_eq!(
                check_fragment_span(value, &span).unwrap_err().kind(),
                ContractErrorKind::NotCharBoundary
            );
        }
    }

    #[test]
    fn whole_fragment_span_covers_the_value() {
        let value = "Привет";
        let span = whole_fragment_span(&FragmentRef::new("t7"), value);
        assert_eq!(span.fragment.as_str(), "t7");
        assert_eq!(span.start, 0);
        assert_eq!(span.end, value.len());
        assert!(check_fragment_span(value, &span).is_ok());
    }

    #[test]
    fn refs_and_view_key_expose_their_ids() {
        let fragment = FragmentRef::from("t3");
        assert_eq!(fragment.as_str(), "t3");
        let element = ElementRef::new(String::from("e5"));
        assert_eq!(element.as_str(), "e5");
        let key = ReaderViewKey::new(ReaderViewKind::Paragraph, element);
        assert_eq!(key.kind, ReaderViewKind::Paragraph);
        assert_eq!(key.element_ref.as_str(), "e5");
    }

    #[test]
    fn consts_match_the_pinned_contract() {
        assert_eq!(READER_PROFILE, "reader_wordml_profile/v1");
        assert_eq!(WORDML_NAMESPACES.len(), 3);
        assert!(WORDML_NAMESPACES
            .contains(&"http://schemas.openxmlformats.org/wordprocessingml/2006/main"));
        assert_eq!(NOTE_DEF_LOCALS, ["footnote", "endnote"].as_slice());
        assert_eq!(
            NOTE_REFERENCE_LOCALS,
            [
                "footnoteReference",
                "endnoteReference",
                "commentReference",
                "annotationRef",
            ]
            .as_slice()
        );
        assert_eq!(
            FIELD_LOCALS,
            ["fldChar", "instrText", "fldSimple"].as_slice()
        );
        assert_eq!(CONTROL_LOCALS, ["tab", "br", "cr"].as_slice());
        assert_eq!(
            CONTAINER_LOCALS,
            ["wordDocument", "body", "tblGrid", "styles"].as_slice()
        );
    }

    #[test]
    fn error_display_is_stable() {
        let err = ContractError::new(ContractErrorKind::OutOfBounds, "x");
        assert_eq!(err.to_string(), "out_of_bounds: x");
    }
}
