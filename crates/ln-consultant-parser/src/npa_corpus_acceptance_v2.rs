//! M221 S04 split acceptance report (`law-nexus/npa-analysis-corpus-acceptance/v2`).
//!
//! This is the successor revision of the frozen M214 v1 acceptance report
//! (`crate::npa_corpus_acceptance`, contract §15). It is **additive**: the v1
//! schema, constants, artifacts and `run_acceptance_with`/`load`/`validate`
//! signatures are untouched. It separates the single v1 `verdict` into three
//! independent verdicts (contract §15A.2, D675):
//!
//! - `transport_integrity` — v1 structural integrity + tamper probe;
//! - `analysis_completion` — per-entry completion capture (§15A.3/§15A.4);
//! - `semantic_acceptance` — always `not_attempted` (D667; no independent
//!   legal-semantic oracle exists).
//!
//! It also makes provider coverage explicit (§15A.5, D676): every declared
//! provider is either `covered` or `uncovered` with a closed `uncovered_reason`
//! (`no_candidates` / `no_selection` / `format_unsupported`); a zero-sample
//! provider is never silently dropped. `law-source/garant` (0 XML) is the
//! canonical `uncovered`/`no_candidates` case.
//!
//! Count/hash-only: ASCII, control-free, every string at most 512 bytes, no
//! decoded corpus text (contract §15A.1/§15A.7, §8.4). `load`/`validate` are
//! fail-closed (`deny_unknown_fields` plus explicit refusals).

use std::collections::{BTreeMap, BTreeSet};

use ln_decode::npa_analysis_wire::FAMILIES;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::npa_corpus_acceptance::{
    AcceptanceEntry, DeclaredRoot, EntryOutcome, StructuralIntegritySection, Verdict,
    FORBIDDEN_TEXT_KEYS,
};

// ------------------------------------------------------------- constants #

/// v2 split-acceptance report schema.
pub const ACCEPTANCE_V2_SCHEMA: &str = "law-nexus/npa-analysis-corpus-acceptance/v2";
/// Owning M221 milestone (distinct from the frozen v1 `MILESTONE`).
pub const M221_MILESTONE: &str = "M221-wbslul";
/// Owning slice.
pub const M221_SLICE: &str = "S04";
/// v2 schema revision.
pub const V2_SCHEMA_VERSION: u64 = 2;
/// Closed bounded lifecycle marker.
pub const V2_LIFECYCLE_BOUNDED: &str = "[bounded]";
/// Declared-before-run minimum completion ratio (S04: every verified entry).
pub const DECLARED_MIN_COMPLETION_RATIO_PPM: u64 = 1_000_000;
/// Declared-before-run per-family minimum yields.
pub const DECLARED_MIN_FAMILY_YIELDS: &[(&str, u64)] = &[("document", 1), ("fragment", 1)];
/// Maximum serialized length of any v2 string (contract §15A.1).
pub const MAX_V2_STRING_BYTES: usize = 512;

/// Closed `completion_basis` token set (§8A.6/§8B.3 union, contract §15A.3).
pub const COMPLETION_BASIS_TOKENS: &[&str] = &[
    "bounded_analysis_complete",
    "hold",
    "text_only",
    "refused_record",
    "limit_reached",
    "caller_scope",
    "unsupported_source",
    "context_incomplete",
];

/// Closed `incomplete_reasons` token set (basis tokens + §8B.3 context reasons).
pub const INCOMPLETE_REASON_TOKENS: &[&str] = &[
    "bounded_analysis_complete",
    "hold",
    "text_only",
    "refused_record",
    "limit_reached",
    "caller_scope",
    "unsupported_source",
    "context_incomplete",
    "context_partial",
    "context_conflicting",
    "context_unavailable",
    "context_cycle",
    "context_limit",
];

/// Closed `ThisDocumentReferenceToken` wire tokens (§8C).
pub const CONTEXT_RESULT_TOKENS: &[&str] =
    &["authorized", "conflicting", "unavailable", "not_requested"];

/// Closed provider tokens (mirrors `ProviderToken::as_str`).
pub const PROVIDER_TOKENS: &[&str] = &["consultant_export", "garant"];

/// Closed verifier-code tokens (the §8B.4 `AnalysisVerifyCode` set).
const V2_VERIFY_CODE_TOKENS: &[&str] = &[
    "envelope_structural",
    "seal_mismatch",
    "manifest_identity_mismatch",
    "fragment_hash_mismatch",
    "span_slice_mismatch",
    "source_ref_substitution",
    "relation_ref_missing",
    "relation_substitution",
    "member_ref_missing",
    "context_outcome_mismatch",
    "completion_mismatch",
];

// --------------------------------------------------------------- enums #

/// Closed `analysis_completion` verdict (§15A.2). Independent of transport.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CompletionVerdict {
    /// Every verified entry is complete and the declared ratios/yields hold.
    Complete,
    /// Structurally integral but at least one verified entry is incomplete, or
    /// the observed completion ratio / a per-family yield is below its floor.
    Incomplete,
    /// The per-entry completion capture is missing, so completion cannot be
    /// honestly derived (§15A.2 rule 4).
    NeedsAttention,
}

impl CompletionVerdict {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Complete => "complete",
            Self::Incomplete => "incomplete",
            Self::NeedsAttention => "needs_attention",
        }
    }
}

/// Closed `semantic_acceptance` verdict. Single token by construction (D667).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SemanticVerdict {
    /// No independent legal-semantic oracle exists; acceptance is never claimed.
    NotAttempted,
}

impl SemanticVerdict {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NotAttempted => "not_attempted",
        }
    }
}

/// Closed reason a declared provider is `uncovered` (§15A.5, D676).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum UncoveredReason {
    /// No candidate in a format the walker admits (e.g. Garant has 0 XML).
    NoCandidates,
    /// Candidates exist in a supported format but none were sampled.
    NoSelection,
    /// The provider has files only in a format the walker does not admit.
    FormatUnsupported,
}

impl UncoveredReason {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NoCandidates => "no_candidates",
            Self::NoSelection => "no_selection",
            Self::FormatUnsupported => "format_unsupported",
        }
    }
}

// ------------------------------------------------------------- structs #

/// The three independent split verdicts (§15A.2). No aggregate verdict exists.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SplitVerdicts {
    /// v1 `Verdict` over structural integrity + tamper probe.
    pub transport_integrity: Verdict,
    /// Independent analysis-completion verdict.
    pub analysis_completion: CompletionVerdict,
    /// Always `not_attempted` (D667).
    pub semantic_acceptance: SemanticVerdict,
}

/// Analysis-completion section (§15A.4). Count/hash-only.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AnalysisCompletionSection {
    /// Total entries in the bounded run.
    pub entries_total: u64,
    /// Verified entries whose captured `completion == complete`.
    pub entries_complete: u64,
    /// Verified entries whose captured `completion == incomplete`.
    pub entries_incomplete: u64,
    /// Verified entries whose completion capture is absent.
    pub entries_missing_capture: u64,
    /// `entries_complete / verified` in parts per million.
    pub observed_completion_ratio_ppm: u64,
    /// Declared-before-run completion-ratio floor.
    pub min_completion_ratio_ppm: u64,
    /// Closed `completion_basis` histogram.
    pub completion_basis: BTreeMap<String, u64>,
    /// Closed `incomplete_reasons` histogram (empty iff `entries_incomplete == 0`).
    pub incomplete_reasons: BTreeMap<String, u64>,
    /// `ThisDocumentReferenceToken` histogram (§8C).
    pub context_result_distribution: BTreeMap<String, u64>,
    /// Aggregated per-family record yields (§8A/§8B families).
    pub per_family_yields: BTreeMap<String, u64>,
    /// Declared-before-run per-family yield floors.
    pub min_family_yields: BTreeMap<String, u64>,
    /// Families whose observed yield is below the declared floor.
    pub below_expected_yield: Vec<String>,
}

/// One declared provider that produced no sampled entry (§15A.5).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct UncoveredProvider {
    /// Closed provider token.
    pub provider: String,
    /// Closed reason the provider is uncovered.
    pub uncovered_reason: UncoveredReason,
}

/// Provider-coverage section (§15A.5). `declared = covered ∪ uncovered`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProviderCoverageSection {
    /// Declared provider tokens copied from the declared roots, sorted.
    pub declared: Vec<String>,
    /// Declared providers with at least one sampled entry, sorted.
    pub covered: Vec<String>,
    /// Declared providers with zero sampled entries, sorted by provider.
    pub uncovered: Vec<UncoveredProvider>,
}

/// Declared-before-run minima (§15A.6). Never inferred from observed results.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct V2Thresholds {
    /// Minimum completion ratio in parts per million (<= 1_000_000).
    pub min_completion_ratio_ppm: u64,
    /// Per-family minimum yields.
    pub min_family_yields: BTreeMap<String, u64>,
}

impl V2Thresholds {
    /// The frozen bounded S04 declaration.
    pub fn declared() -> Self {
        Self {
            min_completion_ratio_ppm: DECLARED_MIN_COMPLETION_RATIO_PPM,
            min_family_yields: DECLARED_MIN_FAMILY_YIELDS
                .iter()
                .map(|(family, floor)| ((*family).to_string(), *floor))
                .collect(),
        }
    }

    /// Declared minima must be well-formed and closed.
    pub fn validate(&self) -> Result<(), String> {
        if self.min_completion_ratio_ppm > 1_000_000 {
            return Err("min_completion_ratio_ppm must not exceed 1_000_000".into());
        }
        for family in self.min_family_yields.keys() {
            if !FAMILIES.contains(&family.as_str()) {
                return Err(format!("unknown min_family_yields family {family}"));
            }
        }
        Ok(())
    }
}

/// The v2 split acceptance report (`...corpus-acceptance/v2`, §15A).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AcceptanceReportV2 {
    /// v2 schema tag.
    pub schema: String,
    /// v2 schema revision.
    pub schema_version: u64,
    /// Closed bounded lifecycle marker.
    pub lifecycle: String,
    /// Owning milestone (`M221-wbslul`).
    pub milestone: String,
    /// Owning slice (`S04`).
    pub slice: String,
    /// Count-only discipline flag.
    pub count_only: bool,
    /// ASCII-only discipline flag.
    pub ascii_only: bool,
    /// Never true (no C5 promotion; D667).
    pub promotion: bool,
    /// Always null (no breadth/coverage claim; §15.6).
    pub coverage_claim: Option<String>,
    /// The three independent verdicts.
    pub verdicts: SplitVerdicts,
    /// Transport structural-integrity counts (reuses the v1 section type).
    pub structural_integrity: StructuralIntegritySection,
    /// Per-entry analysis completion (§15A.4).
    pub analysis_completion: AnalysisCompletionSection,
    /// Declared-versus-sampled provider coverage (§15A.5).
    pub provider_coverage: ProviderCoverageSection,
    /// Declared-before-run minima copied from §15A.6.
    pub declared_thresholds: V2Thresholds,
    /// Non-claims (R1000 active/unclosed, no promotion, bounded fixture-first).
    pub non_claims: Vec<String>,
}

impl AcceptanceReportV2 {
    /// Strict fail-closed load: JSON → forbidden-key scan → path-like scan →
    /// typed schema → `validate`.
    pub fn load(text: &str) -> Result<Self, String> {
        let value = parse_json(text)?;
        let report: Self = serde_json::from_value(value)
            .map_err(|error| format!("v2 acceptance schema: {error}"))?;
        report.validate()?;
        Ok(report)
    }

    /// Internal-consistency validation of a v2 split report.
    pub fn validate(&self) -> Result<(), String> {
        if self.schema != ACCEPTANCE_V2_SCHEMA {
            return Err(format!(
                "v2 acceptance schema must be {ACCEPTANCE_V2_SCHEMA}"
            ));
        }
        if self.schema_version != V2_SCHEMA_VERSION {
            return Err("v2 acceptance schema_version must be 2".into());
        }
        if self.lifecycle != V2_LIFECYCLE_BOUNDED {
            return Err(format!(
                "v2 acceptance lifecycle must be {V2_LIFECYCLE_BOUNDED}"
            ));
        }
        if self.milestone != M221_MILESTONE || self.slice != M221_SLICE {
            return Err(format!(
                "v2 acceptance must name {M221_MILESTONE}/{M221_SLICE}"
            ));
        }
        if !(self.count_only && self.ascii_only) {
            return Err("v2 acceptance must be count_only and ascii_only".into());
        }
        if self.promotion {
            return Err("v2 acceptance promotion must be false (no C5 promotion)".into());
        }
        if self.coverage_claim.is_some() {
            return Err("v2 acceptance coverage_claim must be null (no breadth claim)".into());
        }
        if self.non_claims.is_empty() {
            return Err("v2 acceptance must carry non_claims".into());
        }
        validate_structural_integrity(&self.structural_integrity)?;
        validate_completion(&self.analysis_completion, &self.structural_integrity)?;
        validate_provider_coverage(&self.provider_coverage)?;
        self.declared_thresholds.validate()?;

        if self.analysis_completion.min_completion_ratio_ppm
            != self.declared_thresholds.min_completion_ratio_ppm
        {
            return Err("completion min ratio must equal the declared threshold".into());
        }
        if self.analysis_completion.min_family_yields != self.declared_thresholds.min_family_yields
        {
            return Err("completion min family yields must equal the declared thresholds".into());
        }

        let expected_transport = transport_verdict(&self.structural_integrity);
        if self.verdicts.transport_integrity != expected_transport {
            return Err(format!(
                "transport_integrity {} disagrees with structural counts ({})",
                self.verdicts.transport_integrity.as_str(),
                expected_transport.as_str()
            ));
        }
        let expected_completion = completion_verdict(&self.analysis_completion);
        if self.verdicts.analysis_completion != expected_completion {
            return Err(format!(
                "analysis_completion {} is inconsistent with its own section ({})",
                self.verdicts.analysis_completion.as_str(),
                expected_completion.as_str()
            ));
        }
        if self.verdicts.semantic_acceptance != SemanticVerdict::NotAttempted {
            return Err("semantic_acceptance must always be not_attempted (D667)".into());
        }

        check_count_hash_only(self)?;
        Ok(())
    }

    /// Deterministic, pretty JSON rendering.
    pub fn to_json_string(&self) -> Result<String, String> {
        serde_json::to_string_pretty(self).map_err(|error| error.to_string())
    }
}

/// Deterministic per-entry JSONL companion for a v2 report (§15A.1).
pub fn entries_jsonl(entries: &[AcceptanceEntry]) -> Result<String, String> {
    let mut out = String::new();
    for entry in entries {
        out.push_str(&entry.to_json_line()?);
        out.push('\n');
    }
    Ok(out)
}

/// Non-claims carried by the v2 report (§15A.8).
pub fn acceptance_v2_non_claims() -> Vec<String> {
    vec![
        "transport integrity, analysis completion and semantic acceptance are three independent facts".into(),
        "a transport_integrity pass is neither completeness nor semantic acceptance".into(),
        "no C5 promotion; semantic_acceptance is always not_attempted (D667)".into(),
        "R1000 stays active/unclosed (D638/D656); M221 adds no requirement binding".into(),
        "downstream M208-wrz6fg and M215-M220 stay parked".into(),
        "bounded fixture-first; not a corpus-wide accuracy or breadth claim".into(),
        "count/hash only; no decoded corpus text".into(),
    ]
}

// -------------------------------------------------------------- builder #

/// Build a v2 split report from a bounded set of entries.
///
/// `declared_roots` fixes the declared provider list; `provider_candidate_counts`
/// is the per-provider count of supported-format candidates available to the
/// bounded run (used only to choose between `no_candidates` and `no_selection`
/// for an uncovered provider). `thresholds` is the declared-before-run minima.
///
/// The transport tamper-probe counts are supplied by the bounded runner (T04);
/// this constructor carries zero pending that wiring and therefore derives the
/// transport verdict from the entry outcomes alone.
pub fn build_report_v2(
    entries: &[AcceptanceEntry],
    declared_roots: &[DeclaredRoot],
    provider_candidate_counts: &BTreeMap<String, u64>,
    thresholds: &V2Thresholds,
) -> Result<AcceptanceReportV2, String> {
    thresholds.validate()?;

    let structural_integrity = build_structural_integrity(entries)?;
    let analysis_completion = build_completion(entries, &structural_integrity, thresholds)?;
    let provider_coverage =
        build_provider_coverage(entries, declared_roots, provider_candidate_counts)?;

    let report = AcceptanceReportV2 {
        schema: ACCEPTANCE_V2_SCHEMA.to_string(),
        schema_version: V2_SCHEMA_VERSION,
        lifecycle: V2_LIFECYCLE_BOUNDED.to_string(),
        milestone: M221_MILESTONE.to_string(),
        slice: M221_SLICE.to_string(),
        count_only: true,
        ascii_only: true,
        promotion: false,
        coverage_claim: None,
        verdicts: SplitVerdicts {
            transport_integrity: transport_verdict(&structural_integrity),
            analysis_completion: completion_verdict(&analysis_completion),
            semantic_acceptance: SemanticVerdict::NotAttempted,
        },
        structural_integrity,
        analysis_completion,
        provider_coverage,
        declared_thresholds: thresholds.clone(),
        non_claims: acceptance_v2_non_claims(),
    };
    report.validate()?;
    Ok(report)
}

// ---------------------------------------------------------- computation #

#[derive(Default)]
struct OutcomeCounters {
    verified_ok: u64,
    read_back_refused: u64,
    verify_refused: u64,
    decode_refused: u64,
    gate_refused: u64,
    analysis_refused: u64,
    limit_line_bytes: u64,
    limit_records: u64,
    manifest_pin_mismatch: u64,
}

impl OutcomeCounters {
    fn add(&mut self, outcome: EntryOutcome) {
        match outcome {
            EntryOutcome::VerifiedOk => self.verified_ok += 1,
            EntryOutcome::ReadBackRefused => self.read_back_refused += 1,
            EntryOutcome::VerifyRefused => self.verify_refused += 1,
            EntryOutcome::DecodeRefused => self.decode_refused += 1,
            EntryOutcome::GateRefused => self.gate_refused += 1,
            EntryOutcome::AnalysisRefused => self.analysis_refused += 1,
            EntryOutcome::LimitLineBytes => self.limit_line_bytes += 1,
            EntryOutcome::LimitRecords => self.limit_records += 1,
            EntryOutcome::ManifestPinMismatch => self.manifest_pin_mismatch += 1,
        }
    }

    fn failures(&self) -> u64 {
        self.read_back_refused
            .saturating_add(self.verify_refused)
            .saturating_add(self.decode_refused)
            .saturating_add(self.gate_refused)
            .saturating_add(self.analysis_refused)
            .saturating_add(self.limit_line_bytes)
            .saturating_add(self.limit_records)
            .saturating_add(self.manifest_pin_mismatch)
    }
}

fn build_structural_integrity(
    entries: &[AcceptanceEntry],
) -> Result<StructuralIntegritySection, String> {
    let mut counters = OutcomeCounters::default();
    let mut verify_codes: BTreeMap<String, u64> = BTreeMap::new();
    for entry in entries {
        entry.validate()?;
        counters.add(entry.outcome);
        if let Some(code) = entry.verify_code {
            *verify_codes.entry(code.as_str().to_string()).or_default() += 1;
        }
    }
    let structural_failures = counters.failures();
    Ok(StructuralIntegritySection {
        entries_total: entries.len() as u64,
        verified_ok: counters.verified_ok,
        read_back_refused: counters.read_back_refused,
        verify_refused: counters.verify_refused,
        decode_refused: counters.decode_refused,
        gate_refused: counters.gate_refused,
        analysis_refused: counters.analysis_refused,
        limit_line_bytes: counters.limit_line_bytes,
        limit_records: counters.limit_records,
        manifest_pin_mismatch: counters.manifest_pin_mismatch,
        verify_codes,
        // Filled by the bounded runner (T04); zero means "probe not wired yet".
        tamper_probe_entries: 0,
        tamper_probe_detected: 0,
        tamper_probe_false_negative: 0,
        structural_failures,
        pass: structural_failures == 0,
    })
}

fn build_completion(
    entries: &[AcceptanceEntry],
    structural: &StructuralIntegritySection,
    thresholds: &V2Thresholds,
) -> Result<AnalysisCompletionSection, String> {
    let mut entries_complete = 0u64;
    let mut entries_incomplete = 0u64;
    let mut entries_missing_capture = 0u64;
    let mut completion_basis: BTreeMap<String, u64> = BTreeMap::new();
    let mut incomplete_reasons: BTreeMap<String, u64> = BTreeMap::new();
    let mut context_result_distribution: BTreeMap<String, u64> = BTreeMap::new();
    let mut per_family_yields: BTreeMap<String, u64> = BTreeMap::new();

    for entry in entries {
        if entry.outcome != EntryOutcome::VerifiedOk {
            continue;
        }
        match (
            entry.completion.as_deref(),
            entry.completion_basis.as_deref(),
        ) {
            (Some(completion), Some(basis)) => {
                if !COMPLETION_BASIS_TOKENS.contains(&basis) {
                    return Err(format!("unknown completion_basis token {basis}"));
                }
                *completion_basis.entry(basis.to_string()).or_default() += 1;
                match completion {
                    "complete" => {
                        if !entry.incomplete_reasons.is_empty() {
                            return Err("a complete entry must not carry incomplete_reasons".into());
                        }
                        entries_complete += 1;
                    }
                    "incomplete" => {
                        if entry.incomplete_reasons.is_empty() {
                            return Err("an incomplete entry must carry incomplete_reasons".into());
                        }
                        entries_incomplete += 1;
                    }
                    other => return Err(format!("unknown completion token {other}")),
                }
            }
            (None, None) => {
                if !entry.incomplete_reasons.is_empty() {
                    return Err(
                        "a missing-completion entry must not carry incomplete_reasons".into(),
                    );
                }
                entries_missing_capture += 1;
            }
            _ => return Err("completion and completion_basis must be captured together".into()),
        }
        for reason in &entry.incomplete_reasons {
            if !INCOMPLETE_REASON_TOKENS.contains(&reason.as_str()) {
                return Err(format!("unknown incomplete_reason token {reason}"));
            }
            *incomplete_reasons.entry(reason.clone()).or_default() += 1;
        }
        if let Some(token) = entry.this_document_reference {
            *context_result_distribution
                .entry(token.as_str().to_string())
                .or_default() += 1;
        }
        for (family, yield_count) in &entry.family_yields {
            if !FAMILIES.contains(&family.as_str()) {
                return Err(format!("unknown family_yields token {family}"));
            }
            *per_family_yields.entry(family.clone()).or_default() += yield_count;
        }
    }

    let verified = entries_complete
        .saturating_add(entries_incomplete)
        .saturating_add(entries_missing_capture);
    if verified != structural.verified_ok {
        return Err(format!(
            "completion buckets ({verified}) must equal verified_ok ({})",
            structural.verified_ok
        ));
    }
    let observed_completion_ratio_ppm = entries_complete
        .saturating_mul(1_000_000)
        .checked_div(verified)
        .unwrap_or(0);

    let mut below_expected_yield: Vec<String> = thresholds
        .min_family_yields
        .iter()
        .filter_map(|(family, floor)| {
            let observed = per_family_yields.get(family).copied().unwrap_or(0);
            (observed < *floor).then(|| family.clone())
        })
        .collect();
    below_expected_yield.sort();

    Ok(AnalysisCompletionSection {
        entries_total: entries.len() as u64,
        entries_complete,
        entries_incomplete,
        entries_missing_capture,
        observed_completion_ratio_ppm,
        min_completion_ratio_ppm: thresholds.min_completion_ratio_ppm,
        completion_basis,
        incomplete_reasons,
        context_result_distribution,
        per_family_yields,
        min_family_yields: thresholds.min_family_yields.clone(),
        below_expected_yield,
    })
}

fn build_provider_coverage(
    entries: &[AcceptanceEntry],
    declared_roots: &[DeclaredRoot],
    provider_candidate_counts: &BTreeMap<String, u64>,
) -> Result<ProviderCoverageSection, String> {
    let mut declared: BTreeSet<String> = BTreeSet::new();
    for root in declared_roots {
        let token = root.provider.as_str();
        if !PROVIDER_TOKENS.contains(&token) {
            return Err(format!("unknown declared provider {token}"));
        }
        if !declared.insert(token.to_string()) {
            return Err(format!("duplicate declared provider {token}"));
        }
    }
    if declared.is_empty() {
        return Err("provider coverage must declare at least one provider".into());
    }

    let mut sampled: BTreeMap<String, u64> = BTreeMap::new();
    for entry in entries {
        let token = entry.provider.as_str().to_string();
        if !declared.contains(&token) {
            return Err(format!("entry provider {token} is not declared"));
        }
        *sampled.entry(token).or_default() += 1;
    }

    let mut covered = Vec::new();
    let mut uncovered = Vec::new();
    for provider in &declared {
        let count = sampled.get(provider).copied().unwrap_or(0);
        if count > 0 {
            covered.push(provider.clone());
        } else {
            let candidates = provider_candidate_counts
                .get(provider)
                .copied()
                .unwrap_or(0);
            let uncovered_reason = if candidates == 0 {
                UncoveredReason::NoCandidates
            } else {
                UncoveredReason::NoSelection
            };
            uncovered.push(UncoveredProvider {
                provider: provider.clone(),
                uncovered_reason,
            });
        }
    }

    Ok(ProviderCoverageSection {
        declared: declared.into_iter().collect(),
        covered,
        uncovered,
    })
}

fn transport_verdict(structural: &StructuralIntegritySection) -> Verdict {
    let hard_fail = structural.tamper_probe_false_negative > 0
        || structural.manifest_pin_mismatch > 0
        || structural.verify_refused > 0;
    if hard_fail {
        return Verdict::Fail;
    }
    if structural.structural_failures > 0 {
        return Verdict::NeedsAttention;
    }
    Verdict::Pass
}

fn completion_verdict(section: &AnalysisCompletionSection) -> CompletionVerdict {
    let verified = section
        .entries_complete
        .saturating_add(section.entries_incomplete)
        .saturating_add(section.entries_missing_capture);
    if section.entries_missing_capture > 0 || verified == 0 {
        return CompletionVerdict::NeedsAttention;
    }
    if section.entries_incomplete > 0
        || section.observed_completion_ratio_ppm < section.min_completion_ratio_ppm
        || !section.below_expected_yield.is_empty()
    {
        return CompletionVerdict::Incomplete;
    }
    CompletionVerdict::Complete
}

// ------------------------------------------------------------ validation #

fn validate_structural_integrity(section: &StructuralIntegritySection) -> Result<(), String> {
    if section.entries_total == 0 {
        return Err("structural_integrity.entries_total must be positive".into());
    }
    let failures = section
        .read_back_refused
        .saturating_add(section.verify_refused)
        .saturating_add(section.decode_refused)
        .saturating_add(section.gate_refused)
        .saturating_add(section.analysis_refused)
        .saturating_add(section.limit_line_bytes)
        .saturating_add(section.limit_records)
        .saturating_add(section.manifest_pin_mismatch);
    if section.structural_failures != failures {
        return Err("structural_failures must equal the outcome sum".into());
    }
    if section.entries_total != section.verified_ok.saturating_add(failures) {
        return Err("entries_total must equal verified_ok + structural_failures".into());
    }
    if section.pass != (section.structural_failures == 0) {
        return Err("structural_integrity.pass must mirror structural_failures == 0".into());
    }
    for key in section.verify_codes.keys() {
        if !V2_VERIFY_CODE_TOKENS.contains(&key.as_str()) {
            return Err(format!("unknown verify_code token {key}"));
        }
    }
    let code_sum: u64 = section.verify_codes.values().copied().sum();
    if code_sum != section.verify_refused {
        return Err("verify_codes must sum to verify_refused".into());
    }
    if section
        .tamper_probe_detected
        .saturating_add(section.tamper_probe_false_negative)
        != section.tamper_probe_entries
    {
        return Err("tamper probe detected + false_negative must equal the subset size".into());
    }
    Ok(())
}

fn validate_completion(
    section: &AnalysisCompletionSection,
    structural: &StructuralIntegritySection,
) -> Result<(), String> {
    if section.entries_total != structural.entries_total {
        return Err("completion entries_total must equal structural entries_total".into());
    }
    let verified = section
        .entries_complete
        .saturating_add(section.entries_incomplete)
        .saturating_add(section.entries_missing_capture);
    if verified != structural.verified_ok {
        return Err("completion buckets must sum to verified_ok".into());
    }
    if section.min_completion_ratio_ppm > 1_000_000 {
        return Err("completion min_completion_ratio_ppm must not exceed 1_000_000".into());
    }
    let captured = section
        .entries_complete
        .saturating_add(section.entries_incomplete);
    let basis_sum: u64 = section.completion_basis.values().copied().sum();
    if basis_sum != captured {
        return Err("completion_basis histogram must sum to the captured entries".into());
    }
    for key in section.completion_basis.keys() {
        if !COMPLETION_BASIS_TOKENS.contains(&key.as_str()) {
            return Err(format!("unknown completion_basis token {key}"));
        }
    }
    for key in section.incomplete_reasons.keys() {
        if !INCOMPLETE_REASON_TOKENS.contains(&key.as_str()) {
            return Err(format!("unknown incomplete_reason token {key}"));
        }
    }
    if section.incomplete_reasons.is_empty() != (section.entries_incomplete == 0) {
        return Err("incomplete_reasons must be empty iff entries_incomplete == 0".into());
    }
    for key in section.context_result_distribution.keys() {
        if !CONTEXT_RESULT_TOKENS.contains(&key.as_str()) {
            return Err(format!("unknown context_result token {key}"));
        }
    }
    for key in section
        .per_family_yields
        .keys()
        .chain(section.min_family_yields.keys())
    {
        if !FAMILIES.contains(&key.as_str()) {
            return Err(format!("unknown family token {key}"));
        }
    }
    let mut expected_below: Vec<String> = section
        .min_family_yields
        .iter()
        .filter_map(|(family, floor)| {
            let observed = section.per_family_yields.get(family).copied().unwrap_or(0);
            (observed < *floor).then(|| family.clone())
        })
        .collect();
    expected_below.sort();
    if section.below_expected_yield != expected_below {
        return Err("below_expected_yield disagrees with the declared family floors".into());
    }
    let expected_ratio = section
        .entries_complete
        .saturating_mul(1_000_000)
        .checked_div(verified)
        .unwrap_or(0);
    if section.observed_completion_ratio_ppm != expected_ratio {
        return Err("observed_completion_ratio_ppm disagrees with the captured buckets".into());
    }
    Ok(())
}

fn validate_provider_coverage(section: &ProviderCoverageSection) -> Result<(), String> {
    if section.declared.is_empty() {
        return Err("provider_coverage.declared must not be empty".into());
    }
    let mut declared: BTreeSet<&str> = BTreeSet::new();
    for provider in &section.declared {
        if !PROVIDER_TOKENS.contains(&provider.as_str()) {
            return Err(format!("unknown declared provider {provider}"));
        }
        if !declared.insert(provider.as_str()) {
            return Err(format!("duplicate declared provider {provider}"));
        }
    }
    let mut covered: BTreeSet<&str> = BTreeSet::new();
    for provider in &section.covered {
        if !declared.contains(provider.as_str()) {
            return Err(format!("covered provider {provider} is not declared"));
        }
        if !covered.insert(provider.as_str()) {
            return Err(format!("duplicate covered provider {provider}"));
        }
    }
    let mut uncovered: BTreeSet<&str> = BTreeSet::new();
    for entry in &section.uncovered {
        if !declared.contains(entry.provider.as_str()) {
            return Err(format!(
                "uncovered provider {} is not declared",
                entry.provider
            ));
        }
        if !uncovered.insert(entry.provider.as_str()) {
            return Err(format!("duplicate uncovered provider {}", entry.provider));
        }
        if covered.contains(entry.provider.as_str()) {
            return Err(format!(
                "provider {} cannot be both covered and uncovered",
                entry.provider
            ));
        }
    }
    if covered.len() + uncovered.len() != declared.len() {
        return Err("covered + uncovered must partition the declared providers".into());
    }
    Ok(())
}

fn check_count_hash_only(report: &AcceptanceReportV2) -> Result<(), String> {
    let value = serde_json::to_value(report)
        .map_err(|error| format!("v2 report is not serializable: {error}"))?;
    check_value_strings(&value)
}

fn check_value_strings(value: &Value) -> Result<(), String> {
    match value {
        Value::String(text) => {
            if !text.is_ascii() {
                return Err("v2 report contains a non-ASCII string".into());
            }
            if text.bytes().any(|byte| byte.is_ascii_control()) {
                return Err("v2 report contains a control character".into());
            }
            if text.len() > MAX_V2_STRING_BYTES {
                return Err(format!(
                    "v2 report string exceeds {MAX_V2_STRING_BYTES} bytes"
                ));
            }
        }
        Value::Object(members) => {
            for (key, child) in members {
                check_value_strings(&Value::String(key.clone()))?;
                check_value_strings(child)?;
            }
        }
        Value::Array(items) => {
            for child in items {
                check_value_strings(child)?;
            }
        }
        _ => {}
    }
    Ok(())
}

// ------------------------------------------------------------- loading #

fn parse_json(text: &str) -> Result<Value, String> {
    let value: Value =
        serde_json::from_str(text).map_err(|error| format!("invalid JSON: {error}"))?;
    reject_forbidden_keys(&value, "$")?;
    reject_path_like_strings(&value, "$")?;
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

fn reject_path_like_strings(value: &Value, path: &str) -> Result<(), String> {
    match value {
        Value::String(text) => {
            if text.starts_with('/') {
                return Err(format!("{path}: absolute path is forbidden"));
            }
            if text.contains('\\') {
                return Err(format!("{path}: backslash path is forbidden"));
            }
            if text.split('/').any(|component| component == "..") {
                return Err(format!("{path}: '..' path traversal is forbidden"));
            }
        }
        Value::Object(members) => {
            for (key, child) in members {
                reject_path_like_strings(child, &format!("{path}.{key}"))?;
            }
        }
        Value::Array(items) => {
            for (index, child) in items.iter().enumerate() {
                reject_path_like_strings(child, &format!("{path}[{index}]"))?;
            }
        }
        _ => {}
    }
    Ok(())
}
