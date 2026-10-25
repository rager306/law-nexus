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
use std::fmt::Write as _;
use std::fs;
use std::io::Read as _;
use std::path::Path;

use sha2::{Digest, Sha256};

use ln_decode::identity_envelope::{
    EnvelopeRefusalKind, IDENTITY_ENVELOPE_SCHEMA, IdentityEnvelope,
};
use ln_kb_ontology::frbr_bridge::{FrbrBridgeRefusal, resolve_frbr_pair};
use ln_kb_ontology::registry::{load_expression_id_for_path, works_entry_for_act};

use crate::catalog_sqlite::{EditionJoinRow, SqliteCatalog};

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

// ---------------------------------------------------------------------------
// Published mapping artifact (M224/S07/T03): closed non-claims, sha256 pins,
// deterministic ASCII render, fail-closed CLI exit codes (0/2/3/4/5/6).
// ---------------------------------------------------------------------------

/// Closed `version` of the published mapping artifact.
pub const FRBR_BRIDGE_VERSION: u64 = 1;
/// `kind` discriminator of the published corpus mapping artifact.
pub const FRBR_BRIDGE_KIND: &str = "frbr_bridge_corpus";

/// Bounded non-claims carried by the mapping artifact: ELI is a compatibility
/// projection only, the `cc:` component-concept canon is untouched, and R1000 /
/// R035 stay open.
pub const FRBR_BRIDGE_NON_CLAIMS: [&str; 11] = [
    "eli_urn_is_a_compatibility_projection_not_project_local_canon",
    "cc_component_concept_canon_is_not_replaced_or_rekeyed",
    "one_work_per_act_dated_editions_are_expressions",
    "uri_anchor_is_never_decoded_normalized_or_re_derived",
    "counts_and_keys_only_no_decoded_text",
    "expression_day_is_the_timeline_effect_day_not_the_registry_rev_date",
    "not_r1000_closure",
    "bounded_single_corpus_act_44fz_not_tsg_s6_not_applicable",
    "not_a_jsonld_g1_layer_projection_only",
    "practice_banks_single_version_out_of_scope",
    "not_r035_promotion_bounded_mapping_evidence_only",
];

/// Default tracked S02 identity envelope input (repo-relative).
pub const DEFAULT_ENVELOPE_PATH: &str =
    "prd/migration/rust-evidence/m224-s02-identity-envelope.jsonl";
/// Default tracked m223-S07 consumer receipts input (repo-relative).
pub const DEFAULT_RECEIPTS_PATH: &str =
    "prd/migration/rust-evidence/m223-s07-corpus-receipts.jsonl";
/// Default tracked S06 edition timeline input (repo-relative).
pub const DEFAULT_TIMELINE_PATH: &str =
    "prd/migration/rust-evidence/m224-s06-edition-timeline.json";
/// Default read-only catalog path (repo-relative, gitignored corpus file).
pub const DEFAULT_CATALOG_PATH: &str = "consru_export/consru_export/catalog.sqlite";
/// Default published mapping artifact path (repo-relative, tracked).
pub const DEFAULT_OUT_PATH: &str = "prd/migration/rust-evidence/m224-s07-frbr-bridge.json";
/// Default pinned ontology source (repo-relative, tracked).
pub const DEFAULT_ONTOLOGY_PATH: &str = "prd/architecture/kb-ontology.yaml";
/// Default pinned hierarchy/works registry source (repo-relative, tracked).
pub const DEFAULT_REGISTRY_PATH: &str = "prd/architecture/kb-hierarchy-registry.yaml";
/// Default consumer binary path (repo-relative, build artifact).
pub const DEFAULT_BINARY_PATH: &str = "target/release/frbr-bridge";

/// Exit code: the artifact derives and is published (or `--check` agrees).
pub const EXIT_OK: u8 = 0;
/// Exit code: malformed argv.
pub const EXIT_USAGE: u8 = 2;
/// Exit code: a required input/artifact could not be read (fail-closed).
pub const EXIT_INPUT: u8 = 3;
/// Exit code: the artifact could not be written.
pub const EXIT_OUT_UNWRITABLE: u8 = 4;
/// Exit code: the FRBR join refused (schema drift, set drift, catalog miss,
/// anchor mismatch, unknown act, bad ordinal, non-ASCII payload).
pub const EXIT_JOIN_REFUSED: u8 = 5;
/// Exit code: `--check` byte-compare drifted.
pub const EXIT_DRIFT: u8 = 6;

/// Parsed `frbr-bridge` argv. Every path defaults to the tracked/build
/// location so the bare binary reproduces the published artifact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BridgeCli {
    /// S02 identity envelope JSONL input.
    pub envelope: String,
    /// m223-S07 consumer receipts JSONL input.
    pub receipts: String,
    /// Read-only catalog (`editions`) input.
    pub catalog: String,
    /// S06 edition timeline JSON input.
    pub timeline: String,
    /// Published mapping artifact path.
    pub out: String,
    /// Pinned ontology source (kb-ontology.yaml).
    pub ontology: String,
    /// Pinned registry source (kb-hierarchy-registry.yaml).
    pub registry: String,
    /// Consumer binary whose bytes are pinned.
    pub binary: String,
    /// `--check`: re-derive and byte-compare instead of writing.
    pub check: bool,
}

impl Default for BridgeCli {
    fn default() -> Self {
        Self {
            envelope: DEFAULT_ENVELOPE_PATH.to_owned(),
            receipts: DEFAULT_RECEIPTS_PATH.to_owned(),
            catalog: DEFAULT_CATALOG_PATH.to_owned(),
            timeline: DEFAULT_TIMELINE_PATH.to_owned(),
            out: DEFAULT_OUT_PATH.to_owned(),
            ontology: DEFAULT_ONTOLOGY_PATH.to_owned(),
            registry: DEFAULT_REGISTRY_PATH.to_owned(),
            binary: DEFAULT_BINARY_PATH.to_owned(),
            check: false,
        }
    }
}

/// Strict stdlib argv parser: `--check` is a flag, every other option needs a
/// following non-empty value. An unknown flag, a missing value or an empty
/// value is an exit-2 usage error (never silently defaulted).
pub fn parse_bridge_args<I>(args: I) -> Result<BridgeCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = BridgeCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--envelope" => cli.envelope = bridge_value(&mut iter, "--envelope")?,
            "--receipts" => cli.receipts = bridge_value(&mut iter, "--receipts")?,
            "--catalog" => cli.catalog = bridge_value(&mut iter, "--catalog")?,
            "--timeline" => cli.timeline = bridge_value(&mut iter, "--timeline")?,
            "--out" => cli.out = bridge_value(&mut iter, "--out")?,
            "--ontology" => cli.ontology = bridge_value(&mut iter, "--ontology")?,
            "--registry" => cli.registry = bridge_value(&mut iter, "--registry")?,
            "--binary" => cli.binary = bridge_value(&mut iter, "--binary")?,
            "--check" => cli.check = true,
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    Ok(cli)
}

fn bridge_value(iter: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    let value = iter
        .next()
        .ok_or_else(|| format!("missing value for {flag}"))?;
    if value.is_empty() {
        return Err(format!("empty value for {flag}"));
    }
    Ok(value)
}

/// SHA-256 pins (path + `sha256:<hex>`) of every input the artifact derives
/// from: the three tracked join inputs, the two pinned model sources, the
/// read-only catalog and the consumer binary.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrbrBridgePins {
    pub envelope_path: String,
    pub envelope_sha256: String,
    pub receipts_path: String,
    pub receipts_sha256: String,
    pub timeline_path: String,
    pub timeline_sha256: String,
    pub ontology_path: String,
    pub ontology_sha256: String,
    pub registry_path: String,
    pub registry_sha256: String,
    pub catalog_path: String,
    pub catalog_sha256: String,
    pub consumer_binary_path: String,
    pub consumer_binary_sha256: String,
}

/// Render the mapping artifact (`m224-s07-frbr-bridge/v1`), deterministic and
/// ASCII (non-ASCII payload is escaped as JSON `\uXXXX`, then re-asserted by
/// the redaction guard).
pub fn render_frbr_bridge_json(
    join: &FrbrBridgeJoin,
    pins: &FrbrBridgePins,
) -> Result<String, FrbrBridgeError> {
    let joined = join.rows.len();
    let mut out = String::with_capacity(4096 + joined * 800);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(FRBR_BRIDGE_SCHEMA));
    let _ = writeln!(out, "  \"version\": {},", FRBR_BRIDGE_VERSION);
    let _ = writeln!(out, "  \"kind\": {},", quote_json(FRBR_BRIDGE_KIND));
    let _ = writeln!(
        out,
        "  \"act\": {{\"number\": {}, \"authority\": {}, \"enactment_date\": {}}},",
        quote_json(&join.act_number),
        quote_json(&join.authority),
        quote_json(&join.enactment_date)
    );
    let _ = writeln!(
        out,
        "  \"work\": {{\"id\": {}, \"eli_urn\": {}}},",
        quote_json(&join.work_id),
        quote_json(&join.work_eli_urn)
    );
    let _ = writeln!(
        out,
        "  \"edition_prefix\": {},",
        quote_json(&join.edition_prefix)
    );
    let _ = writeln!(out, "  \"works\": 1,");
    let _ = writeln!(out, "  \"expressions\": {joined},");
    let _ = writeln!(
        out,
        "  \"distinct_effect_days\": {},",
        join.distinct_effect_days
    );
    let _ = writeln!(
        out,
        "  \"distinct_anchors\": {},",
        distinct_anchor_count(join)
    );
    let _ = writeln!(
        out,
        "  \"join_coverage\": {},",
        quote_json(&format!("{joined}/{joined}"))
    );
    let _ = writeln!(
        out,
        "  \"registry_expression_id_divergence\": {},",
        join.registry_expression_id_divergence
    );
    out.push_str("  \"pins\": {\n");
    let _ = writeln!(
        out,
        "    \"envelope\": {},",
        render_pin_json(&pins.envelope_path, &pins.envelope_sha256)
    );
    let _ = writeln!(
        out,
        "    \"receipts\": {},",
        render_pin_json(&pins.receipts_path, &pins.receipts_sha256)
    );
    let _ = writeln!(
        out,
        "    \"timeline\": {},",
        render_pin_json(&pins.timeline_path, &pins.timeline_sha256)
    );
    let _ = writeln!(
        out,
        "    \"ontology\": {},",
        render_pin_json(&pins.ontology_path, &pins.ontology_sha256)
    );
    let _ = writeln!(
        out,
        "    \"registry\": {},",
        render_pin_json(&pins.registry_path, &pins.registry_sha256)
    );
    let _ = writeln!(
        out,
        "    \"catalog\": {},",
        render_pin_json(&pins.catalog_path, &pins.catalog_sha256)
    );
    let _ = writeln!(
        out,
        "    \"consumer_binary\": {}",
        render_pin_json(&pins.consumer_binary_path, &pins.consumer_binary_sha256)
    );
    out.push_str("  },\n");
    let _ = writeln!(
        out,
        "  \"totals\": {{\"join_mismatches\": {}, \"catalog_misses\": {}, \"anchor_mismatches\": {}}},",
        join.totals.join_mismatches, join.totals.catalog_misses, join.totals.anchor_mismatches
    );
    let _ = writeln!(out, "  \"r1000_status\": {},", quote_json(R1000_STATUS));
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in FRBR_BRIDGE_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 < FRBR_BRIDGE_NON_CLAIMS.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(out, "    {}{comma}", quote_json(claim));
    }
    out.push_str("  ],\n");
    out.push_str("  \"per_expression\": [");
    if join.rows.is_empty() {
        out.push_str("]\n}\n");
    } else {
        out.push('\n');
        for (index, row) in join.rows.iter().enumerate() {
            let comma = if index + 1 < join.rows.len() { "," } else { "" };
            let _ = writeln!(
                out,
                "    {{\"relative_path\": {}, \"edition_number\": {}, \"effect_day\": {}, \"effect_iso\": {}, \"expression_id\": {}, \"expression_eli_urn\": {}, \"source_sha256\": {}, \"source_revision\": {}, \"document_version_ref\": {}, \"decoder_profile\": {}, \"uri_anchor\": {}, \"catalog\": {{\"edition_id\": {}, \"document_id\": {}, \"edition_number\": {}}}}}{comma}",
                quote_json(&row.relative_path),
                row.edition_number,
                row.effect_day,
                quote_json(&row.effect_iso),
                quote_json(&row.expression_id),
                quote_json(&row.expression_eli_urn),
                quote_json(&row.source_sha256),
                quote_json(&row.source_revision),
                quote_json(&row.document_version_ref),
                quote_json(&row.decoder_profile),
                quote_json(&row.uri_anchor),
                render_optional_str(row.catalog_edition_id.as_deref()),
                render_optional_str(row.catalog_document_id.as_deref()),
                render_optional_i64(row.catalog_edition_number)
            );
        }
        out.push_str("  ]\n}\n");
    }
    ensure_ascii(&out)?;
    Ok(out)
}

fn distinct_anchor_count(join: &FrbrBridgeJoin) -> u64 {
    join.rows
        .iter()
        .map(|row| row.uri_anchor.as_str())
        .collect::<BTreeSet<&str>>()
        .len() as u64
}

fn render_pin_json(path: &str, sha256: &str) -> String {
    format!(
        "{{\"path\": {}, \"sha256\": {}}}",
        quote_json(path),
        quote_json(sha256)
    )
}

fn render_optional_str(value: Option<&str>) -> String {
    match value {
        Some(value) => quote_json(value),
        None => "null".to_owned(),
    }
}

fn render_optional_i64(value: Option<i64>) -> String {
    match value {
        Some(value) => value.to_string(),
        None => "null".to_owned(),
    }
}

/// Re-derive the artifact and either publish it or (in `--check` mode)
/// byte-compare it against `--out`. Returns the process exit code and a
/// one-line message.
pub fn run_bridge(cli: &BridgeCli) -> (u8, String) {
    match run_bridge_inner(cli) {
        Ok(message) => (EXIT_OK, message),
        Err(error) => (exit_code_for(&error), error.to_string()),
    }
}

fn run_bridge_inner(cli: &BridgeCli) -> Result<String, FrbrBridgeError> {
    let catalog = SqliteCatalog::open_read_only(&cli.catalog)
        .map_err(|error| FrbrBridgeError::new("catalog-open", error.detail().to_owned()))?;
    let map = catalog
        .load_edition_join_map()
        .map_err(|error| FrbrBridgeError::new("catalog-read", error.detail().to_owned()))?;
    let join = build_frbr_bridge_join(
        Path::new(&cli.envelope),
        Path::new(&cli.receipts),
        Path::new(&cli.timeline),
        &map,
    )?;

    let pins = FrbrBridgePins {
        envelope_path: cli.envelope.clone(),
        envelope_sha256: join.envelope_sha256.clone(),
        receipts_path: cli.receipts.clone(),
        receipts_sha256: join.receipts_sha256.clone(),
        timeline_path: cli.timeline.clone(),
        timeline_sha256: join.timeline_sha256.clone(),
        ontology_path: cli.ontology.clone(),
        ontology_sha256: hash_file(Path::new(&cli.ontology), "pin-read")?,
        registry_path: cli.registry.clone(),
        registry_sha256: hash_file(Path::new(&cli.registry), "pin-read")?,
        catalog_path: cli.catalog.clone(),
        catalog_sha256: hash_file(Path::new(&cli.catalog), "pin-read")?,
        consumer_binary_path: cli.binary.clone(),
        consumer_binary_sha256: hash_file(Path::new(&cli.binary), "pin-read")?,
    };
    let rendered = render_frbr_bridge_json(&join, &pins)?;

    let expressions = join.rows.len();
    let distinct_effect_days = join.distinct_effect_days;
    let divergence = join.registry_expression_id_divergence;
    if cli.check {
        let actual = fs::read(&cli.out).map_err(|error| {
            FrbrBridgeError::new(
                "check-missing",
                format!("--out artifact is unreadable: {}", error.kind()),
            )
        })?;
        if actual == rendered.as_bytes() {
            Ok(format!(
                "check=ok expressions={expressions} distinct_effect_days={distinct_effect_days} divergence={divergence}"
            ))
        } else {
            Err(FrbrBridgeError::new(
                "check-drift",
                "the --out artifact differs from the live render",
            ))
        }
    } else {
        fs::write(&cli.out, rendered.as_bytes()).map_err(|error| {
            FrbrBridgeError::new(
                "write-artifact",
                format!("--out is not writable: {}", error.kind()),
            )
        })?;
        Ok(format!(
            "wrote expressions={expressions} distinct_effect_days={distinct_effect_days} divergence={divergence} out={}",
            cli.out
        ))
    }
}

/// Exit code for a derivation/check failure. Read failures (a missing input or
/// an unreadable `--check` artifact) are the input class, the join refusals are
/// the bounded contract class, and a write/drift is its own class.
pub fn exit_code_for(error: &FrbrBridgeError) -> u8 {
    match error.operation() {
        "envelope-read" | "receipts-read" | "timeline-read" | "catalog-open" | "catalog-read"
        | "pin-read" | "check-missing" => EXIT_INPUT,
        "write-artifact" => EXIT_OUT_UNWRITABLE,
        "check-drift" => EXIT_DRIFT,
        _ => EXIT_JOIN_REFUSED,
    }
}

fn hash_file(path: &Path, operation: &'static str) -> Result<String, FrbrBridgeError> {
    let mut file = fs::File::open(path)
        .map_err(|error| err(operation, format!("open failed: {}", error.kind())))?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0_u8; 64 * 1024];
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|error| err(operation, format!("read failed: {}", error.kind())))?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(format!("sha256:{}", hex(&hasher.finalize())))
}

/// Redaction guard: an artifact payload must be ASCII, else fail-closed.
fn ensure_ascii(artifact: &str) -> Result<(), FrbrBridgeError> {
    if artifact.is_ascii() {
        Ok(())
    } else {
        Err(err("redaction", "mapping artifact payload is not ASCII"))
    }
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
