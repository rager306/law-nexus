//! T04 report-contract test (M214-es3jvw S04): reads the tracked S04 corpus
//! acceptance report, adjudication packet, per-entry JSONL and durable battery
//! and asserts the separated, fail-closed contract **without** re-running the
//! corpus.
//!
//! The test is the read-only counterpart to the runtime battery
//! (`npa_corpus_acceptance_run_contract`, T03): it never reads corpus bytes and
//! never re-derives coordinates. It checks that the tracked report is
//! ascii/count/hash-only, that every mandatory section stays separate, that the
//! report pins the tracked sample manifest by content hash, that the semantic
//! section does not promote, that `coverage_claim` is null, that R1000 stays
//! active, that the verdict obeys the declared rules, and that a recursive scan
//! finds no long decoded substrate fragment in any loaded artifact.
//!
//! Non-claims: count/hash only; no decoded corpus text and no semantic claim
//! enters this test or the artifacts it loads.

use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;

use ln_consultant_parser::npa_corpus_acceptance::{
    AcceptanceEntry, AcceptanceReport, AdjudicationPacket, EntryOutcome, Verdict,
    M208_STATUS_PARKED, R1000_STATUS_ACTIVE, SEMANTIC_REFERENCE_STATUS_ABSENT,
};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

const SAMPLE_REL: &str = "prd/migration/rust-evidence/m214-s04-corpus-sample.json";
const REPORT_REL: &str = "prd/migration/rust-evidence/m214-s04-corpus-acceptance.json";
const PACKET_REL: &str = "prd/migration/rust-evidence/m214-s04-adjudication-packet.json";
const ENTRIES_REL: &str = "prd/migration/rust-evidence/m214-s04-corpus-acceptance.jsonl";
const BATTERY_REL: &str = "prd/migration/rust-evidence/m214-s04-acceptance-battery.json";
const HORIZON_REL: &str = "prd/migration/rust-evidence/m214-s04-horizon-reassessment.md";
const CONTRACT_REL: &str = "prd/architecture/npa-analysis-jsonl-contract.md";

/// The mandatory separated sections (§15.3); never merged into one blob.
const SEPARATED_SECTIONS: &[&str] = &[
    "structural_integrity",
    "semantic_adjudication",
    "limits",
    "resources",
    "corpus_breadth",
    "horizon",
    "verdict",
    "verdict_basis",
];

/// No single string value may approach decoded-substrate length. Corpus
/// substrate fragments are multi-kilobyte prose; a small bound plus the
/// ascii/control scan below proves no long fragment leaked.
const MAX_METADATA_STRING: usize = 512;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn read_bytes(rel: &str) -> Vec<u8> {
    fs::read(repo_root().join(rel)).unwrap_or_else(|error| panic!("read {rel}: {error}"))
}

fn read_str(rel: &str) -> String {
    let bytes = read_bytes(rel);
    String::from_utf8(bytes).unwrap_or_else(|error| panic!("{rel} must be utf-8: {error}"))
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut out = String::with_capacity(digest.len() * 2);
    for byte in digest {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

fn collect_strings<'a>(value: &'a Value, out: &mut Vec<&'a str>) {
    match value {
        Value::String(text) => out.push(text),
        Value::Array(items) => {
            for item in items {
                collect_strings(item, out);
            }
        }
        Value::Object(members) => {
            for child in members.values() {
                collect_strings(child, out);
            }
        }
        Value::Null | Value::Bool(_) | Value::Number(_) => {}
    }
}

/// Recursive count/hash-only scan: every string is ascii, control-free and
/// short enough that no long decoded substrate fragment can hide.
fn assert_count_hash_only(value: &Value, label: &str) {
    let mut strings = Vec::new();
    collect_strings(value, &mut strings);
    assert!(!strings.is_empty(), "{label} has no string values");
    for text in strings {
        assert!(text.is_ascii(), "{label} carries non-ascii text");
        assert!(
            !text.contains('\n') && !text.contains('\r') && !text.contains('\t'),
            "{label} carries a control character (decoded substrate)"
        );
        assert!(
            text.chars().count() <= MAX_METADATA_STRING,
            "{label} carries an over-long string ({} chars)",
            text.chars().count()
        );
    }
}

fn load_report() -> AcceptanceReport {
    let raw = read_str(REPORT_REL);
    assert!(
        raw.is_ascii(),
        "the tracked acceptance report must be ascii_only"
    );
    AcceptanceReport::load(&raw).expect("the tracked acceptance report must pass fail-closed load")
}

fn report_value() -> Value {
    serde_json::from_str(&read_str(REPORT_REL)).expect("the tracked report must be valid JSON")
}

#[test]
fn tracked_report_is_fail_closed_and_separated() {
    let raw = read_str(REPORT_REL);
    let report = load_report();
    let value = report_value();

    for section in SEPARATED_SECTIONS {
        assert!(
            value.get(section).is_some(),
            "the report must carry the separated section `{section}`"
        );
    }
    assert_count_hash_only(&value, "report");

    let size = report.declared_thresholds.sample_size;
    assert_eq!(report.structural_integrity.entries_total, size);
    assert_eq!(report.corpus_breadth.sample_size, size);
    assert_eq!(
        report.structural_integrity.verified_ok + report.structural_integrity.structural_failures,
        size,
        "verified_ok + structural_failures must cover the declared sample"
    );
    assert_eq!(
        report.structural_integrity.verified_ok + report.structural_integrity.structural_failures,
        report.structural_integrity.entries_total
    );

    // D667/D668: structural-only semantic section, no promotion, no breadth claim.
    assert!(!report.semantic_adjudication.promotion);
    assert_eq!(
        report.semantic_adjudication.semantic_reference_status,
        SEMANTIC_REFERENCE_STATUS_ABSENT
    );
    assert!(report.corpus_breadth.coverage_claim.is_none());
    assert!(report.corpus_breadth.not_year_type_stratified);

    // Horizon markers must not silently drift.
    assert_eq!(report.horizon.r1000_status, R1000_STATUS_ACTIVE);
    assert_eq!(report.horizon.m208_status, M208_STATUS_PARKED);

    // The report must not carry the raw sample bytes back in.
    assert!(
        !raw.contains("consru_export/consru_export/exports/fas/"),
        "the report must not embed corpus paths beyond the declared roots"
    );
}

#[test]
fn tracked_report_pins_the_sample_manifest() {
    let sample = read_bytes(SAMPLE_REL);
    let report = load_report();
    assert_eq!(
        report.sample_manifest_sha256,
        format!("sha256:{}", sha256_hex(&sample)),
        "the report must pin the tracked sample manifest by content hash"
    );
}

#[test]
fn tracked_report_verdict_obeys_declared_rules() {
    let report = load_report();
    let structural = &report.structural_integrity;
    assert_eq!(
        report.verdict,
        report.compute_verdict(),
        "the stored verdict must equal the declared-rule verdict"
    );
    match report.verdict {
        Verdict::Fail => {
            assert!(
                structural.manifest_pin_mismatch > 0
                    || structural.verify_refused > 0
                    || structural.tamper_probe_false_negative > 0
                    || report.semantic_adjudication.promotion
                    || report.corpus_breadth.coverage_claim.is_some(),
                "a fail verdict requires a declared hard failure"
            );
        }
        Verdict::NeedsAttention => {
            assert_eq!(structural.manifest_pin_mismatch, 0);
            assert_eq!(structural.verify_refused, 0);
            assert_eq!(structural.tamper_probe_false_negative, 0);
            assert!(!report.semantic_adjudication.promotion);
            assert!(report.corpus_breadth.coverage_claim.is_none());
            assert!(
                structural.structural_failures > 0
                    || !report.limits.within_threshold
                    || !report.resources.within_budget
            );
        }
        Verdict::Pass => {
            assert_eq!(structural.structural_failures, 0);
            assert_eq!(report.limits.limit_events_total, 0);
            assert!(report.limits.within_threshold);
            assert!(report.resources.within_budget);
            assert_eq!(structural.tamper_probe_false_negative, 0);
        }
    }
}

#[test]
fn tracked_packet_is_text_free_and_matches_report() {
    let raw = read_str(PACKET_REL);
    assert!(raw.is_ascii(), "the packet must be ascii_only");
    let packet = AdjudicationPacket::load(&raw).expect("the packet must pass fail-closed load");
    let report = load_report();
    let value: Value = serde_json::from_str(&raw).expect("the packet must be valid JSON");
    assert_count_hash_only(&value, "packet");

    assert!(!packet.promotion);
    assert_eq!(
        packet.semantic_reference_status,
        SEMANTIC_REFERENCE_STATUS_ABSENT
    );
    assert_eq!(packet.sample_manifest_sha256, report.sample_manifest_sha256);
    assert_eq!(
        packet.items.len() as u64,
        report.structural_integrity.entries_total
    );
}

#[test]
fn tracked_entries_jsonl_is_complete_and_closed() {
    let raw = read_str(ENTRIES_REL);
    assert!(raw.is_ascii(), "the per-entry JSONL must be ascii_only");
    let report = load_report();

    let mut paths = BTreeSet::new();
    let mut total: u64 = 0;
    let mut verified: u64 = 0;
    let mut failures: u64 = 0;
    for line in raw.lines() {
        assert!(!line.trim().is_empty(), "JSONL must not carry blank lines");
        let entry = AcceptanceEntry::load_line(line).expect("each entry must load closed");
        let value: Value = serde_json::from_str(line).expect("each entry must be valid JSON");
        assert_count_hash_only(&value, "entry");
        assert!(paths.insert(entry.relative_path.clone()), "duplicate path");
        total += 1;
        match entry.outcome {
            EntryOutcome::VerifiedOk => verified += 1,
            _ => failures += 1,
        }
    }
    assert_eq!(total, report.structural_integrity.entries_total);
    assert_eq!(verified, report.structural_integrity.verified_ok);
    assert_eq!(failures, report.structural_integrity.structural_failures);
}

#[test]
fn tracked_battery_is_consistent_with_report() {
    let raw = read_str(BATTERY_REL);
    assert!(raw.is_ascii(), "the battery must be ascii_only");
    let battery: Value = serde_json::from_str(&raw).expect("the battery must be valid JSON");
    assert_count_hash_only(&battery, "battery");

    let report = load_report();
    let structural = &report.structural_integrity;
    let limits = &report.limits;
    let resources = &report.resources;
    let thresholds = &report.declared_thresholds;

    assert_eq!(
        battery["schema"],
        "law-nexus/m214-s04-acceptance-battery/v1"
    );
    assert_eq!(battery["count_only"], json!(true));
    assert_eq!(battery["ascii_only"], json!(true));
    assert_eq!(battery["sample_size"], json!(thresholds.sample_size));
    assert_eq!(
        battery["sample_manifest_sha256"],
        json!(report.sample_manifest_sha256)
    );
    assert_eq!(battery["verdict"], json!(report.verdict.as_str()));
    assert_eq!(
        battery["report_sha256"],
        json!(format!("sha256:{}", sha256_hex(&read_bytes(REPORT_REL))))
    );
    assert!(
        battery["run_command"]
            .as_str()
            .is_some_and(|command| command.contains("npa-corpus-acceptance")),
        "the battery must record the acceptance run command"
    );
    assert!(
        battery["rustc_version"]
            .as_str()
            .is_some_and(|v| !v.is_empty()),
        "the battery must record the rustc version"
    );

    // Declared thresholds vs observed.
    assert_eq!(
        battery["declared_thresholds"],
        serde_json::to_value(thresholds).expect("thresholds serialize")
    );
    let observed = &battery["observed"];
    assert_eq!(observed["entries_total"], json!(structural.entries_total));
    assert_eq!(observed["verified_ok"], json!(structural.verified_ok));
    assert_eq!(
        observed["structural_failures"],
        json!(structural.structural_failures)
    );
    assert_eq!(observed["verify_refused"], json!(structural.verify_refused));
    assert_eq!(observed["decode_refused"], json!(structural.decode_refused));
    assert_eq!(observed["gate_refused"], json!(structural.gate_refused));
    assert_eq!(
        observed["analysis_refused"],
        json!(structural.analysis_refused)
    );
    assert_eq!(
        observed["manifest_pin_mismatch"],
        json!(structural.manifest_pin_mismatch)
    );
    assert_eq!(
        observed["limit_events_total"],
        json!(limits.limit_events_total)
    );
    assert_eq!(observed["within_threshold"], json!(limits.within_threshold));
    assert_eq!(observed["within_budget"], json!(resources.within_budget));
    assert_eq!(
        observed["peak_memory_bytes"],
        serde_json::to_value(resources.peak_memory_bytes).unwrap()
    );
    assert_eq!(observed["total_wall_ms"], json!(resources.total_wall_ms));
    assert_eq!(
        observed["tamper_probe_entries"],
        json!(structural.tamper_probe_entries)
    );
    assert_eq!(
        observed["tamper_probe_detected"],
        json!(structural.tamper_probe_detected)
    );
    assert_eq!(
        observed["tamper_probe_false_negative"],
        json!(structural.tamper_probe_false_negative)
    );

    // Section counters (count/hash-only mirror of the report).
    let sections = &battery["section_counters"];
    for key in [
        "structural_integrity",
        "semantic_adjudication",
        "limits",
        "resources",
        "corpus_breadth",
        "horizon",
    ] {
        assert!(
            sections.get(key).is_some(),
            "the battery must carry the `{key}` section counters"
        );
    }
    assert_eq!(
        sections["structural_integrity"],
        json!(structured_counters(structural))
    );

    // The declared re-test set must be present and non-empty.
    let re_test_set = battery["re_test_set"]
        .as_array()
        .expect("the battery must carry a re_test_set array");
    assert!(!re_test_set.is_empty());
    assert!(re_test_set.iter().all(|item| item.as_str().is_some()));
}

/// T05: the horizon reassessment document must be the human-readable mirror of
/// the report's horizon/semantic boundary. If the report silently promotes the
/// semantic section, closes R1000, resumes M208, or the doc drops a non-claim,
/// this test fails without re-running the corpus.
#[test]
fn tracked_horizon_doc_matches_report_boundary() {
    let doc = read_str(HORIZON_REL);
    assert!(
        !doc.trim().is_empty(),
        "the horizon reassessment must be non-empty"
    );
    assert!(
        doc.is_ascii(),
        "the horizon reassessment must be ascii_only"
    );

    let report = load_report();

    // R1000 marker: the doc's R1000 statement must agree with the report.
    assert!(doc.contains("R1000"), "the horizon doc must name R1000");
    assert!(
        doc.contains(report.horizon.r1000_status.as_str()),
        "the horizon doc must carry the report r1000_status `{}`",
        report.horizon.r1000_status
    );
    assert_eq!(report.horizon.r1000_status, R1000_STATUS_ACTIVE);

    // M208 marker.
    assert!(doc.contains("M208"), "the horizon doc must name M208");
    assert!(
        doc.contains(report.horizon.m208_status.as_str()),
        "the horizon doc must carry the report m208_status `{}`",
        report.horizon.m208_status
    );
    assert_eq!(report.horizon.m208_status, M208_STATUS_PARKED);

    // Semantic section stays structural-only; never promoted.
    assert!(
        doc.contains("structural-only"),
        "the horizon doc must mark the semantic section structural-only"
    );
    assert!(
        !report.semantic_adjudication.promotion,
        "the semantic section must not be promoted"
    );
    assert_eq!(
        report.semantic_adjudication.semantic_reference_status,
        SEMANTIC_REFERENCE_STATUS_ABSENT
    );

    // The explicit non-claims must stay present in the doc.
    for marker in [
        "no corpus-wide accuracy claim",
        "no source authenticity claim",
        "no legal-effect claim",
        "not a semantic oracle",
    ] {
        assert!(
            doc.contains(marker),
            "the horizon doc must carry the non-claim `{marker}`"
        );
    }

    // Contract section 13 must record the S04 outcome and confirm D667/D668.
    let contract = read_str(CONTRACT_REL);
    assert!(
        contract.contains("S04 outcome"),
        "contract section 13 must record the S04 outcome"
    );
    assert!(contract.contains("D667"), "the contract must confirm D667");
    assert!(contract.contains("D668"), "the contract must confirm D668");
}

fn structured_counters(
    structural: &ln_consultant_parser::npa_corpus_acceptance::StructuralIntegritySection,
) -> Value {
    json!({
        "entries_total": structural.entries_total,
        "verified_ok": structural.verified_ok,
        "read_back_refused": structural.read_back_refused,
        "verify_refused": structural.verify_refused,
        "decode_refused": structural.decode_refused,
        "gate_refused": structural.gate_refused,
        "analysis_refused": structural.analysis_refused,
        "limit_line_bytes": structural.limit_line_bytes,
        "limit_records": structural.limit_records,
        "manifest_pin_mismatch": structural.manifest_pin_mismatch,
        "verify_codes": structural.verify_codes,
        "tamper_probe_entries": structural.tamper_probe_entries,
        "tamper_probe_detected": structural.tamper_probe_detected,
        "tamper_probe_false_negative": structural.tamper_probe_false_negative,
        "structural_failures": structural.structural_failures,
        "pass": structural.pass,
    })
}
