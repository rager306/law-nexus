use ln_consultant_parser::drift_baseline::{
    comparable, peak_memory_bytes, regression_disposition, validate_ledger,
};

#[test]
fn incomparable_context_baseline_is_quarantined_fail_closed() {
    assert!(!comparable(true, false, false, true));
    assert_eq!(regression_disposition(false, false), "quarantine");
    assert_eq!(regression_disposition(false, true), "quarantine");
}

#[test]
fn comparable_exact_baseline_distinguishes_drift() {
    assert!(comparable(true, true, true, true));
    assert_eq!(regression_disposition(true, false), "pass");
    assert_eq!(regression_disposition(true, true), "fail");
    assert!(!comparable(true, true, true, false));
}

#[test]
fn ledger_requires_contiguous_unique_pinned_events() {
    let good = r#"{"event_id":"NPA-METRIC-20260909-000001","sequence":1,"supersedes":null,"classification":"exact","metric_family":"operational"}
{"event_id":"NPA-REGRESSION-20260909-000002","sequence":2,"supersedes":null,"classification":"exact","metric_family":"operational"}
"#;
    validate_ledger(good).expect("valid append-only ledger");
    let gap = good.replace("\"sequence\":2", "\"sequence\":3");
    assert!(validate_ledger(&gap).is_err());
    let duplicate = good.replace(
        "NPA-REGRESSION-20260909-000002",
        "NPA-METRIC-20260909-000001",
    );
    assert!(validate_ledger(&duplicate).is_err());
}

#[test]
fn ledger_rejects_future_supersedes_and_proxy_exact_collision() {
    let future = r#"{"event_id":"NPA-METRIC-20260909-000001","sequence":1,"supersedes":"NPA-METRIC-20260909-000009","classification":"exact","metric_family":"operational"}
"#;
    assert!(validate_ledger(future).is_err());
    let proxy = r#"{"event_id":"NPA-METRIC-20260909-000001","sequence":1,"supersedes":null,"classification":"proxy","metric_family":"exact"}
"#;
    assert!(validate_ledger(proxy).is_err());
}

#[test]
fn memory_probe_is_explicitly_optional_on_non_linux() {
    let memory = peak_memory_bytes().expect("VmHWM probe should not fail on supported host");
    if cfg!(target_os = "linux") {
        assert!(memory.is_some());
    }
}

#[test]
fn durable_perf_and_ledger_artifacts_are_present_and_safe() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("prd/migration/rust-evidence");
    let perf =
        std::fs::read_to_string(root.join("m203-s08-perf-receipts.jsonl")).expect("perf receipt");
    let ledger =
        std::fs::read_to_string(root.join("m203-s08-ledger-events.jsonl")).expect("ledger");
    assert!(perf.contains("law-nexus-npa-metric-event/v1"));
    assert!(perf.contains("\"raw_text\":false"));
    validate_ledger(&ledger).expect("ledger contract");
    assert!(!ledger.contains("raw_text_value"));
}
