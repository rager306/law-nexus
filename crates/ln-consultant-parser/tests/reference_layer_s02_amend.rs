//! Amendment-provenance pin for 44-FZ edition 50 (ADR-0031 D4/D8).
//!
//! The S02 demo ("ed-50 amend markers: 22 laws, act marker 188-ФЗ") had no
//! dedicated carrier before this slice: the Rust scanner `scan_edition` was
//! pinned on no edition at all, and the Python battery checked only the 22
//! unique pairs plus "some act exists". This suite pins what the *public* Rust
//! API can see on ed-50: 151 markers, 22 unique `(iso-date, number)` pairs, and
//! exactly one `act` marker whose law is `2013-07-02 188-ФЗ`.
//!
//! The marker's `tier` and `resolved_path` are not visible through the public
//! surface (`resolve_amend` stays private per ADR-0031 D8, and this task must
//! not widen `src/reference_layer.rs` for a test). Those two facts are pinned
//! against the committed artifact by the hermetic Python battery
//! (`scripts/test_m217_reference_s02_amend.py`) instead.
//!
//! The corpus is gitignored, so the suite is corpus-gated: without
//! `consru_export/` it prints `SKIP:` and exits 0. Set `M225_S01_REPO_ROOT=<dir>`
//! to point at another checkout; point it at a nonexistent directory to force
//! the skip path locally (the same knob the S01 suites use).

use ln_consultant_parser::reference_layer::scan_edition;
use std::collections::BTreeSet;
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

/// Edition number parsed from an `edition-<digits>_...` file name. Mirrors the
/// Python reference's `edition_number_of`; the Rust `edition_no_of` is private,
/// and this task must not widen the production module for a test.
fn edition_number_of(name: &str) -> Option<u32> {
    let rest = name.strip_prefix("edition-")?;
    let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
    if digits.is_empty() {
        return None;
    }
    digits.parse().ok()
}

/// Path of the single ed-50 edition file, discovered by scanning the corpus
/// directory (the cache-buster hash in the name is never hardcoded).
fn edition_50_path() -> PathBuf {
    let mut matches: Vec<PathBuf> = std::fs::read_dir(corpus_dir())
        .expect("corpus dir readable")
        .filter_map(|entry| entry.ok().map(|e| e.path()))
        .filter(|path| {
            path.file_name()
                .and_then(|n| n.to_str())
                .and_then(edition_number_of)
                == Some(50)
        })
        .collect();
    matches.sort();
    assert_eq!(
        matches.len(),
        1,
        "exactly one edition-50 file expected, found: {matches:?}"
    );
    matches.remove(0)
}

#[test]
fn edition_50_amend_markers_pin_22_laws_and_the_188_fz_act() {
    // Hermeticity gate: must run before touching the corpus.
    if !corpus_dir().is_dir() || !catalog().is_file() {
        eprintln!(
            "SKIP: consru_export 44-FZ corpus not available (set M225_S01_REPO_ROOT to a full checkout, or to a nonexistent dir to force this skip)"
        );
        return;
    }

    let scanned = scan_edition(&edition_50_path()).expect("ed-50 must scan");
    assert_eq!(scanned.edition_no, 50, "scanned file must be ed-50");

    assert_eq!(
        scanned.amend.len(),
        151,
        "ed-50 must carry 151 amend markers"
    );

    let mut unique: BTreeSet<(String, String)> = BTreeSet::new();
    for (_article, iso, number) in &scanned.amend {
        unique.insert((iso.clone(), number.clone()));
    }
    assert_eq!(unique.len(), 22, "ed-50 must cite exactly 22 amending laws");

    let acts: Vec<&(String, String, String)> = scanned
        .amend
        .iter()
        .filter(|(article, _iso, _number)| article.as_str() == "act")
        .collect();
    assert_eq!(acts.len(), 1, "exactly one act-level marker expected");
    let (article, iso, number) = acts[0];
    assert_eq!(article.as_str(), "act");
    assert_eq!(iso.as_str(), "2013-07-02");
    assert_eq!(number.as_str(), "188-ФЗ");

    eprintln!(
        "ed-50 amend (rust scan_edition): markers={}, unique_laws={}, act=({iso}, {number})",
        scanned.amend.len(),
        unique.len()
    );
}
