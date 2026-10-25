//! T01 contract test (M214-es3jvw S04): the frozen schemas, closed
//! vocabularies and non-claims in `prd/architecture/npa-analysis-jsonl-contract.md`
//! §15, plus the strict fail-closed `load`/`validate` of
//! `npa_corpus_acceptance`.
//!
//! Non-claims: count/hash only; no decoded corpus text and no semantic claim
//! enters this test or the artifacts it loads.

use std::fs;
use std::path::PathBuf;

use ln_consultant_parser::npa_corpus_acceptance::{
    ACCEPTANCE_SCHEMA, ADJUDICATION_SCHEMA, AcceptanceEntry, AcceptanceReport, AdjudicationPacket,
    CorpusSampleManifest, DECLARED_DRAW_SEED, DECLARED_SAMPLE_SIZE, SAMPLE_SCHEMA, SCHEMA_VERSION,
};
use serde_json::{Value, json};

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn declared_thresholds_json() -> Value {
    json!({
        "sample_size": DECLARED_SAMPLE_SIZE,
        "draw_seed": DECLARED_DRAW_SEED,
        "tamper_probe_entries": 12,
        "resource_budget_peak_bytes": 4_294_967_296u64,
        "resource_budget_total_ms": 3_600_000,
        "min_verified_ratio_ppm": 990_000,
        "max_limit_events": 0,
    })
}

fn sample_manifest_json() -> Value {
    let entries: Vec<Value> = (0..DECLARED_SAMPLE_SIZE)
        .map(|i| {
            json!({
                "relative_path": format!("npa/law_{i:04}/edition-0001.xml"),
                "sha256": format!("{:064x}", i + 1),
                "bytes": 100 + i,
                "provider": "consultant_export",
                "document_type": "law",
                "work_family": format!("law_{i:04}"),
            })
        })
        .collect();
    let snapshot = "a".repeat(64);
    json!({
        "schema": SAMPLE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "[bounded]",
        "milestone": "M214-es3jvw",
        "slice": "S04",
        "count_only": true,
        "ascii_only": true,
        "declared_before_run": true,
        "declared_thresholds": declared_thresholds_json(),
        "corpus_snapshot_sha256": snapshot,
        "not_year_type_stratified": true,
        "c3_exclusion": "none (diagnostic sample, not an evaluation holdout)",
        "leakage": {
            "input_candidates": 100_000,
            "exact_duplicate_hashes": 0,
            "excluded_c3_hashes": 0,
            "collapsed_editions": 500,
            "collapsed_families": 499,
            "c3_family_overlap": 0,
            "garant_available": 4,
            "garant_selected": 4,
            "consultant_available": 100_000,
            "consultant_selected": 396,
            "garant_cap": 4,
            "not_year_type_stratified": true,
        },
        "roots": [
            {
                "relative_path": "consru_export/consru_export/exports",
                "provider": "consultant_export",
            },
            { "relative_path": "law-source/garant", "provider": "garant" },
        ],
        "entries": entries,
        "non_claims": ["count/hash only", "not a semantic oracle"],
    })
}

fn acceptance_report_json() -> Value {
    json!({
        "schema": ACCEPTANCE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "[bounded]",
        "milestone": "M214-es3jvw",
        "slice": "S04",
        "count_only": true,
        "ascii_only": true,
        "sample_manifest_sha256": "b".repeat(64),
        "declared_thresholds": declared_thresholds_json(),
        "structural_integrity": {
            "entries_total": DECLARED_SAMPLE_SIZE,
            "verified_ok": DECLARED_SAMPLE_SIZE,
            "read_back_refused": 0,
            "verify_refused": 0,
            "decode_refused": 0,
            "gate_refused": 0,
            "analysis_refused": 0,
            "limit_line_bytes": 0,
            "limit_records": 0,
            "manifest_pin_mismatch": 0,
            "verify_codes": {},
            "tamper_probe_entries": 12,
            "tamper_probe_detected": 12,
            "tamper_probe_false_negative": 0,
            "structural_failures": 0,
            "pass": true,
        },
        "semantic_adjudication": {
            "semantic_reference_status": "absent",
            "promotion": false,
            "adjudication_status": "not_attempted",
            "packet_schema": ADJUDICATION_SCHEMA,
            "adjudication_packet_sha256": "c".repeat(64),
            "adjudicated_entries": 0,
            "non_claims": ["structural-only; no promotion"],
        },
        "limits": { "limit_events_total": 0, "limit_events": {}, "within_threshold": true },
        "resources": {
            "peak_memory_bytes": 123_456_789u64,
            "peak_memory_available": true,
            "total_wall_ms": 60_000,
            "mean_wall_ms": 150,
            "max_wall_ms": 900,
            "within_budget": true,
        },
        "corpus_breadth": {
            "sample_size": DECLARED_SAMPLE_SIZE,
            "provider_counts": { "consultant_export": 396, "garant": 4 },
            "work_family_count": DECLARED_SAMPLE_SIZE,
            "document_type_counts": { "law": DECLARED_SAMPLE_SIZE },
            "not_year_type_stratified": true,
            "coverage_claim": null,
        },
        "horizon": {
            "r1000_status": "active",
            "m208_status": "parked",
            "display_cleaning_status": "remaining (D638)",
            "next_horizon_status": "M215-M220 parked",
        },
        "verdict": "pass",
        "verdict_basis": "all entries verified, no limits, within budget, no overclaim",
        "non_claims": ["not a semantic oracle", "no coverage claim", "R1000 active"],
    })
}

fn adjudication_packet_json() -> Value {
    json!({
        "schema": ADJUDICATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "[bounded]",
        "milestone": "M214-es3jvw",
        "slice": "S04",
        "count_only": true,
        "ascii_only": true,
        "sample_manifest_sha256": "b".repeat(64),
        "promotion": false,
        "semantic_reference_status": "absent",
        "adjudication_status": "not_attempted",
        "items": [
            {
                "entry_index": 0,
                "relative_path": "npa/law_0000/edition-0001.xml",
                "sha256": format!("{:064x}", 1),
                "document_type": "law",
                "work_family": "law_0000",
                "adjudication_status": "not_attempted",
            },
        ],
        "non_claims": ["structural-only", "no promotion"],
    })
}

fn load_manifest(value: &Value) -> Result<CorpusSampleManifest, String> {
    CorpusSampleManifest::load(&value.to_string())
}

fn load_report(value: &Value) -> Result<AcceptanceReport, String> {
    AcceptanceReport::load(&value.to_string())
}

fn load_packet(value: &Value) -> Result<AdjudicationPacket, String> {
    AdjudicationPacket::load(&value.to_string())
}

// --------------------------------------------------------------- contract #

#[test]
fn contract_section_15_freezes_schemas_vocabularies_and_non_claims() {
    let path = repo_root().join("prd/architecture/npa-analysis-jsonl-contract.md");
    let text = fs::read_to_string(&path).expect("the contract doc must be readable");
    for marker in [
        "## 15. S04 corpus acceptance contract",
        "### 15.1 Declared-before-run rule",
        "### 15.2 Schemas",
        "### 15.3 Separated report sections",
        "### 15.4 Closed vocabularies",
        "### 15.5 Fail-closed loading",
        "### 15.6 Non-claims",
        SAMPLE_SCHEMA,
        ACCEPTANCE_SCHEMA,
        ADJUDICATION_SCHEMA,
        "structural_integrity",
        "semantic_adjudication",
        "corpus_breadth",
        "horizon",
        "sample_size = 400",
        "draw_seed = 20308",
        "verified_ok",
        "read_back_refused",
        "verify_refused",
        "decode_refused",
        "gate_refused",
        "analysis_refused",
        "limit_line_bytes",
        "limit_records",
        "manifest_pin_mismatch",
        "line_bytes",
        "not_attempted",
        "no_reference",
        "needs_attention",
        "R1000 stays active/unclosed",
        "M208-wrz6fg stays parked",
        "semantic_reference_status=absent",
        "no C5 promotion",
    ] {
        assert!(
            text.contains(marker),
            "contract §15 must contain {marker:?}"
        );
    }
    assert!(
        text.contains("## 16. Out of scope"),
        "§15 insertion must renumber Out of scope"
    );
    assert!(
        text.contains("## 17. References"),
        "§15 insertion must renumber References"
    );
}

#[test]
fn schema_constants_match_the_contract_strings() {
    assert_eq!(SAMPLE_SCHEMA, "law-nexus/npa-analysis-corpus-sample/v1");
    assert_eq!(
        ACCEPTANCE_SCHEMA,
        "law-nexus/npa-analysis-corpus-acceptance/v1"
    );
    assert_eq!(
        ADJUDICATION_SCHEMA,
        "law-nexus/npa-analysis-adjudication-packet/v1"
    );
}

// --------------------------------------------------------------- positive #

#[test]
fn valid_sample_report_and_packet_load_and_validate() {
    let manifest = load_manifest(&sample_manifest_json()).expect("valid manifest loads");
    assert_eq!(manifest.entries.len() as u64, DECLARED_SAMPLE_SIZE);
    assert!(manifest.declared_before_run);

    let report = load_report(&acceptance_report_json()).expect("valid report loads");
    assert_eq!(report.verdict.as_str(), "pass");
    assert!(!report.semantic_adjudication.promotion);
    assert_eq!(
        report.semantic_adjudication.semantic_reference_status,
        "absent"
    );
    assert!(report.corpus_breadth.coverage_claim.is_none());

    let packet = load_packet(&adjudication_packet_json()).expect("valid packet loads");
    assert!(!packet.promotion);

    let entry = json!({
        "relative_path": "npa/law_0000/edition-0001.xml",
        "sha256": format!("{:064x}", 1),
        "bytes": 100,
        "provider": "consultant_export",
        "document_type": "law",
        "work_family": "law_0000",
        "outcome": "verified_ok",
        "wall_ms": 5,
    });
    AcceptanceEntry::load_line(&entry.to_string()).expect("a verified entry loads");
}

// --------------------------------------------------------------- negative #

#[test]
fn missing_thresholds_block_is_refused() {
    let mut value = sample_manifest_json();
    value
        .as_object_mut()
        .expect("manifest is an object")
        .remove("declared_thresholds");
    let error = load_manifest(&value).expect_err("missing thresholds must be refused");
    assert!(
        error.contains("declared_thresholds") || error.contains("missing field"),
        "unexpected error: {error}"
    );
}

#[test]
fn unknown_tokens_are_refused() {
    let mut value = sample_manifest_json();
    value["entries"][0]["provider"] = json!("bogus_provider");
    assert!(
        load_manifest(&value).is_err(),
        "unknown provider token must be refused"
    );

    let mut report = acceptance_report_json();
    report["verdict"] = json!("mostly_pass");
    assert!(
        load_report(&report).is_err(),
        "unknown verdict token must be refused"
    );

    let mut report = acceptance_report_json();
    report["structural_integrity"]["verify_codes"] = json!({"bogus_code": 1});
    report["structural_integrity"]["verify_refused"] = json!(1);
    report["structural_integrity"]["structural_failures"] = json!(1);
    report["structural_integrity"]["pass"] = json!(false);
    report["structural_integrity"]["verified_ok"] = json!(DECLARED_SAMPLE_SIZE - 1);
    report["verdict"] = json!("needs_attention");
    assert!(
        load_report(&report).is_err(),
        "unknown verify_code token must be refused"
    );
}

#[test]
fn duplicate_entries_are_refused() {
    let mut value = sample_manifest_json();
    value["entries"][1]["relative_path"] = value["entries"][0]["relative_path"].clone();
    let error = load_manifest(&value).expect_err("duplicate relative paths must be refused");
    assert!(error.contains("duplicate"), "unexpected error: {error}");

    let mut value = sample_manifest_json();
    value["entries"][1]["sha256"] = value["entries"][0]["sha256"].clone();
    assert!(
        load_manifest(&value).is_err(),
        "duplicate sha256 must be refused"
    );
}

#[test]
fn traversal_and_absolute_paths_are_refused() {
    let mut value = sample_manifest_json();
    value["entries"][0]["relative_path"] = json!("../escape.xml");
    let error = load_manifest(&value).expect_err("a `..` path must be refused");
    assert!(error.contains("traverse"), "unexpected error: {error}");

    let mut value = sample_manifest_json();
    value["entries"][0]["relative_path"] = json!("/etc/passwd");
    assert!(
        load_manifest(&value).is_err(),
        "an absolute path must be refused"
    );

    let mut value = sample_manifest_json();
    value["roots"][0]["relative_path"] = json!("consru_export/../../secret");
    assert!(
        load_manifest(&value).is_err(),
        "a `..` root must be refused"
    );
}

#[test]
fn raw_text_bearing_fields_are_refused() {
    for key in ["text", "decoded_text", "inline_text", "source_utf8"] {
        let mut value = sample_manifest_json();
        value
            .as_object_mut()
            .expect("manifest is an object")
            .insert(key.to_string(), json!("decoded corpus fragment"));
        let error =
            load_manifest(&value).expect_err("a raw-text-bearing field must be refused anywhere");
        assert!(
            error.contains("forbidden"),
            "unexpected error for {key}: {error}"
        );
    }
}

#[test]
fn semantic_promotion_and_breadth_overclaim_are_refused() {
    let mut report = acceptance_report_json();
    report["semantic_adjudication"]["promotion"] = json!(true);
    assert!(load_report(&report).is_err(), "promotion must be refused");

    let mut report = acceptance_report_json();
    report["semantic_adjudication"]["semantic_reference_status"] = json!("present");
    assert!(
        load_report(&report).is_err(),
        "a non-absent reference must be refused"
    );

    let mut report = acceptance_report_json();
    report["corpus_breadth"]["coverage_claim"] = json!("full corpus coverage");
    assert!(
        load_report(&report).is_err(),
        "a coverage claim must be refused"
    );

    let mut packet = adjudication_packet_json();
    packet["promotion"] = json!(true);
    assert!(
        load_packet(&packet).is_err(),
        "a promoted packet must be refused"
    );
}

#[test]
fn non_active_r1000_and_verdict_inconsistency_are_refused() {
    let mut report = acceptance_report_json();
    report["horizon"]["r1000_status"] = json!("closed");
    assert!(
        load_report(&report).is_err(),
        "a closed R1000 must be refused"
    );

    // A structural failure can never be reported as `pass`.
    let mut report = acceptance_report_json();
    report["structural_integrity"]["verified_ok"] = json!(DECLARED_SAMPLE_SIZE - 1);
    report["structural_integrity"]["read_back_refused"] = json!(1);
    report["structural_integrity"]["structural_failures"] = json!(1);
    report["structural_integrity"]["pass"] = json!(false);
    report["verdict"] = json!("pass");
    let error = load_report(&report).expect_err("pass must not survive a structural failure");
    assert!(error.contains("verdict"), "unexpected error: {error}");
}

#[test]
fn entry_outcome_coherence_is_enforced() {
    let base = json!({
        "relative_path": "npa/law_0000/edition-0001.xml",
        "sha256": format!("{:064x}", 1),
        "bytes": 100,
        "provider": "consultant_export",
        "document_type": "law",
        "work_family": "law_0000",
        "outcome": "verify_refused",
        "wall_ms": 5,
    });
    assert!(
        AcceptanceEntry::load_line(&base.to_string()).is_err(),
        "verify_refused without a verify_code must be refused"
    );

    let mut ok = base.clone();
    ok["verify_code"] = json!("seal_mismatch");
    assert!(AcceptanceEntry::load_line(&ok.to_string()).is_ok());

    let mut bad = base;
    bad["outcome"] = json!("limit_line_bytes");
    bad["verify_code"] = json!("seal_mismatch");
    assert!(
        AcceptanceEntry::load_line(&bad.to_string()).is_err(),
        "limit outcome with a verify_code must be refused"
    );
}
