//! Corpus pageindex producer: join the S02 identity envelope's offline tokens
//! against the catalog to build a corpus pageindex addressed by
//! `(bank, document_key)` and publish two derived, non-authoritative artifacts
//! (M224/S03/T03, ADR-0030 D1/D5/D6, R1000 supporting-only).
//!
//! Inputs are the tracked S02 identity envelope
//! (`m224-s02-identity-envelope/v1`: header + one
//! `relative_path → {source, consultant_uri | anchor_status}` line per manifest
//! entry) and the sha256-pinned observed catalog (`consru_export/…/catalog.sqlite`,
//! opened read-only through [`PageIndexCatalogPort`]).
//!
//! The join is an **exact-token** match: the offline token travels byte-exact
//! into `PageIndexCatalogPort::lookup_by_offline_token` and is never decoded,
//! normalized or re-derived. For each anchored envelope line:
//!
//! - a token with no catalog rows is the closed, counted `key_unresolved`
//!   class (per-bank counter; the bank label is the first path segment as a
//!   **coverage label**, explicitly not an identity);
//! - a token with catalog rows yields one [`PageIndexEntry`] per distinct
//!   `(bank, document_key)`;
//! - a token mapping to more than one key increments `token_multi_keyed` and
//!   keeps all rows;
//! - a key claimed by more than one distinct `relative_path` is a
//!   `key_collision`: the key is excluded from the index (fail-visible, never
//!   a silent winner).
//!
//! The surviving entries are validated through
//! [`ln_decode::corpus_pageindex::CorpusPageIndex::build`] — the same
//! fail-closed key-space gate used by the resolver (path-like keys refused).
//!
//! Two artifacts are rendered, both byte-ASCII (non-ASCII payload escaped as
//! JSON `\uXXXX`) and re-asserted fail-closed:
//!
//! 1. the coverage JSON (`m224-s03-pageindex/v1`, kind `pageindex_coverage`):
//!    the closed `whole_document_para` constant, the counts, the per-bank
//!    tallies, the closed-set negative probe, the envelope/catalog/manifest
//!    pins, and the non-claims;
//! 2. the index JSONL (`m224-s03-pageindex-entries/v1`): a header line plus one
//!    `{bank, document_key, relative_path, offline_token}` line per index entry,
//!    sorted by `(bank, document_key, relative_path)`.
//!
//! The negative probe matches the closed set of extracted document numbers
//! against the index keys and the anchored tokens **without decoding** — it is
//! diagnostic/negative evidence, never a resolution path. Resolution by file
//! path does not exist here: `relative_path` is document identity only.
//!
//! `--check` re-derives both artifacts in memory and byte-compares them against
//! the tracked files without writing (MEM1459 pattern).

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;
use std::fmt::Write as _;
use std::fs;
use std::io::Read as _;
use std::path::Path;

use sha2::{Digest, Sha256};

use ln_decode::corpus_pageindex::{CorpusPageIndex, PageIndexEntry, WHOLE_DOCUMENT_PARA};
use ln_decode::identity_envelope::{IDENTITY_ENVELOPE_SCHEMA, IdentityEnvelope};

use crate::catalog_sqlite::SqliteCatalog;
use crate::page_index_catalog::{
    CatalogPageIndexRecord, InMemoryPageIndexCatalog, PageIndexCatalogPort,
};

/// Closed JSON schema id of the coverage artifact.
pub const PAGEINDEX_SCHEMA: &str = "m224-s03-pageindex/v1";
/// Closed JSONL schema id of the index artifact.
pub const PAGEINDEX_ENTRIES_SCHEMA: &str = "m224-s03-pageindex-entries/v1";
/// Lifecycle status of R1000 carried by both artifacts (D667: integrity is not
/// semantic completeness; S03 never closes R1000).
pub const PAGEINDEX_R1000_STATUS: &str = "active/unclosed";
/// Closed set of extracted document numbers used by the negative probe. The
/// probe is diagnostic evidence only; it is not a resolution path.
pub const PAGEINDEX_NEGATIVE_PROBE_NUMBERS: [&str; 3] = ["44-ФЗ", "402-ФЗ", "5-фкз"];

/// Bounded non-claims carried by the coverage artifact.
pub const PAGEINDEX_NON_CLAIMS: [&str; 6] = [
    "integrity_is_not_semantic_completeness",
    "consultant_uri_tokens_are_opaque_external_references_not_credentials",
    "no_offline_token_is_decoded_normalized_or_re_derived",
    "internal_uri_bank_is_not_a_catalog_bank_without_a_tracked_mapping",
    "paragraph_extent_resolution_is_S05",
    "no_file_path_is_a_resolution_key",
];

/// Exit code: both artifacts derive and (in write mode) are published.
pub const EXIT_OK: u8 = 0;
/// Exit code: malformed argv.
pub const EXIT_USAGE: u8 = 2;
/// Exit code: envelope/catalog derivation failed (fail-closed, nothing written).
pub const EXIT_DERIVATION_FAILED: u8 = 3;
/// Exit code: an artifact could not be written.
pub const EXIT_OUT_UNWRITABLE: u8 = 4;
/// Exit code: `--check` could not read a tracked artifact.
pub const EXIT_ARTIFACT_MISSING: u8 = 5;
/// Exit code: `--check` byte-compare drifted.
pub const EXIT_DRIFT: u8 = 6;

/// Maximum characters retained in a [`PageIndexBuildError`] detail (mirrors the
/// bounded-detail discipline of [`crate::catalog::CatalogError`]).
const MAX_DETAIL_CHARS: usize = 240;

/// Parsed S02 identity envelope header.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnvelopeHeader {
    /// Envelope schema id.
    pub schema: String,
    /// Envelope header kind (`identity_envelope_header`).
    pub kind: String,
    /// Header `counts.entries`.
    pub entries: u64,
    /// Header `counts.anchored`.
    pub anchored: u64,
    /// Header `counts.unresolved`.
    pub unresolved: u64,
    /// Header `manifest.path`.
    pub manifest_path: String,
    /// Header `manifest.sha256`.
    pub manifest_sha256: String,
    /// Header `manifest.inventory_digest`.
    pub inventory_digest: String,
    /// Header `catalog.path`.
    pub catalog_path: String,
    /// Header `catalog.sha256`.
    pub catalog_sha256: String,
    /// Header `r1000_status`.
    pub r1000_status: String,
}

/// Coverage counters of the corpus pageindex build.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PageIndexCounts {
    /// Envelope entries (header `counts.entries`).
    pub entries: u64,
    /// Anchored envelope lines (header `counts.anchored`).
    pub anchored: u64,
    /// Unresolved envelope lines (header `counts.unresolved`).
    pub unresolved: u64,
    /// Anchored lines that entered the token index (`== anchored`).
    pub token_index: u64,
    /// Distinct `relative_path` represented in the final index.
    pub keyed: u64,
    /// Anchored documents absent from the final index (`== anchored - keyed`).
    pub key_unresolved: u64,
    /// Keys claimed by more than one distinct `relative_path` (excluded).
    pub key_collision: u64,
    /// Tokens mapping to more than one `(bank, document_key)`.
    pub token_multi_keyed: u64,
}

/// One row of the closed-set negative probe.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NegativeProbeRow {
    /// The extracted document number probed.
    pub number: String,
    /// `count` of index entries whose `bank` or `document_key` equals the
    /// number (expected 0).
    pub key_matches: u64,
    /// `count` of anchored tokens equal to the number (expected 0).
    pub token_matches: u64,
}

/// Closed-set negative probe: extracted document numbers never match an index
/// key or an anchored token (the number is encrypted inside the offline token;
/// MEM1781). Diagnostics/negative evidence only.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NegativeProbe {
    /// The probed numbers, in closed-set order.
    pub numbers: Vec<String>,
    /// Summed key matches across [`Self::numbers`].
    pub key_matches: u64,
    /// Summed token matches across [`Self::numbers`].
    pub token_matches: u64,
    /// Per-number detail, in closed-set order.
    pub per_number: Vec<NegativeProbeRow>,
}

/// Pins carried by the coverage artifact (envelope/catalog are the CLI paths
/// and computed hashes; manifest is the envelope header pin).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuildMeta {
    /// Envelope path as given on the command line.
    pub envelope_path: String,
    /// `sha256:<hex>` of the envelope file bytes.
    pub envelope_sha256: String,
    /// Catalog path as given on the command line.
    pub catalog_path: String,
    /// `sha256:<hex>` of the catalog file bytes.
    pub catalog_sha256: String,
}

/// Complete corpus pageindex coverage state.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CorpusPageIndexCoverage {
    /// Envelope path as given on the command line.
    pub envelope_path: String,
    /// `sha256:<hex>` of the envelope file bytes.
    pub envelope_sha256: String,
    /// Catalog path as given on the command line.
    pub catalog_path: String,
    /// `sha256:<hex>` of the catalog file bytes.
    pub catalog_sha256: String,
    /// Manifest path carried by the envelope header.
    pub manifest_path: String,
    /// Manifest sha256 carried by the envelope header.
    pub manifest_sha256: String,
    /// Manifest inventory digest carried by the envelope header.
    pub inventory_digest: String,
    /// Coverage counters.
    pub counts: PageIndexCounts,
    /// Indexed documents per catalog bank (coverage label attribution).
    pub keyed_by_bank: BTreeMap<String, u64>,
    /// Unresolved documents per path-segment bank label (coverage label, not
    /// identity).
    pub key_unresolved_by_bank: BTreeMap<String, u64>,
    /// The final index entries, sorted by `(bank, document_key, relative_path)`.
    pub entries: Vec<PageIndexEntry>,
    /// The validated index built from [`Self::entries`].
    pub index: CorpusPageIndex,
    /// The closed-set negative probe result.
    pub negative_probe: NegativeProbe,
}

/// Typed, bounded pageindex derivation failure. Every variant is fail-closed:
/// the caller must not publish a partial artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PageIndexBuildError {
    operation: &'static str,
    detail: String,
}

impl PageIndexBuildError {
    /// Build an error, bounding the detail to [`MAX_DETAIL_CHARS`] characters
    /// and dropping control characters.
    pub fn new(operation: &'static str, detail: impl Into<String>) -> Self {
        Self {
            operation,
            detail: bound_detail(detail.into()),
        }
    }

    /// The operation that failed.
    pub fn operation(&self) -> &'static str {
        self.operation
    }

    /// The bounded human-readable detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for PageIndexBuildError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "corpus pageindex {} failed: {}",
            self.operation, self.detail
        )
    }
}

impl Error for PageIndexBuildError {}

/// Parse the S02 identity envelope header fail-closed.
///
/// Refused: a missing/foreign schema, an unexpected kind, a header without
/// `counts.{entries,anchored,unresolved}`, a missing/blank
/// `manifest.{path,sha256,inventory_digest}` or `catalog.{path,sha256}`, or a
/// header without `r1000_status`.
pub fn parse_envelope_header(text: &str) -> Result<EnvelopeHeader, PageIndexBuildError> {
    fn parse_err(detail: &str) -> PageIndexBuildError {
        PageIndexBuildError::new("envelope-header", detail)
    }
    fn required_string<'a>(
        value: &'a serde_json::Value,
        field: &str,
    ) -> Result<&'a str, PageIndexBuildError> {
        value
            .get(field)
            .and_then(serde_json::Value::as_str)
            .filter(|text| !text.is_empty())
            .ok_or_else(|| PageIndexBuildError::new("envelope-header", format!("{field} missing")))
    }

    let first = text
        .lines()
        .next()
        .ok_or_else(|| parse_err("envelope is empty"))?;
    let header: serde_json::Value =
        serde_json::from_str(first).map_err(|_| parse_err("header is not JSON"))?;
    let schema = required_string(&header, "schema")?.to_owned();
    if schema != IDENTITY_ENVELOPE_SCHEMA {
        return Err(parse_err("unexpected envelope schema"));
    }
    let kind = required_string(&header, "kind")?.to_owned();
    if kind != "identity_envelope_header" {
        return Err(parse_err("unexpected header kind"));
    }
    let counts = header
        .get("counts")
        .ok_or_else(|| parse_err("header has no counts"))?;
    let entries = counts
        .get("entries")
        .and_then(serde_json::Value::as_u64)
        .ok_or_else(|| parse_err("counts.entries missing"))?;
    let anchored = counts
        .get("anchored")
        .and_then(serde_json::Value::as_u64)
        .ok_or_else(|| parse_err("counts.anchored missing"))?;
    let unresolved = counts
        .get("unresolved")
        .and_then(serde_json::Value::as_u64)
        .ok_or_else(|| parse_err("counts.unresolved missing"))?;

    let manifest = header
        .get("manifest")
        .ok_or_else(|| parse_err("header has no manifest"))?;
    let manifest_path = required_string(manifest, "path")?.to_owned();
    let manifest_sha256 = required_string(manifest, "sha256")?.to_owned();
    let inventory_digest = required_string(manifest, "inventory_digest")?.to_owned();

    let catalog = header
        .get("catalog")
        .ok_or_else(|| parse_err("header has no catalog"))?;
    let catalog_path = required_string(catalog, "path")?.to_owned();
    let catalog_sha256 = required_string(catalog, "sha256")?.to_owned();

    let r1000_status = required_string(&header, "r1000_status")?.to_owned();

    Ok(EnvelopeHeader {
        schema,
        kind,
        entries,
        anchored,
        unresolved,
        manifest_path,
        manifest_sha256,
        inventory_digest,
        catalog_path,
        catalog_sha256,
        r1000_status,
    })
}

/// Build coverage from envelope text, pins, and a pageindex catalog port.
///
/// Fail-closed on: a header/catalog-pin mismatch, a malformed or non-canonical
/// envelope line, a body count that disagrees with the header, a duplicate
/// `relative_path`, a catalog lookup failure, or an index entry the resolver
/// key-space refuses (e.g. a path-like catalog bank).
pub fn build_coverage(
    envelope_text: &str,
    meta: &BuildMeta,
    catalog: &dyn PageIndexCatalogPort,
) -> Result<CorpusPageIndexCoverage, PageIndexBuildError> {
    let header = parse_envelope_header(envelope_text)?;
    if header.catalog_sha256 != meta.catalog_sha256 {
        return Err(PageIndexBuildError::new(
            "catalog-sha-mismatch",
            "envelope header catalog pin differs from the computed catalog sha256",
        ));
    }

    let mut envelopes: Vec<IdentityEnvelope> = Vec::new();
    let mut seen_paths: BTreeSet<String> = BTreeSet::new();
    for (index, line) in envelope_text.lines().enumerate() {
        if index == 0 {
            continue; // header
        }
        if line.trim().is_empty() {
            return Err(PageIndexBuildError::new(
                "envelope-record",
                "blank envelope record line",
            ));
        }
        let envelope = IdentityEnvelope::read_back(line).map_err(|refusal| {
            PageIndexBuildError::new(
                "envelope-record",
                format!("envelope line refused: {}", refusal.kind().as_str()),
            )
        })?;
        if !seen_paths.insert(envelope.relative_path.clone()) {
            return Err(PageIndexBuildError::new(
                "envelope-duplicate-path",
                format!(
                    "duplicate relative_path in envelope: {}",
                    envelope.relative_path
                ),
            ));
        }
        envelopes.push(envelope);
    }

    let entries_count = envelopes.len() as u64;
    let anchored_count = envelopes
        .iter()
        .filter(|envelope| envelope.anchor.is_some())
        .count() as u64;
    let unresolved_count = entries_count - anchored_count;
    if entries_count != header.entries
        || anchored_count != header.anchored
        || unresolved_count != header.unresolved
    {
        return Err(PageIndexBuildError::new(
            "envelope-count-mismatch",
            format!(
                "header counts ({}/{}/{}) disagree with body ({entries_count}/{anchored_count}/{unresolved_count})",
                header.entries, header.anchored, header.unresolved
            ),
        ));
    }

    // Exact-token join. The lookup cache is keyed by the byte-exact token; it
    // never decodes or normalizes. The 118-fold duplicate token in the corpus
    // is looked up once.
    let mut cache: BTreeMap<String, Vec<CatalogPageIndexRecord>> = BTreeMap::new();
    let mut candidates: Vec<PageIndexEntry> = Vec::new();
    let mut anchored_tokens: Vec<String> = Vec::new();
    let mut anchored_paths: Vec<String> = Vec::new();
    let mut token_multi_keyed: u64 = 0;
    for envelope in &envelopes {
        let Some(anchor) = &envelope.anchor else {
            continue;
        };
        let token = anchor.as_token().to_owned();
        anchored_tokens.push(token.clone());
        anchored_paths.push(envelope.relative_path.clone());
        let records = if let Some(cached) = cache.get(&token) {
            cached.clone()
        } else {
            let looked_up = catalog.lookup_by_offline_token(&token).map_err(|error| {
                PageIndexBuildError::new("catalog-lookup", error.detail().to_owned())
            })?;
            cache.insert(token.clone(), looked_up.clone());
            looked_up
        };
        if records.is_empty() {
            continue;
        }
        if records.len() > 1 {
            token_multi_keyed += 1;
        }
        for record in records {
            candidates.push(PageIndexEntry {
                bank: record.bank,
                document_key: record.document_key,
                relative_path: envelope.relative_path.clone(),
                offline_token: Some(token.clone()),
            });
        }
    }

    // Key collisions: a key claimed by >1 distinct `relative_path` is excluded
    // (fail-visible, never a silent winner).
    let mut claims: BTreeMap<(String, String), BTreeSet<String>> = BTreeMap::new();
    for entry in &candidates {
        claims
            .entry((entry.bank.clone(), entry.document_key.clone()))
            .or_default()
            .insert(entry.relative_path.clone());
    }
    let mut collided: BTreeSet<(String, String)> = BTreeSet::new();
    for (key, paths) in &claims {
        if paths.len() > 1 {
            collided.insert(key.clone());
        }
    }
    let key_collision = collided.len() as u64;

    let mut entries: Vec<PageIndexEntry> = candidates
        .into_iter()
        .filter(|entry| !collided.contains(&(entry.bank.clone(), entry.document_key.clone())))
        .collect();
    entries.sort_by(|left, right| {
        (&left.bank, &left.document_key, &left.relative_path).cmp(&(
            &right.bank,
            &right.document_key,
            &right.relative_path,
        ))
    });

    let keyed_paths: BTreeSet<String> = entries
        .iter()
        .map(|entry| entry.relative_path.clone())
        .collect();
    let keyed = keyed_paths.len() as u64;
    let key_unresolved = anchored_count - keyed;

    let mut keyed_by_bank: BTreeMap<String, u64> = BTreeMap::new();
    let mut attributed: BTreeSet<String> = BTreeSet::new();
    for entry in &entries {
        if attributed.insert(entry.relative_path.clone()) {
            *keyed_by_bank.entry(entry.bank.clone()).or_insert(0) += 1;
        }
    }
    let mut key_unresolved_by_bank: BTreeMap<String, u64> = BTreeMap::new();
    for path in &anchored_paths {
        if !keyed_paths.contains(path) {
            let bank = bank_of(path).to_owned();
            *key_unresolved_by_bank.entry(bank).or_insert(0) += 1;
        }
    }

    let index = CorpusPageIndex::build(&entries)
        .map_err(|refusal| PageIndexBuildError::new("index-build", refusal.to_string()))?;

    let negative_probe = build_negative_probe(&entries, &anchored_tokens);

    Ok(CorpusPageIndexCoverage {
        envelope_path: meta.envelope_path.clone(),
        envelope_sha256: meta.envelope_sha256.clone(),
        catalog_path: meta.catalog_path.clone(),
        catalog_sha256: meta.catalog_sha256.clone(),
        manifest_path: header.manifest_path,
        manifest_sha256: header.manifest_sha256,
        inventory_digest: header.inventory_digest,
        counts: PageIndexCounts {
            entries: header.entries,
            anchored: header.anchored,
            unresolved: header.unresolved,
            token_index: header.anchored,
            keyed,
            key_unresolved,
            key_collision,
            token_multi_keyed,
        },
        keyed_by_bank,
        key_unresolved_by_bank,
        entries,
        index,
        negative_probe,
    })
}

/// Read the envelope and catalog from disk and build coverage.
pub fn build_corpus_pageindex(
    envelope_path: &Path,
    catalog_path: &Path,
) -> Result<CorpusPageIndexCoverage, PageIndexBuildError> {
    let envelope_bytes = fs::read(envelope_path).map_err(|error| {
        PageIndexBuildError::new("envelope-read", format!("read failed: {}", error.kind()))
    })?;
    let envelope_text = std::str::from_utf8(&envelope_bytes)
        .map_err(|_| PageIndexBuildError::new("envelope-read", "envelope is not valid UTF-8"))?;
    let envelope_sha256 = format!("sha256:{}", hex(&Sha256::digest(&envelope_bytes)));

    let catalog = SqliteCatalog::open_read_only(catalog_path)
        .map_err(|error| PageIndexBuildError::new("catalog-open", error.detail().to_owned()))?;
    let catalog_sha256 = hash_file(catalog_path, "catalog-hash")?;

    // Producer optimization: `court_items.offline_uri` is unindexed, so a
    // per-token lookup would full-scan a ~46 MB table for every one of ~37k
    // tokens. Load the exact-token join once, then serve every lookup through
    // the same [`PageIndexCatalogPort`] interface (in-memory adapter) so the
    // resolution semantics are byte-identical to the SQLite adapter.
    let token_map = catalog
        .load_page_index_token_map()
        .map_err(|error| PageIndexBuildError::new("catalog-preload", error.detail().to_owned()))?;
    let mut preloaded = InMemoryPageIndexCatalog::new();
    for (token, records) in &token_map {
        for record in records {
            preloaded.insert(token, &record.bank, &record.document_key);
        }
    }

    let meta = BuildMeta {
        envelope_path: envelope_path.display().to_string(),
        envelope_sha256,
        catalog_path: catalog_path.display().to_string(),
        catalog_sha256,
    };
    build_coverage(envelope_text, &meta, &preloaded)
}

/// The bank label of a `relative_path`: its first `/`-separated component. A
/// coverage label only — the explicit non-claim is that an internal URI bank is
/// not a catalog bank without a tracked mapping.
fn bank_of(relative_path: &str) -> &str {
    relative_path.split('/').next().unwrap_or(relative_path)
}

/// Closed-set negative probe over the index keys and the anchored tokens
/// (exact equality, no decoding). Diagnostics/negative evidence only.
fn build_negative_probe(entries: &[PageIndexEntry], anchored_tokens: &[String]) -> NegativeProbe {
    let mut rows = Vec::with_capacity(PAGEINDEX_NEGATIVE_PROBE_NUMBERS.len());
    let mut key_total: u64 = 0;
    let mut token_total: u64 = 0;
    for number in PAGEINDEX_NEGATIVE_PROBE_NUMBERS {
        let key_matches = entries
            .iter()
            .filter(|entry| entry.bank == number || entry.document_key == number)
            .count() as u64;
        let token_matches = anchored_tokens
            .iter()
            .filter(|token| token.as_str() == number)
            .count() as u64;
        key_total += key_matches;
        token_total += token_matches;
        rows.push(NegativeProbeRow {
            number: number.to_owned(),
            key_matches,
            token_matches,
        });
    }
    NegativeProbe {
        numbers: PAGEINDEX_NEGATIVE_PROBE_NUMBERS
            .iter()
            .map(|number| (*number).to_owned())
            .collect(),
        key_matches: key_total,
        token_matches: token_total,
        per_number: rows,
    }
}

/// Render the coverage JSON (`m224-s03-pageindex/v1`), deterministic and ASCII
/// (non-ASCII payload is escaped as JSON `\uXXXX`).
pub fn render_pageindex_coverage_json(
    coverage: &CorpusPageIndexCoverage,
) -> Result<String, PageIndexBuildError> {
    let counts = &coverage.counts;
    let mut out = String::with_capacity(2048);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(PAGEINDEX_SCHEMA));
    let _ = writeln!(out, "  \"kind\": {},", quote_json("pageindex_coverage"));
    let _ = writeln!(out, "  \"whole_document_para\": {WHOLE_DOCUMENT_PARA},");
    let _ = writeln!(out, "  \"counts\": {},", render_counts(counts));
    let _ = writeln!(
        out,
        "  \"keyed_by_bank\": {},",
        render_bank_map(&coverage.keyed_by_bank)
    );
    let _ = writeln!(
        out,
        "  \"key_unresolved_by_bank\": {},",
        render_bank_map(&coverage.key_unresolved_by_bank)
    );
    out.push_str("  \"negative_probe\": {\n");
    let _ = writeln!(
        out,
        "    \"numbers\": {},",
        render_string_array(&coverage.negative_probe.numbers)
    );
    let _ = writeln!(
        out,
        "    \"key_matches\": {},",
        coverage.negative_probe.key_matches
    );
    let _ = writeln!(
        out,
        "    \"token_matches\": {},",
        coverage.negative_probe.token_matches
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
            "      {{\"number\": {}, \"key_matches\": {}, \"token_matches\": {}}}{comma}",
            quote_json(&row.number),
            row.key_matches,
            row.token_matches
        );
    }
    out.push_str("    ]\n  },\n");
    let _ = writeln!(out, "  \"meta\": {},", render_meta_pretty(coverage));
    let _ = writeln!(
        out,
        "  \"r1000_status\": {},",
        quote_json(PAGEINDEX_R1000_STATUS)
    );
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in PAGEINDEX_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 < PAGEINDEX_NON_CLAIMS.len() {
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

/// Render the index JSONL (`m224-s03-pageindex-entries/v1`): a header line
/// followed by one entry line per key, sorted by
/// `(bank, document_key, relative_path)`. ASCII by construction, re-asserted
/// fail-closed.
pub fn render_pageindex_jsonl(
    coverage: &CorpusPageIndexCoverage,
) -> Result<String, PageIndexBuildError> {
    let mut out = String::with_capacity(coverage.entries.len() * 256 + 512);
    let _ = writeln!(
        out,
        "{{\"schema\":{},\"kind\":{},\"whole_document_para\":{WHOLE_DOCUMENT_PARA},\"counts\":{},\"meta\":{},\"r1000_status\":{}}}",
        quote_json(PAGEINDEX_ENTRIES_SCHEMA),
        quote_json("pageindex_header"),
        render_counts(&coverage.counts),
        render_meta_compact(coverage),
        quote_json(PAGEINDEX_R1000_STATUS)
    );
    for entry in &coverage.entries {
        let token = match &entry.offline_token {
            Some(token) => quote_json(token),
            None => "null".to_owned(),
        };
        let _ = writeln!(
            out,
            "{{\"bank\":{},\"document_key\":{},\"relative_path\":{},\"offline_token\":{}}}",
            quote_json(&entry.bank),
            quote_json(&entry.document_key),
            quote_json(&entry.relative_path),
            token
        );
    }
    ensure_ascii(&out, "index")?;
    Ok(out)
}

/// Re-derive both artifacts in memory and byte-compare them against the
/// tracked files without writing (MEM1459 `--check` pattern).
pub fn verify_pageindex_artifacts(
    coverage: &CorpusPageIndexCoverage,
    coverage_out: &Path,
    index_out: &Path,
) -> Result<(), PageIndexBuildError> {
    let expected_coverage = render_pageindex_coverage_json(coverage)?;
    let expected_index = render_pageindex_jsonl(coverage)?;
    compare_artifact(coverage_out, expected_coverage.as_bytes(), "coverage")?;
    compare_artifact(index_out, expected_index.as_bytes(), "index")?;
    Ok(())
}

fn compare_artifact(
    path: &Path,
    expected: &[u8],
    artifact: &'static str,
) -> Result<(), PageIndexBuildError> {
    let actual = fs::read(path).map_err(|error| {
        PageIndexBuildError::new(
            "check-missing",
            format!("{artifact} artifact is unreadable: {}", error.kind()),
        )
    })?;
    if actual == expected {
        Ok(())
    } else {
        Err(PageIndexBuildError::new(
            "check-drift",
            format!("{artifact} artifact differs from the live render"),
        ))
    }
}

/// Parsed `corpus-pageindex` argv.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct PageIndexCli {
    /// Envelope path (required).
    pub envelope: String,
    /// Catalog path (required).
    pub catalog: String,
    /// Coverage artifact path (required).
    pub coverage_out: String,
    /// Index artifact path (required).
    pub index_out: String,
    /// `--check`: re-derive and byte-compare instead of writing.
    pub check: bool,
}

/// Strict stdlib argv parser: `--envelope`, `--catalog`, `--coverage-out`,
/// `--index-out` each need a following value; `--check` is a flag. All four
/// paths are required.
pub fn parse_pageindex_args<I>(args: I) -> Result<PageIndexCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = PageIndexCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--envelope" => cli.envelope = next_value(&mut iter, "--envelope")?,
            "--catalog" => cli.catalog = next_value(&mut iter, "--catalog")?,
            "--coverage-out" => cli.coverage_out = next_value(&mut iter, "--coverage-out")?,
            "--index-out" => cli.index_out = next_value(&mut iter, "--index-out")?,
            "--check" => cli.check = true,
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    for (flag, value) in [
        ("--envelope", &cli.envelope),
        ("--catalog", &cli.catalog),
        ("--coverage-out", &cli.coverage_out),
        ("--index-out", &cli.index_out),
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
pub fn run_pageindex(cli: &PageIndexCli) -> (u8, String) {
    match run_pageindex_inner(cli) {
        Ok(message) => (EXIT_OK, message),
        Err(error) => (pageindex_exit_code_for(&error), error.to_string()),
    }
}

fn run_pageindex_inner(cli: &PageIndexCli) -> Result<String, PageIndexBuildError> {
    let coverage = build_corpus_pageindex(Path::new(&cli.envelope), Path::new(&cli.catalog))?;
    let counts = coverage.counts;
    if cli.check {
        verify_pageindex_artifacts(
            &coverage,
            Path::new(&cli.coverage_out),
            Path::new(&cli.index_out),
        )?;
        Ok(format!(
            "check=ok entries={} anchored={} keyed={}",
            counts.entries, counts.anchored, counts.keyed
        ))
    } else {
        let coverage_json = render_pageindex_coverage_json(&coverage)?;
        let index_jsonl = render_pageindex_jsonl(&coverage)?;
        write_artifact(&cli.coverage_out, &coverage_json, "write-coverage")?;
        write_artifact(&cli.index_out, &index_jsonl, "write-index")?;
        Ok(format!(
            "entries={} anchored={} keyed={} key_unresolved={}",
            counts.entries, counts.anchored, counts.keyed, counts.key_unresolved
        ))
    }
}

fn write_artifact(
    path: &str,
    bytes: &str,
    operation: &'static str,
) -> Result<(), PageIndexBuildError> {
    fs::write(path, bytes.as_bytes()).map_err(|error| {
        PageIndexBuildError::new(
            operation,
            format!("artifact is not writable: {}", error.kind()),
        )
    })
}

/// Exit code for a derivation/check failure.
pub fn pageindex_exit_code_for(error: &PageIndexBuildError) -> u8 {
    match error.operation() {
        "check-missing" => EXIT_ARTIFACT_MISSING,
        "check-drift" => EXIT_DRIFT,
        "write-coverage" | "write-index" => EXIT_OUT_UNWRITABLE,
        _ => EXIT_DERIVATION_FAILED,
    }
}

/// Redaction guard: an artifact payload must be ASCII, else fail-closed.
fn ensure_ascii(artifact: &str, name: &str) -> Result<(), PageIndexBuildError> {
    if artifact.is_ascii() {
        Ok(())
    } else {
        Err(PageIndexBuildError::new(
            "redaction",
            format!("{name} artifact payload is not ASCII"),
        ))
    }
}

fn render_counts(counts: &PageIndexCounts) -> String {
    format!(
        "{{\"entries\": {}, \"anchored\": {}, \"unresolved\": {}, \"token_index\": {}, \"keyed\": {}, \"key_unresolved\": {}, \"key_collision\": {}, \"token_multi_keyed\": {}}}",
        counts.entries,
        counts.anchored,
        counts.unresolved,
        counts.token_index,
        counts.keyed,
        counts.key_unresolved,
        counts.key_collision,
        counts.token_multi_keyed
    )
}

fn render_meta_compact(coverage: &CorpusPageIndexCoverage) -> String {
    format!(
        "{{\"envelope\":{{\"path\":{},\"sha256\":{}}},\"catalog\":{{\"path\":{},\"sha256\":{}}},\"manifest\":{{\"path\":{},\"sha256\":{},\"inventory_digest\":{}}}}}",
        quote_json(&coverage.envelope_path),
        quote_json(&coverage.envelope_sha256),
        quote_json(&coverage.catalog_path),
        quote_json(&coverage.catalog_sha256),
        quote_json(&coverage.manifest_path),
        quote_json(&coverage.manifest_sha256),
        quote_json(&coverage.inventory_digest)
    )
}

fn render_meta_pretty(coverage: &CorpusPageIndexCoverage) -> String {
    format!(
        "{{\n    \"envelope\": {{\"path\": {}, \"sha256\": {}}},\n    \"catalog\": {{\"path\": {}, \"sha256\": {}}},\n    \"manifest\": {{\"path\": {}, \"sha256\": {}, \"inventory_digest\": {}}}\n  }}",
        quote_json(&coverage.envelope_path),
        quote_json(&coverage.envelope_sha256),
        quote_json(&coverage.catalog_path),
        quote_json(&coverage.catalog_sha256),
        quote_json(&coverage.manifest_path),
        quote_json(&coverage.manifest_sha256),
        quote_json(&coverage.inventory_digest)
    )
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

fn hash_file(path: &Path, operation: &'static str) -> Result<String, PageIndexBuildError> {
    let mut file = fs::File::open(path).map_err(|error| {
        PageIndexBuildError::new(operation, format!("open failed: {}", error.kind()))
    })?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer).map_err(|error| {
            PageIndexBuildError::new(operation, format!("read failed: {}", error.kind()))
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
