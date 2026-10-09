//! Deterministic, bounded retrieval metrics for the offline citation pipeline.
//!
//! This module is the serde-free computation surface described by the S04
//! contract `prd/retrieval/rust_retrieval_metrics_contract.md`
//! (`retrieval-metrics/rust-v1`). It turns the closed observables of the S02
//! offline retrieval surface ([`OfflineRetrievalCase`], [`OfflineCaseOutcome`])
//! into a bounded quality report and a reproducible structural runtime profile,
//! plus a separate non-asserted host-boundary wall-clock observation.
//!
//! Boundaries (D537/D714/D719 compatible, frozen in the contract):
//!
//! - The metrics are **slice-level**, not product retrieval quality. They carry
//!   an explicit non-claims list ([`RETRIEVAL_METRICS_NON_CLAIMS`]).
//! - There is no new crate dependency, no `io`, no network, and no `time`
//!   inside this library: wall-clock is measured by the caller (the integration
//!   test) and recorded as [`RetrievalObservedTiming`] with
//!   `reproducible: false` / `asserted: false`.
//! - Every emitted value is a counter, a ratio, or a closed string. No raw
//!   decoded legal text, prompt, vector, secret, or generated answer prose can
//!   appear in any output of this module.
//! - The quality metric set and the runtime profile are closed; both are exactly
//!   the fields declared by the contract, and a zero denominator yields `0.0`
//!   as closed behavior (never a panic, never a fabricated `1.0`).

use std::collections::BTreeMap;

use ln_decode::cleaned_wire::CleanedProjection;

use crate::retrieval_offline::{
    OfflineCaseOutcome, OfflineExpectedResult, OfflineRetrievalCase, OfflineSelectionReason,
    ProjectionGraphResolver, RetrievalQueryKind,
};
use crate::retrieval_output::OutputVerdict;

/// Report schema version emitted in [`RetrievalMetricsReport::schema_version`].
pub const RETRIEVAL_METRICS_SCHEMA_VERSION: &str = "retrieval-metrics/rust-v1";

/// The closed non-claims list carried by every [`RetrievalMetricsReport`].
///
/// These are stable, bounded `&'static` tokens: they never carry document text
/// and they name exactly what the slice-level metrics do not prove.
pub const RETRIEVAL_METRICS_NON_CLAIMS: &[&str] = &[
    "does_not_prove_product_retrieval_quality",
    "does_not_prove_legal_answer_correctness",
    "does_not_prove_ranking_mrr_recall_at_k_or_embedding_quality",
    "does_not_prove_parser_completeness",
    "does_not_prove_runtime_throughput_latency_or_falkordb_readiness",
    "does_not_prove_corpus_coverage_three_documents_are_not_the_corpus",
    "does_not_close_gate_g008_or_gate_g011",
    "does_not_clear_the_d7_missing_anchor_quarantine",
    "does_not_write_regenerate_or_repair_the_frozen_architecture_registry_d537",
    "host_boundary_wall_clock_timing_is_reproducible_false_and_asserted_false",
];

/// Closed metric kind (contract `quality` | `runtime`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RetrievalMetricKind {
    /// Quality metrics (selection correctness) over the declared slice.
    Quality,
    /// Structural runtime profile over the declared slice.
    Runtime,
}

impl RetrievalMetricKind {
    /// Every kind, in contract order.
    pub const ALL: [Self; 2] = [Self::Quality, Self::Runtime];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Quality => "quality",
            Self::Runtime => "runtime",
        }
    }
}

/// Closed metric boundary. The only declared boundary is `slice`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RetrievalMetricBoundary {
    /// Slice-level metrics over the declared documents, not the corpus.
    Slice,
}

impl RetrievalMetricBoundary {
    /// Every boundary, in contract order.
    pub const ALL: [Self; 1] = [Self::Slice];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Slice => "slice",
        }
    }
}

/// Closed reproducibility marker.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RetrievalMetricReproducibility {
    /// Reproducible evidence (the structural runtime profile).
    Reproducible,
    /// Host-boundary wall-clock observed but never asserted.
    HostBoundaryObservedUnasserted,
}

impl RetrievalMetricReproducibility {
    /// Every marker, in contract order.
    pub const ALL: [Self; 2] = [Self::Reproducible, Self::HostBoundaryObservedUnasserted];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Reproducible => "reproducible",
            Self::HostBoundaryObservedUnasserted => "host_boundary_observed_unasserted",
        }
    }
}

/// Closed identity of one quality metric, used by threshold breaches.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RetrievalQualityMetricId {
    SelectionAccuracy,
    PositiveSelectionRate,
    ScopedNoAnswerAccuracy,
    AmbiguousRejectionRate,
    UnsafeRejectionRate,
    UnresolvableCitationRejectionRate,
}

impl RetrievalQualityMetricId {
    /// Every metric identity, in contract order.
    pub const ALL: [Self; 6] = [
        Self::SelectionAccuracy,
        Self::PositiveSelectionRate,
        Self::ScopedNoAnswerAccuracy,
        Self::AmbiguousRejectionRate,
        Self::UnsafeRejectionRate,
        Self::UnresolvableCitationRejectionRate,
    ];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::SelectionAccuracy => "selection_accuracy",
            Self::PositiveSelectionRate => "positive_selection_rate",
            Self::ScopedNoAnswerAccuracy => "scoped_no_answer_accuracy",
            Self::AmbiguousRejectionRate => "ambiguous_rejection_rate",
            Self::UnsafeRejectionRate => "unsafe_rejection_rate",
            Self::UnresolvableCitationRejectionRate => "unresolvable_citation_rejection_rate",
        }
    }
}

/// The observed result class of one outcome.
///
/// This is the contract's `observed_class(outcome)`: it is derived **only** from
/// the closed `validator_verdict`, mirroring the three-class
/// [`OfflineExpectedResult`] vocabulary. A proof-level rejection
/// (`validator_verdict == None`) is classed as [`OfflineExpectedResult::Rejected`].
pub fn observed_class(outcome: &OfflineCaseOutcome) -> OfflineExpectedResult {
    match outcome.validator_verdict {
        Some(OutputVerdict::Accepted) => OfflineExpectedResult::Selected,
        Some(OutputVerdict::AcceptedScopedNoAnswer) => OfflineExpectedResult::ScopedNoAnswer,
        Some(OutputVerdict::Rejected) | None => OfflineExpectedResult::Rejected,
    }
}

/// The closed quality metric set plus its case-class counters.
#[derive(Debug, Clone, PartialEq)]
pub struct RetrievalQualityMetrics {
    /// Cases whose observed class equals the expected class, over `total_cases`.
    pub selection_accuracy: f64,
    /// Selected cases, over `positive_cases`.
    pub positive_selection_rate: f64,
    /// Scoped-no-answer cases, over `scoped_cases`.
    pub scoped_no_answer_accuracy: f64,
    /// Ambiguous-lookup rejections, over `ambiguous_cases`.
    pub ambiguous_rejection_rate: f64,
    /// Invalid-candidate rejections, over `unsafe_cases`.
    pub unsafe_rejection_rate: f64,
    /// Unresolvable-citation rejections, over `unresolvable_cases`.
    pub unresolvable_citation_rejection_rate: f64,
    /// Number of cases evaluated.
    pub total_cases: usize,
    /// Cases with `expected_result == Selected`.
    pub positive_cases: usize,
    /// Cases with `expected_result == ScopedNoAnswer`.
    pub scoped_cases: usize,
    /// Cases with `query_kind == AmbiguousLookup`.
    pub ambiguous_cases: usize,
    /// Cases with `query_kind == InvalidCandidate`.
    pub unsafe_cases: usize,
    /// Outcomes with `selection_reason == UnresolvedCandidateEvidence`.
    pub unresolvable_cases: usize,
    /// Cases whose observed class differs from the expected class.
    pub mismatch_count: usize,
}

impl RetrievalQualityMetrics {
    /// The observed value for one closed metric identity.
    pub fn value(&self, metric: RetrievalQualityMetricId) -> f64 {
        match metric {
            RetrievalQualityMetricId::SelectionAccuracy => self.selection_accuracy,
            RetrievalQualityMetricId::PositiveSelectionRate => self.positive_selection_rate,
            RetrievalQualityMetricId::ScopedNoAnswerAccuracy => self.scoped_no_answer_accuracy,
            RetrievalQualityMetricId::AmbiguousRejectionRate => self.ambiguous_rejection_rate,
            RetrievalQualityMetricId::UnsafeRejectionRate => self.unsafe_rejection_rate,
            RetrievalQualityMetricId::UnresolvableCitationRejectionRate => {
                self.unresolvable_citation_rejection_rate
            }
        }
    }
}

/// Closed-behavior ratio: a zero denominator yields `0.0`, never a panic.
fn ratio(numerator: usize, denominator: usize) -> f64 {
    if denominator == 0 {
        0.0
    } else {
        numerator as f64 / denominator as f64
    }
}

/// Compute the six closed quality metrics from the declared cases and outcomes.
///
/// Cases and outcomes are joined by `case_id`. A case without a matching outcome
/// is classed as `Rejected` (fail-closed); outcomes without a matching case are
/// only consulted by the unresolvable-citation metric, whose denominator is the
/// outcome set itself. Every value is deterministic (integer counts only) and
/// carries no raw text.
pub fn compute_retrieval_quality_metrics(
    cases: &[OfflineRetrievalCase],
    outcomes: &[OfflineCaseOutcome],
) -> RetrievalQualityMetrics {
    let outcomes_by_case: BTreeMap<&str, &OfflineCaseOutcome> = outcomes
        .iter()
        .map(|outcome| (outcome.case_id.as_str(), outcome))
        .collect();

    let mut total_cases = 0usize;
    let mut positive_cases = 0usize;
    let mut scoped_cases = 0usize;
    let mut ambiguous_cases = 0usize;
    let mut unsafe_cases = 0usize;
    let mut mismatch_count = 0usize;

    let mut selection_hits = 0usize;
    let mut positive_hits = 0usize;
    let mut scoped_hits = 0usize;
    let mut ambiguous_hits = 0usize;
    let mut unsafe_hits = 0usize;

    for case in cases {
        total_cases += 1;
        // A missing outcome is a proof-level rejection, fail-closed.
        let observed = outcomes_by_case
            .get(case.case_id.as_str())
            .map(|outcome| observed_class(outcome))
            .unwrap_or(OfflineExpectedResult::Rejected);
        let matched = observed == case.expected_result;
        if matched {
            selection_hits += 1;
        } else {
            mismatch_count += 1;
        }
        match case.expected_result {
            OfflineExpectedResult::Selected => {
                positive_cases += 1;
                if observed == OfflineExpectedResult::Selected {
                    positive_hits += 1;
                }
            }
            OfflineExpectedResult::ScopedNoAnswer => {
                scoped_cases += 1;
                if observed == OfflineExpectedResult::ScopedNoAnswer {
                    scoped_hits += 1;
                }
            }
            OfflineExpectedResult::Rejected => {}
        }
        if case.query_kind == RetrievalQueryKind::AmbiguousLookup {
            ambiguous_cases += 1;
            let reason = outcomes_by_case
                .get(case.case_id.as_str())
                .map(|outcome| outcome.selection_reason);
            if reason == Some(OfflineSelectionReason::AmbiguousCandidateSet)
                && observed == OfflineExpectedResult::Rejected
            {
                ambiguous_hits += 1;
            }
        }
        if case.query_kind == RetrievalQueryKind::InvalidCandidate {
            unsafe_cases += 1;
            let reason = outcomes_by_case
                .get(case.case_id.as_str())
                .map(|outcome| outcome.selection_reason);
            if reason == Some(OfflineSelectionReason::UnsafePayloadRejected)
                && observed == OfflineExpectedResult::Rejected
            {
                unsafe_hits += 1;
            }
        }
    }

    // The unresolvable-citation metric is defined over the outcome set: its
    // denominator is the outcomes carrying the unresolved evidence reason.
    let mut unresolvable_cases = 0usize;
    let mut unresolvable_hits = 0usize;
    for outcome in outcomes {
        if outcome.selection_reason == OfflineSelectionReason::UnresolvedCandidateEvidence {
            unresolvable_cases += 1;
            if observed_class(outcome) == OfflineExpectedResult::Rejected {
                unresolvable_hits += 1;
            }
        }
    }

    RetrievalQualityMetrics {
        selection_accuracy: ratio(selection_hits, total_cases),
        positive_selection_rate: ratio(positive_hits, positive_cases),
        scoped_no_answer_accuracy: ratio(scoped_hits, scoped_cases),
        ambiguous_rejection_rate: ratio(ambiguous_hits, ambiguous_cases),
        unsafe_rejection_rate: ratio(unsafe_hits, unsafe_cases),
        unresolvable_citation_rejection_rate: ratio(unresolvable_hits, unresolvable_cases),
        total_cases,
        positive_cases,
        scoped_cases,
        ambiguous_cases,
        unsafe_cases,
        unresolvable_cases,
        mismatch_count,
    }
}

/// The closed, reproducible structural runtime profile of the offline pipeline.
///
/// Every counter is a deterministic count over the declared slice; the profile
/// carries no timing, throughput, or service claim and two runs over the same
/// slice must be equal.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RetrievalRuntimeProfile {
    /// Declared slice documents driven through the enabled pipeline.
    pub documents_processed: usize,
    /// Total view nodes across the documents' cleaned projections.
    pub projected_views: usize,
    /// Total segment nodes across the documents' cleaned projections.
    pub projected_segments: usize,
    /// Total evidence spans minted by the per-document resolvers.
    pub resolver_evidence_spans: usize,
    /// Total declared cases run.
    pub cases_run: usize,
}

impl RetrievalRuntimeProfile {
    /// The profile's reproducibility marker: always reproducible.
    pub fn reproducibility(&self) -> RetrievalMetricReproducibility {
        RetrievalMetricReproducibility::Reproducible
    }

    /// Accumulate one document's structural counts into the profile.
    pub fn record_counts(&mut self, views: usize, segments: usize, evidence_spans: usize) {
        self.documents_processed += 1;
        self.projected_views += views;
        self.projected_segments += segments;
        self.resolver_evidence_spans += evidence_spans;
    }

    /// Accumulate one document's cleaned projection and its resolver.
    pub fn record_document(
        &mut self,
        projection: &CleanedProjection,
        resolver: &ProjectionGraphResolver,
    ) {
        self.record_counts(
            projection.projection.views.len(),
            projection.projection.segments.len(),
            resolver.evidence_span_ids().count(),
        );
    }

    /// Build a profile from a single document and its resolver.
    pub fn from_document(
        projection: &CleanedProjection,
        resolver: &ProjectionGraphResolver,
        cases_run: usize,
    ) -> Self {
        let mut profile = Self::default();
        profile.record_document(projection, resolver);
        profile.cases_run = cases_run;
        profile
    }

    /// Build a profile from many documents, each with its own resolver.
    pub fn from_documents<'a, I>(documents: I, cases_run: usize) -> Self
    where
        I: IntoIterator<Item = (&'a CleanedProjection, &'a ProjectionGraphResolver)>,
    {
        let mut profile = Self::default();
        for (projection, resolver) in documents {
            profile.record_document(projection, resolver);
        }
        profile.cases_run = cases_run;
        profile
    }
}

/// A host-boundary wall-clock observation: measured, reported, never asserted.
///
/// `reproducible` and `asserted` are fixed to `false` by construction and are
/// exposed read-only, so a caller cannot turn an environment-dependent
/// observation into reproducible evidence or a timing gate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RetrievalObservedTiming {
    /// Number of measured iterations.
    pub iterations: usize,
    /// Minimum wall-clock duration across iterations, in milliseconds.
    pub elapsed_ms_min: u64,
    /// Median wall-clock duration across iterations, in milliseconds.
    pub elapsed_ms_median: u64,
    reproducible: bool,
    asserted: bool,
}

impl RetrievalObservedTiming {
    /// Record an observation. `reproducible` and `asserted` are always `false`.
    pub fn new(iterations: usize, elapsed_ms_min: u64, elapsed_ms_median: u64) -> Self {
        Self {
            iterations,
            elapsed_ms_min,
            elapsed_ms_median,
            reproducible: false,
            asserted: false,
        }
    }

    /// The observation's reproducibility marker: always host-boundary.
    pub fn reproducibility(&self) -> RetrievalMetricReproducibility {
        RetrievalMetricReproducibility::HostBoundaryObservedUnasserted
    }

    /// Always `false`: host-boundary timing is not reproducible evidence.
    pub fn reproducible(&self) -> bool {
        self.reproducible
    }

    /// Always `false`: the test never asserts a timing threshold.
    pub fn asserted(&self) -> bool {
        self.asserted
    }
}

/// One quality-threshold breach: a closed metric identity and its gap.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RetrievalMetricBreach {
    /// The closed metric identity that breached its threshold.
    pub metric: RetrievalQualityMetricId,
    /// The declared threshold.
    pub threshold: f64,
    /// The observed value.
    pub observed: f64,
}

/// The declared quality thresholds. All six are `1.0` on the declared slice.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct RetrievalMetricThreshold {
    pub selection_accuracy: f64,
    pub positive_selection_rate: f64,
    pub scoped_no_answer_accuracy: f64,
    pub ambiguous_rejection_rate: f64,
    pub unsafe_rejection_rate: f64,
    pub unresolvable_citation_rejection_rate: f64,
}

impl RetrievalMetricThreshold {
    /// The declared slice thresholds: all quality metrics must be `1.0`.
    pub const SLICE: Self = Self {
        selection_accuracy: 1.0,
        positive_selection_rate: 1.0,
        scoped_no_answer_accuracy: 1.0,
        ambiguous_rejection_rate: 1.0,
        unsafe_rejection_rate: 1.0,
        unresolvable_citation_rejection_rate: 1.0,
    };

    /// The declared threshold for one closed metric identity.
    pub fn value(&self, metric: RetrievalQualityMetricId) -> f64 {
        match metric {
            RetrievalQualityMetricId::SelectionAccuracy => self.selection_accuracy,
            RetrievalQualityMetricId::PositiveSelectionRate => self.positive_selection_rate,
            RetrievalQualityMetricId::ScopedNoAnswerAccuracy => self.scoped_no_answer_accuracy,
            RetrievalQualityMetricId::AmbiguousRejectionRate => self.ambiguous_rejection_rate,
            RetrievalQualityMetricId::UnsafeRejectionRate => self.unsafe_rejection_rate,
            RetrievalQualityMetricId::UnresolvableCitationRejectionRate => {
                self.unresolvable_citation_rejection_rate
            }
        }
    }

    /// The closed list of metrics whose observed value is below threshold.
    ///
    /// The order is fixed by [`RetrievalQualityMetricId::ALL`], so the breach
    /// list is deterministic. An empty list means every metric meets its
    /// threshold.
    pub fn breaches(&self, metrics: &RetrievalQualityMetrics) -> Vec<RetrievalMetricBreach> {
        RetrievalQualityMetricId::ALL
            .iter()
            .filter_map(|metric| {
                let threshold = self.value(*metric);
                let observed = metrics.value(*metric);
                if observed < threshold {
                    Some(RetrievalMetricBreach {
                        metric: *metric,
                        threshold,
                        observed,
                    })
                } else {
                    None
                }
            })
            .collect()
    }
}

/// The bounded metrics report: the only observable surface of this module.
#[derive(Debug, Clone, PartialEq)]
pub struct RetrievalMetricsReport {
    /// Report schema version ([`RETRIEVAL_METRICS_SCHEMA_VERSION`]).
    pub schema_version: &'static str,
    /// Closed metric kind.
    pub kind: RetrievalMetricKind,
    /// Closed metric boundary.
    pub boundary: RetrievalMetricBoundary,
    /// The closed quality metric set.
    pub quality: RetrievalQualityMetrics,
    /// The reproducible structural runtime profile.
    pub runtime_profile: RetrievalRuntimeProfile,
    /// The non-asserted host-boundary timing observation, when measured.
    pub observed_timing: Option<RetrievalObservedTiming>,
    /// The closed non-claims list ([`RETRIEVAL_METRICS_NON_CLAIMS`]).
    pub non_claims: &'static [&'static str],
}

impl RetrievalMetricsReport {
    /// Build a slice-bound report with the frozen schema version and non-claims.
    pub fn new(
        kind: RetrievalMetricKind,
        quality: RetrievalQualityMetrics,
        runtime_profile: RetrievalRuntimeProfile,
        observed_timing: Option<RetrievalObservedTiming>,
    ) -> Self {
        Self {
            schema_version: RETRIEVAL_METRICS_SCHEMA_VERSION,
            kind,
            boundary: RetrievalMetricBoundary::Slice,
            quality,
            runtime_profile,
            observed_timing,
            non_claims: RETRIEVAL_METRICS_NON_CLAIMS,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// One authored case with a closed query kind and expected result.
    fn case(
        case_id: &str,
        query_kind: RetrievalQueryKind,
        expected_result: OfflineExpectedResult,
    ) -> OfflineRetrievalCase {
        OfflineRetrievalCase {
            case_id: case_id.to_owned(),
            query_id: format!("Q-{case_id}"),
            scope_id: "SCOPE-test".to_owned(),
            as_of_date: "2024-06-15".to_owned(),
            query_kind,
            selector: "semantic:body".to_owned(),
            expected_result,
        }
    }

    /// One authored outcome with a closed selection reason and validator verdict.
    fn outcome(
        case_id: &str,
        reason: OfflineSelectionReason,
        verdict: Option<OutputVerdict>,
    ) -> OfflineCaseOutcome {
        OfflineCaseOutcome {
            case_id: case_id.to_owned(),
            query_id: format!("Q-{case_id}"),
            selection_reason: reason,
            validator_verdict: verdict,
            primary_code: None,
            expected_result: OfflineExpectedResult::Rejected,
            matched: true,
        }
    }

    /// The deterministic synthetic corpus covering every declared class.
    fn full_cover_corpus() -> (Vec<OfflineRetrievalCase>, Vec<OfflineCaseOutcome>) {
        let cases = vec![
            case(
                "c1",
                RetrievalQueryKind::ExactNodeAddress,
                OfflineExpectedResult::Selected,
            ),
            case(
                "c2",
                RetrievalQueryKind::MarkerKind,
                OfflineExpectedResult::Selected,
            ),
            case(
                "c3",
                RetrievalQueryKind::MarkerKind,
                OfflineExpectedResult::ScopedNoAnswer,
            ),
            case(
                "c4",
                RetrievalQueryKind::MarkerKind,
                OfflineExpectedResult::Rejected,
            ),
            case(
                "c5",
                RetrievalQueryKind::InvalidCandidate,
                OfflineExpectedResult::Rejected,
            ),
            case(
                "c6",
                RetrievalQueryKind::ExactNodeAddress,
                OfflineExpectedResult::Rejected,
            ),
            case(
                "c7",
                RetrievalQueryKind::ScopedNoCandidate,
                OfflineExpectedResult::ScopedNoAnswer,
            ),
            case(
                "c8",
                RetrievalQueryKind::AmbiguousLookup,
                OfflineExpectedResult::Rejected,
            ),
        ];
        let outcomes = vec![
            outcome(
                "c1",
                OfflineSelectionReason::ExactNodeAddressMatch,
                Some(OutputVerdict::Accepted),
            ),
            outcome(
                "c2",
                OfflineSelectionReason::MarkerKindMatch,
                Some(OutputVerdict::Accepted),
            ),
            outcome(
                "c3",
                OfflineSelectionReason::ScopedNoCandidate,
                Some(OutputVerdict::AcceptedScopedNoAnswer),
            ),
            outcome("c4", OfflineSelectionReason::AmbiguousCandidateSet, None),
            outcome("c5", OfflineSelectionReason::UnsafePayloadRejected, None),
            outcome(
                "c6",
                OfflineSelectionReason::UnresolvedCandidateEvidence,
                Some(OutputVerdict::Rejected),
            ),
            outcome(
                "c7",
                OfflineSelectionReason::ScopedNoCandidate,
                Some(OutputVerdict::AcceptedScopedNoAnswer),
            ),
            outcome("c8", OfflineSelectionReason::AmbiguousCandidateSet, None),
        ];
        (cases, outcomes)
    }

    #[test]
    fn observed_class_is_derived_only_from_the_closed_verdict() {
        assert_eq!(
            observed_class(&outcome(
                "x",
                OfflineSelectionReason::MarkerKindMatch,
                Some(OutputVerdict::Accepted)
            )),
            OfflineExpectedResult::Selected
        );
        assert_eq!(
            observed_class(&outcome(
                "x",
                OfflineSelectionReason::ScopedNoCandidate,
                Some(OutputVerdict::AcceptedScopedNoAnswer)
            )),
            OfflineExpectedResult::ScopedNoAnswer
        );
        assert_eq!(
            observed_class(&outcome(
                "x",
                OfflineSelectionReason::UnsafePayloadRejected,
                None
            )),
            OfflineExpectedResult::Rejected
        );
        assert_eq!(
            observed_class(&outcome(
                "x",
                OfflineSelectionReason::AmbiguousCandidateSet,
                Some(OutputVerdict::Rejected)
            )),
            OfflineExpectedResult::Rejected
        );
    }

    #[test]
    fn full_cover_corpus_meets_every_threshold() {
        let (cases, outcomes) = full_cover_corpus();
        let metrics = compute_retrieval_quality_metrics(&cases, &outcomes);
        assert_eq!(metrics.total_cases, 8);
        assert_eq!(metrics.positive_cases, 2);
        assert_eq!(metrics.scoped_cases, 2);
        assert_eq!(metrics.ambiguous_cases, 1);
        assert_eq!(metrics.unsafe_cases, 1);
        assert_eq!(metrics.unresolvable_cases, 1);
        assert_eq!(metrics.mismatch_count, 0);
        for metric in RetrievalQualityMetricId::ALL {
            assert_eq!(
                metrics.value(metric),
                1.0,
                "metric {} must be 1.0 on the full-cover corpus",
                metric.as_str()
            );
        }
        assert!(RetrievalMetricThreshold::SLICE
            .breaches(&metrics)
            .is_empty());
    }

    #[test]
    fn zero_denominator_is_closed_behavior_not_a_panic() {
        let metrics = compute_retrieval_quality_metrics(&[], &[]);
        assert_eq!(metrics.total_cases, 0);
        assert_eq!(metrics.mismatch_count, 0);
        for metric in RetrievalQualityMetricId::ALL {
            assert_eq!(
                metrics.value(metric),
                0.0,
                "metric {} must be 0.0 on an empty denominator",
                metric.as_str()
            );
        }
        // Threshold breaches are enumerated, never a panic, and never a 1.0.
        let breaches = RetrievalMetricThreshold::SLICE.breaches(&metrics);
        assert_eq!(breaches.len(), RetrievalQualityMetricId::ALL.len());
        for breach in &breaches {
            assert_eq!(breach.observed, 0.0);
            assert_eq!(breach.threshold, 1.0);
        }
    }

    #[test]
    fn subset_denominator_zero_yields_zero_for_that_metric_only() {
        // No ambiguous and no unsafe cases, but a valid positive case.
        let cases = vec![case(
            "p1",
            RetrievalQueryKind::ExactNodeAddress,
            OfflineExpectedResult::Selected,
        )];
        let outcomes = vec![outcome(
            "p1",
            OfflineSelectionReason::ExactNodeAddressMatch,
            Some(OutputVerdict::Accepted),
        )];
        let metrics = compute_retrieval_quality_metrics(&cases, &outcomes);
        assert_eq!(metrics.selection_accuracy, 1.0);
        assert_eq!(metrics.positive_selection_rate, 1.0);
        assert_eq!(metrics.ambiguous_rejection_rate, 0.0);
        assert_eq!(metrics.unsafe_rejection_rate, 0.0);
        assert_eq!(metrics.unresolvable_citation_rejection_rate, 0.0);
        assert_eq!(metrics.mismatch_count, 0);
    }

    #[test]
    fn mismatch_and_negative_observations_are_reported_as_breaches() {
        let (cases, mut outcomes) = full_cover_corpus();
        // c1 is expected Selected but observed Rejected: a real mismatch.
        // c6 also expects Rejected but now observes an accepted verdict, so the
        // unresolvable rejection rate drops below 1.0; it is a second mismatch.
        outcomes[0] = outcome(
            "c1",
            OfflineSelectionReason::MarkerKindMatch,
            Some(OutputVerdict::Rejected),
        );
        outcomes[5] = outcome(
            "c6",
            OfflineSelectionReason::UnresolvedCandidateEvidence,
            Some(OutputVerdict::Accepted),
        );
        let metrics = compute_retrieval_quality_metrics(&cases, &outcomes);
        assert_eq!(metrics.mismatch_count, 2);
        assert_eq!(metrics.selection_accuracy, 6.0 / 8.0);
        assert_eq!(metrics.positive_selection_rate, 0.5);
        assert_eq!(metrics.unresolvable_citation_rejection_rate, 0.0);

        let breaches = RetrievalMetricThreshold::SLICE.breaches(&metrics);
        let ids: Vec<RetrievalQualityMetricId> =
            breaches.iter().map(|breach| breach.metric).collect();
        assert!(ids.contains(&RetrievalQualityMetricId::SelectionAccuracy));
        assert!(ids.contains(&RetrievalQualityMetricId::PositiveSelectionRate));
        assert!(ids.contains(&RetrievalQualityMetricId::UnresolvableCitationRejectionRate));

        // Determinism: a second computation is identical.
        let again = compute_retrieval_quality_metrics(&cases, &outcomes);
        assert_eq!(metrics, again);

        // The breach list follows the closed, deterministic contract order.
        let mut sorted = ids.clone();
        sorted.sort_by_key(|metric| {
            RetrievalQualityMetricId::ALL
                .iter()
                .position(|candidate| candidate == metric)
                .expect("every breach metric is a declared metric")
        });
        assert_eq!(ids, sorted);
    }

    #[test]
    fn missing_outcome_fails_closed_as_rejected() {
        // A case with no matching outcome is classed as Rejected (fail-closed),
        // so a Selected expectation is a mismatch, never an accidental success.
        let selected = vec![case(
            "solo",
            RetrievalQueryKind::ExactNodeAddress,
            OfflineExpectedResult::Selected,
        )];
        let metrics = compute_retrieval_quality_metrics(&selected, &[]);
        assert_eq!(metrics.total_cases, 1);
        assert_eq!(metrics.selection_accuracy, 0.0);
        assert_eq!(metrics.positive_selection_rate, 0.0);
        assert_eq!(metrics.mismatch_count, 1);

        // The symmetric honest match: a Rejected expectation with no outcome.
        let rejected = vec![case(
            "r1",
            RetrievalQueryKind::InvalidCandidate,
            OfflineExpectedResult::Rejected,
        )];
        let metrics = compute_retrieval_quality_metrics(&rejected, &[]);
        assert_eq!(metrics.selection_accuracy, 1.0);
        assert_eq!(metrics.mismatch_count, 0);
    }

    #[test]
    fn full_cover_metrics_are_deterministic() {
        let (cases, outcomes) = full_cover_corpus();
        let first = compute_retrieval_quality_metrics(&cases, &outcomes);
        let second = compute_retrieval_quality_metrics(&cases, &outcomes);
        assert_eq!(first, second);
    }

    #[test]
    fn runtime_profile_aggregates_and_is_reproducible() {
        let mut first = RetrievalRuntimeProfile::default();
        first.record_counts(3, 40, 40);
        first.record_counts(2, 10, 10);
        first.cases_run = 16;

        let mut second = RetrievalRuntimeProfile::default();
        second.record_counts(3, 40, 40);
        second.record_counts(2, 10, 10);
        second.cases_run = 16;

        assert_eq!(first, second, "two identical runs must be equal");
        assert_eq!(first.documents_processed, 2);
        assert_eq!(first.projected_views, 5);
        assert_eq!(first.projected_segments, 50);
        assert_eq!(first.resolver_evidence_spans, 50);
        assert_eq!(first.cases_run, 16);
        assert_eq!(
            first.reproducibility(),
            RetrievalMetricReproducibility::Reproducible
        );
    }

    #[test]
    fn host_boundary_timing_is_never_reproducible_or_asserted() {
        let timing = RetrievalObservedTiming::new(5, 1, 2);
        assert!(!timing.reproducible());
        assert!(!timing.asserted());
        assert_eq!(
            timing.reproducibility(),
            RetrievalMetricReproducibility::HostBoundaryObservedUnasserted
        );
        assert_eq!(
            timing.reproducibility().as_str(),
            "host_boundary_observed_unasserted"
        );
    }

    #[test]
    fn report_is_bounded_and_carries_no_raw_payload() {
        const SENTINEL: &str = "SENTINEL_RAW_LEGAL_TEXT";
        let mut cases = full_cover_corpus().0;
        // Poison every carried identifier with a sentinel; none may propagate.
        for (index, case) in cases.iter_mut().enumerate() {
            case.case_id = format!("{SENTINEL}-{index}");
            case.query_id = format!("{SENTINEL}-q-{index}");
            case.selector = format!("{SENTINEL}-selector");
        }
        let mut outcomes = full_cover_corpus().1;
        for (index, outcome) in outcomes.iter_mut().enumerate() {
            outcome.case_id = format!("{SENTINEL}-{index}");
            outcome.query_id = format!("{SENTINEL}-q-{index}");
        }
        let metrics = compute_retrieval_quality_metrics(&cases, &outcomes);
        let report = RetrievalMetricsReport::new(
            RetrievalMetricKind::Quality,
            metrics,
            RetrievalRuntimeProfile::default(),
            Some(RetrievalObservedTiming::new(1, 0, 0)),
        );
        let debug = format!("{report:?}");
        assert!(
            !debug.contains(SENTINEL),
            "the report must not carry payload"
        );
        assert_eq!(report.schema_version, "retrieval-metrics/rust-v1");
        assert_eq!(report.kind, RetrievalMetricKind::Quality);
        assert_eq!(report.boundary, RetrievalMetricBoundary::Slice);
        assert!(!report.non_claims.is_empty());
        for claim in report.non_claims {
            assert!(!claim.contains(SENTINEL));
            assert!(!claim.is_empty());
        }
    }

    #[test]
    fn closed_enums_expose_stable_wire_strings() {
        assert_eq!(RetrievalMetricKind::Quality.as_str(), "quality");
        assert_eq!(RetrievalMetricKind::Runtime.as_str(), "runtime");
        assert_eq!(RetrievalMetricBoundary::Slice.as_str(), "slice");
        assert_eq!(
            RetrievalMetricReproducibility::Reproducible.as_str(),
            "reproducible"
        );
        assert_eq!(
            RetrievalMetricReproducibility::HostBoundaryObservedUnasserted.as_str(),
            "host_boundary_observed_unasserted"
        );
        for metric in RetrievalQualityMetricId::ALL {
            assert!(!metric.as_str().is_empty());
        }
        assert!(!RETRIEVAL_METRICS_NON_CLAIMS.is_empty());
    }
}
