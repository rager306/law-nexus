//! Bounded source-preserving JSONL package: XML bytes -> decoded-source records -> verify.
//!
//! One observable vertical capability: capture decoded content from supplied XML
//! bytes into a strict, versioned, LF-terminated JSONL package (`manifest`
//! first, `element`/`text` records, `footer` last), then read it back through a
//! structural package verifier (not an independent XML oracle).
//!
//! ## What this is
//!
//! A **decoded source model**, not an XML lexical byte roundtrip. It carries:
//!
//! * one `element` record per source element, in pre-order, with a source-local
//!   id (`e0..eN`), `parent` / `child_index` / `depth` for navigation, the Clark
//!   tag, the Clark attributes, the namespace declarations **declared on that
//!   element**, and the declared/inherited `xml:space` state;
//! * one `text` record per non-empty element `text` / `tail` slot, in document
//!   order, stored once with an owner reference and the `text` / `tail` slot.
//!   All decoded Unicode text is preserved verbatim — whitespace and NBSP
//!   included, no collapsing, no trimming.
//!
//! It carries **no XML byte coordinates**, and it does not preserve CDATA
//! boundaries, attribute order, entity syntax, comments, processing
//! instructions, or the XML declaration. Those policies are declared in the
//! manifest `policies` and re-checked by the verifier.
//!
//! ## Bounded memory
//!
//! [`capture`] parses the whole bounded document in memory (`max_input_bytes`):
//! this is explicitly **not** a streaming decoder. Every cap is hard
//! fail-closed; a cap breach returns an error and produces no package.
//!
//! ## Trust boundary
//!
//! The footer `capture_status: "complete"` means the **bounded capture policy**
//! completed over the supplied bytes. It is **not** a claim of legal
//! completeness, source authenticity, corpus coverage, or reference/cleaning
//! semantics. `source_sha256` and the deterministic record seal are integrity
//! checks, not authenticity: an actor who controls the bytes can recompute
//! them. [`verify_against_source`] re-runs the same capture on supplied XML and
//! compares structurally; it is **not independent proof** because it shares the
//! capture algorithm.
//!
//! Out of scope for this slice: reader/clean/literal-run projection, tokenization,
//! JEV semantic identity, filesystem atomic publish, and any CLI.

use std::borrow::Cow;
use std::collections::{BTreeMap, HashMap, HashSet};
use std::fmt;
use std::io::{BufRead, Write};

use quick_xml::events::attributes::AttrError;
use quick_xml::events::{BytesStart, Event};
use quick_xml::name::ResolveResult;
use quick_xml::NsReader;
use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use serde_json::Value;
use sha2::{Digest, Sha256};

/// Manifest schema tag.
pub const MANIFEST_SCHEMA: &str = "law-nexus/source-package-manifest/v1";
/// Footer schema tag.
pub const FOOTER_SCHEMA: &str = "law-nexus/source-package-footer/v1";
/// Element record schema tag.
pub const ELEMENT_SCHEMA: &str = "law-nexus/source-package-element/v1";
/// Text record schema tag.
pub const TEXT_SCHEMA: &str = "law-nexus/source-package-text/v1";
/// Model name.
pub const MODEL: &str = "law-nexus/source-package-model/v1";
/// Profile name.
pub const PROFILE: &str = "source_package_decoded_text/v1";
/// Capability name.
pub const CAPABILITY: &str = "source_package_jsonl";
/// Schema version pinned by this slice.
pub const SCHEMA_VERSION: u64 = 1;

const CAPTURE_POLICY: &str = "bounded_whole_document_memory_hard_fail_closed";
const COMPLETION_BASIS: &str =
    "bounded_capture_policy_complete_not_legal_completeness_not_authenticity";
const XML_SPACE_CLARK: &str = "{http://www.w3.org/XML/1998/namespace}space";
const DUPLICATE_KEY_SENTINEL: &str = "__gs_duplicate_json_key__";

// ------------------------------------------------------------------ limits #

/// Hard fail-closed capture/read limits. All values are `u64`; a `bool` or any
/// non-integer JSON token is rejected by the typed deserializer.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Limits {
    /// Maximum XML input bytes accepted by [`capture`].
    pub max_input_bytes: u64,
    /// Maximum serialized package bytes accepted by [`read_package`] / written.
    pub max_package_bytes: u64,
    /// Maximum bytes in a single JSONL line.
    pub max_line_bytes: u64,
    /// Maximum element nesting depth.
    pub max_depth: u64,
    /// Maximum number of element records.
    pub max_nodes: u64,
    /// Maximum number of text fragment records.
    pub max_text_fragments: u64,
    /// Maximum decoded text bytes across all fragments.
    pub max_text_bytes: u64,
    /// Maximum total records (elements + text fragments).
    pub max_records: u64,
    /// Maximum attributes + namespace declarations per element.
    pub max_attrs_per_element: u64,
}

impl Default for Limits {
    fn default() -> Self {
        Limits {
            max_input_bytes: 64 * 1024 * 1024,
            max_package_bytes: 512 * 1024 * 1024,
            max_line_bytes: 64 * 1024 * 1024,
            max_depth: 4096,
            max_nodes: 2_000_000,
            max_text_fragments: 2_000_000,
            max_text_bytes: 512 * 1024 * 1024,
            max_records: 4_000_000,
            max_attrs_per_element: 1024,
        }
    }
}

// ----------------------------------------------------------------- policies #

/// Declared preservation/exclusion policies. Every field is re-checked by the
/// verifier against its pinned constant.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Policies {
    pub text_scope: String,
    pub document_level_text: String,
    pub directive_records: String,
    pub cdata_boundaries: String,
    pub entity_scope: String,
    pub binary_payloads: String,
    pub unknown_elements: String,
    pub namespaces: String,
    pub xml_space: String,
    pub raw_xml_lexical_form: String,
    pub memory_model: String,
    pub authenticity: String,
}

impl Policies {
    fn expected() -> Policies {
        Policies {
            text_scope: "element_text_and_tail_slots".to_string(),
            document_level_text: "outside_root_excluded_not_claimed".to_string(),
            directive_records: "comments_pi_declaration_excluded_metadata_not_claimed".to_string(),
            cdata_boundaries: "not_preserved".to_string(),
            entity_scope: "predefined_and_numeric_only_dtd_rejected".to_string(),
            binary_payloads: "all_decoded_text_retained_no_exclusions".to_string(),
            unknown_elements: "retained".to_string(),
            namespaces: "clark_resolved_declarations_recorded".to_string(),
            xml_space: "declared_and_inherited_recorded".to_string(),
            raw_xml_lexical_form: "not_preserved_not_claimed".to_string(),
            memory_model: "bounded_whole_document_not_streaming".to_string(),
            authenticity: "integrity_only_not_authenticity".to_string(),
        }
    }
}

// ------------------------------------------------------------------ records #

/// Element `text` / `tail` slot discriminator.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum TextSlot {
    Text,
    Tail,
}

impl TextSlot {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            TextSlot::Text => "text",
            TextSlot::Tail => "tail",
        }
    }
}

/// One source element record.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ElementRecord {
    pub kind: String,
    pub schema: String,
    pub id: String,
    // Nullable members are still **required keys**: `required_nullable` makes a
    // missing key a typed error while accepting an explicit `null` value.
    #[serde(deserialize_with = "required_nullable")]
    pub parent: Option<String>,
    #[serde(deserialize_with = "required_nullable")]
    pub child_index: Option<u64>,
    pub depth: u64,
    pub clark_tag: String,
    pub attrs: BTreeMap<String, String>,
    pub namespace_declarations: BTreeMap<String, String>,
    #[serde(deserialize_with = "required_nullable")]
    pub xml_space_declared: Option<bool>,
    pub xml_space_effective: bool,
    #[serde(deserialize_with = "required_nullable")]
    pub text_ref: Option<String>,
    #[serde(deserialize_with = "required_nullable")]
    pub tail_ref: Option<String>,
}

/// One decoded text fragment record. `value` is the exact decoded Unicode text
/// (whitespace and NBSP included).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TextRecord {
    pub kind: String,
    pub schema: String,
    pub id: String,
    pub owner: String,
    pub slot: TextSlot,
    pub value: String,
    pub chars: u64,
    pub bytes: u64,
}

/// A package body record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Record {
    Element(ElementRecord),
    Text(TextRecord),
}

impl Record {
    /// Closed kind string.
    pub const fn kind(&self) -> &'static str {
        match self {
            Record::Element(_) => "element",
            Record::Text(_) => "text",
        }
    }
}

impl Serialize for Record {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        match self {
            Record::Element(record) => record.serialize(serializer),
            Record::Text(record) => record.serialize(serializer),
        }
    }
}

// ------------------------------------------------------------------ counts #

/// Intrinsic counts recomputed from the records by the verifier.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Counts {
    pub elements: u64,
    pub text_fragments: u64,
    pub text_chars: u64,
    pub text_bytes: u64,
    pub namespace_declarations: u64,
    pub records: u64,
}

// ---------------------------------------------------------------- manifest #

/// Source identity carried as integrity evidence only.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceRef {
    pub sha256: String,
    pub bytes: u64,
}

/// The first line of a package.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub kind: String,
    pub schema: String,
    pub version: u64,
    pub model: String,
    pub profile: String,
    pub capability: String,
    pub capture_policy: String,
    pub source: SourceRef,
    pub limits: Limits,
    pub policies: Policies,
    pub non_authoritative: bool,
}

// ------------------------------------------------------------------ footer #

/// Capture-policy completion state. Only `complete` is emitted; any other token
/// is rejected by the typed deserializer.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum CaptureStatus {
    Complete,
}

/// The last line of a package.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Footer {
    pub kind: String,
    pub schema: String,
    pub version: u64,
    pub capture_status: CaptureStatus,
    pub completion_basis: String,
    pub source_sha256: String,
    pub counts: Counts,
    #[serde(
        skip_serializing_if = "Option::is_none",
        deserialize_with = "required_nullable"
    )]
    pub records_seal_hash: Option<String>,
    #[serde(
        skip_serializing_if = "Option::is_none",
        deserialize_with = "required_nullable"
    )]
    pub manifest_hash: Option<String>,
    pub non_authoritative: bool,
}

// ----------------------------------------------------------------- package #

/// A parsed/validated source package.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Package {
    manifest: Manifest,
    records: Vec<Record>,
    footer: Footer,
}

impl Package {
    /// Borrow the manifest.
    pub fn manifest(&self) -> &Manifest {
        &self.manifest
    }

    /// Borrow the records.
    pub fn records(&self) -> &[Record] {
        &self.records
    }

    /// Borrow the footer.
    pub fn footer(&self) -> &Footer {
        &self.footer
    }

    /// Build a package from raw parts **without** sealing or validation.
    ///
    /// Diagnostic/test surface only: it is not part of the supported production
    /// API. Call [`Package::resign`] to recompute the seal, then
    /// [`Package::verify`] to gate. Production callers should use [`capture`] or
    /// [`read_package`].
    #[doc(hidden)]
    pub fn from_parts(manifest: Manifest, records: Vec<Record>, footer: Footer) -> Package {
        Package {
            manifest,
            records,
            footer,
        }
    }

    /// Recompute `records_seal_hash` and `manifest_hash` from the current parts.
    /// This repairs integrity hashes only; it does **not** validate structure.
    #[doc(hidden)]
    pub fn resign(&mut self) -> Result<(), SourcePackageError> {
        self.footer.records_seal_hash = Some(records_seal_hash(&self.records)?);
        self.footer.manifest_hash =
            Some(manifest_hash(&self.manifest, &self.records, &self.footer)?);
        Ok(())
    }

    /// Determine whether the package JSONL ends with a single LF.
    pub fn is_lf_terminated(text: &str) -> bool {
        text.ends_with('\n') && !text.contains('\r')
    }

    /// Serialize the package to LF-terminated JSONL.
    ///
    /// The package is verified (structure, counts, topology, seals) and checked
    /// against its declared export limits before any line is produced, so this
    /// public method never emits a package that would not read back. Diagnostic
    /// callers that intentionally hold inconsistent parts must use
    /// [`Package::from_parts`]/[`Package::resign`] and inspect them without
    /// serializing.
    pub fn to_jsonl(&self) -> Result<String, SourcePackageError> {
        let limits = &self.manifest.limits;
        self.verify_with(limits)?;
        self.check_exportable(limits)?;
        let mut out = canonical_json(&self.manifest)?;
        for record in &self.records {
            out.push('\n');
            out.push_str(&serialize_record(record)?);
        }
        out.push('\n');
        out.push_str(&canonical_json(&self.footer)?);
        out.push('\n');
        Ok(out)
    }

    /// Validate the package, then write it. Nothing is written when validation
    /// fails. A mid-stream writer error is surfaced; a partially written stream
    /// never contains an accepted footer. The effective caps are the per-field
    /// minimum of `limits` and the package's declared manifest limits.
    pub fn write_to<W: Write>(
        &self,
        writer: &mut W,
        limits: &Limits,
    ) -> Result<(), SourcePackageError> {
        let effective = effective_limits(limits, &self.manifest.limits);
        self.verify_with(&effective)?;
        self.check_exportable(&effective)?;
        let text = self.to_jsonl()?;
        writer
            .write_all(text.as_bytes())
            .map_err(SourcePackageError::from_io)?;
        Ok(())
    }

    /// Verify the closed manifest/footer contracts, the intrinsic counts, the
    /// record seal, the element topology, the text/tail ownership and document
    /// order, and the reference integrity. This is the source-free half; the
    /// source-grounded comparison is [`verify_against_source`].
    pub fn verify(&self) -> Result<(), SourcePackageError> {
        self.verify_with(&self.manifest.limits)
    }

    /// Verify with an externally supplied cap set. Callers use the per-field
    /// minimum of their own caps and the package's declared limits, so a package
    /// can only tighten the caller's ceiling.
    fn verify_with(&self, limits: &Limits) -> Result<(), SourcePackageError> {
        verify_package(self, limits)
    }

    /// Confirm the package serializes under `limits` without building the whole
    /// JSONL string: each canonical line is checked and the running total is
    /// checked against the package cap.
    fn check_exportable(&self, limits: &Limits) -> Result<(), SourcePackageError> {
        let mut total: u64 = 0;
        let mut line_index: u64 = 0;
        let mut check = |line_len: u64| -> Result<(), SourcePackageError> {
            if line_len > limits.max_line_bytes {
                return Err(SourcePackageError::new(
                    ErrorKind::LineTooLong,
                    format!("line {line_index} exceeds cap {}", limits.max_line_bytes),
                ));
            }
            total = total.saturating_add(line_len.saturating_add(1));
            if total > limits.max_package_bytes {
                return Err(SourcePackageError::new(
                    ErrorKind::PackageTooLarge,
                    format!("package exceeds cap {}", limits.max_package_bytes),
                ));
            }
            line_index = line_index.saturating_add(1);
            Ok(())
        };
        check(canonical_json(&self.manifest)?.len() as u64)?;
        for record in &self.records {
            check(serialize_record(record)?.len() as u64)?;
        }
        check(canonical_json(&self.footer)?.len() as u64)?;
        Ok(())
    }

    /// True when the decoded records and the semantic profile identity match.
    /// Execution limits and integrity hashes are deliberately not compared.
    fn semantically_equal(&self, other: &Package) -> bool {
        self.manifest.model == other.manifest.model
            && self.manifest.profile == other.manifest.profile
            && self.manifest.capability == other.manifest.capability
            && self.manifest.policies == other.manifest.policies
            && self.records == other.records
    }
}

/// Outcome of [`verify_against_source`]. Both flags are explicit; neither is an
/// independent authenticity or completeness proof.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SourceComparison {
    /// The package's declared `source_sha256` equals the sha256 of the supplied bytes.
    pub source_sha256_matches: bool,
    /// The decoded records and the semantic profile identity are equal. Execution
    /// limits, integrity hashes, and the source byte digest are not compared.
    pub structurally_equal: bool,
}

// ------------------------------------------------------------------ errors #

/// Stable, branchable error kinds. Details are bounded, typed metadata and never
/// carry decoded source text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorKind {
    InputTooLarge,
    PackageTooLarge,
    LineTooLong,
    NonUtf8Input,
    NonUtf8Package,
    UnsupportedEncoding,
    DtdForbidden,
    MalformedXml,
    MultipleRoots,
    NoRoot,
    UnclosedElements,
    DocumentLevelText,
    UnboundPrefix,
    DuplicateAttribute,
    AttributeCountExceeded,
    InvalidXmlSpace,
    DepthExceeded,
    NodeCapExceeded,
    TextFragmentCapExceeded,
    TextByteCapExceeded,
    RecordCapExceeded,
    MissingTrailingLf,
    CarriageReturnForbidden,
    EmptyLine,
    EmptyPackage,
    MissingFooter,
    MisorderedFooter,
    MissingManifest,
    MisorderedManifest,
    JsonSyntax,
    DuplicateJsonKey,
    TypeMismatch,
    UnknownKind,
    SchemaMismatch,
    VersionUnsupported,
    SourceHashMismatch,
    HashMissing,
    HashMalformed,
    RecordsSealMismatch,
    ManifestHashMismatch,
    CountMismatch,
    DuplicateRecordId,
    SectionOrderMismatch,
    RootCount,
    ParentDangling,
    DepthMismatch,
    ChildIndexMismatch,
    ElementOrderMismatch,
    TextOwnerDangling,
    TextSlotDuplicate,
    TextRefDangling,
    TextRefMismatch,
    TextOrderMismatch,
    TextLengthMismatch,
    InvalidXmlChar,
    LimitExceeded,
    Serialization,
    Io,
}

impl ErrorKind {
    const fn as_str(self) -> &'static str {
        use ErrorKind::*;
        match self {
            InputTooLarge => "input_too_large",
            PackageTooLarge => "package_too_large",
            LineTooLong => "line_too_long",
            NonUtf8Input => "non_utf8_input",
            NonUtf8Package => "non_utf8_package",
            UnsupportedEncoding => "unsupported_encoding",
            DtdForbidden => "dtd_forbidden",
            MalformedXml => "malformed_xml",
            MultipleRoots => "multiple_roots",
            NoRoot => "no_root",
            UnclosedElements => "unclosed_elements",
            DocumentLevelText => "document_level_text",
            UnboundPrefix => "unbound_prefix",
            DuplicateAttribute => "duplicate_attribute",
            AttributeCountExceeded => "attribute_count_exceeded",
            InvalidXmlSpace => "invalid_xml_space",
            DepthExceeded => "depth_exceeded",
            NodeCapExceeded => "node_cap_exceeded",
            TextFragmentCapExceeded => "text_fragment_cap_exceeded",
            TextByteCapExceeded => "text_byte_cap_exceeded",
            RecordCapExceeded => "record_cap_exceeded",
            MissingTrailingLf => "missing_trailing_lf",
            CarriageReturnForbidden => "carriage_return_forbidden",
            EmptyLine => "empty_line",
            EmptyPackage => "empty_package",
            MissingFooter => "missing_footer",
            MisorderedFooter => "misordered_footer",
            MissingManifest => "missing_manifest",
            MisorderedManifest => "misordered_manifest",
            JsonSyntax => "json_syntax",
            DuplicateJsonKey => "duplicate_json_key",
            TypeMismatch => "type_mismatch",
            UnknownKind => "unknown_kind",
            SchemaMismatch => "schema_mismatch",
            VersionUnsupported => "version_unsupported",
            SourceHashMismatch => "source_hash_mismatch",
            HashMissing => "hash_missing",
            HashMalformed => "hash_malformed",
            RecordsSealMismatch => "records_seal_mismatch",
            ManifestHashMismatch => "manifest_hash_mismatch",
            CountMismatch => "count_mismatch",
            DuplicateRecordId => "duplicate_record_id",
            SectionOrderMismatch => "section_order_mismatch",
            RootCount => "root_count",
            ParentDangling => "parent_dangling",
            DepthMismatch => "depth_mismatch",
            ChildIndexMismatch => "child_index_mismatch",
            ElementOrderMismatch => "element_order_mismatch",
            TextOwnerDangling => "text_owner_dangling",
            TextSlotDuplicate => "text_slot_duplicate",
            TextRefDangling => "text_ref_dangling",
            TextRefMismatch => "text_ref_mismatch",
            TextOrderMismatch => "text_order_mismatch",
            TextLengthMismatch => "text_length_mismatch",
            InvalidXmlChar => "invalid_xml_char",
            LimitExceeded => "limit_exceeded",
            Serialization => "serialization",
            Io => "io",
        }
    }
}

/// A fail-closed source-package error. `detail` is bounded, typed metadata and
/// never carries decoded source text.
#[derive(Debug, Clone)]
pub struct SourcePackageError {
    kind: ErrorKind,
    detail: String,
}

impl SourcePackageError {
    fn new(kind: ErrorKind, detail: impl Into<String>) -> SourcePackageError {
        SourcePackageError {
            kind,
            detail: truncate_detail(detail.into()),
        }
    }

    fn from_io(error: std::io::Error) -> SourcePackageError {
        SourcePackageError::new(ErrorKind::Io, format!("{}", error.kind()))
    }

    /// The stable error kind.
    pub fn kind(&self) -> ErrorKind {
        self.kind
    }

    /// The bounded diagnostic detail (never decoded source text).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for SourcePackageError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.detail.is_empty() {
            write!(formatter, "source package error: {}", self.kind.as_str())
        } else {
            write!(
                formatter,
                "source package error: {}: {}",
                self.kind.as_str(),
                self.detail
            )
        }
    }
}

impl std::error::Error for SourcePackageError {}

fn truncate_detail(mut detail: String) -> String {
    const MAX: usize = 200;
    if detail.len() > MAX {
        // Keep the bound on bytes but never split a UTF-8 scalar.
        let mut cut = MAX;
        while cut > 0 && !detail.is_char_boundary(cut) {
            cut -= 1;
        }
        detail.truncate(cut);
    }
    detail
}

// ------------------------------------------------------------- public API #

/// Capture decoded content from supplied XML bytes into a bounded source package.
///
/// Hard fail-closed: any malformed input or exceeded limit returns an error and
/// no package. The parse holds the whole bounded document in memory. XML 1.0
/// end-of-line normalization (`\r\n`/`\r` -> `\n`) is applied to literal input
/// before parsing; character references are preserved. `source_sha256` is
/// computed over the original, un-normalized bytes.
pub fn capture(xml: &[u8], limits: &Limits) -> Result<Package, SourcePackageError> {
    if xml.len() as u64 > limits.max_input_bytes {
        return Err(SourcePackageError::new(
            ErrorKind::InputTooLarge,
            format!("input {} > cap {}", xml.len(), limits.max_input_bytes),
        ));
    }
    let text = std::str::from_utf8(xml).map_err(|_| {
        SourcePackageError::new(ErrorKind::NonUtf8Input, "input is not valid UTF-8")
    })?;
    let source_sha256 = sha256_hex(xml);

    // XML 1.0 section 2.11: literal CRLF and CR are normalized to LF before
    // parsing. Character references are untouched (they contain no literal CR).
    let normalized: Cow<'_, str> = if text.contains('\r') {
        Cow::Owned(normalize_eol(text))
    } else {
        Cow::Borrowed(text)
    };
    let mut reader = NsReader::from_str(normalized.as_ref());
    reader.config_mut().trim_text(false);
    // A `--` sequence inside a comment is ill-formed XML. quick-xml does not
    // validate comments by default; enable the bounded check so excluded
    // comment metadata cannot carry syntactically invalid markup.
    reader.config_mut().check_comments = true;

    let mut nodes: Vec<Node> = Vec::new();
    let mut stack: Vec<usize> = Vec::new();
    let mut root: Option<usize> = None;
    let mut declared = false;
    let mut started = false;
    let mut total_text_bytes: u64 = 0;

    loop {
        let (_resolve, event) = reader
            .read_resolved_event()
            .map_err(|_| SourcePackageError::new(ErrorKind::MalformedXml, "xml read failed"))?;
        match event {
            Event::Start(start) => {
                started = true;
                let index = begin_element(&mut nodes, &stack, &mut root, &start, &reader, limits)?;
                stack.push(index);
            }
            Event::Empty(start) => {
                started = true;
                let index = begin_element(&mut nodes, &stack, &mut root, &start, &reader, limits)?;
                finish_element(&mut nodes, index);
            }
            Event::End(_) => {
                started = true;
                let index = stack.pop().ok_or_else(|| {
                    SourcePackageError::new(ErrorKind::MalformedXml, "unexpected end tag")
                })?;
                finish_element(&mut nodes, index);
            }
            Event::Text(event) => {
                started = true;
                let value = event.unescape().map_err(|_| {
                    SourcePackageError::new(ErrorKind::MalformedXml, "text unescape failed")
                })?;
                validate_xml_chars(value.as_ref())?;
                handle_text(
                    &mut nodes,
                    &stack,
                    value.as_ref(),
                    &mut total_text_bytes,
                    limits,
                )?;
            }
            Event::CData(cdata) => {
                started = true;
                let bytes = cdata.into_inner().into_owned();
                let value = std::str::from_utf8(&bytes).map_err(|_| {
                    SourcePackageError::new(ErrorKind::MalformedXml, "cdata is not UTF-8")
                })?;
                validate_xml_chars(value)?;
                handle_text(&mut nodes, &stack, value, &mut total_text_bytes, limits)?;
            }
            Event::Comment(_) | Event::PI(_) => {
                // Explicit policy: comments and processing instructions are
                // excluded metadata, never carried and never claimed.
                started = true;
            }
            Event::Decl(decl) => {
                if declared || started {
                    return Err(SourcePackageError::new(
                        ErrorKind::MalformedXml,
                        "xml declaration must appear once at the document start",
                    ));
                }
                declared = true;
                // Reject duplicate, unknown, and ill-formed declaration attributes.
                // `BytesDecl` has no attribute iterator, so reconstruct the
                // `BytesStart` view over its raw content (name length 3 = "xml").
                let raw_decl: &[u8] = &decl;
                let decl_start =
                    BytesStart::from_content(String::from_utf8_lossy(raw_decl).into_owned(), 3);
                let mut seen_attrs: HashSet<Vec<u8>> = HashSet::new();
                for attribute in decl_start.attributes() {
                    let attribute = attribute.map_err(|_| {
                        SourcePackageError::new(
                            ErrorKind::MalformedXml,
                            "xml declaration attribute is malformed",
                        )
                    })?;
                    let key = attribute.key.as_ref().to_vec();
                    if !seen_attrs.insert(key.clone()) {
                        return Err(SourcePackageError::new(
                            ErrorKind::MalformedXml,
                            "xml declaration has a duplicate attribute",
                        ));
                    }
                    if key != b"version" && key != b"encoding" && key != b"standalone" {
                        return Err(SourcePackageError::new(
                            ErrorKind::MalformedXml,
                            "xml declaration has an unknown attribute",
                        ));
                    }
                }
                let version = decl.version().map_err(|_| {
                    SourcePackageError::new(
                        ErrorKind::MalformedXml,
                        "xml declaration version is missing or malformed",
                    )
                })?;
                if version.as_ref() != b"1.0" {
                    return Err(SourcePackageError::new(
                        ErrorKind::VersionUnsupported,
                        "only xml version 1.0 is supported",
                    ));
                }
                if let Some(encoding) = decl.encoding() {
                    let encoding = encoding.map_err(|_| {
                        SourcePackageError::new(
                            ErrorKind::UnsupportedEncoding,
                            "xml declaration encoding is malformed",
                        )
                    })?;
                    let name = String::from_utf8_lossy(&encoding).to_lowercase();
                    if name != "utf-8" && name != "utf8" {
                        return Err(SourcePackageError::new(
                            ErrorKind::UnsupportedEncoding,
                            "declared encoding is not UTF-8",
                        ));
                    }
                }
            }
            Event::DocType(_) => {
                return Err(SourcePackageError::new(
                    ErrorKind::DtdForbidden,
                    "DTD/doctype is forbidden",
                ));
            }
            Event::Eof => break,
        }
    }

    if !stack.is_empty() {
        return Err(SourcePackageError::new(
            ErrorKind::UnclosedElements,
            format!("{} element(s) left open", stack.len()),
        ));
    }
    let root = root.ok_or_else(|| SourcePackageError::new(ErrorKind::NoRoot, "no root element"))?;
    if nodes[root].parent.is_some() {
        return Err(SourcePackageError::new(
            ErrorKind::NoRoot,
            "root invariant violated",
        ));
    }

    let (element_records, text_records) = build_records(&nodes)?;
    if element_records.len() as u64 > limits.max_nodes {
        return Err(SourcePackageError::new(
            ErrorKind::NodeCapExceeded,
            format!(
                "elements {} > cap {}",
                element_records.len(),
                limits.max_nodes
            ),
        ));
    }
    if text_records.len() as u64 > limits.max_text_fragments {
        return Err(SourcePackageError::new(
            ErrorKind::TextFragmentCapExceeded,
            format!(
                "text fragments {} > cap {}",
                text_records.len(),
                limits.max_text_fragments
            ),
        ));
    }
    let total_text_bytes: u64 = text_records.iter().map(|record| record.bytes).sum();
    if total_text_bytes > limits.max_text_bytes {
        return Err(SourcePackageError::new(
            ErrorKind::TextByteCapExceeded,
            format!(
                "text bytes {} > cap {}",
                total_text_bytes, limits.max_text_bytes
            ),
        ));
    }
    let total_records = element_records.len() + text_records.len();
    if total_records as u64 > limits.max_records {
        return Err(SourcePackageError::new(
            ErrorKind::RecordCapExceeded,
            format!("records {} > cap {}", total_records, limits.max_records),
        ));
    }

    let mut records: Vec<Record> = Vec::with_capacity(total_records);
    records.extend(element_records.into_iter().map(Record::Element));
    records.extend(text_records.into_iter().map(Record::Text));

    let counts = recompute_counts(&records);
    let manifest = Manifest {
        kind: "source_package_manifest".to_string(),
        schema: MANIFEST_SCHEMA.to_string(),
        version: SCHEMA_VERSION,
        model: MODEL.to_string(),
        profile: PROFILE.to_string(),
        capability: CAPABILITY.to_string(),
        capture_policy: CAPTURE_POLICY.to_string(),
        source: SourceRef {
            sha256: source_sha256.clone(),
            bytes: xml.len() as u64,
        },
        limits: limits.clone(),
        policies: Policies::expected(),
        non_authoritative: true,
    };
    let footer = Footer {
        kind: "source_package_footer".to_string(),
        schema: FOOTER_SCHEMA.to_string(),
        version: SCHEMA_VERSION,
        capture_status: CaptureStatus::Complete,
        completion_basis: COMPLETION_BASIS.to_string(),
        source_sha256,
        counts,
        records_seal_hash: None,
        manifest_hash: None,
        non_authoritative: true,
    };
    let mut package = Package {
        manifest,
        records,
        footer,
    };
    package.resign()?;
    package.verify()?;
    // The package must be exportable under its own declared limits: a decoded
    // text value whose JSON escaping exceeds max_line_bytes would otherwise
    // capture successfully but never write.
    package.check_exportable(limits)?;
    Ok(package)
}

/// Read a validated package from a bounded reader.
///
/// Reading is incremental. The manifest is parsed first; the per-field effective
/// limits are the minimum of the caller's caps and the manifest's declared
/// limits. Every subsequent line is length-bounded before it is parsed, records
/// are counted against the caps before they are retained, and the footer must be
/// the final line (verified to EOF). A short manifest that claims huge limits
/// therefore cannot force unbounded allocation.
pub fn read_package<R: BufRead>(
    mut reader: R,
    limits: &Limits,
) -> Result<Package, SourcePackageError> {
    let mut total: u64 = 0;

    // Line 1: manifest. Only caller limits are trusted until it is parsed.
    let mut line = Vec::new();
    match read_line_bounded(
        &mut reader,
        &mut line,
        limits.max_line_bytes,
        &mut total,
        limits.max_package_bytes,
    )? {
        LineRead::Eof => {
            return Err(SourcePackageError::new(
                ErrorKind::EmptyPackage,
                "empty package",
            ))
        }
        LineRead::EofNoLf => {
            return Err(SourcePackageError::new(
                ErrorKind::MissingTrailingLf,
                "package does not end with LF",
            ))
        }
        LineRead::Line => {}
    }
    line.pop();
    let manifest_line = finish_line(&line, 1)?;
    let manifest_value = strict_value(manifest_line, 1)?;
    if manifest_value.get("kind").and_then(Value::as_str) != Some("source_package_manifest") {
        return Err(SourcePackageError::new(
            ErrorKind::MisorderedManifest,
            "manifest is not the first line",
        ));
    }
    let manifest: Manifest = from_value_typed(manifest_value, 1)?;
    let effective = effective_limits(limits, &manifest.limits);

    let mut records: Vec<Record> = Vec::new();
    let mut element_count: u64 = 0;
    let mut text_count: u64 = 0;
    let mut text_bytes: u64 = 0;
    let mut line_number: u64 = 1;
    loop {
        let mut line = Vec::new();
        match read_line_bounded(
            &mut reader,
            &mut line,
            effective.max_line_bytes,
            &mut total,
            effective.max_package_bytes,
        )? {
            LineRead::Eof => {
                return Err(SourcePackageError::new(
                    ErrorKind::MissingFooter,
                    "package has no footer",
                ))
            }
            LineRead::EofNoLf => {
                return Err(SourcePackageError::new(
                    ErrorKind::MissingTrailingLf,
                    "package does not end with LF",
                ))
            }
            LineRead::Line => {}
        }
        line.pop();
        line_number += 1;
        let text_line = finish_line(&line, line_number)?;
        let value = strict_value(text_line, line_number)?;
        match value.get("kind").and_then(Value::as_str) {
            Some("source_package_footer") => {
                let footer: Footer = from_value_typed(value, line_number)?;
                // The footer must be the last line: any further byte is an error.
                let mut probe = [0u8; 1];
                let read = reader
                    .read(&mut probe)
                    .map_err(SourcePackageError::from_io)?;
                if read != 0 {
                    return Err(SourcePackageError::new(
                        ErrorKind::MisorderedFooter,
                        "footer is not the last line",
                    ));
                }
                let package = Package {
                    manifest,
                    records,
                    footer,
                };
                package.verify_with(&effective)?;
                return Ok(package);
            }
            Some("source_package_manifest") => {
                return Err(SourcePackageError::new(
                    ErrorKind::MisorderedManifest,
                    "more than one manifest line",
                ));
            }
            Some("element") => {
                let record = parse_record(value, line_number)?;
                if let Record::Element(element) = &record {
                    element_count = element_count.saturating_add(1);
                    if element_count > effective.max_nodes {
                        return Err(SourcePackageError::new(
                            ErrorKind::NodeCapExceeded,
                            "element count reached the effective cap",
                        ));
                    }
                    if element.depth > effective.max_depth {
                        return Err(SourcePackageError::new(
                            ErrorKind::DepthExceeded,
                            "element depth reached the effective cap",
                        ));
                    }
                    let attribute_count =
                        element.attrs.len() as u64 + element.namespace_declarations.len() as u64;
                    if attribute_count > effective.max_attrs_per_element {
                        return Err(SourcePackageError::new(
                            ErrorKind::AttributeCountExceeded,
                            "attributes+declarations reached the effective cap",
                        ));
                    }
                }
                if element_count.saturating_add(text_count) > effective.max_records {
                    return Err(SourcePackageError::new(
                        ErrorKind::RecordCapExceeded,
                        "record count reached the effective cap",
                    ));
                }
                records.push(record);
            }
            Some("text") => {
                let record = parse_record(value, line_number)?;
                if let Record::Text(text) = &record {
                    text_count = text_count.saturating_add(1);
                    if text_count > effective.max_text_fragments {
                        return Err(SourcePackageError::new(
                            ErrorKind::TextFragmentCapExceeded,
                            "text fragment count reached the effective cap",
                        ));
                    }
                    text_bytes = text_bytes.saturating_add(text.bytes);
                    if text_bytes > effective.max_text_bytes {
                        return Err(SourcePackageError::new(
                            ErrorKind::TextByteCapExceeded,
                            "text bytes reached the effective cap",
                        ));
                    }
                }
                if element_count.saturating_add(text_count) > effective.max_records {
                    return Err(SourcePackageError::new(
                        ErrorKind::RecordCapExceeded,
                        "record count reached the effective cap",
                    ));
                }
                records.push(record);
            }
            _ => {
                return Err(SourcePackageError::new(
                    ErrorKind::UnknownKind,
                    format!("line {line_number}: unknown record kind"),
                ));
            }
        }
    }
}

enum LineRead {
    Eof,
    EofNoLf,
    Line,
}

/// Read one LF-terminated line without ever allocating more than `line_cap`
/// bytes for it. Returns `EofNoLf` when bytes remain but there is no trailing
/// LF. The running `total` is checked against `total_cap` with saturating
/// arithmetic so `u64::MAX` caps cannot overflow.
fn read_line_bounded<R: BufRead>(
    reader: &mut R,
    out: &mut Vec<u8>,
    line_cap: u64,
    total: &mut u64,
    total_cap: u64,
) -> Result<LineRead, SourcePackageError> {
    loop {
        let buf = reader.fill_buf().map_err(SourcePackageError::from_io)?;
        if buf.is_empty() {
            return Ok(if out.is_empty() {
                LineRead::Eof
            } else {
                LineRead::EofNoLf
            });
        }
        match buf.iter().position(|&byte| byte == b'\n') {
            Some(position) => {
                let take = position + 1;
                if out.len() as u64 + take as u64 > line_cap {
                    return Err(SourcePackageError::new(
                        ErrorKind::LineTooLong,
                        "line exceeds the cap",
                    ));
                }
                if (*total).saturating_add(take as u64) > total_cap {
                    return Err(SourcePackageError::new(
                        ErrorKind::PackageTooLarge,
                        "package exceeds the cap",
                    ));
                }
                out.extend_from_slice(&buf[..take]);
                *total = (*total).saturating_add(take as u64);
                reader.consume(take);
                return Ok(LineRead::Line);
            }
            None => {
                let take = buf.len();
                if out.len() as u64 + take as u64 > line_cap {
                    return Err(SourcePackageError::new(
                        ErrorKind::LineTooLong,
                        "line exceeds the cap",
                    ));
                }
                if (*total).saturating_add(take as u64) > total_cap {
                    return Err(SourcePackageError::new(
                        ErrorKind::PackageTooLarge,
                        "package exceeds the cap",
                    ));
                }
                out.extend_from_slice(buf);
                *total = (*total).saturating_add(take as u64);
                reader.consume(take);
            }
        }
    }
}

fn finish_line(line: &[u8], line_number: u64) -> Result<&str, SourcePackageError> {
    if line.contains(&b'\r') {
        return Err(SourcePackageError::new(
            ErrorKind::CarriageReturnForbidden,
            "package contains carriage returns",
        ));
    }
    if line.is_empty() {
        return Err(SourcePackageError::new(
            ErrorKind::EmptyLine,
            format!("blank line {line_number}"),
        ));
    }
    std::str::from_utf8(line).map_err(|_| {
        SourcePackageError::new(ErrorKind::NonUtf8Package, "package line is not valid UTF-8")
    })
}

/// Per-field minimum of the caller's caps and the package's declared limits: a
/// caller cap is a ceiling, a manifest cap can only tighten it.
fn effective_limits(caller: &Limits, declared: &Limits) -> Limits {
    Limits {
        max_input_bytes: caller.max_input_bytes.min(declared.max_input_bytes),
        max_package_bytes: caller.max_package_bytes.min(declared.max_package_bytes),
        max_line_bytes: caller.max_line_bytes.min(declared.max_line_bytes),
        max_depth: caller.max_depth.min(declared.max_depth),
        max_nodes: caller.max_nodes.min(declared.max_nodes),
        max_text_fragments: caller.max_text_fragments.min(declared.max_text_fragments),
        max_text_bytes: caller.max_text_bytes.min(declared.max_text_bytes),
        max_records: caller.max_records.min(declared.max_records),
        max_attrs_per_element: caller
            .max_attrs_per_element
            .min(declared.max_attrs_per_element),
    }
}

/// Validate, then write a package. See [`Package::write_to`].
pub fn write_package<W: Write>(
    package: &Package,
    writer: &mut W,
    limits: &Limits,
) -> Result<(), SourcePackageError> {
    package.write_to(writer, limits)
}

/// Re-capture the supplied XML and compare it structurally with the package.
///
/// Both flags are explicit. `structurally_equal` shares the capture algorithm
/// with the package builder, so it is **not** independent proof of authenticity,
/// completeness, or legal correctness.
pub fn verify_against_source(
    package: &Package,
    xml: &[u8],
    limits: &Limits,
) -> Result<SourceComparison, SourcePackageError> {
    let rebuilt = capture(xml, limits)?;
    Ok(SourceComparison {
        source_sha256_matches: package.manifest.source.sha256 == sha256_hex(xml),
        structurally_equal: package.semantically_equal(&rebuilt),
    })
}

// --------------------------------------------------------------- internals #

struct Node {
    parent: Option<usize>,
    child_index: Option<u64>,
    depth: u64,
    clark_tag: String,
    attrs: BTreeMap<String, String>,
    namespace_declarations: BTreeMap<String, String>,
    xml_space_declared: Option<bool>,
    xml_space_effective: bool,
    text: String,
    tail: String,
    content: String,
    children: Vec<usize>,
}

fn begin_element(
    nodes: &mut Vec<Node>,
    stack: &[usize],
    root: &mut Option<usize>,
    start: &BytesStart<'_>,
    reader: &NsReader<&[u8]>,
    limits: &Limits,
) -> Result<usize, SourcePackageError> {
    let parent = stack.last().copied();
    if parent.is_none() && root.is_some() {
        return Err(SourcePackageError::new(
            ErrorKind::MultipleRoots,
            "more than one root element",
        ));
    }
    if nodes.len() as u64 >= limits.max_nodes {
        return Err(SourcePackageError::new(
            ErrorKind::NodeCapExceeded,
            format!("elements reached cap {}", limits.max_nodes),
        ));
    }
    let depth = parent.map(|index| nodes[index].depth + 1).unwrap_or(0);
    if depth > limits.max_depth {
        return Err(SourcePackageError::new(
            ErrorKind::DepthExceeded,
            format!("depth {} > cap {}", depth, limits.max_depth),
        ));
    }
    // Text accumulated since the previous sibling belongs to the parent's
    // `text` slot (before the first child) or the previous child's `tail`.
    if let Some(parent_index) = parent {
        flush_content(nodes, parent_index);
    }

    let (resolve, local) = reader.resolve_element(start.name());
    validate_qname(start.name().as_ref(), "element")?;
    let clark_tag = clark_name(resolve, local.as_ref(), "element")?;

    let mut attrs: BTreeMap<String, String> = BTreeMap::new();
    let mut declarations: BTreeMap<String, String> = BTreeMap::new();
    let mut raw_seen: HashSet<Vec<u8>> = HashSet::new();
    let parent_space = parent
        .map(|index| nodes[index].xml_space_effective)
        .unwrap_or(false);
    let mut xml_space_declared: Option<bool> = None;

    for attribute in start.attributes() {
        let attribute = match attribute {
            Ok(attribute) => attribute,
            Err(AttrError::Duplicated(_, _)) => {
                return Err(SourcePackageError::new(
                    ErrorKind::DuplicateAttribute,
                    "duplicate attribute key",
                ))
            }
            Err(_) => {
                return Err(SourcePackageError::new(
                    ErrorKind::MalformedXml,
                    "malformed attribute",
                ))
            }
        };
        let raw = attribute.key.as_ref().to_vec();
        // XML 1.0 `AttValue` forbids a literal `<` before unescaping; an entity
        // reference such as `&lt;` remains valid and is checked after unescape.
        if attribute.value.as_ref().contains(&b'<') {
            return Err(SourcePackageError::new(
                ErrorKind::MalformedXml,
                "attribute value contains a literal '<'",
            ));
        }
        // Validate the raw attribute name (including `xmlns`/`xmlns:p`) as a
        // QName before any namespace resolution or declaration bookkeeping.
        validate_qname(attribute.key.as_ref(), "attribute")?;
        if !raw_seen.insert(raw) {
            return Err(SourcePackageError::new(
                ErrorKind::DuplicateAttribute,
                "duplicate attribute key",
            ));
        }
        if let Some(prefix) = namespace_declaration_prefix(attribute.key.as_ref()) {
            // Bounded policy: namespace URIs are literal. quick-xml resolves
            // namespace bindings from the raw (undecoded) attribute bytes, so a
            // reference or a literal tab/LF/CR would desynchronize the resolved
            // Clark name from `namespace_declarations`.
            let raw_value = attribute.value.as_ref();
            if raw_value
                .iter()
                .any(|byte| matches!(byte, b'&' | b'\t' | b'\n' | b'\r'))
            {
                return Err(SourcePackageError::new(
                    ErrorKind::MalformedXml,
                    "namespace declaration uses a reference or literal whitespace",
                ));
            }
            let value = std::str::from_utf8(raw_value).map_err(|_| {
                SourcePackageError::new(
                    ErrorKind::MalformedXml,
                    "namespace declaration is not valid UTF-8",
                )
            })?;
            validate_xml_chars(value)?;
            if declarations.insert(prefix, value.to_string()).is_some() {
                return Err(SourcePackageError::new(
                    ErrorKind::DuplicateAttribute,
                    "duplicate namespace declaration",
                ));
            }
            if (attrs.len() + declarations.len()) as u64 > limits.max_attrs_per_element {
                return Err(SourcePackageError::new(
                    ErrorKind::AttributeCountExceeded,
                    "attributes+declarations reached cap",
                ));
            }
            continue;
        }
        let (resolve, local) = reader.resolve_attribute(attribute.key);
        let name = clark_name(resolve, local.as_ref(), "attribute")?;
        if attrs.contains_key(&name) {
            return Err(SourcePackageError::new(
                ErrorKind::DuplicateAttribute,
                "duplicate resolved attribute name",
            ));
        }
        let raw_value = attribute.value.as_ref();
        let normalized_value = normalize_attr_whitespace(raw_value);
        let decoded = std::str::from_utf8(&normalized_value).map_err(|_| {
            SourcePackageError::new(ErrorKind::MalformedXml, "malformed attribute value")
        })?;
        let value = quick_xml::escape::unescape(decoded).map_err(|_| {
            SourcePackageError::new(ErrorKind::MalformedXml, "malformed attribute value")
        })?;
        validate_xml_chars(value.as_ref())?;
        if name == XML_SPACE_CLARK {
            let flag = match value.as_ref() {
                "preserve" => true,
                "default" => false,
                _ => {
                    return Err(SourcePackageError::new(
                        ErrorKind::InvalidXmlSpace,
                        "xml:space value is not preserve|default",
                    ))
                }
            };
            xml_space_declared = Some(flag);
        }
        attrs.insert(name, value.into_owned());
        if (attrs.len() + declarations.len()) as u64 > limits.max_attrs_per_element {
            return Err(SourcePackageError::new(
                ErrorKind::AttributeCountExceeded,
                "attributes+declarations reached cap",
            ));
        }
    }

    if (attrs.len() + declarations.len()) as u64 > limits.max_attrs_per_element {
        return Err(SourcePackageError::new(
            ErrorKind::AttributeCountExceeded,
            "attributes+declarations reached cap",
        ));
    }

    let child_index = parent.map(|index| nodes[index].children.len() as u64);
    let xml_space_effective = xml_space_declared.unwrap_or(parent_space);
    let index = nodes.len();
    nodes.push(Node {
        parent,
        child_index,
        depth,
        clark_tag,
        attrs,
        namespace_declarations: declarations,
        xml_space_declared,
        xml_space_effective,
        text: String::new(),
        tail: String::new(),
        content: String::new(),
        children: Vec::new(),
    });
    match parent {
        Some(parent_index) => nodes[parent_index].children.push(index),
        None => *root = Some(index),
    }
    Ok(index)
}

fn flush_content(nodes: &mut [Node], index: usize) {
    let content = std::mem::take(&mut nodes[index].content);
    if content.is_empty() {
        return;
    }
    if let Some(&last) = nodes[index].children.last() {
        nodes[last].tail.push_str(&content);
    } else {
        nodes[index].text.push_str(&content);
    }
}

fn finish_element(nodes: &mut [Node], index: usize) {
    flush_content(nodes, index);
}

fn handle_text(
    nodes: &mut [Node],
    stack: &[usize],
    value: &str,
    total_text_bytes: &mut u64,
    limits: &Limits,
) -> Result<(), SourcePackageError> {
    if let Some(&index) = stack.last() {
        // Enforce the text-byte cap while accumulating, before record building,
        // so a caller setting a small cap cannot force unbounded accumulation.
        *total_text_bytes = (*total_text_bytes).saturating_add(value.len() as u64);
        if *total_text_bytes > limits.max_text_bytes {
            return Err(SourcePackageError::new(
                ErrorKind::TextByteCapExceeded,
                format!("text bytes reached cap {}", limits.max_text_bytes),
            ));
        }
        nodes[index].content.push_str(value);
        return Ok(());
    }
    // Document-level content: only XML whitespace is tolerated, and it is out
    // of the carried text scope (declared in `policies.document_level_text`).
    let xml_whitespace = value
        .chars()
        .all(|ch| matches!(ch, ' ' | '\t' | '\r' | '\n'));
    if xml_whitespace {
        Ok(())
    } else {
        Err(SourcePackageError::new(
            ErrorKind::DocumentLevelText,
            "non-whitespace text outside the root element",
        ))
    }
}

/// XML 1.0 section 2.11 literal end-of-line normalization: `\r\n` and lone `\r`
/// become `\n`. Character references are untouched because they carry no literal
/// carriage return in the source bytes.
fn normalize_eol(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    while let Some(ch) = chars.next() {
        if ch == '\r' {
            if chars.peek() == Some(&'\n') {
                chars.next();
            }
            out.push('\n');
        } else {
            out.push(ch);
        }
    }
    out
}

/// XML 1.0 section 3.3.3 literal attribute whitespace normalization: literal
/// TAB/LF/CR become a space. Operates on the raw (pre-unescape) bytes so a
/// character reference such as `&#9;` keeps its tab.
fn normalize_attr_whitespace(raw: &[u8]) -> Cow<'_, [u8]> {
    if raw.iter().any(|byte| matches!(byte, b'\t' | b'\n' | b'\r')) {
        Cow::Owned(
            raw.iter()
                .map(|&byte| {
                    if matches!(byte, b'\t' | b'\n' | b'\r') {
                        b' '
                    } else {
                        byte
                    }
                })
                .collect(),
        )
    } else {
        Cow::Borrowed(raw)
    }
}

/// The XML 1.0 `Char` production.
fn is_xml_char(ch: char) -> bool {
    matches!(ch, '\u{9}' | '\u{A}' | '\u{D}')
        || ('\u{20}'..='\u{D7FF}').contains(&ch)
        || ('\u{E000}'..='\u{FFFD}').contains(&ch)
        || ('\u{10000}'..='\u{10FFFF}').contains(&ch)
}

fn validate_xml_chars(value: &str) -> Result<(), SourcePackageError> {
    if value.chars().any(|ch| !is_xml_char(ch)) {
        return Err(SourcePackageError::new(
            ErrorKind::InvalidXmlChar,
            "value contains a character outside the XML 1.0 Char set",
        ));
    }
    Ok(())
}

/// XML 1.0 (fifth edition) `NameStartChar` production.
fn is_xml_name_start(ch: char) -> bool {
    matches!(ch, ':' | 'A'..='Z' | '_' | 'a'..='z')
        || ('\u{C0}'..='\u{D6}').contains(&ch)
        || ('\u{D8}'..='\u{F6}').contains(&ch)
        || ('\u{F8}'..='\u{2FF}').contains(&ch)
        || ('\u{370}'..='\u{37D}').contains(&ch)
        || ('\u{37F}'..='\u{1FFF}').contains(&ch)
        || ('\u{200C}'..='\u{200D}').contains(&ch)
        || ('\u{2070}'..='\u{218F}').contains(&ch)
        || ('\u{2C00}'..='\u{2FEF}').contains(&ch)
        || ('\u{3001}'..='\u{D7FF}').contains(&ch)
        || ('\u{F900}'..='\u{FDCF}').contains(&ch)
        || ('\u{FDF0}'..='\u{FFFD}').contains(&ch)
        || ('\u{10000}'..='\u{EFFFF}').contains(&ch)
}

/// XML 1.0 (fifth edition) `NameChar` production.
fn is_xml_name_char(ch: char) -> bool {
    is_xml_name_start(ch)
        || matches!(ch, '-' | '.' | '0'..='9' | '\u{B7}')
        || ('\u{300}'..='\u{36F}').contains(&ch)
        || ('\u{203F}'..='\u{2040}').contains(&ch)
}

/// `NCName` (XML Namespaces 1.0): a `Name` with no colon.
fn is_ncname(name: &str) -> bool {
    let mut chars = name.chars();
    match chars.next() {
        Some(first) if first != ':' && is_xml_name_start(first) => {
            chars.all(|ch| ch != ':' && is_xml_name_char(ch))
        }
        _ => false,
    }
}

/// An XML `QName`: `Prefix? ':' LocalPart`, i.e. zero or one colon with every
/// component a non-empty `NCName`. `Name` production characters (`#xB7`,
/// combining marks, `#x203F-#x2040`) are accepted after the first character.
fn is_qname(name: &str) -> bool {
    let mut parts = name.split(':');
    match (parts.next(), parts.next(), parts.next()) {
        (Some(local), None, None) => is_ncname(local),
        (Some(prefix), Some(local), None) => is_ncname(prefix) && is_ncname(local),
        _ => false,
    }
}

/// Validate a raw (undecoded) element/attribute/namespace-declaration name as an
/// XML `QName`. The bytes are checked as UTF-8 first so validation never runs on
/// a lossy replacement string; a name outside the XML 1.0 productions (including
/// an embedded NUL or any non-`Char` code point) is rejected.
fn validate_qname(raw: &[u8], scope: &'static str) -> Result<(), SourcePackageError> {
    let name = std::str::from_utf8(raw).map_err(|_| {
        SourcePackageError::new(
            ErrorKind::MalformedXml,
            format!("{scope} name is not valid UTF-8"),
        )
    })?;
    if !is_qname(name) {
        return Err(SourcePackageError::new(
            ErrorKind::MalformedXml,
            format!("{scope} name is not a valid XML QName"),
        ));
    }
    Ok(())
}

fn namespace_declaration_prefix(raw: &[u8]) -> Option<String> {
    if raw == b"xmlns" {
        Some(String::new())
    } else {
        raw.strip_prefix(b"xmlns:")
            .map(|prefix| String::from_utf8_lossy(prefix).into_owned())
    }
}

fn clark_name(
    resolve: ResolveResult<'_>,
    local: &[u8],
    scope: &'static str,
) -> Result<String, SourcePackageError> {
    match resolve {
        ResolveResult::Unbound => Ok(String::from_utf8_lossy(local).into_owned()),
        ResolveResult::Bound(namespace) => {
            if namespace.as_ref().is_empty() {
                Ok(String::from_utf8_lossy(local).into_owned())
            } else {
                Ok(format!(
                    "{{{}}}{}",
                    String::from_utf8_lossy(namespace.as_ref()),
                    String::from_utf8_lossy(local)
                ))
            }
        }
        ResolveResult::Unknown(_prefix) => Err(SourcePackageError::new(
            ErrorKind::UnboundPrefix,
            format!("{} prefix is unbound", scope),
        )),
    }
}

fn build_records(
    nodes: &[Node],
) -> Result<(Vec<ElementRecord>, Vec<TextRecord>), SourcePackageError> {
    let mut elements: Vec<ElementRecord> = nodes
        .iter()
        .enumerate()
        .map(|(index, node)| ElementRecord {
            kind: "element".to_string(),
            schema: ELEMENT_SCHEMA.to_string(),
            id: format!("e{index}"),
            parent: node.parent.map(|parent| format!("e{parent}")),
            child_index: node.child_index,
            depth: node.depth,
            clark_tag: node.clark_tag.clone(),
            attrs: node.attrs.clone(),
            namespace_declarations: node.namespace_declarations.clone(),
            xml_space_declared: node.xml_space_declared,
            xml_space_effective: node.xml_space_effective,
            text_ref: None,
            tail_ref: None,
        })
        .collect();
    let mut texts: Vec<TextRecord> = Vec::new();
    let root = nodes
        .iter()
        .position(|node| node.parent.is_none())
        .ok_or_else(|| SourcePackageError::new(ErrorKind::NoRoot, "no root element"))?;
    emit_text(nodes, root, &mut elements, &mut texts);
    Ok((elements, texts))
}

fn emit_text(
    nodes: &[Node],
    root: usize,
    elements: &mut [ElementRecord],
    texts: &mut Vec<TextRecord>,
) {
    // Iterative pre-order walk with explicit tail steps: the element tree can be
    // as deep as the caller's cap, so recursion is never used.
    enum Step {
        Node(usize),
        Tail(usize),
    }
    let mut stack = vec![Step::Node(root)];
    while let Some(step) = stack.pop() {
        match step {
            Step::Node(index) => {
                if !nodes[index].text.is_empty() {
                    let value = nodes[index].text.clone();
                    let id = format!("t{}", texts.len());
                    push_text_record(
                        texts,
                        &mut elements[index],
                        TextSlot::Text,
                        index,
                        value,
                        id,
                    );
                }
                for &child in nodes[index].children.iter().rev() {
                    stack.push(Step::Tail(child));
                    stack.push(Step::Node(child));
                }
            }
            Step::Tail(child) => {
                if !nodes[child].tail.is_empty() {
                    let value = nodes[child].tail.clone();
                    let id = format!("t{}", texts.len());
                    push_text_record(
                        texts,
                        &mut elements[child],
                        TextSlot::Tail,
                        child,
                        value,
                        id,
                    );
                }
            }
        }
    }
}

fn push_text_record(
    texts: &mut Vec<TextRecord>,
    element: &mut ElementRecord,
    slot: TextSlot,
    owner_index: usize,
    value: String,
    id: String,
) {
    let chars = value.chars().count() as u64;
    let bytes = value.len() as u64;
    texts.push(TextRecord {
        kind: "text".to_string(),
        schema: TEXT_SCHEMA.to_string(),
        id: id.clone(),
        owner: format!("e{owner_index}"),
        slot,
        value,
        chars,
        bytes,
    });
    match slot {
        TextSlot::Text => element.text_ref = Some(id),
        TextSlot::Tail => element.tail_ref = Some(id),
    }
}

// ------------------------------------------------------------- serializing #

fn canonical_json<T: Serialize>(value: &T) -> Result<String, SourcePackageError> {
    serde_json::to_string(value).map_err(|error| {
        SourcePackageError::new(ErrorKind::Serialization, safe_serde_detail(&error))
    })
}

fn serialize_record(record: &Record) -> Result<String, SourcePackageError> {
    canonical_json(record)
}

/// Deterministic sha256 seal over the records in file order.
pub fn records_seal_hash(records: &[Record]) -> Result<String, SourcePackageError> {
    let mut hasher = Sha256::new();
    for (index, record) in records.iter().enumerate() {
        if index > 0 {
            hasher.update(b"\n");
        }
        hasher.update(serialize_record(record)?.as_bytes());
    }
    Ok(hex_lower(&hasher.finalize()))
}

/// Root hash binding the manifest, the record seal, and the footer body (all
/// footer fields except the two hash fields themselves).
pub fn manifest_hash(
    manifest: &Manifest,
    records: &[Record],
    footer: &Footer,
) -> Result<String, SourcePackageError> {
    let mut body = footer.clone();
    body.records_seal_hash = None;
    body.manifest_hash = None;
    let canonical = format!(
        "{}\n{}\n{}",
        canonical_json(manifest)?,
        records_seal_hash(records)?,
        canonical_json(&body)?
    );
    Ok(sha256_hex(canonical.as_bytes()))
}

fn recompute_counts(records: &[Record]) -> Counts {
    let mut counts = Counts {
        elements: 0,
        text_fragments: 0,
        text_chars: 0,
        text_bytes: 0,
        namespace_declarations: 0,
        records: records.len() as u64,
    };
    for record in records {
        match record {
            Record::Element(element) => {
                counts.elements += 1;
                counts.namespace_declarations += element.namespace_declarations.len() as u64;
            }
            Record::Text(text) => {
                counts.text_fragments += 1;
                counts.text_chars += text.chars;
                counts.text_bytes += text.bytes;
            }
        }
    }
    counts
}

// ------------------------------------------------------------------ verify #

fn verify_package(package: &Package, limits: &Limits) -> Result<(), SourcePackageError> {
    let manifest = &package.manifest;
    if manifest.kind != "source_package_manifest"
        || manifest.schema != MANIFEST_SCHEMA
        || manifest.model != MODEL
        || manifest.profile != PROFILE
        || manifest.capability != CAPABILITY
        || manifest.capture_policy != CAPTURE_POLICY
        || !manifest.non_authoritative
    {
        return Err(SourcePackageError::new(
            ErrorKind::SchemaMismatch,
            "manifest identity/constants mismatch",
        ));
    }
    if manifest.version != SCHEMA_VERSION {
        return Err(SourcePackageError::new(
            ErrorKind::VersionUnsupported,
            format!("manifest version {}", manifest.version),
        ));
    }
    if !is_hex64(&manifest.source.sha256) {
        return Err(SourcePackageError::new(
            ErrorKind::HashMalformed,
            "manifest source sha256 is not 64 lowercase hex",
        ));
    }
    if manifest.policies != Policies::expected() {
        return Err(SourcePackageError::new(
            ErrorKind::SchemaMismatch,
            "policy declaration mismatch",
        ));
    }

    let footer = &package.footer;
    if footer.kind != "source_package_footer"
        || footer.schema != FOOTER_SCHEMA
        || footer.completion_basis != COMPLETION_BASIS
        || !footer.non_authoritative
    {
        return Err(SourcePackageError::new(
            ErrorKind::SchemaMismatch,
            "footer identity/constants mismatch",
        ));
    }
    if footer.version != SCHEMA_VERSION {
        return Err(SourcePackageError::new(
            ErrorKind::VersionUnsupported,
            format!("footer version {}", footer.version),
        ));
    }
    if footer.source_sha256 != manifest.source.sha256 {
        return Err(SourcePackageError::new(
            ErrorKind::SourceHashMismatch,
            "footer source sha256 differs from manifest",
        ));
    }
    if !is_hex64(&footer.source_sha256) {
        return Err(SourcePackageError::new(
            ErrorKind::HashMalformed,
            "footer source sha256 is not 64 lowercase hex",
        ));
    }

    verify_records(package, limits)?;

    if manifest.source.bytes > limits.max_input_bytes {
        return Err(SourcePackageError::new(
            ErrorKind::LimitExceeded,
            format!(
                "source bytes {} > max_input_bytes {}",
                manifest.source.bytes, limits.max_input_bytes
            ),
        ));
    }

    let seal = footer.records_seal_hash.as_deref().ok_or_else(|| {
        SourcePackageError::new(ErrorKind::HashMissing, "missing records_seal_hash")
    })?;
    if !is_hex64(seal) {
        return Err(SourcePackageError::new(
            ErrorKind::HashMalformed,
            "records_seal_hash is not 64 lowercase hex",
        ));
    }
    if seal != records_seal_hash(&package.records)? {
        return Err(SourcePackageError::new(
            ErrorKind::RecordsSealMismatch,
            "records seal hash mismatch",
        ));
    }

    let root = footer
        .manifest_hash
        .as_deref()
        .ok_or_else(|| SourcePackageError::new(ErrorKind::HashMissing, "missing manifest_hash"))?;
    if !is_hex64(root) {
        return Err(SourcePackageError::new(
            ErrorKind::HashMalformed,
            "manifest_hash is not 64 lowercase hex",
        ));
    }
    if root != manifest_hash(manifest, &package.records, footer)? {
        return Err(SourcePackageError::new(
            ErrorKind::ManifestHashMismatch,
            "manifest root hash mismatch",
        ));
    }
    Ok(())
}

fn compare_counts(declared: &Counts, actual: &Counts) -> Result<(), SourcePackageError> {
    let pairs = [
        ("elements", declared.elements, actual.elements),
        (
            "text_fragments",
            declared.text_fragments,
            actual.text_fragments,
        ),
        ("text_chars", declared.text_chars, actual.text_chars),
        ("text_bytes", declared.text_bytes, actual.text_bytes),
        (
            "namespace_declarations",
            declared.namespace_declarations,
            actual.namespace_declarations,
        ),
        ("records", declared.records, actual.records),
    ];
    for (field, declared_value, actual_value) in pairs {
        if declared_value != actual_value {
            return Err(SourcePackageError::new(
                ErrorKind::CountMismatch,
                format!("{field}: declared {declared_value} != actual {actual_value}"),
            ));
        }
    }
    Ok(())
}

fn enforce_limits(
    limits: &Limits,
    counts: &Counts,
    records: &[Record],
) -> Result<(), SourcePackageError> {
    if counts.elements > limits.max_nodes {
        return Err(SourcePackageError::new(
            ErrorKind::LimitExceeded,
            format!(
                "elements {} > max_nodes {}",
                counts.elements, limits.max_nodes
            ),
        ));
    }
    if counts.text_fragments > limits.max_text_fragments {
        return Err(SourcePackageError::new(
            ErrorKind::LimitExceeded,
            format!(
                "text_fragments {} > cap {}",
                counts.text_fragments, limits.max_text_fragments
            ),
        ));
    }
    if counts.text_bytes > limits.max_text_bytes {
        return Err(SourcePackageError::new(
            ErrorKind::LimitExceeded,
            format!(
                "text_bytes {} > cap {}",
                counts.text_bytes, limits.max_text_bytes
            ),
        ));
    }
    if counts.records > limits.max_records {
        return Err(SourcePackageError::new(
            ErrorKind::LimitExceeded,
            format!("records {} > cap {}", counts.records, limits.max_records),
        ));
    }
    let max_depth = records
        .iter()
        .filter_map(|record| match record {
            Record::Element(element) => Some(element.depth),
            Record::Text(_) => None,
        })
        .max()
        .unwrap_or(0);
    if max_depth > limits.max_depth {
        return Err(SourcePackageError::new(
            ErrorKind::LimitExceeded,
            format!("depth {} > cap {}", max_depth, limits.max_depth),
        ));
    }
    for (index, record) in records.iter().enumerate() {
        if let Record::Element(element) = record {
            let attribute_count =
                element.attrs.len() as u64 + element.namespace_declarations.len() as u64;
            if attribute_count > limits.max_attrs_per_element {
                return Err(SourcePackageError::new(
                    ErrorKind::LimitExceeded,
                    format!(
                        "element {} attributes+declarations {} > cap {}",
                        index, attribute_count, limits.max_attrs_per_element
                    ),
                ));
            }
        }
    }
    Ok(())
}

fn verify_records(package: &Package, limits: &Limits) -> Result<(), SourcePackageError> {
    // Caps first: recompute the intrinsic counts and enforce every limit before
    // any topology/order walk, so an over-limit package is rejected without
    // building traversal structures.
    let actual = recompute_counts(&package.records);
    enforce_limits(limits, &actual, &package.records)?;
    compare_counts(&package.footer.counts, &actual)?;

    let mut seen_text = false;
    let mut element_records: Vec<&ElementRecord> = Vec::new();
    let mut text_records: Vec<&TextRecord> = Vec::new();
    for record in &package.records {
        match record {
            Record::Element(element) => {
                if seen_text {
                    return Err(SourcePackageError::new(
                        ErrorKind::SectionOrderMismatch,
                        "element record after a text record",
                    ));
                }
                if element.kind != "element" || element.schema != ELEMENT_SCHEMA {
                    return Err(SourcePackageError::new(
                        ErrorKind::SchemaMismatch,
                        "element identity/constants mismatch",
                    ));
                }
                if element.clark_tag.is_empty() {
                    return Err(SourcePackageError::new(
                        ErrorKind::SchemaMismatch,
                        "empty clark tag",
                    ));
                }
                element_records.push(element);
            }
            Record::Text(text) => {
                seen_text = true;
                if text.kind != "text" || text.schema != TEXT_SCHEMA {
                    return Err(SourcePackageError::new(
                        ErrorKind::SchemaMismatch,
                        "text identity/constants mismatch",
                    ));
                }
                text_records.push(text);
            }
        }
    }

    let ids_ok = element_records
        .iter()
        .enumerate()
        .all(|(index, element)| element.id == format!("e{index}"))
        && text_records
            .iter()
            .enumerate()
            .all(|(index, text)| text.id == format!("t{index}"));
    if !ids_ok {
        return Err(SourcePackageError::new(
            ErrorKind::DuplicateRecordId,
            "record ids are not the canonical e0.. / t0.. sequence",
        ));
    }

    let mut id_index: HashMap<&str, usize> = HashMap::new();
    for (index, element) in element_records.iter().enumerate() {
        if id_index.insert(element.id.as_str(), index).is_some() {
            return Err(SourcePackageError::new(
                ErrorKind::DuplicateRecordId,
                "duplicate element id",
            ));
        }
    }
    let mut text_index: HashMap<&str, usize> = HashMap::new();
    for (index, text) in text_records.iter().enumerate() {
        if text_index.insert(text.id.as_str(), index).is_some() {
            return Err(SourcePackageError::new(
                ErrorKind::DuplicateRecordId,
                "duplicate text id",
            ));
        }
    }

    let node_count = element_records.len();
    if node_count == 0 {
        return Err(SourcePackageError::new(
            ErrorKind::NoRoot,
            "no element records",
        ));
    }

    // Topology: exactly one root, parents exist, depth and child_index coherent.
    let mut roots: Vec<usize> = Vec::new();
    let mut children: Vec<Vec<usize>> = vec![Vec::new(); node_count];
    for (index, element) in element_records.iter().enumerate() {
        match element.parent.as_deref() {
            None => {
                if element.depth != 0 || element.child_index.is_some() {
                    return Err(SourcePackageError::new(
                        ErrorKind::DepthMismatch,
                        "root element has non-zero depth or child_index",
                    ));
                }
                roots.push(index);
            }
            Some(parent_id) => {
                let parent = id_index.get(parent_id).copied().ok_or_else(|| {
                    SourcePackageError::new(
                        ErrorKind::ParentDangling,
                        format!("element e{index} parent is not an element"),
                    )
                })?;
                if element_records[parent].depth + 1 != element.depth {
                    return Err(SourcePackageError::new(
                        ErrorKind::DepthMismatch,
                        format!("element e{index} depth is not parent depth + 1"),
                    ));
                }
                children[parent].push(index);
            }
        }
    }
    if roots.len() != 1 {
        return Err(SourcePackageError::new(
            ErrorKind::RootCount,
            format!("{} root elements", roots.len()),
        ));
    }
    for (parent, kids) in children.iter().enumerate() {
        for (position, child) in kids.iter().enumerate() {
            if element_records[*child].child_index != Some(position as u64) {
                return Err(SourcePackageError::new(
                    ErrorKind::ChildIndexMismatch,
                    format!("element e{child} child_index is not {position} under e{parent}"),
                ));
            }
        }
    }

    let root = roots[0];
    let mut order: Vec<usize> = Vec::with_capacity(node_count);
    let mut stack = vec![root];
    while let Some(index) = stack.pop() {
        order.push(index);
        for child in children[index].iter().rev() {
            stack.push(*child);
        }
    }
    if order.len() != node_count
        || order
            .iter()
            .enumerate()
            .any(|(position, value)| position != *value)
    {
        return Err(SourcePackageError::new(
            ErrorKind::ElementOrderMismatch,
            "element records are not in canonical pre-order",
        ));
    }

    // xml:space coherence.
    for (index, element) in element_records.iter().enumerate() {
        let expected = element.xml_space_declared.unwrap_or_else(|| {
            element
                .parent
                .as_deref()
                .and_then(|parent| id_index.get(parent).copied())
                .map(|parent| element_records[parent].xml_space_effective)
                .unwrap_or(false)
        });
        if element.xml_space_effective != expected {
            return Err(SourcePackageError::new(
                ErrorKind::SchemaMismatch,
                format!("element e{index} xml:space inheritance mismatch"),
            ));
        }
    }

    // Text records: owner, slot uniqueness, lengths, refs, document order.
    let mut slots: HashSet<(&str, TextSlot)> = HashSet::new();
    for (position, text) in text_records.iter().enumerate() {
        let _owner = id_index.get(text.owner.as_str()).copied().ok_or_else(|| {
            SourcePackageError::new(
                ErrorKind::TextOwnerDangling,
                format!("text t{position} owner is not an element"),
            )
        })?;
        if !slots.insert((text.owner.as_str(), text.slot)) {
            return Err(SourcePackageError::new(
                ErrorKind::TextSlotDuplicate,
                format!(
                    "duplicate text slot at record t{position} ({})",
                    text.slot.as_str()
                ),
            ));
        }
        if text.chars != text.value.chars().count() as u64 || text.bytes != text.value.len() as u64
        {
            return Err(SourcePackageError::new(
                ErrorKind::TextLengthMismatch,
                format!("text {} chars/bytes do not match value", text.id),
            ));
        }
    }

    // Text/tail document order: the fragment sequence re-derived from the
    // element topology and reference presence must match the record order.
    let mut expected_order: Vec<(usize, TextSlot)> = Vec::new();
    collect_text_order(&element_records, &children, root, &mut expected_order);
    let actual_order: Vec<(usize, TextSlot)> = text_records
        .iter()
        .map(|text| {
            (
                *id_index.get(text.owner.as_str()).unwrap_or(&usize::MAX),
                text.slot,
            )
        })
        .collect();
    if expected_order != actual_order {
        return Err(SourcePackageError::new(
            ErrorKind::TextOrderMismatch,
            "text records are not in canonical text/tail document order",
        ));
    }

    // Element refs must resolve to the matching text record.
    for (index, element) in element_records.iter().enumerate() {
        for (slot, reference) in [
            (TextSlot::Text, element.text_ref.as_deref()),
            (TextSlot::Tail, element.tail_ref.as_deref()),
        ] {
            let Some(reference) = reference else { continue };
            let text = text_index.get(reference).copied().ok_or_else(|| {
                SourcePackageError::new(
                    ErrorKind::TextRefDangling,
                    format!(
                        "element e{index} {slot} ref is dangling",
                        slot = slot.as_str()
                    ),
                )
            })?;
            let record = text_records[text];
            if record.owner != element.id || record.slot != slot {
                return Err(SourcePackageError::new(
                    ErrorKind::TextRefMismatch,
                    format!(
                        "element e{index} {slot} ref points at the wrong owner/slot",
                        slot = slot.as_str()
                    ),
                ));
            }
        }
    }
    Ok(())
}

fn collect_text_order(
    elements: &[&ElementRecord],
    children: &[Vec<usize>],
    root: usize,
    out: &mut Vec<(usize, TextSlot)>,
) {
    // Iterative twin of the pre-order walk used by `emit_text`; no recursion.
    enum Step {
        Node(usize),
        Tail(usize),
    }
    let mut stack = vec![Step::Node(root)];
    while let Some(step) = stack.pop() {
        match step {
            Step::Node(index) => {
                if elements[index].text_ref.is_some() {
                    out.push((index, TextSlot::Text));
                }
                for &child in children[index].iter().rev() {
                    stack.push(Step::Tail(child));
                    stack.push(Step::Node(child));
                }
            }
            Step::Tail(child) => {
                if elements[child].tail_ref.is_some() {
                    out.push((child, TextSlot::Tail));
                }
            }
        }
    }
}

// --------------------------------------------------------------- reading #

/// Deserialize an `Option<T>` member while making the key itself mandatory.
///
/// Plain `Option` fields are treated as absent-when-missing by serde's
/// `missing_field` deserializer. Attaching this function makes serde emit a
/// `missing_field` error for an absent key (via `deserialize_with`), while an
/// explicit `null` is still deserialized to `None`.
fn required_nullable<'de, D, T>(deserializer: D) -> Result<Option<T>, D::Error>
where
    D: Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::<T>::deserialize(deserializer)
}

fn parse_record(value: Value, line: u64) -> Result<Record, SourcePackageError> {
    let kind = value.get("kind").and_then(Value::as_str).ok_or_else(|| {
        SourcePackageError::new(
            ErrorKind::TypeMismatch,
            format!("line {line}: missing kind"),
        )
    })?;
    match kind {
        "element" => Ok(Record::Element(from_value_typed(value, line)?)),
        "text" => Ok(Record::Text(from_value_typed(value, line)?)),
        _ => Err(SourcePackageError::new(
            ErrorKind::UnknownKind,
            format!("line {line}: unknown record kind"),
        )),
    }
}

fn from_value_typed<T: serde::de::DeserializeOwned>(
    value: Value,
    line: u64,
) -> Result<T, SourcePackageError> {
    serde_json::from_value(value).map_err(|error| {
        SourcePackageError::new(
            ErrorKind::TypeMismatch,
            format!("line {line}: {}", safe_serde_detail(&error)),
        )
    })
}

/// Stable, source-free rendering of a serde_json error: the category and the
/// line/column are structural metadata; the original payload is never included.
fn safe_serde_detail(error: &serde_json::Error) -> String {
    format!(
        "json {:?} at line {} column {}",
        error.classify(),
        error.line(),
        error.column()
    )
}

fn strict_value(line: &str, line_number: u64) -> Result<Value, SourcePackageError> {
    let mut deserializer = serde_json::Deserializer::from_str(line);
    StrictValue::deserialize(&mut deserializer).map_err(|error| {
        if error.to_string().contains(DUPLICATE_KEY_SENTINEL) {
            SourcePackageError::new(
                ErrorKind::DuplicateJsonKey,
                format!("line {line_number}: duplicate JSON key"),
            )
        } else {
            SourcePackageError::new(
                ErrorKind::JsonSyntax,
                format!("line {line_number}: {}", safe_serde_detail(&error)),
            )
        }
    })?;
    deserializer.end().map_err(|error| {
        SourcePackageError::new(
            ErrorKind::JsonSyntax,
            format!("line {line_number}: {}", safe_serde_detail(&error)),
        )
    })?;
    serde_json::from_str::<Value>(line).map_err(|error| {
        SourcePackageError::new(
            ErrorKind::JsonSyntax,
            format!("line {line_number}: {}", safe_serde_detail(&error)),
        )
    })
}

fn is_hex64(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

fn sha256_hex(bytes: &[u8]) -> String {
    hex_lower(&Sha256::digest(bytes))
}

fn hex_lower(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

// -------------------------------------------- duplicate-key strict scanner #

/// A structural JSON validator that rejects duplicate object keys at any depth.
/// Tokenization/parsing is serde_json's; this walks the value tree and discards
/// the payload, so it carries no data of its own.
struct StrictValue;

impl<'de> Deserialize<'de> for StrictValue {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        deserializer.deserialize_any(StrictVisitor)
    }
}

struct StrictVisitor;

impl<'de> Visitor<'de> for StrictVisitor {
    type Value = StrictValue;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("any JSON value")
    }

    fn visit_bool<E: de::Error>(self, _value: bool) -> Result<StrictValue, E> {
        Ok(StrictValue)
    }

    fn visit_i64<E: de::Error>(self, _value: i64) -> Result<StrictValue, E> {
        Ok(StrictValue)
    }

    fn visit_u64<E: de::Error>(self, _value: u64) -> Result<StrictValue, E> {
        Ok(StrictValue)
    }

    fn visit_f64<E: de::Error>(self, _value: f64) -> Result<StrictValue, E> {
        Ok(StrictValue)
    }

    fn visit_str<E: de::Error>(self, _value: &str) -> Result<StrictValue, E> {
        Ok(StrictValue)
    }

    fn visit_string<E: de::Error>(self, _value: String) -> Result<StrictValue, E> {
        Ok(StrictValue)
    }

    fn visit_unit<E: de::Error>(self) -> Result<StrictValue, E> {
        Ok(StrictValue)
    }

    fn visit_none<E: de::Error>(self) -> Result<StrictValue, E> {
        Ok(StrictValue)
    }

    fn visit_some<D: Deserializer<'de>>(self, deserializer: D) -> Result<StrictValue, D::Error> {
        StrictValue::deserialize(deserializer)
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<StrictValue, A::Error> {
        while seq.next_element::<StrictValue>()?.is_some() {}
        Ok(StrictValue)
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<StrictValue, A::Error> {
        let mut seen: HashSet<String> = HashSet::new();
        while let Some(key) = map.next_key::<String>()? {
            if !seen.insert(key) {
                return Err(de::Error::custom(DUPLICATE_KEY_SENTINEL));
            }
            map.next_value::<StrictValue>()?;
        }
        Ok(StrictValue)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn limits_default_is_positive() {
        let limits = Limits::default();
        assert!(limits.max_input_bytes > 0);
        assert!(limits.max_depth > 0);
    }

    #[test]
    fn hex_lower_is_deterministic() {
        assert_eq!(hex_lower(&[0x00, 0xab, 0xff]), "00abff");
    }

    #[test]
    fn strict_value_rejects_duplicate_keys() {
        let error = strict_value("{\"a\":1,\"a\":2}", 1).expect_err("duplicate key rejected");
        assert_eq!(error.kind(), ErrorKind::DuplicateJsonKey);
    }
}
