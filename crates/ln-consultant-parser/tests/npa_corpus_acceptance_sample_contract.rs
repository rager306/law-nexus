//! T02 contract test (M214-es3jvw S04): the pinned provider/work-family
//! stratified sample builder over synthetic corpora.
//!
//! Non-claims: synthetic fixtures only; count/hash only; no decoded corpus
//! text enters the manifest. The real tracked manifest is materialized by
//! `npa-corpus-sample` (T02) over the declared corpus roots.

use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::corpus_sample::SourceRootKind;
use ln_consultant_parser::npa_corpus_acceptance::{
    build_sample, declared_sample_roots, CorpusSampleManifest, DeclaredThresholds, SampleRoot,
    C3_EXCLUSION_NONE, CONSULTANT_ROOT_RELATIVE, DECLARED_SAMPLE_SIZE, GARANT_ROOT_RELATIVE,
};
use sha2::{Digest, Sha256};

fn unique_dir(tag: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock is after the epoch")
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("m214-s04-{tag}-{}-{nanos}", std::process::id()));
    fs::create_dir_all(&dir).expect("temp dir is creatable");
    dir
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    let mut out = String::with_capacity(digest.len() * 2);
    for byte in digest {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

/// Write `families` consultant documents, each in its own `npa/law_XXXX`
/// work-family directory, carrying a unique in-body marker.
fn write_consultant(root: &Path, families: usize) {
    for index in 0..families {
        let dir = root.join("npa").join(format!("law_{index:04}"));
        fs::create_dir_all(&dir).expect("family dir is creatable");
        let body = format!("<doc id=\"{index}\">secret-marker-{index}</doc>");
        fs::write(dir.join("edition-0001.xml"), body).expect("fixture file is writable");
    }
}

/// A synthetic corpus: an exports tree with `families` distinct families plus
/// an (empty) garant root.
fn fixture(tag: &str, families: usize) -> (PathBuf, PathBuf, PathBuf) {
    let base = unique_dir(tag);
    let consultant = base.join("consru_export/consru_export/exports");
    let garant = base.join("law-source/garant");
    fs::create_dir_all(&consultant).expect("consultant root is creatable");
    fs::create_dir_all(&garant).expect("garant root is creatable");
    write_consultant(&consultant, families);
    (base, consultant, garant)
}

fn roots(consultant: &Path, garant: &Path) -> Vec<SampleRoot> {
    declared_sample_roots(consultant.to_path_buf(), garant.to_path_buf())
        .expect("declared roots are valid")
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn declared_roots_use_the_frozen_repo_paths() {
    let roots = declared_sample_roots(
        PathBuf::from(CONSULTANT_ROOT_RELATIVE),
        PathBuf::from(GARANT_ROOT_RELATIVE),
    )
    .expect("frozen roots are valid");
    assert_eq!(roots.len(), 2);
    assert_eq!(roots[0].relative_path, CONSULTANT_ROOT_RELATIVE);
    assert_eq!(roots[0].kind, SourceRootKind::ConsultantExport);
    assert_eq!(roots[1].relative_path, GARANT_ROOT_RELATIVE);
    assert_eq!(roots[1].kind, SourceRootKind::Garant);
}

#[test]
fn synthetic_sample_is_pinned_deterministic_and_count_hash_only() {
    let (base, consultant, garant) = fixture("pinned", 450);
    let first = build_sample(&roots(&consultant, &garant)).expect("fixture yields a sample");
    let second = build_sample(&roots(&consultant, &garant)).expect("rebuild is stable");

    assert_eq!(first.entries.len() as u64, DECLARED_SAMPLE_SIZE);
    assert_eq!(first.corpus_snapshot_sha256, second.corpus_snapshot_sha256);
    assert!(first.declared_before_run);
    assert!(first.not_year_type_stratified);
    assert_eq!(first.c3_exclusion, C3_EXCLUSION_NONE);
    assert_eq!(first.roots.len(), 2);
    assert_eq!(first.leakage.consultant_selected, DECLARED_SAMPLE_SIZE);
    assert_eq!(first.leakage.garant_selected, 0);

    for entry in &first.entries {
        assert_eq!(entry.provider.as_str(), "consultant_export");
        let file = consultant.join(&entry.relative_path);
        let bytes = fs::read(&file).expect("pinned file exists");
        assert_eq!(entry.bytes, bytes.len() as u64);
        assert_eq!(entry.sha256, format!("sha256:{}", sha256_hex(&bytes)));
        assert!(!entry.work_family.is_empty());
        assert!(!entry.document_type.is_empty());
    }

    // Byte-stable JSON and a clean round-trip through the fail-closed loader.
    let text = first.to_json_string().expect("manifest renders");
    assert_eq!(text, second.to_json_string().expect("rebuild renders"));
    let loaded = CorpusSampleManifest::load(&text).expect("manifest round-trips");
    assert_eq!(loaded.entries.len() as u64, DECLARED_SAMPLE_SIZE);

    // Count/hash only: no decoded fixture text leaks into the artifact.
    assert!(!text.contains("secret-marker"));
    assert!(!text.contains("<doc"));
    fs::remove_dir_all(&base).ok();
}

#[test]
fn snapshot_hash_changes_when_inventory_content_changes() {
    let (base, consultant, garant) = fixture("snapshot", 450);
    let first = build_sample(&roots(&consultant, &garant)).expect("fixture yields a sample");
    fs::write(
        consultant.join("npa/law_0000/edition-0001.xml"),
        b"<doc id=\"0\">changed</doc>",
    )
    .expect("fixture is rewritable");
    let second = build_sample(&roots(&consultant, &garant)).expect("rebuild succeeds");
    assert_ne!(
        first.corpus_snapshot_sha256, second.corpus_snapshot_sha256,
        "the snapshot must bind inventory content, not only paths"
    );
    fs::remove_dir_all(&base).ok();
}

#[test]
fn insufficient_inventory_fails_closed() {
    let (base, consultant, garant) = fixture("short", 5);
    let error =
        build_sample(&roots(&consultant, &garant)).expect_err("too few families must fail closed");
    assert!(
        error.contains("insufficient") || error.contains("refused"),
        "unexpected error: {error}"
    );
    fs::remove_dir_all(&base).ok();
}

#[test]
fn absent_root_fails_closed() {
    let (base, consultant, _garant) = fixture("absent", 5);
    let missing = base.join("law-source/does-not-exist");
    let error = build_sample(&roots(&consultant, &missing))
        .expect_err("an absent declared root must fail closed");
    assert!(error.contains("absent"), "unexpected error: {error}");
    fs::remove_dir_all(&base).ok();
}

#[test]
fn duplicate_declared_roots_are_refused() {
    let (base, consultant, garant) = fixture("dup", 5);
    let mut list = roots(&consultant, &garant);
    let mut duplicate = list[0].clone();
    duplicate.path = garant.clone();
    list.push(duplicate);
    let error = build_sample(&list).expect_err("duplicate declared roots must be refused");
    assert!(
        error.contains("duplicate declared root"),
        "unexpected error: {error}"
    );
    fs::remove_dir_all(&base).ok();
}

#[test]
fn non_ascii_entry_path_is_refused() {
    let (base, consultant, garant) = fixture("nonascii", 1);
    let dir = consultant.join("npa").join("закон_0001");
    fs::create_dir_all(&dir).expect("cyrillic family dir is creatable");
    fs::write(dir.join("edition.xml"), b"<doc/>").expect("fixture file is writable");
    let error = build_sample(&roots(&consultant, &garant))
        .expect_err("an ascii_only manifest must refuse a non-ascii path");
    assert!(error.contains("non-ascii"), "unexpected error: {error}");
    fs::remove_dir_all(&base).ok();
}

#[test]
fn empty_corpus_file_is_refused() {
    let (base, consultant, garant) = fixture("empty", 1);
    fs::write(consultant.join("npa/law_0000/edition-0001.xml"), b"").expect("file is writable");
    let error = build_sample(&roots(&consultant, &garant))
        .expect_err("an empty corpus file must be refused");
    assert!(
        error.contains("empty corpus file"),
        "unexpected error: {error}"
    );
    fs::remove_dir_all(&base).ok();
}

#[test]
fn tracked_sample_manifest_is_present_and_pinned() {
    let path = repo_root().join("prd/migration/rust-evidence/m214-s04-corpus-sample.json");
    let text = fs::read_to_string(&path).expect("tracked S04 sample manifest must exist");
    let manifest = CorpusSampleManifest::load(&text).expect("tracked manifest must be valid");
    assert_eq!(manifest.entries.len() as u64, DECLARED_SAMPLE_SIZE);
    assert!(manifest.declared_before_run);
    assert_eq!(manifest.declared_thresholds, DeclaredThresholds::declared());
    assert_eq!(manifest.roots.len(), 2);
    assert!(manifest.not_year_type_stratified);
    assert!(text.is_ascii(), "the tracked sample must stay ascii-only");
}
