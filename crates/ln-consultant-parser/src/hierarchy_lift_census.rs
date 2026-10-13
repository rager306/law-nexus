//! Per-document hierarchy-lift census consumer over the materialized
//! cleaned-wire JSONL layer (M224/S05/T03).
//!
//! This is the corpus-facing *consumer* half of the S05 lift: it reads **only**
//! the materialized cleaned-wire JSONL artifact (schema
//! `law-nexus/cleaned-projection/v1`) produced by the `cleaned-project export`
//! producer, reconstructs the decoded block stream through
//! [`ln_decode::wire_blocks::blocks_from_cleaned_projection`], extracts the
//! hierarchy markers with the single authoritative extractor
//! ([`ln_decode::hierarchy::extract_hierarchy_candidates`]) and places them on
//! the detected `document_groups` ladder
//! ([`ln_decode::hierarchy_lift::detect_and_lift`]).
//!
//! It carries **no** `--from-xml` option and never opens the source XML/ODT
//! artifact: the producer touches the source bytes exactly once, the consumer
//! reads the JSONL layer (the S07 `consumer-run` contract, mirrored here).
//! The original source identity is *read*, not re-derived, from the projection's
//! [`ln_decode::cleaned_wire::SourcePin`] (`wire_source.sha256`).
//!
//! Output is one counts-only per-document JSON (`m224-s05-hierarchy-lift-doc/v1`,
//! ASCII by construction): no decoded text, only group identity, the detection
//! provenance, token/role/marker counts, the unmapped-token accounting and the
//! declared non-claims. The bounded corpus census (T04) aggregates these
//! per-document payloads; nothing here is a legal hierarchy claim.
//!
//! Boundary (S05): this is a structural ladder placement, not a `StructuralAst`
//! fold and not an assembly FSM / edition timeline step — those stay in S06. No
//! `ComponentConcept` is minted; the crate does not depend on `ln-kb-ontology`
//! (MEM832).

use std::collections::BTreeMap;
use std::error::Error;
use std::fmt;
use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use ln_decode::cleaned_wire::read_cleaned_wire;
use ln_decode::domain::SourceFormatId;
use ln_decode::hierarchy::extract_hierarchy_candidates;
use ln_decode::hierarchy_lift::detect_and_lift;
use ln_decode::structural_profile::{
    DetectionFactor, GroupDetection, StructuralProfile, UnknownReason,
};
use ln_decode::wire_blocks::blocks_from_cleaned_projection;

/// Closed JSON schema id of the per-document census payload.
pub const DOC_SCHEMA: &str = "m224-s05-hierarchy-lift-doc/v1";
/// Closed `kind` discriminator of the per-document census payload.
pub const DOC_KIND: &str = "hierarchy_lift_doc";
/// Lifecycle status of R1000 carried by the payload (D667: integrity is not
/// semantic completeness; S05 never closes R1000).
pub const R1000_STATUS: &str = "active/unclosed";
/// `by_group` key for a document whose group could not be detected (fail-closed).
pub const GROUP_UNKNOWN_KEY: &str = "Unknown";

/// Exit code: the per-document payload derived successfully.
pub const EXIT_OK: u8 = 0;
/// Exit code: malformed argv.
pub const EXIT_USAGE: u8 = 2;
/// Exit code: the cleaned-wire JSONL input is unreadable.
pub const EXIT_INPUT_UNREADABLE: u8 = 3;
/// Exit code: the output artifact is not writable.
pub const EXIT_OUT_UNWRITABLE: u8 = 4;
/// Exit code: the cleaned-wire layer (or a downstream lift invariant) was
/// refused fail-closed and nothing was published.
pub const EXIT_WIRE_REFUSED: u8 = 5;

/// Bounded non-claims carried by the payload: what this consumer is **not**.
pub const CENSUS_NON_CLAIMS: [&str; 5] = [
    "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml_or_odt",
    "counts_are_a_structural_lift_heuristic_not_legal_hierarchy_truth",
    "integrity_is_not_semantic_completeness",
    "an_unmapped_marker_is_fail_closed_never_a_guessed_default",
    "no_component_concept_is_minted",
];

/// Maximum characters retained in a bounded error detail (mirrors
/// [`crate::document_group_coverage`]).
const MAX_DETAIL_CHARS: usize = 240;

/// Accepted `--source-format` values. The producer knows the document family;
/// the consumer never infers it (it only labels the reconstructed blocks).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum CensusSourceFormat {
    /// Consultant WordML family (`.xml`).
    #[default]
    WordMl,
    /// Garant ODT family (`.odt`).
    Odt,
}

impl CensusSourceFormat {
    /// Stable CLI token (`wordml` | `odt`) carried in the payload.
    pub const fn as_str(self) -> &'static str {
        match self {
            CensusSourceFormat::WordMl => "wordml",
            CensusSourceFormat::Odt => "odt",
        }
    }

    fn from_token(token: &str) -> Option<Self> {
        match token {
            "wordml" => Some(CensusSourceFormat::WordMl),
            "odt" => Some(CensusSourceFormat::Odt),
            _ => None,
        }
    }

    fn to_source_format_id(self) -> SourceFormatId {
        match self {
            CensusSourceFormat::WordMl => SourceFormatId::ConsultantWordMl,
            CensusSourceFormat::Odt => SourceFormatId::GarantOdt,
        }
    }
}

/// Parsed `hierarchy-lift-census` argv.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct HierarchyLiftCensusCli {
    /// Materialized cleaned-wire JSONL path (required).
    pub cleaned_wire: String,
    /// Corpus-relative document path used for group detection (required).
    pub corpus_path: String,
    /// Declared source family (optional; defaults to `wordml`).
    pub source_format: CensusSourceFormat,
    /// Per-document payload path (optional; JSON goes to stdout when absent).
    pub out: Option<String>,
}

/// Counts-only per-document hierarchy-lift census. Carries no decoded text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyLiftDocCensus {
    /// Corpus-relative path as given on the command line.
    pub corpus_path: String,
    /// Declared source family token.
    pub source_format: String,
    /// Detected (or metadata-named) group id; `""` when none was detected.
    pub group: String,
    /// Closed detection provenance token.
    pub detection: String,
    /// Markers per group (`Unknown` for an undetected group); sum == markers.
    pub by_group: BTreeMap<String, u64>,
    /// Markers per decode catalog token; sum == markers.
    pub by_catalog_token: BTreeMap<String, u64>,
    /// Bound placements per ladder role; sum == bound.
    pub by_role: BTreeMap<String, u64>,
    /// Unique first-wins candidates considered.
    pub markers: u64,
    /// Candidates placed on a normative ladder role.
    pub bound: u64,
    /// Candidates that failed a normative placement (any reason).
    pub unknown: u64,
    /// Markers carried by the `text_only` non-normative barrier.
    pub non_normative_markers: u64,
    /// True when the detected profile is `text_only`.
    pub non_normative: bool,
    /// Token accounting for every candidate that failed a normative
    /// placement; sum == unknown.
    pub unmapped_tokens: BTreeMap<String, u64>,
    /// Lowercase-hex sha256 of the frozen source bytes (from the projection).
    pub wire_source_sha256: String,
    /// Byte length of the frozen source (from the projection).
    pub wire_source_bytes: u64,
    /// `sha256:<hex>` of the consumed cleaned-wire JSONL bytes.
    pub cleaned_wire_sha256: String,
}

/// Typed, bounded census derivation failure. Every variant is fail-closed: the
/// caller must not publish a partial payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyLiftCensusError {
    operation: String,
    detail: String,
}

impl HierarchyLiftCensusError {
    /// Build a bounded error for `operation`.
    pub fn new(operation: impl Into<String>, detail: impl Into<String>) -> Self {
        Self {
            operation: operation.into(),
            detail: bound_detail(detail.into()),
        }
    }

    /// Stable operation tag used for exit-code mapping.
    pub fn operation(&self) -> &str {
        &self.operation
    }

    /// Bounded human detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }

    /// Process exit code for this failure.
    pub fn exit_code(&self) -> u8 {
        match self.operation.as_str() {
            "input-read" => EXIT_INPUT_UNREADABLE,
            "out-write" => EXIT_OUT_UNWRITABLE,
            _ => EXIT_WIRE_REFUSED,
        }
    }
}

impl fmt::Display for HierarchyLiftCensusError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "hierarchy lift census {} failed: {}",
            self.operation, self.detail
        )
    }
}

impl Error for HierarchyLiftCensusError {}

/// Strict stdlib argv parser: `--cleaned-wire`, `--corpus-path`, `--source-format`
/// and `--out` each need a following value. The two input paths are required.
/// `--from-xml` is deliberately not accepted.
pub fn parse_hierarchy_lift_census_args<I>(args: I) -> Result<HierarchyLiftCensusCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = HierarchyLiftCensusCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--cleaned-wire" => cli.cleaned_wire = next_value(&mut iter, "--cleaned-wire")?,
            "--corpus-path" => cli.corpus_path = next_value(&mut iter, "--corpus-path")?,
            "--source-format" => {
                let token = next_value(&mut iter, "--source-format")?;
                cli.source_format = CensusSourceFormat::from_token(&token).ok_or_else(|| {
                    format!("unsupported --source-format '{token}' (expected wordml|odt)")
                })?;
            }
            "--out" => cli.out = Some(next_value(&mut iter, "--out")?),
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    for (flag, value) in [
        ("--cleaned-wire", &cli.cleaned_wire),
        ("--corpus-path", &cli.corpus_path),
    ] {
        if value.is_empty() {
            return Err(format!("missing required {flag}"));
        }
    }
    Ok(cli)
}

fn next_value(iter: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    iter.next()
        .ok_or_else(|| format!("missing value for {flag}"))
}

/// Derive the per-document census from the materialized cleaned-wire layer.
///
/// Fail-closed: an unreadable input, a refused wire layer, a failed block
/// bridge, an unavailable embedded catalog, or an accounting-identity violation
/// aborts derivation with no payload produced. Only the JSONL layer is read —
/// the source artifact is never opened.
pub fn build_hierarchy_lift_doc_census(
    cli: &HierarchyLiftCensusCli,
) -> Result<HierarchyLiftDocCensus, HierarchyLiftCensusError> {
    let bytes = fs::read(&cli.cleaned_wire).map_err(|error| {
        HierarchyLiftCensusError::new(
            "input-read",
            format!("cleaned wire is unreadable: {}", error.kind()),
        )
    })?;
    let text = std::str::from_utf8(&bytes).map_err(|_| {
        HierarchyLiftCensusError::new("input-read", "cleaned wire is not valid UTF-8")
    })?;
    let cleaned_wire_sha256 = format!("sha256:{}", hex(&Sha256::digest(&bytes)));

    let projection = read_cleaned_wire(text).map_err(|error| {
        HierarchyLiftCensusError::new(
            "wire-refused",
            format!("cleaned wire refused: {}", error.kind().as_str()),
        )
    })?;
    let wire_source_sha256 = projection.source.sha256.clone();
    let wire_source_bytes = projection.source.bytes;

    let blocks =
        blocks_from_cleaned_projection(&projection, cli.source_format.to_source_format_id())
            .map_err(|error| {
                HierarchyLiftCensusError::new(
                    "wire-refused",
                    format!("block bridge refused: {}", error.as_str()),
                )
            })?;
    let candidates = extract_hierarchy_candidates(&blocks);

    let profile = StructuralProfile::embedded().map_err(|error| {
        HierarchyLiftCensusError::new(
            "profile-load",
            format!("embedded catalog unavailable: {error}"),
        )
    })?;
    let report = detect_and_lift(
        &profile,
        Some(cli.corpus_path.as_str()),
        None,
        None,
        &blocks,
        &candidates,
    );

    let mut by_catalog_token: BTreeMap<String, u64> = BTreeMap::new();
    for candidate in candidates.candidates() {
        *by_catalog_token
            .entry(candidate.catalog_token().to_owned())
            .or_insert(0) += 1;
    }

    let mut by_group: BTreeMap<String, u64> = BTreeMap::new();
    if report.markers_total > 0 {
        let key = if report.group.is_empty() {
            GROUP_UNKNOWN_KEY.to_owned()
        } else {
            report.group.clone()
        };
        *by_group.entry(key).or_insert(0) += report.markers_total as u64;
    }

    let non_normative_markers = if report.non_normative {
        report.markers_total as u64
    } else {
        0
    };

    let census = HierarchyLiftDocCensus {
        corpus_path: cli.corpus_path.clone(),
        source_format: cli.source_format.as_str().to_owned(),
        group: report.group.clone(),
        detection: detection_token(&report.detection),
        by_group,
        by_catalog_token,
        by_role: report
            .per_role
            .iter()
            .map(|(role, count)| (role.clone(), *count as u64))
            .collect(),
        markers: report.markers_total as u64,
        bound: report.bound as u64,
        unknown: report.unknown as u64,
        non_normative_markers,
        non_normative: report.non_normative,
        unmapped_tokens: report
            .unmapped_tokens
            .iter()
            .map(|(token, count)| (token.clone(), *count as u64))
            .collect(),
        wire_source_sha256,
        wire_source_bytes,
        cleaned_wire_sha256,
    };
    verify_accounting(&census)?;
    Ok(census)
}

/// Render the per-document payload (`m224-s05-hierarchy-lift-doc/v1`),
/// deterministic and ASCII (non-ASCII payload is escaped as JSON `\uXXXX`).
pub fn render_hierarchy_lift_doc(
    census: &HierarchyLiftDocCensus,
) -> Result<String, HierarchyLiftCensusError> {
    let mut out = String::with_capacity(2048);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(DOC_SCHEMA));
    let _ = writeln!(out, "  \"kind\": {},", quote_json(DOC_KIND));
    let _ = writeln!(
        out,
        "  \"corpus_path\": {},",
        quote_json(&census.corpus_path)
    );
    let _ = writeln!(
        out,
        "  \"source_format\": {},",
        quote_json(&census.source_format)
    );
    let _ = writeln!(out, "  \"group\": {},", quote_json(&census.group));
    let _ = writeln!(out, "  \"detection\": {},", quote_json(&census.detection));
    let _ = writeln!(
        out,
        "  \"lift\": {{\"markers\": {}, \"bound\": {}, \"unknown\": {}, \"non_normative\": {}}},",
        census.markers, census.bound, census.unknown, census.non_normative_markers
    );
    let _ = writeln!(out, "  \"by_group\": {},", render_u64_map(&census.by_group));
    let _ = writeln!(
        out,
        "  \"by_catalog_token\": {},",
        render_u64_map(&census.by_catalog_token)
    );
    let _ = writeln!(out, "  \"by_role\": {},", render_u64_map(&census.by_role));
    let _ = writeln!(
        out,
        "  \"unmapped_tokens\": {},",
        render_u64_map(&census.unmapped_tokens)
    );
    let _ = writeln!(out, "  \"non_normative\": {},", census.non_normative);
    let _ = writeln!(
        out,
        "  \"wire_source\": {{\"sha256\": {}, \"bytes\": {}}},",
        quote_json(&census.wire_source_sha256),
        census.wire_source_bytes
    );
    let _ = writeln!(
        out,
        "  \"cleaned_wire_sha256\": {},",
        quote_json(&census.cleaned_wire_sha256)
    );
    let _ = writeln!(out, "  \"r1000_status\": {},", quote_json(R1000_STATUS));
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in CENSUS_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 < CENSUS_NON_CLAIMS.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(out, "    {}{comma}", quote_json(claim));
    }
    out.push_str("  ]\n}\n");
    ensure_ascii(&out, "per-document census")?;
    Ok(out)
}

/// Derive the payload and either emit it (stdout) or write it to `--out`.
/// Returns the process exit code and the message line: the JSON payload when
/// no `--out` is given, otherwise a one-line summary.
pub fn run_hierarchy_lift_census(cli: &HierarchyLiftCensusCli) -> (u8, String) {
    let census = match build_hierarchy_lift_doc_census(cli) {
        Ok(census) => census,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    let json = match render_hierarchy_lift_doc(&census) {
        Ok(json) => json,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    match cli.out.as_deref().filter(|value| !value.is_empty()) {
        Some(out) => match fs::write(Path::new(out), json.as_bytes()) {
            Ok(()) => (EXIT_OK, summary_line(&census)),
            Err(error) => (
                EXIT_OUT_UNWRITABLE,
                HierarchyLiftCensusError::new(
                    "out-write",
                    format!("artifact is not writable: {}", error.kind()),
                )
                .to_string(),
            ),
        },
        None => (EXIT_OK, json),
    }
}

/// Closed detection provenance token for the payload (observability only).
fn detection_token(detection: &GroupDetection) -> String {
    match detection {
        GroupDetection::Bound { factor, .. } => match factor {
            DetectionFactor::Needle => "bound:needle",
            DetectionFactor::NeedleAndProbe => "bound:needle_and_probe",
        },
        GroupDetection::Unknown { reason } => match reason {
            UnknownReason::NoMetadata => "unknown:no_metadata",
            UnknownReason::ProbeConflict { .. } => "unknown:probe_conflict",
        },
        GroupDetection::Conflict { .. } => "conflict",
    }
    .to_owned()
}

/// One-line human summary for the `--out` write path.
fn summary_line(census: &HierarchyLiftDocCensus) -> String {
    format!(
        "group={} markers={} bound={} unknown={} non_normative={}",
        if census.group.is_empty() {
            GROUP_UNKNOWN_KEY
        } else {
            census.group.as_str()
        },
        census.markers,
        census.bound,
        census.unknown,
        census.non_normative
    )
}

/// Fail-closed accounting invariants of one per-document payload.
fn verify_accounting(census: &HierarchyLiftDocCensus) -> Result<(), HierarchyLiftCensusError> {
    if census.markers != census.bound + census.unknown + census.non_normative_markers {
        return Err(HierarchyLiftCensusError::new(
            "accounting",
            "markers != bound + unknown + non_normative",
        ));
    }
    if sum_map(&census.by_catalog_token) != census.markers {
        return Err(HierarchyLiftCensusError::new(
            "accounting",
            "sum(by_catalog_token) != markers",
        ));
    }
    if sum_map(&census.by_group) != census.markers {
        return Err(HierarchyLiftCensusError::new(
            "accounting",
            "sum(by_group) != markers",
        ));
    }
    if sum_map(&census.by_role) != census.bound {
        return Err(HierarchyLiftCensusError::new(
            "accounting",
            "sum(by_role) != bound",
        ));
    }
    if sum_map(&census.unmapped_tokens) != census.unknown {
        return Err(HierarchyLiftCensusError::new(
            "accounting",
            "sum(unmapped_tokens) != unknown",
        ));
    }
    if census.non_normative && census.non_normative_markers != census.markers {
        return Err(HierarchyLiftCensusError::new(
            "accounting",
            "non_normative document does not account every marker as non-normative",
        ));
    }
    Ok(())
}

fn sum_map(map: &BTreeMap<String, u64>) -> u64 {
    map.values().sum()
}

/// Redaction guard: a payload must be ASCII, else fail-closed.
fn ensure_ascii(payload: &str, name: &str) -> Result<(), HierarchyLiftCensusError> {
    if payload.is_ascii() {
        Ok(())
    } else {
        Err(HierarchyLiftCensusError::new(
            "redaction",
            format!("{name} payload is not ASCII"),
        ))
    }
}

fn render_u64_map(map: &BTreeMap<String, u64>) -> String {
    let mut out = String::from("{");
    let mut first = true;
    for (key, count) in map {
        if !first {
            out.push_str(", ");
        }
        first = false;
        out.push_str(&quote_json(key));
        let _ = write!(out, ": {count}");
    }
    out.push('}');
    out
}

/// Minimal JSON string escaper with a strict-ASCII posture: quotes,
/// backslashes, control characters, and every non-ASCII code point are
/// escaped. This keeps payloads byte-ASCII (the redaction guard).
fn quote_json(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for character in value.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            character if (character as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", character as u32);
            }
            character if !character.is_ascii() => {
                let code = character as u32;
                if code > 0xFFFF {
                    let offset = code - 0x1_0000;
                    let _ = write!(
                        out,
                        "\\u{:04x}\\u{:04x}",
                        0xD800 + (offset >> 10),
                        0xDC00 + (offset & 0x3FF)
                    );
                } else {
                    let _ = write!(out, "\\u{code:04x}");
                }
            }
            character => out.push(character),
        }
    }
    out.push('"');
    out
}

fn hex(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0F) as usize] as char);
    }
    out
}

fn bound_detail(raw: String) -> String {
    let mut out = String::new();
    for character in raw.chars() {
        if character.is_control() {
            continue;
        }
        if out.chars().count() >= MAX_DETAIL_CHARS {
            break;
        }
        out.push(character);
    }
    out
}
