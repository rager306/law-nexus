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
//! Boundary (S06): the `assembly` (T01) and `chain` (T02) modes are
//! implemented; the `timeline` mode and the `--ctv` layer are declared in the
//! CLI grammar but fail closed here (T03-T04 fill them in). The crate never
//! re-parses XML — `ln-decode` reconstructs the block stream;
//! `ln-kb-ontology` owns the registry, membership and oracle-diff vocabulary.

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
    AmendmentDraftOp, HierarchyBinding, HierarchyMap, HierarchyMapOutcome, HierarchyMarker,
    admit_membership_proposals, assemble_with_oracle_diff, diff_marker_sets,
    drafts_from_marker_diff, map_hierarchy_marker, marker_from_decode_token, oracle_diff,
    propose_membership_from_markers,
};
use ln_kb_ontology::registry::{
    embedded_binding_count_for_path, load_edition_day_for_path, load_expression_id_for_path,
    load_hierarchy_map_for_path,
};
use ln_temporal::domain::{
    AmendingActId, ComponentConceptId, MembershipChangeKind, StructuralAstNode,
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

/// Maximum characters retained in a bounded error detail (mirrors the S05
/// census consumer).
const MAX_DETAIL_CHARS: usize = 240;

/// Declared assembly mode. [`AssemblyMode::Assembly`] (T01) and
/// [`AssemblyMode::Chain`] (T02) are implemented; `timeline` is accepted by
/// the grammar and fails closed.
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
        return (
            EXIT_USAGE,
            EditionTimelineError::new(
                "usage",
                "--ctv layer is not implemented in this build (T04)".to_owned(),
            )
            .to_string(),
        );
    }
    match cli.mode {
        AssemblyMode::Assembly => {}
        AssemblyMode::Chain => return run_chain(cli),
        AssemblyMode::Timeline => {
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
