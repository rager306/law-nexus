//! S04 corpus acceptance: frozen schemas, closed vocabularies and strict
//! fail-closed loading.
//!
//! This module fixes the three S04 artifacts:
//!
//! - the pinned sample manifest (`law-nexus/npa-analysis-corpus-sample/v1`),
//! - the separated acceptance report
//!   (`law-nexus/npa-analysis-corpus-acceptance/v1`),
//! - the text-free adjudication packet
//!   (`law-nexus/npa-analysis-adjudication-packet/v1`).
//!
//! It carries **no** decoded corpus text: every value is a count, a hash, a
//! closed token or a source-relative path. `load`/`validate` refuse invalid
//! JSON, a missing thresholds block, unknown tokens, duplicate entries,
//! `..`/absolute paths and any raw-text-bearing field.
//!
//! Non-claims (M214 S04): the corpus sweep is not a semantic oracle; the
//! semantic section is structural-only (`semantic_reference_status=absent`,
//! no C5 promotion); no accuracy or corpus-breadth claim is made; R1000 stays
//! active/unclosed and M208-wrz6fg stays parked. Count/hash only — no decoded
//! corpus text enters tracked evidence.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::fs;
use std::io::Read;
use std::path::{Component, Path, PathBuf};

use ln_decode::npa_analysis_verify::AnalysisVerifyCode;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::corpus_sample::{self, SampleCandidate, SourceRootKind};

// ------------------------------------------------------------- constants #

/// S04 sample manifest schema.
pub const SAMPLE_SCHEMA: &str = "law-nexus/npa-analysis-corpus-sample/v1";
/// S04 acceptance report schema (also the per-entry JSONL companion).
pub const ACCEPTANCE_SCHEMA: &str = "law-nexus/npa-analysis-corpus-acceptance/v1";
/// S04 adjudication packet schema.
pub const ADJUDICATION_SCHEMA: &str = "law-nexus/npa-analysis-adjudication-packet/v1";

/// Closed lifecycle marker used by every S04 artifact.
pub const LIFECYCLE_BOUNDED: &str = "[bounded]";
/// Owning milestone.
pub const MILESTONE: &str = "M214-es3jvw";
/// Owning slice.
pub const SLICE: &str = "S04";
/// S04 schema revision.
pub const SCHEMA_VERSION: u64 = 1;

/// Declared S04 sample size (§15.1, fixed before the run).
pub const DECLARED_SAMPLE_SIZE: u64 = 400;
/// Declared draw seed (`corpus_sample::DEFAULT_DRAW_SEED`).
pub const DECLARED_DRAW_SEED: u64 = crate::corpus_sample::DEFAULT_DRAW_SEED;
/// Declared tamper-probe subset size.
pub const DECLARED_TAMPER_PROBE_ENTRIES: u64 = 12;
/// Declared run-level peak-memory budget (4 GiB).
pub const DECLARED_RESOURCE_BUDGET_PEAK_BYTES: u64 = 4 * 1024 * 1024 * 1024;
/// Declared run-level wall-time budget (1 hour).
pub const DECLARED_RESOURCE_BUDGET_TOTAL_MS: u64 = 60 * 60 * 1000;
/// Declared minimum verified ratio in parts per million.
pub const DECLARED_MIN_VERIFIED_RATIO_PPM: u64 = 990_000;
/// Declared maximum number of limit events for a `pass`.
pub const DECLARED_MAX_LIMIT_EVENTS: u64 = 0;

/// The semantic section has no reference corpus at S04.
pub const SEMANTIC_REFERENCE_STATUS_ABSENT: &str = "absent";
/// R1000 remains open (D638/D655).
pub const R1000_STATUS_ACTIVE: &str = "active";
/// M208-wrz6fg remains parked (D651).
pub const M208_STATUS_PARKED: &str = "parked";

/// Declared C3 exclusion for the diagnostic S04 sample.
pub const C3_EXCLUSION_NONE: &str = "none (diagnostic sample, not an evaluation holdout)";
/// Declared Consultant source root (repo-relative).
pub const CONSULTANT_ROOT_RELATIVE: &str = "consru_export/consru_export/exports";
/// Declared Garant source root (repo-relative).
pub const GARANT_ROOT_RELATIVE: &str = "law-source/garant";

/// Top-level keys that would re-carry decoded corpus text (§12 H12). `load`
/// refuses any of these anywhere in the document, before deserialization.
pub const FORBIDDEN_TEXT_KEYS: &[&str] = &[
    "text",
    "source_utf8",
    "inline_text",
    "decoded_text",
    "segment_text",
    "raw_text",
    "decoded",
    "body_text",
    "content_text",
    "source_text",
    "block_text",
];

/// Allowed `verify_codes` histogram keys (the closed §8B.4 set).
pub const VERIFY_CODE_TOKENS: &[&str] = &[
    "envelope_structural",
    "seal_mismatch",
    "fragment_hash_mismatch",
    "span_slice_mismatch",
    "source_ref_substitution",
    "relation_ref_missing",
    "relation_substitution",
    "member_ref_missing",
    "context_outcome_mismatch",
    "completion_mismatch",
];

/// Allowed `limit_events` histogram keys.
pub const LIMIT_KIND_TOKENS: &[&str] = &["line_bytes", "records"];

// --------------------------------------------------------------- enums #

/// Declared source-root provider token.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProviderToken {
    /// `consru_export/consru_export/exports` (the full Consultant corpus).
    ConsultantExport,
    /// `law-source/garant` (the separate Garant format).
    Garant,
}

impl ProviderToken {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ConsultantExport => "consultant_export",
            Self::Garant => "garant",
        }
    }

    /// Map the corpus metadata root kind into the schema token.
    pub const fn from_root_kind(kind: SourceRootKind) -> Self {
        match kind {
            SourceRootKind::ConsultantExport => Self::ConsultantExport,
            SourceRootKind::Garant => Self::Garant,
        }
    }

    /// Map the schema token back into the corpus metadata root kind.
    pub const fn to_root_kind(self) -> SourceRootKind {
        match self {
            Self::ConsultantExport => SourceRootKind::ConsultantExport,
            Self::Garant => SourceRootKind::Garant,
        }
    }
}

/// Closed per-entry outcome vocabulary (§15.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EntryOutcome {
    /// Export/read-back/verify all succeeded for this entry.
    VerifiedOk,
    /// The rendered envelope could not be read back.
    ReadBackRefused,
    /// The independent verifier refused the envelope (carries a `VerifyCode`).
    VerifyRefused,
    /// `source_package::capture` refused the bytes.
    DecodeRefused,
    /// `reader_gate::gate_reader` refused the source class.
    GateRefused,
    /// `npa_analysis_records::analyze_document` refused the document.
    AnalysisRefused,
    /// A line exceeded `max_line_bytes`.
    LimitLineBytes,
    /// The record total exceeded `max_records`.
    LimitRecords,
    /// The recomputed content hash disagreed with the pinned manifest.
    ManifestPinMismatch,
}

impl EntryOutcome {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::VerifiedOk => "verified_ok",
            Self::ReadBackRefused => "read_back_refused",
            Self::VerifyRefused => "verify_refused",
            Self::DecodeRefused => "decode_refused",
            Self::GateRefused => "gate_refused",
            Self::AnalysisRefused => "analysis_refused",
            Self::LimitLineBytes => "limit_line_bytes",
            Self::LimitRecords => "limit_records",
            Self::ManifestPinMismatch => "manifest_pin_mismatch",
        }
    }

    /// A non-`verified_ok` outcome is a structural failure.
    pub const fn is_failure(self) -> bool {
        !matches!(self, Self::VerifiedOk)
    }
}

/// Closed limit-kind vocabulary (§15.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LimitKind {
    /// A single emitted line exceeded `max_line_bytes`.
    LineBytes,
    /// The interior record total exceeded `max_records`.
    Records,
}

impl LimitKind {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::LineBytes => "line_bytes",
            Self::Records => "records",
        }
    }
}

/// Closed semantic-adjudication status (§15.4). S04 is structural-only.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AdjudicationStatus {
    /// No semantic adjudication was attempted (S04 default).
    NotAttempted,
    /// Adjudication is deferred to a later horizon.
    Deferred,
    /// No semantic reference corpus exists at this horizon.
    NoReference,
}

impl AdjudicationStatus {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NotAttempted => "not_attempted",
            Self::Deferred => "deferred",
            Self::NoReference => "no_reference",
        }
    }
}

/// Closed aggregate verdict vocabulary (§15.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    /// Every entry verified, no limits, within budget, no overclaim.
    Pass,
    /// No hard failure but a refusal/limit/resource/ratio pressure.
    NeedsAttention,
    /// A hard failure: pin mismatch, verify refusal, tamper false negative,
    /// promotion or a semantic/breadth overclaim.
    Fail,
}

impl Verdict {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pass => "pass",
            Self::NeedsAttention => "needs_attention",
            Self::Fail => "fail",
        }
    }
}

/// Closed verifier-code token mirroring the §8B.4 `AnalysisVerifyCode` set.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VerifyCodeToken {
    EnvelopeStructural,
    SealMismatch,
    FragmentHashMismatch,
    SpanSliceMismatch,
    SourceRefSubstitution,
    RelationRefMissing,
    RelationSubstitution,
    MemberRefMissing,
    ContextOutcomeMismatch,
    CompletionMismatch,
}

impl VerifyCodeToken {
    /// Closed wire token (identical to `AnalysisVerifyCode::as_str`).
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::EnvelopeStructural => "envelope_structural",
            Self::SealMismatch => "seal_mismatch",
            Self::FragmentHashMismatch => "fragment_hash_mismatch",
            Self::SpanSliceMismatch => "span_slice_mismatch",
            Self::SourceRefSubstitution => "source_ref_substitution",
            Self::RelationRefMissing => "relation_ref_missing",
            Self::RelationSubstitution => "relation_substitution",
            Self::MemberRefMissing => "member_ref_missing",
            Self::ContextOutcomeMismatch => "context_outcome_mismatch",
            Self::CompletionMismatch => "completion_mismatch",
        }
    }

    /// Map a live verifier code into the schema token.
    pub const fn from_code(code: AnalysisVerifyCode) -> Self {
        match code {
            AnalysisVerifyCode::EnvelopeStructural => Self::EnvelopeStructural,
            AnalysisVerifyCode::SealMismatch => Self::SealMismatch,
            AnalysisVerifyCode::FragmentHashMismatch => Self::FragmentHashMismatch,
            AnalysisVerifyCode::SpanSliceMismatch => Self::SpanSliceMismatch,
            AnalysisVerifyCode::SourceRefSubstitution => Self::SourceRefSubstitution,
            AnalysisVerifyCode::RelationRefMissing => Self::RelationRefMissing,
            AnalysisVerifyCode::RelationSubstitution => Self::RelationSubstitution,
            AnalysisVerifyCode::MemberRefMissing => Self::MemberRefMissing,
            AnalysisVerifyCode::ContextOutcomeMismatch => Self::ContextOutcomeMismatch,
            AnalysisVerifyCode::CompletionMismatch => Self::CompletionMismatch,
        }
    }

    /// Map the schema token back into the live verifier code.
    pub const fn to_code(self) -> AnalysisVerifyCode {
        match self {
            Self::EnvelopeStructural => AnalysisVerifyCode::EnvelopeStructural,
            Self::SealMismatch => AnalysisVerifyCode::SealMismatch,
            Self::FragmentHashMismatch => AnalysisVerifyCode::FragmentHashMismatch,
            Self::SpanSliceMismatch => AnalysisVerifyCode::SpanSliceMismatch,
            Self::SourceRefSubstitution => AnalysisVerifyCode::SourceRefSubstitution,
            Self::RelationRefMissing => AnalysisVerifyCode::RelationRefMissing,
            Self::RelationSubstitution => AnalysisVerifyCode::RelationSubstitution,
            Self::MemberRefMissing => AnalysisVerifyCode::MemberRefMissing,
            Self::ContextOutcomeMismatch => AnalysisVerifyCode::ContextOutcomeMismatch,
            Self::CompletionMismatch => AnalysisVerifyCode::CompletionMismatch,
        }
    }
}

// ------------------------------------------------------------- structs #

/// Declared-before-run thresholds carried by the sample manifest and copied
/// into the acceptance report (§15.1).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DeclaredThresholds {
    /// Declared sample size (S04: 400).
    pub sample_size: u64,
    /// Declared draw seed (S04: `DEFAULT_DRAW_SEED`).
    pub draw_seed: u64,
    /// Declared tamper-probe subset size.
    pub tamper_probe_entries: u64,
    /// Declared run-level peak-memory budget in bytes.
    pub resource_budget_peak_bytes: u64,
    /// Declared run-level wall-time budget in milliseconds.
    pub resource_budget_total_ms: u64,
    /// Declared minimum verified ratio in parts per million.
    pub min_verified_ratio_ppm: u64,
    /// Declared maximum number of limit events for a `pass`.
    pub max_limit_events: u64,
}

impl DeclaredThresholds {
    /// The frozen S04 declaration.
    pub const fn declared() -> Self {
        Self {
            sample_size: DECLARED_SAMPLE_SIZE,
            draw_seed: DECLARED_DRAW_SEED,
            tamper_probe_entries: DECLARED_TAMPER_PROBE_ENTRIES,
            resource_budget_peak_bytes: DECLARED_RESOURCE_BUDGET_PEAK_BYTES,
            resource_budget_total_ms: DECLARED_RESOURCE_BUDGET_TOTAL_MS,
            min_verified_ratio_ppm: DECLARED_MIN_VERIFIED_RATIO_PPM,
            max_limit_events: DECLARED_MAX_LIMIT_EVENTS,
        }
    }

    /// Fail-closed validation; the S04 declaration is fixed and non-zero.
    pub fn validate(&self) -> Result<(), String> {
        if self.sample_size != DECLARED_SAMPLE_SIZE {
            return Err(format!(
                "declared sample_size must be {DECLARED_SAMPLE_SIZE}, got {}",
                self.sample_size
            ));
        }
        if self.draw_seed != DECLARED_DRAW_SEED {
            return Err(format!(
                "declared draw_seed must be {DECLARED_DRAW_SEED}, got {}",
                self.draw_seed
            ));
        }
        if self.tamper_probe_entries == 0 {
            return Err("declared tamper_probe_entries must be positive".into());
        }
        if self.resource_budget_peak_bytes == 0 || self.resource_budget_total_ms == 0 {
            return Err("declared resource budget must be positive".into());
        }
        if self.min_verified_ratio_ppm > 1_000_000 {
            return Err("declared min_verified_ratio_ppm must be at most 1000000".into());
        }
        Ok(())
    }
}

/// Leakage diagnostics copied from `corpus_sample::LeakageReport` (§15.2).
#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SampleLeakage {
    pub input_candidates: u64,
    pub exact_duplicate_hashes: u64,
    pub excluded_c3_hashes: u64,
    pub collapsed_editions: u64,
    pub collapsed_families: u64,
    pub c3_family_overlap: u64,
    pub garant_available: u64,
    pub garant_selected: u64,
    pub consultant_available: u64,
    pub consultant_selected: u64,
    pub garant_cap: u64,
    pub not_year_type_stratified: bool,
}

/// One declared source root.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DeclaredRoot {
    /// Source-root-relative path (e.g. `consru_export/consru_export/exports`).
    pub relative_path: String,
    /// Provider token bound to the root.
    pub provider: ProviderToken,
}

/// One pinned sample entry.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SampleEntry {
    /// Source-root-relative path.
    pub relative_path: String,
    /// Content sha256 (bare 64-hex or `sha256:`-prefixed).
    pub sha256: String,
    /// Content byte length.
    pub bytes: u64,
    /// Provider token.
    pub provider: ProviderToken,
    /// Bounded document-type label.
    pub document_type: String,
    /// Provider-qualified work-family key.
    pub work_family: String,
}

/// Pinned stratified corpus sample manifest (`...corpus-sample/v1`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusSampleManifest {
    pub schema: String,
    pub schema_version: u64,
    pub lifecycle: String,
    pub milestone: String,
    pub slice: String,
    pub count_only: bool,
    pub ascii_only: bool,
    /// True when the thresholds block was frozen before the run.
    pub declared_before_run: bool,
    pub declared_thresholds: DeclaredThresholds,
    /// Deterministic sha256 over the sorted `(relative_path, sha256)` inventory.
    pub corpus_snapshot_sha256: String,
    /// Declared not year/type stratified (D668).
    pub not_year_type_stratified: bool,
    /// Declared C3 exclusion (S04: `none (diagnostic sample, not an evaluation holdout)`).
    pub c3_exclusion: String,
    pub leakage: SampleLeakage,
    pub roots: Vec<DeclaredRoot>,
    pub entries: Vec<SampleEntry>,
    pub non_claims: Vec<String>,
}

impl CorpusSampleManifest {
    /// Strict fail-closed load: JSON → forbidden-key scan → typed schema →
    /// `validate`.
    pub fn load(text: &str) -> Result<Self, String> {
        let value = parse_json(text)?;
        let manifest: Self = serde_json::from_value(value)
            .map_err(|error| format!("sample manifest schema: {error}"))?;
        manifest.validate()?;
        Ok(manifest)
    }

    /// Internal-consistency validation.
    pub fn validate(&self) -> Result<(), String> {
        if self.schema != SAMPLE_SCHEMA {
            return Err(format!("sample schema must be {SAMPLE_SCHEMA}"));
        }
        if self.schema_version != SCHEMA_VERSION {
            return Err("sample schema_version must be 1".into());
        }
        if self.lifecycle != LIFECYCLE_BOUNDED {
            return Err(format!("sample lifecycle must be {LIFECYCLE_BOUNDED}"));
        }
        if self.milestone != MILESTONE || self.slice != SLICE {
            return Err(format!("sample must name {MILESTONE}/{SLICE}"));
        }
        if !(self.count_only && self.ascii_only) {
            return Err("sample must be count_only and ascii_only".into());
        }
        if !self.declared_before_run {
            return Err("sample thresholds must be declared before the run".into());
        }
        self.declared_thresholds.validate()?;
        validate_sha256(&self.corpus_snapshot_sha256)?;
        if !self.not_year_type_stratified || !self.leakage.not_year_type_stratified {
            return Err("sample must be provider/work-family stratified, not year/type".into());
        }
        if self.c3_exclusion.trim().is_empty() {
            return Err("sample c3_exclusion must be declared".into());
        }
        if self.roots.is_empty() {
            return Err("sample must declare at least one source root".into());
        }
        let mut root_paths = BTreeSet::new();
        for root in &self.roots {
            validate_relative_path(&root.relative_path)?;
            if !root_paths.insert(root.relative_path.clone()) {
                return Err(format!("duplicate declared root {}", root.relative_path));
            }
        }
        if self.entries.is_empty() {
            return Err("sample must pin at least one entry".into());
        }
        if self.entries.len() as u64 != self.declared_thresholds.sample_size {
            return Err(format!(
                "sample entries ({}) must equal declared sample_size ({})",
                self.entries.len(),
                self.declared_thresholds.sample_size
            ));
        }
        let mut paths = BTreeSet::new();
        let mut hashes = BTreeSet::new();
        for entry in &self.entries {
            validate_relative_path(&entry.relative_path)?;
            validate_sha256(&entry.sha256)?;
            if entry.bytes == 0 {
                return Err(format!("entry {} has zero bytes", entry.relative_path));
            }
            if entry.document_type.trim().is_empty() || entry.work_family.trim().is_empty() {
                return Err(format!(
                    "entry {} lacks a document_type/work_family",
                    entry.relative_path
                ));
            }
            if !paths.insert(entry.relative_path.clone()) {
                return Err(format!("duplicate entry path {}", entry.relative_path));
            }
            if !hashes.insert(normalize_sha256(&entry.sha256)) {
                return Err(format!(
                    "duplicate entry sha256 for {}",
                    entry.relative_path
                ));
            }
        }
        if self.non_claims.is_empty() {
            return Err("sample must carry non_claims".into());
        }
        Ok(())
    }

    /// Deterministic, pretty JSON rendering.
    pub fn to_json_string(&self) -> Result<String, String> {
        serde_json::to_string_pretty(self).map_err(|error| error.to_string())
    }
}

/// Per-entry JSONL record (the acceptance report's companion detail).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AcceptanceEntry {
    pub relative_path: String,
    pub sha256: String,
    pub bytes: u64,
    pub provider: ProviderToken,
    pub document_type: String,
    pub work_family: String,
    pub outcome: EntryOutcome,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub verify_code: Option<VerifyCodeToken>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub limit_kind: Option<LimitKind>,
    pub wall_ms: u64,
}

impl AcceptanceEntry {
    /// Strict fail-closed load of one JSONL line.
    pub fn load_line(text: &str) -> Result<Self, String> {
        let value = parse_json(text)?;
        let entry: Self =
            serde_json::from_value(value).map_err(|error| format!("entry schema: {error}"))?;
        entry.validate()?;
        Ok(entry)
    }

    /// Validate the bounded fields and the outcome-token coherence.
    pub fn validate(&self) -> Result<(), String> {
        validate_relative_path(&self.relative_path)?;
        validate_sha256(&self.sha256)?;
        if self.bytes == 0 {
            return Err(format!("entry {} has zero bytes", self.relative_path));
        }
        match self.outcome {
            EntryOutcome::VerifyRefused => {
                if self.verify_code.is_none() {
                    return Err("verify_refused must carry a verify_code".into());
                }
                if self.limit_kind.is_some() {
                    return Err("verify_refused must not carry a limit_kind".into());
                }
            }
            EntryOutcome::LimitLineBytes => {
                if self.limit_kind != Some(LimitKind::LineBytes) {
                    return Err("limit_line_bytes must carry limit_kind=line_bytes".into());
                }
                if self.verify_code.is_some() {
                    return Err("limit_line_bytes must not carry a verify_code".into());
                }
            }
            EntryOutcome::LimitRecords => {
                if self.limit_kind != Some(LimitKind::Records) {
                    return Err("limit_records must carry limit_kind=records".into());
                }
                if self.verify_code.is_some() {
                    return Err("limit_records must not carry a verify_code".into());
                }
            }
            _ => {
                if self.verify_code.is_some() || self.limit_kind.is_some() {
                    return Err(format!(
                        "{} must not carry verify_code/limit_kind",
                        self.outcome.as_str()
                    ));
                }
            }
        }
        Ok(())
    }
}

/// Structural-integrity section (§15.3).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StructuralIntegritySection {
    pub entries_total: u64,
    pub verified_ok: u64,
    pub read_back_refused: u64,
    pub verify_refused: u64,
    pub decode_refused: u64,
    pub gate_refused: u64,
    pub analysis_refused: u64,
    pub limit_line_bytes: u64,
    pub limit_records: u64,
    pub manifest_pin_mismatch: u64,
    /// Closed verifier-code histogram; sums to `verify_refused`.
    pub verify_codes: std::collections::BTreeMap<String, u64>,
    pub tamper_probe_entries: u64,
    pub tamper_probe_detected: u64,
    pub tamper_probe_false_negative: u64,
    /// Sum of every non-`verified_ok` outcome.
    pub structural_failures: u64,
    /// True only when `structural_failures == 0`.
    pub pass: bool,
}

impl StructuralIntegritySection {
    fn validate(&self) -> Result<(), String> {
        if self.entries_total == 0 {
            return Err("structural_integrity.entries_total must be positive".into());
        }
        let failures = self
            .read_back_refused
            .saturating_add(self.verify_refused)
            .saturating_add(self.decode_refused)
            .saturating_add(self.gate_refused)
            .saturating_add(self.analysis_refused)
            .saturating_add(self.limit_line_bytes)
            .saturating_add(self.limit_records)
            .saturating_add(self.manifest_pin_mismatch);
        if self.structural_failures != failures {
            return Err(format!(
                "structural_failures ({}) must equal the outcome sum ({failures})",
                self.structural_failures
            ));
        }
        if self.entries_total != self.verified_ok.saturating_add(self.structural_failures) {
            return Err("entries_total must equal verified_ok + structural_failures".into());
        }
        if self.pass != (self.structural_failures == 0) {
            return Err("structural_integrity.pass must mirror structural_failures == 0".into());
        }
        for key in self.verify_codes.keys() {
            if !VERIFY_CODE_TOKENS.contains(&key.as_str()) {
                return Err(format!("unknown verify_code token {key}"));
            }
        }
        let code_sum: u64 = self.verify_codes.values().copied().sum();
        if code_sum != self.verify_refused {
            return Err("verify_codes must sum to verify_refused".into());
        }
        if self.tamper_probe_entries == 0 {
            return Err("tamper_probe_entries must be positive".into());
        }
        if self
            .tamper_probe_detected
            .saturating_add(self.tamper_probe_false_negative)
            != self.tamper_probe_entries
        {
            return Err("tamper probe detected + false_negative must equal the subset size".into());
        }
        Ok(())
    }
}

/// Semantic-adjudication section (§15.3, D667).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SemanticAdjudicationSection {
    /// S04: `absent`.
    pub semantic_reference_status: String,
    /// S04: `false` — no C5 promotion.
    pub promotion: bool,
    pub adjudication_status: AdjudicationStatus,
    /// The adjudication packet schema this report points at.
    pub packet_schema: String,
    /// sha256 of the text-free adjudication packet.
    pub adjudication_packet_sha256: String,
    pub adjudicated_entries: u64,
    pub non_claims: Vec<String>,
}

impl SemanticAdjudicationSection {
    fn validate(&self) -> Result<(), String> {
        if self.semantic_reference_status != SEMANTIC_REFERENCE_STATUS_ABSENT {
            return Err(format!(
                "semantic_reference_status must be {SEMANTIC_REFERENCE_STATUS_ABSENT} (D667)"
            ));
        }
        if self.promotion {
            return Err("semantic_adjudication.promotion must be false".into());
        }
        if self.packet_schema != ADJUDICATION_SCHEMA {
            return Err(format!("packet_schema must be {ADJUDICATION_SCHEMA}"));
        }
        validate_sha256(&self.adjudication_packet_sha256)?;
        if self.non_claims.is_empty() {
            return Err("semantic_adjudication must carry non_claims".into());
        }
        Ok(())
    }
}

/// Limits section (§15.3).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LimitsSection {
    pub limit_events_total: u64,
    /// Closed `LimitKind` histogram.
    pub limit_events: std::collections::BTreeMap<String, u64>,
    pub within_threshold: bool,
}

impl LimitsSection {
    fn validate(&self) -> Result<(), String> {
        for key in self.limit_events.keys() {
            if !LIMIT_KIND_TOKENS.contains(&key.as_str()) {
                return Err(format!("unknown limit_kind token {key}"));
            }
        }
        let sum: u64 = self.limit_events.values().copied().sum();
        if sum != self.limit_events_total {
            return Err("limit_events must sum to limit_events_total".into());
        }
        Ok(())
    }
}

/// Resources section (§15.3).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ResourcesSection {
    /// Process peak RSS; `null` when the platform cannot report it.
    pub peak_memory_bytes: Option<u64>,
    /// True iff `peak_memory_bytes` is present (never a silent zero).
    pub peak_memory_available: bool,
    pub total_wall_ms: u64,
    pub mean_wall_ms: u64,
    pub max_wall_ms: u64,
    pub within_budget: bool,
}

impl ResourcesSection {
    fn validate(&self) -> Result<(), String> {
        if self.peak_memory_available != self.peak_memory_bytes.is_some() {
            return Err("peak_memory_available must mirror peak_memory_bytes.is_some()".into());
        }
        if self.max_wall_ms > self.total_wall_ms {
            return Err("max_wall_ms must not exceed total_wall_ms".into());
        }
        Ok(())
    }
}

/// Corpus-breadth section (§15.3).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CorpusBreadthSection {
    pub sample_size: u64,
    /// Provider histogram: `consultant_export` / `garant`.
    pub provider_counts: std::collections::BTreeMap<String, u64>,
    pub work_family_count: u64,
    /// Document-type histogram.
    pub document_type_counts: std::collections::BTreeMap<String, u64>,
    pub not_year_type_stratified: bool,
    /// S04: `null` — no coverage claim (§15.6).
    pub coverage_claim: Option<String>,
}

impl CorpusBreadthSection {
    fn validate(&self) -> Result<(), String> {
        if self.sample_size == 0 {
            return Err("corpus_breadth.sample_size must be positive".into());
        }
        for key in self.provider_counts.keys() {
            if !matches!(key.as_str(), "consultant_export" | "garant") {
                return Err(format!("unknown provider token {key}"));
            }
        }
        let providers: u64 = self.provider_counts.values().copied().sum();
        if providers != self.sample_size {
            return Err("provider_counts must sum to sample_size".into());
        }
        if self.work_family_count == 0 {
            return Err("work_family_count must be positive".into());
        }
        let types: u64 = self.document_type_counts.values().copied().sum();
        if types != self.sample_size {
            return Err("document_type_counts must sum to sample_size".into());
        }
        if !self.not_year_type_stratified {
            return Err("corpus_breadth must declare not_year_type_stratified".into());
        }
        if self.coverage_claim.is_some() {
            return Err("coverage_claim must be null (no breadth claim)".into());
        }
        Ok(())
    }
}

/// Horizon section (§15.3).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HorizonSection {
    pub r1000_status: String,
    pub m208_status: String,
    pub display_cleaning_status: String,
    pub next_horizon_status: String,
}

impl HorizonSection {
    fn validate(&self) -> Result<(), String> {
        if self.r1000_status != R1000_STATUS_ACTIVE {
            return Err(format!(
                "horizon.r1000_status must be {R1000_STATUS_ACTIVE}"
            ));
        }
        if self.m208_status != M208_STATUS_PARKED {
            return Err(format!("horizon.m208_status must be {M208_STATUS_PARKED}"));
        }
        if self.display_cleaning_status.trim().is_empty()
            || self.next_horizon_status.trim().is_empty()
        {
            return Err("horizon display-cleaning and next-horizon status must be declared".into());
        }
        Ok(())
    }
}

/// Separated corpus acceptance report (`...corpus-acceptance/v1`, §15.3).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AcceptanceReport {
    pub schema: String,
    pub schema_version: u64,
    pub lifecycle: String,
    pub milestone: String,
    pub slice: String,
    pub count_only: bool,
    pub ascii_only: bool,
    /// sha256 of the pinned sample manifest this report accepts.
    pub sample_manifest_sha256: String,
    /// Declared-before-run thresholds copied from the manifest.
    pub declared_thresholds: DeclaredThresholds,
    pub structural_integrity: StructuralIntegritySection,
    pub semantic_adjudication: SemanticAdjudicationSection,
    pub limits: LimitsSection,
    pub resources: ResourcesSection,
    pub corpus_breadth: CorpusBreadthSection,
    pub horizon: HorizonSection,
    pub verdict: Verdict,
    pub verdict_basis: String,
    pub non_claims: Vec<String>,
}

impl AcceptanceReport {
    /// Strict fail-closed load: JSON → forbidden-key scan → typed schema →
    /// `validate`.
    pub fn load(text: &str) -> Result<Self, String> {
        let value = parse_json(text)?;
        let report: Self = serde_json::from_value(value)
            .map_err(|error| format!("acceptance report schema: {error}"))?;
        report.validate()?;
        Ok(report)
    }

    /// The declared verdict rule (§15.3, §15.4).
    pub fn compute_verdict(&self) -> Verdict {
        let structural = &self.structural_integrity;
        let hard_fail = structural.tamper_probe_false_negative > 0
            || structural.manifest_pin_mismatch > 0
            || structural.verify_refused > 0
            || self.semantic_adjudication.promotion
            || self.semantic_adjudication.semantic_reference_status
                != SEMANTIC_REFERENCE_STATUS_ABSENT
            || self.corpus_breadth.coverage_claim.is_some();
        if hard_fail {
            return Verdict::Fail;
        }
        let verified_ppm = structural
            .verified_ok
            .saturating_mul(1_000_000)
            .checked_div(structural.entries_total)
            .unwrap_or(0);
        let attention = structural.read_back_refused > 0
            || structural.decode_refused > 0
            || structural.gate_refused > 0
            || structural.analysis_refused > 0
            || structural.limit_line_bytes > 0
            || structural.limit_records > 0
            || !self.limits.within_threshold
            || !self.resources.within_budget
            || verified_ppm < self.declared_thresholds.min_verified_ratio_ppm;
        if attention {
            return Verdict::NeedsAttention;
        }
        Verdict::Pass
    }

    /// Internal-consistency validation of every separated section.
    pub fn validate(&self) -> Result<(), String> {
        if self.schema != ACCEPTANCE_SCHEMA {
            return Err(format!("acceptance schema must be {ACCEPTANCE_SCHEMA}"));
        }
        if self.schema_version != SCHEMA_VERSION {
            return Err("acceptance schema_version must be 1".into());
        }
        if self.lifecycle != LIFECYCLE_BOUNDED {
            return Err(format!("acceptance lifecycle must be {LIFECYCLE_BOUNDED}"));
        }
        if self.milestone != MILESTONE || self.slice != SLICE {
            return Err(format!("acceptance must name {MILESTONE}/{SLICE}"));
        }
        if !(self.count_only && self.ascii_only) {
            return Err("acceptance must be count_only and ascii_only".into());
        }
        validate_sha256(&self.sample_manifest_sha256)?;
        self.declared_thresholds.validate()?;
        self.structural_integrity.validate()?;
        self.semantic_adjudication.validate()?;
        self.limits.validate()?;
        self.resources.validate()?;
        self.corpus_breadth.validate()?;
        self.horizon.validate()?;

        if self.corpus_breadth.sample_size != self.declared_thresholds.sample_size {
            return Err("corpus_breadth.sample_size must equal declared sample_size".into());
        }
        if self.structural_integrity.entries_total != self.declared_thresholds.sample_size {
            return Err("structural entries_total must equal declared sample_size".into());
        }
        if self.limits.within_threshold
            != (self.limits.limit_events_total <= self.declared_thresholds.max_limit_events)
        {
            return Err("limits.within_threshold must mirror declared max_limit_events".into());
        }
        if self.structural_integrity.limit_line_bytes + self.structural_integrity.limit_records
            != self.limits.limit_events_total
        {
            return Err("limit entry outcomes must equal limit_events_total".into());
        }
        let peak_within = self
            .resources
            .peak_memory_bytes
            .is_none_or(|peak| peak <= self.declared_thresholds.resource_budget_peak_bytes);
        let time_within =
            self.resources.total_wall_ms <= self.declared_thresholds.resource_budget_total_ms;
        if self.resources.within_budget != (peak_within && time_within) {
            return Err("resources.within_budget must mirror the declared budget".into());
        }
        if self.verdict != self.compute_verdict() {
            return Err(format!(
                "verdict {} disagrees with the declared rules ({})",
                self.verdict.as_str(),
                self.compute_verdict().as_str()
            ));
        }
        if self.verdict_basis.trim().is_empty() {
            return Err("verdict_basis must not be empty".into());
        }
        if self.non_claims.is_empty() {
            return Err("acceptance must carry non_claims".into());
        }
        Ok(())
    }

    /// Deterministic, pretty JSON rendering.
    pub fn to_json_string(&self) -> Result<String, String> {
        serde_json::to_string_pretty(self).map_err(|error| error.to_string())
    }
}

/// One text-free adjudication packet item.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AdjudicationItem {
    pub entry_index: u64,
    pub relative_path: String,
    pub sha256: String,
    pub document_type: String,
    pub work_family: String,
    pub adjudication_status: AdjudicationStatus,
}

impl AdjudicationItem {
    fn validate(&self) -> Result<(), String> {
        validate_relative_path(&self.relative_path)?;
        validate_sha256(&self.sha256)?;
        if self.document_type.trim().is_empty() || self.work_family.trim().is_empty() {
            return Err("adjudication item lacks a document_type/work_family".into());
        }
        Ok(())
    }
}

/// Text-free, count/hash-only adjudication packet (`...adjudication-packet/v1`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AdjudicationPacket {
    pub schema: String,
    pub schema_version: u64,
    pub lifecycle: String,
    pub milestone: String,
    pub slice: String,
    pub count_only: bool,
    pub ascii_only: bool,
    pub sample_manifest_sha256: String,
    /// S04: `false`.
    pub promotion: bool,
    /// S04: `absent`.
    pub semantic_reference_status: String,
    pub adjudication_status: AdjudicationStatus,
    pub items: Vec<AdjudicationItem>,
    pub non_claims: Vec<String>,
}

impl AdjudicationPacket {
    /// Strict fail-closed load: JSON → forbidden-key scan → typed schema →
    /// `validate`.
    pub fn load(text: &str) -> Result<Self, String> {
        let value = parse_json(text)?;
        let packet: Self = serde_json::from_value(value)
            .map_err(|error| format!("adjudication packet schema: {error}"))?;
        packet.validate()?;
        Ok(packet)
    }

    /// Internal-consistency validation.
    pub fn validate(&self) -> Result<(), String> {
        if self.schema != ADJUDICATION_SCHEMA {
            return Err(format!("adjudication schema must be {ADJUDICATION_SCHEMA}"));
        }
        if self.schema_version != SCHEMA_VERSION {
            return Err("adjudication schema_version must be 1".into());
        }
        if self.lifecycle != LIFECYCLE_BOUNDED {
            return Err(format!(
                "adjudication lifecycle must be {LIFECYCLE_BOUNDED}"
            ));
        }
        if self.milestone != MILESTONE || self.slice != SLICE {
            return Err(format!("adjudication must name {MILESTONE}/{SLICE}"));
        }
        if !(self.count_only && self.ascii_only) {
            return Err("adjudication must be count_only and ascii_only".into());
        }
        validate_sha256(&self.sample_manifest_sha256)?;
        if self.promotion {
            return Err("adjudication promotion must be false".into());
        }
        if self.semantic_reference_status != SEMANTIC_REFERENCE_STATUS_ABSENT {
            return Err(format!(
                "adjudication semantic_reference_status must be {SEMANTIC_REFERENCE_STATUS_ABSENT}"
            ));
        }
        let mut indices = BTreeSet::new();
        let mut paths = BTreeSet::new();
        for item in &self.items {
            item.validate()?;
            if !indices.insert(item.entry_index) {
                return Err(format!(
                    "duplicate adjudication entry_index {}",
                    item.entry_index
                ));
            }
            if !paths.insert(item.relative_path.clone()) {
                return Err(format!(
                    "duplicate adjudication path {}",
                    item.relative_path
                ));
            }
        }
        if self.non_claims.is_empty() {
            return Err("adjudication must carry non_claims".into());
        }
        Ok(())
    }

    /// Deterministic, pretty JSON rendering.
    pub fn to_json_string(&self) -> Result<String, String> {
        serde_json::to_string_pretty(self).map_err(|error| error.to_string())
    }
}

// ------------------------------------------------------- sample builder #

/// One declared source root for [`build_sample`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SampleRoot {
    /// Repo-relative declared root recorded in the manifest.
    pub relative_path: String,
    /// On-disk location walked by the builder.
    pub path: PathBuf,
    /// Provider kind of the root.
    pub kind: SourceRootKind,
}

impl SampleRoot {
    /// Build a declared root; the declared path must be normalized and
    /// relative so the manifest cannot record an absolute/traversing root.
    pub fn new(
        relative_path: impl Into<String>,
        path: impl Into<PathBuf>,
        kind: SourceRootKind,
    ) -> Result<Self, String> {
        let relative_path = relative_path.into();
        validate_relative_path(&relative_path)?;
        let path = path.into();
        if path.as_os_str().is_empty() {
            return Err("source root disk path must not be empty".into());
        }
        Ok(Self {
            relative_path,
            path,
            kind,
        })
    }
}

/// Declared repo-relative S04 roots with optional disk overrides. The
/// canonical disk locations are `consru_export/consru_export/exports` and
/// `law-source/garant`; overrides exist only for synthetic runs.
pub fn declared_sample_roots(
    consultant_disk: impl Into<PathBuf>,
    garant_disk: impl Into<PathBuf>,
) -> Result<Vec<SampleRoot>, String> {
    Ok(vec![
        SampleRoot::new(
            CONSULTANT_ROOT_RELATIVE,
            consultant_disk,
            SourceRootKind::ConsultantExport,
        )?,
        SampleRoot::new(GARANT_ROOT_RELATIVE, garant_disk, SourceRootKind::Garant)?,
    ])
}

/// Walk the declared roots, pin every XML file by content sha256 + byte
/// length, draw the frozen provider/work-family stratified sample and return
/// the sealed [`CorpusSampleManifest`] (§15.1, D668).
///
/// Fail-closed: an absent declared root, a duplicate declared root or
/// inventory row, a non-ASCII entry path (the manifest declares
/// `ascii_only`), an empty file, or an inventory smaller than the declared
/// `sample_size` is an error — never a silent shrink and never a fabricated
/// entry.
pub fn build_sample(roots: &[SampleRoot]) -> Result<CorpusSampleManifest, String> {
    if roots.is_empty() {
        return Err("build_sample requires at least one declared root".into());
    }
    let mut declared_roots = Vec::with_capacity(roots.len());
    let mut seen_root_paths = BTreeSet::new();
    let mut inventory: Vec<SampleCandidate> = Vec::new();
    let mut bytes_by_key: BTreeMap<(SourceRootKind, String), u64> = BTreeMap::new();
    for root in roots {
        if !root.path.is_dir() {
            return Err(format!(
                "declared source root is absent: {} ({})",
                root.relative_path,
                root.path.display()
            ));
        }
        if !seen_root_paths.insert(root.relative_path.clone()) {
            return Err(format!("duplicate declared root {}", root.relative_path));
        }
        declared_roots.push(DeclaredRoot {
            relative_path: root.relative_path.clone(),
            provider: ProviderToken::from_root_kind(root.kind),
        });
        let files = ln_decode::npa_sweep::walk_xml_files(&root.path, None)
            .map_err(|error| format!("walk {}: {error}", root.path.display()))?;
        for path in files {
            let meta = corpus_sample::classify_path(&path, &root.path, root.kind)
                .map_err(|error| format!("classify {}: {error}", path.display()))?;
            if !meta.relative_path.is_ascii() {
                return Err(format!(
                    "ascii_only manifest refuses non-ascii path: {}",
                    meta.relative_path
                ));
            }
            let (sha256, bytes) = sha256_file(&path)?;
            if bytes == 0 {
                return Err(format!("empty corpus file {}", meta.relative_path));
            }
            let key = (root.kind, meta.relative_path.clone());
            if bytes_by_key.insert(key, bytes).is_some() {
                return Err(format!("duplicate inventory entry {}", meta.relative_path));
            }
            inventory.push(SampleCandidate {
                relative_path: meta.relative_path.clone(),
                content_hash: sha256,
                meta,
            });
        }
    }
    if inventory.is_empty() {
        return Err("declared roots yielded no XML inventory".into());
    }
    let corpus_snapshot_sha256 = inventory_snapshot_sha256(&inventory);
    let c3_hashes: BTreeSet<String> = BTreeSet::new();
    let plan = corpus_sample::draw(
        inventory,
        &c3_hashes,
        usize::try_from(DECLARED_SAMPLE_SIZE).unwrap_or(usize::MAX),
        DECLARED_DRAW_SEED,
    )
    .map_err(|error| format!("sample draw refused: {error}"))?;
    let mut entries = Vec::with_capacity(plan.candidates.len());
    for candidate in &plan.candidates {
        let provider = ProviderToken::from_root_kind(candidate.meta.provider);
        let bytes = bytes_by_key
            .get(&(candidate.meta.provider, candidate.relative_path.clone()))
            .copied()
            .ok_or_else(|| format!("missing byte length for {}", candidate.relative_path))?;
        entries.push(SampleEntry {
            relative_path: candidate.relative_path.clone(),
            sha256: candidate.content_hash.clone(),
            bytes,
            provider,
            document_type: candidate.meta.document_type.clone(),
            work_family: candidate.meta.work_family.key.clone(),
        });
    }
    let manifest = CorpusSampleManifest {
        schema: SAMPLE_SCHEMA.into(),
        schema_version: SCHEMA_VERSION,
        lifecycle: LIFECYCLE_BOUNDED.into(),
        milestone: MILESTONE.into(),
        slice: SLICE.into(),
        count_only: true,
        ascii_only: true,
        declared_before_run: true,
        declared_thresholds: DeclaredThresholds::declared(),
        corpus_snapshot_sha256,
        not_year_type_stratified: true,
        c3_exclusion: C3_EXCLUSION_NONE.into(),
        leakage: SampleLeakage::from_report(&plan.leakage),
        roots: declared_roots,
        entries,
        non_claims: sample_non_claims(),
    };
    manifest.validate()?;
    Ok(manifest)
}

impl SampleLeakage {
    fn from_report(report: &corpus_sample::LeakageReport) -> Self {
        Self {
            input_candidates: report.input_candidates as u64,
            exact_duplicate_hashes: report.exact_duplicate_hashes as u64,
            excluded_c3_hashes: report.excluded_c3_hashes as u64,
            collapsed_editions: report.collapsed_editions as u64,
            collapsed_families: report.collapsed_families as u64,
            c3_family_overlap: report.c3_family_overlap as u64,
            garant_available: report.garant_available as u64,
            garant_selected: report.garant_selected as u64,
            consultant_available: report.consultant_available as u64,
            consultant_selected: report.consultant_selected as u64,
            garant_cap: report.garant_cap as u64,
            not_year_type_stratified: report.not_year_type_stratified,
        }
    }
}

/// Non-claims carried by the sample manifest (§15.6).
pub fn sample_non_claims() -> Vec<String> {
    vec![
        "count/hash only; no decoded corpus text".into(),
        "bounded provider/work-family stratified sample; not a corpus-coverage claim".into(),
        "the corpus sweep is not a semantic oracle".into(),
        "no C5 promotion; R1000 stays active/unclosed; M208-wrz6fg stays parked".into(),
    ]
}

/// Deterministic sha256 over the sorted `(relative_path, sha256)` inventory.
fn inventory_snapshot_sha256(inventory: &[SampleCandidate]) -> String {
    let mut rows: Vec<String> = inventory
        .iter()
        .map(|candidate| {
            format!(
                "{}\t{}",
                candidate.relative_path,
                normalize_sha256(&candidate.content_hash)
            )
        })
        .collect();
    rows.sort();
    let mut hasher = Sha256::new();
    for row in &rows {
        hasher.update(row.as_bytes());
        hasher.update(b"\n");
    }
    format!("sha256:{}", hex_lower(&hasher.finalize()))
}

/// Stream one file through sha256 and report its byte length.
fn sha256_file(path: &Path) -> Result<(String, u64), String> {
    let mut file =
        fs::File::open(path).map_err(|error| format!("open {}: {error}", path.display()))?;
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    let mut total: u64 = 0;
    loop {
        let read = file
            .read(&mut buffer)
            .map_err(|error| format!("read {}: {error}", path.display()))?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
        total = total.saturating_add(read as u64);
    }
    Ok((format!("sha256:{}", hex_lower(&hasher.finalize())), total))
}

fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

// ----------------------------------------------------------- validation #

/// Reject `..`, absolute and backslash paths; require a non-empty
/// source-root-relative path.
pub fn validate_relative_path(path: &str) -> Result<(), String> {
    if path.trim().is_empty() {
        return Err("path must not be empty".into());
    }
    if path.contains('\\') {
        return Err("path must use '/' separators".into());
    }
    if path.starts_with('/') {
        return Err("path must be relative, not absolute".into());
    }
    let parsed = Path::new(path);
    if parsed.is_absolute() {
        return Err("path must be relative, not absolute".into());
    }
    for component in parsed.components() {
        match component {
            Component::ParentDir => return Err("path must not traverse its root".into()),
            Component::RootDir | Component::Prefix(_) => {
                return Err("path must be relative, not absolute".into())
            }
            Component::Normal(_) | Component::CurDir => {}
        }
    }
    Ok(())
}

/// Require a 64-hex sha256, optionally `sha256:`-prefixed.
pub fn validate_sha256(value: &str) -> Result<(), String> {
    let hex = normalize_sha256(value);
    if hex.len() != 64 || !hex.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err("sha256 must be 64 hexadecimal digits".into());
    }
    Ok(())
}

fn normalize_sha256(value: &str) -> String {
    value
        .strip_prefix("sha256:")
        .unwrap_or(value)
        .to_ascii_lowercase()
}

fn parse_json(text: &str) -> Result<Value, String> {
    let value: Value =
        serde_json::from_str(text).map_err(|error| format!("invalid JSON: {error}"))?;
    reject_forbidden_keys(&value, "$")?;
    Ok(value)
}

fn reject_forbidden_keys(value: &Value, path: &str) -> Result<(), String> {
    match value {
        Value::Object(members) => {
            for (key, child) in members {
                if FORBIDDEN_TEXT_KEYS.contains(&key.as_str()) {
                    return Err(format!(
                        "{path}: raw-text-bearing field '{key}' is forbidden (count/hash-only)"
                    ));
                }
                reject_forbidden_keys(child, &format!("{path}.{key}"))?;
            }
        }
        Value::Array(items) => {
            for (index, child) in items.iter().enumerate() {
                reject_forbidden_keys(child, &format!("{path}[{index}]"))?;
            }
        }
        _ => {}
    }
    Ok(())
}
