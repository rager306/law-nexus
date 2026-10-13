//! Corpus assembly consumer over the materialized cleaned-wire JSONL layer
//! (M224/S06/T01).
//!
//! This is the corpus-facing *assembly* half of S06: it reads **only** the
//! materialized cleaned-wire JSONL artifact (schema
//! `law-nexus/cleaned-projection/v1`) produced by the `cleaned-project export`
//! producer, reconstructs the decoded block stream through
//! [`ln_decode::wire_blocks::blocks_from_cleaned_projection`], extracts the
//! hierarchy markers with the single authoritative extractor
//! ([`ln_decode::hierarchy::extract_hierarchy`]) and drives the assembly FSM
//! over the registry snapshot:
//!
//! ```text
//! markers -> propose_membership_from_markers -> admit_membership_proposals
//!         -> commit -> fold -> assemble_with_oracle_diff
//! ```
//!
//! It carries **no** `--from-xml` option and never opens the source XML/ODT
//! artifact: the producer touches the source bytes exactly once, the consumer
//! reads the JSONL layer. The original source identity is *read*, not
//! re-derived, from the projection's [`ln_decode::cleaned_wire::SourcePin`].
//!
//! Output is one counts-only ASCII JSON (`edition-assembly/v1`): marker,
//! proposal, admission, root/node and oracle-drift counts, an
//! `expression_id_present` flag and the declared non-claims. No decoded text
//! is emitted; nothing here is a legal hierarchy claim.
//!
//! Boundary (S06/T01): single-edition `assembly` mode only. The `chain` and
//! `timeline` modes and the `--ctv` layer are declared in the CLI grammar but
//! fail closed here (T02-T04 fill them in). The crate never re-parses XML —
//! `ln-decode` reconstructs the block stream; `ln-kb-ontology` owns the
//! registry, membership and oracle-diff vocabulary.

use std::error::Error;
use std::fmt;
use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use ln_decode::cleaned_wire::read_cleaned_wire;
use ln_decode::domain::SourceFormatId;
use ln_decode::hierarchy::extract_hierarchy;
use ln_decode::wire_blocks::blocks_from_cleaned_projection;

use ln_kb_ontology::domain::{
    HierarchyMap, HierarchyMarker, admit_membership_proposals, assemble_with_oracle_diff,
    marker_from_decode_token, propose_membership_from_markers,
};
use ln_kb_ontology::registry::{
    embedded_binding_count_for_path, load_edition_day_for_path, load_expression_id_for_path,
    load_hierarchy_map_for_path,
};

/// Closed JSON schema id of the single-edition assembly payload.
pub const ASSEMBLY_SCHEMA: &str = "edition-assembly/v1";
/// Closed `kind` discriminator of the single-edition assembly payload.
pub const ASSEMBLY_KIND: &str = "edition_assembly";
/// Lifecycle status of R1000 carried by the payload (D667: integrity is not
/// semantic completeness; S06 never closes R1000).
pub const R1000_STATUS: &str = "active/unclosed";
/// Provenance used when the corpus path mints no Expression ID (mirrors the
/// `law-nexus-inspect` C2-oracle fallback). The payload records the absence
/// via `expression_id_present=false`.
pub const SYNTHETIC_PROVENANCE: &str = "amendingact:c2-oracle-edition";

/// Exit code: the assembly payload derived successfully.
pub const EXIT_OK: u8 = 0;
/// Exit code: malformed argv / TSV usage.
pub const EXIT_USAGE: u8 = 2;
/// Exit code: a cleaned-wire JSONL input is unreadable.
pub const EXIT_INPUT_UNREADABLE: u8 = 3;
/// Exit code: the output artifact is not writable.
pub const EXIT_OUT_UNWRITABLE: u8 = 4;
/// Exit code: the cleaned-wire layer (or a downstream assembly invariant) was
/// refused fail-closed and nothing was published.
pub const EXIT_WIRE_REFUSED: u8 = 5;

/// Bounded non-claims carried by the payload: what this consumer is **not**.
pub const ASSEMBLY_NON_CLAIMS: [&str; 6] = [
    "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml_or_odt",
    "assembly_is_a_structural_projection_not_legal_hierarchy_authority",
    "provenance_falls_back_to_a_synthetic_c2_oracle_when_no_expression_mints",
    "effect_day_prefers_from_date_else_rev_date_process_truth_not_legal_truth",
    "integrity_is_not_semantic_completeness",
    "mints_no_component_concept_beyond_the_embedded_registry",
];

/// Maximum characters retained in a bounded error detail (mirrors the S05
/// census consumer).
const MAX_DETAIL_CHARS: usize = 240;

/// Declared assembly mode. Only [`AssemblyMode::Assembly`] is implemented in
/// this task; `chain`/`timeline` are accepted by the grammar and fail closed.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum AssemblyMode {
    /// Single-edition snapshot assembly (T01).
    #[default]
    Assembly,
    /// Two-edition structural replay (T02).
    Chain,
    /// Full edition timeline over N editions (T03).
    Timeline,
}

impl AssemblyMode {
    /// Stable CLI token carried in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            AssemblyMode::Assembly => "assembly",
            AssemblyMode::Chain => "chain",
            AssemblyMode::Timeline => "timeline",
        }
    }

    fn from_token(token: &str) -> Option<Self> {
        match token {
            "assembly" => Some(AssemblyMode::Assembly),
            "chain" => Some(AssemblyMode::Chain),
            "timeline" => Some(AssemblyMode::Timeline),
            _ => None,
        }
    }
}

/// Parsed `edition-timeline` argv.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditionTimelineCli {
    /// TSV file listing `edition_number<TAB>corpus_path<TAB>cleaned_wire` rows.
    pub editions: String,
    /// Assembly mode (defaults to `assembly`).
    pub mode: AssemblyMode,
    /// Request the CTV/text layer (T04; not implemented here).
    pub ctv: bool,
    /// Payload path (optional; JSON goes to stdout when absent).
    pub out: Option<String>,
}

/// One parsed TSV edition row.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionRow {
    /// Edition sequence number (`edition-0118` -> 118).
    pub edition_number: u32,
    /// Corpus-relative document path (used for registry/day/identity grounding).
    pub corpus_path: String,
    /// Materialized cleaned-wire JSONL path.
    pub cleaned_wire: String,
}

/// Counts-only result of one assembly FSM pass. Carries no decoded text.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditionAssemblyCounts {
    /// Decoded hierarchy markers extracted from the wire layer.
    pub markers: u64,
    /// Structural attach drafts proposed from document order.
    pub proposals: u64,
    /// Drafts that survived the structural conflict gate.
    pub admitted: u64,
    /// Forest roots of the folded membership AST.
    pub roots: u64,
    /// Total nodes of the folded membership AST.
    pub nodes: u64,
    /// Attach events committed for the admitted edges.
    pub committed: u64,
    /// Oracle drift (`missing + phantom`).
    pub drift: u64,
    /// Expected CCs missing from the folded AST.
    pub missing: u64,
    /// Folded CCs absent from the oracle snapshot.
    pub phantom: u64,
}

/// Counts-only single-edition assembly payload. Carries no decoded text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionAssembly {
    /// Edition sequence number from the TSV row.
    pub edition_number: u32,
    /// Corpus-relative path as given in the TSV row.
    pub corpus_path: String,
    /// Effect-day ordinal used for commit and fold.
    pub effect_day: i64,
    /// True when the corpus path minted a real per-edition Expression ID.
    pub expression_id_present: bool,
    /// Registry bindings matched for the corpus path.
    pub registry_bindings: u64,
    /// Assembly FSM counts.
    pub counts: EditionAssemblyCounts,
    /// Lowercase-hex sha256 of the frozen source (from the projection).
    pub wire_source_sha256: String,
    /// Byte length of the frozen source (from the projection).
    pub wire_source_bytes: u64,
    /// `sha256:<hex>` of the consumed cleaned-wire JSONL bytes.
    pub cleaned_wire_sha256: String,
}

/// Extracted markers plus the wire-layer identity pins.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WireMarkers {
    /// Decoded hierarchy markers, in document order.
    pub markers: Vec<HierarchyMarker>,
    /// Lowercase-hex sha256 of the frozen source (from the projection).
    pub wire_source_sha256: String,
    /// Byte length of the frozen source (from the projection).
    pub wire_source_bytes: u64,
    /// `sha256:<hex>` of the consumed cleaned-wire JSONL bytes.
    pub cleaned_wire_sha256: String,
}

/// Typed, bounded assembly derivation failure. Every variant is fail-closed:
/// the caller must not publish a partial payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionTimelineError {
    operation: String,
    detail: String,
}

impl EditionTimelineError {
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
            "usage" => EXIT_USAGE,
            "input-read" => EXIT_INPUT_UNREADABLE,
            "out-write" => EXIT_OUT_UNWRITABLE,
            _ => EXIT_WIRE_REFUSED,
        }
    }
}

impl fmt::Display for EditionTimelineError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "edition timeline {} failed: {}",
            self.operation, self.detail
        )
    }
}

impl Error for EditionTimelineError {}

/// Strict stdlib argv parser: `--editions`, `--mode`, `--out` each need a
/// following value; `--ctv` is a flag. `--from-xml` is deliberately not
/// accepted.
pub fn parse_edition_timeline_args<I>(args: I) -> Result<EditionTimelineCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = EditionTimelineCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--editions" => cli.editions = next_value(&mut iter, "--editions")?,
            "--mode" => {
                let token = next_value(&mut iter, "--mode")?;
                cli.mode = AssemblyMode::from_token(&token).ok_or_else(|| {
                    format!("unsupported --mode '{token}' (expected assembly|chain|timeline)")
                })?;
            }
            "--ctv" => cli.ctv = true,
            "--out" => cli.out = Some(next_value(&mut iter, "--out")?),
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    if cli.editions.is_empty() {
        return Err("missing required --editions".to_owned());
    }
    Ok(cli)
}

fn next_value(iter: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    iter.next()
        .ok_or_else(|| format!("missing value for {flag}"))
}

/// Parse the `--editions` TSV text into rows.
///
/// Each non-blank, non-comment line is `edition_number<TAB>corpus_path<TAB>
/// cleaned_wire`. A malformed line is a usage error, never a silent skip.
pub fn parse_edition_rows(text: &str) -> Result<Vec<EditionRow>, EditionTimelineError> {
    let mut rows = Vec::new();
    for (index, raw) in text.lines().enumerate() {
        let line = raw.trim_end_matches('\r');
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        let mut fields = line.split('\t');
        let (Some(number), Some(corpus_path), Some(cleaned_wire), None) =
            (fields.next(), fields.next(), fields.next(), fields.next())
        else {
            return Err(EditionTimelineError::new(
                "usage",
                format!("line {}: expected 3 tab-separated fields", index + 1),
            ));
        };
        let edition_number = number.trim().parse::<u32>().map_err(|_| {
            EditionTimelineError::new(
                "usage",
                format!("line {}: edition_number is not a u32", index + 1),
            )
        })?;
        if corpus_path.is_empty() || cleaned_wire.is_empty() {
            return Err(EditionTimelineError::new(
                "usage",
                format!("line {}: empty corpus or cleaned-wire path", index + 1),
            ));
        }
        rows.push(EditionRow {
            edition_number,
            corpus_path: corpus_path.to_owned(),
            cleaned_wire: cleaned_wire.to_owned(),
        });
    }
    Ok(rows)
}

/// Extract decoded markers from a materialized cleaned-wire JSONL artifact.
///
/// Fail-closed: a refused wire layer or a failed block bridge aborts with no
/// markers. Only the JSONL layer is read — the source artifact is never opened.
pub fn markers_from_cleaned_wire(bytes: &[u8]) -> Result<WireMarkers, EditionTimelineError> {
    let text = std::str::from_utf8(bytes)
        .map_err(|_| EditionTimelineError::new("input-read", "cleaned wire is not valid UTF-8"))?;
    let cleaned_wire_sha256 = format!("sha256:{}", hex(&Sha256::digest(bytes)));

    let projection = read_cleaned_wire(text).map_err(|error| {
        EditionTimelineError::new(
            "wire-refused",
            format!("cleaned wire refused: {}", error.kind().as_str()),
        )
    })?;
    let wire_source_sha256 = projection.source.sha256.clone();
    let wire_source_bytes = projection.source.bytes;

    let blocks = blocks_from_cleaned_projection(&projection, SourceFormatId::ConsultantWordMl)
        .map_err(|error| {
            EditionTimelineError::new(
                "wire-refused",
                format!("block bridge refused: {}", error.as_str()),
            )
        })?;

    let mut markers = Vec::new();
    for block in &blocks {
        if let Some(node) = extract_hierarchy(block)
            && let Ok(marker) =
                marker_from_decode_token(None, node.level().as_str(), node.number(), node.title())
        {
            markers.push(marker);
        }
    }

    Ok(WireMarkers {
        markers,
        wire_source_sha256,
        wire_source_bytes,
        cleaned_wire_sha256,
    })
}

/// Drive the assembly FSM for one edition snapshot: propose -> admit ->
/// commit/fold -> oracle diff. Pure over the supplied registry map.
pub fn assemble_edition(
    markers: &[HierarchyMarker],
    map: &HierarchyMap,
    effect_day: i64,
    provenance: &str,
) -> Result<EditionAssemblyCounts, EditionTimelineError> {
    let propose = propose_membership_from_markers(map, markers).map_err(|error| {
        EditionTimelineError::new("assembly", format!("propose refused: {error}"))
    })?;
    let admit = admit_membership_proposals(&propose.proposals);
    let report =
        assemble_with_oracle_diff(&admit, map, effect_day, provenance).map_err(|error| {
            EditionTimelineError::new("assembly", format!("assembly refused: {error}"))
        })?;

    let counts = EditionAssemblyCounts {
        markers: markers.len() as u64,
        proposals: propose.proposals.len() as u64,
        admitted: admit.admitted.len() as u64,
        roots: report.root_count as u64,
        nodes: report.node_count as u64,
        committed: report.committed as u64,
        drift: report.drift as u64,
        missing: report.missing as u64,
        phantom: report.phantom as u64,
    };
    verify_accounting(&counts)?;
    Ok(counts)
}

/// Derive the single-edition assembly payload from the materialized wire layer.
///
/// In `assembly` mode the TSV must hold exactly one row. Fail-closed: an
/// unreadable input, a malformed TSV, a refused wire layer, an unavailable
/// embedded registry, an ungroundable effect day, or an assembly refusal
/// aborts with no payload produced.
pub fn build_assembly(cli: &EditionTimelineCli) -> Result<EditionAssembly, EditionTimelineError> {
    let tsv = fs::read_to_string(&cli.editions).map_err(|error| {
        EditionTimelineError::new(
            "input-read",
            format!("editions TSV is unreadable: {}", error.kind()),
        )
    })?;
    let mut rows = parse_edition_rows(&tsv)?;
    if rows.len() != 1 {
        return Err(EditionTimelineError::new(
            "usage",
            format!("assembly mode expects exactly 1 row, got {}", rows.len()),
        ));
    }
    build_assembly_row(rows.remove(0))
}

/// Derive the payload for one already-parsed edition row.
pub fn build_assembly_row(row: EditionRow) -> Result<EditionAssembly, EditionTimelineError> {
    let bytes = fs::read(&row.cleaned_wire).map_err(|error| {
        EditionTimelineError::new(
            "input-read",
            format!("cleaned wire is unreadable: {}", error.kind()),
        )
    })?;
    let wire = markers_from_cleaned_wire(&bytes)?;

    let map = load_hierarchy_map_for_path(&row.corpus_path).map_err(|error| {
        EditionTimelineError::new("registry", format!("registry map refused: {error}"))
    })?;
    let registry_bindings = embedded_binding_count_for_path(&row.corpus_path).map_err(|error| {
        EditionTimelineError::new("registry", format!("registry count refused: {error}"))
    })? as u64;

    let effect_day = edition_effect_day(&row.corpus_path).ok_or_else(|| {
        EditionTimelineError::new(
            "identity",
            "no grounded effect day for the corpus path".to_owned(),
        )
    })?;

    let minted = load_expression_id_for_path(&row.corpus_path);
    let expression_id_present = minted.is_some();
    let provenance = minted.unwrap_or_else(|| SYNTHETIC_PROVENANCE.to_owned());

    let counts = assemble_edition(&wire.markers, &map, effect_day, &provenance)?;

    Ok(EditionAssembly {
        edition_number: row.edition_number,
        corpus_path: row.corpus_path,
        effect_day,
        expression_id_present,
        registry_bindings,
        counts,
        wire_source_sha256: wire.wire_source_sha256,
        wire_source_bytes: wire.wire_source_bytes,
        cleaned_wire_sha256: wire.cleaned_wire_sha256,
    })
}

/// Resolve the structural effect-day ordinal for a corpus path.
///
/// Prefers an explicit `from-YYYY-MM-DD` filename date (the day the structural
/// change takes effect, mirroring `law-nexus-inspect replay`), else falls back
/// to the registered edition day. Returns `None` when neither grounds.
pub fn edition_effect_day(path: &str) -> Option<i64> {
    if let Some(iso) = from_date_in_path(path)
        && let Ok(day) = ln_temporal::calendar::legal_act_effect_day_to_ordinal(&iso)
    {
        return Some(day);
    }
    load_edition_day_for_path(path)
}

/// Extract an ISO day after `from-` in the final path segment, or `None`.
fn from_date_in_path(path: &str) -> Option<String> {
    let name = path.rsplit('/').next()?;
    let index = name.find("from-")?;
    let rest = &name[index + 5..];
    let candidate = rest.get(..10)?;
    let bytes = candidate.as_bytes();
    if bytes.len() == 10
        && bytes[..4].iter().all(u8::is_ascii_digit)
        && bytes[4] == b'-'
        && bytes[5..7].iter().all(u8::is_ascii_digit)
        && bytes[7] == b'-'
        && bytes[8..].iter().all(u8::is_ascii_digit)
    {
        Some(candidate.to_owned())
    } else {
        None
    }
}

/// Render the single-edition payload (`edition-assembly/v1`), deterministic
/// and ASCII (non-ASCII payload is escaped as JSON `\uXXXX`).
pub fn render_assembly(assembly: &EditionAssembly) -> Result<String, EditionTimelineError> {
    let counts = &assembly.counts;
    let mut out = String::with_capacity(1536);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(ASSEMBLY_SCHEMA));
    let _ = writeln!(out, "  \"kind\": {},", quote_json(ASSEMBLY_KIND));
    let _ = writeln!(out, "  \"edition_number\": {},", assembly.edition_number);
    let _ = writeln!(
        out,
        "  \"corpus_path\": {},",
        quote_json(&assembly.corpus_path)
    );
    let _ = writeln!(out, "  \"effect_day\": {},", assembly.effect_day);
    let _ = writeln!(
        out,
        "  \"expression_id_present\": {},",
        assembly.expression_id_present
    );
    let _ = writeln!(
        out,
        "  \"registry_bindings\": {},",
        assembly.registry_bindings
    );
    let _ = writeln!(out, "  \"markers\": {},", counts.markers);
    let _ = writeln!(out, "  \"proposals\": {},", counts.proposals);
    let _ = writeln!(out, "  \"admitted\": {},", counts.admitted);
    let _ = writeln!(out, "  \"committed\": {},", counts.committed);
    let _ = writeln!(out, "  \"roots\": {},", counts.roots);
    let _ = writeln!(out, "  \"nodes\": {},", counts.nodes);
    let _ = writeln!(out, "  \"drift\": {},", counts.drift);
    let _ = writeln!(out, "  \"missing\": {},", counts.missing);
    let _ = writeln!(out, "  \"phantom\": {},", counts.phantom);
    let _ = writeln!(
        out,
        "  \"wire_source\": {{\"sha256\": {}, \"bytes\": {}}},",
        quote_json(&assembly.wire_source_sha256),
        assembly.wire_source_bytes
    );
    let _ = writeln!(
        out,
        "  \"cleaned_wire_sha256\": {},",
        quote_json(&assembly.cleaned_wire_sha256)
    );
    let _ = writeln!(out, "  \"r1000_status\": {},", quote_json(R1000_STATUS));
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in ASSEMBLY_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 < ASSEMBLY_NON_CLAIMS.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(out, "    {}{comma}", quote_json(claim));
    }
    out.push_str("  ]\n}\n");
    ensure_ascii(&out, "assembly payload")?;
    Ok(out)
}

/// Derive the payload and either emit it (stdout) or write it to `--out`.
/// Returns the process exit code and the message line: the JSON payload when
/// no `--out` is given, otherwise a one-line summary.
pub fn run_edition_timeline(cli: &EditionTimelineCli) -> (u8, String) {
    if cli.mode != AssemblyMode::Assembly {
        return (
            EXIT_USAGE,
            EditionTimelineError::new(
                "usage",
                format!(
                    "mode '{}' is not implemented in this build",
                    cli.mode.as_str()
                ),
            )
            .to_string(),
        );
    }
    if cli.ctv {
        return (
            EXIT_USAGE,
            EditionTimelineError::new(
                "usage",
                "--ctv layer is not implemented in this build (T04)".to_owned(),
            )
            .to_string(),
        );
    }
    let assembly = match build_assembly(cli) {
        Ok(assembly) => assembly,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    let json = match render_assembly(&assembly) {
        Ok(json) => json,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    match cli.out.as_deref().filter(|value| !value.is_empty()) {
        Some(out) => match fs::write(Path::new(out), json.as_bytes()) {
            Ok(()) => (EXIT_OK, summary_line(&assembly)),
            Err(error) => (
                EXIT_OUT_UNWRITABLE,
                EditionTimelineError::new(
                    "out-write",
                    format!("artifact is not writable: {}", error.kind()),
                )
                .to_string(),
            ),
        },
        None => (EXIT_OK, json),
    }
}

/// One-line human summary for the `--out` write path.
fn summary_line(assembly: &EditionAssembly) -> String {
    format!(
        "edition={} markers={} proposals={} admitted={} roots={} nodes={} drift={}",
        assembly.edition_number,
        assembly.counts.markers,
        assembly.counts.proposals,
        assembly.counts.admitted,
        assembly.counts.roots,
        assembly.counts.nodes,
        assembly.counts.drift
    )
}

/// Fail-closed accounting invariants of one assembly pass.
fn verify_accounting(counts: &EditionAssemblyCounts) -> Result<(), EditionTimelineError> {
    if counts.drift != counts.missing + counts.phantom {
        return Err(EditionTimelineError::new(
            "accounting",
            "drift != missing + phantom",
        ));
    }
    if counts.admitted > counts.proposals {
        return Err(EditionTimelineError::new(
            "accounting",
            "admitted > proposals",
        ));
    }
    if counts.committed != counts.admitted {
        return Err(EditionTimelineError::new(
            "accounting",
            "committed != admitted",
        ));
    }
    Ok(())
}

/// Redaction guard: a payload must be ASCII, else fail-closed.
fn ensure_ascii(payload: &str, name: &str) -> Result<(), EditionTimelineError> {
    if payload.is_ascii() {
        Ok(())
    } else {
        Err(EditionTimelineError::new(
            "redaction",
            format!("{name} is not ASCII"),
        ))
    }
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
