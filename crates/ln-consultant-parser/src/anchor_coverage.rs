//! Corpus-wide Consultant URI anchor coverage: the S02 corpus manifest joined
//! against the catalog, deterministic coverage accounting, the identity
//! envelope corpus run, and the 0-match negative probe (M224/S02/T04,
//! ADR-0030 D1, D744).
//!
//! Inputs are the tracked S02 corpus manifest
//! (`m223-s02-corpus-inventory/v1`: header + `{relative_path, sha256, bytes}`
//! rows) and the observed Consultant catalog (`editions.relative_path`,
//! `editions.source_id` = the full offline token). Every manifest entry gets
//! exactly one resolution outcome:
//!
//! - the catalog resolves the path → the catalog `source_id` is parsed as a
//!   [`ConsultantUriAnchor`] and must survive **byte-exact** (a parse that
//!   would normalize the token is refused, never silently accepted);
//! - the catalog has no row → [`AnchorStatus::UnresolvedNotInCatalog`], an
//!   honest counted class, never a silent skip.
//!
//! The outputs are two derived, non-authoritative artifacts:
//!
//! - the coverage JSON (`m224-s02-uri-anchor-coverage/v1`): counts, per-bank
//!   accounting, the closed-set negative probe, and the manifest/catalog pins;
//! - the identity envelope JSONL: a header line plus one
//!   [`IdentityEnvelope`] line per manifest entry, in manifest order, rendered
//!   by [`IdentityEnvelope::render_jsonl_line`] (T03 wire).
//!
//! Both artifacts are ASCII by construction (non-ASCII payload is escaped as
//! JSON `\uXXXX`), and [`render_coverage_json`] / [`render_envelope_jsonl`]
//! re-assert that invariant fail-closed. The negative probe matches extracted
//! document numbers against `editions.source_id` (exact and `LIKE`) purely as
//! diagnostics/negative evidence — it is never a resolution path.
//!
//! `--check` re-derives both artifacts in memory and byte-compares them
//! against the tracked files without writing (MEM1459 pattern).

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;
use std::fmt::Write as _;
use std::fs;
use std::io::Read as _;
use std::path::Path;

use rusqlite::{Connection, OpenFlags};
use sha2::{Digest, Sha256};

use ln_decode::consultant_uri_anchor::ConsultantUriAnchor;
use ln_decode::identity_envelope::{IDENTITY_ENVELOPE_SCHEMA, IdentityEnvelope};

use crate::catalog_anchor::CatalogAnchorPort;
use crate::catalog_sqlite::SqliteCatalog;

/// Closed JSON schema id of the coverage artifact.
pub const COVERAGE_SCHEMA: &str = "m224-s02-uri-anchor-coverage/v1";
/// Closed JSONL schema id of the S02 corpus manifest this module consumes.
pub const MANIFEST_SCHEMA: &str = "m223-s02-corpus-inventory/v1";
/// Lifecycle status of R1000 carried by both artifacts (D667: integrity is not
/// semantic completeness; S02 never closes R1000).
pub const R1000_STATUS: &str = "active/unclosed";
/// Closed set of extracted document numbers used by the negative probe. The
/// probe is diagnostic evidence only; it is not a resolution path.
pub const NEGATIVE_PROBE_NUMBERS: [&str; 3] = ["44-ФЗ", "402-ФЗ", "5-фкз"];
/// Exit code: both artifacts derive and (in write mode) are published.
pub const EXIT_OK: u8 = 0;
/// Exit code: malformed argv.
pub const EXIT_USAGE: u8 = 2;
/// Exit code: manifest/catalog derivation failed (fail-closed, nothing written).
pub const EXIT_DERIVATION_FAILED: u8 = 3;
/// Exit code: an artifact could not be written.
pub const EXIT_OUT_UNWRITABLE: u8 = 4;
/// Exit code: `--check` could not read a tracked artifact.
pub const EXIT_ARTIFACT_MISSING: u8 = 5;
/// Exit code: `--check` byte-compare drifted.
pub const EXIT_DRIFT: u8 = 6;

/// Bounded non-claims carried by the coverage artifact. The offline tokens are
/// declared opaque external references (not credentials); the unresolved class
/// is declared honest accounting; no token is decoded or re-derived.
pub const COVERAGE_NON_CLAIMS: [&str; 4] = [
    "integrity_is_not_semantic_completeness",
    "consultant_uri_tokens_are_opaque_external_references_not_credentials",
    "anchor_unresolved_is_a_counted_closed_class_not_a_silent_skip",
    "no_offline_token_is_decoded_normalized_or_re_derived",
];

/// Maximum characters retained in an [`AnchorCoverageError`] detail (mirrors
/// the bounded-detail discipline of [`crate::catalog::CatalogError`]).
const MAX_DETAIL_CHARS: usize = 240;

/// One manifest record: pinned structural identity of a corpus document.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ManifestEntry {
    /// Corpus-relative path (`courts/acn/…xml`), `/`-joined, ASCII.
    pub relative_path: String,
    /// Content hash `sha256:<64 lowercase hex>` over the raw document bytes.
    pub sha256: String,
    /// Raw document byte length.
    pub bytes: u64,
}

/// Parsed S02 corpus manifest.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CorpusManifest {
    /// Schema id of the manifest header.
    pub schema: String,
    /// Manifest rows in file order.
    pub entries: Vec<ManifestEntry>,
    /// Header inventory digest `sha256:<64 lowercase hex>`.
    pub inventory_digest: String,
}

/// One resolution outcome for a manifest entry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnchorCoverageEntry {
    /// Corpus-relative path, verbatim from the manifest.
    pub relative_path: String,
    /// Manifest content hash, byte-exact.
    pub sha256: String,
    /// Manifest byte length.
    pub bytes: u64,
    /// `Some(anchor)` when the catalog resolved the path; `None` is the
    /// `anchor_unresolved` class.
    pub anchor: Option<ConsultantUriAnchor>,
}

/// One row of the closed-set negative probe.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NegativeProbeRow {
    /// The extracted document number probed.
    pub number: String,
    /// `count(*)` of `editions.source_id = <number>` (expected 0).
    pub exact_matches: u64,
    /// `count(*)` of `editions.source_id LIKE '%<number>%'` (expected 0).
    pub like_matches: u64,
}

/// Closed-set negative probe: extracted document numbers never match a catalog
/// `source_id` (the number is encrypted inside the offline token; MEM1781).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NegativeProbe {
    /// The probed numbers, in closed-set order.
    pub numbers: Vec<String>,
    /// Summed exact matches across [`Self::numbers`].
    pub exact_matches: u64,
    /// Summed `LIKE` matches across [`Self::numbers`].
    pub like_matches: u64,
    /// Per-number detail, in closed-set order.
    pub per_number: Vec<NegativeProbeRow>,
}

/// Complete corpus coverage state (in manifest order).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnchorCoverage {
    /// Manifest path as given on the command line.
    pub manifest_path: String,
    /// `sha256:<hex>` of the manifest file bytes.
    pub manifest_sha256: String,
    /// Header `inventory_digest` of the manifest.
    pub inventory_digest: String,
    /// Catalog path as given on the command line.
    pub catalog_path: String,
    /// `sha256:<hex>` of the catalog file bytes.
    pub catalog_sha256: String,
    /// Per-entry outcomes, in manifest order.
    pub entries: Vec<AnchorCoverageEntry>,
    /// Anchored counts by bank (first `relative_path` component).
    pub anchored_by_bank: BTreeMap<String, u64>,
    /// Unresolved counts by bank (first `relative_path` component).
    pub unresolved_by_bank: BTreeMap<String, u64>,
    /// The closed-set negative probe result.
    pub negative_probe: NegativeProbe,
}

impl AnchorCoverage {
    /// `(entries, anchored, unresolved)` derived from [`Self::entries`].
    pub fn counts(&self) -> (u64, u64, u64) {
        let entries = self.entries.len() as u64;
        let anchored = self
            .entries
            .iter()
            .filter(|entry| entry.anchor.is_some())
            .count() as u64;
        (entries, anchored, entries - anchored)
    }
}

/// Typed, bounded coverage derivation failure. Every variant is fail-closed:
/// the caller must not publish a partial artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnchorCoverageError {
    operation: &'static str,
    detail: String,
}

impl AnchorCoverageError {
    pub fn new(operation: &'static str, detail: impl Into<String>) -> Self {
        Self {
            operation,
            detail: bound_detail(detail.into()),
        }
    }

    pub fn operation(&self) -> &'static str {
        self.operation
    }

    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for AnchorCoverageError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "anchor coverage {} failed: {}",
            self.operation, self.detail
        )
    }
}

impl Error for AnchorCoverageError {}

/// Parse the S02 corpus manifest fail-closed.
///
/// Refused: a missing/foreign header schema, a header without
/// `counts.entries` or `inventory_digest`, malformed or blank record lines,
/// records without `relative_path`/`sha256`/`bytes`, a `sha256` that is not
/// `sha256:<64 lowercase hex>`, unsafe/non-ASCII relative paths, duplicate
/// paths, and a body count that disagrees with the header.
pub fn parse_corpus_manifest(text: &str) -> Result<CorpusManifest, AnchorCoverageError> {
    fn parse_err(detail: &str) -> AnchorCoverageError {
        AnchorCoverageError::new("manifest-parse", detail)
    }

    let mut lines = text.lines();
    let header_line = lines.next().ok_or_else(|| parse_err("manifest is empty"))?;
    let header: serde_json::Value =
        serde_json::from_str(header_line).map_err(|_| parse_err("header is not JSON"))?;
    let schema = header
        .get("schema")
        .and_then(serde_json::Value::as_str)
        .ok_or_else(|| parse_err("header has no schema"))?;
    if schema != MANIFEST_SCHEMA {
        return Err(parse_err("unexpected manifest schema"));
    }
    let expected_entries = header
        .get("counts")
        .and_then(|counts| counts.get("entries"))
        .and_then(serde_json::Value::as_u64)
        .ok_or_else(|| parse_err("header has no counts.entries"))?;
    let inventory_digest = header
        .get("inventory_digest")
        .and_then(serde_json::Value::as_str)
        .filter(|digest| !digest.is_empty())
        .ok_or_else(|| parse_err("header has no inventory_digest"))?
        .to_owned();

    let mut entries = Vec::new();
    let mut seen: BTreeSet<String> = BTreeSet::new();
    for line in lines {
        if line.trim().is_empty() {
            return Err(parse_err("blank manifest record line"));
        }
        let record: serde_json::Value =
            serde_json::from_str(line).map_err(|_| parse_err("record line is not JSON"))?;
        let relative_path = record
            .get("relative_path")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| parse_err("record has no relative_path"))?;
        validate_relative_path(relative_path)?;
        if !seen.insert(relative_path.to_owned()) {
            return Err(AnchorCoverageError::new(
                "manifest-duplicate-path",
                format!("duplicate relative_path in manifest: {relative_path}"),
            ));
        }
        let sha256 = record
            .get("sha256")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| parse_err("record has no sha256"))?;
        validate_sha256(sha256)?;
        let bytes = record
            .get("bytes")
            .and_then(serde_json::Value::as_u64)
            .ok_or_else(|| parse_err("record has no bytes"))?;
        entries.push(ManifestEntry {
            relative_path: relative_path.to_owned(),
            sha256: sha256.to_owned(),
            bytes,
        });
    }

    if entries.len() as u64 != expected_entries {
        return Err(AnchorCoverageError::new(
            "manifest-count-mismatch",
            format!(
                "header counts.entries={expected_entries} but body has {}",
                entries.len()
            ),
        ));
    }
    Ok(CorpusManifest {
        schema: schema.to_owned(),
        entries,
        inventory_digest,
    })
}

fn validate_relative_path(path: &str) -> Result<(), AnchorCoverageError> {
    fn unsafe_path() -> AnchorCoverageError {
        AnchorCoverageError::new(
            "manifest-unsafe-path",
            "manifest relative_path is not a safe ASCII repo-relative path",
        )
    }
    if path.is_empty() || !path.is_ascii() {
        return Err(unsafe_path());
    }
    if path.starts_with('/')
        || path.contains('\\')
        || path.contains('\0')
        || path.chars().any(|character| character.is_control())
    {
        return Err(unsafe_path());
    }
    for component in path.split('/') {
        if component.is_empty() || component == "." || component == ".." {
            return Err(unsafe_path());
        }
    }
    Ok(())
}

fn validate_sha256(value: &str) -> Result<(), AnchorCoverageError> {
    let Some(rest) = value.strip_prefix("sha256:") else {
        return Err(AnchorCoverageError::new(
            "manifest-parse",
            "record sha256 lacks the sha256: prefix",
        ));
    };
    let lowercase_hex = rest
        .bytes()
        .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte));
    if rest.len() != 64 || !lowercase_hex {
        return Err(AnchorCoverageError::new(
            "manifest-parse",
            "record sha256 is not 64 lowercase hex digits",
        ));
    }
    Ok(())
}

/// Read and parse the S02 corpus manifest from disk.
pub fn read_corpus_manifest(path: &Path) -> Result<CorpusManifest, AnchorCoverageError> {
    let bytes = fs::read(path).map_err(|error| {
        AnchorCoverageError::new("manifest-read", format!("read failed: {}", error.kind()))
    })?;
    let text = String::from_utf8(bytes)
        .map_err(|_| AnchorCoverageError::new("manifest-read", "manifest is not valid UTF-8"))?;
    parse_corpus_manifest(&text)
}

/// Build the corpus coverage by joining every manifest entry against the
/// catalog anchor port, then run the closed-set negative probe.
pub fn build_anchor_coverage(
    manifest_path: &Path,
    catalog_path: &Path,
) -> Result<AnchorCoverage, AnchorCoverageError> {
    let manifest_bytes = fs::read(manifest_path).map_err(|error| {
        AnchorCoverageError::new("manifest-read", format!("read failed: {}", error.kind()))
    })?;
    let manifest_text = std::str::from_utf8(&manifest_bytes)
        .map_err(|_| AnchorCoverageError::new("manifest-read", "manifest is not valid UTF-8"))?;
    let manifest = parse_corpus_manifest(manifest_text)?;
    let manifest_sha256 = format!("sha256:{}", hex(&Sha256::digest(&manifest_bytes)));

    let catalog = SqliteCatalog::open_read_only(catalog_path)
        .map_err(|error| AnchorCoverageError::new("catalog-open", error.detail().to_owned()))?;

    let mut entries = Vec::with_capacity(manifest.entries.len());
    let mut anchored_by_bank: BTreeMap<String, u64> = BTreeMap::new();
    let mut unresolved_by_bank: BTreeMap<String, u64> = BTreeMap::new();

    for entry in &manifest.entries {
        let record = catalog
            .lookup_by_relative_path(&entry.relative_path)
            .map_err(|error| {
                AnchorCoverageError::new("catalog-lookup", error.detail().to_owned())
            })?;
        let anchor = match record {
            Some(record) => {
                let parsed = ConsultantUriAnchor::parse(&record.source_id).map_err(|refusal| {
                    AnchorCoverageError::new(
                        "anchor-parse",
                        format!("catalog source_id refused: {}", refusal.kind().as_str()),
                    )
                })?;
                // Byte-exactness gate: a parse that would normalize the token
                // (e.g. a non-canonical internal anchor) is refused rather than
                // silently accepted.
                if parsed.as_token() != record.source_id {
                    return Err(AnchorCoverageError::new(
                        "anchor-not-byte-exact",
                        "catalog source_id is not byte-exact after parsing",
                    ));
                }
                Some(parsed)
            }
            None => None,
        };
        let bank = bank_of(&entry.relative_path).to_owned();
        if anchor.is_some() {
            *anchored_by_bank.entry(bank).or_insert(0) += 1;
        } else {
            *unresolved_by_bank.entry(bank).or_insert(0) += 1;
        }
        entries.push(AnchorCoverageEntry {
            relative_path: entry.relative_path.clone(),
            sha256: entry.sha256.clone(),
            bytes: entry.bytes,
            anchor,
        });
    }

    let negative_probe = probe_negative_matches(catalog_path)?;
    let catalog_sha256 = hash_file(catalog_path, "catalog-hash")?;

    Ok(AnchorCoverage {
        manifest_path: manifest_path.display().to_string(),
        manifest_sha256,
        inventory_digest: manifest.inventory_digest,
        catalog_path: catalog_path.display().to_string(),
        catalog_sha256,
        entries,
        anchored_by_bank,
        unresolved_by_bank,
        negative_probe,
    })
}

/// The bank of a manifest path: its first `/`-separated component.
fn bank_of(relative_path: &str) -> &str {
    relative_path.split('/').next().unwrap_or(relative_path)
}

/// Closed-set negative probe against `editions.source_id`: exact equality and
/// `LIKE '%<number>%'`. Diagnostics/negative evidence only — never a
/// resolution path. The numbers are bound parameters.
fn probe_negative_matches(catalog_path: &Path) -> Result<NegativeProbe, AnchorCoverageError> {
    let probe_err = |detail: &str| AnchorCoverageError::new("negative-probe", detail);
    let flags = OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_FULL_MUTEX;
    let connection = Connection::open_with_flags(catalog_path, flags)
        .map_err(|_| probe_err("catalog could not be opened read-only for the probe"))?;
    let mut exact_statement = connection
        .prepare("SELECT COUNT(*) FROM editions WHERE source_id = ?1")
        .map_err(|_| probe_err("exact probe statement could not be prepared"))?;
    let mut like_statement = connection
        .prepare("SELECT COUNT(*) FROM editions WHERE source_id LIKE '%' || ?1 || '%'")
        .map_err(|_| probe_err("like probe statement could not be prepared"))?;

    let mut rows = Vec::with_capacity(NEGATIVE_PROBE_NUMBERS.len());
    let mut exact_total: u64 = 0;
    let mut like_total: u64 = 0;
    for number in NEGATIVE_PROBE_NUMBERS {
        let exact: i64 = exact_statement
            .query_row([number], |row| row.get(0))
            .map_err(|_| probe_err("exact probe query failed"))?;
        let like: i64 = like_statement
            .query_row([number], |row| row.get(0))
            .map_err(|_| probe_err("like probe query failed"))?;
        let exact = u64::try_from(exact).map_err(|_| probe_err("negative match count"))?;
        let like = u64::try_from(like).map_err(|_| probe_err("negative match count"))?;
        exact_total += exact;
        like_total += like;
        rows.push(NegativeProbeRow {
            number: number.to_owned(),
            exact_matches: exact,
            like_matches: like,
        });
    }
    Ok(NegativeProbe {
        numbers: NEGATIVE_PROBE_NUMBERS
            .iter()
            .map(|number| (*number).to_owned())
            .collect(),
        exact_matches: exact_total,
        like_matches: like_total,
        per_number: rows,
    })
}

/// Render the coverage JSON (`m224-s02-uri-anchor-coverage/v1`), deterministic
/// and ASCII (non-ASCII payload is escaped as JSON `\uXXXX`).
pub fn render_coverage_json(coverage: &AnchorCoverage) -> Result<String, AnchorCoverageError> {
    let (entries, anchored, unresolved) = coverage.counts();
    let mut out = String::with_capacity(1024);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(COVERAGE_SCHEMA));
    let _ = writeln!(
        out,
        "  \"counts\": {{\"entries\": {entries}, \"anchored\": {anchored}, \"unresolved\": {unresolved}}},"
    );
    let _ = writeln!(
        out,
        "  \"anchored_by_bank\": {},",
        render_bank_map(&coverage.anchored_by_bank)
    );
    let _ = writeln!(
        out,
        "  \"unresolved_by_bank\": {},",
        render_bank_map(&coverage.unresolved_by_bank)
    );
    out.push_str("  \"negative_probe\": {\n");
    let _ = writeln!(
        out,
        "    \"numbers\": {},",
        render_string_array(&coverage.negative_probe.numbers)
    );
    let _ = writeln!(
        out,
        "    \"exact_matches\": {},",
        coverage.negative_probe.exact_matches
    );
    let _ = writeln!(
        out,
        "    \"like_matches\": {},",
        coverage.negative_probe.like_matches
    );
    out.push_str("    \"per_number\": [\n");
    for (index, row) in coverage.negative_probe.per_number.iter().enumerate() {
        let comma = if index + 1 < coverage.negative_probe.per_number.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(
            out,
            "      {{\"number\": {}, \"exact_matches\": {}, \"like_matches\": {}}}{comma}",
            quote_json(&row.number),
            row.exact_matches,
            row.like_matches
        );
    }
    out.push_str("    ]\n  },\n");
    let _ = writeln!(
        out,
        "  \"manifest\": {{\"path\": {}, \"sha256\": {}, \"inventory_digest\": {}}},",
        quote_json(&coverage.manifest_path),
        quote_json(&coverage.manifest_sha256),
        quote_json(&coverage.inventory_digest)
    );
    let _ = writeln!(
        out,
        "  \"catalog\": {{\"path\": {}, \"sha256\": {}}},",
        quote_json(&coverage.catalog_path),
        quote_json(&coverage.catalog_sha256)
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

/// Render the identity envelope JSONL: a header line followed by exactly one
/// [`IdentityEnvelope::render_jsonl_line`] per manifest entry, in manifest
/// order. ASCII by construction, re-asserted fail-closed.
pub fn render_envelope_jsonl(coverage: &AnchorCoverage) -> Result<String, AnchorCoverageError> {
    let (entries, anchored, unresolved) = coverage.counts();
    let mut out = String::with_capacity(coverage.entries.len() * 320 + 512);
    let _ = writeln!(
        out,
        "{{\"schema\":{},\"kind\":\"identity_envelope_header\",\"counts\":{{\"entries\":{entries},\"anchored\":{anchored},\"unresolved\":{unresolved}}},\"manifest\":{{\"path\":{},\"sha256\":{},\"inventory_digest\":{}}},\"catalog\":{{\"path\":{},\"sha256\":{}}},\"r1000_status\":{}}}",
        quote_json(IDENTITY_ENVELOPE_SCHEMA),
        quote_json(&coverage.manifest_path),
        quote_json(&coverage.manifest_sha256),
        quote_json(&coverage.inventory_digest),
        quote_json(&coverage.catalog_path),
        quote_json(&coverage.catalog_sha256),
        quote_json(R1000_STATUS)
    );
    for entry in &coverage.entries {
        let envelope = match &entry.anchor {
            Some(anchor) => IdentityEnvelope::anchored(
                entry.relative_path.clone(),
                entry.sha256.clone(),
                entry.bytes,
                anchor.clone(),
            ),
            None => IdentityEnvelope::unresolved(
                entry.relative_path.clone(),
                entry.sha256.clone(),
                entry.bytes,
            ),
        };
        out.push_str(&envelope.render_jsonl_line());
    }
    ensure_ascii(&out, "envelope")?;
    Ok(out)
}

/// Re-derive both artifacts in memory and byte-compare them against the
/// tracked files without writing (MEM1459 `--check` pattern).
pub fn verify_artifacts(
    coverage: &AnchorCoverage,
    coverage_out: &Path,
    envelope_out: &Path,
) -> Result<(), AnchorCoverageError> {
    let expected_coverage = render_coverage_json(coverage)?;
    let expected_envelope = render_envelope_jsonl(coverage)?;
    compare_artifact(coverage_out, expected_coverage.as_bytes(), "coverage")?;
    compare_artifact(envelope_out, expected_envelope.as_bytes(), "envelope")?;
    Ok(())
}

fn compare_artifact(
    path: &Path,
    expected: &[u8],
    artifact: &'static str,
) -> Result<(), AnchorCoverageError> {
    let actual = fs::read(path).map_err(|error| {
        AnchorCoverageError::new(
            "check-missing",
            format!("{artifact} artifact is unreadable: {}", error.kind()),
        )
    })?;
    if actual == expected {
        Ok(())
    } else {
        Err(AnchorCoverageError::new(
            "check-drift",
            format!("{artifact} artifact differs from the live render"),
        ))
    }
}

/// Parsed `identity-anchor-coverage` argv.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct CoverageCli {
    /// Manifest path (required).
    pub manifest: String,
    /// Catalog path (required).
    pub catalog: String,
    /// Coverage artifact path (required).
    pub coverage_out: String,
    /// Envelope artifact path (required).
    pub envelope_out: String,
    /// `--check`: re-derive and byte-compare instead of writing.
    pub check: bool,
}

/// Strict stdlib argv parser: `--manifest`, `--catalog`, `--coverage-out`,
/// `--envelope-out` each need a following value; `--check` is a flag. All four
/// paths are required.
pub fn parse_coverage_args<I>(args: I) -> Result<CoverageCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = CoverageCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--manifest" => cli.manifest = next_value(&mut iter, "--manifest")?,
            "--catalog" => cli.catalog = next_value(&mut iter, "--catalog")?,
            "--coverage-out" => cli.coverage_out = next_value(&mut iter, "--coverage-out")?,
            "--envelope-out" => cli.envelope_out = next_value(&mut iter, "--envelope-out")?,
            "--check" => cli.check = true,
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    for (flag, value) in [
        ("--manifest", &cli.manifest),
        ("--catalog", &cli.catalog),
        ("--coverage-out", &cli.coverage_out),
        ("--envelope-out", &cli.envelope_out),
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

/// Derive coverage and either publish both artifacts or (in `--check` mode)
/// byte-compare them. Returns the process exit code and a one-line message.
pub fn run_coverage(cli: &CoverageCli) -> (u8, String) {
    match run_coverage_inner(cli) {
        Ok(message) => (EXIT_OK, message),
        Err(error) => (exit_code_for(&error), error.to_string()),
    }
}

fn run_coverage_inner(cli: &CoverageCli) -> Result<String, AnchorCoverageError> {
    let coverage = build_anchor_coverage(Path::new(&cli.manifest), Path::new(&cli.catalog))?;
    let (entries, anchored, unresolved) = coverage.counts();
    if cli.check {
        verify_artifacts(
            &coverage,
            Path::new(&cli.coverage_out),
            Path::new(&cli.envelope_out),
        )?;
        Ok(format!("check=ok entries={entries} anchored={anchored}"))
    } else {
        let coverage_json = render_coverage_json(&coverage)?;
        let envelope_jsonl = render_envelope_jsonl(&coverage)?;
        write_artifact(&cli.coverage_out, &coverage_json, "write-coverage")?;
        write_artifact(&cli.envelope_out, &envelope_jsonl, "write-envelope")?;
        Ok(format!(
            "entries={entries} anchored={anchored} unresolved={unresolved}"
        ))
    }
}

fn write_artifact(
    path: &str,
    bytes: &str,
    operation: &'static str,
) -> Result<(), AnchorCoverageError> {
    fs::write(path, bytes.as_bytes()).map_err(|error| {
        AnchorCoverageError::new(
            operation,
            format!("artifact is not writable: {}", error.kind()),
        )
    })
}

/// Exit code for a derivation/check failure.
pub fn exit_code_for(error: &AnchorCoverageError) -> u8 {
    match error.operation() {
        "check-missing" => EXIT_ARTIFACT_MISSING,
        "check-drift" => EXIT_DRIFT,
        "write-coverage" | "write-envelope" => EXIT_OUT_UNWRITABLE,
        _ => EXIT_DERIVATION_FAILED,
    }
}

/// Redaction guard: an artifact payload must be ASCII, else fail-closed.
fn ensure_ascii(artifact: &str, name: &str) -> Result<(), AnchorCoverageError> {
    if artifact.is_ascii() {
        Ok(())
    } else {
        Err(AnchorCoverageError::new(
            "redaction",
            format!("{name} artifact payload is not ASCII"),
        ))
    }
}

fn render_bank_map(map: &BTreeMap<String, u64>) -> String {
    let mut out = String::from("{");
    let mut first = true;
    for (bank, count) in map {
        if !first {
            out.push_str(", ");
        }
        first = false;
        out.push_str(&quote_json(bank));
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

fn hash_file(path: &Path, operation: &'static str) -> Result<String, AnchorCoverageError> {
    let mut file = fs::File::open(path).map_err(|error| {
        AnchorCoverageError::new(operation, format!("open failed: {}", error.kind()))
    })?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer).map_err(|error| {
            AnchorCoverageError::new(operation, format!("read failed: {}", error.kind()))
        })?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(format!("sha256:{}", hex(&hasher.finalize())))
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
