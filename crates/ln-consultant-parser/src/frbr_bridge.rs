//! Corpus FRBR-bridge join: S02 identity envelope + m223-S07 receipts +
//! catalog `editions` + S06 edition timeline, keyed by `relative_path` and
//! `edition_number` (M224/S07/T02; ADR-0030 D1 byte-exact join; ADR-0015).
//!
//! Three tracked inputs are joined against a read-only catalog edition map for
//! one bounded act (`44-fz`, 118 dated editions):
//!
//! - the **S02 identity envelope** (`m224-s02-identity-envelope/v1`): the
//!   header is skipped explicitly (its `counts.entries`/`counts.anchored` are
//!   used as a cross-check) and every entity line is parsed **only** through
//!   [`IdentityEnvelope::byte_exact_round_trip`] — a non-canonical render is
//!   refused, never normalized (MEM2103);
//! - the **m223-S07 consumer receipts** (`m223-s07-consumer-receipt/v1`):
//!   `counts.identity.{document_version_ref, source_revision, decoder_profile,
//!   source_sha256, parent_schema}`;
//! - the **S06 edition timeline** (`m224-s06-edition-timeline/v1`):
//!   `per_edition[].{edition_number, effect_day}`;
//! - the **catalog edition map** ([`SqliteCatalog::load_edition_join_map`]):
//!   `source_id` (anchor token), `edition_id`, `document_id`,
//!   `edition_number`.
//!
//! Every check is fail-closed ([`FrbrBridgeError`] with a stable operation
//! tag): schema drift on any input, catalog miss, anchor byte-mismatch,
//! receipt sha mismatch, set drift, unknown act, bad ordinal, bad edition
//! number, non-ASCII payload. There is no "empty success" branch. Work
//! identity and ordinal→ISO conversion are delegated to
//! [`ln_kb_ontology::frbr_bridge::resolve_frbr_pair`] (T01), never re-minted
//! here. The registry rev-only expression id
//! ([`ln_kb_ontology::registry::load_expression_id_for_path`]) and the
//! timeline effect-day expression id are compared and their **divergence is
//! counted, not smoothed** (a published non-claim).

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::fmt;
use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use ln_decode::identity_envelope::{
    EnvelopeRefusalKind, IDENTITY_ENVELOPE_SCHEMA, IdentityEnvelope,
};
use ln_kb_ontology::frbr_bridge::{FrbrBridgeRefusal, resolve_frbr_pair};
use ln_kb_ontology::registry::{load_expression_id_for_path, works_entry_for_act};

use crate::catalog_sqlite::EditionJoinRow;

/// Closed JSON schema id of the published corpus mapping artifact (T03).
pub const FRBR_BRIDGE_SCHEMA: &str = "m224-s07-frbr-bridge/v1";
/// Schema id of the S02 identity envelope input.
pub const ENVELOPE_SCHEMA: &str = IDENTITY_ENVELOPE_SCHEMA;
/// `kind` discriminator of the S02 envelope header line (skipped explicitly).
pub const ENVELOPE_HEADER_KIND: &str = "identity_envelope_header";
/// Schema id of the m223-S07 consumer receipt input.
pub const RECEIPTS_SCHEMA: &str = "m223-s07-consumer-receipt/v1";
/// Schema id of the S06 edition timeline input.
pub const TIMELINE_SCHEMA: &str = "m224-s06-edition-timeline/v1";
/// Lifecycle status of R1000 carried by the mapping artifact (never closed).
pub const R1000_STATUS: &str = "active/unclosed";

/// Registry act number of the single bounded corpus act (44-FZ).
pub const DEFAULT_ACT_NUMBER: &str = "44-fz";
/// Manifest path prefix that bounds the edition set to the 44-FZ editions.
pub const DEFAULT_EDITION_PREFIX: &str = "npa/law_2013-04-05_44-fz/edition-";

/// Edition filename segment that carries the ordinal edition number.
const EDITION_SEGMENT_PREFIX: &str = "edition-";

/// Maximum characters retained in a [`FrbrBridgeError`] detail (mirrors the
/// bounded-detail discipline of [`crate::anchor_coverage`]).
const MAX_DETAIL_CHARS: usize = 240;

/// One joined edition row: envelope identity + receipt identity + catalog ids
/// + timeline effect day + resolved Work/Expression URI pair.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrbrBridgeJoinRow {
    /// Manifest relative path (the join key).
    pub relative_path: String,
    /// Ordinal edition number parsed from the `edition-NNNN` filename segment.
    pub edition_number: i64,
    /// Civil-day ordinal of the legal-act effect day (from the S06 timeline).
    pub effect_day: i64,
    /// ISO effect day (`YYYY-MM-DD`) converted only through `ln_temporal`.
    pub effect_iso: String,
    /// Registry Work id (`work:ru:federal:zakon:2013-04-05:44-fz`).
    pub work_id: String,
    /// ELI-compatible Work URN (`urn:lex:ru:federal:zakon:2013-04-05;44-fz`).
    pub work_eli_urn: String,
    /// Expression id minted over the timeline effect day.
    pub expression_id: String,
    /// ELI-compatible Expression URN (`<work_eli_urn>@<effect_iso>`).
    pub expression_eli_urn: String,
    /// Envelope `source.sha256` (`sha256:<hex>`).
    pub source_sha256: String,
    /// Receipt `counts.identity.source_revision` (raw hex).
    pub source_revision: String,
    /// Receipt `counts.identity.document_version_ref`.
    pub document_version_ref: String,
    /// Receipt `counts.identity.decoder_profile`.
    pub decoder_profile: String,
    /// Envelope `consultant_uri`, byte-exact (never decoded/normalized).
    pub uri_anchor: String,
    /// Catalog `edition_id`, if present.
    pub catalog_edition_id: Option<String>,
    /// Catalog `document_id`, if present.
    pub catalog_document_id: Option<String>,
    /// Catalog `edition_number`, if present.
    pub catalog_edition_number: Option<i64>,
    /// Catalog `revision_date`, if present (observability only; not rendered).
    pub catalog_revision_date: Option<String>,
}

/// Join accounting totals. Every value is zero on success because every
/// mismatch is a fail-closed refusal: publishing zeros is the proof there was
/// nothing to reconcile.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct FrbrBridgeTotals {
    /// Catalog edition-number / set inconsistencies observed.
    pub join_mismatches: u64,
    /// Envelope paths absent from the catalog edition map.
    pub catalog_misses: u64,
    /// Envelope anchor vs catalog `source_id` byte mismatches.
    pub anchor_mismatches: u64,
}

/// A complete, reproducible FRBR bridge over one bounded corpus act.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrbrBridgeJoin {
    /// Registry act number (`44-fz`).
    pub act_number: String,
    /// Work authority from the `works:` table (`federal`).
    pub authority: String,
    /// Work enactment date from the `works:` table (`2013-04-05`).
    pub enactment_date: String,
    /// Manifest path prefix that bounded the edition set.
    pub edition_prefix: String,
    /// Registry Work id.
    pub work_id: String,
    /// ELI-compatible Work URN.
    pub work_eli_urn: String,
    /// Joined rows, ordered by the manifest `relative_path` (edition order).
    pub rows: Vec<FrbrBridgeJoinRow>,
    /// Count of distinct Expression effect ISO days across the rows.
    pub distinct_effect_days: u64,
    /// Rows whose registry rev-only expression id differs from the timeline
    /// effect-day expression id (published, never smoothed).
    pub registry_expression_id_divergence: u64,
    /// Join accounting (all zero on success).
    pub totals: FrbrBridgeTotals,
    /// `sha256:<hex>` pin of the envelope input bytes.
    pub envelope_sha256: String,
    /// `sha256:<hex>` pin of the receipts input bytes.
    pub receipts_sha256: String,
    /// `sha256:<hex>` pin of the timeline input bytes.
    pub timeline_sha256: String,
}

/// Typed, bounded FRBR-bridge refusal. Every variant is fail-closed: the caller
/// must not publish a partial mapping. [`Self::operation`] is a stable tag the
/// T03 CLI maps onto its exit codes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrbrBridgeError {
    operation: String,
    detail: String,
}

impl FrbrBridgeError {
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

impl fmt::Display for FrbrBridgeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "frbr bridge {} failed: {}",
            self.operation, self.detail
        )
    }
}

impl Error for FrbrBridgeError {}

/// Header counts of the S02 identity envelope (parsed from the skipped header).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct EnvelopeCounts {
    entries: u64,
    anchored: u64,
}

/// The receipt identity fields the join pins per edition path.
#[derive(Debug, Clone, PartialEq, Eq)]
struct ReceiptIdentity {
    document_version_ref: String,
    source_revision: String,
    decoder_profile: String,
    source_sha256: String,
}

fn err(operation: &'static str, detail: impl Into<String>) -> FrbrBridgeError {
    FrbrBridgeError::new(operation, detail)
}

/// Build the bounded 44-FZ FRBR bridge from file paths and a catalog edition map.
pub fn build_frbr_bridge_join(
    envelope_path: &Path,
    receipts_path: &Path,
    timeline_path: &Path,
    catalog_rows: &BTreeMap<String, EditionJoinRow>,
) -> Result<FrbrBridgeJoin, FrbrBridgeError> {
    let envelope_bytes = read_input(envelope_path, "envelope-read")?;
    let receipts_bytes = read_input(receipts_path, "receipts-read")?;
    let timeline_bytes = read_input(timeline_path, "timeline-read")?;
    build_frbr_bridge_join_from_bytes(
        DEFAULT_ACT_NUMBER,
        DEFAULT_EDITION_PREFIX,
        &envelope_bytes,
        &receipts_bytes,
        &timeline_bytes,
        catalog_rows,
    )
}

/// Byte-level core of [`build_frbr_bridge_join`] (hermetic, fixture-friendly).
///
/// `act_number` and `edition_prefix` are explicit so a caller can drive the
/// unknown-act and set-drift refusals from hermetic fixtures.
pub fn build_frbr_bridge_join_from_bytes(
    act_number: &str,
    edition_prefix: &str,
    envelope_bytes: &[u8],
    receipts_bytes: &[u8],
    timeline_bytes: &[u8],
    catalog_rows: &BTreeMap<String, EditionJoinRow>,
) -> Result<FrbrBridgeJoin, FrbrBridgeError> {
    let envelope_text = decode_ascii(envelope_bytes, "envelope-read")?;
    let receipts_text = decode_ascii(receipts_bytes, "receipts-read")?;
    let timeline_text = decode_ascii(timeline_bytes, "timeline-read")?;

    let envelope_by_path = parse_envelope(envelope_text, edition_prefix)?;
    let receipts_by_path = parse_receipts(receipts_text, edition_prefix)?;
    let timeline_by_number = parse_timeline(timeline_text)?;

    let entry = works_entry_for_act(act_number).ok_or_else(|| {
        err(
            "unknown-act",
            format!("act {act_number} is not in the works: table"),
        )
    })?;

    // set(envelope) == set(receipts)
    let envelope_paths: BTreeSet<&String> = envelope_by_path.keys().collect();
    let receipt_paths: BTreeSet<&String> = receipts_by_path.keys().collect();
    if envelope_paths != receipt_paths {
        return Err(err(
            "set-mismatch",
            "the S02 envelope and m223-S07 receipt edition path sets differ",
        ));
    }

    // set(catalog) covers set(envelope): a missing row is a catalog miss
    // (checked per path so the refusal tag stays precise), an extra bounded
    // prefix row is drift.
    for path in &envelope_paths {
        if !catalog_rows.contains_key(*path) {
            return Err(err(
                "catalog-miss",
                format!("no catalog edition for {path}"),
            ));
        }
    }
    for path in catalog_rows
        .keys()
        .filter(|path| path.starts_with(edition_prefix))
    {
        if !envelope_by_path.contains_key(path) {
            return Err(err(
                "set-mismatch",
                "the catalog carries a bounded edition path absent from the S02 envelope set",
            ));
        }
    }

    // set(timeline numbers) == set(edition numbers)
    let mut envelope_numbers: BTreeSet<i64> = BTreeSet::new();
    for path in &envelope_paths {
        envelope_numbers.insert(parse_edition_number(path)?);
    }
    let timeline_numbers: BTreeSet<i64> = timeline_by_number.keys().copied().collect();
    if envelope_numbers != timeline_numbers {
        return Err(err(
            "set-mismatch",
            "the S06 timeline edition numbers differ from the envelope edition numbers",
        ));
    }

    let mut rows: Vec<FrbrBridgeJoinRow> = Vec::with_capacity(envelope_by_path.len());
    let mut effect_days: BTreeSet<String> = BTreeSet::new();
    let mut divergence: u64 = 0;
    let mut work_id: Option<String> = None;
    let mut work_eli_urn: Option<String> = None;

    for (path, envelope) in &envelope_by_path {
        let number = parse_edition_number(path)?;
        let receipt = receipts_by_path
            .get(path)
            .ok_or_else(|| err("set-mismatch", format!("no receipt for {path}")))?;
        let catalog = catalog_rows
            .get(path)
            .ok_or_else(|| err("catalog-miss", format!("no catalog edition for {path}")))?;
        let effect_day = *timeline_by_number.get(&number).ok_or_else(|| {
            err(
                "set-mismatch",
                format!("no timeline point for edition {number}"),
            )
        })?;

        if let Some(catalog_number) = catalog.edition_number
            && catalog_number != number
        {
            return Err(err(
                "join-mismatch",
                format!(
                    "catalog edition_number {catalog_number} disagrees with the filename number {number}"
                ),
            ));
        }

        let anchor = envelope.anchor.as_ref().ok_or_else(|| {
            err(
                "anchor-mismatch",
                format!("envelope edition {path} carries no consultant_uri"),
            )
        })?;
        if anchor.as_token() != catalog.source_id {
            return Err(err(
                "anchor-mismatch",
                format!("envelope anchor for {path} differs from catalog source_id"),
            ));
        }

        if format!("sha256:{}", receipt.source_sha256) != envelope.source_sha256 {
            return Err(err(
                "receipt-sha-mismatch",
                format!("receipt source_sha256 for {path} differs from the envelope"),
            ));
        }

        let pair = resolve_frbr_pair(act_number, effect_day).map_err(map_refusal)?;
        match &work_id {
            Some(existing) if existing != &pair.work_id => {
                return Err(err(
                    "join-mismatch",
                    format!("row {path} resolved a different Work id"),
                ));
            }
            Some(_) => {}
            None => {
                work_id = Some(pair.work_id.clone());
                work_eli_urn = Some(pair.work_eli_urn.clone());
            }
        }

        let registry_id = load_expression_id_for_path(path);
        if registry_id.as_deref() != Some(pair.expression_id.as_str()) {
            divergence += 1;
        }

        effect_days.insert(pair.effect_iso.clone());
        rows.push(FrbrBridgeJoinRow {
            relative_path: path.clone(),
            edition_number: number,
            effect_day,
            effect_iso: pair.effect_iso,
            work_id: pair.work_id,
            work_eli_urn: pair.work_eli_urn,
            expression_id: pair.expression_id,
            expression_eli_urn: pair.expression_eli_urn,
            source_sha256: envelope.source_sha256.clone(),
            source_revision: receipt.source_revision.clone(),
            document_version_ref: receipt.document_version_ref.clone(),
            decoder_profile: receipt.decoder_profile.clone(),
            uri_anchor: anchor.as_token().to_owned(),
            catalog_edition_id: catalog.edition_id.clone(),
            catalog_document_id: catalog.document_id.clone(),
            catalog_edition_number: catalog.edition_number,
            catalog_revision_date: catalog.revision_date.clone(),
        });
    }

    let work_id = work_id.ok_or_else(|| err("set-mismatch", "the bounded edition set is empty"))?;
    let work_eli_urn = work_eli_urn.ok_or_else(|| err("set-mismatch", "no ELI work URN"))?;

    Ok(FrbrBridgeJoin {
        act_number: act_number.to_owned(),
        authority: entry.authority,
        enactment_date: entry.enactment_date,
        edition_prefix: edition_prefix.to_owned(),
        work_id,
        work_eli_urn,
        rows,
        distinct_effect_days: effect_days.len() as u64,
        registry_expression_id_divergence: divergence,
        totals: FrbrBridgeTotals::default(),
        envelope_sha256: hash_bytes(envelope_bytes),
        receipts_sha256: hash_bytes(receipts_bytes),
        timeline_sha256: hash_bytes(timeline_bytes),
    })
}

fn read_input(path: &Path, operation: &'static str) -> Result<Vec<u8>, FrbrBridgeError> {
    fs::read(path).map_err(|error| err(operation, format!("read failed: {}", error.kind())))
}

fn decode_ascii<'a>(bytes: &'a [u8], operation: &'static str) -> Result<&'a str, FrbrBridgeError> {
    let text =
        std::str::from_utf8(bytes).map_err(|_| err(operation, "input is not valid UTF-8"))?;
    if !text.is_ascii() {
        return Err(err("non-ascii", "input payload is not ASCII"));
    }
    Ok(text)
}

/// Parse the S02 envelope: header explicitly skipped (counts cross-checked),
/// every entity line parsed only through the canonical byte-exact round trip.
fn parse_envelope(
    text: &str,
    edition_prefix: &str,
) -> Result<BTreeMap<String, IdentityEnvelope>, FrbrBridgeError> {
    let mut lines = text.lines();
    let header_line = lines
        .next()
        .ok_or_else(|| err("envelope-schema", "the envelope is empty"))?;
    let counts = parse_envelope_header(header_line)?;

    let mut by_path: BTreeMap<String, IdentityEnvelope> = BTreeMap::new();
    let mut entries: u64 = 0;
    let mut anchored: u64 = 0;
    for line in lines {
        entries += 1;
        let envelope = IdentityEnvelope::byte_exact_round_trip(line).map_err(|refusal| {
            if refusal.kind() == EnvelopeRefusalKind::NonAscii {
                err("non-ascii", "an envelope entity line is not ASCII")
            } else {
                err(
                    "envelope-parse",
                    format!("envelope entity line refused: {}", refusal.kind().as_str()),
                )
            }
        })?;
        if envelope.anchor.is_some() {
            anchored += 1;
        }
        if envelope.relative_path.starts_with(edition_prefix)
            && by_path
                .insert(envelope.relative_path.clone(), envelope)
                .is_some()
        {
            return Err(err(
                "set-mismatch",
                "the envelope carries a duplicate edition path",
            ));
        }
    }

    if entries != counts.entries || anchored != counts.anchored {
        return Err(err(
            "envelope-counts",
            format!(
                "envelope counts disagree: parsed entries={entries} anchored={anchored}, \
                 header entries={} anchored={}",
                counts.entries, counts.anchored
            ),
        ));
    }
    Ok(by_path)
}

fn parse_envelope_header(line: &str) -> Result<EnvelopeCounts, FrbrBridgeError> {
    let header: serde_json::Value = serde_json::from_str(line)
        .map_err(|_| err("envelope-schema", "the envelope header is not JSON"))?;
    if header.get("schema").and_then(serde_json::Value::as_str) != Some(ENVELOPE_SCHEMA) {
        return Err(err(
            "envelope-schema",
            format!("the envelope header schema is not {ENVELOPE_SCHEMA}"),
        ));
    }
    if header.get("kind").and_then(serde_json::Value::as_str) != Some(ENVELOPE_HEADER_KIND) {
        return Err(err(
            "envelope-schema",
            format!("the envelope header kind is not {ENVELOPE_HEADER_KIND}"),
        ));
    }
    let counts = header.get("counts").ok_or_else(|| {
        err(
            "envelope-schema",
            "the envelope header has no counts object",
        )
    })?;
    let entries = counts
        .get("entries")
        .and_then(serde_json::Value::as_u64)
        .ok_or_else(|| {
            err(
                "envelope-schema",
                "the envelope header lacks counts.entries",
            )
        })?;
    let anchored = counts
        .get("anchored")
        .and_then(serde_json::Value::as_u64)
        .ok_or_else(|| {
            err(
                "envelope-schema",
                "the envelope header lacks counts.anchored",
            )
        })?;
    Ok(EnvelopeCounts { entries, anchored })
}

/// Parse the m223-S07 receipts: every line's schema is validated fail-closed;
/// only the bounded edition-prefix lines are retained for the join.
fn parse_receipts(
    text: &str,
    edition_prefix: &str,
) -> Result<BTreeMap<String, ReceiptIdentity>, FrbrBridgeError> {
    let mut by_path: BTreeMap<String, ReceiptIdentity> = BTreeMap::new();
    for (index, line) in text.lines().enumerate() {
        if line.is_empty() {
            continue;
        }
        let value: serde_json::Value = serde_json::from_str(line).map_err(|_| {
            err(
                "receipts-schema",
                format!("receipt line {} is not JSON", index + 1),
            )
        })?;
        if value.get("schema").and_then(serde_json::Value::as_str) != Some(RECEIPTS_SCHEMA) {
            return Err(err(
                "receipts-schema",
                format!("receipt line {} schema is not {RECEIPTS_SCHEMA}", index + 1),
            ));
        }
        let path = value
            .get("relative_path")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| err("receipts-schema", "a receipt lacks relative_path"))?;
        if !path.starts_with(edition_prefix) {
            continue;
        }
        let identity = value
            .get("counts")
            .and_then(|counts| counts.get("identity"))
            .ok_or_else(|| err("receipts-schema", "a receipt lacks counts.identity"))?;
        // Validate the full identity shape fail-closed, including the
        // `parent_schema` token the S02 envelope documents.
        require_str(identity, "parent_schema", "receipts-schema")?;
        let receipt = ReceiptIdentity {
            document_version_ref: require_str(identity, "document_version_ref", "receipts-schema")?
                .to_owned(),
            source_revision: require_str(identity, "source_revision", "receipts-schema")?
                .to_owned(),
            decoder_profile: require_str(identity, "decoder_profile", "receipts-schema")?
                .to_owned(),
            source_sha256: require_str(identity, "source_sha256", "receipts-schema")?.to_owned(),
        };
        if by_path.insert(path.to_owned(), receipt).is_some() {
            return Err(err(
                "set-mismatch",
                "the receipts carry a duplicate bounded edition path",
            ));
        }
    }
    Ok(by_path)
}

/// Parse the S06 edition timeline into `edition_number → effect_day`.
fn parse_timeline(text: &str) -> Result<BTreeMap<i64, i64>, FrbrBridgeError> {
    let value: serde_json::Value = serde_json::from_str(text)
        .map_err(|_| err("timeline-schema", "the timeline is not JSON"))?;
    if value.get("schema").and_then(serde_json::Value::as_str) != Some(TIMELINE_SCHEMA) {
        return Err(err(
            "timeline-schema",
            format!("the timeline schema is not {TIMELINE_SCHEMA}"),
        ));
    }
    let per_edition = value
        .get("per_edition")
        .and_then(serde_json::Value::as_array)
        .ok_or_else(|| err("timeline-schema", "the timeline lacks a per_edition array"))?;
    let mut by_number: BTreeMap<i64, i64> = BTreeMap::new();
    for point in per_edition {
        let number = point
            .get("edition_number")
            .and_then(serde_json::Value::as_i64)
            .ok_or_else(|| err("timeline-schema", "a timeline point lacks edition_number"))?;
        let day = point
            .get("effect_day")
            .and_then(serde_json::Value::as_i64)
            .ok_or_else(|| err("timeline-schema", "a timeline point lacks effect_day"))?;
        if by_number.insert(number, day).is_some() {
            return Err(err(
                "set-mismatch",
                "the timeline carries a duplicate edition_number",
            ));
        }
    }
    Ok(by_number)
}

fn require_str<'a>(
    object: &'a serde_json::Value,
    key: &str,
    operation: &'static str,
) -> Result<&'a str, FrbrBridgeError> {
    object
        .get(key)
        .and_then(serde_json::Value::as_str)
        .ok_or_else(|| err(operation, format!("missing or non-string field {key}")))
}

/// Parse the ordinal edition number from the `edition-NNNN` filename segment.
fn parse_edition_number(path: &str) -> Result<i64, FrbrBridgeError> {
    let file = path.rsplit('/').next().unwrap_or(path);
    let rest = file.strip_prefix(EDITION_SEGMENT_PREFIX).ok_or_else(|| {
        err(
            "bad-edition-number",
            format!("{path} lacks an edition-NNNN segment"),
        )
    })?;
    let digits: String = rest.chars().take_while(char::is_ascii_digit).collect();
    if digits.is_empty() {
        return Err(err(
            "bad-edition-number",
            format!("{path} carries no decimal edition number"),
        ));
    }
    digits.parse::<i64>().map_err(|_| {
        err(
            "bad-edition-number",
            format!("{path} edition number overflows i64"),
        )
    })
}

fn map_refusal(refusal: FrbrBridgeRefusal) -> FrbrBridgeError {
    let operation = match refusal {
        FrbrBridgeRefusal::UnknownAct => "unknown-act",
        FrbrBridgeRefusal::InvalidOrdinal => "bad-ordinal",
        FrbrBridgeRefusal::InvalidEffectDay => "bad-effect-day",
        FrbrBridgeRefusal::CalendarUnavailable => "calendar-unavailable",
        FrbrBridgeRefusal::WorkMintFailed => "work-mint-failed",
        FrbrBridgeRefusal::ExpressionMintFailed => "expression-mint-failed",
    };
    err(operation, refusal.as_str())
}

fn hash_bytes(bytes: &[u8]) -> String {
    format!("sha256:{}", hex(&Sha256::digest(bytes)))
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
    for ch in raw.chars() {
        if ch.is_control() {
            continue;
        }
        if out.chars().count() >= MAX_DETAIL_CHARS {
            break;
        }
        out.push(ch);
    }
    out
}
