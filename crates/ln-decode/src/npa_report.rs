//! M211 S04 T05: end-to-end NPA classification runner and the canonical
//! `npa-integration-report/v1` (ADR-0029, D519/D620).
//!
//! The runner drives the full chain over the mandatory frozen seed
//! (`typed-parity-fixture.tsv` fragments):
//! `npa_typed::scan_typed_diagnosed` ->
//! `local_grammar::extract_act_list_frames_from_typed` ->
//! `npa_link::build_linked_document` -> `npa_classify::classify_members`,
//! and diffs the classification against the tracked Python differential
//! reference (`classification-parity-fixture.tsv`, D519/D621). It
//! re-renders the canonical JSON tree through the shared
//! `npa_wire::{Json, render_json}` (D622) instead of inventing a second
//! serializer, and it never mutates a frozen surface.
//!
//! The report keeps two **separate** planes:
//!
//! * `correctness` — classification rows (lemma/bucket/verdict/graph/
//!   identity_key) and typed-detection agreement, each metric carrying an
//!   explicit numerator/denominator; a zero denominator is `not-measured`,
//!   never 0/0 or a perfect 1.
//! * `refusal` — fail-closed diagnostic counters, each with its own
//!   opportunity denominator.
//!
//! The optional corpus mode reuses `npa_sweep::walk_and_observe`. When no
//! default root exists the run is an explicit `skipped` (exit 0), never a
//! failure. The fixture itself is mandatory: a missing source is fatal and
//! fail-closed. No completeness claim is derived from counts or hashes
//! (INV-22); every output is `derived`/`[proposed]`.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use crate::domain::ParsedBlock;
use crate::local_grammar::{self, FrameDiagnostic};
use crate::npa_classify::{self, ClassificationDiagnostic};
use crate::npa_link::{self, LinkDiagnostic};
use crate::npa_sweep::{walk_and_observe, FileTerminal, SweepObserver};
use crate::npa_typed;
use crate::npa_wire::{render_json, Json};

pub use crate::npa_sweep::{
    EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_ROOT_MISSING, EXIT_USAGE, EXIT_WALK_FAILED,
};

/// Closed schema tag of the integration report (D620).
pub const INTEGRATION_SCHEMA: &str = "npa-integration-report/v1";
/// Integer schema version of [`INTEGRATION_SCHEMA`].
pub const INTEGRATION_SCHEMA_VERSION: u32 = 1;
/// Default `label` when `--label` is omitted.
pub const DEFAULT_LABEL: &str = "npa-integration";

// ── measured metrics ───────────────────────────────────────────────────────

/// Measurement status of one ratio. A zero denominator yields
/// [`MetricStatus::NotMeasured`], never 0 and never a perfect 1 (D519).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MetricStatus {
    Measured,
    NotMeasured,
}

impl MetricStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Measured => "measured",
            Self::NotMeasured => "not-measured",
        }
    }
}

/// One published metric: explicit `numerator`/`denominator` plus status.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Metric {
    pub numerator: u64,
    pub denominator: u64,
    pub status: MetricStatus,
}

impl Metric {
    pub const NOT_MEASURED: Metric = Metric {
        numerator: 0,
        denominator: 0,
        status: MetricStatus::NotMeasured,
    };
}

/// Build a metric; a zero denominator is `not-measured` and drops the
/// numerator to 0 (there is nothing correct to count).
pub const fn measured_metric(numerator: u64, denominator: u64) -> Metric {
    if denominator == 0 {
        Metric::NOT_MEASURED
    } else {
        Metric {
            numerator,
            denominator,
            status: MetricStatus::Measured,
        }
    }
}

fn metric_json(metric: Metric) -> Json {
    let value = match metric.status {
        MetricStatus::Measured => Json::Str(format!("{}/{}", metric.numerator, metric.denominator)),
        MetricStatus::NotMeasured => Json::Null,
    };
    Json::obj(vec![
        ("numerator", Json::Int(metric.numerator as i64)),
        ("denominator", Json::Int(metric.denominator as i64)),
        ("status", Json::Str(metric.status.as_str().to_owned())),
        ("value", value),
    ])
}

// ── planes ─────────────────────────────────────────────────────────────────

/// Classification differential against the tracked Python reference.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ClassificationDiff {
    pub rows: u64,
    pub frozen_rows: u64,
    pub synthetic_rows: u64,
    pub matching: u64,
    pub wrong: u64,
    pub missing: u64,
    pub extra: u64,
    pub lemma_ok: u64,
    pub bucket_ok: u64,
    pub verdict_ok: u64,
    pub graph_ok: u64,
    pub identity_key_ok: u64,
}

/// Typed detection agreement with the frozen `typed-parity-fixture.tsv`.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct DetectionDiff {
    pub reference_rows: u64,
    pub predicted_rows: u64,
    pub matching: u64,
    pub wrong: u64,
    pub missing: u64,
    pub extra: u64,
}

/// Correctness plane: the two differential sub-planes, never averaged.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CorrectnessPlane {
    pub classification: ClassificationDiff,
    pub detection: DetectionDiff,
}

/// Refusal plane: fail-closed diagnostic counters plus their opportunity
/// denominators.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RefusalPlane {
    pub documents: u64,
    pub frames: u64,
    pub members: u64,
    pub open_series_without_head: u64,
    pub incompatible_series_head: u64,
    pub type_not_inherited: u64,
    pub head_family_carry_refused: u64,
    pub alias_without_declaration: u64,
    pub head_unavailable: u64,
    pub frame_member_limit_reached: u64,
    pub conflicting_frames_retained: u64,
    pub owner_unresolved: u64,
    pub grammar_contract_refused: u64,
    pub type_unresolved: u64,
    pub type_missing: u64,
    pub unknown_kind: u64,
    pub span_invalid: u64,
}

impl RefusalPlane {
    fn note_link(&mut self, diagnostic: LinkDiagnostic) {
        match diagnostic {
            LinkDiagnostic::OpenSeriesWithoutHead => self.open_series_without_head += 1,
            LinkDiagnostic::IncompatibleSeriesHead => self.incompatible_series_head += 1,
            LinkDiagnostic::TypeNotInherited => self.type_not_inherited += 1,
            LinkDiagnostic::HeadFamilyCarryRefused => self.head_family_carry_refused += 1,
            LinkDiagnostic::AliasWithoutDeclaration => self.alias_without_declaration += 1,
            LinkDiagnostic::HeadUnavailable => self.head_unavailable += 1,
        }
    }

    fn note_frame(&mut self, diagnostic: FrameDiagnostic) {
        match diagnostic {
            FrameDiagnostic::FrameMemberLimitReached => self.frame_member_limit_reached += 1,
            FrameDiagnostic::ConflictingFramesRetained => self.conflicting_frames_retained += 1,
            FrameDiagnostic::OwnerUnresolved => self.owner_unresolved += 1,
            FrameDiagnostic::GrammarContractRefused => self.grammar_contract_refused += 1,
            FrameDiagnostic::TypeUnresolved => self.type_unresolved += 1,
        }
    }

    fn note_classification(&mut self, diagnostic: ClassificationDiagnostic) {
        match diagnostic {
            ClassificationDiagnostic::SpanInvalid => self.span_invalid += 1,
            ClassificationDiagnostic::TypeMissing => self.type_missing += 1,
            ClassificationDiagnostic::UnknownKind => self.unknown_kind += 1,
        }
    }
}

/// Optional corpus plane (count-only, `[smoke]`, never a completeness claim).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum CorpusStatus {
    #[default]
    Skipped,
    Measured,
}

impl CorpusStatus {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Skipped => "skipped",
            Self::Measured => "measured",
        }
    }
}

/// Corpus-mode observation aggregate.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CorpusPlane {
    pub status: CorpusStatus,
    pub root: String,
    pub files_attempted: u64,
    pub files_decoded: u64,
    pub files_failed: u64,
    pub blocks: u64,
    pub refusal: RefusalPlane,
}

// ── fixture readers (fail-closed) ──────────────────────────────────────────

fn members_fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-members")
}

fn lawref_fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

#[derive(Debug, Default)]
struct TypedFixture {
    /// doc -> ordered fragment file names.
    docs: BTreeMap<String, Vec<String>>,
    /// doc -> frozen `(date, number, type_name)` reference members.
    typed: BTreeMap<String, Vec<(String, String, String)>>,
}

fn read_typed_fixture(path: &Path) -> Result<TypedFixture, String> {
    let text =
        fs::read_to_string(path).map_err(|e| format!("MISSING SOURCE: {}: {e}", path.display()))?;
    let mut fixture = TypedFixture::default();
    let mut current: Option<String> = None;
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        match cols.first().copied() {
            Some("doc") if cols.len() >= 2 => {
                current = Some(cols[1].to_string());
                fixture.docs.entry(cols[1].to_string()).or_default();
                fixture.typed.entry(cols[1].to_string()).or_default();
            }
            Some("frag") if cols.len() >= 2 => {
                if let Some(cur) = current.as_deref() {
                    if let Some(frags) = fixture.docs.get_mut(cur) {
                        frags.push(cols[1].to_string());
                    }
                }
            }
            Some("typed") if cols.len() >= 4 => {
                if let Some(cur) = current.as_deref() {
                    if let Some(typed) = fixture.typed.get_mut(cur) {
                        typed.push((
                            cols[1].to_string(),
                            cols[2].to_string(),
                            cols[3].to_string(),
                        ));
                    }
                }
            }
            _ => {}
        }
    }
    if fixture.docs.is_empty() {
        return Err("MISSING SOURCE: typed fixture has no documents".to_owned());
    }
    Ok(fixture)
}

struct ReferenceRow {
    kind: String,
    doc: String,
    canon: String,
    body: String,
    lemma: String,
    bucket: String,
    verdict: String,
    graph: String,
    identity_key: String,
}

fn read_classification_reference(path: &Path) -> Result<Vec<ReferenceRow>, String> {
    let text =
        fs::read_to_string(path).map_err(|e| format!("MISSING SOURCE: {}: {e}", path.display()))?;
    let mut rows = Vec::new();
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        if cols.len() != 10 {
            return Err(format!(
                "MISSING SOURCE: malformed classification fixture row ({} columns): {line:?}",
                cols.len()
            ));
        }
        rows.push(ReferenceRow {
            kind: cols[0].to_string(),
            doc: cols[1].to_string(),
            canon: cols[2].to_string(),
            body: cols[3].to_string(),
            lemma: cols[4].to_string(),
            bucket: cols[5].to_string(),
            verdict: cols[6].to_string(),
            graph: cols[7].to_string(),
            identity_key: cols[8].to_string(),
        });
    }
    if rows.is_empty() {
        return Err("MISSING SOURCE: classification fixture has no data rows".to_owned());
    }
    Ok(rows)
}

/// Raw fragment texts for one document, in fixture order. Missing source is
/// fatal (fail-closed), never a silent skip.
fn load_doc_paras(fixture: &TypedFixture, doc: &str) -> Result<Vec<String>, String> {
    let frags = fixture
        .docs
        .get(doc)
        .ok_or_else(|| format!("MISSING SOURCE: {doc} absent from typed fixture"))?;
    if frags.is_empty() {
        return Err(format!("MISSING SOURCE: {doc} has no fragments"));
    }
    let lawref = lawref_fixture_dir();
    frags
        .iter()
        .map(|frag| {
            let path = lawref.join(frag);
            fs::read_to_string(&path)
                .map_err(|e| format!("MISSING SOURCE: {}: {e}", path.display()))
        })
        .collect()
}

/// Python reference convention (D621): raw `npa-lawref/` fragment files
/// concatenated with a single `"\n"`, no trimming.
fn doc_text(fixture: &TypedFixture, doc: &str) -> Result<String, String> {
    Ok(load_doc_paras(fixture, doc)?.join("\n"))
}

// ── fixture analysis ───────────────────────────────────────────────────────

struct Analysis {
    correctness: CorrectnessPlane,
    refusal: RefusalPlane,
}

fn analyze_classification(
    fixture: &TypedFixture,
    rows: &[ReferenceRow],
) -> Result<ClassificationDiff, String> {
    let mut diff = ClassificationDiff::default();
    let mut reference_keys: BTreeSet<(String, String, String, String)> = BTreeSet::new();
    let mut predicted_keys: BTreeSet<(String, String, String, String)> = BTreeSet::new();

    for row in rows {
        diff.rows += 1;
        if row.kind == "synthetic" {
            diff.synthetic_rows += 1;
        } else {
            diff.frozen_rows += 1;
        }
        let text = if row.kind == "synthetic" {
            row.body.clone()
        } else {
            doc_text(fixture, &row.doc)?
        };
        let key = (
            row.kind.clone(),
            row.doc.clone(),
            row.canon.clone(),
            row.body.clone(),
        );
        reference_keys.insert(key.clone());
        predicted_keys.insert(key);

        let classified = npa_classify::classify(&row.canon, &text);
        let mut all_fields = true;
        if classified.lemma == row.lemma {
            diff.lemma_ok += 1;
        } else {
            all_fields = false;
        }
        if classified.bucket.as_str() == row.bucket {
            diff.bucket_ok += 1;
        } else {
            all_fields = false;
        }
        if classified.verdict.as_str() == row.verdict {
            diff.verdict_ok += 1;
        } else {
            all_fields = false;
        }
        if classified.graph.as_str() == row.graph {
            diff.graph_ok += 1;
        } else {
            all_fields = false;
        }
        if classified.identity_key.as_str() == row.identity_key {
            diff.identity_key_ok += 1;
        } else {
            all_fields = false;
        }
        if all_fields {
            diff.matching += 1;
        } else {
            diff.wrong += 1;
        }
    }

    diff.missing = reference_keys.difference(&predicted_keys).count() as u64;
    diff.extra = predicted_keys.difference(&reference_keys).count() as u64;
    Ok(diff)
}

fn analyze_fixture() -> Result<Analysis, String> {
    let fixture = read_typed_fixture(&members_fixture_dir().join("typed-parity-fixture.tsv"))?;
    let rows = read_classification_reference(
        &members_fixture_dir().join("classification-parity-fixture.tsv"),
    )?;

    let classification = analyze_classification(&fixture, &rows)?;

    let mut detection = DetectionDiff::default();
    let mut refusal = RefusalPlane::default();
    let mut reference_keys: BTreeSet<(String, String, String)> = BTreeSet::new();
    let mut predicted_keys: BTreeSet<(String, String, String)> = BTreeSet::new();

    for doc in fixture.docs.keys() {
        let paras = load_doc_paras(&fixture, doc)?;

        // Full chain: typed -> frames -> linked -> classify.
        let (typed, _anchor_diagnostics) = npa_typed::scan_typed_diagnosed(&paras);
        let frames = local_grammar::extract_act_list_frames_from_typed(&paras);
        let linked = npa_link::build_linked_document(&paras);
        let (_members, classification_diagnostics) =
            npa_classify::classify_members(&linked, &paras);

        refusal.documents += 1;
        refusal.frames += frames.len() as u64;
        refusal.members += linked.members.len() as u64;
        for diagnostic in &linked.diagnostics {
            refusal.note_link(*diagnostic);
        }
        for frame in &frames {
            if let Some(diagnostic) = frame.diagnostic {
                refusal.note_frame(diagnostic);
            }
        }
        for diagnostic in &classification_diagnostics {
            refusal.note_classification(*diagnostic);
        }

        // Detection agreement: (date, number) -> type_name, first non-empty
        // wins, mirroring the S02 parity convention.
        let want: BTreeMap<(String, String), String> = fixture
            .typed
            .get(doc)
            .map(|typed| {
                typed
                    .iter()
                    .map(|(date, number, type_name)| {
                        ((date.clone(), number.clone()), type_name.clone())
                    })
                    .collect()
            })
            .unwrap_or_default();
        let mut got: BTreeMap<(String, String), String> = BTreeMap::new();
        for member in typed.iter().filter(|m| !m.type_name.is_empty()) {
            got.entry((member.date.clone(), member.number.clone()))
                .or_insert_with(|| member.type_name.clone());
        }
        for key in want.keys() {
            reference_keys.insert((doc.clone(), key.0.clone(), key.1.clone()));
        }
        for key in got.keys() {
            predicted_keys.insert((doc.clone(), key.0.clone(), key.1.clone()));
        }
        for (key, want_type) in &want {
            match got.get(key) {
                Some(got_type) if got_type == want_type => detection.matching += 1,
                Some(_) => detection.wrong += 1,
                None => detection.missing += 1,
            }
        }
        for key in got.keys() {
            if !want.contains_key(key) {
                detection.extra += 1;
            }
        }
    }

    detection.reference_rows = reference_keys.len() as u64;
    detection.predicted_rows = predicted_keys.len() as u64;

    Ok(Analysis {
        correctness: CorrectnessPlane {
            classification,
            detection,
        },
        refusal,
    })
}

// ── canonical rendering ────────────────────────────────────────────────────

fn classification_json(diff: &ClassificationDiff) -> Json {
    let rows = diff.rows;
    Json::obj(vec![
        (
            "rows",
            Json::obj(vec![
                ("frozen", Json::Int(diff.frozen_rows as i64)),
                ("synthetic", Json::Int(diff.synthetic_rows as i64)),
                ("total", Json::Int(rows as i64)),
            ]),
        ),
        (
            "matching",
            metric_json(measured_metric(diff.matching, rows)),
        ),
        ("wrong", metric_json(measured_metric(diff.wrong, rows))),
        ("missing", metric_json(measured_metric(diff.missing, rows))),
        ("extra", metric_json(measured_metric(diff.extra, rows))),
        ("lemma", metric_json(measured_metric(diff.lemma_ok, rows))),
        ("bucket", metric_json(measured_metric(diff.bucket_ok, rows))),
        (
            "verdict",
            metric_json(measured_metric(diff.verdict_ok, rows)),
        ),
        ("graph", metric_json(measured_metric(diff.graph_ok, rows))),
        (
            "identity_key",
            metric_json(measured_metric(diff.identity_key_ok, rows)),
        ),
    ])
}

fn detection_json(diff: &DetectionDiff) -> Json {
    let reference = diff.reference_rows;
    let predicted = diff.predicted_rows;
    Json::obj(vec![
        ("reference_rows", Json::Int(reference as i64)),
        ("predicted_rows", Json::Int(predicted as i64)),
        (
            "matching",
            metric_json(measured_metric(diff.matching, reference)),
        ),
        ("wrong", metric_json(measured_metric(diff.wrong, reference))),
        (
            "missing",
            metric_json(measured_metric(diff.missing, reference)),
        ),
        ("extra", metric_json(measured_metric(diff.extra, predicted))),
    ])
}

fn correctness_json(correctness: &CorrectnessPlane) -> Json {
    Json::obj(vec![
        (
            "classification",
            classification_json(&correctness.classification),
        ),
        ("detection", detection_json(&correctness.detection)),
    ])
}

fn refusal_json(refusal: &RefusalPlane) -> Json {
    let documents = refusal.documents;
    let frames = refusal.frames;
    let members = refusal.members;
    Json::obj(vec![
        (
            "denominators",
            Json::obj(vec![
                ("documents", Json::Int(documents as i64)),
                ("frames", Json::Int(frames as i64)),
                ("members", Json::Int(members as i64)),
            ]),
        ),
        (
            "OpenSeriesWithoutHead",
            metric_json(measured_metric(refusal.open_series_without_head, documents)),
        ),
        (
            "IncompatibleSeriesHead",
            metric_json(measured_metric(refusal.incompatible_series_head, documents)),
        ),
        (
            "TypeNotInherited",
            metric_json(measured_metric(refusal.type_not_inherited, documents)),
        ),
        (
            "HeadFamilyCarryRefused",
            metric_json(measured_metric(
                refusal.head_family_carry_refused,
                documents,
            )),
        ),
        (
            "AliasWithoutDeclaration",
            metric_json(measured_metric(
                refusal.alias_without_declaration,
                documents,
            )),
        ),
        (
            "HeadUnavailable",
            metric_json(measured_metric(refusal.head_unavailable, documents)),
        ),
        (
            "frame_member_limit_reached",
            metric_json(measured_metric(refusal.frame_member_limit_reached, frames)),
        ),
        (
            "conflicting_frames_retained",
            metric_json(measured_metric(refusal.conflicting_frames_retained, frames)),
        ),
        (
            "owner_unresolved",
            metric_json(measured_metric(refusal.owner_unresolved, frames)),
        ),
        (
            "grammar_contract_refused",
            metric_json(measured_metric(refusal.grammar_contract_refused, frames)),
        ),
        (
            "type_unresolved",
            metric_json(measured_metric(refusal.type_unresolved, frames)),
        ),
        (
            "type_missing",
            metric_json(measured_metric(refusal.type_missing, members)),
        ),
        (
            "unknown_kind",
            metric_json(measured_metric(refusal.unknown_kind, members)),
        ),
        (
            "span_invalid",
            metric_json(measured_metric(refusal.span_invalid, members)),
        ),
    ])
}

fn corpus_json(corpus: &CorpusPlane) -> Json {
    Json::obj(vec![
        ("status", Json::Str(corpus.status.as_str().to_owned())),
        ("root", Json::Str(corpus.root.clone())),
        ("files_attempted", Json::Int(corpus.files_attempted as i64)),
        ("files_decoded", Json::Int(corpus.files_decoded as i64)),
        ("files_failed", Json::Int(corpus.files_failed as i64)),
        ("blocks", Json::Int(corpus.blocks as i64)),
        ("refusal", refusal_json(&corpus.refusal)),
    ])
}

fn limit_rows() -> Vec<Json> {
    vec![
        Json::Str("derived Rust-owned differential report".to_owned()),
        Json::Str("Python reference is differential, not independent gold (D519)".to_owned()),
        Json::Str("no completeness claim from counts or hashes (INV-22)".to_owned()),
    ]
}

fn non_claim_rows() -> Vec<Json> {
    vec![
        Json::Str("Does not measure legal correctness".to_owned()),
        Json::Str("Does not adopt TYPE vocabulary".to_owned()),
        Json::Str("Does not rewrite frozen S01-S04 stores".to_owned()),
        Json::Str("Frozen seed rows only; corpus mode is a bounded smoke".to_owned()),
    ]
}

/// Render the canonical `npa-integration-report/v1` bytes through the shared
/// `npa_wire` tree (`json.dumps(..., indent=2, sort_keys=True) + "\n"`).
/// Byte-deterministic: the same planes render the same string.
pub fn render_integration_report(
    label: &str,
    run_status: &str,
    correctness: &CorrectnessPlane,
    refusal: &RefusalPlane,
    corpus: &CorpusPlane,
) -> String {
    let envelope = Json::obj(vec![
        ("schema", Json::Str(INTEGRATION_SCHEMA.to_owned())),
        (
            "schema_version",
            Json::Int(INTEGRATION_SCHEMA_VERSION as i64),
        ),
        ("label", Json::Str(label.to_owned())),
        ("run_status", Json::Str(run_status.to_owned())),
        ("derived", Json::Bool(true)),
        (
            "lifecycle",
            Json::Arr(vec![Json::Str("proposed".to_owned())]),
        ),
        ("authoritative", Json::Bool(false)),
        ("is_gold", Json::Bool(false)),
        ("not_human", Json::Bool(true)),
        ("not_s03_metrics", Json::Bool(true)),
        ("correctness", correctness_json(correctness)),
        ("refusal", refusal_json(refusal)),
        ("corpus", corpus_json(corpus)),
        ("limits", Json::Arr(limit_rows())),
        ("non_claims", Json::Arr(non_claim_rows())),
    ]);
    let mut out = String::new();
    render_json(&envelope, 0, &mut out);
    out.push('\n');
    out
}

// ── CLI ────────────────────────────────────────────────────────────────────

/// Parsed argv of the `npa-integration-runner` binary.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct IntegrationCli {
    pub root: Option<String>,
    pub out: Option<String>,
    pub limit: Option<u64>,
    pub label: Option<String>,
}

/// Strict stdlib argv parser: `--root`, `--out`, `--limit`, `--label`.
/// Unknown flags, positionals, missing values, and non-numeric limits are
/// usage errors.
pub fn parse_integration_args<I>(args: I) -> Result<IntegrationCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = IntegrationCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => cli.root = Some(next_value(&mut iter, "--root")?),
            "--out" => cli.out = Some(next_value(&mut iter, "--out")?),
            "--label" => cli.label = Some(next_value(&mut iter, "--label")?),
            "--limit" => {
                let raw = next_value(&mut iter, "--limit")?;
                cli.limit =
                    Some(raw.parse().map_err(|_| {
                        format!("--limit expects a non-negative integer, got '{raw}'")
                    })?);
            }
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    Ok(cli)
}

fn next_value(iter: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    iter.next()
        .ok_or_else(|| format!("missing value for {flag}"))
}

/// Everything the thin binary prints and exits with after one run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IntegrationRun {
    pub exit_code: u8,
    /// Rendered report; `None` on fatal paths (nothing valid to print).
    pub json: Option<String>,
    pub to_stdout: bool,
    pub stderr: String,
}

#[derive(Debug, Default)]
struct CorpusObserver {
    files_attempted: u64,
    files_decoded: u64,
    files_failed: u64,
    blocks: u64,
    refusal: RefusalPlane,
}

impl SweepObserver for CorpusObserver {
    fn observe_file(&mut self, _path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.files_attempted += 1;
        match terminal {
            FileTerminal::Decoded => {
                self.files_decoded += 1;
                self.blocks += blocks.len() as u64;
                let paras: Vec<String> =
                    blocks.iter().map(|block| block.text().to_owned()).collect();
                if paras.is_empty() {
                    return;
                }
                let frames = local_grammar::extract_act_list_frames_from_typed(&paras);
                let linked = npa_link::build_linked_document(&paras);
                let (_members, classification_diagnostics) =
                    npa_classify::classify_members(&linked, &paras);
                self.refusal.documents += 1;
                self.refusal.frames += frames.len() as u64;
                self.refusal.members += linked.members.len() as u64;
                for diagnostic in &linked.diagnostics {
                    self.refusal.note_link(*diagnostic);
                }
                for frame in &frames {
                    if let Some(diagnostic) = frame.diagnostic {
                        self.refusal.note_frame(diagnostic);
                    }
                }
                for diagnostic in &classification_diagnostics {
                    self.refusal.note_classification(*diagnostic);
                }
            }
            FileTerminal::Failed => self.files_failed += 1,
        }
    }
}

fn write_atomic(path: &Path, body: &str) -> std::io::Result<()> {
    let tmp = PathBuf::from(format!("{}.tmp", path.display()));
    let result = fs::write(&tmp, body).and_then(|()| fs::rename(&tmp, path));
    if result.is_err() {
        let _ = fs::remove_file(tmp);
    }
    result
}

/// Library-level runner: build the mandatory fixture planes, optionally walk
/// the corpus through the shared `npa_sweep` seam, and render one canonical
/// `npa-integration-report/v1`.
///
/// Failure paths are explicit: a missing fixture source is fatal
/// (`EXIT_WALK_FAILED`, no output), an explicit missing `--root` is
/// `EXIT_ROOT_MISSING`, a walk failure is `EXIT_WALK_FAILED`, and an
/// unwritable `--out` is `EXIT_OUT_UNWRITABLE`. An absent default root with
/// no explicit `--root` is an explicit `skipped` (exit 0), never a fail.
pub fn run_integration_report(cli: &IntegrationCli, default_root: &Path) -> IntegrationRun {
    let analysis = match analyze_fixture() {
        Ok(analysis) => analysis,
        Err(err) => {
            return IntegrationRun {
                exit_code: EXIT_WALK_FAILED,
                json: None,
                to_stdout: false,
                stderr: format!("fixture failure: {err}"),
            }
        }
    };
    let label = cli
        .label
        .clone()
        .unwrap_or_else(|| DEFAULT_LABEL.to_owned());

    let explicit = cli.root.is_some();
    let root = cli
        .root
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_root.to_path_buf());

    let (run_status, corpus) = if !root.is_dir() {
        if explicit {
            return IntegrationRun {
                exit_code: EXIT_ROOT_MISSING,
                json: None,
                to_stdout: false,
                stderr: format!("root not found: {}", root.display()),
            };
        }
        (
            "skipped",
            CorpusPlane {
                status: CorpusStatus::Skipped,
                root: root.to_string_lossy().into_owned(),
                ..CorpusPlane::default()
            },
        )
    } else {
        let mut observer = CorpusObserver::default();
        if let Err(err) = walk_and_observe(&root, cli.limit, &mut observer) {
            return IntegrationRun {
                exit_code: EXIT_WALK_FAILED,
                json: None,
                to_stdout: false,
                stderr: format!("walk failed: {err}"),
            };
        }
        (
            "complete",
            CorpusPlane {
                status: CorpusStatus::Measured,
                root: root.to_string_lossy().into_owned(),
                files_attempted: observer.files_attempted,
                files_decoded: observer.files_decoded,
                files_failed: observer.files_failed,
                blocks: observer.blocks,
                refusal: observer.refusal,
            },
        )
    };

    let body = render_integration_report(
        &label,
        run_status,
        &analysis.correctness,
        &analysis.refusal,
        &corpus,
    );
    let stderr = format!(
        "run_status={run_status} classification_rows={} detection={}/{} refusal_documents={}",
        analysis.correctness.classification.rows,
        analysis.correctness.detection.matching,
        analysis.correctness.detection.reference_rows,
        analysis.refusal.documents,
    );

    match &cli.out {
        None => IntegrationRun {
            exit_code: EXIT_OK,
            json: Some(body),
            to_stdout: true,
            stderr,
        },
        Some(out) => match write_atomic(Path::new(out), &body) {
            Ok(()) => IntegrationRun {
                exit_code: EXIT_OK,
                json: None,
                to_stdout: false,
                stderr,
            },
            Err(err) => IntegrationRun {
                exit_code: EXIT_OUT_UNWRITABLE,
                json: None,
                to_stdout: false,
                stderr: format!("cannot open --out {out}: {err}"),
            },
        },
    }
}
