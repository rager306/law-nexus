//! M211 S04 T05: `npa-integration-runner` argv/exit-code contract.
//!
//! The thin binary is exercised end to end with a bounded temp corpus, while
//! the frozen-fixture path is driven through the library (`run_integration_report`),
//! which is exactly what the binary calls. No test walks the real
//! `consru_export` corpus.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use ln_decode::npa_report::{
    parse_integration_args, run_integration_report, IntegrationCli, INTEGRATION_SCHEMA,
};
use ln_decode::npa_sweep::{EXIT_OK, EXIT_ROOT_MISSING, EXIT_USAGE};

fn absent_default() -> &'static Path {
    Path::new("/npa-integration-runner-absent-default-root")
}

fn temp_root(tag: &str) -> PathBuf {
    let path = std::env::temp_dir().join(format!(
        "npa-integration-runner-{tag}-{}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&path);
    fs::create_dir_all(&path).expect("fixture root");
    path
}

fn write_xml(root: &Path, name: &str) {
    fs::write(
        root.join(name),
        r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:r><w:t>Федеральный закон от 01.01.2020 N 1-ФЗ</w:t></w:r></w:p></w:wordDocument>"#,
    )
    .expect("fixture xml");
}

#[test]
fn cli_parser_is_closed_and_bounded() {
    let cli = parse_integration_args([
        "--root".into(),
        "root".into(),
        "--out".into(),
        "out.json".into(),
        "--limit".into(),
        "0".into(),
        "--label".into(),
        "bounded".into(),
    ])
    .expect("accepted flags");
    assert_eq!(cli.root.as_deref(), Some("root"));
    assert_eq!(cli.out.as_deref(), Some("out.json"));
    assert_eq!(cli.limit, Some(0));
    assert_eq!(cli.label.as_deref(), Some("bounded"));

    assert!(parse_integration_args(vec!["--bogus".into()]).is_err());
    assert!(parse_integration_args(vec!["positional".into()]).is_err());
    assert!(parse_integration_args(vec!["--root".into()]).is_err());
    assert!(parse_integration_args(vec!["--limit".into(), "x".into()]).is_err());
}

#[test]
fn binary_help_exits_zero() {
    let output = Command::new(env!("CARGO_BIN_EXE_npa-integration-runner"))
        .arg("--help")
        .output()
        .expect("binary launches");
    assert!(output.status.success(), "help must exit 0");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("npa-integration-runner"), "usage text");
    assert!(
        stdout.contains("npa-integration-report/v1"),
        "usage names the schema"
    );
}

#[test]
fn binary_unknown_flag_is_usage_error() {
    let output = Command::new(env!("CARGO_BIN_EXE_npa-integration-runner"))
        .arg("--definitely-not-a-flag")
        .output()
        .expect("binary launches");
    assert_eq!(output.status.code(), Some(EXIT_USAGE as i32));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("unexpected argument"),
        "usage error is reported"
    );
}

#[test]
fn frozen_fixture_run_exits_zero_with_valid_json() {
    let run = run_integration_report(&IntegrationCli::default(), absent_default());
    assert_eq!(run.exit_code, EXIT_OK, "stderr: {}", run.stderr);
    let json = run.json.expect("report");
    assert!(json.contains(INTEGRATION_SCHEMA));
    assert!(json.starts_with('{') && json.ends_with("}\n"));
    assert!(
        json.contains("\"run_status\": \"skipped\""),
        "absent default root keeps the fixture report but marks the corpus skip"
    );
}

#[test]
fn explicit_missing_root_is_root_missing() {
    let cli = IntegrationCli {
        root: Some("/npa-integration-runner-explicit-missing".into()),
        ..IntegrationCli::default()
    };
    let run = run_integration_report(&cli, absent_default());
    assert_eq!(run.exit_code, EXIT_ROOT_MISSING);
    assert!(run.json.is_none());
    assert!(run.stderr.contains("root not found"));
}

#[test]
fn corpus_mode_with_a_root_walks_and_reports_measured() {
    let root = temp_root("fixture");
    write_xml(&root, "a.xml");

    let cli = IntegrationCli {
        root: Some(root.to_string_lossy().into_owned()),
        ..IntegrationCli::default()
    };
    let run = run_integration_report(&cli, absent_default());
    assert_eq!(run.exit_code, EXIT_OK, "stderr: {}", run.stderr);
    let json = run.json.expect("report");
    assert!(json.contains("\"run_status\": \"complete\""));
    assert!(json.contains("\"status\": \"measured\""));
    assert!(json.contains("\"files_attempted\": 1"));
    assert!(
        !json.contains("Федеральный закон"),
        "payload text must never leak into the count-only corpus plane"
    );

    fs::remove_dir_all(root).ok();
}

#[test]
fn out_path_writes_atomically_and_stays_count_only() {
    let root = temp_root("out");
    write_xml(&root, "a.xml");
    let out = root.join("report.json");

    let cli = IntegrationCli {
        root: Some(root.to_string_lossy().into_owned()),
        out: Some(out.to_string_lossy().into_owned()),
        limit: Some(1),
        ..IntegrationCli::default()
    };
    let run = run_integration_report(&cli, absent_default());
    assert_eq!(run.exit_code, EXIT_OK, "stderr: {}", run.stderr);
    assert!(run.json.is_none(), "with --out nothing streams to stdout");
    assert!(!run.to_stdout);
    let written = fs::read_to_string(&out).expect("atomic output written");
    assert!(written.contains(INTEGRATION_SCHEMA));
    assert!(written.contains("\"files_decoded\": 1"));
    assert!(!written.contains("Федеральный закон"));

    fs::remove_dir_all(root).ok();
}

#[test]
fn binary_end_to_end_on_bounded_root() {
    let root = temp_root("bin");
    write_xml(&root, "a.xml");
    let output = Command::new(env!("CARGO_BIN_EXE_npa-integration-runner"))
        .arg("--root")
        .arg(root.to_string_lossy().as_ref())
        .arg("--label")
        .arg("bounded-smoke")
        .output()
        .expect("binary launches");
    assert!(output.status.success(), "exit 0 on bounded root");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains(INTEGRATION_SCHEMA));
    assert!(stdout.contains("\"label\": \"bounded-smoke\""));
    assert!(stdout.contains("\"run_status\": \"complete\""));

    fs::remove_dir_all(root).ok();
}
