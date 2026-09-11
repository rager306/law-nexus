use std::{fs, path::PathBuf};

use ln_consultant_parser::contour_diagnostics::{
    self, Cli, Comparison, EXIT_INCOMPARABLE, EXIT_MISSING, EXIT_ROOT_MISSING,
};

fn fixture() -> PathBuf {
    let path = std::env::temp_dir().join(format!(
        "ln-c4-{}-{:?}",
        std::process::id(),
        std::thread::current().id()
    ));
    let _ = fs::create_dir_all(&path);
    fs::write(path.join("law_2024-01.xml"), b"<not-wordml/>").unwrap();
    path
}

#[test]
fn bounded_run_is_closed_and_deterministic() {
    let root = fixture();
    let cli = Cli {
        root: Some(root.display().to_string()),
        limit: Some(1),
        label: "contract".into(),
        ..Cli::default()
    };
    let first = contour_diagnostics::run(&cli, &root);
    let second = contour_diagnostics::run(&cli, &root);
    assert_eq!(first.0, 0);
    assert_eq!(first.1, second.1);
    let report = first.1.unwrap();
    contour_diagnostics::validate_jsonl(&report).unwrap();
    assert!(report.contains("non_claims"));
    assert!(!report.contains("not-wordml"));
    let _ = fs::remove_dir_all(root);
}

#[test]
fn malformed_file_is_counted_not_panicked() {
    let root = fixture();
    let cli = Cli {
        root: Some(root.display().to_string()),
        ..Cli::default()
    };
    let (_, report, _) = contour_diagnostics::run(&cli, &root);
    assert!(report.unwrap().contains("failed"));
    let _ = fs::remove_dir_all(root);
}

#[test]
fn missing_explicit_root_is_fail_closed() {
    let root = std::env::temp_dir().join("ln-c4-does-not-exist");
    let cli = Cli {
        root: Some(root.display().to_string()),
        ..Cli::default()
    };
    assert_eq!(contour_diagnostics::run(&cli, &root).0, EXIT_ROOT_MISSING);
}

#[test]
fn jobs_two_matches_sequential_on_fixture() {
    let root = fixture();
    let sequential = Cli {
        root: Some(root.display().to_string()),
        limit: Some(1),
        label: "jobs-contract".into(),
        jobs: 1,
        ..Cli::default()
    };
    let mut parallel = sequential.clone();
    parallel.jobs = 2;
    let first = contour_diagnostics::run(&sequential, &root);
    let second = contour_diagnostics::run(&parallel, &root);
    assert_eq!(first.0, 0);
    assert_eq!(first.0, second.0);
    assert_eq!(first.1, second.1);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn canonical_payload_and_comparison_are_fail_closed() {
    let root = fixture();
    let cli = Cli {
        root: Some(root.display().to_string()),
        limit: Some(1),
        ..Cli::default()
    };
    let report = contour_diagnostics::run(&cli, &root).1.unwrap();
    assert!(report.contains("npa-contour-diagnostics/v2"));
    assert!(report.contains("block_presence"));
    assert!(report.contains("identity_binding_not_measured"));
    assert_eq!(
        contour_diagnostics::compare_reports(&report, None),
        Comparison::MissingBaseline
    );
    assert_eq!(
        contour_diagnostics::compare_reports(&report, Some("{}")),
        Comparison::IncomparableInput
    );
    let forged = report.replace("inventory_digest", "forged_digest");
    assert_eq!(
        contour_diagnostics::compare_reports(&report, Some(&forged)),
        Comparison::IncomparableInput
    );
    let drift = report.replace("\"files\":1", "\"files\":2");
    assert_eq!(
        contour_diagnostics::compare_reports(&report, Some(&drift)),
        Comparison::SemanticDrift
    );
    let operational = report.replace("\"label\":\"fixture-gate\"", "\"label\":\"other\"");
    assert_eq!(
        contour_diagnostics::compare_reports(&report, Some(&operational)),
        Comparison::OperationalOnly
    );
    let _ = fs::remove_dir_all(root);
}

#[test]
fn check_codes_distinguish_missing_and_incomparable_baselines() {
    let root = fixture();
    let out = root.join("receipt.jsonl");
    let base = Cli {
        root: Some(root.display().to_string()),
        out: Some(out.display().to_string()),
        ..Cli::default()
    };
    assert_eq!(contour_diagnostics::run(&base, &root).0, 0);
    fs::write(&out, "{}").unwrap();
    let mut check = base.clone();
    check.check = true;
    assert_eq!(contour_diagnostics::run(&check, &root).0, EXIT_INCOMPARABLE);
    fs::remove_file(&out).unwrap();
    assert_eq!(contour_diagnostics::run(&check, &root).0, EXIT_MISSING);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn check_rejects_stale_receipt() {
    let root = fixture();
    let out = root.join("receipt.jsonl");
    let base = Cli {
        root: Some(root.display().to_string()),
        out: Some(out.display().to_string()),
        limit: Some(1),
        label: "check-contract".into(),
        ..Cli::default()
    };
    assert_eq!(contour_diagnostics::run(&base, &root).0, 0);
    let mut check = base.clone();
    check.check = true;
    assert_eq!(contour_diagnostics::run(&check, &root).0, 0);
    check.label = "changed-label".into();
    assert_eq!(contour_diagnostics::run(&check, &root).0, 0);
    let _ = fs::remove_dir_all(root);
}
