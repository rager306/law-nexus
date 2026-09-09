use ln_consultant_parser::corpus_manifest::{self, Admission};
use std::{collections::BTreeSet, fs, path::Path};

fn repo_path(relative: &str) -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(relative)
}
fn manifest(n: usize) -> corpus_manifest::CorpusManifest {
    corpus_manifest::load(&repo_path(&format!(
        "prd/migration/rust-evidence/m203-s08-c5-gold-manifest-{n}.json"
    )))
    .expect("frozen C5 manifest")
}

#[test]
fn ladder_is_nested_provider_stratified_and_proposed() {
    let c3 = corpus_manifest::load(&repo_path(
        "prd/migration/rust-evidence/m203-s08-c3-holdout-manifest.json",
    ))
    .unwrap();
    let r100 = manifest(100);
    let r400 = manifest(400);
    let r800 = manifest(800);
    assert_eq!(
        (r100.entries.len(), r400.entries.len(), r800.entries.len()),
        (100, 400, 800)
    );
    for r in [&r100, &r400, &r800] {
        assert_eq!(r.stratum, "C5");
        assert_eq!(r.lifecycle, "[proposed]");
        assert!(!r.sealed);
        assert!(r.manifest_digest.is_none());
        assert!(r
            .entries
            .iter()
            .all(|e| matches!(e.admission, Admission::DoubleCodedAccepted)));
        assert!(r.entries.iter().any(|e| e.provider == "consultant"));
        assert!(r.entries.iter().any(|e| e.provider == "garant"));
        assert!(r
            .entries
            .iter()
            .all(|e| !e.evidence_anchor.contains("raw") && !e.evidence_anchor.contains("text")));
    }
    let keys = |r: &corpus_manifest::CorpusManifest| {
        r.entries
            .iter()
            .map(|e| (e.entry_id.clone(), e.content_hash.clone()))
            .collect::<BTreeSet<_>>()
    };
    assert!(keys(&r100).is_subset(&keys(&r400)));
    assert!(keys(&r400).is_subset(&keys(&r800)));
    assert!(corpus_manifest::disjoint(&c3, &r800));
}

#[test]
fn durable_receipts_have_three_rungs_and_fail_closed_pins() {
    let root = repo_path("prd/migration/rust-evidence");
    let coding = fs::read_to_string(root.join("m203-s08-c5-coding.jsonl")).unwrap();
    let agreement = fs::read_to_string(root.join("m203-s08-c5-agreement.jsonl")).unwrap();
    let quality = fs::read_to_string(root.join("m203-s08-quality-receipts.jsonl")).unwrap();
    assert_eq!(coding.lines().count(), 3);
    assert_eq!(agreement.lines().count(), 3);
    assert_eq!(quality.lines().count(), 3);
    for line in quality.lines() {
        assert!(line.contains("\"human_acceptance\":null"));
        assert!(line.contains("\"critical_field_loss\":0"));
        assert!(line.contains("\"source_span_loss\":0"));
        assert!(line.contains("\"false_fact_mint\":0"));
        assert!(line.contains("not validated gold"));
        assert!(line.contains("not R035/R070"));
    }
    for line in agreement.lines() {
        assert!(line.contains("\"classification\":\"proxy\""));
        assert!(line.contains("\"percent\":1.0"));
        assert!(line.contains("\"alpha\":1.0"));
    }
    assert!(!coding.contains("raw_text_value"));
    assert!(coding
        .lines()
        .all(|line| line.contains("\"raw_text\":false")));
}

#[test]
fn ladder_cli_check_detects_staleness() {
    let root = repo_path("consru_export/consru_export/exports");
    let out = repo_path("prd/migration/rust-evidence");
    let status = std::process::Command::new(env!("CARGO_BIN_EXE_npa-gold-ladder"))
        .args([
            "--root",
            root.to_str().unwrap(),
            "--out",
            out.to_str().unwrap(),
            "--rung",
            "100",
            "--check",
        ])
        .status()
        .expect("run ladder check");
    assert!(status.success());
}
