//! T03 CLI contract (M200-8s4kwq S01): `npa-bounds-scan` argv semantics and
//! the thin runner exit-code contract. The strict stdlib parser and the
//! runner live in `ln_decode::npa_bounds` so contract tests exercise
//! library functions; the binary itself is argv + printing only, and its
//! `--help` smoke is the plan's `cargo run ... -- --help` verify step.

use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::npa_bounds::{parse_bounds_args, run_bounds_scan, validate_bounds_jsonl, BoundsCli};
use ln_decode::npa_sweep::{EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_ROOT_MISSING};

const ABSENT: &str = "/npa-bounds-cli-t03-absent-root";

/// Minimal Consultant WordML fixture: one paragraph per `&str` entry.
fn wordml_document(paragraphs: &[&str]) -> String {
    let body = paragraphs
        .iter()
        .map(|text| format!("<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"))
        .collect::<String>();
    format!("<w:wordDocument xmlns:w=\"urn:word\">{body}</w:wordDocument>")
}

/// Unique per-test temp root; pre-cleaned so reruns start empty.
fn temp_root(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("npa-bounds-cli-t03-{}-{tag}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp bounds cli root must be creatable");
    dir
}

fn write_xml(root: &Path, relative: &str, paragraphs: &[&str]) {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("relative parent exists")).expect("fixture dir");
    fs::write(&path, wordml_document(paragraphs)).expect("fixture xml");
}

/// CLI with fixed clock metadata so repeated runs are byte-identical.
fn fixed_cli() -> BoundsCli {
    BoundsCli {
        started_at: Some("2026-09-05T00:00:00Z".to_owned()),
        ended_at: Some("2026-09-05T00:00:01Z".to_owned()),
        ..BoundsCli::default()
    }
}

/// T03: the strict stdlib argv parser accepts the full flag set with
/// defaults, later-occurrence override, and a joined command line.
#[test]
fn t03_cli_parse_flags_defaults_and_overrides() {
    let cli = parse_bounds_args(Vec::new()).expect("empty argv is the default run");
    assert_eq!(cli, BoundsCli::default());
    assert_eq!(cli.label, "fixture-gate");
    assert_eq!(cli.command, "npa-bounds-scan");

    let cli = parse_bounds_args([
        "--root".to_owned(),
        "r".to_owned(),
        "--out".to_owned(),
        "o".to_owned(),
        "--limit".to_owned(),
        "3".to_owned(),
        "--label".to_owned(),
        "L".to_owned(),
        "--source-revision".to_owned(),
        "R".to_owned(),
        "--rust-toolchain".to_owned(),
        "T".to_owned(),
    ])
    .expect("full flag set parses");
    assert_eq!(cli.root.as_deref(), Some("r"));
    assert_eq!(cli.out.as_deref(), Some("o"));
    assert_eq!(cli.limit, Some(3));
    assert_eq!(cli.label, "L");
    assert_eq!(cli.source_revision.as_deref(), Some("R"));
    assert_eq!(cli.rust_toolchain.as_deref(), Some("T"));
    assert_eq!(
        cli.command,
        "npa-bounds-scan --root r --out o --limit 3 --label L --source-revision R --rust-toolchain T"
    );

    let cli = parse_bounds_args([
        "--limit".to_owned(),
        "1".to_owned(),
        "--limit".to_owned(),
        "2".to_owned(),
    ])
    .expect("later occurrences override earlier ones");
    assert_eq!(cli.limit, Some(2));
}

/// T03: unknown flags, positionals, missing flag values, and non-numeric
/// limits are usage errors (the bin maps them to exit 2).
#[test]
fn t03_cli_parse_rejects_bad_argv() {
    assert!(parse_bounds_args(vec!["--unknown".to_owned()]).is_err());
    assert!(parse_bounds_args(vec!["positional".to_owned()]).is_err());
    assert!(parse_bounds_args(vec!["--root".to_owned()]).is_err());
    assert!(parse_bounds_args(vec!["--out".to_owned()]).is_err());
    assert!(parse_bounds_args(vec!["--label".to_owned()]).is_err());
    assert!(
        parse_bounds_args(vec!["--limit".to_owned(), "x".to_owned()]).is_err(),
        "non-numeric limit"
    );
    assert!(
        parse_bounds_args(vec!["--limit".to_owned(), "-1".to_owned()]).is_err(),
        "negative limit"
    );
}

/// T03: a successful run maps the exit-OK path, writes `--out`
/// byte-identically across repeated runs, and reports counts on stderr.
#[test]
fn t03_cli_run_ok_writes_out_and_counts() {
    let root = temp_root("ok");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    write_xml(&root, "exports/npa/b.xml", &["01.02.2003 65-ФЗ"]);
    let out_a = root.join("bounds-a.jsonl");

    let mut cli = fixed_cli();
    cli.root = Some(root.to_string_lossy().into_owned());
    cli.out = Some(out_a.to_string_lossy().into_owned());
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(
        run.jsonl.is_none(),
        "an --out run returns nothing for stdout"
    );
    assert!(run.stderr.contains("files_attempted=2"));
    assert!(run.stderr.contains("files_decoded=2"));
    let first_bytes = fs::read(&out_a).expect("out written");

    // Same argv (same output artifact) once more: the repeated run must be
    // byte-identical. (A different --out path lawfully changes the
    // manifest's output_artifact field, so identity is pinned per argv.)
    let run_two = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run_two.exit_code, EXIT_OK);
    assert_eq!(
        first_bytes,
        fs::read(&out_a).expect("second out written"),
        "repeated runs are byte-identical"
    );
    let written = fs::read_to_string(&out_a).expect("out readable");
    validate_bounds_jsonl(&written).expect("the out file stays closed");

    fs::remove_dir_all(&root).ok();
}

/// T03: without `--out` the aggregate goes to stdout and stays closed.
#[test]
fn t03_cli_run_stdout_when_no_out() {
    let root = temp_root("stdout");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    let mut cli = fixed_cli();
    cli.root = Some(root.to_string_lossy().into_owned());
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.to_stdout);
    let jsonl = run.jsonl.expect("stdout run returns the aggregate");
    validate_bounds_jsonl(&jsonl).expect("closed schema");

    fs::remove_dir_all(&root).ok();
}

/// T03: an explicit missing root is `EXIT_ROOT_MISSING`; an unwritable
/// `--out` target is `EXIT_OUT_UNWRITABLE` with a failure note.
#[test]
fn t03_cli_missing_explicit_root_and_unwritable_out() {
    let cli = BoundsCli {
        root: Some(ABSENT.to_owned()),
        ..fixed_cli()
    };
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_ROOT_MISSING);
    assert!(run.jsonl.is_none());
    assert!(run.stderr.contains("root not found"));

    let root = temp_root("unwritable");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    let mut cli = fixed_cli();
    cli.root = Some(root.to_string_lossy().into_owned());
    cli.out = Some(
        root.join("no")
            .join("such")
            .join("dir")
            .join("bounds.jsonl")
            .to_string_lossy()
            .into_owned(),
    );
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OUT_UNWRITABLE);
    assert!(run.stderr.contains("cannot open --out"));

    fs::remove_dir_all(&root).ok();
}

/// T03: a missing default root is skip-mode — exit 0 with a zeroed closed
/// aggregate on stdout and a skip note on stderr.
#[test]
fn t03_cli_skip_mode_default_root_absent() {
    let run = run_bounds_scan(&fixed_cli(), Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.to_stdout);
    assert!(run.stderr.starts_with("skip:"));
    let jsonl = run.jsonl.expect("skip-mode renders the zeroed aggregate");
    validate_bounds_jsonl(&jsonl).expect("closed schema");
    assert!(jsonl.contains("\"files_attempted\":0"));
    assert!(jsonl.contains("\"observed_file_count\":0"));

    fs::remove_dir_all(ABSENT).ok();
}

/// T03: `--limit 0` runs the empty walk — zero attempts, closed aggregate.
#[test]
fn t03_cli_limit_zero_runs_empty() {
    let root = temp_root("limit0");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    let mut cli = fixed_cli();
    cli.root = Some(root.to_string_lossy().into_owned());
    cli.limit = Some(0);
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.stderr.contains("files_attempted=0"));
    let jsonl = run.jsonl.expect("empty run still renders the aggregate");
    assert!(jsonl.contains("\"files_attempted\":0"));
    validate_bounds_jsonl(&jsonl).expect("closed schema");

    fs::remove_dir_all(&root).ok();
}
