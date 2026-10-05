//! T04 bounded fixture run + declared recall/coverage gate (M221-wbslul S04).
//!
//! Exercises the bounded (T04) surface end-to-end on a tracked fixture corpus
//! plus the real `law-source/garant` root:
//!
//! - `build_bounded_inventory` walks the declared roots without the frozen v1
//!   sample-size pin (D677) and records zero-candidate providers;
//! - `run_acceptance_entries` drives the real pipeline over the fixture entries;
//! - `build_report_v2` yields three independent verdicts at once
//!   (`transport_integrity=pass`, `analysis_completion=incomplete`,
//!   `semantic_acceptance=not_attempted`) with `garant` `uncovered/no_candidates`;
//! - the declared-before-run minima are fixed in code and the recall/coverage
//!   gate is `below_declared` when a producer's yield is below the declaration;
//! - a repeated bounded run is deterministic (bar wall time);
//! - an empty bounded report is refused fail-closed.
//!
//! Non-claims: count/hash only; no decoded corpus text. `context-unavailable.xml`
//! is the only fixture carrying the (Russian) this-ref surface the §8C.2 trigger
//! requires — the trigger vocabulary in `document_context.rs` is not ASCII, so
//! unlike the plan's "both fixtures ASCII" hint this one fixture is UTF-8.

use std::path::PathBuf;

use ln_consultant_parser::corpus_sample::SourceRootKind;
use ln_consultant_parser::npa_corpus_acceptance::{
    build_bounded_inventory, run_acceptance_entries, AcceptanceEntry, AcceptanceOptions,
    BoundedInventory, SampleRoot, TamperProbeCounts,
};
use ln_consultant_parser::npa_corpus_acceptance_v2::{
    build_report_v2, AcceptanceReportV2, CompletionVerdict, DeclaredExpectations,
    ExpectationGateOutcome, SemanticVerdict, UncoveredReason, V2Thresholds,
};

const FIXTURE_RELATIVE: &str = "crates/ln-consultant-parser/tests/fixtures/m221-bounded";
const GARANT_RELATIVE: &str = "law-source/garant";

fn fixture_root() -> SampleRoot {
    SampleRoot::new(
        FIXTURE_RELATIVE,
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/m221-bounded"),
        SourceRootKind::ConsultantExport,
    )
    .expect("the fixture root is well formed")
}

fn garant_root() -> SampleRoot {
    SampleRoot::new(
        GARANT_RELATIVE,
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../law-source/garant"),
        SourceRootKind::Garant,
    )
    .expect("the garant root is well formed")
}

/// Zero the wall-time observations so a repeated run can be compared exactly.
fn strip_timing(entries: &[AcceptanceEntry]) -> Vec<AcceptanceEntry> {
    entries
        .iter()
        .cloned()
        .map(|mut entry| {
            entry.wall_ms = 0;
            entry
        })
        .collect()
}

fn build_report(
    entries: &[AcceptanceEntry],
    inventory: &BoundedInventory,
    tamper_probe: TamperProbeCounts,
) -> AcceptanceReportV2 {
    build_report_v2(
        entries,
        &inventory.declared_roots,
        &inventory.provider_candidate_counts,
        tamper_probe,
        &V2Thresholds::declared(),
    )
    .expect("the bounded report builds")
}

#[test]
fn bounded_fixture_run_separates_integrity_from_completion() {
    let roots = vec![fixture_root(), garant_root()];
    assert!(
        roots[1].path.is_dir(),
        "law-source/garant must exist on disk; the test must fail-closed otherwise"
    );

    let inventory = build_bounded_inventory(&roots).expect("the bounded inventory builds");
    assert_eq!(
        inventory.entries.len(),
        2,
        "the fixture corpus has exactly two XML files"
    );
    assert_eq!(
        inventory
            .provider_candidate_counts
            .get("consultant_export")
            .copied(),
        Some(2)
    );
    assert_eq!(
        inventory.provider_candidate_counts.get("garant").copied(),
        Some(0),
        "garant contributes 0 supported-format candidates"
    );

    let options = AcceptanceOptions::default();
    let run = run_acceptance_entries(&inventory.entries, &roots, &options)
        .expect("the bounded run executes");
    assert_eq!(
        run.tamper_probe_entries, options.tamper_probe_entries,
        "the declared tamper-probe subset is always exercised"
    );
    assert_eq!(
        run.tamper_probe_false_negative, 0,
        "the verifier detects every probe"
    );

    let report = build_report(&run.entries, &inventory, run.tamper_probe_counts());

    assert_eq!(report.verdicts.transport_integrity.as_str(), "pass");
    assert_eq!(
        report.verdicts.analysis_completion,
        CompletionVerdict::Incomplete
    );
    assert_eq!(
        report.verdicts.semantic_acceptance,
        SemanticVerdict::NotAttempted
    );
    assert!(report.structural_integrity.pass);
    assert_eq!(report.structural_integrity.verified_ok, 2);
    assert!(
        report.analysis_completion.entries_incomplete >= 1,
        "the non-resolved context entry is incomplete"
    );
    assert!(
        report.analysis_completion.entries_complete >= 1,
        "the plain fixture is complete"
    );
    assert!(
        report
            .analysis_completion
            .incomplete_reasons
            .contains_key("context_unavailable"),
        "the non-resolved context entry is recorded as context_unavailable"
    );
    assert_eq!(
        report.expectation_gate,
        ExpectationGateOutcome::BelowDeclared,
        "an incomplete producer is below the declared-before-run completion floor"
    );

    assert_eq!(report.provider_coverage.covered, vec!["consultant_export"]);
    assert_eq!(report.provider_coverage.uncovered.len(), 1);
    assert_eq!(report.provider_coverage.uncovered[0].provider, "garant");
    assert_eq!(
        report.provider_coverage.uncovered[0].uncovered_reason,
        UncoveredReason::NoCandidates
    );

    // The report is still count/hash-only even though a fixture is UTF-8.
    let text = report.to_json_string().expect("the report renders");
    assert!(text.is_ascii(), "the report stays ASCII-only");
    AcceptanceReportV2::load(&text).expect("the rendered report loads fail-closed");
}

#[test]
fn declared_expectations_are_fixed_before_the_run() {
    let expectations = DeclaredExpectations::declared();
    assert_eq!(expectations.min_completion_ratio_ppm, 1_000_000);
    assert_eq!(expectations.min_family_yields.get("document"), Some(&1));
    assert_eq!(expectations.min_family_yields.get("fragment"), Some(&1));
    assert_eq!(expectations.thresholds(), V2Thresholds::declared());
}

#[test]
fn inflated_family_minimum_fails_the_gate() {
    let roots = vec![fixture_root(), garant_root()];
    let inventory = build_bounded_inventory(&roots).expect("the bounded inventory builds");
    let run = run_acceptance_entries(&inventory.entries, &roots, &AcceptanceOptions::default())
        .expect("the bounded run executes");

    let mut inflated = V2Thresholds::declared();
    inflated
        .min_family_yields
        .insert("document".to_string(), 1_000_000);
    let report = build_report_v2(
        &run.entries,
        &inventory.declared_roots,
        &inventory.provider_candidate_counts,
        run.tamper_probe_counts(),
        &inflated,
    )
    .expect("the report builds against the inflated declaration");

    assert_eq!(
        report.expectation_gate,
        ExpectationGateOutcome::BelowDeclared
    );
    assert!(
        !report.analysis_completion.below_expected_yield.is_empty(),
        "the unmet family floor is named"
    );
    assert_ne!(
        report.verdicts.analysis_completion,
        CompletionVerdict::Complete
    );
}

#[test]
fn empty_bounded_report_is_refused() {
    let roots = vec![fixture_root(), garant_root()];
    let inventory = build_bounded_inventory(&roots).expect("the bounded inventory builds");
    let run = run_acceptance_entries(&inventory.entries, &roots, &AcceptanceOptions::default())
        .expect("the bounded run executes");

    let error = build_report_v2(
        &[],
        &inventory.declared_roots,
        &inventory.provider_candidate_counts,
        run.tamper_probe_counts(),
        &V2Thresholds::declared(),
    )
    .expect_err("an empty report is refused fail-closed");
    assert!(
        error.contains("entries_total"),
        "unexpected refusal: {error}"
    );
}

#[test]
fn repeated_bounded_run_is_deterministic() {
    let roots = vec![fixture_root(), garant_root()];
    let first = build_bounded_inventory(&roots).expect("first inventory");
    let second = build_bounded_inventory(&roots).expect("second inventory");
    assert_eq!(first, second, "the bounded inventory is deterministic");

    let options = AcceptanceOptions::default();
    let run_a = run_acceptance_entries(&first.entries, &roots, &options).expect("run a");
    let run_b = run_acceptance_entries(&first.entries, &roots, &options).expect("run b");
    assert_eq!(strip_timing(&run_a.entries), strip_timing(&run_b.entries));
    assert_eq!(run_a.tamper_probe_entries, run_b.tamper_probe_entries);
    assert_eq!(run_a.tamper_probe_detected, run_b.tamper_probe_detected);
    assert_eq!(
        run_a.tamper_probe_false_negative,
        run_b.tamper_probe_false_negative
    );

    let report_a = build_report(&run_a.entries, &first, run_a.tamper_probe_counts());
    let report_b = build_report(&run_b.entries, &second, run_b.tamper_probe_counts());
    assert_eq!(
        report_a, report_b,
        "the v2 report is deterministic (wall time excluded)"
    );
}
