//! Contract test: corpus-wide Consultant URI anchor coverage (M224/S02/T04).
//!
//! Exercises the library surface and the `identity-anchor-coverage` bin on a
//! seeded SQLite fixture + synthetic S02 manifest: accounting, per-bank
//! classes, byte-exact envelope lines, the closed-set negative probe, the
//! ASCII redaction posture, `--check` byte-identity/drift, determinism, and
//! fail-closed manifest refusals.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::anchor_coverage::{
    self, AnchorCoverageError, EXIT_ARTIFACT_MISSING, EXIT_DRIFT, build_anchor_coverage,
    parse_corpus_manifest, parse_coverage_args, render_coverage_json, render_envelope_jsonl,
    verify_artifacts,
};
use ln_decode::identity_envelope::IdentityEnvelope;
use rusqlite::{Connection, OpenFlags};

const BIN: &str = env!("CARGO_BIN_EXE_identity-anchor-coverage");

const TOKEN_A: &str = "consultantplus://offline/ref=235B1A968E4D59A97657E85BD86F6A71B8663B3F47605928A0B816F3C818983C064F496A1349154AB2FDE3A7CC220A36DABFB0FC2Ea4RCK";
const TOKEN_B: &str = "consultantplus://offline/ref=9E3314DB7361376719B3ADCEA898430BE476990BC9F6D0C1BD194E8D474CA6B73B5B623A5CF89E2A75B80C3814bD31I";

const RECORDS: [(&str, u64); 4] = [
    ("courts/acn/a.xml", 10),
    ("fas/b.xml", 20),
    ("npa/c.xml", 30),
    ("xml/d.xml", 40),
];

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
            "ln-anchor-coverage-{}-{}-{}-{label}",
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

fn manifest_text(records: &[(&str, u64)]) -> String {
    let mut text = String::new();
    text.push_str(&format!(
        "{{\"schema\":\"m223-s02-corpus-inventory/v1\",\"version\":1,\"root\":\"consru_export/consru_export/exports\",\
\"counts\":{{\"entries\":{},\"total_bytes\":0,\"max_bytes\":0}},\"subdirs\":{{}},\
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

/// Minimal JSON string escaper for the synthetic manifest writer.
fn json_escape(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

fn write_manifest(dir: &Path, records: &[(&str, u64)]) -> PathBuf {
    let path = dir.join("manifest.jsonl");
    fs::write(&path, manifest_text(records)).expect("write manifest fixture");
    path
}

/// Seed the observed catalog schema with one `editions` row per
/// `(manifest_relative_path, source_id)` pair.
fn seed_catalog(dir: &Path, rows: &[(&str, &str)]) -> PathBuf {
    let path = dir.join("catalog.sqlite");
    let connection = Connection::open_with_flags(
        &path,
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE,
    )
    .expect("writable fixture connection");
    connection
        .execute_batch(
            "CREATE TABLE documents (
                source_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                offline_uri TEXT,
                kind TEXT
            );
            CREATE TABLE editions (
                edition_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                document_type TEXT,
                document_date TEXT,
                number TEXT,
                revision_date TEXT,
                edition_number INTEGER,
                relative_path TEXT
            );",
        )
        .expect("create observed catalog schema");
    for (index, (relative_path, source_id)) in rows.iter().enumerate() {
        connection
            .execute(
                "INSERT INTO editions (
                    edition_id, source_id, document_type, document_date, number,
                    revision_date, edition_number, relative_path
                 ) VALUES (?1, ?2, 'zakon', '2020-01-01', NULL, '2020-01-01', 1, ?3)",
                rusqlite::params![
                    format!("edition-{index}"),
                    source_id,
                    format!("exports/{relative_path}")
                ],
            )
            .expect("insert editions row");
    }
    drop(connection);
    path
}

fn standard_fixture(dir: &Path) -> (PathBuf, PathBuf) {
    let manifest = write_manifest(dir, &RECORDS);
    let catalog = seed_catalog(
        dir,
        &[("courts/acn/a.xml", TOKEN_A), ("fas/b.xml", TOKEN_B)],
    );
    (manifest, catalog)
}

#[test]
fn builds_counts_and_bank_maps() {
    let dir = TempDir::new("counts");
    let (manifest, catalog) = standard_fixture(dir.path());
    let coverage = build_anchor_coverage(&manifest, &catalog).expect("coverage builds");

    assert_eq!(coverage.counts(), (4, 2, 2));
    assert_eq!(
        coverage.anchored_by_bank,
        BTreeMap::from([("courts".to_owned(), 1), ("fas".to_owned(), 1)])
    );
    assert_eq!(
        coverage.unresolved_by_bank,
        BTreeMap::from([("npa".to_owned(), 1), ("xml".to_owned(), 1)])
    );
    // Manifest order is preserved (T04: envelope order = manifest order).
    let paths: Vec<&str> = coverage
        .entries
        .iter()
        .map(|entry| entry.relative_path.as_str())
        .collect();
    assert_eq!(
        paths,
        vec!["courts/acn/a.xml", "fas/b.xml", "npa/c.xml", "xml/d.xml"]
    );

    let json = render_coverage_json(&coverage).expect("coverage render");
    let value: serde_json::Value = serde_json::from_str(&json).expect("coverage JSON parses");
    assert_eq!(value["schema"], "m224-s02-uri-anchor-coverage/v1");
    assert_eq!(value["counts"]["entries"].as_u64(), Some(4));
    assert_eq!(value["counts"]["anchored"].as_u64(), Some(2));
    assert_eq!(value["counts"]["unresolved"].as_u64(), Some(2));
    assert_eq!(value["r1000_status"], "active/unclosed");
    assert!(!value["non_claims"].as_array().unwrap().is_empty());
    // Accounting invariant: bank maps sum to the totals.
    let sum = |key: &str| -> u64 {
        value[key]
            .as_object()
            .unwrap()
            .values()
            .map(|count| count.as_u64().unwrap())
            .sum()
    };
    assert_eq!(sum("anchored_by_bank"), 2);
    assert_eq!(sum("unresolved_by_bank"), 2);
    // Closed-set negative probe: 0 matches for every extracted number.
    assert_eq!(value["negative_probe"]["exact_matches"].as_u64(), Some(0));
    assert_eq!(value["negative_probe"]["like_matches"].as_u64(), Some(0));
    let numbers: Vec<&str> = value["negative_probe"]["numbers"]
        .as_array()
        .unwrap()
        .iter()
        .map(|number| number.as_str().unwrap())
        .collect();
    assert_eq!(numbers, vec!["44-ФЗ", "402-ФЗ", "5-фкз"]);
    for row in value["negative_probe"]["per_number"].as_array().unwrap() {
        assert_eq!(row["exact_matches"].as_u64(), Some(0));
        assert_eq!(row["like_matches"].as_u64(), Some(0));
    }
}

#[test]
fn envelope_lines_are_byte_exact_and_classed() {
    let dir = TempDir::new("envelope");
    let (manifest, catalog) = standard_fixture(dir.path());
    let coverage = build_anchor_coverage(&manifest, &catalog).expect("coverage builds");
    let envelope = render_envelope_jsonl(&coverage).expect("envelope render");

    let lines: Vec<&str> = envelope.lines().collect();
    assert_eq!(lines.len(), 1 + coverage.entries.len());
    let header: serde_json::Value = serde_json::from_str(lines[0]).expect("header parses");
    assert_eq!(header["schema"], "m224-s02-identity-envelope/v1");
    assert_eq!(header["kind"], "identity_envelope_header");
    assert_eq!(header["counts"]["entries"].as_u64(), Some(4));

    let expected_tokens = BTreeMap::from([("courts/acn/a.xml", TOKEN_A), ("fas/b.xml", TOKEN_B)]);
    for (index, entry) in coverage.entries.iter().enumerate() {
        let line = lines[index + 1];
        let parsed = IdentityEnvelope::read_back(line).expect("canonical envelope line");
        assert_eq!(parsed.relative_path, entry.relative_path);
        assert_eq!(parsed.source_sha256, entry.sha256);
        assert_eq!(parsed.source_bytes, entry.bytes);
        match expected_tokens.get(entry.relative_path.as_str()) {
            Some(source_token) => {
                let parsed =
                    IdentityEnvelope::byte_exact_round_trip(line).expect("byte-exact round trip");
                parsed
                    .verify_byte_exact(source_token)
                    .expect("carried token is byte-exact to the catalog source_id");
                assert!(line.contains("\"consultant_uri\""));
                assert!(!line.contains("anchor_status"));
            }
            None => {
                assert!(parsed.anchor.is_none());
                assert!(line.contains("\"anchor_status\":\"anchor_unresolved\""));
                assert!(!line.contains("consultant_uri"));
            }
        }
    }
}

#[test]
fn artifacts_are_ascii_with_escaped_probe_numbers() {
    let dir = TempDir::new("ascii");
    let (manifest, catalog) = standard_fixture(dir.path());
    let coverage = build_anchor_coverage(&manifest, &catalog).expect("coverage builds");

    let coverage_json = render_coverage_json(&coverage).expect("coverage render");
    let envelope_jsonl = render_envelope_jsonl(&coverage).expect("envelope render");
    assert!(coverage_json.is_ascii(), "coverage payload must be ASCII");
    assert!(envelope_jsonl.is_ascii(), "envelope payload must be ASCII");
    // The closed-set probe literals are carried as JSON \uXXXX escapes, so the
    // artifact stays byte-ASCII without weakening the redaction guard.
    assert!(coverage_json.contains("\\u0424\\u0417"));
    assert!(!coverage_json.contains('Ф'));
    let value: serde_json::Value = serde_json::from_str(&coverage_json).unwrap();
    assert_eq!(value["negative_probe"]["numbers"][0], "44-ФЗ");
}

#[test]
fn negative_probe_detects_planted_match() {
    let dir = TempDir::new("planted");
    let manifest = write_manifest(dir.path(), &RECORDS);
    let catalog = seed_catalog(
        dir.path(),
        &[
            ("courts/acn/a.xml", TOKEN_A),
            // Planted diagnostic row: an extracted number is NOT a token; the
            // probe must surface it rather than be vacuously zero.
            ("not-in-manifest.xml", "44-ФЗ"),
        ],
    );
    let coverage = build_anchor_coverage(&manifest, &catalog).expect("coverage builds");
    assert_eq!(coverage.negative_probe.exact_matches, 1);
    assert_eq!(coverage.negative_probe.like_matches, 1);
    let planted = coverage
        .negative_probe
        .per_number
        .iter()
        .find(|row| row.number == "44-ФЗ")
        .expect("planted number probed");
    assert_eq!(planted.exact_matches, 1);
    assert_eq!(planted.like_matches, 1);
}

#[test]
fn bin_write_check_are_byte_identical_and_drift_fails_closed() {
    let dir = TempDir::new("bin");
    let (manifest, catalog) = standard_fixture(dir.path());
    let coverage_out = dir.path().join("coverage.json");
    let envelope_out = dir.path().join("envelope.jsonl");
    let manifest_arg = manifest.display().to_string();
    let catalog_arg = catalog.display().to_string();
    let coverage_arg = coverage_out.display().to_string();
    let envelope_arg = envelope_out.display().to_string();

    let write = Command::new(BIN)
        .args([
            "--manifest",
            &manifest_arg,
            "--catalog",
            &catalog_arg,
            "--coverage-out",
            &coverage_arg,
            "--envelope-out",
            &envelope_arg,
        ])
        .output()
        .expect("run bin in write mode");
    assert_eq!(write.status.code(), Some(0), "write mode exits clean");
    assert!(coverage_out.exists() && envelope_out.exists());

    let check = Command::new(BIN)
        .args([
            "--manifest",
            &manifest_arg,
            "--catalog",
            &catalog_arg,
            "--coverage-out",
            &coverage_arg,
            "--envelope-out",
            &envelope_arg,
            "--check",
        ])
        .output()
        .expect("run bin in check mode");
    assert_eq!(check.status.code(), Some(0), "check mode byte-identity");

    // Byte drift in the envelope is refused (never silently accepted), and the
    // check never rewrites the artifact.
    let mut drifted = fs::read(&envelope_out).unwrap();
    drifted.push(b'x');
    fs::write(&envelope_out, &drifted).unwrap();
    let drift = Command::new(BIN)
        .args([
            "--manifest",
            &manifest_arg,
            "--catalog",
            &catalog_arg,
            "--coverage-out",
            &coverage_arg,
            "--envelope-out",
            &envelope_arg,
            "--check",
        ])
        .output()
        .expect("run bin in check mode after drift");
    assert_eq!(drift.status.code(), Some(i32::from(EXIT_DRIFT)));
    assert_eq!(
        fs::read(&envelope_out).unwrap(),
        drifted,
        "check never writes"
    );

    fs::remove_file(&coverage_out).unwrap();
    let missing = Command::new(BIN)
        .args([
            "--manifest",
            &manifest_arg,
            "--catalog",
            &catalog_arg,
            "--coverage-out",
            &coverage_arg,
            "--envelope-out",
            &envelope_arg,
            "--check",
        ])
        .output()
        .expect("run bin in check mode after removal");
    assert_eq!(
        missing.status.code(),
        Some(i32::from(EXIT_ARTIFACT_MISSING))
    );

    // Coverage-artifact byte drift is refused too, and the clean envelope is
    // republished first so only the coverage file is mutated.
    fs::remove_file(&envelope_out).unwrap();
    let republish = Command::new(BIN)
        .args([
            "--manifest",
            &manifest_arg,
            "--catalog",
            &catalog_arg,
            "--coverage-out",
            &coverage_arg,
            "--envelope-out",
            &envelope_arg,
        ])
        .output()
        .expect("republish clean artifacts");
    assert_eq!(republish.status.code(), Some(0));
    let mut coverage_drift = fs::read(&coverage_out).unwrap();
    coverage_drift.push(b'\n');
    fs::write(&coverage_out, &coverage_drift).unwrap();
    let coverage_check = Command::new(BIN)
        .args([
            "--manifest",
            &manifest_arg,
            "--catalog",
            &catalog_arg,
            "--coverage-out",
            &coverage_arg,
            "--envelope-out",
            &envelope_arg,
            "--check",
        ])
        .output()
        .expect("run bin in check mode after coverage drift");
    assert_eq!(coverage_check.status.code(), Some(i32::from(EXIT_DRIFT)));

    // Library-level missing artifact refusal.
    let coverage =
        render_coverage_json(&build_anchor_coverage(&manifest, &catalog).unwrap()).expect("render");
    assert!(!coverage.is_empty());
    let absent_out = dir.path().join("absent-coverage.json");
    let error = verify_artifacts(
        &build_anchor_coverage(&manifest, &catalog).unwrap(),
        &absent_out,
        &envelope_out,
    )
    .expect_err("missing coverage artifact must fail closed");
    assert_eq!(error.operation(), "check-missing");
}

#[test]
fn double_render_is_deterministic() {
    let dir = TempDir::new("determinism");
    let (manifest, catalog) = standard_fixture(dir.path());
    let first = build_anchor_coverage(&manifest, &catalog).expect("first build");
    let second = build_anchor_coverage(&manifest, &catalog).expect("second build");
    assert_eq!(
        render_coverage_json(&first).unwrap(),
        render_coverage_json(&second).unwrap()
    );
    assert_eq!(
        render_envelope_jsonl(&first).unwrap(),
        render_envelope_jsonl(&second).unwrap()
    );
}

#[test]
fn argv_requires_all_four_paths() {
    let parsed = parse_coverage_args(
        [
            "--manifest",
            "m.jsonl",
            "--catalog",
            "c.sqlite",
            "--coverage-out",
            "cov.json",
            "--envelope-out",
            "env.jsonl",
            "--check",
        ]
        .into_iter()
        .map(str::to_owned),
    )
    .expect("complete argv parses");
    assert!(parsed.check);
    assert_eq!(parsed.manifest, "m.jsonl");

    let missing = parse_coverage_args(["--manifest", "m.jsonl"].into_iter().map(str::to_owned))
        .expect_err("missing paths are refused");
    assert!(
        missing.contains("--catalog"),
        "detail names the missing flag"
    );
    let unknown =
        parse_coverage_args(["--wat"].into_iter().map(str::to_owned)).expect_err("unknown flag");
    assert!(unknown.contains("--wat"));
}

#[test]
fn manifest_fail_closed_refusals() {
    let expect_op = |text: &str, operation: &str| {
        let error = parse_corpus_manifest(text).expect_err("manifest must be refused");
        assert_eq!(error.operation(), operation, "text: {text:.80}");
    };

    // Header without counts.entries.
    expect_op(
        "{\"schema\":\"m223-s02-corpus-inventory/v1\",\"inventory_digest\":\"sha256:d\"}\n",
        "manifest-parse",
    );
    // Foreign schema.
    expect_op(
        "{\"schema\":\"other/v1\",\"counts\":{\"entries\":0},\"inventory_digest\":\"sha256:d\"}\n",
        "manifest-parse",
    );
    // Duplicate path.
    expect_op(
        &format!(
            "{}{}{}",
            manifest_text(&[("a.xml", 1)]).lines().next().unwrap(),
            "\n",
            manifest_text(&[("a.xml", 1), ("a.xml", 1)])
                .lines()
                .skip(1)
                .collect::<Vec<_>>()
                .join("\n")
        ),
        "manifest-duplicate-path",
    );
    // Body count disagrees with header.
    let mut mismatch = manifest_text(&[("a.xml", 1), ("b.xml", 2)]);
    mismatch = mismatch.replacen("\"entries\":2", "\"entries\":3", 1);
    expect_op(&mismatch, "manifest-count-mismatch");
    // Unsafe and escaped paths.
    for path in ["../x.xml", "/abs.xml", "a//b.xml", "a\\b.xml", "./a.xml"] {
        expect_op(&manifest_text(&[(path, 1)]), "manifest-unsafe-path");
    }
    // Non-ASCII path.
    expect_op(&manifest_text(&[("npa/Ф.xml", 1)]), "manifest-unsafe-path");
    // Missing / malformed record fields.
    expect_op(
        &format!(
            "{}\n{{\"relative_path\":\"a.xml\",\"bytes\":1}}\n",
            manifest_text(&[]).lines().next().unwrap()
        ),
        "manifest-parse",
    );
    expect_op(
        &format!(
            "{}\n{{\"relative_path\":\"a.xml\",\"sha256\":\"sha256:zz\",\"bytes\":1}}\n",
            manifest_text(&[]).lines().next().unwrap()
        ),
        "manifest-parse",
    );
    // Blank line between records.
    expect_op(
        &format!(
            "{}\n{}\n\n",
            manifest_text(&[("a.xml", 1)]).lines().next().unwrap(),
            manifest_text(&[("a.xml", 1)]).lines().nth(1).unwrap()
        ),
        "manifest-parse",
    );
}

#[test]
fn build_refuses_missing_inputs() {
    let dir = TempDir::new("missing-inputs");
    let manifest = write_manifest(dir.path(), &RECORDS);
    let missing_catalog = dir.path().join("absent.sqlite");
    let error = build_anchor_coverage(&manifest, &missing_catalog)
        .expect_err("missing catalog fails closed");
    assert_eq!(error.operation(), "catalog-open");

    let missing_manifest = dir.path().join("absent.jsonl");
    let catalog = seed_catalog(dir.path(), &[]);
    let error = build_anchor_coverage(&missing_manifest, &catalog)
        .expect_err("missing manifest fails closed");
    assert_eq!(error.operation(), "manifest-read");
}

#[test]
fn catalog_anchor_error_is_bounded_and_typed() {
    let error = AnchorCoverageError::new("test", "x".repeat(400));
    assert!(error.detail().chars().count() <= 240);
    assert_eq!(anchor_coverage::exit_code_for(&error), 3);
}
