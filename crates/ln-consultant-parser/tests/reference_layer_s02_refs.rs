//! D4 reference measurement pin for 44-FZ edition 50 (ADR-0031 D4/D8).
//!
//! The Python reference commits the ed-50 D4 measurement
//! (`prd/migration/rust-evidence/m217-reference-references.json`); this suite
//! pins that the Rust port reproduces it byte for byte and exposes the same
//! counts through the public surface (`references_document`). Three negative
//! surfaces are pinned too: the applicability gate keeps fixture corpora at
//! exit 0 (never exit 3), a corpus without edition 50 is not applicable, and a
//! tampered measurement artifact fails closed with `EXIT_DRIFT` (6).
//!
//! The corpus is gitignored, so the corpus-dependent tests are gated: without
//! `consru_export/` they print `SKIP:` and return (exit 0). Set
//! `M225_S01_REPO_ROOT=<dir>` to point at another checkout; point it at a
//! nonexistent directory to force the skip path locally (the same knob the S01
//! suites use).

use ln_consultant_parser::reference_layer::{
    DeriveOptions, EXIT_DRIFT, EXIT_INPUT, EXIT_OK, MEASUREMENT_EDITION, artifact_paths,
    measurement_applicable, references_document, run_check, try_derive,
};
use std::path::{Path, PathBuf};

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

fn committed(name: &str) -> String {
    let path = committed_dir().join(name);
    std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("committed artifact {} unreadable: {e}", path.display()))
}

fn fixtures() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/reference-layer")
}

/// Corpus-gated hermeticity guard. Must run before any corpus read.
fn skip_without_corpus() -> bool {
    if corpus_dir().is_dir() && catalog().is_file() {
        return false;
    }
    eprintln!(
        "SKIP: consru_export 44-FZ corpus not available (set M225_S01_REPO_ROOT to a full checkout, or to a nonexistent dir to force this skip)"
    );
    true
}

fn opts(corpus: PathBuf, catalog: PathBuf) -> DeriveOptions {
    DeriveOptions {
        limit_editions: None,
        corpus_dir: corpus,
        catalog,
    }
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

#[test]
fn references_document_is_byte_identical_to_the_python_reference() {
    if skip_without_corpus() {
        return;
    }
    let derived = references_document(&corpus_dir(), &catalog(), MEASUREMENT_EDITION)
        .expect("ed-50 references measurement must derive");
    let oracle = committed("m217-reference-references.json");
    assert_eq!(
        derived, oracle,
        "the D4 measurement must be byte-identical to the committed Python reference"
    );

    // The public counts are pinned on the derived document (not on the file).
    let doc: serde_json::Value = serde_json::from_str(&derived).expect("derived document parses");
    assert_eq!(doc["schema_version"], "m217-reference-references/v1");
    assert_eq!(doc["scope"]["edition_no"], MEASUREMENT_EDITION);
    assert_eq!(doc["counts"]["candidates"], 379);
    assert_eq!(doc["counts"]["internal"], 346);
    assert_eq!(doc["counts"]["external_sentence"], 33);
    assert_eq!(doc["counts"]["requisites"], 611);
    assert_eq!(doc["counts"]["requisites_exact_date"], 609);
    assert_eq!(doc["counts"]["requisites_unique"], 50);
    assert_eq!(
        doc["counts"]["deep_links"], 0,
        "S02 has no target-act corpus"
    );
    assert!(
        doc["counts"]["deep_link_candidates"].as_u64().unwrap_or(0) >= 1,
        "deep-link mechanics must be proven by a non-empty candidate set"
    );
    // The 44-ФЗ requisites resolve to the corpus in the same order the
    // committed artifact publishes them.
    let counts = &doc["counts"];
    eprintln!(
        "rust D4 ed-50: candidates={} internal={} external_sentence={} requisites={} exact_date={} unique={} deep_link_candidates={} deep_links={}",
        counts["candidates"],
        counts["internal"],
        counts["external_sentence"],
        counts["requisites"],
        counts["requisites_exact_date"],
        counts["requisites_unique"],
        counts["deep_link_candidates"],
        counts["deep_links"],
    );
}

#[test]
fn measurement_is_not_applicable_without_edition_50() {
    // Hermetic: no corpus needed. Fixture corpora carry editions 1 and 2 only.
    assert!(
        !measurement_applicable(&fixtures().join("basic")),
        "a fixture corpus without edition 50 is not applicable"
    );
    assert!(!measurement_applicable(&fixtures().join("other-act")));
    assert!(!measurement_applicable(Path::new("/nonexistent-lns02")));
}

#[test]
fn fixture_corpus_stays_exit_ok_under_the_measurement_gate() {
    // Hermetic: the applicability gate must not turn a fixture corpus into an
    // exit-3 or a drift failure (D782).
    let tmp = std::env::temp_dir().join("ln-ref-s02-gate");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = empty_catalog(&tmp);
    let corpus = fixtures().join("basic");
    assert!(!measurement_applicable(&corpus));
    let out = tmp.join("out");
    std::fs::create_dir_all(&out).expect("out");

    let reference = try_derive(&opts(corpus.clone(), catalog.clone())).expect("basic derives");
    for (path, body) in artifact_paths(&out).iter().zip([
        &reference.timeline,
        &reference.digests,
        &reference.named_graphs,
        &reference.amend,
    ]) {
        std::fs::write(path, body).expect("seed artifact");
    }
    assert_eq!(
        run_check(&corpus, &catalog, &out),
        EXIT_OK,
        "a corpus without edition 50 must stay exit 0"
    );
    let _ = std::fs::remove_dir_all(&tmp);
}

/// Write a minimal WordML 2003 document (namespace-declared) holding `paras`.
fn write_wordml(path: &Path, paras: &[&str]) {
    let mut body = String::from(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?><w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\">",
    );
    for p in paras {
        body.push_str(&format!("<w:p><w:r><w:t>{p}</w:t></w:r></w:p>"));
    }
    body.push_str("</w:wordDocument>");
    std::fs::write(path, body).expect("write wordml");
}

#[test]
fn references_document_fails_closed_on_unreadable_measurement_inputs() {
    // Hermetic: hand-built ed-50 corpora, no real corpus needed. Each path must
    // bubble a `RefError` (ADR-0031 D6 exit 3), never a panic and never exit 0.
    let tmp = std::env::temp_dir().join("ln-ref-s02-failclosed");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = empty_catalog(&tmp);
    const ED50: &str = "edition-0050_rev-unknown_from-unknown_aaaaaaaa.xml";

    // (a) an ed-50 file without the WordML 2003 namespace -> exit 3.
    let notwordml = tmp.join("notwordml");
    std::fs::create_dir_all(&notwordml).expect("dir");
    std::fs::write(notwordml.join(ED50), "<x/>").expect("write");
    assert!(measurement_applicable(&notwordml));
    let err = references_document(&notwordml, &catalog, MEASUREMENT_EDITION)
        .expect_err("a non-WordML ed-50 file must not derive");
    assert_eq!(err.exit_code(), EXIT_INPUT);

    // (b) a valid ed-50 WordML corpus whose requisite resolution needs an
    // unreadable catalog -> exit 3 (the requisite must sit in the article body,
    // not on the dropped heading line).
    let broken = tmp.join("brokencat");
    std::fs::create_dir_all(&broken).expect("dir");
    write_wordml(
        &broken.join(ED50),
        &[
            "Статья 1. Первая.",
            "Основание — Федеральный закон от 05.04.2013 N 44-ФЗ.",
        ],
    );
    let garbage = tmp.join("garbage.sqlite");
    std::fs::write(&garbage, b"not a sqlite database".repeat(20)).expect("write");
    let err = references_document(&broken, &garbage, MEASUREMENT_EDITION)
        .expect_err("an unreadable catalog must not derive");
    assert_eq!(err.exit_code(), EXIT_INPUT);

    // (c) a corpus without edition 50 -> not applicable, and a direct call
    // fails closed rather than silently returning an empty document.
    let no50 = tmp.join("no50");
    std::fs::create_dir_all(&no50).expect("dir");
    std::fs::write(
        no50.join("edition-0049_rev-unknown_from-unknown_cccccccc.xml"),
        "<x/>",
    )
    .expect("write");
    assert!(!measurement_applicable(&no50));
    let err = references_document(&no50, &catalog, MEASUREMENT_EDITION)
        .expect_err("a corpus without edition 50 must not derive");
    assert_eq!(err.exit_code(), EXIT_INPUT);
    let _ = std::fs::remove_dir_all(&tmp);
}

#[test]
fn tampered_references_artifact_fails_closed_with_drift() {
    if skip_without_corpus() {
        return;
    }
    let tmp = std::env::temp_dir().join("ln-ref-s02-drift");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    // Seed the four full-corpus artifacts from the committed oracle, then
    // corrupt only the D4 measurement.
    for name in COMMITTED_ARTIFACTS {
        std::fs::write(tmp.join(name), committed(name)).expect("seed artifact");
    }
    std::fs::write(tmp.join("m217-reference-references.json"), "{}\n").expect("tamper");

    let code = run_check(&corpus_dir(), &catalog(), &tmp);
    let _ = std::fs::remove_dir_all(&tmp);
    assert_eq!(
        code, EXIT_DRIFT,
        "a tampered D4 measurement must fail closed with drift"
    );
}
