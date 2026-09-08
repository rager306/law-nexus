//! Contract tests for the count-only npa-frames-baseline diagnostic profile.
use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::npa_frames_baseline::{
    parse_frames_baseline_args, run_frames_baseline, validate_frames_baseline_jsonl, FramesCli,
    FRAMES_SCHEMA,
};
use ln_decode::npa_sweep::{EXIT_OK, EXIT_ROOT_MISSING};

const ABSENT: &str = "/npa-frames-baseline-cli-absent-root";

fn temp_root(tag: &str) -> PathBuf {
    let root =
        std::env::temp_dir().join(format!("npa-frames-baseline-{}-{tag}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(root.join("exports/npa")).expect("fixture root");
    root
}

fn write_xml(root: &Path, name: &str, text: &str) {
    let xml = format!(
        "<w:wordDocument xmlns:w=\"urn:word\"><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:wordDocument>"
    );
    fs::write(root.join("exports/npa").join(name), xml).expect("fixture xml");
}

#[test]
fn t04_parser_accepts_flags_and_rejects_unknown_values() {
    let cli = parse_frames_baseline_args([
        "--root".into(),
        "r".into(),
        "--out".into(),
        "o".into(),
        "--limit".into(),
        "0".into(),
        "--label".into(),
        "baseline".into(),
        "--progress".into(),
        "2".into(),
    ])
    .expect("flags parse");
    assert_eq!(cli.root.as_deref(), Some("r"));
    assert_eq!(cli.out.as_deref(), Some("o"));
    assert_eq!(cli.limit, Some(0));
    assert_eq!(cli.label, "baseline");
    assert_eq!(cli.progress_every, Some(2));
    assert!(parse_frames_baseline_args(vec!["--unknown".into()]).is_err());
    assert!(parse_frames_baseline_args(vec!["--progress".into(), "0".into()]).is_err());
}

#[test]
fn t04_empty_scan_has_closed_header_and_zero_aggregate() {
    let root = temp_root("empty");
    write_xml(&root, "a.xml", "статья 15");
    let cli = FramesCli {
        root: Some(root.to_string_lossy().into_owned()),
        limit: Some(0),
        ..FramesCli::default()
    };
    let run = run_frames_baseline(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    let output = run.jsonl.expect("stdout aggregate");
    validate_frames_baseline_jsonl(&output).expect("closed schema");
    assert!(output.contains(&format!("\"schema\":\"{FRAMES_SCHEMA}\"")));
    assert!(output.contains("\"files_attempted\":0"));
    assert!(output.contains("\"frames\":0"));
    assert!(!output.contains("статья"));
    let _ = fs::remove_dir_all(root);
}

#[test]
fn t04_missing_default_root_is_skip_mode_and_explicit_root_fails() {
    let skip = run_frames_baseline(&FramesCli::default(), Path::new(ABSENT));
    assert_eq!(skip.exit_code, EXIT_OK);
    assert!(skip.stderr.starts_with("skip:"));
    validate_frames_baseline_jsonl(&skip.jsonl.expect("skip aggregate"))
        .expect("closed skip schema");

    let cli = FramesCli {
        root: Some(ABSENT.into()),
        ..FramesCli::default()
    };
    let missing = run_frames_baseline(&cli, Path::new(ABSENT));
    assert_eq!(missing.exit_code, EXIT_ROOT_MISSING);
    assert!(missing.jsonl.is_none());
    let _ = fs::remove_dir_all(ABSENT);
}

#[test]
fn t04_fixture_scan_reports_counts_only_and_statuses() {
    let root = temp_root("counts");
    write_xml(&root, "a.xml", "статья 15, 16 и 17");
    let cli = FramesCli {
        root: Some(root.to_string_lossy().into_owned()),
        ..FramesCli::default()
    };
    let run = run_frames_baseline(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.stderr.contains("files_attempted=1"));
    let output = run.jsonl.expect("stdout aggregate");
    validate_frames_baseline_jsonl(&output).expect("closed fixture schema");
    assert!(output.contains("\"files_attempted\":1"));
    assert!(output.contains("\"structural_values_max\":3"));
    assert!(output.contains("\"record_kind\":\"frame_status_counts\""));
    assert!(!output.contains("<w:"));
    let _ = fs::remove_dir_all(root);
}
