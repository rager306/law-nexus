//! Full-corpus parity battery: the Rust reference-layer derivation must
//! byte-match the committed Python-reference artifacts (ADR-0031 / D778).
//!
//! The committed `prd/migration/rust-evidence/m217-reference-*` files are the
//! parity oracle produced by `scripts/m217_reference_jsonld.py --check`; the
//! Rust port is accepted only when it reproduces them byte for byte. The
//! negative test pins the fail-closed path: a tampered artifact must be
//! reported as drift (exit 6), never silently accepted.
//!
//! The 44-FZ corpus (`consru_export/`) is gitignored, while CI runs
//! `cargo test --workspace --offline` on a clean checkout. The suite is
//! therefore corpus-gated: when the corpus is absent every corpus-dependent
//! test prints `SKIP:` and returns (exit 0) instead of panicking inside
//! `derive` or asserting `EXIT_OK` against `EXIT_INPUT`. When the corpus is
//! present the run is the full, unweakened oracle — no `#[ignore]` and no
//! opt-in env var. Set `M225_S01_REPO_ROOT=<dir>` to point at another
//! checkout, or at a nonexistent directory to exercise the skip path locally
//! (the same knob is used by `reference_layer_digests_prefix.rs`).

use ln_consultant_parser::reference_layer::{
    DeriveOptions, EXIT_DRIFT, EXIT_OK, Reference, derive, run_check,
};
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

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

/// Pure, corpus-free predicate: does `root` hold the 44-FZ corpus and catalog?
fn corpus_available_at(root: &Path) -> bool {
    root.join("consru_export/consru_export/exports/npa/law_2013-04-05_44-fz")
        .is_dir()
        && root
            .join("consru_export/consru_export/catalog.sqlite")
            .is_file()
}

fn corpus_available() -> bool {
    corpus_available_at(&repo_root())
}

/// Corpus-gated hermeticity guard. Must run before any corpus or artifact read.
fn skip_without_corpus() -> bool {
    if corpus_available() {
        return false;
    }
    eprintln!(
        "SKIP: consru_export 44-FZ corpus not available (set M225_S01_REPO_ROOT to a full checkout, or to a nonexistent dir to force this skip)"
    );
    true
}

fn corpus_dir() -> PathBuf {
    repo_root()
        .join("consru_export")
        .join("consru_export")
        .join("exports")
        .join("npa")
        .join("law_2013-04-05_44-fz")
}

fn catalog_path() -> PathBuf {
    repo_root()
        .join("consru_export")
        .join("consru_export")
        .join("catalog.sqlite")
}

fn opts() -> DeriveOptions {
    DeriveOptions {
        limit_editions: None,
        corpus_dir: corpus_dir(),
        catalog: catalog_path(),
    }
}

fn committed(name: &str) -> String {
    let path = repo_root()
        .join("prd")
        .join("migration")
        .join("rust-evidence")
        .join(name);
    std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("committed artifact {} unreadable: {e}", path.display()))
}

/// The full 118-edition corpus takes ~90 s to derive in a debug build, so the
/// battery derives once and shares the result across every assertion.
fn reference() -> &'static Reference {
    static REF: OnceLock<Reference> = OnceLock::new();
    REF.get_or_init(|| derive(&opts()))
}

const ARTIFACTS: [&str; 4] = [
    "m217-reference-timeline.json",
    "m217-reference-digests.jsonl",
    "m217-reference-named-graphs.json",
    "m217-reference-amend-provenance.json",
];

#[test]
fn all_reference_artifacts_are_byte_identical_to_the_python_reference() {
    if skip_without_corpus() {
        return;
    }
    let r = reference();
    let bodies = [&r.timeline, &r.digests, &r.named_graphs, &r.amend];
    for (name, body) in ARTIFACTS.iter().zip(bodies) {
        assert_eq!(
            *body,
            committed(name),
            "{name} must be byte-identical to the committed Python reference"
        );
    }
}

#[test]
fn structural_breaks_match_documented_law_history() {
    if skip_without_corpus() {
        return;
    }
    let derived: serde_json::Value =
        serde_json::from_str(&reference().timeline).expect("derived timeline parses");
    let breaks: Vec<(u64, u64)> = derived["editions"]
        .as_array()
        .expect("editions array")
        .iter()
        .filter(|e| e["break_from_previous"].as_bool().unwrap_or(false))
        .map(|e| {
            (
                e["edition_no"].as_u64().unwrap_or(0),
                e["removed_from_previous"].as_u64().unwrap_or(0),
            )
        })
        .collect();
    assert_eq!(
        breaks,
        vec![(64, 3), (76, 5), (81, 40)],
        "article-count breaks must stay pinned to the documented 476-FZ purge band"
    );
}

#[test]
fn check_reports_ok_against_the_committed_artifacts() {
    if skip_without_corpus() {
        return;
    }
    let code = run_check(&corpus_dir(), &catalog_path(), &committed_dir());
    assert_eq!(code, EXIT_OK, "--check must accept the committed artifacts");
}

#[test]
fn check_fails_closed_on_a_tampered_artifact() {
    if skip_without_corpus() {
        return;
    }
    let tmp = std::env::temp_dir().join("ln-reference-layer-drift");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("temp dir");
    for name in ARTIFACTS {
        std::fs::write(tmp.join(name), committed(name)).expect("seed artifact");
    }
    let target = tmp.join(ARTIFACTS[0]);
    let mut body = std::fs::read_to_string(&target).expect("read seeded artifact");
    body.push(' ');
    std::fs::write(&target, body).expect("tamper artifact");

    let code = run_check(&corpus_dir(), &catalog_path(), &tmp);
    let _ = std::fs::remove_dir_all(&tmp);
    assert_eq!(
        code, EXIT_DRIFT,
        "a tampered artifact must fail closed with drift"
    );
}

/// Runs in both modes: absent roots are always unavailable; the positive
/// branch is only asserted when the real corpus is present.
#[test]
fn corpus_gate_reports_an_absent_root_as_unavailable() {
    assert!(
        !corpus_available_at(Path::new("/nonexistent-lns01")),
        "a nonexistent root must report the corpus as unavailable"
    );
    if corpus_available() {
        assert!(
            corpus_available_at(&repo_root()),
            "the resolved repo root must report the corpus as available"
        );
    } else {
        eprintln!("SKIP: positive corpus gate assertion needs the 44-FZ corpus");
    }
}

fn committed_dir() -> PathBuf {
    repo_root()
        .join("prd")
        .join("migration")
        .join("rust-evidence")
}
