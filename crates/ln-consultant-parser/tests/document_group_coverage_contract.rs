//! Contract test: corpus `document_groups` coverage (M224/S04/T03).
//!
//! Exercises the library surface and the `document-group-coverage` bin on a
//! synthetic S02 manifest + embedded ontology catalog: the accounting
//! identities, the separate structural/principal axes (D667), the per-bank
//! header pins, the catalog-derived non-normative class list, `--check`
//! byte-identity/drift, determinism, the ASCII redaction posture, and the
//! fail-closed refusals (foreign schema, subdir mismatch, malformed subdirs,
//! practice bank leaking into an AST-bearing structural group).

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::document_group_coverage::{
    BankCoverage, CLASS_NON_NORMATIVE, CLASS_NORMATIVE, CLASS_UNKNOWN, COVERAGE_KIND,
    COVERAGE_SCHEMA, DocumentGroupCoverage, EXIT_ARTIFACT_MISSING, EXIT_DRIFT,
    build_document_group_coverage, parse_document_group_coverage_args,
    render_document_group_coverage, run_document_group_coverage, verify_document_group_coverage,
};
use ln_kb_ontology::bank_normativity::BankNormativity;

const BIN: &str = env!("CARGO_BIN_EXE_document-group-coverage");

static TEMP_SEQ: AtomicU64 = AtomicU64::new(0);

struct TempDir {
    path: PathBuf,
}

impl TempDir {
    fn new(label: &str) -> Self {
        let seq = TEMP_SEQ.fetch_add(1, Ordering::Relaxed);
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or(0);
        let path = std::env::temp_dir().join(format!(
            "ln-document-group-coverage-{}-{}-{}-{label}",
            std::process::id(),
            nanos,
            seq
        ));
        fs::create_dir_all(&path).expect("create temp dir");
        Self { path }
    }

    fn path(&self) -> &Path {
        &self.path
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.path);
    }
}

/// Deterministic valid-looking `sha256:<64 lowercase hex>` for record `index`.
fn entry_sha(index: u8) -> String {
    format!("sha256:{:02x}{}", index, "0".repeat(62))
}

/// Build a synthetic `m223-s02-corpus-inventory/v1` manifest. `subdirs` is
/// rendered verbatim as the header `subdirs` value so tests can inject a
/// mismatch or a malformed pin.
fn manifest_text(records: &[(&str, u64)], subdirs: &str) -> String {
    let mut text = String::new();
    text.push_str(&format!(
        "{{\"schema\":\"m223-s02-corpus-inventory/v1\",\"version\":1,\"root\":\"consru_export/consru_export/exports\",\
\"counts\":{{\"entries\":{},\"total_bytes\":0,\"max_bytes\":0}},\"subdirs\":{subdirs},\
\"pins\":{{\"count\":0,\"total_bytes\":0,\"max_bytes\":0,\"match\":true,\"drift\":[]}},\
\"inventory_digest\":\"sha256:{}\"}}\n",
        records.len(),
        "d".repeat(64)
    ));
    for (index, (relative_path, bytes)) in records.iter().enumerate() {
        text.push_str(&format!(
            "{{\"relative_path\":\"{}\",\"sha256\":\"{}\",\"bytes\":{bytes}}}\n",
            json_escape(relative_path),
            entry_sha(index as u8 + 1)
        ));
    }
    text
}

fn json_escape(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

fn write_manifest(dir: &Path, records: &[(&str, u64)], subdirs: &str) -> PathBuf {
    let path = dir.join("manifest.jsonl");
    fs::write(&path, manifest_text(records, subdirs)).expect("write manifest fixture");
    path
}

/// Header pins matching [`SEEDED_RECORDS`].
const SEEDED_SUBDIRS: &str =
    "{\"courts\":{\"entries\":2},\"fas\":{\"entries\":2},\"npa\":{\"entries\":3}}";

/// Eight seeded records covering both axes plus the explicit special keys:
/// `courts/acn/*` + `fas/determination_*` → structural `non_normative`;
/// `courts/court_*` + `fas/decision_*` → `court_practice`;
/// `npa/law_*` + `npa/directive_*` → structural law groups;
/// `npa/kodeks_decree_*` → same-rank `Conflict`; `unknownbank/*` → `Unknown`.
const SEEDED_RECORDS: [(&str, u64); 8] = [
    ("courts/acn/0001-edition.xml", 10),
    ("courts/court_5.xml", 20),
    ("fas/decision_2025.xml", 30),
    ("fas/determination_2026.xml", 40),
    ("npa/law_44-fz.xml", 50),
    ("npa/directive_1-r.xml", 60),
    ("npa/kodeks_decree_1.xml", 70),
    ("unknownbank/doc.xml", 80),
];

fn seeded(dir: &Path) -> PathBuf {
    write_manifest(dir, &SEEDED_RECORDS, SEEDED_SUBDIRS)
}

#[test]
fn accounting_identities_hold_on_the_fixture() {
    let dir = TempDir::new("accounting");
    let manifest = seeded(dir.path());
    let coverage = build_document_group_coverage(&manifest).expect("build coverage");

    assert_eq!(coverage.entries, 8);
    let counts = coverage.counts();
    assert_eq!(counts.normative, 3, "npa rows are normative");
    assert_eq!(counts.non_normative, 4, "courts/fas rows are non-normative");
    assert_eq!(counts.unknown, 1, "unknownbank row is unknown");
    assert_eq!(counts.normative + counts.non_normative + counts.unknown, 8);
    assert_eq!(
        coverage.by_class.values().sum::<u64>(),
        coverage.entries,
        "sum(by_class) == entries"
    );
    assert_eq!(
        coverage
            .by_bank
            .values()
            .map(|bank| bank.total)
            .sum::<u64>(),
        coverage.entries,
        "sum(by_bank totals) == entries"
    );
    assert_eq!(
        coverage.by_group.values().sum::<u64>(),
        coverage.entries,
        "sum(by_group) == entries"
    );
    assert_eq!(coverage.ctv_blocked, counts.non_normative);
    assert_eq!(coverage.ctv_blocked, 4);
}

#[test]
fn per_bank_split_matches_the_fixture_and_header_pins() {
    let dir = TempDir::new("per-bank");
    let manifest = seeded(dir.path());
    let coverage = build_document_group_coverage(&manifest).expect("build coverage");

    let courts = coverage.by_bank.get("courts").copied().unwrap();
    assert_eq!(
        courts,
        BankCoverage {
            total: 2,
            normative: 0,
            non_normative: 2,
            unknown: 0
        }
    );
    let fas = coverage.by_bank.get("fas").copied().unwrap();
    assert_eq!(fas.total, 2);
    assert_eq!(fas.non_normative, 2);
    let npa = coverage.by_bank.get("npa").copied().unwrap();
    assert_eq!(
        npa,
        BankCoverage {
            total: 3,
            normative: 3,
            non_normative: 0,
            unknown: 0
        }
    );
}

#[test]
fn unknown_bank_is_a_separate_class_not_folded() {
    let dir = TempDir::new("unknown-bank");
    let manifest = seeded(dir.path());
    let coverage = build_document_group_coverage(&manifest).expect("build coverage");

    let unknown = coverage.by_bank.get("unknownbank").copied().unwrap();
    assert_eq!(unknown.total, 1);
    assert_eq!(unknown.unknown, 1);
    assert_eq!(unknown.normative, 0);
    assert_eq!(unknown.non_normative, 0);
    assert_eq!(coverage.by_class.get(CLASS_UNKNOWN), Some(&1));
    // The unknown bank row also has no structural needle → explicit `Unknown`.
    assert_eq!(coverage.by_group.get("Unknown"), Some(&1));
}

#[test]
fn conflict_group_is_keyed_explicitly_on_the_structural_axis() {
    let dir = TempDir::new("conflict");
    let manifest = seeded(dir.path());
    let coverage = build_document_group_coverage(&manifest).expect("build coverage");

    assert_eq!(
        coverage.by_group.get("Conflict"),
        Some(&1),
        "same-rank code/presidential_decree binds are Conflict, never silently folded"
    );
    // The conflict row is in the normative npa bank, so it is not CTV-blocked.
    assert_eq!(coverage.by_class.get(CLASS_NORMATIVE), Some(&3));
}

#[test]
fn non_normative_classes_are_catalog_derived() {
    let dir = TempDir::new("classes");
    let manifest = seeded(dir.path());
    let coverage = build_document_group_coverage(&manifest).expect("build coverage");

    assert_eq!(
        coverage.non_normative_classes,
        vec!["court_practice".to_owned(), "non_normative".to_owned()]
    );
    assert!(!coverage.document_groups_version.is_empty());
}

#[test]
fn class_keys_match_the_bank_normativity_contract() {
    assert_eq!(CLASS_NORMATIVE, BankNormativity::Normative.as_str());
    assert_eq!(CLASS_NON_NORMATIVE, BankNormativity::NonNormative.as_str());
    assert_eq!(CLASS_UNKNOWN, BankNormativity::Unknown.as_str());
}

#[test]
fn render_is_ascii_and_carries_the_closed_schema() {
    let dir = TempDir::new("render");
    let manifest = seeded(dir.path());
    let coverage = build_document_group_coverage(&manifest).expect("build coverage");
    let rendered = render_document_group_coverage(&coverage).expect("render");
    assert!(rendered.is_ascii(), "artifact payload must be byte-ASCII");
    assert!(rendered.contains(COVERAGE_SCHEMA));
    assert!(rendered.contains(COVERAGE_KIND));
    assert!(rendered.contains("\"r1000_status\": \"active/unclosed\""));
    assert!(rendered.contains("structural_group_unknown_is_not_legal_non_normativity"));
}

#[test]
fn render_escapes_non_ascii_manifest_path() {
    let coverage = DocumentGroupCoverage {
        manifest_path: "prd/\u{043c}\u{0430}\u{043d}ифест.jsonl".to_owned(),
        manifest_sha256: format!("sha256:{}", "a".repeat(64)),
        inventory_digest: format!("sha256:{}", "b".repeat(64)),
        entries: 0,
        by_class: BTreeMap::new(),
        by_bank: BTreeMap::new(),
        by_group: BTreeMap::new(),
        non_normative_classes: Vec::new(),
        ctv_blocked: 0,
        document_groups_version: "fnv1a64-0".to_owned(),
    };
    let rendered = render_document_group_coverage(&coverage).expect("render");
    assert!(
        rendered.is_ascii(),
        "non-ASCII must be escaped, not emitted"
    );
    assert!(rendered.contains("\\u043c"));
}

#[test]
fn double_render_is_deterministic() {
    let dir = TempDir::new("determinism");
    let manifest = seeded(dir.path());
    let first = build_document_group_coverage(&manifest).expect("first build");
    let second = build_document_group_coverage(&manifest).expect("second build");
    assert_eq!(
        render_document_group_coverage(&first).unwrap(),
        render_document_group_coverage(&second).unwrap()
    );
}

#[test]
fn bin_writes_and_check_is_byte_identical() {
    let dir = TempDir::new("bin");
    let manifest = seeded(dir.path());
    let out = dir.path().join("coverage.json");

    let write = Command::new(BIN)
        .args([
            "--manifest",
            manifest.to_str().unwrap(),
            "--out",
            out.to_str().unwrap(),
        ])
        .output()
        .expect("run bin in write mode");
    assert_eq!(write.status.code(), Some(0));
    let stderr = String::from_utf8_lossy(&write.stderr);
    assert!(
        stderr.contains("entries=8 non_normative=4"),
        "log line reports the corpus counts: {stderr}"
    );
    assert!(fs::read(&out).unwrap().is_ascii());

    let check = Command::new(BIN)
        .args([
            "--manifest",
            manifest.to_str().unwrap(),
            "--out",
            out.to_str().unwrap(),
            "--check",
        ])
        .output()
        .expect("run bin in check mode");
    assert_eq!(check.status.code(), Some(0));
    assert!(String::from_utf8_lossy(&check.stderr).contains("check=ok entries=8 non_normative=4"));

    // Drift detection: an extra byte must be caught.
    let mut drifted = fs::read(&out).unwrap();
    drifted.push(b'\n');
    fs::write(&out, &drifted).unwrap();
    let drift = Command::new(BIN)
        .args([
            "--manifest",
            manifest.to_str().unwrap(),
            "--out",
            out.to_str().unwrap(),
            "--check",
        ])
        .output()
        .expect("run check after drift");
    assert_eq!(drift.status.code(), Some(i32::from(EXIT_DRIFT)));

    // Missing artifact refusal.
    let absent = dir.path().join("absent.json");
    let missing = Command::new(BIN)
        .args([
            "--manifest",
            manifest.to_str().unwrap(),
            "--out",
            absent.to_str().unwrap(),
            "--check",
        ])
        .output()
        .expect("run check against a missing artifact");
    assert_eq!(
        missing.status.code(),
        Some(i32::from(EXIT_ARTIFACT_MISSING))
    );
}

#[test]
fn library_check_refuses_missing_artifact() {
    let dir = TempDir::new("lib-check");
    let manifest = seeded(dir.path());
    let coverage = build_document_group_coverage(&manifest).unwrap();
    let absent = dir.path().join("absent.json");
    let error = verify_document_group_coverage(&coverage, &absent)
        .expect_err("missing artifact must fail closed");
    assert_eq!(error.operation(), "check-missing");
}

#[test]
fn argv_requires_manifest_and_out() {
    let parsed = parse_document_group_coverage_args(
        ["--manifest", "m.jsonl", "--out", "o.json", "--check"]
            .into_iter()
            .map(str::to_owned),
    )
    .expect("complete argv parses");
    assert!(parsed.check);
    assert_eq!(parsed.manifest, "m.jsonl");
    assert_eq!(parsed.out, "o.json");

    let missing = parse_document_group_coverage_args(
        ["--manifest", "m.jsonl"].into_iter().map(str::to_owned),
    )
    .expect_err("missing --out is refused");
    assert!(missing.contains("--out"), "detail names the missing flag");
    let unknown = parse_document_group_coverage_args(["--wat"].into_iter().map(str::to_owned))
        .expect_err("unknown flag is refused");
    assert!(unknown.contains("--wat"));
    let no_value =
        parse_document_group_coverage_args(["--manifest"].into_iter().map(str::to_owned))
            .expect_err("flag without value is refused");
    assert!(no_value.contains("--manifest"));
}

#[test]
fn subdir_pin_mismatch_fails_closed() {
    let dir = TempDir::new("subdir-mismatch");
    let manifest = write_manifest(
        dir.path(),
        &SEEDED_RECORDS,
        "{\"courts\":{\"entries\":99},\"fas\":{\"entries\":2},\"npa\":{\"entries\":3}}",
    );
    let error =
        build_document_group_coverage(&manifest).expect_err("mismatched header pin must fail");
    assert_eq!(error.operation(), "manifest-subdir-mismatch");
    assert!(error.detail().contains("courts"));
}

#[test]
fn malformed_subdir_pin_fails_closed() {
    let dir = TempDir::new("malformed-subdir");
    let manifest = write_manifest(
        dir.path(),
        &SEEDED_RECORDS,
        "{\"courts\":5,\"fas\":{\"entries\":2},\"npa\":{\"entries\":3}}",
    );
    let error =
        build_document_group_coverage(&manifest).expect_err("non-object subdir pin must fail");
    assert_eq!(error.operation(), "manifest-parse");
}

#[test]
fn missing_subdirs_pin_is_tolerated() {
    let dir = TempDir::new("no-subdirs");
    let manifest = write_manifest(dir.path(), &SEEDED_RECORDS, "{}");
    let coverage = build_document_group_coverage(&manifest).expect("absent pins are tolerated");
    assert_eq!(coverage.entries, 8);
    assert_eq!(coverage.counts().non_normative, 4);
}

#[test]
fn practice_bank_leaking_into_structural_group_fails_closed() {
    let dir = TempDir::new("leak");
    // `courts/kodeks_*.xml` carries the `kodeks` path needle (code, rank 10),
    // so a non-normative bank would bind to an AST-bearing structural group.
    let manifest = write_manifest(dir.path(), &[("courts/kodeks_1.xml", 10)], "{}");
    let error =
        build_document_group_coverage(&manifest).expect_err("practice leak must fail closed");
    assert_eq!(error.operation(), "practice-bank-structural-leak");
}

#[test]
fn foreign_manifest_schema_fails_closed() {
    let dir = TempDir::new("foreign");
    let path = dir.path().join("manifest.jsonl");
    fs::write(
        &path,
        "{\"schema\":\"other/v1\",\"counts\":{\"entries\":0},\"inventory_digest\":\"sha256:d\"}\n",
    )
    .unwrap();
    let error = build_document_group_coverage(&path).expect_err("foreign schema must fail");
    assert_eq!(error.operation(), "manifest-parse");
}

#[test]
fn absent_manifest_fails_closed() {
    let dir = TempDir::new("absent-manifest");
    let path = dir.path().join("does-not-exist.jsonl");
    let error =
        build_document_group_coverage(&path).expect_err("missing manifest must fail closed");
    assert_eq!(error.operation(), "manifest-read");
}

#[test]
fn run_surface_returns_exit_codes() {
    let dir = TempDir::new("run");
    let manifest = seeded(dir.path());
    let out = dir.path().join("coverage.json");
    let write_cli = parse_document_group_coverage_args(
        [
            "--manifest",
            manifest.to_str().unwrap(),
            "--out",
            out.to_str().unwrap(),
        ]
        .into_iter()
        .map(str::to_owned),
    )
    .unwrap();
    let (code, message) = run_document_group_coverage(&write_cli);
    assert_eq!(code, 0);
    assert_eq!(message, "entries=8 non_normative=4");

    let usage_cli = parse_document_group_coverage_args(
        ["--manifest", manifest.to_str().unwrap()]
            .into_iter()
            .map(str::to_owned),
    )
    .expect_err("usage error");
    assert!(usage_cli.contains("--out"));
}
