//! Read-only `npa-bounds-scan/v1` sibling measurement profile over the T02
//! observation seam (M200-8s4kwq S01/T03, D388 bounds evidence).
//!
//! The accumulator drives [`crate::npa_sweep::walk_and_observe`] — the same
//! deterministic walker and production `ConsultantWordMlBlockDecoder`
//! decode path the corpus sweep uses — and measures, per file:
//!
//! * the direct metrics declared by
//!   `prd/architecture/npa-bounds-scanner-profile.yaml` (document decode
//!   outcome, covering-lexer counts, contour-A capture volumes and span
//!   relations), and
//! * a deterministic lexical-proxy subset, every kind namespaced `proxy_*`
//!   and never treated as a semantic frame or a bound decision.
//!
//! Output is a hand-rolled, closed-schema JSONL (D328/D353 pattern, stdlib
//! only, no serde): bounded histograms with histogram-derived quantile
//! estimates, a bounded top-K outlier-anchor scaffold, a terminal run
//! manifest with source/profile hashes, and no raw legal text — anchors
//! carry relative paths, hashes, and byte spans only (Q3). Numeric bound
//! decisions stay deferred-undefined (profile `runtime_stop`); the
//! unavailable-until-runtime metrics and the unimplemented declared proxy
//! sub-metrics are pinned in the `unavailable` record and drift-checked
//! against the tracked profile by contract tests.

use std::fmt::Write as _;
use std::fs;
use std::io::Write as _;
use std::path::{Path, PathBuf};

use crate::domain::{fingerprint_bytes, ParsedBlock};
use crate::lawref::{capture_lawrefs, LawRef};
use crate::lexer::{self, NpaToken, TokenKind};
use crate::npa_sweep::{walk_and_observe, FileTerminal, SweepObserver};

pub use crate::capture_bounds::{
    arbitrate_pair, on_candidate_limit, span_relation, CandidateLimitOutcome, PairDiagnostic,
    PairOutcome, SpanRelation, CANDIDATE_LIMIT_REACHED, PROPOSED_CANDIDATE_CEILING,
};

/// Exit-code contract reused verbatim from the corpus sweep (same walk /
/// usage / out / root / walk-failure semantics).
pub use crate::npa_sweep::{
    EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_ROOT_MISSING, EXIT_USAGE, EXIT_WALK_FAILED,
};

/// Closed schema tag and version of the aggregate JSONL.
pub const BOUNDS_SCHEMA: &str = "npa-bounds-scan/v1";
pub const BOUNDS_SCHEMA_VERSION: u32 = 1;

/// Schema of the tracked profile the scanner is measured against.
pub const PROFILE_SCHEMA: &str = "law-nexus-npa-bounds-scanner-profile/v1";

/// Bounded top-K scaffold cap: how many outlier anchors each distribution
/// metric retains. This is a bounded-memory scaffold rule, NOT the
/// deferred-undefined `top_k` bound selection (profile `aggregation.top_k`).
pub const TOP_K_SCAFFOLD_CAP: usize = 8;

/// Closed normalized pattern-report labels mapped to the seven production
/// `lawref` pattern ids (the profile's `patterns` list is the label set).
pub const PATTERN_LABELS: [(&str, &str); 7] = [
    ("abbrev-hier-chain", "abbrev-hier-chain"),
    ("amendment-window", "abbrev-amendment-window"),
    ("date-docno", "date-docno-window"),
    ("fullword", "fullword-ref"),
    ("quoted-enum", "quoted-enum"),
    ("range", "range_candidate"),
    ("anaphora", "anaphora_candidate"),
];

/// Unavailable-until-runtime metrics (profile `unavailable_until_runtime`):
/// rendered verbatim in the `unavailable` record and drift-pinned against
/// the tracked profile by contract tests. Never measured here.
pub const UNAVAILABLE_METRICS: [&str; 8] = [
    "true CoordinatingFrame member count",
    "true Cartesian frame expansion cardinality",
    "accepted continues_series hop count",
    "scoped alias candidate count",
    "ContextRequest count and fan-out",
    "memo hit rate and derivation depth",
    "SemanticFieldClaim count per field",
    "context sufficient/partial/conflicting/cycle/limit distributions",
];

/// Profile-declared proxy sub-metrics this scaffold does not implement
/// (rendered verbatim in the `unavailable` record and drift-pinned against
/// the tracked profile). Implementing a subset of the declared proxy menu
/// is allowed; inventing undeclared metrics is not.
pub const DEFERRED_PROXY_SUBMETRICS: [&str; 13] = [
    "block_distance",
    "punctuation_shape",
    "open_close_shape",
    "endpoint_shape",
    "marker_present",
    "owner_proxy_present",
    "overlap_relations",
    "candidate_block_distance",
    "intervening_block_kinds",
    "punctuation_continuity",
    "aliases_per_document",
    "repeated_alias_key_count",
    "block_distance_to_explicit_key_use",
];

/// Closed scaffold limitations rendered in the terminal run manifest.
const LIMITATIONS: [&str; 9] = [
    "npa-bounds-scan/v1 is a [proposed] scaffold (D388): numeric bounds decisions are deferred-undefined",
    "top_k outlier retention is a bounded scaffold cap; top_k selection is deferred-undefined",
    "quantiles are bounded-histogram estimates (containing bucket lower edge), not exact order statistics",
    "fragment-local offsets normalize a document fragment as the plain concatenation of decoded block texts",
    "malformed/unreadable classification probes a second read of failed files only",
    "cross-block tail proxy distance is fixed to the adjacent block (distance=1)",
    "declared proxy sub-metrics listed in the unavailable record are not implemented in this scaffold",
    "ended_at is captured after the walk completes; periodic --out rewrites during a run carry run_status incomplete",
    "document_content_hash anchors are fingerprinted at render time with a bounded probe read of anchor files",
];

/// Fixed serialization order of the nine closed token kinds.
const KINDS: [TokenKind; 9] = [
    TokenKind::Word,
    TokenKind::Abbrev,
    TokenKind::HierNum,
    TokenKind::Date,
    TokenKind::DocNo,
    TokenKind::EnumMarker,
    TokenKind::LawCode,
    TokenKind::Punct,
    TokenKind::Space,
];

/// Closed distribution-metric slots: (metric_kind, namespace, shape).
/// Direct metrics first, then the `proxy_*` subset; the order is the fixed
/// render order and is hashed into the measurement definitions.
const METRIC_DEFS: [(&str, &str, &str); 8] = [
    ("blocks_per_document", "direct", "document-block-count"),
    ("tokens_per_block", "direct", "block-token-count"),
    ("candidates_per_block", "direct", "block-candidate-count"),
    (
        "candidates_per_document",
        "direct",
        "document-candidate-count",
    ),
    (
        "proxy_date_docno_members_per_block",
        "proxy",
        "block-date-docno-pair-count",
    ),
    (
        "proxy_structural_range_blocks_per_block",
        "proxy",
        "block-range-presence",
    ),
    (
        "proxy_alias_surfaces_per_document",
        "proxy",
        "document-alias-surface-count",
    ),
    (
        "proxy_cross_block_tails_per_document",
        "proxy",
        "document-cross-block-tail-count",
    ),
];

const M_BLOCKS_PER_DOC: usize = 0;
const M_TOKENS_PER_BLOCK: usize = 1;
const M_CANDIDATES_PER_BLOCK: usize = 2;
const M_CANDIDATES_PER_DOC: usize = 3;
const M_PROXY_DATE_DOCNO: usize = 4;
const M_PROXY_RANGE: usize = 5;
const M_PROXY_ALIAS: usize = 6;
const M_PROXY_TAILS: usize = 7;
const METRIC_SLOTS: usize = 8;

/// Quantile keys (num/den fractions of the observation count, ceiling rank).
const QUANTILES: [(&str, u64, u64); 5] = [
    ("p50", 1, 2),
    ("p90", 9, 10),
    ("p95", 19, 20),
    ("p99", 99, 100),
    ("p999", 999, 1000),
];

/// Bounded histogram scheme: exact buckets for values `0..=63`, then dyadic
/// ranges up to the overflow bucket `[131072, +inf)` — 76 closed buckets.
const HIST_BUCKETS: usize = 76;
const DYADIC_LABELS: [&str; 12] = [
    "64-127",
    "128-255",
    "256-511",
    "512-1023",
    "1024-2047",
    "2048-4095",
    "4096-8191",
    "8192-16383",
    "16384-32767",
    "32768-65535",
    "65536-131071",
    "131072+",
];
const DYADIC_LOWS: [u64; 12] = [
    64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072,
];

/// The frozen lexical surface the alias proxy counts (profile
/// `alias_surface` observable: the explicit «далее» surface). Frozen data,
/// not code: changing it is a measurement-definition change and moves the
/// measurement definitions hash.
pub const ALIAS_SURFACE_WORD: &str = "далее";

fn kind_index(kind: TokenKind) -> usize {
    KINDS
        .iter()
        .position(|candidate| *candidate == kind)
        .expect("closed TokenKind set")
}

fn pattern_index(label: &str) -> usize {
    PATTERN_LABELS
        .iter()
        .position(|(candidate, _)| *candidate == label)
        .expect("closed pattern label table")
}

fn normalized_pattern_label_or_unmapped(pattern_id: &str) -> Option<&'static str> {
    PATTERN_LABELS
        .iter()
        .find(|(_, id)| *id == pattern_id)
        .map(|(label, _)| *label)
}

fn span_index(relation: SpanRelation) -> usize {
    match relation {
        SpanRelation::Exact => 0,
        SpanRelation::Containment => 1,
        SpanRelation::PartialOverlap => 2,
        SpanRelation::Disjoint => 3,
    }
}

fn bucket_index(value: u64) -> usize {
    if value <= 63 {
        return value as usize;
    }
    let mut index = 64usize;
    let mut high = 127u64;
    while value > high && index < HIST_BUCKETS - 1 {
        high = high * 2 + 1;
        index += 1;
    }
    index
}

fn bucket_label(index: usize) -> &'static str {
    if index <= 63 {
        // Exact numeric buckets 0..=63; the label is the decimal value.
        // The table stays closed and tiny, so a small match arm chain is
        // avoided in favor of a computed static slice.
        EXACT_LABELS[index]
    } else {
        DYADIC_LABELS[index - 64]
    }
}

const EXACT_LABELS: [&str; 64] = [
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16",
    "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32",
    "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48",
    "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63",
];

fn bucket_low_edge(index: usize) -> u64 {
    if index <= 63 {
        index as u64
    } else {
        DYADIC_LOWS[index - 64]
    }
}

/// Normalized report label for a production pattern id (`None` for an id
/// outside the closed seven-pattern canon — counted as `pattern_unmapped`).
pub fn normalized_pattern_label(pattern_id: &str) -> Option<&'static str> {
    normalized_pattern_label_or_unmapped(pattern_id)
}

/// Lexical proxy: number of Date+DocNo adjacency pairs in a token stream —
/// a `Date` token with a `DocNo` token at most two positions ahead,
/// skipping at most one intervening `Space`. Profile
/// `coordinating_act_list` core observable (scaffold: no block distance,
/// punctuation shape, or open/close shape).
pub fn count_date_docno_pairs(tokens: &[NpaToken]) -> u64 {
    let mut pairs = 0u64;
    for index in 0..tokens.len() {
        if tokens[index].kind != TokenKind::Date {
            continue;
        }
        let mut probe = index + 1;
        while probe < tokens.len() && probe <= index + 2 && tokens[probe].kind == TokenKind::Space {
            probe += 1;
        }
        if probe < tokens.len() && probe <= index + 2 && tokens[probe].kind == TokenKind::DocNo {
            pairs += 1;
        }
    }
    pairs
}

/// Lexical proxy: `Word` tokens whose lexeme equals `word` (the frozen
/// `ALIAS_SURFACE_WORD` for the alias observable).
pub fn count_word_surfaces(tokens: &[NpaToken], src: &str, word: &str) -> u64 {
    tokens
        .iter()
        .filter(|token| token.kind == TokenKind::Word && token.lexeme(src) == word)
        .count() as u64
}

/// Lexical proxy: a block "opens" an act-type / list-opening surface when
/// any production capture is a `fullword-ref` or `abbrev-hier-chain`
/// candidate (the current production patterns closest to the profile's
/// act-type/list-opening surface proxy).
pub fn block_opens_list_surface(candidates: &[LawRef]) -> bool {
    candidates.iter().any(|candidate| {
        matches!(
            candidate.pattern_id.as_str(),
            "fullword-ref" | "abbrev-hier-chain"
        )
    })
}

/// Lexical proxy: the first non-`Space` token is a `Date` with a `DocNo`
/// token at most two positions ahead — the profile's cross-block-tail
/// "block beginning with Date+DocNo" observable (scaffold distance = 1).
pub fn block_opens_with_date_docno(tokens: &[NpaToken]) -> bool {
    let mut index = 0usize;
    while index < tokens.len() && tokens[index].kind == TokenKind::Space {
        index += 1;
    }
    if index >= tokens.len() || tokens[index].kind != TokenKind::Date {
        return false;
    }
    let mut probe = index + 1;
    while probe < tokens.len() && probe <= index + 2 && tokens[probe].kind == TokenKind::Space {
        probe += 1;
    }
    probe < tokens.len() && probe <= index + 2 && tokens[probe].kind == TokenKind::DocNo
}

/// Bounded per-observation anchor data retained only while it survives the
/// top-K scaffold (paths and spans, never text).
#[derive(Debug, Clone)]
struct AnchorObs {
    value: u64,
    rel_path: String,
    block_index: Option<u64>,
    frag_start: u64,
    frag_end: u64,
    source: Option<(u64, u64)>,
}

/// Borrowed anchor core built once per observed block/document and cloned
/// into [`AnchorObs`] only on a top-K insert.
#[derive(Debug, Clone, Copy)]
struct AnchorCore<'a> {
    rel_path: &'a str,
    block_index: Option<u64>,
    frag: (u64, u64),
    source: Option<(u64, u64)>,
}

/// One bounded distribution aggregate: count / min / max, a 76-bucket
/// bounded histogram (the quantile sketch), and the top-K outlier anchor
/// scaffold. Never retains all observations (profile `memory_rule`).
#[derive(Debug)]
struct MetricAgg {
    count: u64,
    min: u64,
    max: u64,
    buckets: [u64; HIST_BUCKETS],
    topk: Vec<AnchorObs>,
}

impl Default for MetricAgg {
    fn default() -> Self {
        Self {
            count: 0,
            min: 0,
            max: 0,
            buckets: [0; HIST_BUCKETS],
            topk: Vec::new(),
        }
    }
}

impl MetricAgg {
    fn observe(&mut self, value: u64, core: &AnchorCore) {
        if self.count == 0 || value < self.min {
            self.min = value;
        }
        if self.count == 0 || value > self.max {
            self.max = value;
        }
        self.count += 1;
        self.buckets[bucket_index(value)] += 1;
        let qualifies = self.topk.len() < TOP_K_SCAFFOLD_CAP
            || self.topk.last().is_some_and(|last| value > last.value);
        if qualifies {
            let position = self
                .topk
                .iter()
                .position(|obs| value > obs.value)
                .unwrap_or(self.topk.len());
            self.topk.insert(
                position,
                AnchorObs {
                    value,
                    rel_path: core.rel_path.to_owned(),
                    block_index: core.block_index,
                    frag_start: core.frag.0,
                    frag_end: core.frag.1,
                    source: core.source,
                },
            );
            self.topk.truncate(TOP_K_SCAFFOLD_CAP);
        }
    }

    /// Histogram-derived quantile estimate: the lower edge of the bucket
    /// containing the ceiling rank. Deterministic and bounded; not an
    /// exact order statistic (manifest limitation).
    fn quantile_estimate(&self, num: u64, den: u64) -> Option<u64> {
        if self.count == 0 {
            return None;
        }
        let rank = num
            .saturating_mul(self.count)
            .div_ceil(den)
            .clamp(1, self.count);
        let mut cumulative = 0u64;
        for (index, &bucket) in self.buckets.iter().enumerate() {
            cumulative += bucket;
            if cumulative >= rank {
                return Some(bucket_low_edge(index));
            }
        }
        Some(bucket_low_edge(HIST_BUCKETS - 1))
    }
}

/// Aggregate summary exposed to tests and callers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MetricStat {
    pub count: u64,
    pub min: u64,
    pub max: u64,
}

/// Run metadata the accumulator renders into the header and terminal run
/// manifest. Deterministic per run: the thin CLI stamps `started_at`
/// immediately before the scan and the runner captures `ended_at` after
/// the walk completes; library callers inject fixed values for byte-stable
/// fixture runs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoundsRunMeta {
    /// Verbatim header `label` (the run label, e.g. `fixture-gate`).
    pub label: String,
    /// Corpus root as run (manifest `corpus_root`).
    pub corpus_root: String,
    /// Manifest `source_revision` (`None` renders JSON `null`).
    pub source_revision: Option<String>,
    /// Manifest `rust_toolchain` (`None` renders JSON `null`).
    pub rust_toolchain: Option<String>,
    /// Manifest `started_at` (`None` renders JSON `null`).
    pub started_at: Option<String>,
    /// Manifest `ended_at` (`None` renders JSON `null`).
    pub ended_at: Option<String>,
    /// Manifest `command` (the joined argv of the thin CLI).
    pub command: String,
    /// Manifest `output_artifact` (`stdout` or the `--out` path).
    pub output_artifact: String,
    /// `CONSULTANT_EXPORT_DIR` set-and-non-empty (boolean only — the env
    /// value itself is never rendered).
    pub export_dir_env_set: bool,
}

impl BoundsRunMeta {
    /// Defaults for a `fixture-gate` run over `corpus_root`.
    pub fn new(corpus_root: impl Into<String>) -> Self {
        Self {
            label: "fixture-gate".to_owned(),
            corpus_root: corpus_root.into(),
            source_revision: None,
            rust_toolchain: None,
            started_at: None,
            ended_at: None,
            command: "npa-bounds-scan".to_owned(),
            output_artifact: "stdout".to_owned(),
            export_dir_env_set: false,
        }
    }
}

/// `npa-bounds-scan/v1` measurement accumulator over the observation seam.
/// Read-only over the corpus: it never mutates inputs and never retains
/// block text — only counts, hashes, paths, and byte spans (Q3).
#[derive(Debug)]
pub struct BoundsAcc {
    root: PathBuf,
    meta: BoundsRunMeta,
    files_attempted: u64,
    files_decoded: u64,
    malformed: u64,
    unreadable: u64,
    bytes_observed: u64,
    documents: u64,
    blocks_total: u64,
    tokens_total: u64,
    candidates_total: u64,
    coverage_failures: u64,
    pattern_unmapped: u64,
    kind_hist: [u64; 9],
    pattern_counts: [u64; 7],
    span_counts: [u64; 4],
    metrics: [MetricAgg; METRIC_SLOTS],
}

impl BoundsAcc {
    /// New accumulator for one scan over `root` with `meta` rendered into
    /// the header and terminal manifest.
    pub fn new(root: &Path, meta: BoundsRunMeta) -> Self {
        Self {
            root: root.to_path_buf(),
            meta,
            files_attempted: 0,
            files_decoded: 0,
            malformed: 0,
            unreadable: 0,
            bytes_observed: 0,
            documents: 0,
            blocks_total: 0,
            tokens_total: 0,
            candidates_total: 0,
            coverage_failures: 0,
            pattern_unmapped: 0,
            kind_hist: [0; 9],
            pattern_counts: [0; 7],
            span_counts: [0; 4],
            metrics: std::array::from_fn(|_| MetricAgg::default()),
        }
    }

    /// T01 honesty seam: stamp the terminal `ended_at` after the walk
    /// completes (the runner calls this when the caller did not inject a
    /// fixed clock).
    pub fn set_ended_at(&mut self, ended_at: Option<String>) {
        self.meta.ended_at = ended_at;
    }

    pub fn files_attempted(&self) -> u64 {
        self.files_attempted
    }

    pub fn files_decoded(&self) -> u64 {
        self.files_decoded
    }

    pub fn malformed_count(&self) -> u64 {
        self.malformed
    }

    pub fn unreadable_count(&self) -> u64 {
        self.unreadable
    }

    pub fn documents_total(&self) -> u64 {
        self.documents
    }

    pub fn blocks_total(&self) -> u64 {
        self.blocks_total
    }

    pub fn tokens_total(&self) -> u64 {
        self.tokens_total
    }

    pub fn candidates_total(&self) -> u64 {
        self.candidates_total
    }

    pub fn coverage_failures(&self) -> u64 {
        self.coverage_failures
    }

    pub fn pattern_unmapped(&self) -> u64 {
        self.pattern_unmapped
    }

    pub fn kind_count(&self, kind: TokenKind) -> u64 {
        self.kind_hist[kind_index(kind)]
    }

    /// Count for one normalized pattern label (`0` outside the table).
    pub fn pattern_total(&self, label: &str) -> u64 {
        PATTERN_LABELS
            .iter()
            .position(|(candidate, _)| *candidate == label)
            .map_or(0, |index| self.pattern_counts[index])
    }

    /// Count for one span relation.
    pub fn span_total(&self, relation: SpanRelation) -> u64 {
        self.span_counts[span_index(relation)]
    }

    /// count/min/max for one closed metric kind (`None` when unobserved).
    pub fn metric_stat(&self, name: &str) -> Option<MetricStat> {
        let slot = METRIC_DEFS
            .iter()
            .position(|(metric, _, _)| *metric == name)?;
        let agg = &self.metrics[slot];
        (agg.count > 0).then_some(MetricStat {
            count: agg.count,
            min: agg.min,
            max: agg.max,
        })
    }

    /// Retained outlier anchors for one closed metric kind.
    pub fn metric_anchor_len(&self, name: &str) -> Option<usize> {
        let slot = METRIC_DEFS
            .iter()
            .position(|(metric, _, _)| *metric == name)?;
        Some(self.metrics[slot].topk.len())
    }

    fn observe_metric(&mut self, slot: usize, value: u64, core: &AnchorCore) {
        self.metrics[slot].observe(value, core);
    }

    /// Terminal render: the walk completed, so the run manifest carries the
    /// explicit `run_status:"complete"` (T01).
    pub fn render_jsonl(&self) -> String {
        self.render_jsonl_with("complete")
    }

    /// T01 interruption diagnostic: the current aggregate with the explicit
    /// `run_status:"incomplete"` marker and the clock the metadata actually
    /// holds (production partial rewrites render `ended_at:null` — no
    /// fabricated completion time). Same closed schema, same fifteen lines.
    pub fn render_jsonl_incomplete(&self) -> String {
        self.render_jsonl_with("incomplete")
    }

    /// Render the closed-schema aggregate: fifteen JSON objects, one per
    /// line, in fixed `record_kind` order (header, totals, token kind
    /// histogram, pattern counters, span relations, eight metric records,
    /// unavailable, run manifest). Hand-rolled (D328/D353); no raw sentence
    /// survives as a string value (Q3).
    fn render_jsonl_with(&self, run_status: &str) -> String {
        let mut out = String::with_capacity(16_384);
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"header\",\"schema\":{},\"schema_version\":{},",
                "\"label\":{},\"lifecycle\":\"[diagnostic]\",",
                "\"decoder\":\"ConsultantWordMlBlockDecoder\",",
                "\"lexer\":\"ln_decode::lexer::lex\",",
                "\"contour_a\":\"ln_decode::lawref::capture_lawrefs\",",
                "\"crate\":\"ln-decode\",\"profile_schema\":{},\"profile_hash\":{},",
                "\"non_claims\":[\"official-publication\",\"R070\",\"LawRef\",\"N2-gate\",",
                "\"semantic-frame\",\"bound-decision\"]}}"
            ),
            quote(BOUNDS_SCHEMA),
            BOUNDS_SCHEMA_VERSION,
            quote(&self.meta.label),
            quote(PROFILE_SCHEMA),
            quote(&tracked_profile_hash()),
        );
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"totals\",\"files_attempted\":{},\"files_decoded\":{},",
                "\"malformed\":{},\"unreadable\":{},\"bytes_observed\":{},\"documents\":{},",
                "\"blocks\":{},\"tokens\":{},\"candidates\":{},\"coverage_failures\":{},",
                "\"pattern_unmapped\":{}}}"
            ),
            self.files_attempted,
            self.files_decoded,
            self.malformed,
            self.unreadable,
            self.bytes_observed,
            self.documents,
            self.blocks_total,
            self.tokens_total,
            self.candidates_total,
            self.coverage_failures,
            self.pattern_unmapped,
        );
        let kinds = KINDS
            .iter()
            .map(|kind| {
                format!(
                    "\"{}\":{}",
                    kind.as_str(),
                    self.kind_hist[kind_index(*kind)]
                )
            })
            .collect::<Vec<_>>()
            .join(",");
        let _ = writeln!(out, "{{\"record_kind\":\"token_kind_histogram\",{kinds}}}");
        let mut pattern_pairs = PATTERN_LABELS
            .iter()
            .map(|(label, _)| format!("\"{label}\":{}", self.pattern_counts[pattern_index(label)]))
            .collect::<Vec<_>>();
        pattern_pairs.push(format!("\"pattern_unmapped\":{}", self.pattern_unmapped));
        let _ = writeln!(
            out,
            "{{\"record_kind\":\"candidates_by_pattern\",{}}}",
            pattern_pairs.join(",")
        );
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"span_relations\",\"exact_span_pairs\":{},",
                "\"containment_pairs\":{},\"partial_overlap_pairs\":{},\"disjoint_pairs\":{}}}"
            ),
            self.span_counts[0], self.span_counts[1], self.span_counts[2], self.span_counts[3],
        );
        for (slot, (name, namespace, shape)) in METRIC_DEFS.iter().enumerate() {
            let agg = &self.metrics[slot];
            let histogram = (0..HIST_BUCKETS)
                .map(|index| format!("\"{}\":{}", bucket_label(index), agg.buckets[index]))
                .collect::<Vec<_>>()
                .join(",");
            let quantiles = QUANTILES
                .iter()
                .map(|(key, num, den)| {
                    let estimate = agg
                        .quantile_estimate(*num, *den)
                        .map_or_else(|| "null".to_owned(), |value| value.to_string());
                    format!("\"{key}\":{estimate}")
                })
                .collect::<Vec<_>>()
                .join(",");
            let anchors = agg
                .topk
                .iter()
                .map(|obs| self.anchor_json(name, shape, obs))
                .collect::<Vec<_>>()
                .join(",");
            let _ = writeln!(
                out,
                concat!(
                    "{{\"record_kind\":\"metric\",\"metric_kind\":{},\"namespace\":{},",
                    "\"count\":{},\"min\":{},\"max\":{},\"histogram\":{{{}}},",
                    "\"quantiles\":{{{}}},\"top_k_outlier_anchors\":[{}]}}"
                ),
                quote(name),
                quote(namespace),
                agg.count,
                opt_u64((agg.count > 0).then_some(agg.min)),
                opt_u64((agg.count > 0).then_some(agg.max)),
                histogram,
                quantiles,
                anchors,
            );
        }
        let unavailable = UNAVAILABLE_METRICS
            .iter()
            .map(|item| quote(item))
            .collect::<Vec<_>>()
            .join(",");
        let deferred = DEFERRED_PROXY_SUBMETRICS
            .iter()
            .map(|item| quote(item))
            .collect::<Vec<_>>()
            .join(",");
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"unavailable\",\"metrics\":[{}],",
                "\"deferred_proxy_submetrics\":[{}],\"top_k\":\"deferred-undefined\"}}"
            ),
            unavailable, deferred,
        );
        let limitations = LIMITATIONS
            .iter()
            .map(|item| quote(item))
            .collect::<Vec<_>>()
            .join(",");
        let _ = writeln!(
            out,
            concat!(
                "{{\"record_kind\":\"run_manifest\",\"schema_version\":{},",
                "\"run_status\":{},\"lifecycle\":\"[diagnostic]\",\"started_at\":{},\"ended_at\":{},",
                "\"source_revision\":{},\"scanner_source_hash\":{},",
                "\"scanner_build_profile\":{},\"rust_toolchain\":{},\"corpus_root\":{},",
                "\"observed_file_count\":{},\"observed_bytes\":{},\"success_count\":{},",
                "\"malformed_count\":{},\"unreadable_count\":{},",
                "\"measurement_definitions_hash\":{},\"command\":{},",
                "\"environment_non_secret\":{{\"consultant_export_dir_set\":{}}},",
                "\"output_artifact\":{},\"limitations\":[{}]}}"
            ),
            BOUNDS_SCHEMA_VERSION,
            quote(run_status),
            opt_str(self.meta.started_at.as_deref()),
            opt_str(self.meta.ended_at.as_deref()),
            opt_str(self.meta.source_revision.as_deref()),
            quote(&scanner_source_hash()),
            quote(build_profile()),
            opt_str(self.meta.rust_toolchain.as_deref()),
            quote(&self.meta.corpus_root),
            self.files_attempted,
            self.bytes_observed,
            self.files_decoded,
            self.malformed,
            self.unreadable,
            quote(&measurement_definitions_hash()),
            quote(&self.meta.command),
            self.meta.export_dir_env_set,
            quote(&self.meta.output_artifact),
            limitations,
        );
        out
    }

    /// One anchor object: exactly the profile `anchor_record.fields`, in
    /// profile order. `document_content_hash` fingerprints the anchor file
    /// at render time (bounded: only retained anchors are read); a file
    /// unreadable at render renders the closed sentinel
    /// `unavailable-at-render`. No field ever carries legal text (Q3).
    fn anchor_json(&self, metric_kind: &str, shape: &str, obs: &AnchorObs) -> String {
        let content_hash = match fs::read(self.root.join(&obs.rel_path)) {
            Ok(bytes) => fingerprint_bytes(&bytes),
            Err(_) => "unavailable-at-render".to_owned(),
        };
        format!(
            concat!(
                "{{\"document_relative_path\":{},\"document_content_hash\":{},",
                "\"source_revision\":{},\"block_index\":{},",
                "\"fragment_local_start_byte\":{},\"fragment_local_end_byte\":{},",
                "\"source_span_start_byte\":{},\"source_span_end_byte\":{},",
                "\"metric_kind\":{},\"compact_shape\":{}}}"
            ),
            quote(&obs.rel_path),
            quote(&content_hash),
            opt_str(self.meta.source_revision.as_deref()),
            opt_u64(obs.block_index),
            obs.frag_start,
            obs.frag_end,
            opt_u64(obs.source.map(|span| span.0)),
            opt_u64(obs.source.map(|span| span.1)),
            quote(metric_kind),
            quote(shape),
        )
    }
}

impl SweepObserver for BoundsAcc {
    fn observe_file(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.files_attempted += 1;
        let rel = path
            .strip_prefix(&self.root)
            .unwrap_or(path)
            .to_string_lossy()
            .into_owned();
        match terminal {
            FileTerminal::Decoded => {
                self.files_decoded += 1;
                self.bytes_observed += fs::metadata(path).map_or(0, |meta| meta.len());
                let fragment_len: u64 = blocks.iter().map(|block| block.text().len() as u64).sum();
                let mut doc_candidates = 0u64;
                let mut alias_surfaces = 0u64;
                let mut cross_block_tails = 0u64;
                let mut prev_block_opens_list = false;
                let mut frag_offset = 0u64;
                for (index, block) in blocks.iter().enumerate() {
                    let block_index = index as u64;
                    let text = block.text();
                    let frag_start = frag_offset;
                    let frag_end = frag_start + text.len() as u64;
                    frag_offset = frag_end;
                    let source = block.source_location().span();
                    let core = AnchorCore {
                        rel_path: &rel,
                        block_index: Some(block_index),
                        frag: (frag_start, frag_end),
                        source: Some((source.start() as u64, source.end() as u64)),
                    };
                    // Covering lexer: kind census + covering-concatenation
                    // invariant (fixture acceptance: token concatenation
                    // equals every decoded block text).
                    let tokens = lexer::lex(text);
                    self.tokens_total += tokens.len() as u64;
                    let mut covered = String::with_capacity(text.len());
                    for token in &tokens {
                        covered.push_str(token.lexeme(text));
                        self.kind_hist[kind_index(token.kind)] += 1;
                    }
                    if covered != text {
                        self.coverage_failures += 1;
                    }
                    self.observe_metric(M_TOKENS_PER_BLOCK, tokens.len() as u64, &core);
                    // Contour-A captures through the production API.
                    let candidates = capture_lawrefs(text);
                    let candidates = candidates.captures();
                    self.candidates_total += candidates.len() as u64;
                    doc_candidates += candidates.len() as u64;
                    for candidate in candidates {
                        match normalized_pattern_label_or_unmapped(&candidate.pattern_id) {
                            Some(label) => self.pattern_counts[pattern_index(label)] += 1,
                            None => self.pattern_unmapped += 1,
                        }
                    }
                    for left in 0..candidates.len() {
                        for right in (left + 1)..candidates.len() {
                            let a = candidates[left].span;
                            let b = candidates[right].span;
                            let relation =
                                span_relation((a.start(), a.end()), (b.start(), b.end()));
                            self.span_counts[span_index(relation)] += 1;
                        }
                    }
                    self.observe_metric(M_CANDIDATES_PER_BLOCK, candidates.len() as u64, &core);
                    // Namespaced lexical proxies (never semantic frames).
                    let date_docno_pairs = count_date_docno_pairs(&tokens);
                    self.observe_metric(M_PROXY_DATE_DOCNO, date_docno_pairs, &core);
                    let has_range = candidates
                        .iter()
                        .any(|candidate| candidate.pattern_id == "range_candidate");
                    self.observe_metric(M_PROXY_RANGE, u64::from(has_range), &core);
                    alias_surfaces += count_word_surfaces(&tokens, text, ALIAS_SURFACE_WORD);
                    if prev_block_opens_list && block_opens_with_date_docno(&tokens) {
                        cross_block_tails += 1;
                    }
                    prev_block_opens_list = block_opens_list_surface(candidates);
                    self.blocks_total += 1;
                }
                let doc_core = AnchorCore {
                    rel_path: &rel,
                    block_index: None,
                    frag: (0, fragment_len),
                    source: None,
                };
                self.observe_metric(M_BLOCKS_PER_DOC, blocks.len() as u64, &doc_core);
                self.observe_metric(M_CANDIDATES_PER_DOC, doc_candidates, &doc_core);
                self.observe_metric(M_PROXY_ALIAS, alias_surfaces, &doc_core);
                self.observe_metric(M_PROXY_TAILS, cross_block_tails, &doc_core);
                self.documents += 1;
            }
            FileTerminal::Failed => {
                // The seam merges read and decode failures into one atomic
                // `Failed`; classify with a bounded probe read of failed
                // files only: readable-but-undecodable is malformed, an
                // unreadable file is unreadable.
                if fs::read(path).is_ok() {
                    self.malformed += 1;
                } else {
                    self.unreadable += 1;
                }
            }
        }
    }
}

/// Path of the tracked scanner profile (repo-relative from the crate dir —
/// the same `CARGO_MANIFEST_DIR/../..` join the tracked corpus tests use).
pub fn tracked_profile_path() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("prd")
        .join("architecture")
        .join("npa-bounds-scanner-profile.yaml")
}

/// Fingerprint of the tracked profile bytes (manifest `profile_hash`);
/// `unavailable` when the profile is not present in this checkout.
pub fn tracked_profile_hash() -> String {
    fs::read(tracked_profile_path())
        .map(|bytes| fingerprint_bytes(&bytes))
        .unwrap_or_else(|_| "unavailable".to_owned())
}

/// Fingerprint over the scanner implementation source itself, embedded at
/// compile time, so evidence binds to the exact scanner code that ran.
fn scanner_source_hash() -> String {
    static SCANNER_SOURCE_BYTES: &[u8] = include_bytes!("npa_bounds.rs");
    fingerprint_bytes(SCANNER_SOURCE_BYTES)
}

/// Compile-time build profile (`debug`/`release`), `unknown` when cargo
/// does not expose it to rustc.
fn build_profile() -> &'static str {
    match option_env!("PROFILE") {
        Some("release") => "release",
        Some("debug") => "debug",
        _ => "unknown",
    }
}

/// Canonical serialization of the closed measurement definitions (metric
/// slots, pattern table, histogram scheme, quantile keys, span relations,
/// scaffold cap) — fingerprinted into the manifest so any definition drift
/// moves the hash.
fn measurement_definitions() -> String {
    let mut defs = String::new();
    let _ = writeln!(defs, "schema={BOUNDS_SCHEMA}/{BOUNDS_SCHEMA_VERSION}");
    let kinds = KINDS
        .iter()
        .map(|kind| kind.as_str())
        .collect::<Vec<_>>()
        .join(",");
    let _ = writeln!(defs, "kinds={kinds}");
    let patterns = PATTERN_LABELS
        .iter()
        .map(|(label, id)| format!("{label}:{id}"))
        .collect::<Vec<_>>()
        .join(",");
    let _ = writeln!(defs, "patterns={patterns}");
    let metrics = METRIC_DEFS
        .iter()
        .map(|(name, namespace, shape)| format!("{name}:{namespace}:{shape}"))
        .collect::<Vec<_>>()
        .join(",");
    let _ = writeln!(defs, "metrics={metrics}");
    let buckets = (0..64)
        .map(|value| value.to_string())
        .chain(DYADIC_LABELS.iter().map(|label| (*label).to_owned()))
        .collect::<Vec<_>>()
        .join(",");
    let _ = writeln!(defs, "histogram={buckets}");
    let quantiles = QUANTILES
        .iter()
        .map(|(key, _, _)| *key)
        .collect::<Vec<_>>()
        .join(",");
    let _ = writeln!(defs, "quantiles={quantiles}");
    let _ = writeln!(
        defs,
        "span_relations=exact,containment,partial_overlap,disjoint"
    );
    let _ = writeln!(defs, "top_k_scaffold_cap={TOP_K_SCAFFOLD_CAP}");
    let _ = writeln!(defs, "alias_surface_word={ALIAS_SURFACE_WORD}");
    defs
}

fn measurement_definitions_hash() -> String {
    fingerprint_bytes(measurement_definitions().as_bytes())
}

/// Everything the thin binary prints and exits with after one scan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoundsRun {
    pub exit_code: u8,
    /// Rendered aggregate; `None` on fatal error paths (nothing to print).
    pub jsonl: Option<String>,
    /// `true` when `jsonl` belongs on stdout (no usable `--out`).
    pub to_stdout: bool,
    /// Counts line or failure note for stderr — counts and paths only,
    /// never payload bytes or block text (Q3).
    pub stderr: String,
    /// Count-only progress heartbeats captured during the walk
    /// (`scanned=<n>`; empty when `--progress` was not given).
    pub progress_lines: Vec<String>,
    /// Number of periodic atomic partial rewrites of `--out` performed
    /// before the terminal write (0 without `--progress` or `--out`).
    pub partial_flushes: u64,
}

/// Parsed argv of the `npa-bounds-scan` binary — stdlib only, no clap.
/// Lives in the domain module (not the bin) so the CLI contract is testable
/// as a library function.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoundsCli {
    /// Explicit scan root (an existing tree of `*.xml`). `None` resolves
    /// the default export root, where absence is skip-mode.
    pub root: Option<String>,
    /// Aggregate output path; `None` sends the JSONL to stdout.
    pub out: Option<String>,
    /// Cap on XML files, applied after the deterministic sort; `0` is a
    /// valid empty scan.
    pub limit: Option<u64>,
    /// Verbatim header run label; defaults to `fixture-gate`.
    pub label: String,
    /// Manifest `source_revision` (operator-supplied evidence identity).
    pub source_revision: Option<String>,
    /// Manifest `rust_toolchain` (operator-supplied evidence identity).
    pub rust_toolchain: Option<String>,
    /// Manifest `started_at` (set by the thin CLI clock, fixed by tests).
    pub started_at: Option<String>,
    /// Manifest `ended_at` (set by the thin CLI clock, fixed by tests).
    pub ended_at: Option<String>,
    /// Manifest `command` (the joined argv as parsed).
    pub command: String,
    /// Heartbeat + periodic partial-flush interval (`--progress <n>`, n ≥ 1):
    /// every n observed files. `None` disables both; a directly constructed
    /// `Some(0)` also disables (the parser never yields it).
    pub progress_every: Option<u64>,
    /// Emit heartbeats to live stderr during the walk. Not parsed from
    /// argv: the thin binary sets this; library runs capture
    /// `progress_lines` without touching the real stderr.
    pub progress_stderr: bool,
}

impl Default for BoundsCli {
    fn default() -> Self {
        Self {
            root: None,
            out: None,
            limit: None,
            label: "fixture-gate".to_owned(),
            source_revision: None,
            rust_toolchain: None,
            started_at: None,
            ended_at: None,
            command: "npa-bounds-scan".to_owned(),
            progress_every: None,
            progress_stderr: false,
        }
    }
}

/// Strict stdlib argv parser: `--root`, `--out`, `--limit`, `--progress`,
/// `--label`, `--source-revision`, `--rust-toolchain`, each with a following
/// value; later occurrences override earlier ones. Unknown flags,
/// positionals, missing values, and non-numeric `--limit`/`--progress`
/// values are usage errors (`--progress 0` included — omit the flag to
/// disable progress).
pub fn parse_bounds_args<I>(args: I) -> Result<BoundsCli, String>
where
    I: IntoIterator<Item = String>,
{
    let args: Vec<String> = args.into_iter().collect();
    let mut cli = BoundsCli::default();
    let mut iter = args.iter().cloned();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => cli.root = Some(next_value(&mut iter, "--root")?),
            "--out" => cli.out = Some(next_value(&mut iter, "--out")?),
            "--label" => cli.label = next_value(&mut iter, "--label")?,
            "--source-revision" => {
                cli.source_revision = Some(next_value(&mut iter, "--source-revision")?)
            }
            "--rust-toolchain" => {
                cli.rust_toolchain = Some(next_value(&mut iter, "--rust-toolchain")?)
            }
            "--limit" => {
                let raw = next_value(&mut iter, "--limit")?;
                let parsed = raw
                    .parse::<u64>()
                    .map_err(|_| format!("--limit expects a non-negative integer, got '{raw}'"))?;
                cli.limit = Some(parsed);
            }
            "--progress" => {
                let raw = next_value(&mut iter, "--progress")?;
                let parsed = raw.parse::<u64>().map_err(|_| {
                    format!("--progress expects a non-negative integer, got '{raw}'")
                })?;
                if parsed == 0 {
                    return Err(
                        "--progress expects a positive integer (omit the flag to disable)"
                            .to_owned(),
                    );
                }
                cli.progress_every = Some(parsed);
            }
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    cli.command = format!("npa-bounds-scan {}", args.join(" "))
        .trim_end()
        .to_owned();
    Ok(cli)
}

fn next_value(iter: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    iter.next()
        .ok_or_else(|| format!("missing value for {flag}"))
}

/// RFC3339 UTC timestamp from the system clock, stdlib only. The thin CLI
/// stamps `started_at` immediately before the scan; the runner stamps
/// `ended_at` after the walk completes (T01 honesty).
pub fn rfc3339_now() -> String {
    let elapsed = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = elapsed.as_secs();
    let (days, rest) = (secs / 86_400, secs % 86_400);
    let (year, month, day) = civil_from_days(days as i64);
    format!(
        "{year:04}-{month:02}-{day:02}T{:02}:{:02}:{:02}Z",
        rest / 3_600,
        (rest % 3_600) / 60,
        rest % 60
    )
}

/// Days-since-epoch to civil date (Howard Hinnant's algorithm; stdlib only).
fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let shifted = days + 719_468;
    let era = if shifted >= 0 {
        shifted
    } else {
        shifted - 146_096
    } / 146_097;
    let day_of_era = (shifted - era * 146_097) as u64;
    let year_of_era =
        (day_of_era - day_of_era / 1_460 + day_of_era / 36_524 - day_of_era / 146_096) / 365;
    let year = year_of_era as i64 + era * 400;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let mp = (5 * day_of_year + 2) / 153;
    let day = (day_of_year - (153 * mp + 2) / 5 + 1) as u32;
    let month = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if month <= 2 { year + 1 } else { year }, month, day)
}

/// Atomic `--out` write (T01): the payload lands at `<out>.tmp` in the same
/// directory and a single rename replaces the published aggregate, so a
/// kill mid-write never tears the file — a reader sees either the previous
/// rewrite or the new one, never a half-written diagnostic.
fn write_out_atomic(out_path: &Path, payload: &str) -> std::io::Result<()> {
    let tmp = PathBuf::from(format!("{}.tmp", out_path.display()));
    let result = fs::write(&tmp, payload).and_then(|()| fs::rename(&tmp, out_path));
    if result.is_err() {
        let _ = fs::remove_file(&tmp);
    }
    result
}

/// T01 interruption seam: atomically rewrite `--out` with the current
/// aggregate and the explicit `run_status:"incomplete"` marker, so an
/// interrupted run leaves a valid closed-schema diagnostic instead of no
/// evidence. The terminal write later replaces it with the complete
/// manifest.
pub fn write_partial_out(out_path: &Path, acc: &BoundsAcc) -> std::io::Result<()> {
    write_out_atomic(out_path, &acc.render_jsonl_incomplete())
}

/// Walk-loop wrapper (T01): forwards every observation to the accumulator
/// and, every `every` files, records a count-only heartbeat and — when an
/// `--out` target is configured — atomically rewrites it as an explicit
/// incomplete diagnostic. Heartbeats never carry paths or payload (Q3).
struct ProgressObserver<'a> {
    inner: &'a mut BoundsAcc,
    every: u64,
    out_path: Option<&'a Path>,
    live_stderr: bool,
    seen: u64,
    progress_lines: Vec<String>,
    partial_flushes: u64,
    flush_error: Option<String>,
}

impl SweepObserver for ProgressObserver<'_> {
    fn observe_file(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.inner.observe_file(path, terminal, blocks);
        if self.every == 0 {
            return;
        }
        self.seen += 1;
        if !self.seen.is_multiple_of(self.every) {
            return;
        }
        self.progress_lines.push(format!("scanned={}", self.seen));
        if self.live_stderr {
            let mut stderr = std::io::stderr().lock();
            let _ = writeln!(stderr, "npa-bounds-scan: scanned={}", self.seen);
            let _ = stderr.flush();
        }
        if let Some(out) = self.out_path {
            match write_partial_out(out, self.inner) {
                Ok(()) => self.partial_flushes += 1,
                Err(err) if self.flush_error.is_none() => {
                    self.flush_error = Some(format!("cannot open --out {}: {err}", out.display()));
                }
                Err(_) => {}
            }
        }
    }
}

/// Library-level scan runner: exactly what the binary does after argv
/// parsing. `default_root` is injected so tests never touch the live
/// `consru_export` corpus; the binary passes
/// [`crate::npa_sweep::default_sweep_root`]. Drives the production walk +
/// decode path through [`BoundsAcc`] as the observation sink. `ended_at` is
/// captured after the walk completes unless the caller injected a fixed
/// clock (T01); `--progress` adds count-only heartbeats and periodic
/// atomic partial rewrites of `--out`.
pub fn run_bounds_scan(cli: &BoundsCli, default_root: &Path) -> BoundsRun {
    let explicit = cli.root.is_some();
    let root = cli
        .root
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_root.to_path_buf());
    let export_dir_env_set = std::env::var("CONSULTANT_EXPORT_DIR")
        .ok()
        .is_some_and(|value| !value.trim().is_empty());
    let meta = BoundsRunMeta {
        label: cli.label.clone(),
        corpus_root: root.to_string_lossy().into_owned(),
        source_revision: cli.source_revision.clone(),
        rust_toolchain: cli.rust_toolchain.clone(),
        started_at: cli.started_at.clone(),
        ended_at: cli.ended_at.clone(),
        command: cli.command.clone(),
        output_artifact: cli.out.clone().unwrap_or_else(|| "stdout".to_owned()),
        export_dir_env_set,
    };

    if !root.is_dir() {
        if explicit {
            return BoundsRun {
                exit_code: EXIT_ROOT_MISSING,
                jsonl: None,
                to_stdout: false,
                stderr: format!("root not found: {}", root.display()),
                progress_lines: Vec::new(),
                partial_flushes: 0,
            };
        }
        // Skip-mode: a checkout without the export still completes with a
        // closed-schema zeroed aggregate (the corpus_role skip pattern).
        // The zero-file walk completed, so the manifest honestly reports a
        // real ended_at and run_status complete (T01).
        let mut acc = BoundsAcc::new(&root, meta);
        if cli.ended_at.is_none() {
            acc.set_ended_at(Some(rfc3339_now()));
        }
        return BoundsRun {
            exit_code: EXIT_OK,
            jsonl: Some(acc.render_jsonl()),
            to_stdout: true,
            stderr: format!("skip: default corpus root absent: {}", root.display()),
            progress_lines: Vec::new(),
            partial_flushes: 0,
        };
    }

    let mut acc = BoundsAcc::new(&root, meta);
    let mut observer = ProgressObserver {
        inner: &mut acc,
        every: cli.progress_every.unwrap_or(0),
        out_path: cli.out.as_deref().map(Path::new),
        live_stderr: cli.progress_stderr,
        seen: 0,
        progress_lines: Vec::new(),
        partial_flushes: 0,
        flush_error: None,
    };
    let walk_result = walk_and_observe(&root, cli.limit, &mut observer);
    let ProgressObserver {
        inner: acc,
        progress_lines,
        partial_flushes,
        flush_error,
        ..
    } = observer;

    if let Err(err) = walk_result {
        return BoundsRun {
            exit_code: EXIT_WALK_FAILED,
            jsonl: None,
            to_stdout: false,
            stderr: format!("walk failed: {err}"),
            progress_lines,
            partial_flushes,
        };
    }

    // T01 honesty: ended_at is captured after the walk completes — not
    // before the scan call — unless a test injected a fixed clock.
    if cli.ended_at.is_none() {
        acc.set_ended_at(Some(rfc3339_now()));
    }
    let stderr = format!(
        concat!(
            "files_attempted={} files_decoded={} malformed={} unreadable={} ",
            "blocks={} candidates={}"
        ),
        acc.files_attempted(),
        acc.files_decoded(),
        acc.malformed_count(),
        acc.unreadable_count(),
        acc.blocks_total(),
        acc.candidates_total(),
    );
    match &cli.out {
        None => BoundsRun {
            exit_code: EXIT_OK,
            jsonl: Some(acc.render_jsonl()),
            to_stdout: true,
            stderr,
            progress_lines,
            partial_flushes,
        },
        Some(out_path) => {
            // A failed periodic rewrite means the --out target is unusable:
            // fail closed with the first error (same exit-3 contract).
            if let Some(message) = flush_error {
                return BoundsRun {
                    exit_code: EXIT_OUT_UNWRITABLE,
                    jsonl: None,
                    to_stdout: false,
                    stderr: message,
                    progress_lines,
                    partial_flushes,
                };
            }
            match write_out_atomic(Path::new(out_path), &acc.render_jsonl()) {
                Ok(()) => BoundsRun {
                    exit_code: EXIT_OK,
                    jsonl: None,
                    to_stdout: false,
                    stderr,
                    progress_lines,
                    partial_flushes,
                },
                Err(err) => BoundsRun {
                    exit_code: EXIT_OUT_UNWRITABLE,
                    jsonl: None,
                    to_stdout: false,
                    stderr: format!("cannot open --out {out_path}: {err}"),
                    progress_lines,
                    partial_flushes,
                },
            }
        }
    }
}

/// Closed-key reader over rendered output: every line must parse as one
/// JSON object, carry a known `record_kind`, and stay inside that record's
/// key allowlist. Any unexpected key fails closed. (Same D328 char-cursor
/// pattern as `npa_sweep`; kept local because that reader is private and
/// `npa_sweep.rs` is outside this task's file set.)
pub fn validate_bounds_jsonl(output: &str) -> Result<(), String> {
    for (index, line) in output.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let parsed = scan_jsonl_line(line)
            .map_err(|err| format!("npa-bounds-scan line {}: {err}", index + 1))?;
        let Some(record_kind) = parsed.record_kind.as_deref() else {
            return Err(format!(
                "npa-bounds-scan line {}: missing record_kind",
                index + 1
            ));
        };
        for key in &parsed.keys {
            let allowed = match record_kind {
                "header" => HEADER_KEYS.contains(&key.as_str()),
                "totals" => TOTALS_KEYS.contains(&key.as_str()),
                "token_kind_histogram" => {
                    key == "record_kind" || KINDS.iter().any(|kind| kind.as_str() == key)
                }
                "candidates_by_pattern" => {
                    key == "record_kind"
                        || PATTERN_LABELS.iter().any(|(label, _)| *label == key)
                        || key == "pattern_unmapped"
                }
                "span_relations" => SPAN_KEYS.contains(&key.as_str()),
                "metric" => METRIC_KEYS.contains(&key.as_str()),
                "unavailable" => UNAVAILABLE_KEYS.contains(&key.as_str()),
                "run_manifest" => MANIFEST_KEYS.contains(&key.as_str()),
                other => {
                    return Err(format!(
                        "npa-bounds-scan line {}: unknown record_kind '{other}'",
                        index + 1
                    ))
                }
            };
            if !allowed {
                return Err(format!(
                    "npa-bounds-scan line {}: unexpected key '{key}' for record_kind '{record_kind}'",
                    index + 1
                ));
            }
        }
    }
    Ok(())
}

const HEADER_KEYS: [&str; 12] = [
    "record_kind",
    "schema",
    "schema_version",
    "label",
    "lifecycle",
    "decoder",
    "lexer",
    "contour_a",
    "crate",
    "profile_schema",
    "profile_hash",
    "non_claims",
];
const TOTALS_KEYS: [&str; 12] = [
    "record_kind",
    "files_attempted",
    "files_decoded",
    "malformed",
    "unreadable",
    "bytes_observed",
    "documents",
    "blocks",
    "tokens",
    "candidates",
    "coverage_failures",
    "pattern_unmapped",
];
const SPAN_KEYS: [&str; 5] = [
    "record_kind",
    "exact_span_pairs",
    "containment_pairs",
    "partial_overlap_pairs",
    "disjoint_pairs",
];
const METRIC_KEYS: [&str; 9] = [
    "record_kind",
    "metric_kind",
    "namespace",
    "count",
    "min",
    "max",
    "histogram",
    "quantiles",
    "top_k_outlier_anchors",
];
const UNAVAILABLE_KEYS: [&str; 4] = [
    "record_kind",
    "metrics",
    "deferred_proxy_submetrics",
    "top_k",
];
const MANIFEST_KEYS: [&str; 21] = [
    "record_kind",
    "schema_version",
    "run_status",
    "lifecycle",
    "started_at",
    "ended_at",
    "source_revision",
    "scanner_source_hash",
    "scanner_build_profile",
    "rust_toolchain",
    "corpus_root",
    "observed_file_count",
    "observed_bytes",
    "success_count",
    "malformed_count",
    "unreadable_count",
    "measurement_definitions_hash",
    "command",
    "environment_non_secret",
    "output_artifact",
    "limitations",
];

/// Minimal JSON string escaper for the hand-rolled writer: quotes,
/// backslash, and control characters only; legal UTF-8 passes verbatim.
fn quote(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if (ch as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", ch as u32);
            }
            ch => out.push(ch),
        }
    }
    out.push('"');
    out
}

fn opt_str(value: Option<&str>) -> String {
    value.map_or_else(|| "null".to_owned(), quote)
}

fn opt_u64(value: Option<u64>) -> String {
    value.map_or_else(|| "null".to_owned(), |value| value.to_string())
}

/// Top-level keys of one JSON object line, plus its `record_kind` if
/// present.
struct LineKeys {
    keys: Vec<String>,
    record_kind: Option<String>,
}

/// Char cursor for the closed-key reader (stdlib only, D328 pattern).
struct Cursor<'a> {
    src: std::str::Chars<'a>,
}

impl Cursor<'_> {
    fn peek(&mut self) -> Option<char> {
        self.src.clone().next()
    }

    fn bump(&mut self) -> Option<char> {
        self.src.next()
    }

    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(' ') | Some('\t') | Some('\r')) {
            self.bump();
        }
    }

    fn expect(&mut self, want: char) -> Result<(), String> {
        match self.bump() {
            Some(ch) if ch == want => Ok(()),
            other => Err(format!("expected '{want}', found {other:?}")),
        }
    }

    fn read_string(&mut self) -> Result<String, String> {
        self.expect('"')?;
        let mut value = String::new();
        loop {
            match self.bump() {
                None => return Err("unterminated JSON string".to_owned()),
                Some('"') => return Ok(value),
                Some('\\') => match self.bump() {
                    Some('n') => value.push('\n'),
                    Some('t') => value.push('\t'),
                    Some('r') => value.push('\r'),
                    Some('b') => value.push('\u{8}'),
                    Some('f') => value.push('\u{c}'),
                    Some('/') | Some('\\') | Some('"') => {}
                    Some('u') => {
                        for _ in 0..4 {
                            self.bump();
                        }
                    }
                    other => return Err(format!("bad JSON escape {other:?}")),
                },
                Some(ch) => value.push(ch),
            }
        }
    }

    fn read_word(&mut self) -> Result<String, String> {
        let mut word = String::new();
        while matches!(self.peek(), Some(ch) if ch.is_ascii_alphabetic()) {
            word.push(self.bump().expect("peeked char"));
        }
        if word.is_empty() {
            return Err("expected a JSON literal".to_owned());
        }
        Ok(word)
    }

    fn expect_literal(&mut self, want: &str) -> Result<(), String> {
        let word = self.read_word()?;
        if word == want {
            Ok(())
        } else {
            Err(format!("bad JSON literal '{word}'"))
        }
    }

    fn skip_value(&mut self) -> Result<(), String> {
        self.skip_ws();
        match self.peek() {
            Some('"') => self.read_string().map(|_| ()),
            Some('{') => {
                self.bump();
                self.skip_container('}', true)
            }
            Some('[') => {
                self.bump();
                self.skip_container(']', false)
            }
            Some('-') | Some('0'..='9') => {
                while matches!(self.peek(), Some(ch) if ch.is_ascii_digit() || matches!(ch, '-' | '+' | '.' | 'e' | 'E'))
                {
                    self.bump();
                }
                Ok(())
            }
            Some('t') => self.expect_literal("true"),
            Some('f') => self.expect_literal("false"),
            Some('n') => self.expect_literal("null"),
            other => Err(format!("unexpected JSON value start {other:?}")),
        }
    }

    fn skip_container(&mut self, close: char, is_object: bool) -> Result<(), String> {
        self.skip_ws();
        if self.peek() == Some(close) {
            self.bump();
            return Ok(());
        }
        loop {
            self.skip_ws();
            if is_object {
                self.read_string()?;
                self.skip_ws();
                self.expect(':')?;
                self.skip_value()?;
            } else if self.peek() == Some(close) {
                self.bump();
                return Ok(());
            } else {
                self.skip_value()?;
            }
            self.skip_ws();
            match self.bump() {
                Some(',') => continue,
                Some(ch) if ch == close => return Ok(()),
                other => return Err(format!("expected ',' or '{close}', found {other:?}")),
            }
        }
    }
}

fn scan_jsonl_line(line: &str) -> Result<LineKeys, String> {
    let mut cursor = Cursor { src: line.chars() };
    cursor.skip_ws();
    cursor.expect('{')?;
    let mut keys = Vec::new();
    let mut record_kind = None;
    cursor.skip_ws();
    if cursor.peek() == Some('}') {
        cursor.bump();
        if cursor.bump().is_some() {
            return Err("trailing content after object".to_owned());
        }
        return Ok(LineKeys { keys, record_kind });
    }
    loop {
        cursor.skip_ws();
        let key = cursor.read_string()?;
        keys.push(key.clone());
        cursor.skip_ws();
        cursor.expect(':')?;
        if key == "record_kind" {
            cursor.skip_ws();
            let value = cursor
                .read_string()
                .map_err(|_| "record_kind must be a string".to_owned())?;
            record_kind = Some(value);
        } else {
            cursor.skip_value()?;
        }
        cursor.skip_ws();
        match cursor.bump() {
            Some(',') => continue,
            Some('}') => break,
            other => return Err(format!("expected ',' or '}}', found {other:?}")),
        }
    }
    if cursor.bump().is_some() {
        return Err("trailing content after object".to_owned());
    }
    Ok(LineKeys { keys, record_kind })
}
