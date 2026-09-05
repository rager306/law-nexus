//! T03 CLI contract (M200-8s4kwq S01): `npa-bounds-scan` argv semantics and
//! the thin runner exit-code contract. The strict stdlib parser and the
//! runner live in `ln_decode::npa_bounds` so contract tests exercise
//! library functions; the binary itself is argv + printing only, and its
//! `--help` smoke is the plan's `cargo run ... -- --help` verify step.

use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::npa_bounds::{
    parse_bounds_args, run_bounds_scan, validate_bounds_jsonl, write_partial_out, BoundsAcc,
    BoundsCli, BoundsRunMeta,
};
use ln_decode::npa_sweep::{walk_and_observe, EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_ROOT_MISSING};

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

// ---------------------------------------------------------------------------
// T01 (M200-8s4kwq S02): run-metadata honesty. `ended_at` is captured after
// the walk completes unless injected by tests, stderr progress heartbeats
// are count-only, and periodic atomic rewrites of `--out` leave an explicit
// `run_status:"incomplete"` diagnostic when a run is killed mid-walk.
// ---------------------------------------------------------------------------

/// T01: an injected clock keeps renders byte-identical (the preserved S01
/// contract), and the terminal manifest closes with `run_status:"complete"`.
#[test]
fn t01_injected_clock_stays_byte_identical_and_complete() {
    let root = temp_root("t01-injected");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    write_xml(&root, "exports/npa/b.xml", &["01.02.2003 65-ФЗ"]);
    let out_a = root.join("bounds-inj-a.jsonl");

    let mut cli = fixed_cli();
    cli.root = Some(root.to_string_lossy().into_owned());
    cli.out = Some(out_a.to_string_lossy().into_owned());
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    let first_bytes = fs::read(&out_a).expect("first out written");

    // Same argv once more (a different --out path lawfully changes the
    // manifest's output_artifact field, so identity is pinned per argv).
    let run_two = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run_two.exit_code, EXIT_OK);
    assert_eq!(
        first_bytes,
        fs::read(&out_a).expect("second out written"),
        "injected clocks keep byte-identical renders"
    );
    let written = fs::read_to_string(&out_a).expect("out readable");
    validate_bounds_jsonl(&written).expect("closed schema");
    assert!(written.contains("\"run_status\":\"complete\""));
    assert!(written.contains("\"ended_at\":\"2026-09-05T00:00:01Z\""));

    fs::remove_dir_all(&root).ok();
}

/// T01: when `ended_at` is not injected, the runner captures it after the
/// walk completes — a completed run never renders a null `ended_at`, and
/// the injected `started_at` passes through untouched.
#[test]
fn t01_ended_at_captured_after_walk_when_not_injected() {
    let root = temp_root("t01-ended");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    write_xml(&root, "exports/npa/b.xml", &["01.02.2003 65-ФЗ"]);
    let out = root.join("bounds-ended.jsonl");

    let mut cli = fixed_cli();
    cli.ended_at = None;
    cli.root = Some(root.to_string_lossy().into_owned());
    cli.out = Some(out.to_string_lossy().into_owned());
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    let written = fs::read_to_string(&out).expect("out readable");
    validate_bounds_jsonl(&written).expect("closed schema");
    assert!(written.contains("\"run_status\":\"complete\""));
    assert!(written.contains("\"started_at\":\"2026-09-05T00:00:00Z\""));
    assert!(
        !written.contains("\"ended_at\":null"),
        "a completed run renders a real ended_at"
    );

    fs::remove_dir_all(&root).ok();
}

/// T01: `--progress <n>` parses into the heartbeat/flush interval; `0`,
/// non-numeric values, and missing values are usage errors.
#[test]
fn t01_progress_flag_parse() {
    let cli = parse_bounds_args([
        "--progress".to_owned(),
        "500".to_owned(),
        "--limit".to_owned(),
        "1".to_owned(),
    ])
    .expect("--progress parses");
    assert_eq!(cli.progress_every, Some(500));
    assert_eq!(cli.command, "npa-bounds-scan --progress 500 --limit 1");

    assert!(
        parse_bounds_args(vec!["--progress".to_owned(), "0".to_owned()]).is_err(),
        "0 disables by omitting the flag, not by value"
    );
    assert!(parse_bounds_args(vec!["--progress".to_owned(), "x".to_owned()]).is_err());
    assert!(parse_bounds_args(vec!["--progress".to_owned()]).is_err());
    assert_eq!(
        parse_bounds_args(Vec::new())
            .expect("default argv parses")
            .progress_every,
        None
    );
}

/// T01: progress heartbeats are count-only (`scanned=<n>` — digits only,
/// never paths or payload), and the terminal stderr counts line is unchanged.
#[test]
fn t01_progress_heartbeats_are_count_only() {
    let root = temp_root("t01-progress");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    write_xml(&root, "exports/npa/b.xml", &["01.02.2003 65-ФЗ"]);
    write_xml(&root, "exports/npa/c.xml", &["ст. 15.1"]);

    let mut cli = fixed_cli();
    cli.root = Some(root.to_string_lossy().into_owned());
    cli.progress_every = Some(2);
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert_eq!(run.progress_lines, vec!["scanned=2".to_owned()]);
    for line in &run.progress_lines {
        let count = line.strip_prefix("scanned=").expect("count-only prefix");
        count
            .parse::<u64>()
            .expect("digits only — no paths or payload in heartbeats");
    }
    assert_eq!(run.partial_flushes, 0, "no --out, no partial rewrites");
    assert!(run.stderr.contains("files_attempted=3"));
    let jsonl = run.jsonl.expect("stdout run returns the aggregate");
    validate_bounds_jsonl(&jsonl).expect("closed schema");
    assert!(jsonl.contains("\"run_status\":\"complete\""));

    fs::remove_dir_all(&root).ok();
}

/// T01: with `--out`, every heartbeat interval atomically rewrites the
/// aggregate as an explicit incomplete diagnostic; the terminal write
/// replaces it with the complete manifest and leaves no temp residue.
#[test]
fn t01_progress_with_out_flushes_periodically_and_atomically() {
    let root = temp_root("t01-flush");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    write_xml(&root, "exports/npa/b.xml", &["01.02.2003 65-ФЗ"]);
    write_xml(&root, "exports/npa/c.xml", &["ст. 15.1"]);
    write_xml(&root, "exports/npa/d.xml", &["ст. 15.1"]);
    let out = root.join("bounds-flush.jsonl");

    let mut cli = fixed_cli();
    cli.root = Some(root.to_string_lossy().into_owned());
    cli.out = Some(out.to_string_lossy().into_owned());
    cli.progress_every = Some(1);
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    assert_eq!(
        run.partial_flushes, 4,
        "one atomic partial rewrite per heartbeat interval"
    );
    let written = fs::read_to_string(&out).expect("final out");
    validate_bounds_jsonl(&written).expect("final out stays closed");
    assert!(written.contains("\"run_status\":\"complete\""));
    assert!(written.contains("\"observed_file_count\":4"));
    assert!(
        !root.join("bounds-flush.jsonl.tmp").exists(),
        "atomic rename leaves no temp residue"
    );

    fs::remove_dir_all(&root).ok();
}

/// T01: the interruption seam renders the current aggregate with the
/// explicit `run_status:"incomplete"` marker and no fabricated ended_at; a
/// later complete run replaces it atomically (kill → incomplete evidence).
#[test]
fn t01_partial_flush_marks_incomplete_diagnostic() {
    let root = temp_root("t01-partial");
    write_xml(&root, "exports/npa/a.xml", &["ст. 15.1"]);
    write_xml(&root, "exports/npa/b.xml", &["01.02.2003 65-ФЗ"]);
    let out = root.join("bounds-partial.jsonl");

    // Kill simulation: observe exactly one of two files, then flush the
    // partial diagnostic through the T01 seam.
    let mut acc = BoundsAcc::new(
        &root,
        BoundsRunMeta::new(root.to_string_lossy().into_owned()),
    );
    walk_and_observe(&root, Some(1), &mut acc).expect("walk must succeed");
    write_partial_out(&out, &acc).expect("partial flush writes");

    let partial = fs::read_to_string(&out).expect("interrupted run left a diagnostic");
    validate_bounds_jsonl(&partial).expect("the incomplete diagnostic stays closed");
    assert!(partial.contains("\"run_status\":\"incomplete\""));
    assert!(partial.contains("\"observed_file_count\":1"));
    assert!(
        partial.contains("\"ended_at\":null"),
        "no fake completion clock on an interrupted run"
    );
    assert!(
        !root.join("bounds-partial.jsonl.tmp").exists(),
        "no temp residue"
    );

    // The rerun completes and replaces the diagnostic with the manifest.
    let mut cli = fixed_cli();
    cli.root = Some(root.to_string_lossy().into_owned());
    cli.out = Some(out.to_string_lossy().into_owned());
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    let final_out = fs::read_to_string(&out).expect("final out");
    assert!(final_out.contains("\"run_status\":\"complete\""));
    assert!(final_out.contains("\"observed_file_count\":2"));

    fs::remove_dir_all(&root).ok();
}

/// T01: skip-mode is a completed zero-file run, so its manifest also
/// renders a real `ended_at` and `run_status:"complete"`.
#[test]
fn t01_skip_mode_reports_completion_clock() {
    let cli = BoundsCli {
        ended_at: None,
        ..fixed_cli()
    };
    let run = run_bounds_scan(&cli, Path::new(ABSENT));
    assert_eq!(run.exit_code, EXIT_OK);
    let jsonl = run.jsonl.expect("skip-mode renders the zeroed aggregate");
    validate_bounds_jsonl(&jsonl).expect("closed schema");
    assert!(jsonl.contains("\"run_status\":\"complete\""));
    assert!(!jsonl.contains("\"ended_at\":null"));
}
