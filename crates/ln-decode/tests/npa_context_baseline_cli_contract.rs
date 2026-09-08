//! Contract tests for the bounded, count-only document-context baseline.

use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::npa_context_baseline::{
    parse_context_baseline_args, run_context_baseline, validate_context_baseline_jsonl, ContextCli,
    CONTEXT_SCHEMA,
};
use ln_decode::npa_sweep::{EXIT_OK, EXIT_ROOT_MISSING};

fn temp_root(tag: &str) -> PathBuf {
    let path =
        std::env::temp_dir().join(format!("npa-context-baseline-{tag}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&path);
    fs::create_dir_all(&path).expect("fixture root");
    path
}

fn write_xml(root: &Path, name: &str) {
    fs::write(
        root.join(name),
        r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:r><w:t>ст. 15.1</w:t></w:r></w:p></w:wordDocument>"#,
    )
    .expect("fixture xml");
}

#[test]
fn cli_parser_is_closed_and_bounded() {
    let cli = parse_context_baseline_args([
        "--root".into(),
        "root".into(),
        "--limit".into(),
        "0".into(),
        "--label".into(),
        "bounded".into(),
        "--progress".into(),
        "2".into(),
    ])
    .expect("accepted flags");
    assert_eq!(cli.root.as_deref(), Some("root"));
    assert_eq!(cli.limit, Some(0));
    assert_eq!(cli.label, "bounded");
    assert_eq!(cli.progress_every, Some(2));
    assert!(parse_context_baseline_args(vec!["--unknown".into()]).is_err());
    assert!(parse_context_baseline_args(vec!["--progress".into(), "0".into()]).is_err());
}

#[test]
fn absent_default_root_is_explicit_skip_mode() {
    let root = Path::new("/npa-context-baseline-default-root-absent");
    let _ = fs::remove_dir_all(root);
    let run = run_context_baseline(&ContextCli::default(), root);
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.to_stdout);
    assert!(run.stderr.starts_with("skip:"));
    let jsonl = run.jsonl.expect("skip aggregate");
    validate_context_baseline_jsonl(&jsonl).expect("closed JSONL");
    assert!(jsonl.contains(CONTEXT_SCHEMA));
    assert!(jsonl.contains("\"files_attempted\":0"));
}

#[test]
fn explicit_missing_root_is_not_silent_skip() {
    let cli = ContextCli {
        root: Some("/npa-context-baseline-explicit-missing".into()),
        ..ContextCli::default()
    };
    let run = run_context_baseline(&cli, Path::new("/unused-default"));
    assert_eq!(run.exit_code, EXIT_ROOT_MISSING);
    assert!(run.jsonl.is_none());
    assert!(run.stderr.contains("root not found"));
}

#[test]
fn bounded_fixture_limit_zero_and_atomic_output_stay_count_only() {
    let root = temp_root("fixture");
    write_xml(&root, "a.xml");
    write_xml(&root, "b.xml");

    let empty = ContextCli {
        root: Some(root.to_string_lossy().into_owned()),
        limit: Some(0),
        ..ContextCli::default()
    };
    let run = run_context_baseline(&empty, Path::new("/unused-default"));
    assert_eq!(run.exit_code, EXIT_OK);
    let jsonl = run.jsonl.expect("stdout aggregate");
    validate_context_baseline_jsonl(&jsonl).expect("closed empty aggregate");
    assert!(jsonl.contains("\"files_attempted\":0"));

    let out = root.join("context.jsonl");
    let cli = ContextCli {
        root: Some(root.to_string_lossy().into_owned()),
        out: Some(out.to_string_lossy().into_owned()),
        limit: Some(1),
        ..ContextCli::default()
    };
    let run = run_context_baseline(&cli, Path::new("/unused-default"));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(!run.to_stdout);
    assert!(run.stderr.contains("files_attempted=1"));
    let written = fs::read_to_string(&out).expect("atomic output");
    validate_context_baseline_jsonl(&written).expect("closed output");
    assert!(written.contains("\"files_decoded\":1"));
    assert!(!written.contains("ст. 15.1"), "payload text must not leak");

    fs::remove_dir_all(root).ok();
}
