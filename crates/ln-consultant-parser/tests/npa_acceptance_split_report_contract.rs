//! T03 v2 split-acceptance report contract (M221-wbslul S04).
//!
//! Exercises the new `npa_corpus_acceptance_v2` type directly, without the
//! bounded runner (T04) or the CLI (T05):
//!
//! - a valid report round-trips through `load`/`validate` and carries three
//!   independent verdicts at once: `transport_integrity = pass`,
//!   `analysis_completion = incomplete`, `semantic_acceptance = not_attempted`;
//! - a declared provider with zero sampled entries is surfaced `uncovered`
//!   (`garant` + `no_candidates`), never silently dropped;
//! - `load`/`validate` are fail-closed on promotion, coverage claim, an unknown
//!   token, a raw-text key, a `..`/absolute path and mismatched counters;
//! - the serialized report is count/hash-only: ASCII, control-free, strings at
//!   most 512 bytes.
//!
//! Non-claims: fixtures are inline; count/hash only; no decoded corpus text.

use std::collections::BTreeMap;

use ln_consultant_parser::npa_corpus_acceptance::{
    AcceptanceEntry, DeclaredRoot, EntryOutcome, ProviderToken, TamperProbeCounts,
    ThisDocumentReferenceToken,
};
use ln_consultant_parser::npa_corpus_acceptance_v2::{
    AcceptanceReportV2, CompletionVerdict, SemanticVerdict, UncoveredReason, V2Thresholds,
    build_report_v2,
};
use serde_json::{Value, json};

/// A 64-hex sha256-shaped string (never a real corpus digest).
fn sha(seed: u8) -> String {
    format!("{seed:02x}").repeat(32)
}

#[allow(clippy::too_many_arguments)]
fn entry(
    path: &str,
    provider: ProviderToken,
    this_document_reference: Option<ThisDocumentReferenceToken>,
    completion: Option<&str>,
    basis: Option<&str>,
    reasons: &[&str],
    families: &[(&str, u64)],
) -> AcceptanceEntry {
    AcceptanceEntry {
        relative_path: path.to_string(),
        sha256: sha(1),
        bytes: 128,
        provider,
        document_type: "wordml".to_string(),
        work_family: "family-a".to_string(),
        outcome: EntryOutcome::VerifiedOk,
        verify_code: None,
        limit_kind: None,
        this_document_reference,
        completion: completion.map(str::to_string),
        completion_basis: basis.map(str::to_string),
        incomplete_reasons: reasons.iter().map(|reason| (*reason).to_string()).collect(),
        family_yields: families
            .iter()
            .map(|(family, count)| ((*family).to_string(), *count))
            .collect(),
        wall_ms: 5,
    }
}

/// Two integral entries: one complete, one `context_incomplete`.
fn valid_entries() -> Vec<AcceptanceEntry> {
    vec![
        entry(
            "npa/law_0001/edition-0001.xml",
            ProviderToken::ConsultantExport,
            Some(ThisDocumentReferenceToken::NotRequested),
            Some("complete"),
            Some("bounded_analysis_complete"),
            &[],
            &[("document", 3), ("fragment", 2)],
        ),
        entry(
            "npa/law_0002/edition-0001.xml",
            ProviderToken::ConsultantExport,
            Some(ThisDocumentReferenceToken::Unavailable),
            Some("incomplete"),
            Some("context_incomplete"),
            &["context_unavailable"],
            &[("document", 1), ("context", 1)],
        ),
    ]
}

fn declared_roots() -> Vec<DeclaredRoot> {
    vec![
        DeclaredRoot {
            relative_path: "consru_export/consru_export/exports".to_string(),
            provider: ProviderToken::ConsultantExport,
        },
        DeclaredRoot {
            relative_path: "law-source/garant".to_string(),
            provider: ProviderToken::Garant,
        },
    ]
}

fn candidate_counts() -> BTreeMap<String, u64> {
    let mut counts = BTreeMap::new();
    counts.insert("consultant_export".to_string(), 2);
    counts.insert("garant".to_string(), 0);
    counts
}

/// The synthetic tamper-probe counts for this report-only battery (the bounded
/// runner supplies the real counts; T04 wires them).
fn probe() -> TamperProbeCounts {
    TamperProbeCounts {
        entries: 2,
        detected: 2,
        false_negative: 0,
    }
}

fn valid_report() -> AcceptanceReportV2 {
    build_report_v2(
        &valid_entries(),
        &declared_roots(),
        &candidate_counts(),
        probe(),
        &V2Thresholds::declared(),
    )
    .expect("a coherent bounded report builds")
}

/// Re-serialize a valid report after mutating its JSON value.
fn mutate(report: &AcceptanceReportV2, mutate: impl FnOnce(&mut Value)) -> String {
    let mut value: Value = serde_json::from_str(&report.to_json_string().expect("report renders"))
        .expect("valid JSON");
    mutate(&mut value);
    value.to_string()
}

// -------------------------------------------------- split verdicts #

#[test]
fn valid_report_round_trips_with_three_independent_verdicts() {
    let report = valid_report();
    report.validate().expect("the built report validates");
    let text = report.to_json_string().expect("report renders");

    let loaded = AcceptanceReportV2::load(&text).expect("the rendered report loads fail-closed");
    assert_eq!(loaded, report, "load must round-trip byte-for-byte");
    assert_eq!(loaded.verdicts.transport_integrity.as_str(), "pass");
    assert_eq!(
        loaded.verdicts.analysis_completion,
        CompletionVerdict::Incomplete
    );
    assert_eq!(
        loaded.verdicts.semantic_acceptance,
        SemanticVerdict::NotAttempted
    );
    assert!(
        loaded.structural_integrity.pass,
        "an integral but incomplete report keeps a structural pass"
    );
    assert_eq!(loaded.analysis_completion.entries_complete, 1);
    assert_eq!(loaded.analysis_completion.entries_incomplete, 1);
    assert_eq!(
        loaded.analysis_completion.observed_completion_ratio_ppm,
        500_000
    );
    assert!(
        loaded.analysis_completion.below_expected_yield.is_empty(),
        "the bounded fixture meets the declared per-family floors"
    );
}

// ------------------------------------------------- provider coverage #

#[test]
fn zero_sample_provider_is_uncovered_no_candidates() {
    let report = valid_report();
    let coverage = &report.provider_coverage;
    assert_eq!(coverage.declared, vec!["consultant_export", "garant"]);
    assert_eq!(coverage.covered, vec!["consultant_export"]);
    assert_eq!(coverage.uncovered.len(), 1);
    assert_eq!(coverage.uncovered[0].provider, "garant");
    assert_eq!(
        coverage.uncovered[0].uncovered_reason,
        UncoveredReason::NoCandidates
    );
    assert_eq!(
        coverage.uncovered[0].uncovered_reason.as_str(),
        "no_candidates"
    );
}

#[test]
fn existing_candidates_without_selection_are_uncovered_no_selection() {
    let mut counts = candidate_counts();
    counts.insert("garant".to_string(), 7);
    let report = build_report_v2(
        &valid_entries(),
        &declared_roots(),
        &counts,
        probe(),
        &V2Thresholds::declared(),
    )
    .expect("report builds with a non-empty candidate pool");
    assert_eq!(report.provider_coverage.uncovered.len(), 1);
    assert_eq!(
        report.provider_coverage.uncovered[0].uncovered_reason,
        UncoveredReason::NoSelection
    );
}

// ------------------------------------------------------- hostile #

#[test]
fn load_refuses_unknown_transport_token() {
    let report = valid_report();
    let text = mutate(&report, |value| {
        value["verdicts"]["transport_integrity"] = json!("unknown");
    });
    let error = AcceptanceReportV2::load(&text).expect_err("an unknown token is refused");
    assert!(error.contains("schema"), "unexpected refusal: {error}");
}

#[test]
fn load_refuses_raw_text_key() {
    let report = valid_report();
    let text = mutate(&report, |value| {
        value["raw_text"] = json!("leaked corpus text");
    });
    let error = AcceptanceReportV2::load(&text).expect_err("a raw-text key is refused");
    assert!(error.contains("forbidden"), "unexpected refusal: {error}");
}

#[test]
fn load_refuses_promotion_true() {
    let report = valid_report();
    let text = mutate(&report, |value| {
        value["promotion"] = json!(true);
    });
    let error = AcceptanceReportV2::load(&text).expect_err("promotion=true is refused");
    assert!(error.contains("promotion"), "unexpected refusal: {error}");
}

#[test]
fn load_refuses_coverage_claim() {
    let report = valid_report();
    let text = mutate(&report, |value| {
        value["coverage_claim"] = json!("whole-corpus coverage");
    });
    let error = AcceptanceReportV2::load(&text).expect_err("a coverage claim is refused");
    assert!(
        error.contains("coverage_claim"),
        "unexpected refusal: {error}"
    );
}

#[test]
fn load_refuses_mismatched_counters() {
    let report = valid_report();
    let text = mutate(&report, |value| {
        value["analysis_completion"]["entries_complete"] = json!(2);
    });
    let error = AcceptanceReportV2::load(&text).expect_err("mismatched counters are refused");
    assert!(error.contains("completion"), "unexpected refusal: {error}");
}

#[test]
fn load_refuses_absolute_path() {
    let report = valid_report();
    let text = mutate(&report, |value| {
        value["non_claims"] = json!(["/etc/passwd"]);
    });
    let error = AcceptanceReportV2::load(&text).expect_err("an absolute path is refused");
    assert!(error.contains("absolute"), "unexpected refusal: {error}");
}

#[test]
fn load_refuses_parent_dir_path() {
    let report = valid_report();
    let text = mutate(&report, |value| {
        value["non_claims"] = json!(["../escape"]);
    });
    let error = AcceptanceReportV2::load(&text).expect_err("a '..' path is refused");
    assert!(error.contains("traversal"), "unexpected refusal: {error}");
}

// ------------------------------------------------- count/hash only #

#[test]
fn serialized_report_is_count_hash_only() {
    let text = valid_report().to_json_string().expect("report renders");
    let value: Value = serde_json::from_str(&text).expect("valid JSON");
    assert_ascii_control_free(&value);
}

fn assert_ascii_control_free(value: &Value) {
    match value {
        Value::String(text) => {
            assert!(text.is_ascii(), "non-ASCII string: {text:?}");
            assert!(
                !text.bytes().any(|byte| byte.is_ascii_control()),
                "control character in string: {text:?}"
            );
            assert!(text.len() <= 512, "string over 512 bytes: {text:?}");
        }
        Value::Object(members) => {
            for (key, child) in members {
                assert!(key.is_ascii(), "non-ASCII key: {key:?}");
                assert_ascii_control_free(child);
            }
        }
        Value::Array(items) => {
            for child in items {
                assert_ascii_control_free(child);
            }
        }
        _ => {}
    }
}
