//! Composition battery for `law-nexus-inspect reference-package build|check`
//! (M011, ADR-0031 D6).
//!
//! The product CLI must expose the proven `reference_layer` derivation over
//! the tracked measure-ed50 fixture with the honest exit contract: 0 ok /
//! 2 argv / 3 unreadable inputs / 6 byte drift (5 stays reserved and is not
//! emitted by the Rust side). Every case runs the real binary
//! (`CARGO_BIN_EXE_law-nexus-inspect`), so the manual argv parser, the
//! composition and the library exit codes are proven together.
//!
//! Non-claims: fixture-level proof only. No corpus-wide D5/D4 execution is
//! claimed or performed here, and the tracked fixture tree stays read-only —
//! every case runs against a scratch copy.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

const CORE_ARTIFACTS: [&str; 4] = [
    "m217-reference-timeline.json",
    "m217-reference-digests.jsonl",
    "m217-reference-named-graphs.json",
    "m217-reference-amend-provenance.json",
];
const MEASUREMENT_ARTIFACTS: [&str; 2] = [
    "m217-reference-references.json",
    "m217-reference-pageindex.json",
];
const ARTIFACTS: [&str; 6] = [
    "m217-reference-timeline.json",
    "m217-reference-digests.jsonl",
    "m217-reference-named-graphs.json",
    "m217-reference-amend-provenance.json",
    "m217-reference-references.json",
    "m217-reference-pageindex.json",
];
const MEASURE_EDITION_FILE: &str = "edition-0050_rev-2017-01-01_from-unknown_deadbeef.xml";

const EXIT_OK: i32 = 0;
const EXIT_ARGV: i32 = 2;
const EXIT_INPUT: i32 = 3;
const EXIT_DRIFT: i32 = 6;

fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_law-nexus-inspect")
}

/// A tracked reference-layer fixture, shared with the Rust and Python
/// reference batteries (`tests/fixtures/reference-layer/`).
fn fixture(name: &str) -> PathBuf {
    [
        env!("CARGO_MANIFEST_DIR"),
        "..",
        "ln-consultant-parser",
        "tests",
        "fixtures",
        "reference-layer",
        name,
    ]
    .iter()
    .collect::<PathBuf>()
}

/// Hermetic scratch root named after the test, recreated fresh per run.
fn scratch(test: &str) -> PathBuf {
    let tmp = std::env::temp_dir().join(format!("ln-refpkg-{test}"));
    let _ = fs::remove_dir_all(&tmp);
    fs::create_dir_all(&tmp).expect("scratch root");
    tmp
}

/// Copy a tracked fixture corpus into the scratch root under its own name:
/// the catalog rows filter on the act directory name, and a scratch copy
/// keeps the tracked tree read-only even under a buggy build.
fn copy_corpus(source: &Path, target: &Path) {
    fs::create_dir_all(target).expect("corpus dir");
    for entry in fs::read_dir(source).expect("fixture dir") {
        let entry = entry.expect("fixture entry");
        let path = entry.path();
        if path.is_dir() {
            copy_corpus(&path, &target.join(entry.file_name()));
        } else {
            fs::copy(&path, target.join(entry.file_name())).expect("copy fixture file");
        }
    }
}

/// The measure-ed50 catalog, built by the repository's own Python recipe
/// (`scripts/test_m217_reference_parity.py`: `build_catalog` over
/// `MEASURE_CATALOG_ROWS`) through the pinned `uv run --frozen` interpreter.
/// Std-only on the Rust side — this crate takes no sqlite dependency — and
/// the rows stay single-sourced in the recipe: the two enacting acts the
/// fixture's requisites name. The 2-ФЗ mention resolves by number only and
/// the 999-ФЗ mention stays unresolved, so all three resolution tiers stay
/// exercised exactly as in the differential battery.
fn measure_catalog(scratch: &Path) -> PathBuf {
    const RECIPE: &str = "\
import sys
sys.path.insert(0, 'scripts')
from test_m217_reference_parity import MEASURE_CATALOG_ROWS, build_catalog
from pathlib import Path
build_catalog(Path(sys.argv[1]), list(MEASURE_CATALOG_ROWS))
";
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .canonicalize()
        .expect("repo root");
    let path = scratch.join("catalog.sqlite");
    let output = Command::new("uv")
        .args(["run", "--frozen", "python", "-c", RECIPE])
        .arg(&path)
        .current_dir(&repo)
        .output()
        .expect("spawn uv for the fixture recipe");
    assert!(
        output.status.success(),
        "recipe build_catalog failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    path
}

fn run(args: &[String]) -> (i32, String, String) {
    let out = Command::new(binary())
        .args(args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn law-nexus-inspect");
    (
        out.status.code().expect("normal exit carries a code"),
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
    )
}

fn build_args(corpus: &Path, catalog: &Path, out_dir: &Path) -> Vec<String> {
    vec![
        "reference-package".into(),
        "build".into(),
        "--corpus-dir".into(),
        corpus.to_string_lossy().into_owned(),
        "--catalog".into(),
        catalog.to_string_lossy().into_owned(),
        "--out-dir".into(),
        out_dir.to_string_lossy().into_owned(),
    ]
}

fn check_args(corpus: &Path, catalog: &Path, out_dir: &Path) -> Vec<String> {
    let mut args = build_args(corpus, catalog, out_dir);
    args[1] = "check".into();
    args
}

fn artifact_bytes(dir: &Path, names: &[&str]) -> Vec<(String, Vec<u8>)> {
    names
        .iter()
        .map(|name| {
            (
                (*name).to_owned(),
                fs::read(dir.join(name)).unwrap_or_else(|e| panic!("read {name}: {e}")),
            )
        })
        .collect()
}

/// Corpus files plus catalog bytes, sorted — the input-safety snapshot
/// compared before and after builds (INTENT N2/SC1).
fn input_snapshot(corpus: &Path, catalog: &Path) -> Vec<(String, Vec<u8>)> {
    let mut files: Vec<(String, Vec<u8>)> = fs::read_dir(corpus)
        .expect("corpus read")
        .map(|entry| entry.expect("corpus entry"))
        .map(|entry| {
            (
                entry.file_name().to_string_lossy().into_owned(),
                fs::read(entry.path()).expect("corpus file"),
            )
        })
        .collect();
    files.sort_by(|a, b| a.0.cmp(&b.0));
    files.push(("catalog.sqlite".into(), fs::read(catalog).expect("catalog")));
    files
}

fn dir_entry_names(dir: &Path) -> Vec<String> {
    let mut names: Vec<String> = fs::read_dir(dir)
        .expect("out dir")
        .map(|entry| {
            entry
                .expect("out entry")
                .file_name()
                .to_string_lossy()
                .into_owned()
        })
        .collect();
    names.sort();
    names
}

/// (SC1, E1, N2) A measure-ed50 build writes the full six-artifact set, is
/// byte-identical on a rebuild into the same directory, touches nothing
/// outside `--out-dir`, and leaves the corpus and catalog byte-unchanged.
#[test]
fn build_measure_ed50_package_is_complete_idempotent_and_input_safe() {
    let tmp = scratch("build-idempotent");
    let corpus = tmp.join("measure-ed50");
    copy_corpus(&fixture("measure-ed50"), &corpus);
    let catalog = measure_catalog(&tmp);
    let out = tmp.join("package");
    fs::create_dir_all(&out).expect("out dir");
    let unrelated = out.join("operator-notes.txt");
    fs::write(&unrelated, "kept across builds\n").expect("unrelated file");

    let before = input_snapshot(&corpus, &catalog);
    let (code, stdout, stderr) = run(&build_args(&corpus, &catalog, &out));
    assert_eq!(code, EXIT_OK, "build must exit 0; stderr: {stderr}");
    assert!(
        !stdout.contains("measurement not applicable"),
        "measure-ed50 carries edition 50, measurements must be written: {stdout}"
    );
    for name in ARTIFACTS {
        let bytes = fs::read(out.join(name)).unwrap_or_else(|e| panic!("read {name}: {e}"));
        assert!(
            !bytes.is_empty(),
            "{name} must be a real artifact, not zero bytes"
        );
    }
    let mut expected = ARTIFACTS
        .iter()
        .map(|n| (*n).to_owned())
        .collect::<Vec<_>>();
    expected.push("operator-notes.txt".into());
    expected.sort();
    assert_eq!(
        dir_entry_names(&out),
        expected,
        "build must write exactly its artifact set and leave unrelated files alone"
    );
    assert_eq!(
        input_snapshot(&corpus, &catalog),
        before,
        "build must not mutate the corpus or the catalog"
    );

    let first = artifact_bytes(&out, &ARTIFACTS);
    let (code, _stdout, stderr) = run(&build_args(&corpus, &catalog, &out));
    assert_eq!(code, EXIT_OK, "rebuild must exit 0; stderr: {stderr}");
    assert_eq!(
        artifact_bytes(&out, &ARTIFACTS),
        first,
        "rebuild into the same out-dir must be byte-identical"
    );
    assert_eq!(
        input_snapshot(&corpus, &catalog),
        before,
        "rebuild must still not mutate the corpus or the catalog"
    );
}

/// (SC2, N1) `check` passes the unmodified package, and a package where every
/// artifact byte is flipped exits 6 naming every drift row — no row is
/// swallowed, no warn-and-pass path exists.
#[test]
fn check_unmodified_package_passes_and_flipped_bytes_all_exit_6() {
    let tmp = scratch("check-drift");
    let corpus = tmp.join("measure-ed50");
    copy_corpus(&fixture("measure-ed50"), &corpus);
    let catalog = measure_catalog(&tmp);
    let out = tmp.join("package");
    let (code, _stdout, stderr) = run(&build_args(&corpus, &catalog, &out));
    assert_eq!(code, EXIT_OK, "build must exit 0; stderr: {stderr}");

    let (code, stdout, stderr) = run(&check_args(&corpus, &catalog, &out));
    assert_eq!(
        code, EXIT_OK,
        "unmodified package must check ok; stderr: {stderr}"
    );
    assert!(
        stdout.contains("check=ok"),
        "expected the ok marker: {stdout}"
    );

    let built = artifact_bytes(&out, &ARTIFACTS);
    for (name, bytes) in &built {
        let mut drifted = bytes.clone();
        drifted[0] = if drifted[0] == b'{' { b'X' } else { b'{' };
        fs::write(out.join(name), drifted).expect("write drift");
    }
    let (code, _stdout, stderr) = run(&check_args(&corpus, &catalog, &out));
    assert_eq!(
        code, EXIT_DRIFT,
        "any artifact byte drift must exit 6; stderr: {stderr}"
    );
    for (name, _) in &built {
        assert!(
            stderr.contains(name),
            "every drift row must be named on stderr; missing {name} in: {stderr}"
        );
    }

    for (name, bytes) in &built {
        fs::write(out.join(name), bytes).expect("restore artifact");
    }
    let (code, _stdout, stderr) = run(&check_args(&corpus, &catalog, &out));
    assert_eq!(
        code, EXIT_OK,
        "restored package must check ok; stderr: {stderr}"
    );
}

/// (E2) A zero-byte artifact exists but differs from the derivation: that is
/// drift (6), never a missing-input exit 3.
#[test]
fn zero_byte_artifact_is_drift_exit_6_not_missing_input_exit_3() {
    let tmp = scratch("zero-byte");
    let corpus = tmp.join("measure-ed50");
    copy_corpus(&fixture("measure-ed50"), &corpus);
    let catalog = measure_catalog(&tmp);
    let out = tmp.join("package");
    let (code, _stdout, stderr) = run(&build_args(&corpus, &catalog, &out));
    assert_eq!(code, EXIT_OK, "build must exit 0; stderr: {stderr}");

    let pageindex = out.join("m217-reference-pageindex.json");
    fs::write(&pageindex, b"").expect("truncate artifact to zero bytes");
    let (code, _stdout, stderr) = run(&check_args(&corpus, &catalog, &out));
    assert_eq!(
        code, EXIT_DRIFT,
        "a zero-byte artifact is drift (6), not exit 3; stderr: {stderr}"
    );
}

/// (SC2) A deleted artifact is also drift, never a silent pass.
#[test]
fn deleted_artifact_is_drift_exit_6() {
    let tmp = scratch("deleted-artifact");
    let corpus = tmp.join("measure-ed50");
    copy_corpus(&fixture("measure-ed50"), &corpus);
    let catalog = measure_catalog(&tmp);
    let out = tmp.join("package");
    let (code, _stdout, stderr) = run(&build_args(&corpus, &catalog, &out));
    assert_eq!(code, EXIT_OK, "build must exit 0; stderr: {stderr}");
    fs::remove_file(out.join("m217-reference-timeline.json")).expect("delete artifact");
    let (code, _stdout, stderr) = run(&check_args(&corpus, &catalog, &out));
    assert_eq!(
        code, EXIT_DRIFT,
        "a deleted artifact must exit 6; stderr: {stderr}"
    );
}

/// (SC3) Two builds into different temporary directories are byte-identical.
#[test]
fn builds_into_different_dirs_are_byte_identical() {
    let tmp = scratch("determinism");
    let corpus = tmp.join("measure-ed50");
    copy_corpus(&fixture("measure-ed50"), &corpus);
    let catalog = measure_catalog(&tmp);
    let out_a = tmp.join("package-a");
    let out_b = tmp.join("package-b");
    let (code, _stdout, stderr) = run(&build_args(&corpus, &catalog, &out_a));
    assert_eq!(code, EXIT_OK, "build a must exit 0; stderr: {stderr}");
    let (code, _stdout, stderr) = run(&build_args(&corpus, &catalog, &out_b));
    assert_eq!(code, EXIT_OK, "build b must exit 0; stderr: {stderr}");
    assert_eq!(
        artifact_bytes(&out_a, &ARTIFACTS),
        artifact_bytes(&out_b, &ARTIFACTS),
        "every re-derivation path must produce byte-identical artifacts"
    );
}

/// (SC4) A missing catalog, an absent corpus dir and an empty corpus
/// directory (zero XML documents) each exit 3 — on build and on check.
#[test]
fn unreadable_inputs_exit_3() {
    let tmp = scratch("unreadable");
    let catalog = measure_catalog(&tmp);

    let absent = tmp.join("no-such-corpus");
    let (code, _stdout, stderr) = run(&build_args(&absent, &catalog, &tmp.join("out")));
    assert_eq!(
        code, EXIT_INPUT,
        "absent corpus dir must exit 3; stderr: {stderr}"
    );
    let (code, _stdout, stderr) = run(&check_args(&absent, &catalog, &tmp.join("out")));
    assert_eq!(
        code, EXIT_INPUT,
        "absent corpus dir must exit 3 on check; stderr: {stderr}"
    );

    let corpus = tmp.join("measure-ed50");
    copy_corpus(&fixture("measure-ed50"), &corpus);
    let missing_catalog = tmp.join("absent.sqlite");
    let (code, _stdout, stderr) = run(&build_args(&corpus, &missing_catalog, &tmp.join("out")));
    assert_eq!(
        code, EXIT_INPUT,
        "missing catalog must exit 3; stderr: {stderr}"
    );

    let empty = tmp.join("empty-act");
    fs::create_dir_all(&empty).expect("empty corpus dir");
    let (code, _stdout, stderr) = run(&build_args(&empty, &catalog, &tmp.join("out")));
    assert_eq!(
        code, EXIT_INPUT,
        "an empty corpus directory is an invalid input (3), stderr: {stderr}"
    );
}

/// (SC5) Unknown flags, missing required flags, a flag value that is not
/// there, an unknown mode and no mode at all are argv errors (2).
#[test]
fn invalid_arguments_exit_2() {
    let cli = |args: &[&str]| {
        let owned: Vec<String> = args.iter().map(|a| (*a).to_owned()).collect();
        run(&owned)
    };
    let cases: [&[&str]; 5] = [
        &[
            "reference-package",
            "build",
            "--corpus-dir",
            "x",
            "--catalog",
            "y",
            "--out-dir",
            "z",
            "--bogus",
        ],
        &["reference-package", "build", "--corpus-dir", "x"],
        &["reference-package", "check", "--corpus-dir"],
        &[
            "reference-package",
            "frobnicate",
            "--corpus-dir",
            "x",
            "--catalog",
            "y",
            "--out-dir",
            "z",
        ],
        &["reference-package"],
    ];
    for args in cases {
        let (code, _stdout, stderr) = cli(args);
        assert_eq!(
            code, EXIT_ARGV,
            "args {args:?} must exit 2; stderr: {stderr}"
        );
        assert!(!stderr.is_empty(), "argv errors must say why: {stderr}");
    }
}

/// (SC6) A corpus without edition 50 builds and checks with the measurements
/// explicitly marked not applicable and never written; a corpus carrying
/// edition 50 among others has its measurements compared normally (E4).
#[test]
fn measurement_scope_follows_edition_50_presence() {
    let tmp = scratch("measurement-scope");
    let catalog = measure_catalog(&tmp);

    // No edition 50: the `basic` fixture corpus.
    let corpus = tmp.join("basic");
    copy_corpus(&fixture("basic"), &corpus);
    let out = tmp.join("package-basic");
    let (code, stdout, stderr) = run(&build_args(&corpus, &catalog, &out));
    assert_eq!(code, EXIT_OK, "no-ed50 build must exit 0; stderr: {stderr}");
    assert!(
        stdout.contains("measurement not applicable: corpus has no edition 50"),
        "build must mark the measurements not applicable: {stdout}"
    );
    for name in CORE_ARTIFACTS {
        assert!(out.join(name).is_file(), "core artifact {name} must exist");
    }
    for name in MEASUREMENT_ARTIFACTS {
        assert!(
            !out.join(name).exists(),
            "not-applicable measurement {name} must not be written"
        );
    }
    let (code, stdout, stderr) = run(&check_args(&corpus, &catalog, &out));
    assert_eq!(code, EXIT_OK, "no-ed50 check must exit 0; stderr: {stderr}");
    assert!(
        stdout.contains("measurement not applicable"),
        "check must keep the explicit not-applicable marking: {stdout}"
    );
    assert!(
        stdout.contains("check=ok"),
        "no-ed50 check must pass: {stdout}"
    );

    // Edition 50 among others: `basic` plus the ed-50 edition file.
    let mixed = tmp.join("mixed-ed50");
    copy_corpus(&fixture("basic"), &mixed);
    fs::copy(
        fixture("measure-ed50").join(MEASURE_EDITION_FILE),
        mixed.join(MEASURE_EDITION_FILE),
    )
    .expect("copy ed50 edition into mixed corpus");
    let mixed_out = tmp.join("package-mixed");
    let (code, stdout, stderr) = run(&build_args(&mixed, &catalog, &mixed_out));
    assert_eq!(code, EXIT_OK, "mixed build must exit 0; stderr: {stderr}");
    assert!(
        !stdout.contains("measurement not applicable"),
        "a corpus carrying edition 50 must compare its measurements: {stdout}"
    );
    for name in MEASUREMENT_ARTIFACTS {
        assert!(
            mixed_out.join(name).is_file(),
            "measurement {name} must exist"
        );
    }
    let (code, _stdout, stderr) = run(&check_args(&mixed, &catalog, &mixed_out));
    assert_eq!(code, EXIT_OK, "mixed check must exit 0; stderr: {stderr}");
}
