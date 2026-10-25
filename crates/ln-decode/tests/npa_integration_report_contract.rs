//! M211 S04 T05: `npa-integration-report/v1` contract.
//!
//! Pure library tests over the shared `npa_wire` canonical renderer (D622).
//! No filesystem mutation, no corpus walk: the mandatory frozen fixture is
//! the only input. The report must publish the honesty keys, keep
//! correctness and refusal as separate planes, treat a zero denominator as
//! `not-measured` (never 0 and never a perfect 1), reproduce byte for byte
//! on replay, and carry the T04 refusal codes.

use std::path::Path;

use ln_decode::npa_report::{
    CorpusPlane, CorrectnessPlane, INTEGRATION_SCHEMA, INTEGRATION_SCHEMA_VERSION, IntegrationCli,
    Metric, MetricStatus, RefusalPlane, measured_metric, render_integration_report,
    run_integration_report,
};
use ln_decode::npa_sweep::EXIT_OK;

fn absent_default() -> &'static Path {
    Path::new("/npa-integration-report-absent-default-root")
}

fn fixture_run() -> (String, String) {
    let run = run_integration_report(&IntegrationCli::default(), absent_default());
    assert_eq!(run.exit_code, EXIT_OK, "stderr: {}", run.stderr);
    assert!(run.to_stdout, "report must stream to stdout without --out");
    let json = run.json.expect("skip run still renders the report");
    (json, run.stderr)
}

#[test]
fn schema_and_honesty_keys_are_present() {
    let (json, _) = fixture_run();
    assert_eq!(INTEGRATION_SCHEMA, "npa-integration-report/v1");
    assert_eq!(INTEGRATION_SCHEMA_VERSION, 1);
    for needle in [
        "\"schema\": \"npa-integration-report/v1\"",
        "\"schema_version\": 1",
        "\"derived\": true",
        "\"lifecycle\": [",
        "\"proposed\"",
        "\"authoritative\": false",
        "\"is_gold\": false",
        "\"not_human\": true",
        "\"not_s03_metrics\": true",
    ] {
        assert!(json.contains(needle), "missing honesty fragment {needle}");
    }
    assert!(!json.starts_with('\u{feff}'), "no UTF-8 BOM");
    assert!(json.ends_with('\n'), "canonical bytes end with newline");
    assert!(json.starts_with("{\n"), "canonical object rendering");
}

#[test]
fn correctness_and_refusal_are_separate_planes() {
    let (json, _) = fixture_run();
    assert!(json.contains("\"correctness\": {"), "correctness plane");
    assert!(json.contains("\"refusal\": {"), "refusal plane");
    assert!(
        json.contains("\"classification\": {"),
        "classification sub-plane"
    );
    assert!(json.contains("\"detection\": {"), "detection sub-plane");
    assert!(
        json.contains("\"denominators\": {"),
        "refusal denominators block"
    );
    for forbidden in [
        "\"overall\":",
        "\"combined\":",
        "\"average\":",
        "\"accuracy\":",
    ] {
        assert!(
            !json.contains(forbidden),
            "correctness and refusal must not be averaged: {forbidden}"
        );
    }
}

#[test]
fn frozen_classification_differential_stays_measured() {
    let (json, _) = fixture_run();
    // 69 frozen + 9 synthetic reference rows (D621).
    assert!(json.contains("\"total\": 78"), "78 reference rows");
    assert!(
        json.contains("\"value\": \"78/78\""),
        "classification differential must match the Python reference"
    );
    for needle in [
        "\"lemma\": {",
        "\"bucket\": {",
        "\"verdict\": {",
        "\"graph\": {",
        "\"identity_key\": {",
    ] {
        assert!(json.contains(needle), "missing per-field metric {needle}");
    }
    // Typed detection agreement: 112 frozen typed members (S02 gate).
    assert!(json.contains("\"reference_rows\": 112"), "112 typed rows");
    assert!(
        json.contains("\"value\": \"112/112\""),
        "detection agreement must match the frozen typed fixture"
    );
}

#[test]
fn refusal_plane_carries_t04_codes() {
    let (json, _) = fixture_run();
    for needle in [
        "\"TypeNotInherited\": {",
        "\"HeadFamilyCarryRefused\": {",
        "\"OpenSeriesWithoutHead\": {",
        "\"IncompatibleSeriesHead\": {",
        "\"AliasWithoutDeclaration\": {",
        "\"HeadUnavailable\": {",
        "\"frame_member_limit_reached\": {",
        "\"conflicting_frames_retained\": {",
        "\"owner_unresolved\": {",
        "\"grammar_contract_refused\": {",
        "\"type_unresolved\": {",
    ] {
        assert!(json.contains(needle), "missing refusal code {needle}");
    }
}

#[test]
fn empty_denominator_is_not_measured_never_zero_or_one() {
    assert_eq!(
        measured_metric(0, 0),
        Metric {
            numerator: 0,
            denominator: 0,
            status: MetricStatus::NotMeasured,
        }
    );
    // A nonzero numerator with a zero denominator must NOT read as a perfect 1.
    let impossible = measured_metric(7, 0);
    assert_eq!(impossible.status, MetricStatus::NotMeasured);
    assert_eq!(impossible.numerator, 0);
    assert_eq!(impossible.denominator, 0);

    let empty = render_integration_report(
        "empty",
        "skipped",
        &CorrectnessPlane::default(),
        &RefusalPlane::default(),
        &CorpusPlane::default(),
    );
    assert!(
        empty.contains("\"status\": \"not-measured\""),
        "empty planes must publish not-measured"
    );
    assert!(
        empty.contains("\"value\": null"),
        "not-measured value must be null"
    );
    assert!(
        !empty.contains("\"status\": \"measured\""),
        "empty planes must not publish a measured metric"
    );
    assert!(empty.contains("\"total\": 0"));
}

#[test]
fn report_replay_is_byte_deterministic() {
    let cli = IntegrationCli::default();
    let first = run_integration_report(&cli, absent_default());
    let second = run_integration_report(&cli, absent_default());
    assert_eq!(first.exit_code, second.exit_code);
    assert_eq!(first.json, second.json, "two runs must be byte-identical");
    assert_eq!(first.stderr, second.stderr);
}

#[test]
fn explicit_missing_root_is_root_missing() {
    let cli = IntegrationCli {
        root: Some("/npa-integration-report-explicit-missing".to_owned()),
        ..IntegrationCli::default()
    };
    let run = run_integration_report(&cli, absent_default());
    assert_eq!(run.exit_code, ln_decode::npa_sweep::EXIT_ROOT_MISSING);
    assert!(run.json.is_none(), "fatal run must not print a report");
    assert!(run.stderr.contains("root not found"));
}

#[test]
fn absent_default_root_is_explicit_skip_not_failure() {
    let (json, stderr) = fixture_run();
    assert!(
        json.contains("\"run_status\": \"skipped\""),
        "absent default root must be an explicit skip"
    );
    assert!(
        json.contains("\"status\": \"skipped\""),
        "corpus plane must be skipped"
    );
    assert!(stderr.contains("run_status=skipped"));
}
