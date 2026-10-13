//! Corpus-wide `document_groups` coverage over the S02 corpus manifest
//! (M224/S04/T03, ADR-0030 D2/D6, D667).
//!
//! This is the producer-side corpus pass required by ADR-0030 D6: it joins the
//! tracked S02 corpus manifest (`m223-s02-corpus-inventory/v1`: header +
//! `{relative_path, sha256, bytes}` rows) against the embedded ontology
//! catalog and publishes a derived, non-authoritative coverage artifact.
//!
//! Two axes are deliberately kept separate (D667 non-claim):
//!
//! - the **principal** axis: which export bank a path belongs to and whether
//!   that bank is normative law or non-normative practice. Owned by
//!   [`ln_kb_ontology::bank_normativity`]; `courts`/`fas` are non-normative,
//!   `npa`/`xml` are normative, anything else is a fail-visible `Unknown`.
//! - the **structural** axis: which `document_groups` profile the *path* alone
//!   binds to ([`ln_kb_ontology::catalog::OntologyCatalog::classify_document_group`],
//!   factor A, no XML re-parse). A structural `Unknown` is *not* a legal
//!   non-normativity claim.
//!
//! The artifact carries the accounting identities, the per-bank breakdown, the
//! structural group breakdown, the catalog-derived non-normative class list,
//! the CTV-blocked count (`= non-normative bank entries`), the catalog version,
//! and the manifest pins. It is ASCII by construction (non-ASCII payload is
//! escaped as JSON `\uXXXX`) and [`render_document_group_coverage`] re-asserts
//! that invariant fail-closed.
//!
//! `--check` re-derives the artifact in memory and byte-compares it against the
//! tracked file without writing (MEM1459 pattern). Nothing here re-parses XML:
//! classification is path-only over the manifest.

use std::collections::BTreeMap;
use std::error::Error;
use std::fmt;
use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use ln_kb_ontology::bank_normativity::{
    BankNormativity, bank_normativity, bank_of, ctv_blocked_by_bank,
};
use ln_kb_ontology::catalog::{DocumentGroupOutcome, OntologyCatalog, document_groups_version};

use crate::anchor_coverage::{CorpusManifest, parse_corpus_manifest};

/// Closed JSON schema id of the coverage artifact.
pub const COVERAGE_SCHEMA: &str = "m224-s04-document-group-coverage/v1";
/// Closed `kind` discriminator of the coverage artifact.
pub const COVERAGE_KIND: &str = "document_group_coverage";
/// Lifecycle status of R1000 carried by the artifact (D667: integrity is not
/// semantic completeness; S04 never closes R1000).
pub const R1000_STATUS: &str = "active/unclosed";
/// `by_group` key for a path that binds to no structural group.
pub const GROUP_UNKNOWN_KEY: &str = "Unknown";
/// `by_group` key for a path whose needles bind two structural groups at the
/// same rank.
pub const GROUP_CONFLICT_KEY: &str = "Conflict";

/// Stable `by_class`/`by_bank` key for the normative bank class.
pub const CLASS_NORMATIVE: &str = "normative";
/// Stable `by_class`/`by_bank` key for the non-normative (practice) bank class.
pub const CLASS_NON_NORMATIVE: &str = "non-normative";
/// Stable `by_class`/`by_bank` key for the fail-visible unknown bank class.
pub const CLASS_UNKNOWN: &str = "unknown";

/// Exit code: the artifact derives and (in write mode) is published.
pub const EXIT_OK: u8 = 0;
/// Exit code: malformed argv.
pub const EXIT_USAGE: u8 = 2;
/// Exit code: manifest/derivation failed (fail-closed, nothing written).
pub const EXIT_DERIVATION_FAILED: u8 = 3;
/// Exit code: the artifact could not be written.
pub const EXIT_OUT_UNWRITABLE: u8 = 4;
/// Exit code: `--check` could not read the tracked artifact.
pub const EXIT_ARTIFACT_MISSING: u8 = 5;
/// Exit code: `--check` byte-compare drifted.
pub const EXIT_DRIFT: u8 = 6;

/// Bounded non-claims carried by the coverage artifact.
pub const COVERAGE_NON_CLAIMS: [&str; 6] = [
    "integrity_is_not_semantic_completeness",
    "structural_group_unknown_is_not_legal_non_normativity",
    "bank_is_export_bucket_not_catalog_legal_bank",
    "non_normative_class_is_structural_coverage_heuristic_not_legal_claim",
    "xml_bank_practice_member_is_a_documented_coarse_approximation",
    "no_xml_reparse",
];

/// Maximum characters retained in a [`DocumentGroupCoverageError`] detail
/// (mirrors the bounded-detail discipline of [`crate::anchor_coverage`]).
const MAX_DETAIL_CHARS: usize = 240;

/// Per-bank accounting: total entries plus the normativity class split.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct BankCoverage {
    /// Total manifest entries in this bank.
    pub total: u64,
    /// Entries whose bank class is normative.
    pub normative: u64,
    /// Entries whose bank class is non-normative.
    pub non_normative: u64,
    /// Entries whose bank class is unknown.
    pub unknown: u64,
}

impl BankCoverage {
    fn record(&mut self, class: BankNormativity) {
        self.total += 1;
        match class {
            BankNormativity::Normative => self.normative += 1,
            BankNormativity::NonNormative => self.non_normative += 1,
            BankNormativity::Unknown => self.unknown += 1,
        }
    }
}

/// Derived class counts over the whole manifest.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct ClassCounts {
    /// Total manifest entries.
    pub entries: u64,
    /// Entries whose bank class is normative.
    pub normative: u64,
    /// Entries whose bank class is non-normative.
    pub non_normative: u64,
    /// Entries whose bank class is unknown.
    pub unknown: u64,
}

/// Complete corpus `document_groups` coverage state (aggregate only; the
/// 43k-entry manifest is not retained).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentGroupCoverage {
    /// Manifest path as given on the command line.
    pub manifest_path: String,
    /// `sha256:<hex>` of the manifest file bytes.
    pub manifest_sha256: String,
    /// Header `inventory_digest` of the manifest.
    pub inventory_digest: String,
    /// Total manifest entries.
    pub entries: u64,
    /// Bank-normativity counts, keyed by the stable class string.
    pub by_class: BTreeMap<String, u64>,
    /// Per-bank totals and class split (principal axis).
    pub by_bank: BTreeMap<String, BankCoverage>,
    /// Structural group counts (structural axis; `Unknown`/`Conflict` included
    /// as explicit keys, never folded into a group).
    pub by_group: BTreeMap<String, u64>,
    /// Sorted catalog group ids whose structural profile is non-normative.
    pub non_normative_classes: Vec<String>,
    /// Entries whose bank class is non-normative (the CTV barrier count).
    pub ctv_blocked: u64,
    /// `document_groups` section hash of the embedded catalog.
    pub document_groups_version: String,
}

impl DocumentGroupCoverage {
    /// Class counts derived from [`Self::by_class`].
    pub fn counts(&self) -> ClassCounts {
        ClassCounts {
            entries: self.entries,
            normative: self.class_count(CLASS_NORMATIVE),
            non_normative: self.class_count(CLASS_NON_NORMATIVE),
            unknown: self.class_count(CLASS_UNKNOWN),
        }
    }

    fn class_count(&self, class: &str) -> u64 {
        self.by_class.get(class).copied().unwrap_or(0)
    }
}

/// Typed, bounded coverage derivation failure. Every variant is fail-closed:
/// the caller must not publish a partial artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentGroupCoverageError {
    operation: String,
    detail: String,
}

impl DocumentGroupCoverageError {
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
}

impl fmt::Display for DocumentGroupCoverageError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "document group coverage {} failed: {}",
            self.operation, self.detail
        )
    }
}

impl Error for DocumentGroupCoverageError {}

/// Build the corpus `document_groups` coverage from the tracked S02 manifest
/// and the embedded ontology catalog.
///
/// Fail-closed: any manifest refusal, embedded-catalog failure, bound group
/// that is absent from the catalog, accounting identity violation, per-bank
/// header mismatch, or practice bank bound to an AST-bearing structural group
/// aborts derivation with no artifact written.
pub fn build_document_group_coverage(
    manifest_path: &Path,
) -> Result<DocumentGroupCoverage, DocumentGroupCoverageError> {
    let manifest_bytes = fs::read(manifest_path).map_err(|error| {
        DocumentGroupCoverageError::new("manifest-read", format!("read failed: {}", error.kind()))
    })?;
    let manifest_text = std::str::from_utf8(&manifest_bytes).map_err(|_| {
        DocumentGroupCoverageError::new("manifest-read", "manifest is not valid UTF-8")
    })?;
    let manifest = parse_corpus_manifest(manifest_text)
        .map_err(|error| DocumentGroupCoverageError::new(error.operation(), error.detail()))?;
    let manifest_sha256 = format!("sha256:{}", hex(&Sha256::digest(&manifest_bytes)));

    let catalog = OntologyCatalog::embedded()
        .map_err(|error| DocumentGroupCoverageError::new("catalog-load", error.to_string()))?;
    let mut non_normative_classes: Vec<String> = catalog
        .document_groups
        .iter()
        .filter(|group| group.is_non_normative())
        .map(|group| group.id.clone())
        .collect();
    non_normative_classes.sort();

    let subdirs = parse_manifest_subdirs(manifest_text)?;

    let mut by_class: BTreeMap<String, u64> = BTreeMap::new();
    let mut by_bank: BTreeMap<String, BankCoverage> = BTreeMap::new();
    let mut by_group: BTreeMap<String, u64> = BTreeMap::new();
    let mut ctv_blocked: u64 = 0;

    for entry in &manifest.entries {
        let bank = bank_of(&entry.relative_path).to_owned();
        let class = bank_normativity(&bank);
        *by_class.entry(class.as_str().to_owned()).or_insert(0) += 1;
        by_bank.entry(bank).or_default().record(class);
        if ctv_blocked_by_bank(class) {
            ctv_blocked += 1;
        }

        let key = match catalog.classify_document_group(Some(&entry.relative_path), None, None) {
            DocumentGroupOutcome::Bound { group, .. } => {
                let profile = catalog.document_group(&group).ok_or_else(|| {
                    DocumentGroupCoverageError::new(
                        "catalog-group",
                        format!("classifier bound an unknown document group: {group}"),
                    )
                })?;
                // CTV barrier at the corpus level: practice-bank text must bind
                // to a structurally non-normative (text-only) group, never to
                // an AST-bearing structural profile (ADR-0020, ADR-0030 D2).
                if class == BankNormativity::NonNormative && !profile.is_non_normative() {
                    return Err(DocumentGroupCoverageError::new(
                        "practice-bank-structural-leak",
                        format!("non-normative bank bound to structural group {group}"),
                    ));
                }
                group
            }
            DocumentGroupOutcome::Unknown => GROUP_UNKNOWN_KEY.to_owned(),
            DocumentGroupOutcome::Conflict { .. } => GROUP_CONFLICT_KEY.to_owned(),
        };
        *by_group.entry(key).or_insert(0) += 1;
    }

    let coverage = DocumentGroupCoverage {
        manifest_path: manifest_path.display().to_string(),
        manifest_sha256,
        inventory_digest: manifest.inventory_digest.clone(),
        entries: manifest.entries.len() as u64,
        by_class,
        by_bank,
        by_group,
        non_normative_classes,
        ctv_blocked,
        document_groups_version: document_groups_version(),
    };
    verify_accounting(&coverage, &manifest, &subdirs)?;
    Ok(coverage)
}

/// Verify the universal accounting identities plus the header per-bank pins.
fn verify_accounting(
    coverage: &DocumentGroupCoverage,
    manifest: &CorpusManifest,
    subdirs: &BTreeMap<String, u64>,
) -> Result<(), DocumentGroupCoverageError> {
    if coverage.entries != manifest.entries.len() as u64 {
        return Err(DocumentGroupCoverageError::new(
            "accounting",
            "entry count disagrees with the parsed manifest",
        ));
    }
    let class_total: u64 = coverage.by_class.values().sum();
    if class_total != coverage.entries {
        return Err(DocumentGroupCoverageError::new(
            "accounting",
            format!(
                "sum(by_class)={class_total} != entries={}",
                coverage.entries
            ),
        ));
    }
    let bank_total: u64 = coverage.by_bank.values().map(|bank| bank.total).sum();
    if bank_total != coverage.entries {
        return Err(DocumentGroupCoverageError::new(
            "accounting",
            format!(
                "sum(by_bank totals)={bank_total} != entries={}",
                coverage.entries
            ),
        ));
    }
    let group_total: u64 = coverage.by_group.values().sum();
    if group_total != coverage.entries {
        return Err(DocumentGroupCoverageError::new(
            "accounting",
            format!(
                "sum(by_group)={group_total} != entries={}",
                coverage.entries
            ),
        ));
    }
    if coverage.ctv_blocked != coverage.counts().non_normative {
        return Err(DocumentGroupCoverageError::new(
            "accounting",
            "ctv_blocked disagrees with the non-normative bank class count",
        ));
    }
    for (bank, expected) in subdirs {
        let actual = coverage
            .by_bank
            .get(bank)
            .map(|entry| entry.total)
            .unwrap_or(0);
        if actual != *expected {
            return Err(DocumentGroupCoverageError::new(
                "manifest-subdir-mismatch",
                format!("bank {bank} has {actual} entries but the header pins {expected}"),
            ));
        }
    }
    Ok(())
}

/// Parse the optional header `subdirs.<bank>.entries` pins into a bank→count
/// map. A missing `subdirs` key yields an empty map; a present but malformed
/// `subdirs` object is refused fail-closed.
fn parse_manifest_subdirs(text: &str) -> Result<BTreeMap<String, u64>, DocumentGroupCoverageError> {
    let parse_err = |detail: &str| DocumentGroupCoverageError::new("manifest-parse", detail);
    let header_line = text
        .lines()
        .next()
        .ok_or_else(|| parse_err("manifest is empty"))?;
    let header: serde_json::Value =
        serde_json::from_str(header_line).map_err(|_| parse_err("header is not JSON"))?;
    let mut out = BTreeMap::new();
    let Some(subdirs) = header.get("subdirs") else {
        return Ok(out);
    };
    let object = subdirs
        .as_object()
        .ok_or_else(|| parse_err("header subdirs is not an object"))?;
    for (bank, value) in object {
        let entries = value
            .get("entries")
            .and_then(serde_json::Value::as_u64)
            .ok_or_else(|| parse_err("header subdir lacks a numeric entries pin"))?;
        out.insert(bank.clone(), entries);
    }
    Ok(out)
}

/// Render the coverage JSON (`m224-s04-document-group-coverage/v1`),
/// deterministic and ASCII (non-ASCII payload is escaped as JSON `\uXXXX`).
pub fn render_document_group_coverage(
    coverage: &DocumentGroupCoverage,
) -> Result<String, DocumentGroupCoverageError> {
    let counts = coverage.counts();
    let mut out = String::with_capacity(4096);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(COVERAGE_SCHEMA));
    let _ = writeln!(out, "  \"kind\": {},", quote_json(COVERAGE_KIND));
    let _ = writeln!(
        out,
        "  \"counts\": {{\"entries\": {}, \"normative\": {}, \"non_normative\": {}, \"unknown\": {}}},",
        counts.entries, counts.normative, counts.non_normative, counts.unknown
    );
    let _ = writeln!(
        out,
        "  \"by_class\": {},",
        render_u64_map(&coverage.by_class)
    );
    out.push_str("  \"by_bank\": {\n");
    for (index, (bank, value)) in coverage.by_bank.iter().enumerate() {
        let comma = if index + 1 < coverage.by_bank.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(
            out,
            "    {}: {{\"total\": {}, \"normative\": {}, \"non_normative\": {}, \"unknown\": {}}}{comma}",
            quote_json(bank),
            value.total,
            value.normative,
            value.non_normative,
            value.unknown
        );
    }
    out.push_str("  },\n");
    let _ = writeln!(
        out,
        "  \"by_group\": {},",
        render_u64_map(&coverage.by_group)
    );
    let _ = writeln!(
        out,
        "  \"non_normative_classes\": {},",
        render_string_array(&coverage.non_normative_classes)
    );
    let _ = writeln!(out, "  \"ctv_blocked\": {},", coverage.ctv_blocked);
    let _ = writeln!(
        out,
        "  \"catalog\": {{\"document_groups_version\": {}}},",
        quote_json(&coverage.document_groups_version)
    );
    let _ = writeln!(
        out,
        "  \"manifest\": {{\"path\": {}, \"sha256\": {}, \"inventory_digest\": {}}},",
        quote_json(&coverage.manifest_path),
        quote_json(&coverage.manifest_sha256),
        quote_json(&coverage.inventory_digest)
    );
    let _ = writeln!(out, "  \"r1000_status\": {},", quote_json(R1000_STATUS));
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in COVERAGE_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 < COVERAGE_NON_CLAIMS.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(out, "    {}{comma}", quote_json(claim));
    }
    out.push_str("  ]\n}\n");
    ensure_ascii(&out, "coverage")?;
    Ok(out)
}

/// Re-derive the artifact in memory and byte-compare it against the tracked
/// file without writing (MEM1459 `--check` pattern).
pub fn verify_document_group_coverage(
    coverage: &DocumentGroupCoverage,
    out: &Path,
) -> Result<(), DocumentGroupCoverageError> {
    let expected = render_document_group_coverage(coverage)?;
    let actual = fs::read(out).map_err(|error| {
        DocumentGroupCoverageError::new(
            "check-missing",
            format!("coverage artifact is unreadable: {}", error.kind()),
        )
    })?;
    if actual == expected.as_bytes() {
        Ok(())
    } else {
        Err(DocumentGroupCoverageError::new(
            "check-drift",
            "coverage artifact differs from the live render",
        ))
    }
}

/// Parsed `document-group-coverage` argv.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct DocumentGroupCoverageCli {
    /// Manifest path (required).
    pub manifest: String,
    /// Artifact path (required).
    pub out: String,
    /// `--check`: re-derive and byte-compare instead of writing.
    pub check: bool,
}

/// Strict stdlib argv parser: `--manifest` and `--out` each need a following
/// value; `--check` is a flag. Both paths are required.
pub fn parse_document_group_coverage_args<I>(args: I) -> Result<DocumentGroupCoverageCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = DocumentGroupCoverageCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--manifest" => cli.manifest = next_value(&mut iter, "--manifest")?,
            "--out" => cli.out = next_value(&mut iter, "--out")?,
            "--check" => cli.check = true,
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    for (flag, value) in [("--manifest", &cli.manifest), ("--out", &cli.out)] {
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

/// Derive coverage and either publish the artifact or (in `--check` mode)
/// byte-compare it. Returns the process exit code and a one-line message.
pub fn run_document_group_coverage(cli: &DocumentGroupCoverageCli) -> (u8, String) {
    match run_document_group_coverage_inner(cli) {
        Ok(message) => (EXIT_OK, message),
        Err(error) => (
            document_group_coverage_exit_code_for(&error),
            error.to_string(),
        ),
    }
}

fn run_document_group_coverage_inner(
    cli: &DocumentGroupCoverageCli,
) -> Result<String, DocumentGroupCoverageError> {
    let coverage = build_document_group_coverage(Path::new(&cli.manifest))?;
    let counts = coverage.counts();
    if cli.check {
        verify_document_group_coverage(&coverage, Path::new(&cli.out))?;
        Ok(format!(
            "check=ok entries={} non_normative={}",
            counts.entries, counts.non_normative
        ))
    } else {
        let rendered = render_document_group_coverage(&coverage)?;
        fs::write(&cli.out, rendered.as_bytes()).map_err(|error| {
            DocumentGroupCoverageError::new(
                "write-artifact",
                format!("artifact is not writable: {}", error.kind()),
            )
        })?;
        Ok(format!(
            "entries={} non_normative={}",
            counts.entries, counts.non_normative
        ))
    }
}

/// Exit code for a derivation/check failure.
pub fn document_group_coverage_exit_code_for(error: &DocumentGroupCoverageError) -> u8 {
    match error.operation() {
        "check-missing" => EXIT_ARTIFACT_MISSING,
        "check-drift" => EXIT_DRIFT,
        "write-artifact" => EXIT_OUT_UNWRITABLE,
        _ => EXIT_DERIVATION_FAILED,
    }
}

/// Redaction guard: an artifact payload must be ASCII, else fail-closed.
fn ensure_ascii(artifact: &str, name: &str) -> Result<(), DocumentGroupCoverageError> {
    if artifact.is_ascii() {
        Ok(())
    } else {
        Err(DocumentGroupCoverageError::new(
            "redaction",
            format!("{name} artifact payload is not ASCII"),
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

fn render_string_array(values: &[String]) -> String {
    let mut out = String::from("[");
    for (index, value) in values.iter().enumerate() {
        if index > 0 {
            out.push_str(", ");
        }
        out.push_str(&quote_json(value));
    }
    out.push(']');
    out
}

/// Minimal JSON string escaper with a strict-ASCII posture: quotes,
/// backslashes, control characters, and every non-ASCII code point are
/// escaped. This keeps artifact payloads byte-ASCII (the redaction guard).
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
