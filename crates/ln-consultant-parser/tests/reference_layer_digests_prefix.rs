//! Bounded digest-matrix oracle for editions 1..=12 (ADR-0031 / D778).
//!
//! The full-corpus oracle in `reference_layer_parity.rs` derives all 118
//! editions (~90 s) and proves byte parity for four artifacts. This suite pins
//! the *truncated* derivation path (`DeriveOptions::limit_editions`): the
//! digest matrix of editions 1..=12 must be a byte prefix of the committed
//! Python-reference `m217-reference-digests.jsonl`.
//!
//! The corpus is gitignored, so the suite is corpus-gated: without
//! `consru_export/` it prints `SKIP:` and exits 0. Set
//! `M225_S01_REPO_ROOT=<dir>` to point at another checkout; point it at a
//! nonexistent directory to force the skip path locally.

use ln_consultant_parser::reference_layer::{DeriveOptions, try_derive};
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::time::Instant;

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

fn committed_digests() -> PathBuf {
    repo_root()
        .join("prd")
        .join("migration")
        .join("rust-evidence")
        .join("m217-reference-digests.jsonl")
}

#[test]
fn editions_1_to_12_digest_matrix_is_a_byte_prefix_of_the_python_reference() {
    // Hermeticity gate: must run before touching the corpus or the artifact.
    if !corpus_dir().is_dir() || !catalog().is_file() {
        eprintln!(
            "SKIP: consru_export 44-FZ corpus not available (set M225_S01_REPO_ROOT to a full checkout, or to a nonexistent dir to force this skip)"
        );
        return;
    }

    let committed = std::fs::read_to_string(committed_digests())
        .unwrap_or_else(|e| panic!("committed digests unreadable: {e}"));
    let lines: Vec<&str> = committed.lines().collect();

    // Derive the boundary from the committed artifact instead of hardcoding it:
    // header + every art_digest row whose edition_no is <= 12. Those rows are
    // the leading block of the file (the artifact is ordered by edition).
    let mut n = 0usize;
    for line in &lines {
        let record: Value = serde_json::from_str(line).expect("committed digest row parses");
        let keep = match record["record_kind"].as_str() {
            Some("header") => true,
            Some("art_digest") => record["edition_no"].as_u64().unwrap_or(u64::MAX) <= 12,
            other => panic!("unexpected record_kind in committed digests: {other:?}"),
        };
        if !keep {
            break;
        }
        n += 1;
    }
    assert_eq!(
        n, 1378,
        "editions 1..=12 must span exactly 1378 artifact lines"
    );
    let prefix = lines[..n].join("\n") + "\n";
    assert_eq!(
        prefix.len(),
        343859,
        "the 1..=12 prefix must stay at 343859 bytes"
    );

    let started = Instant::now();
    let reference = try_derive(&DeriveOptions {
        limit_editions: Some(12),
        corpus_dir: corpus_dir(),
        catalog: catalog(),
    })
    .expect("bounded derivation must succeed on an available corpus");
    let elapsed = started.elapsed();
    eprintln!(
        "editions 1..=12: lines={n}, bytes={}, elapsed={elapsed:?}",
        prefix.len()
    );

    // Byte identity, not line-by-line or normalized comparison.
    assert_eq!(
        reference.digests, prefix,
        "digest matrix of editions 1..=12 must be byte-identical to the Python-reference prefix"
    );

    // Boundary and header shape.
    assert_eq!(
        reference.digests.lines().count(),
        n,
        "derived digest matrix must have exactly the prefix line count"
    );
    let last: Value =
        serde_json::from_str(reference.digests.lines().last().expect("non-empty digests"))
            .expect("last derived digest row parses");
    assert_eq!(last["edition_no"], 12, "truncation must end at edition 12");
    assert_eq!(
        last["article"], "statya-114",
        "edition 12 must end at statya-114"
    );
    let next: Value = serde_json::from_str(lines[n]).expect("row after the prefix parses");
    assert_eq!(
        next["edition_no"], 13,
        "the first line after the prefix must belong to edition 13"
    );

    // Absence check: truncation must not leak edition 13 into the output.
    assert!(
        !reference.digests.contains("\"edition_no\":13"),
        "bounded derivation must not emit edition 13 rows"
    );

    // The header stays in the output, identical in shape to the artifact.
    assert!(reference.digests.contains("m217-norm/v1"));
    assert!(reference.digests.starts_with("{\"non_claims\""));
}
