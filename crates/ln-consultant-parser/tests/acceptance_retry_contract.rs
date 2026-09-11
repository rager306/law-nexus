use std::{fs, path::PathBuf, process::Command};

use ln_consultant_parser::acceptance_retry_contract::{AcceptanceContract, CheckMode};
use ln_consultant_parser::contour_diagnostics::{self, Cli, EXIT_INCOMPARABLE, EXIT_USAGE};

fn fixture() -> PathBuf {
    let path = std::env::temp_dir().join(format!(
        "ln-c4-acceptance-{}-{:?}",
        std::process::id(),
        std::thread::current().id()
    ));
    let _ = fs::create_dir_all(&path);
    fs::write(path.join("law_2024-01.xml"), b"<not-wordml/>").unwrap();
    path
}

fn contract_path() -> &'static str {
    concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../prd/architecture/npa-acceptance-contract.yaml"
    )
}

#[test]
fn tracked_contract_is_strict_and_has_runtime_and_artifact_checks() {
    let contract = AcceptanceContract::parse_file(contract_path()).unwrap();
    assert_eq!(contract.contract_version, "npa-acceptance-contract/v1");
    assert!(contract.checks.iter().any(|c| c.mode == CheckMode::Runtime));
    assert!(contract
        .checks
        .iter()
        .any(|c| c.mode == CheckMode::Artifact));
    assert_eq!(contract.non_claims.len(), 3);
}

#[test]
fn acceptance_requires_explicit_source_pin() {
    let root = fixture();
    let cli = Cli {
        root: Some(root.display().to_string()),
        acceptance_contract: Some(contract_path().into()),
        ..Cli::default()
    };
    assert_eq!(contour_diagnostics::run(&cli, &root).0, EXIT_USAGE);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn receipt_binds_identity_and_mode_mismatch_cannot_reuse_baseline() {
    let root = fixture();
    let out = root.join("receipt.jsonl");
    let base = Cli {
        root: Some(root.display().to_string()),
        out: Some(out.display().to_string()),
        acceptance_contract: Some(contract_path().into()),
        acceptance_mode: Some("runtime".into()),
        source_revision: Some("caller-pin:test-source-v1".into()),
        argv: vec!["--acceptance-mode".into(), "runtime".into()],
        ..Cli::default()
    };
    assert_eq!(contour_diagnostics::run(&base, &root).0, 0);
    let first = fs::read_to_string(&out).unwrap();
    for marker in [
        "\"acceptance_contract_version\":\"npa-acceptance-contract/v1\"",
        "\"acceptance_check_id\":\"c4-live-check\"",
        "\"acceptance_mode\":\"runtime\"",
        "\"source_revision\":\"caller-pin:test-source-v1\"",
        "\"argv\":[\"--acceptance-mode\",\"runtime\"]",
        "\"observed_rustc_version\":\"rustc ",
        "\"duration_ms\":",
    ] {
        assert!(first.contains(marker), "missing marker {marker}");
    }

    let mut retry = base.clone();
    retry.check = true;
    assert_eq!(contour_diagnostics::run(&retry, &root).0, 0);
    assert_eq!(fs::read_to_string(&out).unwrap(), first);

    retry.acceptance_mode = Some("artifact".into());
    retry.argv = vec!["--acceptance-mode".into(), "artifact".into()];
    assert_eq!(contour_diagnostics::run(&retry, &root).0, EXIT_INCOMPARABLE);
    assert_eq!(fs::read_to_string(&out).unwrap(), first);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn cli_rejects_invalid_contract_before_walking() {
    let root = fixture();
    let invalid = root.join("invalid.yaml");
    fs::write(&invalid, "schema: npa-acceptance-contract/v2\n").unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_npa-contour-diagnostics"))
        .args([
            "--root",
            root.to_str().unwrap(),
            "--acceptance-contract",
            invalid.to_str().unwrap(),
            "--source-revision",
            "caller-pin:test",
        ])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(EXIT_USAGE as i32));
    let _ = fs::remove_dir_all(root);
}
