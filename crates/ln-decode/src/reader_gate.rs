//! Reader transfer gate over the frozen `source_package`.
//!
//! Bounded classification of a captured record stream against the pinned reader
//! profile `reader_wordml_profile/v1`. The gate answers one question only: can
//! the WordML reader accept this substrate? Classification is **root-bound**
//! (D636): the first element record (the document root, pre-order) must be a
//! `wordDocument` local name in one of [`WORDML_NAMESPACES`]. Foreign-namespaced
//! children are part of the supported profile (they become `foreign_element`
//! references in S02/S03) and never change the source class.
//!
//! The gate is **fail-closed**: an unsupported source yields a typed
//! [`GateRefusal`] rather than being silently promoted to reader support.
//! It reads only `source_package` records and the reader contract's namespace
//! set; it does not parse XML, build the projection, or carry reader-view
//! semantics. The module is serialization-free and has no XML-parser
//! dependency.
//!
//! Non-claims: this is not corpus coverage, not source authenticity, and not a
//! legal-completeness claim. R1000 stays active.
//!
//! Owning contract: `prd/architecture/reader-transfer-gate.md`.

use std::fmt;

use crate::reader_contract::{ContractError, ContractErrorKind, READER_PROFILE, WORDML_NAMESPACES};
use crate::source_package::{ElementRecord, Record};

/// Reader profile this gate classifies for.
///
/// Re-exported from [`READER_PROFILE`] so gate consumers pin the same profile
/// the reader contract declares.
pub const GATE_READER_PROFILE: &str = READER_PROFILE;

/// Root local name of the pinned reader profile.
pub const READER_ROOT_LOCAL: &str = "wordDocument";

// -------------------------------------------------------------- source class #

/// Closed source-class vocabulary of the reader transfer gate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReaderSourceClass {
    /// The root is a `wordDocument` in a recognised WordML namespace.
    SupportedWordml,
    /// The root element exists and is namespaced, but is not `wordDocument`.
    SourceNotWordml,
    /// The root is `wordDocument`, but its namespace is not a WordML namespace.
    UnsupportedSchema,
    /// The root element carries no namespace (absent or empty declaration).
    NamespaceAbsent,
    /// The record stream holds no element record at all.
    EmptySource,
}

impl ReaderSourceClass {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            ReaderSourceClass::SupportedWordml => "supported_wordml",
            ReaderSourceClass::SourceNotWordml => "source_not_wordml",
            ReaderSourceClass::UnsupportedSchema => "unsupported_schema",
            ReaderSourceClass::NamespaceAbsent => "namespace_absent",
            ReaderSourceClass::EmptySource => "empty_source",
        }
    }

    /// Fail-closed parse of the closed wire vocabulary.
    pub fn from_wire(token: &str) -> Result<Self, ContractError> {
        match token {
            "supported_wordml" => Ok(ReaderSourceClass::SupportedWordml),
            "source_not_wordml" => Ok(ReaderSourceClass::SourceNotWordml),
            "unsupported_schema" => Ok(ReaderSourceClass::UnsupportedSchema),
            "namespace_absent" => Ok(ReaderSourceClass::NamespaceAbsent),
            "empty_source" => Ok(ReaderSourceClass::EmptySource),
            _ => Err(ContractError::new(
                ContractErrorKind::UnknownToken,
                format!("unknown source_class token: {token:?}"),
            )),
        }
    }
}

// ------------------------------------------------------------------ refusal #

/// Typed reader-gate refusal. Carries the closed source class and a
/// human-readable detail; it never carries decoded source text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateRefusal {
    kind: ReaderSourceClass,
    detail: String,
}

impl GateRefusal {
    /// Builds a refusal from a source class and a structural detail.
    pub fn new(kind: ReaderSourceClass, detail: impl Into<String>) -> Self {
        GateRefusal {
            kind,
            detail: detail.into(),
        }
    }

    /// Refused source class.
    pub const fn kind(&self) -> ReaderSourceClass {
        self.kind
    }

    /// Human-readable detail (never parsed; for diagnostics only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for GateRefusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for GateRefusal {}

// ------------------------------------------------------------ classification #

/// Clark namespace of a tag (`{ns}local`), or `None` for an unbound/empty name.
fn clark_namespace(clark_tag: &str) -> Option<&str> {
    let rest = clark_tag.strip_prefix('{')?;
    let close = rest.find('}')?;
    Some(&rest[..close])
}

/// Local name of a Clark tag; the whole tag when it is not Clark-qualified.
fn local_name(clark_tag: &str) -> &str {
    match clark_tag.strip_prefix('{') {
        Some(rest) => match rest.find('}') {
            Some(close) => &rest[close + 1..],
            None => clark_tag,
        },
        None => clark_tag,
    }
}

/// The document root: the first element record in the pre-order element list.
fn root_element(records: &[Record]) -> Option<&ElementRecord> {
    records.iter().find_map(|record| match record {
        Record::Element(element) => Some(element),
        Record::Text(_) => None,
    })
}

/// Classifies a captured record stream. Total and fail-closed: it never indexes
/// and never assumes a well-formed document.
pub fn classify_source(records: &[Record]) -> ReaderSourceClass {
    let Some(root) = root_element(records) else {
        return ReaderSourceClass::EmptySource;
    };
    let Some(namespace) = clark_namespace(&root.clark_tag) else {
        return ReaderSourceClass::NamespaceAbsent;
    };
    if local_name(&root.clark_tag) != READER_ROOT_LOCAL {
        return ReaderSourceClass::SourceNotWordml;
    }
    if !WORDML_NAMESPACES.contains(&namespace) {
        return ReaderSourceClass::UnsupportedSchema;
    }
    ReaderSourceClass::SupportedWordml
}

fn refusal_detail(records: &[Record], class: ReaderSourceClass) -> String {
    match class {
        ReaderSourceClass::SupportedWordml => "supported".to_string(),
        ReaderSourceClass::EmptySource => "record stream has no element records".to_string(),
        ReaderSourceClass::NamespaceAbsent => match root_element(records) {
            Some(root) => format!(
                "root element {:?} has no namespace declaration",
                local_name(&root.clark_tag)
            ),
            None => "root element is absent".to_string(),
        },
        ReaderSourceClass::SourceNotWordml => match root_element(records) {
            Some(root) => format!(
                "root element local name {:?} is not {:?}",
                local_name(&root.clark_tag),
                READER_ROOT_LOCAL
            ),
            None => "root element is absent".to_string(),
        },
        ReaderSourceClass::UnsupportedSchema => match root_element(records) {
            Some(root) => format!(
                "root wordDocument namespace {:?} is not a recognised WordML namespace",
                clark_namespace(&root.clark_tag).unwrap_or("")
            ),
            None => "root element is absent".to_string(),
        },
    }
}

/// Gates a captured record stream. `Ok` only for
/// [`ReaderSourceClass::SupportedWordml`]; every other class is a typed
/// [`GateRefusal`], so an unsupported source can never be silently promoted.
pub fn gate_reader(records: &[Record]) -> Result<ReaderSourceClass, GateRefusal> {
    let class = classify_source(records);
    if class == ReaderSourceClass::SupportedWordml {
        return Ok(class);
    }
    Err(GateRefusal::new(class, refusal_detail(records, class)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::source_package::{capture, Limits};

    const WORDML_2003: &str = "http://schemas.microsoft.com/office/word/2003/wordml";
    const WORDML_OOXML: &str = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
    const WORDML_PURL: &str = "http://purl.oclc.org/ooxml/wordprocessingml/main";

    fn records(xml: &str) -> Vec<Record> {
        capture(xml.as_bytes(), &Limits::default())
            .expect("fixture must capture")
            .records()
            .to_vec()
    }

    fn classify(xml: &str) -> ReaderSourceClass {
        classify_source(&records(xml))
    }

    #[test]
    fn supported_wordml_for_all_three_namespaces() {
        for namespace in [WORDML_2003, WORDML_OOXML, WORDML_PURL] {
            let xml =
                format!(r#"<w:wordDocument xmlns:w="{namespace}"><w:body/></w:wordDocument>"#);
            assert_eq!(classify(&xml), ReaderSourceClass::SupportedWordml);
        }
    }

    #[test]
    fn foreign_child_stays_supported() {
        let xml = format!(
            r#"<w:wordDocument xmlns:w="{WORDML_2003}" xmlns:x="urn:law-nexus:foreign"><x:foo/></w:wordDocument>"#
        );
        let records = records(&xml);
        assert_eq!(
            classify_source(&records),
            ReaderSourceClass::SupportedWordml,
            "foreign-namespaced children are in-profile"
        );
        assert_eq!(
            gate_reader(&records),
            Ok(ReaderSourceClass::SupportedWordml)
        );
    }

    #[test]
    fn source_not_wordml_for_foreign_root() {
        let xml = r#"<note xmlns="urn:example:not-a-word-document"><body/></note>"#;
        assert_eq!(classify(xml), ReaderSourceClass::SourceNotWordml);
        let err = gate_reader(&records(xml)).expect_err("must refuse");
        assert_eq!(err.kind(), ReaderSourceClass::SourceNotWordml);
    }

    #[test]
    fn unsupported_schema_for_foreign_namespace_word_document() {
        let xml = r#"<w:wordDocument xmlns:w="urn:example:unsupported-wordml"><w:body/></w:wordDocument>"#;
        assert_eq!(classify(xml), ReaderSourceClass::UnsupportedSchema);
        let err = gate_reader(&records(xml)).expect_err("must refuse");
        assert_eq!(err.kind(), ReaderSourceClass::UnsupportedSchema);
    }

    #[test]
    fn namespace_absent_for_unqualified_root() {
        let xml = r#"<wordDocument><body/></wordDocument>"#;
        assert_eq!(classify(xml), ReaderSourceClass::NamespaceAbsent);
        let err = gate_reader(&records(xml)).expect_err("must refuse");
        assert_eq!(err.kind(), ReaderSourceClass::NamespaceAbsent);
    }

    #[test]
    fn empty_source_for_no_element_records() {
        let empty: Vec<Record> = Vec::new();
        assert_eq!(classify_source(&empty), ReaderSourceClass::EmptySource);
        let err = gate_reader(&empty).expect_err("must refuse");
        assert_eq!(err.kind(), ReaderSourceClass::EmptySource);
    }

    #[test]
    fn gate_accepts_only_supported_wordml() {
        let xml = format!(r#"<w:wordDocument xmlns:w="{WORDML_2003}"/>"#);
        assert_eq!(
            gate_reader(&records(&xml)),
            Ok(ReaderSourceClass::SupportedWordml)
        );
    }

    #[test]
    fn source_class_wire_vocabulary_is_closed() {
        for class in [
            ReaderSourceClass::SupportedWordml,
            ReaderSourceClass::SourceNotWordml,
            ReaderSourceClass::UnsupportedSchema,
            ReaderSourceClass::NamespaceAbsent,
            ReaderSourceClass::EmptySource,
        ] {
            assert_eq!(
                ReaderSourceClass::from_wire(class.as_str()).expect("round-trip"),
                class
            );
        }
        let err = ReaderSourceClass::from_wire("bogus").expect_err("unknown token must fail");
        assert_eq!(err.kind(), ContractErrorKind::UnknownToken);
    }

    #[test]
    fn refusal_detail_carries_no_decoded_text() {
        let xml =
            r#"<note xmlns="urn:example:not-a-word-document"><p>SECRET-LEGAL-TEXT</p></note>"#;
        let err = gate_reader(&records(xml)).expect_err("must refuse");
        assert!(!err.detail().contains("SECRET-LEGAL-TEXT"));
    }

    #[test]
    fn gate_module_has_no_serialization_or_xml_parser_dependency() {
        let source = include_str!("reader_gate.rs");
        let serde_use = ["use", "serde"].join(" ");
        let xml_parser = ["quick", "_xml"].join("");
        assert!(!source.contains(serde_use.as_str()));
        assert!(!source.contains(xml_parser.as_str()));
    }
}
