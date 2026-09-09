use std::{fs, path::PathBuf};

use ln_consultant_parser::contour_diagnostics::{self, Cli, EXIT_ROOT_MISSING};

fn fixture() -> PathBuf {
    let path = std::env::temp_dir().join(format!("ln-c4-{}", std::process::id()));
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
