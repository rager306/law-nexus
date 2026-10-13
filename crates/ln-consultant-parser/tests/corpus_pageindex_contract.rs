//! Contract suite for the M224/S03 corpus pageindex producer: accounting
//! identities, the exact-token join and its closed unresolved/collision
//! classes, whole-document resolution, path-like refusal, the 0-match negative
//! probe, ASCII/determinism, and the `--check` missing/drift exits.
//!
//! The suite runs entirely on synthetic envelope text plus an in-memory
//! [`PageIndexCatalogPort`]; it never reads the real corpus or catalog.

use std::fs;
use std::path::PathBuf;

use ln_consultant_parser::corpus_pageindex::{
    BuildMeta, EXIT_ARTIFACT_MISSING, EXIT_DRIFT, PageIndexBuildError, build_coverage,
    pageindex_exit_code_for, render_pageindex_coverage_json, render_pageindex_jsonl,
    verify_pageindex_artifacts,
};
use ln_consultant_parser::page_index_catalog::InMemoryPageIndexCatalog;

use ln_decode::consultant_uri_anchor::ConsultantUriAnchor;
use ln_decode::corpus_pageindex::{DocumentScope, PageIndexResolution, WHOLE_DOCUMENT_PARA};
use ln_decode::identity_envelope::IdentityEnvelope;

/// The real S02 catalog pin (sha256:9f3dc86a…) — the synthetic header must pin
/// the same digest the [`BuildMeta`] carries.
const CATALOG_SHA: &str = "9f3dc86a64d2fcd8678fd39831f1a670a5fdfe2a7162ae3d70d4b266f92c29b8";

fn catalog_meta() -> BuildMeta {
    BuildMeta {
        envelope_path: "prd/migration/rust-evidence/m224-s02-identity-envelope.jsonl".to_owned(),
        envelope_sha256: format!("sha256:{}", "c".repeat(64)),
        catalog_path: "consru_export/consru_export/catalog.sqlite".to_owned(),
        catalog_sha256: format!("sha256:{CATALOG_SHA}"),
    }
}

fn header(entries: u64, anchored: u64, unresolved: u64) -> String {
    let value = serde_json::json!({
        "schema": "m224-s02-identity-envelope/v1",
        "kind": "identity_envelope_header",
        "counts": {"entries": entries, "anchored": anchored, "unresolved": unresolved},
        "manifest": {
            "path": "prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl",
            "sha256": format!("sha256:{}", "a".repeat(64)),
            "inventory_digest": format!("sha256:{}", "b".repeat(64))
        },
        "catalog": {
            "path": "consru_export/consru_export/catalog.sqlite",
            "sha256": format!("sha256:{CATALOG_SHA}")
        },
        "r1000_status": "active/unclosed"
    });
    format!("{value}\n")
}

fn token(name: &str) -> String {
    format!("consultantplus://offline/ref={name}")
}

fn anchored_line(relative_path: &str, offline_token: &str) -> String {
    let anchor = ConsultantUriAnchor::parse(offline_token).expect("valid offline anchor");
    IdentityEnvelope::anchored(
        relative_path,
        format!("sha256:{}", "d".repeat(64)),
        1,
        anchor,
    )
    .render_jsonl_line()
}

fn unresolved_line(relative_path: &str) -> String {
    IdentityEnvelope::unresolved(relative_path, format!("sha256:{}", "e".repeat(64)), 1)
        .render_jsonl_line()
}

fn envelope(lines: &[String]) -> String {
    let anchored = lines
        .iter()
        .filter(|line| line.contains("\"consultant_uri\""))
        .count() as u64;
    let entries = lines.len() as u64;
    let mut text = header(entries, anchored, entries - anchored);
    for line in lines {
        text.push_str(line);
    }
    text
}

fn temp_dir(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "ln_corpus_pageindex_contract_{tag}_{}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp dir");
    dir
}

#[test]
fn accounting_identities_and_whole_doc_resolution() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("AAAA"), "ARB", "100");
    catalog.insert(&token("BBBB"), "ARB", "200");
    // TOKEN CCCC has no records -> key_unresolved.

    let text = envelope(&[
        anchored_line("courts/acn/a.xml", &token("AAAA")),
        anchored_line("courts/acn/b.xml", &token("BBBB")),
        anchored_line("courts/acn/c.xml", &token("CCCC")),
        unresolved_line("courts/acn/d.xml"),
    ]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");

    let counts = coverage.counts;
    assert_eq!(counts.entries, 4);
    assert_eq!(counts.anchored, 3);
    assert_eq!(counts.unresolved, 1);
    assert_eq!(
        counts.token_index, counts.anchored,
        "token_index == anchored"
    );
    assert_eq!(counts.keyed, 2);
    assert_eq!(counts.key_unresolved, counts.anchored - counts.keyed);
    assert_eq!(counts.key_collision, 0);
    assert_eq!(counts.token_multi_keyed, 0);
    assert_eq!(
        coverage.keyed_by_bank.values().sum::<u64>(),
        counts.keyed,
        "sum(keyed_by_bank) == keyed"
    );
    assert_eq!(
        coverage.key_unresolved_by_bank.values().sum::<u64>(),
        counts.key_unresolved,
        "sum(key_unresolved_by_bank) == key_unresolved"
    );
    assert_eq!(coverage.key_unresolved_by_bank.get("courts"), Some(&1));

    // Whole-document semantics: the sentinel reads as WholeDocument and never
    // rewrites the token; a concrete para is an ordinary paragraph.
    let whole = coverage
        .index
        .resolve_key("ARB", "100", WHOLE_DOCUMENT_PARA);
    match whole {
        PageIndexResolution::Hit(hit) => {
            assert_eq!(hit.scope, DocumentScope::WholeDocument);
            assert_eq!(hit.scope.as_str(), "whole_document");
        }
        other => panic!("expected whole-document hit, got {other:?}"),
    }
    match coverage.index.resolve_key("ARB", "100", 7) {
        PageIndexResolution::Hit(hit) => assert_eq!(hit.scope, DocumentScope::Paragraph(7)),
        other => panic!("expected paragraph hit, got {other:?}"),
    }
    // A document identity path is never a resolution key.
    assert!(
        !coverage
            .index
            .resolve_offline_token("courts/acn/a.xml")
            .is_hit()
    );
}

#[test]
fn key_collision_excluded_and_counted() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("SAME"), "ARB", "1");

    // Two distinct documents claim the same catalog key -> one collision, the
    // key is excluded rather than letting a silent winner through.
    let text = envelope(&[
        anchored_line("courts/acn/one.xml", &token("SAME")),
        anchored_line("courts/acn/two.xml", &token("SAME")),
    ]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");

    assert_eq!(coverage.counts.key_collision, 1);
    assert_eq!(coverage.counts.keyed, 0);
    assert_eq!(coverage.counts.key_unresolved, 2);
    assert!(coverage.entries.is_empty(), "collided key is excluded");
    assert!(coverage.index.is_empty());
}

#[test]
fn token_multi_keyed_keeps_all_records() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("MULTI"), "ARB", "1");
    catalog.insert(&token("MULTI"), "ASK", "2");

    let text = envelope(&[anchored_line("courts/acn/m.xml", &token("MULTI"))]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");

    assert_eq!(coverage.counts.token_multi_keyed, 1);
    assert_eq!(coverage.counts.keyed, 1);
    assert_eq!(coverage.counts.key_unresolved, 0);
    assert_eq!(coverage.entries.len(), 2, "all rows are kept");
    assert_eq!(coverage.index.len(), 2);
    assert_eq!(coverage.keyed_by_bank.values().sum::<u64>(), 1);
}

#[test]
fn key_unresolved_class_uses_path_segment_label() {
    let catalog = InMemoryPageIndexCatalog::new();
    let text = envelope(&[
        anchored_line("courts/acn/a.xml", &token("NOPE1")),
        anchored_line("npa/law/b.xml", &token("NOPE2")),
        unresolved_line("xml/c.xml"),
    ]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");

    assert_eq!(coverage.counts.keyed, 0);
    assert_eq!(coverage.counts.key_unresolved, 2);
    assert_eq!(coverage.key_unresolved_by_bank.get("courts"), Some(&1));
    assert_eq!(coverage.key_unresolved_by_bank.get("npa"), Some(&1));
    assert!(coverage.entries.is_empty());
}

#[test]
fn path_like_catalog_key_refused() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("PATHY"), "a/b", "1");

    let text = envelope(&[anchored_line("courts/acn/p.xml", &token("PATHY"))]);
    let error = build_coverage(&text, &catalog_meta(), &catalog)
        .expect_err("path-like catalog bank must be refused");
    assert_eq!(error.operation(), "index-build");
    assert!(!error.detail().is_empty());
    assert!(!error.to_string().is_empty());
}

#[test]
fn negative_probe_is_zero() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("AAAA"), "ARB", "100");
    let text = envelope(&[anchored_line("courts/acn/a.xml", &token("AAAA"))]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");

    assert_eq!(coverage.negative_probe.key_matches, 0);
    assert_eq!(coverage.negative_probe.token_matches, 0);
    assert_eq!(
        coverage.negative_probe.numbers,
        vec!["44-ФЗ".to_owned(), "402-ФЗ".to_owned(), "5-фкз".to_owned()]
    );
    for row in &coverage.negative_probe.per_number {
        assert_eq!(row.key_matches, 0);
        assert_eq!(row.token_matches, 0);
    }
}

#[test]
fn render_deterministic_double_render_identical() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("AAAA"), "ARB", "100");
    let text = envelope(&[anchored_line("courts/acn/a.xml", &token("AAAA"))]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");

    let first = render_pageindex_coverage_json(&coverage).expect("render");
    let second = render_pageindex_coverage_json(&coverage).expect("render");
    assert_eq!(first, second, "double render must be byte-identical");
    let index_first = render_pageindex_jsonl(&coverage).expect("render");
    let index_second = render_pageindex_jsonl(&coverage).expect("render");
    assert_eq!(index_first, index_second);
}

#[test]
fn input_change_changes_bytes() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("AAAA"), "ARB", "100");
    let first = envelope(&[anchored_line("courts/acn/a.xml", &token("AAAA"))]);
    let second = envelope(&[anchored_line("courts/acn/CHANGED.xml", &token("AAAA"))]);
    let base = build_coverage(&first, &catalog_meta(), &catalog).expect("coverage should build");
    let changed =
        build_coverage(&second, &catalog_meta(), &catalog).expect("coverage should build");

    // The document identity path lives in the index artifact: a path change is
    // byte-visible there (drift is detectable).
    assert_ne!(
        render_pageindex_jsonl(&base).unwrap(),
        render_pageindex_jsonl(&changed).unwrap(),
        "a changed document identity must change the index bytes"
    );

    // The coverage artifact pins the envelope sha256: a changed envelope file
    // changes the coverage bytes even when the class tallies are unchanged.
    let mut repinned = catalog_meta();
    repinned.envelope_sha256 = format!("sha256:{}", "f".repeat(64));
    let pinned = build_coverage(&first, &repinned, &catalog).expect("coverage should build");
    assert_ne!(
        render_pageindex_coverage_json(&base).unwrap(),
        render_pageindex_coverage_json(&pinned).unwrap(),
        "a changed envelope pin must change the coverage bytes"
    );
}

#[test]
fn artifacts_are_ascii() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("AAAA"), "ARB", "100");
    let text = envelope(&[anchored_line("courts/acn/a.xml", &token("AAAA"))]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");

    let json = render_pageindex_coverage_json(&coverage).unwrap();
    let jsonl = render_pageindex_jsonl(&coverage).unwrap();
    assert!(json.is_ascii(), "coverage payload must be ASCII");
    assert!(jsonl.is_ascii(), "index payload must be ASCII");
    // The Cyrillic negative-probe numbers are escaped, never literal bytes.
    assert!(json.contains("\\u0444"));
    assert!(!json.contains('Ф'));
}

#[test]
fn index_jsonl_header_and_sorted_unique_keys() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("BBBB"), "ARB", "200");
    catalog.insert(&token("AAAA"), "ARB", "100");
    let text = envelope(&[
        anchored_line("courts/acn/b.xml", &token("BBBB")),
        anchored_line("courts/acn/a.xml", &token("AAAA")),
    ]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");
    let jsonl = render_pageindex_jsonl(&coverage).unwrap();
    let mut lines = jsonl.lines();
    let header: serde_json::Value =
        serde_json::from_str(lines.next().expect("header line")).expect("header json");
    assert_eq!(header["schema"], "m224-s03-pageindex-entries/v1");
    assert_eq!(header["kind"], "pageindex_header");
    assert_eq!(header["whole_document_para"], 4294967295u64);

    let parsed: Vec<serde_json::Value> = lines
        .map(|line| serde_json::from_str(line).expect("entry json"))
        .collect();
    assert_eq!(parsed.len(), coverage.entries.len());
    let keys: Vec<(String, String)> = parsed
        .iter()
        .map(|entry| {
            (
                entry["bank"].as_str().unwrap().to_owned(),
                entry["document_key"].as_str().unwrap().to_owned(),
            )
        })
        .collect();
    let mut sorted = keys.clone();
    sorted.sort();
    sorted.dedup();
    assert_eq!(keys, sorted, "keys are sorted ascending and unique");
    for key in &keys {
        assert!(!key.0.contains('/') && !key.0.contains('\\'));
        assert!(!key.1.contains('/') && !key.1.contains('\\'));
    }
}

#[test]
fn header_count_mismatch_rejected() {
    let catalog = InMemoryPageIndexCatalog::new();
    let mut text = header(5, 5, 0); // wrong counts
    text.push_str(&anchored_line("courts/acn/a.xml", &token("AAAA")));
    let error = build_coverage(&text, &catalog_meta(), &catalog)
        .expect_err("count mismatch must be refused");
    assert_eq!(error.operation(), "envelope-count-mismatch");
}

#[test]
fn catalog_pin_mismatch_rejected() {
    let catalog = InMemoryPageIndexCatalog::new();
    let text = header(0, 0, 0);
    let mut meta = catalog_meta();
    meta.catalog_sha256 = format!("sha256:{}", "f".repeat(64));
    let error =
        build_coverage(&text, &meta, &catalog).expect_err("catalog pin mismatch must be refused");
    assert_eq!(error.operation(), "catalog-sha-mismatch");
}

#[test]
fn verify_detects_missing_and_drift() {
    let mut catalog = InMemoryPageIndexCatalog::new();
    catalog.insert(&token("AAAA"), "ARB", "100");
    let text = envelope(&[anchored_line("courts/acn/a.xml", &token("AAAA"))]);
    let coverage = build_coverage(&text, &catalog_meta(), &catalog).expect("coverage should build");

    let dir = temp_dir("check");
    let coverage_path = dir.join("coverage.json");
    let index_path = dir.join("index.jsonl");
    let coverage_json = render_pageindex_coverage_json(&coverage).unwrap();
    let index_jsonl = render_pageindex_jsonl(&coverage).unwrap();
    fs::write(&coverage_path, coverage_json.as_bytes()).unwrap();
    fs::write(&index_path, index_jsonl.as_bytes()).unwrap();

    verify_pageindex_artifacts(&coverage, &coverage_path, &index_path).expect("clean artifacts");

    fs::write(&coverage_path, b"drifted\n").unwrap();
    let drift = verify_pageindex_artifacts(&coverage, &coverage_path, &index_path)
        .expect_err("drift must be detected");
    assert_eq!(drift.operation(), "check-drift");
    assert_eq!(pageindex_exit_code_for(&drift), EXIT_DRIFT);

    // Restore the coverage artifact, then remove the index so the missing-file
    // path is exercised in isolation.
    fs::write(&coverage_path, coverage_json.as_bytes()).unwrap();
    fs::remove_file(&index_path).unwrap();
    let missing = verify_pageindex_artifacts(&coverage, &coverage_path, &index_path)
        .expect_err("missing artifact must be detected");
    assert_eq!(missing.operation(), "check-missing");
    assert_eq!(pageindex_exit_code_for(&missing), EXIT_ARTIFACT_MISSING);

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn non_canonical_envelope_line_rejected() {
    let catalog = InMemoryPageIndexCatalog::new();
    let mut text = header(1, 1, 0);
    text.push_str("{\"schema\":\"m224-s02-identity-envelope/v1\"}\n");
    let error = build_coverage(&text, &catalog_meta(), &catalog)
        .expect_err("non-canonical line must be refused");
    assert_eq!(error.operation(), "envelope-record");
    assert!(matches!(error, PageIndexBuildError { .. }));
}
