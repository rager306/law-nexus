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
//! Boundary (S06): the `assembly` (T01), `chain` (T02), `timeline` (T03) and
//! `--ctv` (T04) layers are implemented. The `--ctv` layer adds an
//! oracle-synthesized presence filter (`edition_ast_at`) and a count-only text
//! CTV (`resolve_ctv`) over the same materialized JSONL layer; it composes
//! with `assembly` and `timeline`, never with `chain`. The timeline folds an
//! ascending
//! edition chain over the same materialized JSONL layer, clamping every
//! transition to `max(previous applied day, effect day)` so a non-monotonic
//! `rev-` date never reorders the replay. The crate never re-parses XML —
//! `ln-decode` reconstructs the block stream; `ln-kb-ontology` owns the
//! registry, membership and oracle-diff vocabulary.

use std::error::Error;
use std::fmt;
use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use ln_decode::article_body::collect_article_texts;
use ln_decode::cleaned_wire::read_cleaned_wire;
use ln_decode::domain::{ParsedBlock, SourceFormatId};
use ln_decode::hierarchy::extract_hierarchy;
use ln_decode::structural_profile::{GroupProfile, StructuralProfile};
use ln_decode::wire_blocks::blocks_from_cleaned_projection;

use ln_kb_ontology::domain::{
    AdmittedMembership, AmendmentDraftOp, ComponentInExpressionEvent, ComponentInExpressionLog,
    CtvResolution, ExpressionId, HierarchyBinding, HierarchyMap, HierarchyMapOutcome,
    HierarchyMarker, MembershipAdmitReport, TextVersionLog, admit_membership_proposals,
    assemble_with_oracle_diff, build_text_log_from_articles, diff_marker_sets,
    drafts_from_marker_diff, edition_ast_at, map_hierarchy_marker, marker_from_decode_token,
    oracle_diff, propose_membership_from_markers, resolve_ctv,
};
use ln_kb_ontology::registry::{
    embedded_binding_count_for_path, load_edition_day_for_path, load_expression_id_for_path,
    load_hierarchy_map_for_path,
};
use ln_temporal::domain::{
    AmendingActId, ComponentConceptId, MembershipChangeKind, StructuralAst, StructuralAstNode,
    VersionedMembershipEvent, VersionedMembershipLog, fold_membership_at,
};

/// Closed JSON schema id of the single-edition assembly payload.
pub const ASSEMBLY_SCHEMA: &str = "edition-assembly/v1";
/// Closed `kind` discriminator of the single-edition assembly payload.
pub const ASSEMBLY_KIND: &str = "edition_assembly";
/// Closed JSON schema id of the two-edition structural chain-replay payload.
pub const CHAIN_SCHEMA: &str = "edition-chain/v1";
/// Closed `kind` discriminator of the two-edition chain-replay payload.
pub const CHAIN_KIND: &str = "edition_chain";
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

/// Bounded non-claims carried by the two-edition chain-replay payload: what
/// the replay is **not**.
pub const CHAIN_NON_CLAIMS: [&str; 6] = [
    "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml_or_odt",
    "chain_replay_is_a_structural_projection_not_legal_amendment_correctness",
    "historical_rebind_is_a_local_fixture_decision_it_never_edits_the_embedded_registry",
    "effect_day_prefers_from_date_else_rev_date_process_truth_not_legal_truth",
    "integrity_is_not_semantic_completeness",
    "mints_no_component_concept_beyond_the_embedded_registry_and_the_local_rebind",
];

/// Closed JSON schema id of the multi-edition structural timeline payload.
pub const TIMELINE_SCHEMA: &str = "edition-timeline/v1";
/// Closed `kind` discriminator of the multi-edition structural timeline
/// payload.
pub const TIMELINE_KIND: &str = "edition_timeline";

/// Bounded non-claims carried by the multi-edition timeline payload: what the
/// fold is **not**.
pub const TIMELINE_NON_CLAIMS: [&str; 7] = [
    "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml_or_odt",
    "edition_timeline_is_a_structural_projection_not_legal_amendment_correctness",
    "historical_rebind_is_a_local_fixture_decision_it_never_edits_the_embedded_registry",
    "effect_day_prefers_from_date_else_rev_date_process_truth_not_legal_truth",
    "non_monotonic_rev_dates_are_clamped_to_the_previous_day_never_silently_reordered",
    "integrity_is_not_semantic_completeness",
    "mints_no_component_concept_beyond_the_embedded_registry_and_the_local_rebind",
];

/// Closed JSON schema id of the per-edition AST presence + text CTV payload.
pub const AST_CTV_SCHEMA: &str = "edition-ast-ctv/v1";
/// Closed `kind` discriminator of the AST presence + text CTV payload.
pub const AST_CTV_KIND: &str = "edition_ast_ctv";

/// Bounded non-claims carried by the AST/CTV payload: what the layer is **not**.
pub const AST_CTV_NON_CLAIMS: [&str; 8] = [
    "reads_only_the_materialized_cleaned_wire_jsonl_never_the_source_xml_or_odt",
    "presence_log_is_oracle_synthesized_not_expression_inheritance",
    "edition_ast_ctv_is_a_structural_projection_not_legal_amendment_correctness",
    "historical_rebind_is_a_local_fixture_decision_it_never_edits_the_embedded_registry",
    "effect_day_prefers_from_date_else_rev_date_process_truth_not_legal_truth",
    "text_ctv_is_raw_text_not_legal_interpretation_or_applicability",
    "missing_text_is_a_fail_closed_unknown_never_fabricated",
    "integrity_is_not_semantic_completeness",
];

/// Maximum characters retained in a bounded error detail (mirrors the S05
/// census consumer).
const MAX_DETAIL_CHARS: usize = 240;

/// Declared assembly mode. [`AssemblyMode::Assembly`] (T01),
/// [`AssemblyMode::Chain`] (T02) and [`AssemblyMode::Timeline`] (T03) are
/// implemented; the `--ctv` layer (T04) composes with `assembly` and
/// `timeline` and is refused for `chain`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum AssemblyMode {
    /// Single-edition snapshot assembly (T01).
    #[default]
    Assembly,
    /// Two-edition structural replay (T02).
    Chain,
    /// Full ascending edition timeline over N editions (T03).
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
    /// Request the presence + text CTV layer (T04) over `assembly` or
    /// `timeline` (refused for `chain`).
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

/// Decoded markers plus the reconstructed block stream and identity pins.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WireLayer {
    /// Decoded hierarchy markers, in document order.
    pub markers: Vec<HierarchyMarker>,
    /// Reconstructed decode blocks (the material for the CTV text layer).
    pub blocks: Vec<ParsedBlock>,
    /// Lowercase-hex sha256 of the frozen source (from the projection).
    pub wire_source_sha256: String,
    /// Byte length of the frozen source (from the projection).
    pub wire_source_bytes: u64,
    /// `sha256:<hex>` of the consumed cleaned-wire JSONL bytes.
    pub cleaned_wire_sha256: String,
}

/// Extract decoded markers **and** the reconstructed block stream from a
/// materialized cleaned-wire JSONL artifact.
///
/// Fail-closed: a refused wire layer or a failed block bridge aborts with no
/// layer. Only the JSONL layer is read — the source artifact is never opened.
pub fn wire_layer_from_cleaned_wire(bytes: &[u8]) -> Result<WireLayer, EditionTimelineError> {
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

    Ok(WireLayer {
        markers,
        blocks,
        wire_source_sha256,
        wire_source_bytes,
        cleaned_wire_sha256,
    })
}

/// Extract decoded markers from a materialized cleaned-wire JSONL artifact.
///
/// Fail-closed: a refused wire layer or a failed block bridge aborts with no
/// markers. Only the JSONL layer is read — the source artifact is never opened.
pub fn markers_from_cleaned_wire(bytes: &[u8]) -> Result<WireMarkers, EditionTimelineError> {
    let layer = wire_layer_from_cleaned_wire(bytes)?;
    Ok(WireMarkers {
        markers: layer.markers,
        wire_source_sha256: layer.wire_source_sha256,
        wire_source_bytes: layer.wire_source_bytes,
        cleaned_wire_sha256: layer.cleaned_wire_sha256,
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

// ─── T02: two-edition structural chain replay (corpus JSONL) ──────────────
// seed snapshot commit + marker-diff drafts applied at the target effect day,
// folded at the target day and compared against a direct target snapshot
// assembly. Mirrors `real_44fz_edition_0080_to_0081_replay_chain`, but over the
// materialized cleaned-wire JSONL layer (no XML re-parse). The seed commit and
// the target oracle both use the same registry map, so the only structural
// difference they can disagree on is the replayed delta itself.

/// Counts-only result of one two-edition chain replay. Carries no text.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditionChainCounts {
    /// Markers present in the target but absent from the seed snapshot.
    pub added: u64,
    /// Markers present in the seed but absent from the target snapshot.
    pub removed: u64,
    /// Total structural drafts (`added + removed`).
    pub drafts: u64,
    /// Attach drafts (equals `added`; carried for the payload contract).
    pub attach: u64,
    /// Detach drafts (equals `removed`; carried for the payload contract).
    pub detach: u64,
    /// Attach drafts actually appended to the replay log.
    pub applied_attach: u64,
    /// Detach drafts actually appended to the replay log.
    pub applied_detach: u64,
    /// Drafts whose marker/parent could not be resolved (fail-closed).
    pub quarantined: u64,
    /// Oracle drift (`missing + phantom`) between replay and target snapshot.
    pub drift: u64,
    /// Target CCs missing from the replay fold.
    pub missing: u64,
    /// Replay CCs absent from the target snapshot.
    pub phantom: u64,
}

/// Counts-only two-edition chain-replay payload. Carries no decoded text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionChain {
    /// Seed edition sequence number from the first TSV row.
    pub seed_edition: u32,
    /// Target edition sequence number from the second TSV row.
    pub target_edition: u32,
    /// Seed corpus-relative path as given in the TSV row.
    pub seed_corpus_path: String,
    /// Target corpus-relative path as given in the TSV row.
    pub target_corpus_path: String,
    /// Effect-day ordinal of the seed snapshot commit.
    pub seed_day: i64,
    /// Effect-day ordinal the drafts are applied at (the target `from-` day).
    pub target_day: i64,
    /// Registry bindings matched for the seed corpus path (before re-bind).
    pub registry_bindings: u64,
    /// Structural `statya` diffs offered to the local historical re-bind.
    pub historical_rebinds: u64,
    /// True when the seed path minted a real per-edition Expression ID.
    pub seed_expression_id_present: bool,
    /// True when the target path minted a real per-edition Expression ID.
    pub target_expression_id_present: bool,
    /// Chain-replay counts.
    pub counts: EditionChainCounts,
    /// `sha256:<hex>` of the consumed seed cleaned-wire JSONL bytes.
    pub seed_cleaned_wire_sha256: String,
    /// `sha256:<hex>` of the consumed target cleaned-wire JSONL bytes.
    pub target_cleaned_wire_sha256: String,
}

/// Pure two-edition structural replay over an explicit registry map.
///
/// Fail-closed: an invalid provenance, a refused proposal/draft step, an
/// unresolvable draft parent (quarantined, never invented), or a fold
/// conflict aborts with no counts. `map` is expected to already carry the
/// historical re-bind ([`build_chain`] registers it), so a removed `statya`
/// can detach from the parent it attached under in the seed snapshot.
pub fn replay_chain(
    seed_markers: &[HierarchyMarker],
    target_markers: &[HierarchyMarker],
    map: &HierarchyMap,
    seed_day: i64,
    target_day: i64,
    seed_provenance: &str,
    target_provenance: &str,
) -> Result<EditionChainCounts, EditionTimelineError> {
    let seed_prov = AmendingActId::parse(seed_provenance).map_err(|error| {
        EditionTimelineError::new("chain", format!("seed provenance refused: {error}"))
    })?;
    let target_prov = AmendingActId::parse(target_provenance).map_err(|error| {
        EditionTimelineError::new("chain", format!("target provenance refused: {error}"))
    })?;

    let seed_propose = propose_membership_from_markers(map, seed_markers).map_err(|error| {
        EditionTimelineError::new("chain", format!("seed propose refused: {error}"))
    })?;
    let seed_admit = admit_membership_proposals(&seed_propose.proposals);
    let target_propose = propose_membership_from_markers(map, target_markers).map_err(|error| {
        EditionTimelineError::new("chain", format!("target propose refused: {error}"))
    })?;
    let target_admit = admit_membership_proposals(&target_propose.proposals);

    // Seed commit: fold the seed structure into the replay log at its day.
    let mut log = VersionedMembershipLog::empty();
    for edge in &seed_admit.admitted {
        let event = VersionedMembershipEvent::try_new(
            MembershipChangeKind::Attach,
            edge.parent.clone(),
            edge.child.clone(),
            seed_day,
            seed_prov.clone(),
        )
        .map_err(|error| {
            EditionTimelineError::new("chain", format!("seed event refused: {error}"))
        })?;
        log.append(event).map_err(|error| {
            EditionTimelineError::new("chain", format!("seed append refused: {error}"))
        })?;
    }

    let diff = diff_marker_sets(seed_markers, target_markers);
    let drafts = drafts_from_marker_diff(seed_markers, target_markers, target_provenance)
        .map_err(|error| EditionTimelineError::new("chain", format!("drafts refused: {error}")))?;

    // Apply each draft at the target day. Attach parents come from the target
    // proposal, detach parents from the seed admission; an unresolved parent
    // is quarantined fail-closed, never invented.
    let mut applied_attach = 0u64;
    let mut applied_detach = 0u64;
    let mut quarantined = 0u64;
    for draft in &drafts {
        let probe =
            HierarchyMarker::try_new(None, &draft.level, &draft.number, None).map_err(|error| {
                EditionTimelineError::new("chain", format!("draft marker refused: {error}"))
            })?;
        let HierarchyMapOutcome::Bound { component } = map_hierarchy_marker(map, &probe) else {
            quarantined = quarantined.saturating_add(1);
            continue;
        };
        let parent = match draft.op {
            AmendmentDraftOp::Attach => target_admit
                .admitted
                .iter()
                .find(|edge| edge.child.as_str() == component.as_str())
                .map(|edge| edge.parent.clone()),
            AmendmentDraftOp::Detach => seed_admit
                .admitted
                .iter()
                .find(|edge| edge.child.as_str() == component.as_str())
                .map(|edge| edge.parent.clone()),
        };
        let Some(parent) = parent else {
            quarantined = quarantined.saturating_add(1);
            continue;
        };
        let kind = match draft.op {
            AmendmentDraftOp::Attach => MembershipChangeKind::Attach,
            AmendmentDraftOp::Detach => MembershipChangeKind::Detach,
        };
        let event = VersionedMembershipEvent::try_new(
            kind,
            parent,
            component,
            target_day,
            target_prov.clone(),
        )
        .map_err(|error| {
            EditionTimelineError::new("chain", format!("draft event refused: {error}"))
        })?;
        log.append(event).map_err(|error| {
            EditionTimelineError::new("chain", format!("draft append refused: {error}"))
        })?;
        match draft.op {
            AmendmentDraftOp::Attach => applied_attach = applied_attach.saturating_add(1),
            AmendmentDraftOp::Detach => applied_detach = applied_detach.saturating_add(1),
        }
    }

    let replay_ast = fold_membership_at(&log, target_day).map_err(|error| {
        EditionTimelineError::new("chain", format!("replay fold refused: {error}"))
    })?;

    // Oracle: a direct snapshot assembly of the target at the same day/map.
    let mut oracle_log = VersionedMembershipLog::empty();
    for edge in &target_admit.admitted {
        let event = VersionedMembershipEvent::try_new(
            MembershipChangeKind::Attach,
            edge.parent.clone(),
            edge.child.clone(),
            target_day,
            target_prov.clone(),
        )
        .map_err(|error| {
            EditionTimelineError::new("chain", format!("oracle event refused: {error}"))
        })?;
        oracle_log.append(event).map_err(|error| {
            EditionTimelineError::new("chain", format!("oracle append refused: {error}"))
        })?;
    }
    let oracle_ast = fold_membership_at(&oracle_log, target_day).map_err(|error| {
        EditionTimelineError::new("chain", format!("oracle fold refused: {error}"))
    })?;
    let oracle_ccs: Vec<ComponentConceptId> = oracle_ast
        .roots()
        .iter()
        .flat_map(collect_chain_ccs)
        .collect();
    let drift = oracle_diff(&replay_ast, &oracle_ccs);

    let counts = EditionChainCounts {
        added: diff.added.len() as u64,
        removed: diff.removed.len() as u64,
        drafts: drafts.len() as u64,
        attach: drafts
            .iter()
            .filter(|draft| draft.op == AmendmentDraftOp::Attach)
            .count() as u64,
        detach: drafts
            .iter()
            .filter(|draft| draft.op == AmendmentDraftOp::Detach)
            .count() as u64,
        applied_attach,
        applied_detach,
        quarantined,
        drift: drift.drift as u64,
        missing: drift.missing as u64,
        phantom: drift.phantom as u64,
    };
    verify_chain_accounting(&counts)?;
    Ok(counts)
}

fn collect_chain_ccs(node: &StructuralAstNode) -> Vec<ComponentConceptId> {
    let mut result = vec![node.component().clone()];
    for child in node.children() {
        result.extend(collect_chain_ccs(child));
    }
    result
}

/// Derive the two-edition chain payload from the materialized wire layer.
///
/// In `chain` mode the TSV must hold exactly two rows (seed, target).
/// Fail-closed: an unreadable input, a malformed TSV, a refused wire layer, an
/// undeducible work slug for the historical re-bind, an unavailable embedded
/// registry, an ungroundable effect day, or a replay refusal aborts with no
/// payload produced.
pub fn build_chain(cli: &EditionTimelineCli) -> Result<EditionChain, EditionTimelineError> {
    let tsv = fs::read_to_string(&cli.editions).map_err(|error| {
        EditionTimelineError::new(
            "input-read",
            format!("editions TSV is unreadable: {}", error.kind()),
        )
    })?;
    let mut rows = parse_edition_rows(&tsv)?;
    if rows.len() != 2 {
        return Err(EditionTimelineError::new(
            "usage",
            format!(
                "chain mode expects exactly 2 rows (seed, target), got {}",
                rows.len()
            ),
        ));
    }
    let target = rows.remove(1);
    let seed = rows.remove(0);

    let seed_bytes = fs::read(&seed.cleaned_wire).map_err(|error| {
        EditionTimelineError::new(
            "input-read",
            format!("seed cleaned wire is unreadable: {}", error.kind()),
        )
    })?;
    let target_bytes = fs::read(&target.cleaned_wire).map_err(|error| {
        EditionTimelineError::new(
            "input-read",
            format!("target cleaned wire is unreadable: {}", error.kind()),
        )
    })?;
    let seed_wire = markers_from_cleaned_wire(&seed_bytes)?;
    let target_wire = markers_from_cleaned_wire(&target_bytes)?;

    let mut map = load_hierarchy_map_for_path(&seed.corpus_path).map_err(|error| {
        EditionTimelineError::new("registry", format!("registry map refused: {error}"))
    })?;
    let slug = corpus_work_slug(&seed.corpus_path).ok_or_else(|| {
        EditionTimelineError::new(
            "identity",
            "cannot derive a work slug for the historical re-bind".to_owned(),
        )
    })?;
    let historical_rebinds =
        rebind_structural_statya(&mut map, &seed_wire.markers, &target_wire.markers, &slug)?;
    let registry_bindings = embedded_binding_count_for_path(&seed.corpus_path).map_err(|error| {
        EditionTimelineError::new("registry", format!("registry count refused: {error}"))
    })? as u64;

    let seed_day = edition_effect_day(&seed.corpus_path).ok_or_else(|| {
        EditionTimelineError::new(
            "identity",
            "no grounded effect day for the seed corpus path".to_owned(),
        )
    })?;
    let target_day = edition_effect_day(&target.corpus_path).ok_or_else(|| {
        EditionTimelineError::new(
            "identity",
            "no grounded effect day for the target corpus path".to_owned(),
        )
    })?;

    let seed_minted = load_expression_id_for_path(&seed.corpus_path);
    let target_minted = load_expression_id_for_path(&target.corpus_path);
    let seed_expression_id_present = seed_minted.is_some();
    let target_expression_id_present = target_minted.is_some();
    let seed_prov = seed_minted.unwrap_or_else(|| SYNTHETIC_PROVENANCE.to_owned());
    let target_prov = target_minted.unwrap_or_else(|| SYNTHETIC_PROVENANCE.to_owned());

    let counts = replay_chain(
        &seed_wire.markers,
        &target_wire.markers,
        &map,
        seed_day,
        target_day,
        &seed_prov,
        &target_prov,
    )?;

    Ok(EditionChain {
        seed_edition: seed.edition_number,
        target_edition: target.edition_number,
        seed_corpus_path: seed.corpus_path,
        target_corpus_path: target.corpus_path,
        seed_day,
        target_day,
        registry_bindings,
        historical_rebinds,
        seed_expression_id_present,
        target_expression_id_present,
        counts,
        seed_cleaned_wire_sha256: seed_wire.cleaned_wire_sha256,
        target_cleaned_wire_sha256: target_wire.cleaned_wire_sha256,
    })
}

/// Register a **local** historical CC for every `statya` in the marker diff so
/// the seed commit can attach a removed article and the replay can detach it.
///
/// Fixture decision (D764): never edits `kb-hierarchy-registry.yaml`; the CC
/// `cc:<slug>:statya-<n>` mirrors the embedded registry naming and is
/// idempotent for numbers already bound. Returns the number of diffs offered.
fn rebind_structural_statya(
    map: &mut HierarchyMap,
    seed_markers: &[HierarchyMarker],
    target_markers: &[HierarchyMarker],
    slug: &str,
) -> Result<u64, EditionTimelineError> {
    let diff = diff_marker_sets(seed_markers, target_markers);
    let mut offered = 0u64;
    for marker in diff.removed.iter().chain(diff.added.iter()) {
        if marker.level() != "statya" {
            continue;
        }
        let cc = ComponentConceptId::parse(&format!("cc:{slug}:statya-{}", marker.number()))
            .map_err(|error| {
                EditionTimelineError::new("registry", format!("rebind cc refused: {error}"))
            })?;
        let binding = HierarchyBinding::try_new(None, marker.level(), marker.number(), cc)
            .map_err(|error| {
                EditionTimelineError::new("registry", format!("rebind binding refused: {error}"))
            })?;
        map.register(binding).map_err(|error| {
            EditionTimelineError::new("registry", format!("rebind register refused: {error}"))
        })?;
        offered = offered.saturating_add(1);
    }
    Ok(offered)
}

/// Derive the work slug (`44-fz`) from a `law_YYYY-MM-DD_<slug>[/...]` corpus
/// path. Returns `None` when no such shape grounds — the caller fails closed
/// rather than inventing an identity.
fn corpus_work_slug(path: &str) -> Option<String> {
    let marker = "law_";
    let bytes = path.as_bytes();
    let mut from = 0usize;
    while let Some(relative) = path[from..].find(marker) {
        let start = from + relative + marker.len();
        if bytes.len() < start + 11 {
            return None;
        }
        let date = &path[start..start + 10];
        if !is_iso_day(date) || bytes.get(start + 10) != Some(&b'_') {
            from = start;
            continue;
        }
        let slug_start = start + 11;
        let slug_end = path[slug_start..]
            .find(['/', '_'])
            .map(|offset| slug_start + offset)
            .unwrap_or(path.len());
        let slug = &path[slug_start..slug_end];
        if slug.is_empty() {
            return None;
        }
        return Some(slug.to_owned());
    }
    None
}

fn is_iso_day(candidate: &str) -> bool {
    let bytes = candidate.as_bytes();
    bytes.len() == 10
        && bytes[..4].iter().all(u8::is_ascii_digit)
        && bytes[4] == b'-'
        && bytes[5..7].iter().all(u8::is_ascii_digit)
        && bytes[7] == b'-'
        && bytes[8..].iter().all(u8::is_ascii_digit)
}

/// Fail-closed accounting invariants of one chain replay.
fn verify_chain_accounting(counts: &EditionChainCounts) -> Result<(), EditionTimelineError> {
    if counts.added + counts.removed != counts.drafts {
        return Err(EditionTimelineError::new(
            "accounting",
            "added + removed != drafts",
        ));
    }
    if counts.attach != counts.added || counts.detach != counts.removed {
        return Err(EditionTimelineError::new(
            "accounting",
            "attach/detach != added/removed",
        ));
    }
    if counts.applied_attach + counts.applied_detach + counts.quarantined != counts.drafts {
        return Err(EditionTimelineError::new(
            "accounting",
            "applied + quarantined != drafts",
        ));
    }
    if counts.drift != counts.missing + counts.phantom {
        return Err(EditionTimelineError::new(
            "accounting",
            "drift != missing + phantom",
        ));
    }
    Ok(())
}

/// Render the two-edition chain payload (`edition-chain/v1`), deterministic
/// and ASCII (non-ASCII payload is escaped as JSON `\uXXXX`).
pub fn render_chain(chain: &EditionChain) -> Result<String, EditionTimelineError> {
    let counts = &chain.counts;
    let mut out = String::with_capacity(2048);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(CHAIN_SCHEMA));
    let _ = writeln!(out, "  \"kind\": {},", quote_json(CHAIN_KIND));
    let _ = writeln!(out, "  \"seed_edition\": {},", chain.seed_edition);
    let _ = writeln!(out, "  \"target_edition\": {},", chain.target_edition);
    let _ = writeln!(
        out,
        "  \"seed_corpus_path\": {},",
        quote_json(&chain.seed_corpus_path)
    );
    let _ = writeln!(
        out,
        "  \"target_corpus_path\": {},",
        quote_json(&chain.target_corpus_path)
    );
    let _ = writeln!(out, "  \"seed_day\": {},", chain.seed_day);
    let _ = writeln!(out, "  \"target_day\": {},", chain.target_day);
    let _ = writeln!(out, "  \"registry_bindings\": {},", chain.registry_bindings);
    let _ = writeln!(
        out,
        "  \"historical_rebinds\": {},",
        chain.historical_rebinds
    );
    let _ = writeln!(
        out,
        "  \"seed_expression_id_present\": {},",
        chain.seed_expression_id_present
    );
    let _ = writeln!(
        out,
        "  \"target_expression_id_present\": {},",
        chain.target_expression_id_present
    );
    let _ = writeln!(out, "  \"added\": {},", counts.added);
    let _ = writeln!(out, "  \"removed\": {},", counts.removed);
    let _ = writeln!(out, "  \"drafts\": {},", counts.drafts);
    let _ = writeln!(out, "  \"attach\": {},", counts.attach);
    let _ = writeln!(out, "  \"detach\": {},", counts.detach);
    let _ = writeln!(out, "  \"applied_attach\": {},", counts.applied_attach);
    let _ = writeln!(out, "  \"applied_detach\": {},", counts.applied_detach);
    let _ = writeln!(out, "  \"quarantined\": {},", counts.quarantined);
    let _ = writeln!(out, "  \"drift\": {},", counts.drift);
    let _ = writeln!(out, "  \"missing\": {},", counts.missing);
    let _ = writeln!(out, "  \"phantom\": {},", counts.phantom);
    let _ = writeln!(
        out,
        "  \"seed_cleaned_wire_sha256\": {},",
        quote_json(&chain.seed_cleaned_wire_sha256)
    );
    let _ = writeln!(
        out,
        "  \"target_cleaned_wire_sha256\": {},",
        quote_json(&chain.target_cleaned_wire_sha256)
    );
    let _ = writeln!(out, "  \"r1000_status\": {},", quote_json(R1000_STATUS));
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in CHAIN_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 < CHAIN_NON_CLAIMS.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(out, "    {}{comma}", quote_json(claim));
    }
    out.push_str("  ]\n}\n");
    ensure_ascii(&out, "chain payload")?;
    Ok(out)
}

// ─── T03: multi-edition structural timeline (corpus JSONL) ────────────────
// Ascending edition chain: the seed snapshot commits its admitted edges on its
// effect day; every following edition replays the marker diff (attach/detach)
// at `max(previous applied day, effect day)` and is compared against a direct
// snapshot assembly at that day. This extends the T02 two-edition replay to N
// editions over one grown registry map (the union of every `statya` seen
// anywhere in the timeline is locally re-bound, D764). No XML re-parse.

/// One edition snapshot offered to the timeline engine.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionSnapshot<'a> {
    /// Edition sequence number (`edition-0118` -> 118).
    pub edition_number: u32,
    /// Grounded effect-day ordinal for this edition (from/rev date rule).
    pub effect_day: i64,
    /// Provenance for the replay events minted from this snapshot.
    pub provenance: &'a str,
    /// Decoded hierarchy markers, in document order.
    pub markers: &'a [HierarchyMarker],
}

/// Counts-only result of one edition within the timeline. Carries no text.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditionTimelinePoint {
    /// Edition sequence number.
    pub edition_number: u32,
    /// Grounded effect day of this edition (from/rev date rule).
    pub effect_day: i64,
    /// Day the transition's drafts were actually applied
    /// (`max(previous applied day, effect day)`).
    pub applied_day: i64,
    /// Decoded markers in the snapshot.
    pub markers: u64,
    /// Structural drafts offered by the transition (`0` for the seed).
    pub drafts: u64,
    /// Drafts appended to the replay log (`applied_attach + applied_detach`).
    pub applied: u64,
    /// Attach drafts appended to the replay log.
    pub applied_attach: u64,
    /// Detach drafts appended to the replay log.
    pub applied_detach: u64,
    /// Drafts whose component/parent could not be resolved (fail-closed).
    pub quarantined: u64,
    /// Oracle drift (`missing + phantom`) of the replay fold.
    pub drift: u64,
    /// Expected CCs missing from the replay fold.
    pub missing: u64,
    /// Replay CCs absent from the oracle snapshot.
    pub phantom: u64,
    /// Forest roots of the replay fold.
    pub roots: u64,
    /// Total nodes of the replay fold.
    pub nodes: u64,
}

/// Aggregate counts of one timeline. Carries no text.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditionTimelineTotals {
    /// Number of editions folded.
    pub editions: u64,
    /// Sum of decoded markers over the editions.
    pub markers: u64,
    /// Sum of structural drafts over the transitions.
    pub drafts: u64,
    /// Sum of applied drafts over the transitions.
    pub applied: u64,
    /// Sum of applied attach drafts.
    pub applied_attach: u64,
    /// Sum of applied detach drafts.
    pub applied_detach: u64,
    /// Sum of quarantined drafts.
    pub quarantined: u64,
    /// Sum of per-edition drift.
    pub drift: u64,
    /// Sum of per-edition missing CCs.
    pub missing: u64,
    /// Sum of per-edition phantom CCs.
    pub phantom: u64,
    /// Maximum folded node count across the editions.
    pub max_nodes: u64,
}

/// A transition whose grounded effect day is earlier than the day the replay
/// already reached; the drafts are clamped to the previous day.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NonMonotonicTransition {
    /// Edition the replay was at.
    pub from_edition: u32,
    /// Applied day of the replay before this transition.
    pub from_day: i64,
    /// Edition whose effect day went backwards.
    pub to_edition: u32,
    /// Grounded (backwards) effect day of the next edition.
    pub to_day: i64,
    /// Day the drafts were clamped to (equals `from_day`).
    pub applied_day: i64,
}

/// Counts-only multi-edition structural timeline payload. Carries no text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionTimeline {
    /// Work slug used for the local historical re-bind (`44-fz`).
    pub slug: String,
    /// Registry bindings matched for the corpus path (before the re-bind).
    pub registry_bindings: u64,
    /// Distinct `statya` numbers locally re-bound across the whole timeline.
    pub historical_rebinds: u64,
    /// Per-edition points, in ascending `edition_number` order.
    pub points: Vec<EditionTimelinePoint>,
    /// Aggregate counts.
    pub totals: EditionTimelineTotals,
    /// Documented non-monotonic transitions (never silently reordered).
    pub non_monotonic_transitions: Vec<NonMonotonicTransition>,
}

/// Fold an ascending edition chain into a structural timeline over an explicit
/// registry map.
///
/// Fail-closed: empty input, an invalid provenance, a refused proposal step, an
/// unresolvable draft parent (quarantined, never invented), a fold conflict, or
/// a violated accounting invariant aborts with no timeline. `map` is expected
/// to already carry the historical re-bind ([`build_timeline`] registers the
/// union of every `statya`), so a removed article can detach from the parent it
/// attached under in an earlier snapshot.
pub fn replay_timeline(
    snapshots: &[EditionSnapshot<'_>],
    map: &HierarchyMap,
    slug: &str,
    registry_bindings: u64,
    historical_rebinds: u64,
) -> Result<EditionTimeline, EditionTimelineError> {
    if snapshots.is_empty() {
        return Err(EditionTimelineError::new(
            "input-read",
            "edition timeline is empty",
        ));
    }

    let mut points: Vec<EditionTimelinePoint> = Vec::with_capacity(snapshots.len());
    let mut non_monotonic_transitions: Vec<NonMonotonicTransition> = Vec::new();
    let mut log = VersionedMembershipLog::empty();

    // Seed: commit its admitted edges at its own effect day.
    let seed = &snapshots[0];
    let seed_prov = parse_timeline_provenance(seed.provenance, "seed")?;
    let seed_admit = admit_snapshot(map, seed.markers, "seed")?;
    for edge in &seed_admit.admitted {
        append_timeline_edge(
            &mut log,
            MembershipChangeKind::Attach,
            &edge.parent,
            &edge.child,
            seed.effect_day,
            seed_prov.clone(),
        )?;
    }
    let seed_oracle = fold_admitted(&seed_admit.admitted, seed.effect_day, seed_prov.clone())?;
    let seed_replay = fold_membership_at(&log, seed.effect_day).map_err(|error| {
        EditionTimelineError::new("timeline", format!("seed fold refused: {error}"))
    })?;
    points.push(build_timeline_point(
        seed.edition_number,
        seed.effect_day,
        seed.effect_day,
        &seed_replay,
        &seed_oracle,
        seed.markers.len() as u64,
        0,
        0,
        0,
        0,
    ));

    let mut prev_markers = seed.markers;
    let mut prev_day = seed.effect_day;
    let mut prev_admit = seed_admit;

    for (index, current) in snapshots.iter().enumerate().skip(1) {
        let current_prov = parse_timeline_provenance(current.provenance, "edition")?;
        // Clamp: a backwards effect day never reorders the replay.
        let applied_day = prev_day.max(current.effect_day);
        if current.effect_day < prev_day {
            non_monotonic_transitions.push(NonMonotonicTransition {
                from_edition: snapshots[index - 1].edition_number,
                from_day: prev_day,
                to_edition: current.edition_number,
                to_day: current.effect_day,
                applied_day,
            });
        }

        let current_admit = admit_snapshot(map, current.markers, "edition")?;
        let drafts = drafts_from_marker_diff(prev_markers, current.markers, current.provenance)
            .map_err(|error| {
                EditionTimelineError::new("timeline", format!("drafts refused: {error}"))
            })?;

        let mut applied_attach = 0u64;
        let mut applied_detach = 0u64;
        let mut quarantined = 0u64;
        for draft in &drafts {
            let probe = HierarchyMarker::try_new(None, &draft.level, &draft.number, None).map_err(
                |error| {
                    EditionTimelineError::new("timeline", format!("draft marker refused: {error}"))
                },
            )?;
            let HierarchyMapOutcome::Bound { component } = map_hierarchy_marker(map, &probe) else {
                quarantined = quarantined.saturating_add(1);
                continue;
            };
            // Attach parents come from the current snapshot; detach parents from
            // the previous snapshot's admission. An unresolved parent is
            // quarantined fail-closed, never invented.
            let parent = match draft.op {
                AmendmentDraftOp::Attach => current_admit
                    .admitted
                    .iter()
                    .find(|edge| edge.child.as_str() == component.as_str())
                    .map(|edge| edge.parent.clone()),
                AmendmentDraftOp::Detach => prev_admit
                    .admitted
                    .iter()
                    .find(|edge| edge.child.as_str() == component.as_str())
                    .map(|edge| edge.parent.clone()),
            };
            let Some(parent) = parent else {
                quarantined = quarantined.saturating_add(1);
                continue;
            };
            let kind = match draft.op {
                AmendmentDraftOp::Attach => MembershipChangeKind::Attach,
                AmendmentDraftOp::Detach => MembershipChangeKind::Detach,
            };
            append_timeline_edge(
                &mut log,
                kind,
                &parent,
                &component,
                applied_day,
                current_prov.clone(),
            )?;
            match draft.op {
                AmendmentDraftOp::Attach => applied_attach = applied_attach.saturating_add(1),
                AmendmentDraftOp::Detach => applied_detach = applied_detach.saturating_add(1),
            }
        }

        let replay_ast = fold_membership_at(&log, applied_day).map_err(|error| {
            EditionTimelineError::new("timeline", format!("replay fold refused: {error}"))
        })?;
        let oracle_ast = fold_admitted(&current_admit.admitted, applied_day, current_prov)?;

        points.push(build_timeline_point(
            current.edition_number,
            current.effect_day,
            applied_day,
            &replay_ast,
            &oracle_ast,
            current.markers.len() as u64,
            drafts.len() as u64,
            applied_attach,
            applied_detach,
            quarantined,
        ));

        prev_markers = current.markers;
        prev_day = applied_day;
        prev_admit = current_admit;
    }

    let totals = timeline_totals(&points);
    verify_timeline_accounting(&points, &totals)?;
    Ok(EditionTimeline {
        slug: slug.to_owned(),
        registry_bindings,
        historical_rebinds,
        points,
        totals,
        non_monotonic_transitions,
    })
}

/// Build one timeline point from the replay fold and its oracle snapshot.
#[allow(clippy::too_many_arguments)]
fn build_timeline_point(
    edition_number: u32,
    effect_day: i64,
    applied_day: i64,
    replay_ast: &StructuralAst,
    oracle_ast: &StructuralAst,
    markers: u64,
    drafts: u64,
    applied_attach: u64,
    applied_detach: u64,
    quarantined: u64,
) -> EditionTimelinePoint {
    let oracle_ccs: Vec<ComponentConceptId> = oracle_ast
        .roots()
        .iter()
        .flat_map(collect_chain_ccs)
        .collect();
    let drift = oracle_diff(replay_ast, &oracle_ccs);
    EditionTimelinePoint {
        edition_number,
        effect_day,
        applied_day,
        markers,
        drafts,
        applied: applied_attach + applied_detach,
        applied_attach,
        applied_detach,
        quarantined,
        drift: drift.drift as u64,
        missing: drift.missing as u64,
        phantom: drift.phantom as u64,
        roots: replay_ast.roots().len() as u64,
        nodes: count_timeline_nodes(replay_ast),
    }
}

/// Fold a set of admitted edges into a fresh snapshot AST at `day`.
fn fold_admitted(
    edges: &[AdmittedMembership],
    day: i64,
    provenance: AmendingActId,
) -> Result<StructuralAst, EditionTimelineError> {
    let mut log = VersionedMembershipLog::empty();
    for edge in edges {
        append_timeline_edge(
            &mut log,
            MembershipChangeKind::Attach,
            &edge.parent,
            &edge.child,
            day,
            provenance.clone(),
        )?;
    }
    fold_membership_at(&log, day)
        .map_err(|error| EditionTimelineError::new("timeline", format!("fold refused: {error}")))
}

/// Propose + admit the attach edges of one snapshot over the registry map.
fn admit_snapshot(
    map: &HierarchyMap,
    markers: &[HierarchyMarker],
    label: &str,
) -> Result<MembershipAdmitReport, EditionTimelineError> {
    let propose = propose_membership_from_markers(map, markers).map_err(|error| {
        EditionTimelineError::new("timeline", format!("{label} propose refused: {error}"))
    })?;
    Ok(admit_membership_proposals(&propose.proposals))
}

/// Append one membership event to the replay log.
fn append_timeline_edge(
    log: &mut VersionedMembershipLog,
    kind: MembershipChangeKind,
    parent: &ComponentConceptId,
    child: &ComponentConceptId,
    day: i64,
    provenance: AmendingActId,
) -> Result<(), EditionTimelineError> {
    let event =
        VersionedMembershipEvent::try_new(kind, parent.clone(), child.clone(), day, provenance)
            .map_err(|error| {
                EditionTimelineError::new("timeline", format!("event refused: {error}"))
            })?;
    log.append(event)
        .map_err(|error| EditionTimelineError::new("timeline", format!("append refused: {error}")))
}

/// Parse a provenance string into an amending-act id, else fail closed.
fn parse_timeline_provenance(
    value: &str,
    label: &str,
) -> Result<AmendingActId, EditionTimelineError> {
    AmendingActId::parse(value).map_err(|error| {
        EditionTimelineError::new("timeline", format!("{label} provenance refused: {error}"))
    })
}

/// Recursive total node count of a folded AST.
fn count_timeline_nodes(ast: &StructuralAst) -> u64 {
    fn count(node: &StructuralAstNode) -> u64 {
        1 + node.children().iter().map(count).sum::<u64>()
    }
    ast.roots().iter().map(count).sum()
}

/// Aggregate per-edition points into totals.
fn timeline_totals(points: &[EditionTimelinePoint]) -> EditionTimelineTotals {
    let mut totals = EditionTimelineTotals {
        editions: points.len() as u64,
        ..EditionTimelineTotals::default()
    };
    for point in points {
        totals.markers = totals.markers.saturating_add(point.markers);
        totals.drafts = totals.drafts.saturating_add(point.drafts);
        totals.applied = totals.applied.saturating_add(point.applied);
        totals.applied_attach = totals.applied_attach.saturating_add(point.applied_attach);
        totals.applied_detach = totals.applied_detach.saturating_add(point.applied_detach);
        totals.quarantined = totals.quarantined.saturating_add(point.quarantined);
        totals.drift = totals.drift.saturating_add(point.drift);
        totals.missing = totals.missing.saturating_add(point.missing);
        totals.phantom = totals.phantom.saturating_add(point.phantom);
        totals.max_nodes = totals.max_nodes.max(point.nodes);
    }
    totals
}

/// Fail-closed accounting invariants of one timeline.
fn verify_timeline_accounting(
    points: &[EditionTimelinePoint],
    totals: &EditionTimelineTotals,
) -> Result<(), EditionTimelineError> {
    let mut seen = EditionTimelineTotals {
        editions: points.len() as u64,
        ..EditionTimelineTotals::default()
    };
    for point in points {
        if point.applied_attach + point.applied_detach != point.applied {
            return Err(EditionTimelineError::new(
                "accounting",
                "applied_attach + applied_detach != applied",
            ));
        }
        if point.applied + point.quarantined != point.drafts {
            return Err(EditionTimelineError::new(
                "accounting",
                "applied + quarantined != drafts",
            ));
        }
        if point.drift != point.missing + point.phantom {
            return Err(EditionTimelineError::new(
                "accounting",
                "drift != missing + phantom",
            ));
        }
        if point.applied_day < point.effect_day {
            return Err(EditionTimelineError::new(
                "accounting",
                "applied_day earlier than effect_day",
            ));
        }
        seen.markers = seen.markers.saturating_add(point.markers);
        seen.drafts = seen.drafts.saturating_add(point.drafts);
        seen.applied = seen.applied.saturating_add(point.applied);
        seen.applied_attach = seen.applied_attach.saturating_add(point.applied_attach);
        seen.applied_detach = seen.applied_detach.saturating_add(point.applied_detach);
        seen.quarantined = seen.quarantined.saturating_add(point.quarantined);
        seen.drift = seen.drift.saturating_add(point.drift);
        seen.missing = seen.missing.saturating_add(point.missing);
        seen.phantom = seen.phantom.saturating_add(point.phantom);
        seen.max_nodes = seen.max_nodes.max(point.nodes);
    }
    if seen != *totals {
        return Err(EditionTimelineError::new(
            "accounting",
            "point totals do not match the aggregate",
        ));
    }
    Ok(())
}

/// Render the multi-edition timeline payload (`edition-timeline/v1`),
/// deterministic and ASCII (non-ASCII payload is escaped as JSON `\uXXXX`).
pub fn render_timeline(timeline: &EditionTimeline) -> Result<String, EditionTimelineError> {
    let totals = &timeline.totals;
    let mut out = String::with_capacity(4096 + timeline.points.len() * 160);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(TIMELINE_SCHEMA));
    let _ = writeln!(out, "  \"kind\": {},", quote_json(TIMELINE_KIND));
    let _ = writeln!(out, "  \"slug\": {},", quote_json(&timeline.slug));
    let _ = writeln!(
        out,
        "  \"registry_bindings\": {},",
        timeline.registry_bindings
    );
    let _ = writeln!(
        out,
        "  \"historical_rebinds\": {},",
        timeline.historical_rebinds
    );
    let _ = writeln!(out, "  \"editions\": {},", totals.editions);
    out.push_str("  \"totals\": {\n");
    let _ = writeln!(out, "    \"markers\": {},", totals.markers);
    let _ = writeln!(out, "    \"drafts\": {},", totals.drafts);
    let _ = writeln!(out, "    \"applied\": {},", totals.applied);
    let _ = writeln!(out, "    \"applied_attach\": {},", totals.applied_attach);
    let _ = writeln!(out, "    \"applied_detach\": {},", totals.applied_detach);
    let _ = writeln!(out, "    \"quarantined\": {},", totals.quarantined);
    let _ = writeln!(out, "    \"drift\": {},", totals.drift);
    let _ = writeln!(out, "    \"missing\": {},", totals.missing);
    let _ = writeln!(out, "    \"phantom\": {},", totals.phantom);
    let _ = writeln!(out, "    \"max_nodes\": {}", totals.max_nodes);
    out.push_str("  },\n");
    out.push_str("  \"non_monotonic_transitions\": [");
    if timeline.non_monotonic_transitions.is_empty() {
        out.push_str("],\n");
    } else {
        out.push('\n');
        for (index, transition) in timeline.non_monotonic_transitions.iter().enumerate() {
            let comma = if index + 1 < timeline.non_monotonic_transitions.len() {
                ","
            } else {
                ""
            };
            let _ = writeln!(
                out,
                "    {{\"from_edition\": {}, \"from_day\": {}, \"to_edition\": {}, \"to_day\": {}, \"applied_day\": {}}}{comma}",
                transition.from_edition,
                transition.from_day,
                transition.to_edition,
                transition.to_day,
                transition.applied_day
            );
        }
        out.push_str("  ],\n");
    }
    out.push_str("  \"per_edition\": [");
    if timeline.points.is_empty() {
        out.push_str("],\n");
    } else {
        out.push('\n');
        for (index, point) in timeline.points.iter().enumerate() {
            let comma = if index + 1 < timeline.points.len() {
                ","
            } else {
                ""
            };
            let _ = writeln!(
                out,
                "    {{\"edition_number\": {}, \"effect_day\": {}, \"applied_day\": {}, \"markers\": {}, \"drafts\": {}, \"applied\": {}, \"applied_attach\": {}, \"applied_detach\": {}, \"quarantined\": {}, \"drift\": {}, \"missing\": {}, \"phantom\": {}, \"roots\": {}, \"nodes\": {}}}{comma}",
                point.edition_number,
                point.effect_day,
                point.applied_day,
                point.markers,
                point.drafts,
                point.applied,
                point.applied_attach,
                point.applied_detach,
                point.quarantined,
                point.drift,
                point.missing,
                point.phantom,
                point.roots,
                point.nodes
            );
        }
        out.push_str("  ],\n");
    }
    let _ = writeln!(out, "  \"r1000_status\": {},", quote_json(R1000_STATUS));
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in TIMELINE_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 < TIMELINE_NON_CLAIMS.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(out, "    {}{comma}", quote_json(claim));
    }
    out.push_str("  ]\n}\n");
    ensure_ascii(&out, "timeline payload")?;
    Ok(out)
}

/// Derive the multi-edition timeline payload from the materialized wire layer.
///
/// Reads every row's cleaned-wire artifact, pre-binds the union of every
/// `statya` number seen in any snapshot (D764, local only), then folds the
/// chain in ascending `edition_number` order. Fail-closed: an empty list, an
/// unreadable input, a malformed TSV, a refused wire layer, an undeducible work
/// slug, an unavailable embedded registry, an ungroundable effect day, or a
/// replay refusal aborts with no payload produced.
pub fn build_timeline(cli: &EditionTimelineCli) -> Result<EditionTimeline, EditionTimelineError> {
    let tsv = fs::read_to_string(&cli.editions).map_err(|error| {
        EditionTimelineError::new(
            "input-read",
            format!("editions TSV is unreadable: {}", error.kind()),
        )
    })?;
    let mut rows = parse_edition_rows(&tsv)?;
    if rows.is_empty() {
        return Err(EditionTimelineError::new(
            "input-read",
            "edition timeline is empty",
        ));
    }
    rows.sort_by_key(|row| row.edition_number);
    for pair in rows.windows(2) {
        if pair[0].edition_number == pair[1].edition_number {
            return Err(EditionTimelineError::new(
                "usage",
                format!("duplicate edition_number {}", pair[0].edition_number),
            ));
        }
    }

    struct Materialized {
        edition_number: u32,
        effect_day: i64,
        provenance: String,
        markers: Vec<HierarchyMarker>,
    }

    let mut materialized: Vec<Materialized> = Vec::with_capacity(rows.len());
    for row in &rows {
        let bytes = fs::read(&row.cleaned_wire).map_err(|error| {
            EditionTimelineError::new(
                "input-read",
                format!(
                    "cleaned wire for edition {} is unreadable: {}",
                    row.edition_number,
                    error.kind()
                ),
            )
        })?;
        let wire = markers_from_cleaned_wire(&bytes)?;
        let effect_day = edition_effect_day(&row.corpus_path).ok_or_else(|| {
            EditionTimelineError::new(
                "identity",
                format!(
                    "no grounded effect day for edition {} corpus path",
                    row.edition_number
                ),
            )
        })?;
        let provenance = load_expression_id_for_path(&row.corpus_path)
            .unwrap_or_else(|| SYNTHETIC_PROVENANCE.to_owned());
        materialized.push(Materialized {
            edition_number: row.edition_number,
            effect_day,
            provenance,
            markers: wire.markers,
        });
    }

    let mut map = load_hierarchy_map_for_path(&rows[0].corpus_path).map_err(|error| {
        EditionTimelineError::new("registry", format!("registry map refused: {error}"))
    })?;
    let slug = corpus_work_slug(&rows[0].corpus_path).ok_or_else(|| {
        EditionTimelineError::new(
            "identity",
            "cannot derive a work slug for the historical re-bind".to_owned(),
        )
    })?;
    let marker_sets: Vec<&[HierarchyMarker]> = materialized
        .iter()
        .map(|item| item.markers.as_slice())
        .collect();
    let historical_rebinds = rebind_union_statya(&mut map, &marker_sets, &slug)?;
    let registry_bindings =
        embedded_binding_count_for_path(&rows[0].corpus_path).map_err(|error| {
            EditionTimelineError::new("registry", format!("registry count refused: {error}"))
        })? as u64;

    let snapshots: Vec<EditionSnapshot<'_>> = materialized
        .iter()
        .map(|item| EditionSnapshot {
            edition_number: item.edition_number,
            effect_day: item.effect_day,
            provenance: item.provenance.as_str(),
            markers: &item.markers,
        })
        .collect();

    replay_timeline(
        &snapshots,
        &map,
        &slug,
        registry_bindings,
        historical_rebinds,
    )
}

/// Register a **local** historical CC for every `statya` number seen in any
/// snapshot so the seed commit can attach an article that the embedded registry
/// does not know and a later detach can detach it.
///
/// Fixture decision (D764): never edits `kb-hierarchy-registry.yaml`; the CC
/// `cc:<slug>:statya-<n>` mirrors the embedded registry naming and is
/// idempotent for numbers already bound. Returns the number of distinct
/// `statya` numbers offered (not only the newly minted ones).
fn rebind_union_statya(
    map: &mut HierarchyMap,
    marker_sets: &[&[HierarchyMarker]],
    slug: &str,
) -> Result<u64, EditionTimelineError> {
    let mut seen: Vec<String> = Vec::new();
    for markers in marker_sets {
        for marker in markers.iter() {
            if marker.level() != "statya" {
                continue;
            }
            let number = marker.number().to_owned();
            if !seen.contains(&number) {
                seen.push(number);
            }
        }
    }
    let mut offered = 0u64;
    for number in &seen {
        let cc =
            ComponentConceptId::parse(&format!("cc:{slug}:statya-{number}")).map_err(|error| {
                EditionTimelineError::new("registry", format!("rebind cc refused: {error}"))
            })?;
        let binding = HierarchyBinding::try_new(None, "statya", number, cc).map_err(|error| {
            EditionTimelineError::new("registry", format!("rebind binding refused: {error}"))
        })?;
        map.register(binding).map_err(|error| {
            EditionTimelineError::new("registry", format!("rebind register refused: {error}"))
        })?;
        offered = offered.saturating_add(1);
    }
    Ok(offered)
}

// ─── T04: per-edition AST presence + text CTV over corpus JSONL ───────────
// After each edition's membership fold, an oracle-synthesized presence log
// filters the composition (`edition_ast_at`) and a count-only text CTV
// (`resolve_ctv`) is computed over the admission components. Counts only: no
// decoded text is emitted. The presence log is a projection, never expression
// inheritance.

/// Counts-only AST/CTV result of one edition. Carries no text.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditionAstCtvPoint {
    /// Edition sequence number.
    pub edition_number: u32,
    /// Grounded effect day of this edition.
    pub effect_day: i64,
    /// Distinct CCs of the folded membership composition (`visible + hidden`).
    pub admitted: u64,
    /// Composition CCs retained by the oracle-synthesized presence set.
    pub visible: u64,
    /// Composition CCs pruned by the presence filter (`admitted - visible`).
    pub hidden: u64,
    /// Admission CCs whose text CTV resolves to exactly one text.
    pub ctv_resolved: u64,
    /// Admission CCs with no text event at or before the effect day.
    pub ctv_unknown: u64,
    /// Admission CCs whose latest same-day text events disagree.
    pub ctv_conflict: u64,
}

/// Aggregate counts of one AST/CTV payload. Carries no text.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditionAstCtvTotals {
    /// Number of editions.
    pub editions: u64,
    /// Sum of `admitted`.
    pub admitted: u64,
    /// Sum of `visible`.
    pub visible: u64,
    /// Sum of `hidden`.
    pub hidden: u64,
    /// Sum of resolved text CTVs.
    pub ctv_resolved: u64,
    /// Sum of unknown text CTVs.
    pub ctv_unknown: u64,
    /// Sum of conflicting text CTVs.
    pub ctv_conflict: u64,
}

/// Counts-only AST/CTV payload. Carries no text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionAstCtv {
    /// Work slug used for the local historical re-bind (`44-fz`).
    pub slug: String,
    /// Registry bindings matched for the corpus path (before the re-bind).
    pub registry_bindings: u64,
    /// Distinct `statya` numbers locally re-bound across the editions.
    pub historical_rebinds: u64,
    /// Per-edition points, in ascending `edition_number` order.
    pub points: Vec<EditionAstCtvPoint>,
    /// Aggregate counts.
    pub totals: EditionAstCtvTotals,
}

/// Presence-filtered view counts: `(visible, hidden)`.
///
/// `visible` are the CCs of the `edition_ast_at` fold (membership filtered by
/// the oracle-synthesized presence set); `hidden` are the composition CCs the
/// filter pruned. `filter_ast_to_expression` drops a CC that is absent from the
/// presence set (and any ancestor with no present descendant) — a pruned CC is
/// reported as hidden, never a silent pass. Fail-closed: a refused composition
/// or presence fold is an error.
pub fn edition_visibility_counts(
    membership_log: &VersionedMembershipLog,
    presence_log: &ComponentInExpressionLog,
    expression: &ExpressionId,
    day: i64,
) -> Result<(u64, u64), EditionTimelineError> {
    let edition =
        edition_ast_at(membership_log, presence_log, expression, day).map_err(|error| {
            EditionTimelineError::new("ctv", format!("edition_ast_at refused: {error}"))
        })?;
    let mut visible: Vec<ComponentConceptId> = Vec::new();
    for root in edition.roots() {
        visible.extend(collect_chain_ccs(root));
    }
    let composition = fold_membership_at(membership_log, day).map_err(|error| {
        EditionTimelineError::new("ctv", format!("composition fold refused: {error}"))
    })?;
    let mut membership: Vec<ComponentConceptId> = Vec::new();
    for root in composition.roots() {
        membership.extend(collect_chain_ccs(root));
    }
    let hidden = membership
        .iter()
        .filter(|cc| !visible.iter().any(|v| v == *cc))
        .count();
    Ok((visible.len() as u64, hidden as u64))
}

/// Counts of `resolve_ctv` over `components`: `(resolved, unknown, conflict)`.
///
/// Each component is counted once. A component with no text event at or before
/// `day` is Unknown (fail-closed, never fabricated); two disagreeing same-day
/// events for one component are a Conflict.
pub fn ctv_resolution_counts(
    log: &TextVersionLog,
    components: &[ComponentConceptId],
    day: i64,
) -> (u64, u64, u64) {
    let mut resolved = 0u64;
    let mut unknown = 0u64;
    let mut conflict = 0u64;
    for (index, cc) in components.iter().enumerate() {
        if components[..index].iter().any(|prior| prior == cc) {
            continue;
        }
        match resolve_ctv(log, cc, day) {
            CtvResolution::Resolved { .. } => resolved = resolved.saturating_add(1),
            CtvResolution::Unknown => unknown = unknown.saturating_add(1),
            CtvResolution::Conflict { .. } => conflict = conflict.saturating_add(1),
        }
    }
    (resolved, unknown, conflict)
}

/// Embedded `federal_law@v1` structural profile (the article unit ladder).
fn federal_law_group() -> Result<GroupProfile, EditionTimelineError> {
    let profile = StructuralProfile::embedded().map_err(|error| {
        EditionTimelineError::new("profile", format!("embedded profile refused: {error}"))
    })?;
    profile.group("federal_law@v1").cloned().ok_or_else(|| {
        EditionTimelineError::new("profile", "federal_law@v1 structural group is absent")
    })
}

/// Build one edition's AST/CTV point from its markers, blocks and registry map.
#[allow(clippy::too_many_arguments)]
fn build_ast_ctv_point(
    edition_number: u32,
    effect_day: i64,
    provenance: &str,
    markers: &[HierarchyMarker],
    blocks: &[ParsedBlock],
    map: &HierarchyMap,
    group: &GroupProfile,
) -> Result<EditionAstCtvPoint, EditionTimelineError> {
    let prov = parse_timeline_provenance(provenance, "ctv")?;
    let expression = ExpressionId::parse(provenance).map_err(|error| {
        EditionTimelineError::new("ctv", format!("expression id refused: {error}"))
    })?;
    let admit = admit_snapshot(map, markers, "ctv")?;

    // Presence channel: oracle-synthesized `include` events for every admitted
    // child (the same composition as `law-nexus-inspect`, not expression
    // inheritance). The membership log mirrors this edition's admission.
    let mut membership_log = VersionedMembershipLog::empty();
    for edge in &admit.admitted {
        append_timeline_edge(
            &mut membership_log,
            MembershipChangeKind::Attach,
            &edge.parent,
            &edge.child,
            effect_day,
            prov.clone(),
        )?;
    }
    let mut presence_log = ComponentInExpressionLog::empty();
    for edge in &admit.admitted {
        let event = ComponentInExpressionEvent::try_new(
            "include",
            expression.clone(),
            edge.child.clone(),
            effect_day,
            provenance,
        )
        .map_err(|error| {
            EditionTimelineError::new("ctv", format!("presence event refused: {error}"))
        })?;
        presence_log.append(event).map_err(|error| {
            EditionTimelineError::new("ctv", format!("presence append refused: {error}"))
        })?;
    }
    let (visible, hidden) =
        edition_visibility_counts(&membership_log, &presence_log, &expression, effect_day)?;

    // Text channel: article bodies per the federal_law@v1 ladder, minted through
    // the (locally re-bound) registry map, then resolved per admission CC.
    let articles = collect_article_texts(group, blocks);
    let text_log = build_text_log_from_articles(
        map,
        articles
            .iter()
            .map(|article| ("statya", article.number(), article.title(), article.text())),
        effect_day,
        provenance,
    );
    let admission_ccs: Vec<ComponentConceptId> = admit
        .admitted
        .iter()
        .map(|edge| edge.child.clone())
        .collect();
    let (ctv_resolved, ctv_unknown, ctv_conflict) =
        ctv_resolution_counts(&text_log, &admission_ccs, effect_day);

    Ok(EditionAstCtvPoint {
        edition_number,
        effect_day,
        admitted: visible + hidden,
        visible,
        hidden,
        ctv_resolved,
        ctv_unknown,
        ctv_conflict,
    })
}

/// Aggregate per-edition AST/CTV points into totals.
fn ast_ctv_totals(points: &[EditionAstCtvPoint]) -> EditionAstCtvTotals {
    let mut totals = EditionAstCtvTotals {
        editions: points.len() as u64,
        ..EditionAstCtvTotals::default()
    };
    for point in points {
        totals.admitted = totals.admitted.saturating_add(point.admitted);
        totals.visible = totals.visible.saturating_add(point.visible);
        totals.hidden = totals.hidden.saturating_add(point.hidden);
        totals.ctv_resolved = totals.ctv_resolved.saturating_add(point.ctv_resolved);
        totals.ctv_unknown = totals.ctv_unknown.saturating_add(point.ctv_unknown);
        totals.ctv_conflict = totals.ctv_conflict.saturating_add(point.ctv_conflict);
    }
    totals
}

/// Fail-closed accounting invariants of one AST/CTV payload.
fn verify_ast_ctv_accounting(
    points: &[EditionAstCtvPoint],
    totals: &EditionAstCtvTotals,
) -> Result<(), EditionTimelineError> {
    let mut seen = EditionAstCtvTotals {
        editions: points.len() as u64,
        ..EditionAstCtvTotals::default()
    };
    for point in points {
        if point.visible + point.hidden != point.admitted {
            return Err(EditionTimelineError::new(
                "accounting",
                "visible + hidden != admitted",
            ));
        }
        seen.admitted = seen.admitted.saturating_add(point.admitted);
        seen.visible = seen.visible.saturating_add(point.visible);
        seen.hidden = seen.hidden.saturating_add(point.hidden);
        seen.ctv_resolved = seen.ctv_resolved.saturating_add(point.ctv_resolved);
        seen.ctv_unknown = seen.ctv_unknown.saturating_add(point.ctv_unknown);
        seen.ctv_conflict = seen.ctv_conflict.saturating_add(point.ctv_conflict);
    }
    if seen != *totals {
        return Err(EditionTimelineError::new(
            "accounting",
            "point totals do not match the aggregate",
        ));
    }
    Ok(())
}

/// Derive the per-edition AST/CTV payload from the materialized wire layer.
///
/// `--ctv` composes with `assembly` (exactly one row) or `timeline` (N rows,
/// folded in ascending order); `chain` has no CTV layer and is refused. The
/// same D764 local re-bind is applied before the text channel mints.
/// Fail-closed: an empty list, an unreadable input, a malformed TSV, a refused
/// wire layer, an undeducible work slug, an unavailable registry/profile, an
/// ungroundable effect day, or a refused fold aborts with no payload.
pub fn build_ast_ctv(cli: &EditionTimelineCli) -> Result<EditionAstCtv, EditionTimelineError> {
    if cli.mode == AssemblyMode::Chain {
        return Err(EditionTimelineError::new(
            "usage",
            "--ctv has no chain layer (expected --mode assembly or --mode timeline)",
        ));
    }
    let tsv = fs::read_to_string(&cli.editions).map_err(|error| {
        EditionTimelineError::new(
            "input-read",
            format!("editions TSV is unreadable: {}", error.kind()),
        )
    })?;
    let mut rows = parse_edition_rows(&tsv)?;
    if rows.is_empty() {
        return Err(EditionTimelineError::new(
            "input-read",
            "edition list is empty",
        ));
    }
    if cli.mode == AssemblyMode::Assembly && rows.len() != 1 {
        return Err(EditionTimelineError::new(
            "usage",
            format!("assembly mode expects exactly 1 row, got {}", rows.len()),
        ));
    }
    rows.sort_by_key(|row| row.edition_number);
    for pair in rows.windows(2) {
        if pair[0].edition_number == pair[1].edition_number {
            return Err(EditionTimelineError::new(
                "usage",
                format!("duplicate edition_number {}", pair[0].edition_number),
            ));
        }
    }

    let group = federal_law_group()?;

    struct Materialized {
        edition_number: u32,
        effect_day: i64,
        provenance: String,
        markers: Vec<HierarchyMarker>,
        blocks: Vec<ParsedBlock>,
    }

    let mut materialized: Vec<Materialized> = Vec::with_capacity(rows.len());
    for row in &rows {
        let bytes = fs::read(&row.cleaned_wire).map_err(|error| {
            EditionTimelineError::new(
                "input-read",
                format!(
                    "cleaned wire for edition {} is unreadable: {}",
                    row.edition_number,
                    error.kind()
                ),
            )
        })?;
        let layer = wire_layer_from_cleaned_wire(&bytes)?;
        let effect_day = edition_effect_day(&row.corpus_path).ok_or_else(|| {
            EditionTimelineError::new(
                "identity",
                format!(
                    "no grounded effect day for edition {} corpus path",
                    row.edition_number
                ),
            )
        })?;
        let provenance = load_expression_id_for_path(&row.corpus_path)
            .unwrap_or_else(|| SYNTHETIC_PROVENANCE.to_owned());
        materialized.push(Materialized {
            edition_number: row.edition_number,
            effect_day,
            provenance,
            markers: layer.markers,
            blocks: layer.blocks,
        });
    }

    let mut map = load_hierarchy_map_for_path(&rows[0].corpus_path).map_err(|error| {
        EditionTimelineError::new("registry", format!("registry map refused: {error}"))
    })?;
    let slug = corpus_work_slug(&rows[0].corpus_path).ok_or_else(|| {
        EditionTimelineError::new(
            "identity",
            "cannot derive a work slug for the historical re-bind".to_owned(),
        )
    })?;
    let marker_sets: Vec<&[HierarchyMarker]> = materialized
        .iter()
        .map(|item| item.markers.as_slice())
        .collect();
    let historical_rebinds = rebind_union_statya(&mut map, &marker_sets, &slug)?;
    let registry_bindings =
        embedded_binding_count_for_path(&rows[0].corpus_path).map_err(|error| {
            EditionTimelineError::new("registry", format!("registry count refused: {error}"))
        })? as u64;

    let mut points = Vec::with_capacity(materialized.len());
    for item in &materialized {
        points.push(build_ast_ctv_point(
            item.edition_number,
            item.effect_day,
            &item.provenance,
            &item.markers,
            &item.blocks,
            &map,
            &group,
        )?);
    }
    let totals = ast_ctv_totals(&points);
    verify_ast_ctv_accounting(&points, &totals)?;
    Ok(EditionAstCtv {
        slug,
        registry_bindings,
        historical_rebinds,
        points,
        totals,
    })
}

/// Render the AST/CTV payload (`edition-ast-ctv/v1`), deterministic and ASCII
/// (non-ASCII payload is escaped as JSON `\uXXXX`).
pub fn render_ast_ctv(ast_ctv: &EditionAstCtv) -> Result<String, EditionTimelineError> {
    let totals = &ast_ctv.totals;
    let mut out = String::with_capacity(1536 + ast_ctv.points.len() * 192);
    out.push_str("{\n");
    let _ = writeln!(out, "  \"schema\": {},", quote_json(AST_CTV_SCHEMA));
    let _ = writeln!(out, "  \"kind\": {},", quote_json(AST_CTV_KIND));
    let _ = writeln!(out, "  \"slug\": {},", quote_json(&ast_ctv.slug));
    let _ = writeln!(
        out,
        "  \"registry_bindings\": {},",
        ast_ctv.registry_bindings
    );
    let _ = writeln!(
        out,
        "  \"historical_rebinds\": {},",
        ast_ctv.historical_rebinds
    );
    let _ = writeln!(out, "  \"editions\": {},", totals.editions);
    out.push_str("  \"totals\": {\n");
    let _ = writeln!(out, "    \"admitted\": {},", totals.admitted);
    let _ = writeln!(out, "    \"visible\": {},", totals.visible);
    let _ = writeln!(out, "    \"hidden\": {},", totals.hidden);
    let _ = writeln!(out, "    \"ctv_resolved\": {},", totals.ctv_resolved);
    let _ = writeln!(out, "    \"ctv_unknown\": {},", totals.ctv_unknown);
    let _ = writeln!(out, "    \"ctv_conflict\": {}", totals.ctv_conflict);
    out.push_str("  },\n");
    out.push_str("  \"per_edition\": [");
    if ast_ctv.points.is_empty() {
        out.push_str("],\n");
    } else {
        out.push('\n');
        for (index, point) in ast_ctv.points.iter().enumerate() {
            let comma = if index + 1 < ast_ctv.points.len() {
                ","
            } else {
                ""
            };
            let _ = writeln!(
                out,
                "    {{\"edition_number\": {}, \"effect_day\": {}, \"admitted\": {}, \"visible\": {}, \"hidden\": {}, \"ctv_resolved\": {}, \"ctv_unknown\": {}, \"ctv_conflict\": {}}}{comma}",
                point.edition_number,
                point.effect_day,
                point.admitted,
                point.visible,
                point.hidden,
                point.ctv_resolved,
                point.ctv_unknown,
                point.ctv_conflict
            );
        }
        out.push_str("  ],\n");
    }
    let _ = writeln!(out, "  \"r1000_status\": {},", quote_json(R1000_STATUS));
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in AST_CTV_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 < AST_CTV_NON_CLAIMS.len() {
            ","
        } else {
            ""
        };
        let _ = writeln!(out, "    {}{comma}", quote_json(claim));
    }
    out.push_str("  ]\n}\n");
    ensure_ascii(&out, "ast-ctv payload")?;
    Ok(out)
}

/// Derive the AST/CTV payload and either emit it (stdout) or write it to
/// `--out`. Mirrors the timeline run path for exit codes and shape.
fn run_ast_ctv(cli: &EditionTimelineCli) -> (u8, String) {
    let ast_ctv = match build_ast_ctv(cli) {
        Ok(value) => value,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    let json = match render_ast_ctv(&ast_ctv) {
        Ok(json) => json,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    match cli.out.as_deref().filter(|value| !value.is_empty()) {
        Some(out) => match fs::write(Path::new(out), json.as_bytes()) {
            Ok(()) => (EXIT_OK, ast_ctv_summary_line(&ast_ctv)),
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

/// One-line human summary for the AST/CTV `--out` write path.
fn ast_ctv_summary_line(ast_ctv: &EditionAstCtv) -> String {
    format!(
        "editions={} admitted={} visible={} hidden={} ctv_resolved={} ctv_unknown={} ctv_conflict={}",
        ast_ctv.totals.editions,
        ast_ctv.totals.admitted,
        ast_ctv.totals.visible,
        ast_ctv.totals.hidden,
        ast_ctv.totals.ctv_resolved,
        ast_ctv.totals.ctv_unknown,
        ast_ctv.totals.ctv_conflict
    )
}

/// Derive the timeline payload and either emit it (stdout) or write it to
/// `--out`. Mirrors the assembly/chain run paths for exit codes and shape.
fn run_timeline(cli: &EditionTimelineCli) -> (u8, String) {
    let timeline = match build_timeline(cli) {
        Ok(timeline) => timeline,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    let json = match render_timeline(&timeline) {
        Ok(json) => json,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    match cli.out.as_deref().filter(|value| !value.is_empty()) {
        Some(out) => match fs::write(Path::new(out), json.as_bytes()) {
            Ok(()) => (EXIT_OK, timeline_summary_line(&timeline)),
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

/// One-line human summary for the timeline `--out` write path.
fn timeline_summary_line(timeline: &EditionTimeline) -> String {
    format!(
        "editions={} drafts={} applied={} quarantined={} drift={} non_monotonic={}",
        timeline.totals.editions,
        timeline.totals.drafts,
        timeline.totals.applied,
        timeline.totals.quarantined,
        timeline.totals.drift,
        timeline.non_monotonic_transitions.len()
    )
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
    if cli.ctv {
        return run_ast_ctv(cli);
    }
    match cli.mode {
        AssemblyMode::Assembly => {}
        AssemblyMode::Chain => return run_chain(cli),
        AssemblyMode::Timeline => return run_timeline(cli),
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

/// Derive the two-edition chain payload and either emit it (stdout) or write
/// it to `--out`. Mirrors the assembly run path for exit codes and output shape.
fn run_chain(cli: &EditionTimelineCli) -> (u8, String) {
    let chain = match build_chain(cli) {
        Ok(chain) => chain,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    let json = match render_chain(&chain) {
        Ok(json) => json,
        Err(error) => return (error.exit_code(), error.to_string()),
    };
    match cli.out.as_deref().filter(|value| !value.is_empty()) {
        Some(out) => match fs::write(Path::new(out), json.as_bytes()) {
            Ok(()) => (EXIT_OK, chain_summary_line(&chain)),
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

/// One-line human summary for the chain `--out` write path.
fn chain_summary_line(chain: &EditionChain) -> String {
    format!(
        "seed={} target={} drafts={} applied_attach={} applied_detach={} quarantined={} drift={}",
        chain.seed_edition,
        chain.target_edition,
        chain.counts.drafts,
        chain.counts.applied_attach,
        chain.counts.applied_detach,
        chain.counts.quarantined,
        chain.counts.drift
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
