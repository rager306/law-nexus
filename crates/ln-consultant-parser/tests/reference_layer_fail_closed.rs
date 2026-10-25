//! Fail-closed contract battery for the ADR-0031 reference layer.
//!
//! ADR-0031 D6 fixes the CLI exit codes: `0` ok, `2` argv, `3` unreadable
//! inputs, `5` schema violation (Python reference only), `6` byte drift. A
//! panic has no exit code, so every unreadable input here must come back as
//! `EXIT_INPUT` — that is what the Python reference does and what this port
//! used to violate by `expect`-ing its way out of a bad corpus.
//!
//! The fixtures under `tests/fixtures/reference-layer/` are the same corpus the
//! Python-side differential battery (`scripts/test_m217_reference_parity.py`)
//! runs, so both implementations are pinned to one input set.

use ln_consultant_parser::reference_layer::{
    DeriveOptions, EXIT_DRIFT, EXIT_INPUT, EXIT_OK, RefError, run_check, try_derive,
};
use std::path::{Path, PathBuf};

fn fixtures() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/reference-layer")
}

/// Empty catalog: no act rows, so every day falls back to the filename or
/// `9999-12-31`. Enough for the contract cases.
fn empty_catalog(dir: &Path) -> PathBuf {
    build_catalog(dir.join("cat-empty.sqlite"), &[])
}

fn build_catalog(path: PathBuf, rows: &[(&str, &str, &str)]) -> PathBuf {
    let _ = std::fs::remove_file(&path);
    let con = rusqlite::Connection::open(&path).expect("create catalog");
    con.execute(
        "create table editions (relative_path text, document_date text, number text)",
        [],
    )
    .expect("schema");
    for (rel, day, number) in rows {
        con.execute(
            "insert into editions (relative_path, document_date, number) values (?1, ?2, ?3)",
            rusqlite::params![rel, day, number],
        )
        .expect("insert");
    }
    drop(con);
    path
}

fn opts(corpus: PathBuf, catalog: PathBuf) -> DeriveOptions {
    DeriveOptions {
        limit_editions: None,
        corpus_dir: corpus,
        catalog,
    }
}

/// Cases the reference layer cannot derive from. Every one must be exit 3.
const UNREADABLE_CASES: [&str; 8] = [
    "zero",      // 0-byte edition file
    "malformed", // XML that never closes
    "notwordml", // well-formed XML with no w:p at all
    "ns2006",    // WordML 2006 namespace, not the 2003 contract namespace
    "unclosed",  // <w:p> without </w:p>
    "badnum",    // edition file name without a numeric edition number
    "badentity", // undeclared &nbsp; entity (ElementTree refuses it)
    "dupnum",    // two editions claiming the same edition number
];

#[test]
fn unreadable_corpus_cases_fail_closed_with_exit_3() {
    let tmp = std::env::temp_dir().join("ln-ref-failclosed");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = empty_catalog(&tmp);
    let out = tmp.join("out");
    for case in UNREADABLE_CASES {
        let corpus = fixtures().join(case);
        assert!(corpus.is_dir(), "missing fixture {case}");
        let code = run_check(&corpus, &catalog, &out);
        assert_eq!(
            code, EXIT_INPUT,
            "{case} must fail closed with exit 3, got {code}"
        );
    }
}

#[test]
fn empty_corpus_dir_fails_closed_with_exit_3() {
    let tmp = std::env::temp_dir().join("ln-ref-empty");
    let _ = std::fs::remove_dir_all(&tmp);
    let corpus = tmp.join("empty-act");
    std::fs::create_dir_all(&corpus).expect("tmp");
    let catalog = empty_catalog(&tmp);
    assert_eq!(run_check(&corpus, &catalog, &tmp.join("out")), EXIT_INPUT);
}

#[test]
fn corrupt_catalog_fails_closed_with_exit_3() {
    let tmp = std::env::temp_dir().join("ln-ref-corrupt-cat");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = tmp.join("garbage.sqlite");
    std::fs::write(&catalog, b"not a sqlite database, just text".repeat(20)).expect("write");
    assert_eq!(
        run_check(&fixtures().join("basic"), &catalog, &tmp.join("out")),
        EXIT_INPUT
    );
}

#[test]
fn try_derive_reports_a_reason_instead_of_panicking() {
    let tmp = std::env::temp_dir().join("ln-ref-reason");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = empty_catalog(&tmp);
    let err: RefError = try_derive(&opts(fixtures().join("ns2006"), catalog.clone()))
        .err()
        .expect("ns2006 must not derive");
    assert_eq!(err.exit_code(), EXIT_INPUT);
    assert!(
        err.reason().contains("WordML 2003"),
        "reason should name the namespace constraint, got: {}",
        err.reason()
    );
    assert!(
        try_derive(&opts(fixtures().join("does-not-exist"), catalog)).is_err(),
        "a missing corpus dir must not panic"
    );
}

#[test]
fn derivable_fixture_compares_ok_then_drifts() {
    // basic is derivable: exit 0 against its own artifacts, 6 against an empty
    // directory. Both halves live in one test because each costs a derivation.
    let tmp = std::env::temp_dir().join("ln-ref-drift");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = empty_catalog(&tmp);
    let corpus = fixtures().join("basic");
    let out = tmp.join("out");
    std::fs::create_dir_all(&out).expect("out");
    assert_eq!(run_check(&corpus, &catalog, &out), EXIT_DRIFT);

    let reference = try_derive(&opts(corpus.clone(), catalog.clone())).expect("basic derives");
    for (path, body) in ln_consultant_parser::reference_layer::artifact_paths(&out)
        .iter()
        .zip([
            &reference.timeline,
            &reference.digests,
            &reference.named_graphs,
            &reference.amend,
        ])
    {
        std::fs::write(path, body).expect("seed artifact");
    }
    assert_eq!(run_check(&corpus, &catalog, &out), EXIT_OK);
}

#[test]
fn catalog_day_fallback_uses_the_actual_act_directory() {
    // The day filter used to be hardcoded to law_2013-04-05_44-fz, so any other
    // act silently got 9999-12-31. Proves the act dir comes from the corpus.
    let tmp = std::env::temp_dir().join("ln-ref-actday");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = build_catalog(
        tmp.join("cat.sqlite"),
        &[
            (
                "exports/npa/other-act/edition-0001_rev-unknown_from-unknown_aaaaaaaa.xml",
                "2019-03-03",
                "11-ФЗ",
            ),
            (
                "exports/npa/other-act/edition-0002_rev-unknown_from-unknown_bbbbbbbb.xml",
                "2022-09-09",
                "11-ФЗ",
            ),
            (
                "exports/npa/law_2013-04-05_44-fz/edition-0001_rev-initial_from-unknown_x.xml",
                "2013-04-05",
                "44-ФЗ",
            ),
        ],
    );
    let reference = try_derive(&opts(fixtures().join("other-act"), catalog)).expect("derives");
    let timeline: serde_json::Value = serde_json::from_str(&reference.timeline).expect("json");
    let days: Vec<String> = timeline["editions"]
        .as_array()
        .expect("editions")
        .iter()
        .map(|e| e["applied_day"].as_str().unwrap_or_default().to_string())
        .collect();
    assert_eq!(days, vec!["2019-03-03", "2022-09-09"]);
}

#[test]
fn bytes_per_part_renders_like_the_python_reference() {
    // `round(x, 2)` must render the way json.dumps renders it (698.0, not
    // 698.00). The 44-FZ value (522.57) carries two decimals, which hid the
    // difference on the pinned corpus; the extended fixtures expose it. The
    // expected tokens are the Python reference's own output for these fixtures.
    let tmp = std::env::temp_dir().join("ln-ref-round");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("tmp");
    let catalog = empty_catalog(&tmp);
    let expected = [
        ("basic", "307.25"),
        ("nonmonotonic", "698.0"),
        ("shrink", "318.0"),
        ("entities", "280.5"),
        ("decimal", "270.25"),
        ("amends", "465.5"),
        ("mixed", "403.5"),
        ("selfclose", "403.5"),
        ("table", "412.5"),
    ];
    for (case, token) in expected {
        let reference = try_derive(&opts(fixtures().join(case), catalog.clone()))
            .unwrap_or_else(|e| panic!("{case} must derive: {e}"));
        let needle = format!("\"bytes_per_part\": {token},");
        assert!(
            reference.timeline.contains(&needle),
            "{case}: expected {needle:?} in the timeline; it must render like the Python reference"
        );
        assert!(
            !reference.timeline.contains("NaN"),
            "{case}: NaN is not valid JSON and must never be emitted"
        );
    }
}
