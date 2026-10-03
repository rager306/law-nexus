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

use std::collections::{BTreeMap, HashMap, HashSet};
use std::fmt;

use crate::source_package::{ElementRecord, Record, TextRecord, TextSlot};

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
    /// The substrate records are internally inconsistent (duplicate id, missing
    /// `parent`, or a text `owner` that is not an element).
    MalformedIndex,
    /// The coverage partition is not a total, duplicate-free function.
    PartitionIncomplete,
}

impl ContractErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            ContractErrorKind::EmptyOrInverted => "empty_or_inverted",
            ContractErrorKind::OutOfBounds => "out_of_bounds",
            ContractErrorKind::NotCharBoundary => "not_char_boundary",
            ContractErrorKind::UnknownToken => "unknown_token",
            ContractErrorKind::MalformedIndex => "malformed_index",
            ContractErrorKind::PartitionIncomplete => "partition_incomplete",
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

// ------------------------------------------------------------- reader roles #

/// Known WordML structural / property local names. A known local classifies as
/// [`ReaderRole::Context`]; an unknown local in a WordML namespace classifies as
/// [`ReaderRole::Unknown`]. This restates the independently reviewed candidate
/// dictionary from the iteration-14 scratch model (`authoritative: false`).
pub const KNOWN_WORDML_LOCALS: &[&str] = &[
    "wordDocument",
    "body",
    "sectPr",
    "p",
    "r",
    "t",
    "br",
    "cr",
    "tab",
    "lastRenderedPageBreak",
    "tbl",
    "tr",
    "tc",
    "hlink",
    "hyperlink",
    "fldChar",
    "instrText",
    "fldSimple",
    "footnote",
    "endnote",
    "footnoteReference",
    "endnoteReference",
    "annotationRef",
    "commentReference",
    "bookmarkStart",
    "bookmarkEnd",
    "styles",
    "style",
    "name",
    "view",
    "docPr",
    "titlePg",
    "hdr",
    "ftr",
    "pict",
    "object",
    "drawing",
    "binData",
    "tblGrid",
    "gridCol",
    "tblW",
    "tblInd",
    "tblBorders",
    "tblLayout",
    "tblCellMar",
    "tcW",
    "tcBorders",
    "tcMar",
    "trHeight",
    "tblHeader",
    "pStyle",
    "rStyle",
    "outlineLvl",
    "jc",
    "spacing",
    "ind",
    "b",
    "i",
    "u",
    "sz",
    "color",
    "rFonts",
    "vertAlign",
    "vAlign",
    "pBdr",
    "shd",
    "widowControl",
    "autoSpaceDE",
    "autoSpaceDN",
    "highlight",
    "ins",
    "del",
];

/// Any local ending in this suffix is a property container.
pub const PROPERTY_CONTAINER_SUFFIX: &str = "Pr";

/// Property containers that do not end in [`PROPERTY_CONTAINER_SUFFIX`].
pub const PROPERTY_CONTAINER_LOCALS: &[&str] = &["tblPrEx"];

/// Role of a substrate element, derived only from its Clark tag. A role is not a
/// view: a `residual` view anchors any element, and an unknown/foreign element is
/// a reference, never a paragraph/residual view.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReaderRole {
    Paragraph,
    Table,
    Row,
    Cell,
    Note,
    Control,
    NoteReference,
    Field,
    RevisionInsertion,
    RevisionDeletion,
    Context,
    Unknown,
    Foreign,
}

impl ReaderRole {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            ReaderRole::Paragraph => "paragraph",
            ReaderRole::Table => "table",
            ReaderRole::Row => "row",
            ReaderRole::Cell => "cell",
            ReaderRole::Note => "note",
            ReaderRole::Control => "control",
            ReaderRole::NoteReference => "note_reference",
            ReaderRole::Field => "field",
            ReaderRole::RevisionInsertion => "revision_insertion",
            ReaderRole::RevisionDeletion => "revision_deletion",
            ReaderRole::Context => "context",
            ReaderRole::Unknown => "unknown",
            ReaderRole::Foreign => "foreign",
        }
    }
}

/// Clark namespace of a tag (`{ns}local`), or `None` for an unbound name.
fn clark_namespace(clark_tag: &str) -> Option<&str> {
    let rest = clark_tag.strip_prefix('{')?;
    let close = rest.find('}')?;
    Some(&rest[..close])
}

/// Local name of a Clark tag; the whole tag when it is not Clark-qualified.
fn local_name(clark_tag: &str) -> &str {
    if let Some(close) = clark_tag.strip_prefix('{').and_then(|rest| rest.find('}')) {
        return &clark_tag[close + 2..];
    }
    clark_tag
}

/// True when the tag is namespaced in one of the three WordML namespaces.
fn is_wordml(clark_tag: &str) -> bool {
    matches!(clark_namespace(clark_tag), Some(ns) if WORDML_NAMESPACES.contains(&ns))
}

/// Property containers: end in `Pr` or are explicit exceptions.
fn is_property_container(local: &str) -> bool {
    local.ends_with(PROPERTY_CONTAINER_SUFFIX) || PROPERTY_CONTAINER_LOCALS.contains(&local)
}

/// A known WordML local (including any property container).
fn is_known_wordml_local(local: &str) -> bool {
    KNOWN_WORDML_LOCALS.contains(&local) || is_property_container(local)
}

/// Classifies a substrate element by its Clark tag. Foreign namespace wins over
/// the local name: a foreign `tab` is not a control.
pub fn role_of_tag(clark_tag: &str) -> ReaderRole {
    if !is_wordml(clark_tag) {
        return ReaderRole::Foreign;
    }
    let local = local_name(clark_tag);
    if local == "p" {
        return ReaderRole::Paragraph;
    }
    if local == "tbl" {
        return ReaderRole::Table;
    }
    if local == "tr" {
        return ReaderRole::Row;
    }
    if local == "tc" {
        return ReaderRole::Cell;
    }
    if NOTE_DEF_LOCALS.contains(&local) {
        return ReaderRole::Note;
    }
    if CONTROL_LOCALS.contains(&local) {
        return ReaderRole::Control;
    }
    if NOTE_REFERENCE_LOCALS.contains(&local) {
        return ReaderRole::NoteReference;
    }
    if FIELD_LOCALS.contains(&local) {
        return ReaderRole::Field;
    }
    if local == "ins" {
        return ReaderRole::RevisionInsertion;
    }
    if local == "del" {
        return ReaderRole::RevisionDeletion;
    }
    if is_known_wordml_local(local) {
        return ReaderRole::Context;
    }
    ReaderRole::Unknown
}

/// Value of the attribute whose *local* name is `local`, from the Clark-keyed
/// substrate `attrs` map.
fn attr_local<'a>(attrs: &'a BTreeMap<String, String>, local: &str) -> Option<&'a str> {
    attrs
        .iter()
        .find(|(key, _)| local_name(key) == local)
        .map(|(_, value)| value.as_str())
}

/// Generated kind for a documented WordML control, or `None`.
///
/// Only `w:tab`, `w:br`, `w:cr` are controls; `w:br w:type="page"` is a page
/// break and every other `w:br` is a line break. There is no `pageBreak` element
/// in WordML. An element outside this vocabulary is never rendered as a control,
/// only retained as a reference.
pub fn control_derived_kind(
    clark_tag: &str,
    attrs: &BTreeMap<String, String>,
) -> Option<ReaderDerivedKind> {
    if !is_wordml(clark_tag) {
        return None;
    }
    match local_name(clark_tag) {
        "tab" => Some(ReaderDerivedKind::Tab),
        "cr" => Some(ReaderDerivedKind::LineBreak),
        "br" => {
            if attr_local(attrs, "type") == Some("page") {
                Some(ReaderDerivedKind::PageBreak)
            } else {
                Some(ReaderDerivedKind::LineBreak)
            }
        }
        _ => None,
    }
}

/// Unresolved reference type for an element, or `None` when the element is a
/// known WordML context/structure element (not a reference).
///
/// A reference never inflates the fragment partition; `resolved` is always
/// false and is an S03 record concern, not part of this classification.
pub fn reference_type_of(
    clark_tag: &str,
    _attrs: &BTreeMap<String, String>,
) -> Option<ReaderReferenceType> {
    if !is_wordml(clark_tag) {
        return Some(ReaderReferenceType::ForeignElement);
    }
    let local = local_name(clark_tag);
    match local {
        "footnoteReference" => Some(ReaderReferenceType::NoteReference),
        "endnoteReference" => Some(ReaderReferenceType::EndnoteReference),
        "commentReference" => Some(ReaderReferenceType::CommentReference),
        "annotationRef" => Some(ReaderReferenceType::AnnotationReference),
        "fldChar" | "instrText" | "fldSimple" => Some(ReaderReferenceType::Field),
        _ if is_known_wordml_local(local) => None,
        _ => Some(ReaderReferenceType::UnknownWordmlElement),
    }
}

// ------------------------------------------------------------- record index #

/// Read-only index over substrate records: element ids in pre-order, text ids in
/// document order, `parent` links and per-element [`ReaderRole`]. It walks the
/// records only and never re-parses XML.
#[derive(Debug, Clone)]
pub struct ReaderRecordIndex {
    elements: Vec<ElementRecord>,
    texts: Vec<TextRecord>,
    element_pos: HashMap<String, usize>,
    text_pos: HashMap<String, usize>,
    parents: HashMap<String, Option<String>>,
    roles: HashMap<String, ReaderRole>,
}

fn malformed_index(detail: String) -> ContractError {
    ContractError::new(ContractErrorKind::MalformedIndex, detail)
}

impl ReaderRecordIndex {
    /// Builds the index, failing closed on a duplicate id, a missing `parent`,
    /// or a text `owner` that is not an element record.
    pub fn new(records: &[Record]) -> Result<Self, ContractError> {
        let mut elements: Vec<ElementRecord> = Vec::new();
        let mut texts: Vec<TextRecord> = Vec::new();
        let mut element_pos: HashMap<String, usize> = HashMap::new();
        let mut text_pos: HashMap<String, usize> = HashMap::new();
        for record in records {
            match record {
                Record::Element(element) => {
                    if element_pos.contains_key(&element.id) {
                        return Err(malformed_index(format!(
                            "duplicate element id {}",
                            element.id
                        )));
                    }
                    element_pos.insert(element.id.clone(), elements.len());
                    elements.push(element.clone());
                }
                Record::Text(text) => {
                    if text_pos.contains_key(&text.id) {
                        return Err(malformed_index(format!("duplicate text id {}", text.id)));
                    }
                    text_pos.insert(text.id.clone(), texts.len());
                    texts.push(text.clone());
                }
            }
        }
        let mut parents: HashMap<String, Option<String>> = HashMap::new();
        let mut roles: HashMap<String, ReaderRole> = HashMap::new();
        for element in &elements {
            if let Some(parent) = &element.parent {
                if !element_pos.contains_key(parent) {
                    return Err(malformed_index(format!(
                        "element {} parent {} is missing",
                        element.id, parent
                    )));
                }
            }
            parents.insert(element.id.clone(), element.parent.clone());
            roles.insert(element.id.clone(), role_of_tag(&element.clark_tag));
        }
        for text in &texts {
            if !element_pos.contains_key(&text.owner) {
                return Err(malformed_index(format!(
                    "text {} owner {} is missing",
                    text.id, text.owner
                )));
            }
        }
        Ok(ReaderRecordIndex {
            elements,
            texts,
            element_pos,
            text_pos,
            parents,
            roles,
        })
    }

    /// Element records in pre-order.
    pub fn elements(&self) -> &[ElementRecord] {
        &self.elements
    }

    /// Text records in document order.
    pub fn texts(&self) -> &[TextRecord] {
        &self.texts
    }

    /// Element record by id.
    pub fn element(&self, id: &str) -> Option<&ElementRecord> {
        self.element_pos.get(id).map(|index| &self.elements[*index])
    }

    /// Text record by id.
    pub fn text(&self, id: &str) -> Option<&TextRecord> {
        self.text_pos.get(id).map(|index| &self.texts[*index])
    }

    /// Role of an element by id.
    pub fn role_of(&self, id: &str) -> Option<ReaderRole> {
        self.roles.get(id).copied()
    }

    /// `source_pos`: pre-order index of an element record.
    pub fn source_pos(&self, id: &str) -> Option<usize> {
        self.element_pos.get(id).copied()
    }

    fn require_role(&self, id: &str) -> Result<ReaderRole, ContractError> {
        self.role_of(id)
            .ok_or_else(|| malformed_index(format!("unknown element reference {id}")))
    }

    fn parent_id<'a>(&'a self, id: &str) -> Result<Option<&'a str>, ContractError> {
        self.parents
            .get(id)
            .map(|parent| parent.as_deref())
            .ok_or_else(|| malformed_index(format!("unknown element reference {id}")))
    }
}

/// Nearest `paragraph`-role ancestor (including the element itself), else a
/// residual anchored by [`residual_anchor`].
pub fn view_key(
    index: &ReaderRecordIndex,
    element_ref: &ElementRef,
) -> Result<ReaderViewKey, ContractError> {
    let mut current = element_ref.as_str();
    loop {
        if index.require_role(current)? == ReaderRole::Paragraph {
            return Ok(ReaderViewKey::new(
                ReaderViewKind::Paragraph,
                ElementRef::new(current),
            ));
        }
        match index.parent_id(current)? {
            Some(parent) => current = parent,
            None => break,
        }
    }
    let anchor = residual_anchor(index, element_ref)?;
    Ok(ReaderViewKey::new(ReaderViewKind::Residual, anchor))
}

/// Walks the real `parent` links to the first parent whose role is in
/// {`table`, `row`, `cell`, `note`}; the element reached at that step is the
/// anchor. With no such parent the outermost reachable element is the anchor.
fn residual_anchor(
    index: &ReaderRecordIndex,
    element_ref: &ElementRef,
) -> Result<ElementRef, ContractError> {
    let mut current = element_ref.as_str();
    loop {
        match index.parent_id(current)? {
            None => return Ok(ElementRef::new(current)),
            Some(parent) => {
                if matches!(
                    index.require_role(parent)?,
                    ReaderRole::Table | ReaderRole::Row | ReaderRole::Cell | ReaderRole::Note
                ) {
                    return Ok(ElementRef::new(current));
                }
                current = parent;
            }
        }
    }
}

/// View a child's `tail` text belongs to: the parent paragraph when the parent
/// is a paragraph, otherwise a residual anchored at the tail-child position.
pub fn tail_view_key(
    index: &ReaderRecordIndex,
    child_ref: &ElementRef,
) -> Result<ReaderViewKey, ContractError> {
    if let Some(parent) = index.parent_id(child_ref.as_str())? {
        if index.require_role(parent)? == ReaderRole::Paragraph {
            return Ok(ReaderViewKey::new(
                ReaderViewKind::Paragraph,
                ElementRef::new(parent),
            ));
        }
    }
    let anchor = residual_anchor(index, child_ref)?;
    Ok(ReaderViewKey::new(ReaderViewKind::Residual, anchor))
}

// ----------------------------------------------------- coverage partition #

/// One primary-view ownership decision for a text record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PrimaryOwnership {
    pub fragment: FragmentRef,
    pub slot: TextSlot,
    pub view: ReaderViewKey,
}

/// Total ownership map from text records to primary views.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PartitionReport {
    pub entries: Vec<PrimaryOwnership>,
}

impl PartitionReport {
    /// Number of owned fragments.
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// True when no fragment is owned.
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Fragments referenced by more than one entry. Never non-empty for a report
    /// produced by [`partition_primary_views`]; injectable for a negative test.
    pub fn duplicates(&self) -> Vec<FragmentRef> {
        let mut counts: HashMap<&str, usize> = HashMap::new();
        let mut order: Vec<&str> = Vec::new();
        for entry in &self.entries {
            let id = entry.fragment.as_str();
            if !counts.contains_key(id) {
                order.push(id);
            }
            *counts.entry(id).or_insert(0) += 1;
        }
        order
            .into_iter()
            .filter(|id| counts[*id] > 1)
            .map(FragmentRef::from)
            .collect()
    }

    /// Entry fragments absent from the index text records.
    pub fn dangling(&self, index: &ReaderRecordIndex) -> Vec<FragmentRef> {
        self.entries
            .iter()
            .filter(|entry| index.text(entry.fragment.as_str()).is_none())
            .map(|entry| entry.fragment.clone())
            .collect()
    }

    /// Index text records referenced by no entry.
    pub fn missing(&self, index: &ReaderRecordIndex) -> Vec<FragmentRef> {
        let covered: HashSet<&str> = self
            .entries
            .iter()
            .map(|entry| entry.fragment.as_str())
            .collect();
        index
            .texts()
            .iter()
            .filter(|text| !covered.contains(text.id.as_str()))
            .map(|text| FragmentRef::from(text.id.as_str()))
            .collect()
    }

    /// True when every text record is referenced exactly once.
    pub fn is_complete(&self, index: &ReaderRecordIndex) -> bool {
        self.duplicates().is_empty()
            && self.dangling(index).is_empty()
            && self.missing(index).is_empty()
    }

    /// Fail-closed partition check; [`ContractErrorKind::PartitionIncomplete`]
    /// carries the duplicate / dangling / missing counts.
    pub fn check(&self, index: &ReaderRecordIndex) -> Result<(), ContractError> {
        let duplicates = self.duplicates();
        let dangling = self.dangling(index);
        let missing = self.missing(index);
        if duplicates.is_empty() && dangling.is_empty() && missing.is_empty() {
            return Ok(());
        }
        Err(ContractError::new(
            ContractErrorKind::PartitionIncomplete,
            format!(
                "partition incomplete: {} duplicate, {} dangling, {} missing fragment(s)",
                duplicates.len(),
                dangling.len(),
                missing.len()
            ),
        ))
    }

    /// Fragments owned by `key`, in document order.
    pub fn fragments_for(&self, key: &ReaderViewKey) -> Vec<FragmentRef> {
        self.entries
            .iter()
            .filter(|entry| entry.view == *key)
            .map(|entry| entry.fragment.clone())
            .collect()
    }
}

/// Assigns every text record to exactly one primary view: `text` slots through
/// [`view_key`], `tail` slots through [`tail_view_key`]. Fails closed when an
/// owner element is absent from the index (a malformed index).
pub fn partition_primary_views(
    index: &ReaderRecordIndex,
) -> Result<PartitionReport, ContractError> {
    let mut entries: Vec<PrimaryOwnership> = Vec::with_capacity(index.texts().len());
    for text in index.texts() {
        let owner = ElementRef::new(text.owner.as_str());
        let view = match text.slot {
            TextSlot::Text => view_key(index, &owner)?,
            TextSlot::Tail => tail_view_key(index, &owner)?,
        };
        entries.push(PrimaryOwnership {
            fragment: FragmentRef::from(text.id.as_str()),
            slot: text.slot,
            view,
        });
    }
    Ok(PartitionReport { entries })
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

// ------------------------------------------------------------------ T03 tests #

#[cfg(test)]
mod index_tests {
    use super::*;

    const NS: &str = "{http://schemas.microsoft.com/office/word/2003/wordml}";

    fn wordml(local: &str) -> String {
        format!("{NS}{local}")
    }

    fn attrs(entries: &[(&str, &str)]) -> BTreeMap<String, String> {
        entries
            .iter()
            .map(|(key, value)| (wordml(key), (*value).to_string()))
            .collect()
    }

    #[test]
    fn role_of_tag_maps_the_contract_vocabulary() {
        assert_eq!(role_of_tag(&wordml("p")), ReaderRole::Paragraph);
        assert_eq!(role_of_tag(&wordml("tbl")), ReaderRole::Table);
        assert_eq!(role_of_tag(&wordml("tr")), ReaderRole::Row);
        assert_eq!(role_of_tag(&wordml("tc")), ReaderRole::Cell);
        assert_eq!(role_of_tag(&wordml("footnote")), ReaderRole::Note);
        assert_eq!(role_of_tag(&wordml("endnote")), ReaderRole::Note);
        assert_eq!(role_of_tag(&wordml("tab")), ReaderRole::Control);
        assert_eq!(
            role_of_tag(&wordml("footnoteReference")),
            ReaderRole::NoteReference
        );
        assert_eq!(role_of_tag(&wordml("instrText")), ReaderRole::Field);
        assert_eq!(role_of_tag(&wordml("ins")), ReaderRole::RevisionInsertion);
        assert_eq!(role_of_tag(&wordml("del")), ReaderRole::RevisionDeletion);
        assert_eq!(role_of_tag(&wordml("pPr")), ReaderRole::Context);
        assert_eq!(role_of_tag(&wordml("tblPrEx")), ReaderRole::Context);
        assert_eq!(role_of_tag(&wordml("totallyUnknown")), ReaderRole::Unknown);
        assert_eq!(role_of_tag("{urn:elsewhere}tab"), ReaderRole::Foreign);
    }

    #[test]
    fn control_derived_kind_is_documented_only() {
        let empty = BTreeMap::new();
        assert_eq!(
            control_derived_kind(&wordml("tab"), &empty),
            Some(ReaderDerivedKind::Tab)
        );
        assert_eq!(
            control_derived_kind(&wordml("cr"), &empty),
            Some(ReaderDerivedKind::LineBreak)
        );
        assert_eq!(
            control_derived_kind(&wordml("br"), &empty),
            Some(ReaderDerivedKind::LineBreak)
        );
        assert_eq!(
            control_derived_kind(&wordml("br"), &attrs(&[("type", "page")])),
            Some(ReaderDerivedKind::PageBreak)
        );
        assert_eq!(control_derived_kind(&wordml("pageBreak"), &empty), None);
        assert_eq!(control_derived_kind("{urn:elsewhere}tab", &empty), None);
    }

    #[test]
    fn reference_type_of_maps_references_and_rejects_context() {
        let empty = BTreeMap::new();
        assert_eq!(
            reference_type_of(&wordml("footnoteReference"), &empty),
            Some(ReaderReferenceType::NoteReference)
        );
        assert_eq!(
            reference_type_of(&wordml("endnoteReference"), &empty),
            Some(ReaderReferenceType::EndnoteReference)
        );
        assert_eq!(
            reference_type_of(&wordml("commentReference"), &empty),
            Some(ReaderReferenceType::CommentReference)
        );
        assert_eq!(
            reference_type_of(&wordml("annotationRef"), &empty),
            Some(ReaderReferenceType::AnnotationReference)
        );
        assert_eq!(
            reference_type_of(&wordml("fldSimple"), &empty),
            Some(ReaderReferenceType::Field)
        );
        assert_eq!(
            reference_type_of(&wordml("strangeLocal"), &empty),
            Some(ReaderReferenceType::UnknownWordmlElement)
        );
        assert_eq!(
            reference_type_of("{urn:elsewhere}foreign", &empty),
            Some(ReaderReferenceType::ForeignElement)
        );
        assert_eq!(reference_type_of(&wordml("p"), &empty), None);
        assert_eq!(reference_type_of(&wordml("tbl"), &empty), None);
    }

    // Synthetic tree used by the view/partition unit tests.
    //
    //   e0 wordDocument
    //     e1 body
    //       e2 p (paragraph)
    //         e3 r
    //           e4 t "Alpha"   (t0)
    //       e5 tbl
    //         e6 tr
    //           e7 tc
    //             e8 p (paragraph inside cell)
    //               e9 r
    //                 e10 t "Beta"  (t1)
    //             e11 r (sibling residual anchor in the cell)
    //               e12 t "Tail"  (t2)
    fn element(id: &str, parent: Option<&str>, local: &str) -> Record {
        Record::Element(ElementRecord {
            kind: "element".into(),
            schema: "test".into(),
            id: id.into(),
            parent: parent.map(str::to_string),
            child_index: None,
            depth: 0,
            clark_tag: wordml(local),
            attrs: BTreeMap::new(),
            namespace_declarations: BTreeMap::new(),
            xml_space_declared: None,
            xml_space_effective: false,
            text_ref: None,
            tail_ref: None,
        })
    }

    fn text(id: &str, owner: &str, slot: TextSlot, value: &str) -> Record {
        Record::Text(TextRecord {
            kind: "text".into(),
            schema: "test".into(),
            id: id.into(),
            owner: owner.into(),
            slot,
            value: value.into(),
            chars: value.chars().count() as u64,
            bytes: value.len() as u64,
        })
    }

    fn synthetic() -> Vec<Record> {
        vec![
            element("e0", None, "wordDocument"),
            element("e1", Some("e0"), "body"),
            element("e2", Some("e1"), "p"),
            element("e3", Some("e2"), "r"),
            element("e4", Some("e3"), "t"),
            text("t0", "e4", TextSlot::Text, "Alpha"),
            element("e5", Some("e1"), "tbl"),
            element("e6", Some("e5"), "tr"),
            element("e7", Some("e6"), "tc"),
            element("e8", Some("e7"), "p"),
            element("e9", Some("e8"), "r"),
            element("e10", Some("e9"), "t"),
            text("t1", "e10", TextSlot::Text, "Beta"),
            element("e11", Some("e7"), "r"),
            element("e12", Some("e11"), "t"),
            text("t2", "e12", TextSlot::Text, "Tail"),
        ]
    }

    #[test]
    fn view_key_uses_nearest_paragraph_then_residual_anchor() {
        let index = ReaderRecordIndex::new(&synthetic()).unwrap();
        assert_eq!(
            view_key(&index, &ElementRef::from("e4")).unwrap(),
            ReaderViewKey::new(ReaderViewKind::Paragraph, ElementRef::from("e2"))
        );
        assert_eq!(
            view_key(&index, &ElementRef::from("e8")).unwrap(),
            ReaderViewKey::new(ReaderViewKind::Paragraph, ElementRef::from("e8"))
        );
        assert_eq!(
            view_key(&index, &ElementRef::from("e12")).unwrap(),
            ReaderViewKey::new(ReaderViewKind::Residual, ElementRef::from("e11"))
        );
    }

    #[test]
    fn tail_view_key_stays_in_the_parent_paragraph_or_becomes_cell_residual() {
        let index = ReaderRecordIndex::new(&synthetic()).unwrap();
        // A tail of a run inside a paragraph belongs to that paragraph.
        assert_eq!(
            tail_view_key(&index, &ElementRef::from("e3")).unwrap(),
            ReaderViewKey::new(ReaderViewKind::Paragraph, ElementRef::from("e2"))
        );
        // A tail of a paragraph inside a cell is a cell-level residual at the
        // paragraph position.
        assert_eq!(
            tail_view_key(&index, &ElementRef::from("e8")).unwrap(),
            ReaderViewKey::new(ReaderViewKind::Residual, ElementRef::from("e8"))
        );
    }

    #[test]
    fn partition_assigns_each_text_once_and_fails_closed_on_injection() {
        let index = ReaderRecordIndex::new(&synthetic()).unwrap();
        let report = partition_primary_views(&index).unwrap();
        assert_eq!(report.len(), 3);
        assert!(report.is_complete(&index));
        assert!(report.check(&index).is_ok());
        assert!(report.duplicates().is_empty());
        assert!(report.dangling(&index).is_empty());
        assert!(report.missing(&index).is_empty());
        assert_eq!(
            report.fragments_for(&ReaderViewKey::new(
                ReaderViewKind::Paragraph,
                ElementRef::from("e2")
            )),
            vec![FragmentRef::from("t0")]
        );
        assert_eq!(
            report.fragments_for(&ReaderViewKey::new(
                ReaderViewKind::Residual,
                ElementRef::from("e11")
            )),
            vec![FragmentRef::from("t2")]
        );

        let mut duplicate = report.clone();
        duplicate.entries.push(duplicate.entries[0].clone());
        assert_eq!(duplicate.duplicates().len(), 1);
        assert_eq!(
            duplicate.check(&index).unwrap_err().kind(),
            ContractErrorKind::PartitionIncomplete
        );

        let mut missing = report.clone();
        missing.entries.pop();
        assert_eq!(missing.missing(&index).len(), 1);
        assert!(missing.check(&index).is_err());

        let mut dangling = report.clone();
        dangling.entries.push(PrimaryOwnership {
            fragment: FragmentRef::from("tX"),
            slot: TextSlot::Text,
            view: ReaderViewKey::new(ReaderViewKind::Residual, ElementRef::from("e0")),
        });
        assert_eq!(dangling.dangling(&index).len(), 1);
        assert!(dangling.check(&index).is_err());
    }

    #[test]
    fn index_rejects_inconsistent_records() {
        // duplicate element id
        let mut records = synthetic();
        records.push(element("e0", Some("e1"), "p"));
        assert_eq!(
            ReaderRecordIndex::new(&records).unwrap_err().kind(),
            ContractErrorKind::MalformedIndex
        );
        // dangling parent
        let mut orphan = synthetic();
        orphan.push(element("e99", Some("e404"), "p"));
        assert_eq!(
            ReaderRecordIndex::new(&orphan).unwrap_err().kind(),
            ContractErrorKind::MalformedIndex
        );
        // text owner missing
        let mut bad_owner = synthetic();
        bad_owner.push(text("t404", "e404", TextSlot::Text, "x"));
        assert_eq!(
            ReaderRecordIndex::new(&bad_owner).unwrap_err().kind(),
            ContractErrorKind::MalformedIndex
        );
    }
}
