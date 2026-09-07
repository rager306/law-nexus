//! Closed count-only artifact for hierarchy extraction candidates
//! (M202-9qf3ta S02, schema `law-nexus-hierarchy-candidate-artifact/v1`).
//!
//! The artifact is a fixed-order, hand-rendered JSON document carrying
//! counts, typed duplicate diagnostics and candidate identities only:
//!
//! - no titles and no raw legal text: `count_only` and `ascii_only` are
//!   pinned `true`, `authoritative` is pinned `false`;
//! - `source_binding.source_digest` is `domain::fingerprint_bytes` over the
//!   exact source bytes; `identity_digest` is `fingerprint_bytes` over the
//!   canonical identity stream (unique candidates in document order, then
//!   duplicate diagnostics, `NUL`-separated fields, one line per record);
//! - validation is closed-key: only the exact fixed key order and the exact
//!   pinned constants are accepted; anything else is typed drift.
//!
//! The failure surface is typed, never `eprintln!` at library level:
//! [`ArtifactError::SchemaDrift`] / [`ArtifactError::PathDrift`] /
//! [`ArtifactError::HashDrift`] / [`ArtifactError::NonAscii`] plus
//! [`ArtifactError::Usage`] / [`ArtifactError::OutUnwritable`] /
//! [`ArtifactError::SourceMissing`].
//!
//! Boundary: extraction in [`crate::hierarchy`] is unchanged; this module
//! never imports ontology/admission modules, never writes registry YAML and
//! never performs admission (D185 / D417 / D418). Source input is explicit;
//! there is no implicit corpus walk.

use std::fmt;
use std::fs;
use std::path::{Component, Path, PathBuf};

use crate::adapters::ConsultantWordMlBlockDecoder;
use crate::domain::{fingerprint_bytes, DecodeRequest, FamilyFormat, HierarchyLevel, PayloadRef};
use crate::hierarchy::{
    catalog_token, extract_hierarchy_candidates, HierarchyCandidateReport,
    HierarchyExtractDiagnostic,
};
use crate::ports::BlockDecoderPort;

/// Fixed artifact schema tag. Any other value is schema drift.
pub const HIERARCHY_CANDIDATE_ARTIFACT_SCHEMA: &str = "law-nexus-hierarchy-candidate-artifact/v1";

/// Pinned lifecycle: candidates are proposals, never adopted truth.
const ARTIFACT_LIFECYCLE: &str = "[proposed]";
const ARTIFACT_CRATE: &str = "ln-decode";
const ARTIFACT_DECODER: &str = "ConsultantWordMlBlockDecoder";
const ARTIFACT_EXTRACTOR: &str = "ln_decode::hierarchy::extract_hierarchy_candidates";
const WORDML_FAMILY: &str = "family:consultant-wordml";

/// Default `payload:` label for the tracked S02 fixture; `--label` overrides.
const DEFAULT_PAYLOAD_LABEL: &str = "payload:m202-hierarchy-candidates";

/// Registry YAML is registry territory: refused for every CLI role.
const REGISTRY_YAML_PATH: &str = "prd/architecture/kb-hierarchy-registry.yaml";

/// Artifact-specific non-claims appended to
/// [`HierarchyCandidateReport::HIERARCHY_CANDIDATE_NON_CLAIMS`].
const ARTIFACT_NON_CLAIMS_TAIL: [&str; 2] = [
    "Artifact is not kb-hierarchy-registry.yaml.",
    "Not R035 validation; corpus 8/94 is SKIP-capable sanity.",
];

/// Typed failure surface for the closed artifact boundary. Variants carry
/// identifiers and details only — never raw legal text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ArtifactError {
    Usage { detail: String },
    PathDrift { path: String },
    OutUnwritable { path: String },
    SourceMissing { path: String },
    SchemaDrift { detail: String },
    NonAscii { detail: String },
    HashDrift { detail: String },
}

impl ArtifactError {
    /// Pinned CLI exit code per failure class.
    pub fn exit_code(&self) -> i32 {
        match self {
            Self::Usage { .. } | Self::PathDrift { .. } => 2,
            Self::OutUnwritable { .. } => 3,
            Self::SourceMissing { .. } => 4,
            Self::SchemaDrift { .. } | Self::NonAscii { .. } | Self::HashDrift { .. } => 6,
        }
    }

    /// Single count-only stderr line. Drift classes use the pinned
    /// `drift=<class>` shape; operational failures use `error=...`.
    pub fn cli_line(&self) -> String {
        match self {
            Self::Usage { detail } => format!("error=usage detail={detail}"),
            Self::PathDrift { path } => format!("drift=path path={path}"),
            Self::OutUnwritable { path } => format!("error=out-unwritable path={path}"),
            Self::SourceMissing { path } => format!("error=source-missing path={path}"),
            Self::SchemaDrift { detail } => format!("drift=schema detail={detail}"),
            Self::NonAscii { detail } => format!("drift=non-ascii detail={detail}"),
            Self::HashDrift { detail } => format!("drift=hash detail={detail}"),
        }
    }
}

impl fmt::Display for ArtifactError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Usage { detail } => write!(formatter, "usage error: {detail}"),
            Self::PathDrift { path } => write!(formatter, "path drift: {path}"),
            Self::OutUnwritable { path } => write!(formatter, "output unwritable: {path}"),
            Self::SourceMissing { path } => write!(formatter, "source missing: {path}"),
            Self::SchemaDrift { detail } => write!(formatter, "schema drift: {detail}"),
            Self::NonAscii { detail } => write!(formatter, "non-ascii content: {detail}"),
            Self::HashDrift { detail } => write!(formatter, "hash drift: {detail}"),
        }
    }
}

impl std::error::Error for ArtifactError {}

/// Parsed CLI invocation for the thin artifact binary.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArtifactCli {
    pub source: PathBuf,
    pub mode: ArtifactMode,
    pub label: String,
}

/// What the CLI should do with the rendered artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ArtifactMode {
    /// Print the artifact to stdout (default mode).
    RenderStdout,
    /// Compare the rendered artifact byte-for-byte against the file at
    /// `out`; never writes, mismatch or missing file is hash drift.
    Check { out: PathBuf },
    /// Write the rendered artifact to `out`.
    Write { out: PathBuf },
}

/// Where the artifact source came from; recorded verbatim in the artifact.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArtifactSourceKind {
    File,
    InlineFixture,
}

impl ArtifactSourceKind {
    fn as_json(self) -> &'static str {
        match self {
            Self::File => "file",
            Self::InlineFixture => "inline-fixture",
        }
    }
}

/// Everything the renderer needs. Titles are deliberately absent: candidate
/// titles are never read (count-only boundary).
#[derive(Debug)]
pub struct ArtifactRenderInput<'a> {
    pub source_kind: ArtifactSourceKind,
    pub source_path: &'a str,
    pub payload_ref: &'a str,
    pub source_bytes: &'a [u8],
    pub report: &'a HierarchyCandidateReport,
    pub include_identities: bool,
}

/// Result of one CLI run: a count-only heartbeat plus, in stdout mode, the
/// rendered artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArtifactRunOutcome {
    pub heartbeat: String,
    pub stdout: Option<String>,
}

/// One identity record: unique candidate in document order, or one row of
/// the duplicate diagnostic tail. Shared by renderer and validator so the
/// canonical identity stream has exactly one definition.
#[derive(Debug, Clone, PartialEq, Eq)]
struct IdentityRow {
    token: String,
    number: String,
    path: Option<String>,
    key_path: String,
    depth: usize,
    marker_start: usize,
    marker_end: usize,
}

/// One duplicate diagnostic record in canonical order.
#[derive(Debug, Clone, PartialEq, Eq)]
struct DuplicateIdentityRow {
    token: String,
    key_path: String,
    first_index: usize,
    later_index: usize,
}

fn drift(detail: impl fmt::Display) -> ArtifactError {
    ArtifactError::SchemaDrift {
        detail: detail.to_string(),
    }
}

fn usage(detail: impl fmt::Display) -> ArtifactError {
    ArtifactError::Usage {
        detail: detail.to_string(),
    }
}

/// Fail closed on any string that could not round-trip as an unescaped JSON
/// string literal. Renderer inputs are library- or CLI-controlled; this is
/// the belt-and-braces guard, not an escape hatch.
fn json_plain(value: &str) -> &str {
    assert!(
        value.bytes().all(|byte| (0x20..0x7f).contains(&byte))
            && !value.contains('"')
            && !value.contains('\\'),
        "artifact string values must be printable ASCII without quotes or backslashes: {value:?}"
    );
    value
}

fn report_identity_rows(report: &HierarchyCandidateReport) -> Vec<IdentityRow> {
    report
        .candidates()
        .iter()
        .map(|candidate| {
            let span = candidate.marker_span();
            IdentityRow {
                token: candidate.catalog_token().to_owned(),
                number: candidate.number().to_owned(),
                path: candidate.path().map(str::to_owned),
                key_path: candidate.key_path().to_owned(),
                depth: candidate.depth(),
                marker_start: span.start(),
                marker_end: span.end(),
            }
        })
        .collect()
}

fn report_duplicate_rows(report: &HierarchyCandidateReport) -> Vec<DuplicateIdentityRow> {
    report
        .diagnostics()
        .iter()
        .map(|diagnostic| match diagnostic {
            HierarchyExtractDiagnostic::DuplicateKey {
                level,
                key_path,
                first_index,
                later_index,
            } => DuplicateIdentityRow {
                token: catalog_token(*level).to_owned(),
                key_path: key_path.clone(),
                first_index: *first_index,
                later_index: *later_index,
            },
        })
        .collect()
}

/// Canonical identity stream: unique candidates in document order, then
/// duplicate diagnostics, `NUL`-separated fields, one line per record.
/// This byte stream (not the file) is what `identity_digest` pins.
fn identity_stream(candidates: &[IdentityRow], duplicates: &[DuplicateIdentityRow]) -> String {
    let mut stream = String::new();
    for row in candidates {
        stream.push_str(&row.token);
        stream.push('\0');
        stream.push_str(&row.number);
        stream.push('\0');
        stream.push_str(row.path.as_deref().unwrap_or(""));
        stream.push('\0');
        stream.push_str(&row.key_path);
        stream.push('\0');
        stream.push_str(&row.depth.to_string());
        stream.push('\n');
    }
    for row in duplicates {
        stream.push_str("dup");
        stream.push('\0');
        stream.push_str(&row.token);
        stream.push('\0');
        stream.push_str(&row.key_path);
        stream.push('\0');
        stream.push_str(&row.first_index.to_string());
        stream.push('\0');
        stream.push_str(&row.later_index.to_string());
        stream.push('\n');
    }
    stream
}

/// Render the closed artifact with the fixed schema v1 key order. The output
/// is deterministic given the same input bytes and report.
pub fn render_hierarchy_candidate_artifact(input: &ArtifactRenderInput<'_>) -> String {
    let candidates = report_identity_rows(input.report);
    let duplicates = report_duplicate_rows(input.report);
    let source_digest = fingerprint_bytes(input.source_bytes);
    let identity_digest = fingerprint_bytes(identity_stream(&candidates, &duplicates).as_bytes());
    let extracted = input.report.extracted_count();
    let unique = input.report.unique_count();
    let duplicate = duplicates.len();
    let nested = candidates.iter().filter(|row| row.path.is_some()).count();

    let mut out = String::new();
    out.push_str("{\n");
    out.push_str(&format!(
        "  \"schema\": \"{HIERARCHY_CANDIDATE_ARTIFACT_SCHEMA}\",\n"
    ));
    out.push_str("  \"schema_version\": 1,\n");
    out.push_str(&format!("  \"lifecycle\": \"{ARTIFACT_LIFECYCLE}\",\n"));
    out.push_str("  \"count_only\": true,\n");
    out.push_str("  \"ascii_only\": true,\n");
    out.push_str("  \"authoritative\": false,\n");
    out.push_str(&format!("  \"crate\": \"{ARTIFACT_CRATE}\",\n"));
    out.push_str(&format!("  \"decoder\": \"{ARTIFACT_DECODER}\",\n"));
    out.push_str(&format!("  \"extractor\": \"{ARTIFACT_EXTRACTOR}\",\n"));
    out.push_str("  \"non_claims\": [\n");
    let claims: Vec<&str> = HierarchyCandidateReport::HIERARCHY_CANDIDATE_NON_CLAIMS
        .iter()
        .copied()
        .chain(ARTIFACT_NON_CLAIMS_TAIL)
        .collect();
    for (index, claim) in claims.iter().enumerate() {
        let comma = if index + 1 == claims.len() { "" } else { "," };
        out.push_str(&format!("    \"{claim}\"{comma}\n"));
    }
    out.push_str("  ],\n");
    out.push_str("  \"source_binding\": {\n");
    out.push_str(&format!(
        "    \"kind\": \"{}\",\n",
        input.source_kind.as_json()
    ));
    out.push_str(&format!(
        "    \"path\": \"{}\",\n",
        json_plain(input.source_path)
    ));
    out.push_str(&format!(
        "    \"payload_ref\": \"{}\",\n",
        json_plain(input.payload_ref)
    ));
    out.push_str(&format!("    \"source_digest\": \"{source_digest}\"\n"));
    out.push_str("  },\n");
    out.push_str("  \"counts\": {\n");
    out.push_str(&format!("    \"extracted\": {extracted},\n"));
    out.push_str(&format!("    \"unique\": {unique},\n"));
    out.push_str(&format!("    \"duplicate\": {duplicate},\n"));
    out.push_str(&format!("    \"nested\": {nested},\n"));
    out.push_str("    \"by_level\": {\n");
    let levels = HierarchyLevel::all();
    let level_total = levels.len();
    for (index, level) in levels.into_iter().enumerate() {
        let token = catalog_token(level);
        let count = candidates.iter().filter(|row| row.token == token).count();
        let comma = if index + 1 == level_total { "" } else { "," };
        out.push_str(&format!("      \"{token}\": {count}{comma}\n"));
    }
    out.push_str("    }\n");
    out.push_str("  },\n");
    out.push_str("  \"diagnostics\": {\n");
    out.push_str(&format!("    \"duplicate_key_count\": {duplicate},\n"));
    if duplicate == 0 {
        out.push_str("    \"duplicate_keys\": []\n");
    } else {
        out.push_str("    \"duplicate_keys\": [\n");
        for (index, row) in duplicates.iter().enumerate() {
            let comma = if index + 1 == duplicate { "" } else { "," };
            out.push_str(&format!(
                "      {{\"catalog_token\": \"{}\", \"key_path\": \"{}\", \
                 \"first_index\": {}, \"later_index\": {}}}{comma}\n",
                json_plain(&row.token),
                json_plain(&row.key_path),
                row.first_index,
                row.later_index
            ));
        }
        out.push_str("    ]\n");
    }
    out.push_str("  },\n");
    out.push_str(&format!("  \"identity_digest\": \"{identity_digest}\""));
    if input.include_identities {
        if candidates.is_empty() {
            out.push_str(",\n  \"candidates\": []\n");
        } else {
            out.push_str(",\n  \"candidates\": [\n");
            for (index, row) in candidates.iter().enumerate() {
                let comma = if index + 1 == candidates.len() {
                    ""
                } else {
                    ","
                };
                let path = match &row.path {
                    Some(path) => format!("\"{}\"", json_plain(path)),
                    None => "null".to_owned(),
                };
                out.push_str(&format!(
                    "    {{\"catalog_token\": \"{}\", \"number\": \"{}\", \"path\": {path}, \
                     \"key_path\": \"{}\", \"depth\": {}, \"marker_span\": \
                     {{\"start\": {}, \"end\": {}}}}}{comma}\n",
                    json_plain(&row.token),
                    json_plain(&row.number),
                    json_plain(&row.key_path),
                    row.depth,
                    row.marker_start,
                    row.marker_end
                ));
            }
            out.push_str("  ]\n");
        }
    } else {
        out.push('\n');
    }
    out.push_str("}\n");
    out
}

// ---------------------------------------------------------------------------
// Closed validator
// ---------------------------------------------------------------------------

/// Line cursor over the rendered layout. Any deviation from the expected
/// fixed-order line is schema drift.
struct Cursor<'a> {
    lines: &'a [&'a str],
    pos: usize,
}

impl<'a> Cursor<'a> {
    fn new(lines: &'a [&'a str]) -> Self {
        Self { lines, pos: 0 }
    }

    fn next_line(&mut self) -> Result<&'a str, ArtifactError> {
        let line = *self
            .lines
            .get(self.pos)
            .ok_or_else(|| drift("artifact ends before the closing brace"))?;
        self.pos += 1;
        Ok(line)
    }

    fn expect(&mut self, literal: &str) -> Result<(), ArtifactError> {
        let line = self.next_line()?;
        if line != literal {
            return Err(drift(format!("expected {literal:?}, found {line:?}")));
        }
        Ok(())
    }

    fn is_exhausted(&self) -> bool {
        self.pos == self.lines.len()
    }
}

fn plain_value<'a>(line: &'a str, prefix: &str, trailing: &str) -> Result<&'a str, ArtifactError> {
    let rest = line
        .strip_prefix(prefix)
        .ok_or_else(|| drift(format!("expected {prefix:?} line, found {line:?}")))?;
    rest.strip_suffix(trailing)
        .ok_or_else(|| drift(format!("missing {trailing:?} at end of {line:?}")))
}

fn quoted_value<'a>(line: &'a str, prefix: &str, trailing: &str) -> Result<&'a str, ArtifactError> {
    let value = plain_value(line, prefix, trailing)?;
    if value.contains('"') || value.contains('\\') {
        return Err(drift(
            "artifact strings must not contain quotes or backslashes",
        ));
    }
    Ok(value)
}

fn parse_usize(text: &str) -> Result<usize, ArtifactError> {
    if text.is_empty() || !text.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(drift(format!("expected a plain integer, found {text:?}")));
    }
    Ok(text
        .parse::<usize>()
        .expect("digit-only text parses as usize"))
}

fn count_value(line: &str, prefix: &str, trailing: &str) -> Result<usize, ArtifactError> {
    parse_usize(plain_value(line, prefix, trailing)?)
}

fn digest_value(line: &str, prefix: &str, trailing: &str) -> Result<String, ArtifactError> {
    let raw = quoted_value(line, prefix, trailing)?;
    validate_digest(raw)?;
    Ok(raw.to_owned())
}

fn validate_digest(raw: &str) -> Result<(), ArtifactError> {
    let hex = raw
        .strip_prefix("fnv1a64:")
        .ok_or_else(|| drift("digest must carry the fnv1a64: prefix"))?;
    if hex.len() != 16 || !hex.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(drift("digest must be 16 hex characters"));
    }
    Ok(())
}

fn level_token(token: &str) -> Result<&'static str, ArtifactError> {
    HierarchyLevel::all()
        .into_iter()
        .map(catalog_token)
        .find(|candidate| *candidate == token)
        .ok_or_else(|| drift(format!("unknown catalog token {token:?}")))
}

fn validate_segment(value: &str) -> Result<(), ArtifactError> {
    if value.is_empty()
        || !value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-' | b'/'))
    {
        return Err(drift(
            "artifact identifiers must be ascii alphanumerics with . - /",
        ));
    }
    Ok(())
}

fn parse_candidate_row(line: &str) -> Result<IdentityRow, ArtifactError> {
    const PREFIX: &str = "    {\"catalog_token\": \"";
    let rest = line
        .strip_prefix(PREFIX)
        .ok_or_else(|| drift(format!("malformed candidate row: {line:?}")))?;
    let (token, rest) = rest
        .split_once("\", \"number\": \"")
        .ok_or_else(|| drift("malformed candidate row catalog_token"))?;
    let token = level_token(token)?;
    let (number, rest) = rest
        .split_once("\", \"path\": ")
        .ok_or_else(|| drift("malformed candidate row number"))?;
    if !number
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || byte == b'.')
    {
        return Err(drift("candidate number must be alphanumeric with dots"));
    }
    let (path, rest) = if let Some(rest) = rest.strip_prefix("null, \"key_path\": \"") {
        (None, rest)
    } else if let Some(quoted) = rest.strip_prefix('"') {
        let (value, rest) = quoted
            .split_once("\", \"key_path\": \"")
            .ok_or_else(|| drift("malformed candidate row path"))?;
        validate_segment(value)?;
        (Some(value.to_owned()), rest)
    } else {
        return Err(drift("candidate path must be null or a string"));
    };
    let (key_path, rest) = rest
        .split_once("\", \"depth\": ")
        .ok_or_else(|| drift("malformed candidate row key_path"))?;
    validate_segment(key_path)?;
    let (depth_text, rest) = rest
        .split_once(", \"marker_span\": {\"start\": ")
        .ok_or_else(|| drift("malformed candidate row depth"))?;
    let depth = parse_usize(depth_text)?;
    let (start_text, rest) = rest
        .split_once(", \"end\": ")
        .ok_or_else(|| drift("malformed candidate marker span start"))?;
    let start = parse_usize(start_text)?;
    // Rows close with `}}` plus a comma separator except on the last row;
    // the byte-exact check pins separator placement, so both spellings
    // parse here. Strip the separator first: `}},` ends with a comma.
    let row_body = rest.strip_suffix(',').unwrap_or(rest);
    let end_text = row_body
        .strip_suffix("}}")
        .ok_or_else(|| drift("unterminated candidate row"))?;
    let end = parse_usize(end_text)?;
    if start >= end {
        return Err(drift("marker span must be non-empty"));
    }
    Ok(IdentityRow {
        token: token.to_owned(),
        number: number.to_owned(),
        path,
        key_path: key_path.to_owned(),
        depth,
        marker_start: start,
        marker_end: end,
    })
}

fn parse_duplicate_row(line: &str) -> Result<DuplicateIdentityRow, ArtifactError> {
    const PREFIX: &str = "      {\"catalog_token\": \"";
    let rest = line
        .strip_prefix(PREFIX)
        .ok_or_else(|| drift(format!("malformed duplicate row: {line:?}")))?;
    let (token, rest) = rest
        .split_once("\", \"key_path\": \"")
        .ok_or_else(|| drift("malformed duplicate row catalog_token"))?;
    let token = level_token(token)?;
    let (key_path, rest) = rest
        .split_once("\", \"first_index\": ")
        .ok_or_else(|| drift("malformed duplicate row key_path"))?;
    validate_segment(key_path)?;
    let (first_text, rest) = rest
        .split_once(", \"later_index\": ")
        .ok_or_else(|| drift("malformed duplicate row indices"))?;
    let first_index = parse_usize(first_text)?;
    // Rows close with `}` plus a comma separator except on the last row;
    // the byte-exact check pins separator placement, so both spellings
    // parse here. Strip the separator first: `},` ends with a comma.
    let later_body = rest.strip_suffix(',').unwrap_or(rest);
    let later_text = later_body
        .strip_suffix('}')
        .ok_or_else(|| drift("unterminated duplicate row"))?;
    let later_index = parse_usize(later_text)?;
    Ok(DuplicateIdentityRow {
        token: token.to_owned(),
        key_path: key_path.to_owned(),
        first_index,
        later_index,
    })
}

fn parse_identity_line(line: &str) -> Result<(String, bool), ArtifactError> {
    const PREFIX: &str = "  \"identity_digest\": \"";
    let rest = line
        .strip_prefix(PREFIX)
        .ok_or_else(|| drift(format!("expected identity_digest line, found {line:?}")))?;
    let close = rest
        .rfind('"')
        .ok_or_else(|| drift("unterminated identity digest"))?;
    let raw = &rest[..close];
    let has_candidates = match &rest[close + 1..] {
        "" => false,
        "," => true,
        _ => return Err(drift("unexpected content after identity digest")),
    };
    validate_digest(raw)?;
    Ok((raw.to_owned(), has_candidates))
}

/// Light closed-shape check on the recorded source path: repo-relative, no
/// parent escape, and never the registry YAML.
fn validate_artifact_path(path: &str) -> Result<(), ArtifactError> {
    if path.starts_with('/')
        || path.split('/').any(|segment| segment == "..")
        || path == REGISTRY_YAML_PATH
    {
        return Err(drift("source path must stay inside the repository"));
    }
    Ok(())
}

/// Validate the closed artifact: ASCII-only bytes, exact fixed key order,
/// pinned constants, consistent counts, and (when identity rows are present)
/// an `identity_digest` that matches the canonical identity stream.
pub fn validate_hierarchy_candidate_artifact(artifact: &str) -> Result<(), ArtifactError> {
    if !artifact.bytes().all(|byte| byte < 0x80) {
        return Err(ArtifactError::NonAscii {
            detail: "artifact must be ascii-only".to_owned(),
        });
    }
    let lines: Vec<&str> = artifact.lines().collect();
    let mut cursor = Cursor::new(&lines);

    cursor.expect("{")?;
    cursor.expect(&format!(
        "  \"schema\": \"{HIERARCHY_CANDIDATE_ARTIFACT_SCHEMA}\","
    ))?;
    cursor.expect("  \"schema_version\": 1,")?;
    cursor.expect(&format!("  \"lifecycle\": \"{ARTIFACT_LIFECYCLE}\","))?;
    cursor.expect("  \"count_only\": true,")?;
    cursor.expect("  \"ascii_only\": true,")?;
    cursor.expect("  \"authoritative\": false,")?;
    cursor.expect(&format!("  \"crate\": \"{ARTIFACT_CRATE}\","))?;
    cursor.expect(&format!("  \"decoder\": \"{ARTIFACT_DECODER}\","))?;
    cursor.expect(&format!("  \"extractor\": \"{ARTIFACT_EXTRACTOR}\","))?;
    cursor.expect("  \"non_claims\": [")?;
    let claims: Vec<&str> = HierarchyCandidateReport::HIERARCHY_CANDIDATE_NON_CLAIMS
        .iter()
        .copied()
        .chain(ARTIFACT_NON_CLAIMS_TAIL)
        .collect();
    for (index, claim) in claims.iter().enumerate() {
        let comma = if index + 1 == claims.len() { "" } else { "," };
        cursor.expect(&format!("    \"{claim}\"{comma}"))?;
    }
    cursor.expect("  ],")?;
    cursor.expect("  \"source_binding\": {")?;
    let kind = quoted_value(cursor.next_line()?, "    \"kind\": \"", "\",")?;
    if !matches!(kind, "file" | "inline-fixture") {
        return Err(drift(format!("unknown source_binding kind {kind:?}")));
    }
    let path = quoted_value(cursor.next_line()?, "    \"path\": \"", "\",")?;
    validate_artifact_path(path)?;
    let payload_ref = quoted_value(cursor.next_line()?, "    \"payload_ref\": \"", "\",")?;
    if PayloadRef::parse(payload_ref).is_err() {
        return Err(drift("payload_ref is not a valid payload ref"));
    }
    let source_digest = digest_value(cursor.next_line()?, "    \"source_digest\": \"", "\"")?;
    cursor.expect("  },")?;
    cursor.expect("  \"counts\": {")?;
    let extracted = count_value(cursor.next_line()?, "    \"extracted\": ", ",")?;
    let unique = count_value(cursor.next_line()?, "    \"unique\": ", ",")?;
    let duplicate = count_value(cursor.next_line()?, "    \"duplicate\": ", ",")?;
    let nested = count_value(cursor.next_line()?, "    \"nested\": ", ",")?;
    cursor.expect("    \"by_level\": {")?;
    let mut by_level: Vec<(&'static str, usize)> = Vec::new();
    let levels = HierarchyLevel::all();
    let level_total = levels.len();
    for (index, level) in levels.into_iter().enumerate() {
        let token = catalog_token(level);
        let line = cursor.next_line()?;
        let prefix = format!("      \"{token}\": ");
        let value = line
            .strip_prefix(prefix.as_str())
            .ok_or_else(|| drift(format!("expected by_level key {token:?}, found {line:?}")))?;
        let value = if index + 1 == level_total {
            value
        } else {
            value
                .strip_suffix(',')
                .ok_or_else(|| drift(format!("missing comma after by_level {token:?}")))?
        };
        by_level.push((token, parse_usize(value)?));
    }
    cursor.expect("    }")?;
    cursor.expect("  },")?;
    cursor.expect("  \"diagnostics\": {")?;
    let duplicate_key_count =
        count_value(cursor.next_line()?, "    \"duplicate_key_count\": ", ",")?;
    let mut duplicate_rows: Vec<DuplicateIdentityRow> = Vec::new();
    let duplicate_keys_open = cursor.next_line()?;
    if duplicate_keys_open == "    \"duplicate_keys\": [" {
        loop {
            let line = cursor.next_line()?;
            if line == "    ]" {
                break;
            }
            duplicate_rows.push(parse_duplicate_row(line)?);
        }
    } else if duplicate_keys_open != "    \"duplicate_keys\": []" {
        return Err(drift(format!(
            "expected duplicate_keys, found {duplicate_keys_open:?}"
        )));
    }
    cursor.expect("  },")?;
    let (identity_digest, has_candidates) = parse_identity_line(cursor.next_line()?)?;
    let candidate_rows: Option<Vec<IdentityRow>> = if has_candidates {
        let open = cursor.next_line()?;
        let mut rows: Vec<IdentityRow> = Vec::new();
        if open == "  \"candidates\": [" {
            loop {
                let line = cursor.next_line()?;
                if line == "  ]" {
                    break;
                }
                rows.push(parse_candidate_row(line)?);
            }
        } else if open != "  \"candidates\": []" {
            return Err(drift(format!("expected candidates, found {open:?}")));
        }
        Some(rows)
    } else {
        None
    };
    cursor.expect("}")?;
    if !cursor.is_exhausted() {
        return Err(drift("trailing content after the closing brace"));
    }

    // Closed count consistency. Counts do not enter the identity stream, so
    // inconsistent counts are schema drift, not hash drift.
    if duplicate_key_count != duplicate {
        return Err(drift("duplicate_key_count must equal counts.duplicate"));
    }
    if duplicate_rows.len() != duplicate {
        return Err(drift("duplicate_keys rows must equal counts.duplicate"));
    }
    if extracted != unique + duplicate {
        return Err(drift("extracted must equal unique + duplicate"));
    }
    let by_level_total: usize = by_level.iter().map(|(_, count)| count).sum();
    if by_level_total != unique {
        return Err(drift("by_level counts must total the unique count"));
    }
    if let Some(rows) = &candidate_rows {
        if rows.len() != unique {
            return Err(drift("candidate rows must equal the unique count"));
        }
        let nested_rows = rows.iter().filter(|row| row.path.is_some()).count();
        if nested_rows != nested {
            return Err(drift("nested must equal rows carrying a ladder path"));
        }
        for (token, count) in &by_level {
            let actual = rows.iter().filter(|row| &row.token == token).count();
            if actual != *count {
                return Err(drift(format!("by_level mismatch for {token:?}")));
            }
        }
        for row in rows {
            let expected_depth = row
                .path
                .as_deref()
                .map(|path| path.split('/').count())
                .unwrap_or(1);
            if row.depth != expected_depth {
                return Err(drift("candidate depth must match its ladder path"));
            }
        }
        for row in &duplicate_rows {
            if row.first_index >= row.later_index {
                return Err(drift("duplicate first_index must precede later_index"));
            }
            if row.later_index >= extracted {
                return Err(drift("duplicate indices must address raw hits"));
            }
        }
        let stream = identity_stream(rows, &duplicate_rows);
        if fingerprint_bytes(stream.as_bytes()) != identity_digest {
            return Err(ArtifactError::HashDrift {
                detail: "identity digest does not match artifact identities".to_owned(),
            });
        }
    }
    let _ = source_digest;
    Ok(())
}

/// Check one artifact against the expected render: the artifact must first
/// validate as a closed v1 document (typed drift classes surface from it),
/// then the bytes must match exactly; any remaining difference is hash drift.
pub fn check_hierarchy_candidate_artifact(
    artifact: &str,
    expected: &str,
) -> Result<(), ArtifactError> {
    validate_hierarchy_candidate_artifact(artifact)?;
    if artifact != expected {
        return Err(ArtifactError::HashDrift {
            detail: "artifact bytes differ from the expected render".to_owned(),
        });
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// CLI argument parser
// ---------------------------------------------------------------------------

fn take_value(
    flags: &mut impl Iterator<Item = String>,
    flag: &str,
) -> Result<String, ArtifactError> {
    flags
        .next()
        .ok_or_else(|| usage(format!("{flag} requires a value")))
}

/// Fail-closed repo path policy: refuse parent escapes, registry YAML and
/// every YAML target (the artifact CLI writes JSON only). Repo-relative
/// paths must be plain `Normal` components. Absolute paths are accepted
/// only when lexically contained in the repository root (controlled
/// runtime/test output such as `CARGO_TARGET_TMPDIR` under `target/`);
/// anything outside the root stays refused.
fn validate_repo_path(path: &Path) -> Result<(), ArtifactError> {
    let text = path.to_string_lossy().into_owned();
    let refused = || ArtifactError::PathDrift { path: text.clone() };
    if text.is_empty()
        || text.contains('\\')
        || text.contains('"')
        || !text.bytes().all(|byte| (0x20..0x7f).contains(&byte))
    {
        return Err(refused());
    }
    if text == REGISTRY_YAML_PATH || text.ends_with(".yaml") || text.ends_with(".yml") {
        return Err(refused());
    }
    if path.is_absolute() {
        let root = find_repo_root().ok_or_else(refused)?;
        if path != root.as_path() && !path.starts_with(&root) {
            return Err(refused());
        }
        if path
            .components()
            .any(|component| matches!(component, Component::ParentDir))
        {
            return Err(refused());
        }
        return Ok(());
    }
    if !path
        .components()
        .all(|component| matches!(component, Component::Normal(_)))
    {
        return Err(refused());
    }
    Ok(())
}

/// Parse the thin CLI surface: `--source <path>` (required), `--check`,
/// `--write`, `--out <path>`, `--label <payload ref>`. `--check` and
/// `--write` are mutually exclusive; both require `--out`. Registry YAML and
/// absolute/parent-escaping paths are refused before any filesystem access.
pub fn parse_artifact_args(args: Vec<String>) -> Result<ArtifactCli, ArtifactError> {
    let mut source: Option<PathBuf> = None;
    let mut check = false;
    let mut write = false;
    let mut out: Option<PathBuf> = None;
    let mut label: Option<String> = None;

    let mut flags = args.into_iter();
    while let Some(flag) = flags.next() {
        match flag.as_str() {
            "--source" => {
                source = Some(PathBuf::from(take_value(&mut flags, "--source")?));
            }
            "--check" => check = true,
            "--write" => write = true,
            "--out" => {
                out = Some(PathBuf::from(take_value(&mut flags, "--out")?));
            }
            "--label" => {
                let value = take_value(&mut flags, "--label")?;
                if PayloadRef::parse(&value).is_err() {
                    return Err(usage("--label must be a valid payload ref"));
                }
                label = Some(value);
            }
            other => return Err(usage(format!("unknown flag {other:?}"))),
        }
    }

    let mode = match (check, write, out.as_ref()) {
        (true, true, _) => return Err(usage("--check and --write are mutually exclusive")),
        (true, false, Some(out)) => ArtifactMode::Check { out: out.clone() },
        (false, true, Some(out)) => ArtifactMode::Write { out: out.clone() },
        (true, false, None) => return Err(usage("--check requires --out")),
        (false, true, None) => return Err(usage("--write requires --out")),
        (false, false, Some(_)) => return Err(usage("--out requires --check or --write")),
        (false, false, None) => ArtifactMode::RenderStdout,
    };

    let source = source.ok_or_else(|| usage("missing --source"))?;
    validate_repo_path(&source)?;
    if let ArtifactMode::Check { out } | ArtifactMode::Write { out } = &mode {
        validate_repo_path(out)?;
    }

    Ok(ArtifactCli {
        source,
        mode,
        label: label.unwrap_or_else(|| DEFAULT_PAYLOAD_LABEL.to_owned()),
    })
}

// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------

/// Walk up from the working directory to the repository root so that
/// repo-relative CLI paths resolve both from the repo root (subprocess) and
/// from the crate directory (cargo test).
fn find_repo_root() -> Option<PathBuf> {
    let mut dir = std::env::current_dir().ok()?;
    loop {
        if dir.join(".git").exists() {
            return Some(dir);
        }
        if !dir.pop() {
            return None;
        }
    }
}

fn resolve_repo_path(path: &Path) -> PathBuf {
    if path.is_absolute() {
        return path.to_path_buf();
    }
    match find_repo_root() {
        Some(root) => root.join(path),
        None => path.to_path_buf(),
    }
}

/// Pinned count-only heartbeat: no title, no absolute or corpus paths.
fn heartbeat_line(report: &HierarchyCandidateReport) -> String {
    format!(
        "extracted={} unique={} drift=0",
        report.extracted_count(),
        report.unique_count()
    )
}

/// One candidate identity from a closed v1 artifact (normalized view).
/// Titles never enter: the artifact is count-only by construction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateArtifactIdentityView {
    pub catalog_token: String,
    pub number: String,
    /// CC-path ladder when the identity is nested; `None` for flat keys.
    pub path: Option<String>,
    /// Stable key admission rows reference (`number` flat, ladder nested).
    pub key_path: String,
}

/// Typed closed view of a v1 candidate artifact: bound digests plus the
/// candidate identities, without titles or raw legal text. The artifact is
/// first gated through [`validate_hierarchy_candidate_artifact`], so every
/// returned view already satisfies the closed schema, pinned constants,
/// count consistency, and (when identities are present) the identity
/// digest. Cross-crate admission (D427) builds its normalized evidence
/// from this view; the SHA-256 over the artifact file bytes stays with the
/// caller, which owns the file read.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateArtifactView {
    pub artifact_schema: String,
    pub lifecycle: String,
    pub authoritative: bool,
    /// Recorded `source_binding.path` the artifact was rendered from.
    pub artifact_source_path: String,
    pub source_digest: String,
    pub identity_digest: String,
    pub candidates: Vec<CandidateArtifactIdentityView>,
}

fn view_scalar<'a>(line: &'a str, prefix: &str, trailing: &str) -> Option<&'a str> {
    let rest = line.strip_prefix(prefix)?;
    let value = rest.strip_suffix(trailing)?;
    if value.contains('"') || value.contains('\\') {
        return None;
    }
    Some(value)
}

/// Parse a closed v1 artifact into its typed view. Fails closed with the
/// same typed [`ArtifactError`] classes as the validator; anything the
/// validator rejects never becomes a view.
pub fn parse_candidate_artifact_view(
    artifact: &str,
) -> Result<CandidateArtifactView, ArtifactError> {
    validate_hierarchy_candidate_artifact(artifact)?;
    let mut schema: Option<String> = None;
    let mut lifecycle: Option<String> = None;
    let mut authoritative: Option<bool> = None;
    let mut source_path: Option<String> = None;
    let mut source_digest: Option<String> = None;
    let mut identity_digest: Option<String> = None;
    let mut candidates: Vec<CandidateArtifactIdentityView> = Vec::new();
    for line in artifact.lines() {
        if line.starts_with("    {\"catalog_token\": \"") {
            let row = parse_candidate_row(line)?;
            candidates.push(CandidateArtifactIdentityView {
                catalog_token: row.token,
                number: row.number,
                path: row.path,
                key_path: row.key_path,
            });
            continue;
        }
        if let Some(value) = view_scalar(line, "  \"schema\": \"", "\",") {
            schema = Some(value.to_owned());
        } else if let Some(value) = view_scalar(line, "  \"lifecycle\": \"", "\",") {
            lifecycle = Some(value.to_owned());
        } else if let Some(rest) = line.strip_prefix("  \"authoritative\": ") {
            let value = rest.strip_suffix(',').unwrap_or(rest);
            authoritative = Some(match value {
                "true" => true,
                "false" => false,
                _ => {
                    return Err(drift("authoritative must be a boolean"));
                }
            });
        } else if let Some(value) = view_scalar(line, "    \"path\": \"", "\",") {
            source_path = Some(value.to_owned());
        } else if let Some(value) = view_scalar(line, "    \"source_digest\": \"", "\"") {
            validate_digest(value)?;
            source_digest = Some(value.to_owned());
        } else if line.starts_with("  \"identity_digest\": \"") {
            let (digest, _) = parse_identity_line(line)?;
            identity_digest = Some(digest);
        }
    }
    let missing = |field: &str| drift(format!("artifact view is missing {field:?}"));
    Ok(CandidateArtifactView {
        artifact_schema: schema.ok_or_else(|| missing("schema"))?,
        lifecycle: lifecycle.ok_or_else(|| missing("lifecycle"))?,
        authoritative: authoritative.ok_or_else(|| missing("authoritative"))?,
        artifact_source_path: source_path.ok_or_else(|| missing("source_binding.path"))?,
        source_digest: source_digest.ok_or_else(|| missing("source_digest"))?,
        identity_digest: identity_digest.ok_or_else(|| missing("identity_digest"))?,
        candidates,
    })
}

/// Run one parsed CLI invocation. Source input is explicit (no implicit
/// corpus walk); `--check` never writes and a missing expected file fails
/// closed as hash drift without creating it.
pub fn run_hierarchy_candidate_artifact(
    cli: &ArtifactCli,
) -> Result<ArtifactRunOutcome, ArtifactError> {
    // Enforce the path gate at the runner boundary too: hand-built `ArtifactCli`
    // values bypass the argument parser, so parser-only enforcement left a
    // write-through path to registry YAML (D185 fail-closed).
    validate_repo_path(&cli.source)?;
    if let ArtifactMode::Check { out } | ArtifactMode::Write { out } = &cli.mode {
        validate_repo_path(out)?;
    }
    let source_path = resolve_repo_path(&cli.source);
    let source_bytes = fs::read(&source_path).map_err(|_| ArtifactError::SourceMissing {
        path: cli.source.display().to_string(),
    })?;
    let payload_ref =
        PayloadRef::parse(&cli.label).map_err(|_| usage("label must be a valid payload ref"))?;
    let family = FamilyFormat::parse(WORDML_FAMILY)
        .map_err(|_| usage("internal family constant rejected"))?;
    let request = DecodeRequest::new(payload_ref, family, &source_bytes);
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .map_err(|_| ArtifactError::SchemaDrift {
            detail: "source failed to decode as consultant wordml".to_owned(),
        })?;
    let report = extract_hierarchy_candidates(&blocks);
    let rendered = render_hierarchy_candidate_artifact(&ArtifactRenderInput {
        source_kind: ArtifactSourceKind::File,
        source_path: &cli.source.to_string_lossy(),
        payload_ref: &cli.label,
        source_bytes: &source_bytes,
        report: &report,
        include_identities: true,
    });
    let heartbeat = heartbeat_line(&report);
    match &cli.mode {
        ArtifactMode::RenderStdout => Ok(ArtifactRunOutcome {
            heartbeat,
            stdout: Some(rendered),
        }),
        ArtifactMode::Write { out } => {
            let out_path = resolve_repo_path(out);
            if let Some(parent) = out_path.parent() {
                fs::create_dir_all(parent).map_err(|_| ArtifactError::OutUnwritable {
                    path: out.display().to_string(),
                })?;
            }
            fs::write(&out_path, rendered.as_bytes()).map_err(|_| {
                ArtifactError::OutUnwritable {
                    path: out.display().to_string(),
                }
            })?;
            Ok(ArtifactRunOutcome {
                heartbeat,
                stdout: None,
            })
        }
        ArtifactMode::Check { out } => {
            let out_path = resolve_repo_path(out);
            let expected_bytes = fs::read(&out_path).map_err(|_| ArtifactError::HashDrift {
                detail: "expected artifact is missing or unreadable".to_owned(),
            })?;
            let expected =
                String::from_utf8(expected_bytes).map_err(|_| ArtifactError::NonAscii {
                    detail: "expected artifact is not utf-8".to_owned(),
                })?;
            check_hierarchy_candidate_artifact(&expected, &rendered)?;
            Ok(ArtifactRunOutcome {
                heartbeat,
                stdout: None,
            })
        }
    }
}
