//! `reference_layer` CLI contract (ADR-0031 D6/D782, verification-matrix row
//! "Python-to-Rust parity slice": subprocess harness test).
//!
//! The library suites pin the derivation; this suite pins the binary surface a
//! caller actually runs: argv handling (exit 2), the not-applicable message on
//! a corpus without edition 50 (exit 0, no measurement artifacts written), and
//! — corpus-gated — the six-artifact write branch plus a fail-closed `--check`
//! (exit 6) after the ladder is tampered with.
//!
//! Exit codes (ADR-0031 D6): 0 ok, 2 argv, 3 unreadable inputs, 6 byte drift.
//! The corpus is gitignored, so corpus-dependent tests are gated: without
//! `consru_export/` they print `SKIP:` and return (exit 0). Set
//! `M225_S01_REPO_ROOT=<dir>` to point at another checkout.

use std::path::{Path, PathBuf};
use std::process::Command;

/// Repository root. `M225_S01_REPO_ROOT` wins when set (it may be a
/// nonexistent path, which is the documented way to exercise the skip path).
fn repo_root() -> PathBuf {
    if let Some(root) = std::env::var_os("M225_S01_REPO_ROOT") {
        return PathBuf::from(root);
    }
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .canonicalize()
        .expect("repo root")
}

fn corpus_dir() -> PathBuf {
    repo_root()
        .join("consru_export")
        .join("consru_export")
        .join("exports")
        .join("npa")
        .join("law_2013-04-05_44-fz")
}

fn catalog() -> PathBuf {
    repo_root()
        .join("consru_export")
        .join("consru_export")
        .join("catalog.sqlite")
}

fn committed_dir() -> PathBuf {
    repo_root()
        .join("prd")
        .join("migration")
        .join("rust-evidence")
}

fn fixtures() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/reference-layer")
}

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_reference_layer"))
}

fn skip_without_corpus() -> bool {
    if corpus_dir().is_dir() && catalog().is_file() {
        return false;
    }
    eprintln!(
        "SKIP: consru_export 44-FZ corpus not available (set M225_S01_REPO_ROOT to a full checkout, or to a nonexistent dir to force this skip)"
    );
    true
}

fn empty_catalog(dir: &Path) -> PathBuf {
    let path = dir.join("cat-empty.sqlite");
    let _ = std::fs::remove_file(&path);
    let con = rusqlite::Connection::open(&path).expect("create catalog");
    con.execute(
        "create table editions (relative_path text, document_date text, number text)",
        [],
    )
    .expect("schema");
    drop(con);
    path
}

const COMMITTED_ARTIFACTS: [&str; 4] = [
    "m217-reference-timeline.json",
    "m217-reference-digests.jsonl",
    "m217-reference-named-graphs.json",
    "m217-reference-amend-provenance.json",
];

const MEASUREMENT_ARTIFACTS: [&str; 2] = [
    "m217-reference-references.json",
    "m217-reference-pageindex.json",
];

#[test]
fn cli_rejects_unknown_argv_with_exit_2() {
    // Hermetic: exit 2 is the argv contract, and it must be a clean exit, not a
    // panic (a panic is not an exit code).
    let out = bin()
        .arg("--definitely-not-a-flag")
        .output()
        .expect("spawn reference_layer");
    assert_eq!(out.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        stderr.contains("unexpected argument: --definitely-not-a-flag"),
        "argv failure must name the offending argument, got: {stderr}"
    );
}

#[test]
fn cli_check_on_a_corpus_without_edition_50_stays_exit_0() {
    // Hermetic: a fixture corpus writes the four full-corpus artifacts and
    // declares the ed-50 measurements not applicable — never exit 3 and never
    // a drift failure (D782).
    let tmp = std::env::temp_dir().join("ln-ref-s02-pageindex-cli-gate");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = empty_catalog(&tmp);
    let out_dir = tmp.join("out");

    let write = bin()
        .args(["--corpus-dir"])
        .arg(fixtures().join("basic"))
        .args(["--catalog"])
        .arg(&catalog)
        .args(["--out-dir"])
        .arg(&out_dir)
        .output()
        .expect("spawn reference_layer");
    assert_eq!(
        write.status.code(),
        Some(0),
        "write mode must stay exit 0: {}",
        String::from_utf8_lossy(&write.stderr)
    );
    for name in COMMITTED_ARTIFACTS {
        assert!(
            out_dir.join(name).is_file(),
            "the four full-corpus artifacts must be written: {name}"
        );
    }
    for name in MEASUREMENT_ARTIFACTS {
        assert!(
            !out_dir.join(name).exists(),
            "a corpus without edition 50 must not write {name}"
        );
    }
    let stdout = String::from_utf8_lossy(&write.stdout).to_string();
    assert!(
        stdout.contains("measurement not applicable: corpus has no edition 50"),
        "the write branch must state applicability, got: {stdout}"
    );

    let check = bin()
        .args(["--check", "--corpus-dir"])
        .arg(fixtures().join("basic"))
        .args(["--catalog"])
        .arg(&catalog)
        .args(["--out-dir"])
        .arg(&out_dir)
        .output()
        .expect("spawn reference_layer");
    assert_eq!(check.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&check.stdout).to_string();
    assert!(
        stdout.contains("check=ok artifacts byte-identical"),
        "the check branch must report a byte-identical corpus, got: {stdout}"
    );
    assert!(
        stdout.contains("measurement not applicable: corpus has no edition 50"),
        "the check branch must state applicability, got: {stdout}"
    );
    let _ = std::fs::remove_dir_all(&tmp);
}

#[test]
fn cli_writes_six_byte_identical_artifacts_and_fails_closed_on_tamper() {
    if skip_without_corpus() {
        return;
    }
    let tmp = std::env::temp_dir().join("ln-ref-s02-pageindex-cli");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");

    let write = bin()
        .args(["--corpus-dir"])
        .arg(corpus_dir())
        .args(["--catalog"])
        .arg(catalog())
        .args(["--out-dir"])
        .arg(&tmp)
        .output()
        .expect("spawn reference_layer");
    assert_eq!(
        write.status.code(),
        Some(0),
        "write mode must stay exit 0: {}",
        String::from_utf8_lossy(&write.stderr)
    );
    // Both measurement documents are written next to the four full-corpus ones
    // and reproduce the committed Python reference byte for byte.
    for name in COMMITTED_ARTIFACTS
        .iter()
        .chain(MEASUREMENT_ARTIFACTS.iter())
    {
        let written = std::fs::read(tmp.join(name))
            .unwrap_or_else(|e| panic!("{name} not written by the CLI: {e}"));
        let oracle = std::fs::read(committed_dir().join(name)).expect("committed oracle");
        assert_eq!(
            written, oracle,
            "{name} written by the CLI must be byte-identical to the Python reference"
        );
    }

    // Tamper only the ladder: `--check` must fail closed with drift (6).
    std::fs::write(tmp.join("m217-reference-pageindex.json"), "{}\n").expect("tamper");
    let check = bin()
        .args(["--check", "--corpus-dir"])
        .arg(corpus_dir())
        .args(["--catalog"])
        .arg(catalog())
        .args(["--out-dir"])
        .arg(&tmp)
        .output()
        .expect("spawn reference_layer");
    assert_eq!(
        check.status.code(),
        Some(6),
        "a tampered ladder must exit 6, stderr: {}",
        String::from_utf8_lossy(&check.stderr)
    );
    let stderr = String::from_utf8_lossy(&check.stderr);
    assert!(
        stderr.contains("m217-reference-pageindex.json: byte drift"),
        "drift must name the ladder artifact, got: {stderr}"
    );
    let _ = std::fs::remove_dir_all(&tmp);
}
