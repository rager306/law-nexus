//! S07/T03 contract suite for the `frbr-bridge` bin + tracked mapping artifact.
//!
//! Exercises the real CLI on hermetic fixtures (a seeded read-only catalog plus
//! canonical envelope/receipt/timeline files) and asserts each fail-closed exit
//! branch is *executed*, not merely declared:
//!
//! - exit 2 — argv grammar (unknown flag, empty value);
//! - exit 3 — an unreadable required input / pin file / `--check` artifact;
//! - exit 4 — the `--out` artifact is not writable;
//! - exit 5 — the join refuses (catalog miss, anchor byte mismatch);
//! - exit 6 — `--check` byte drift.
//!
//! Plus byte-identical write→check idempotency and an in-process deterministic
//! ASCII render. A corpus-gated case re-runs `--check` over the tracked
//! artifact and the `consru_export` catalog; it skips (never false-passes) when
//! the gitignored corpus or the release binary are absent.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::frbr_bridge::{
    EXIT_DRIFT, EXIT_INPUT, EXIT_JOIN_REFUSED, EXIT_OUT_UNWRITABLE, EXIT_USAGE,
    FRBR_BRIDGE_NON_CLAIMS, parse_bridge_args,
};
use ln_consultant_parser::{
    DEFAULT_ACT_NUMBER, DEFAULT_EDITION_PREFIX, EditionJoinRow, FrbrBridgePins,
    build_frbr_bridge_join_from_bytes, exports_path, render_frbr_bridge_json,
};
use ln_decode::consultant_uri_anchor::ConsultantUriAnchor;
use ln_decode::identity_envelope::IdentityEnvelope;
use rusqlite::{Connection, OpenFlags};

const BIN: &str = env!("CARGO_BIN_EXE_frbr-bridge");
const PREFIX: &str = DEFAULT_EDITION_PREFIX;
const SHA_A: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const SHA_B: &str = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210";

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
            "ln-frbr-bridge-{}-{}-{}-{label}",
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

fn token(n: u32) -> String {
    format!("consultantplus://offline/ref=FIXTURE{n:04}TOKEN")
}

fn edition_path(n: u32, rev: &str) -> String {
    format!("{PREFIX}{n:04}_rev-{rev}_from-unknown_00000000.xml")
}

fn envelope_header(entries: u64, anchored: u64) -> String {
    format!(
        "{{\"schema\":\"m224-s02-identity-envelope/v1\",\"kind\":\"identity_envelope_header\",\
         \"counts\":{{\"entries\":{entries},\"anchored\":{anchored},\"unresolved\":0}},\
         \"r1000_status\":\"active/unclosed\"}}\n"
    )
}

fn envelope_line(path: &str, sha_hex: &str, bytes: u64, token: &str) -> String {
    let anchor = ConsultantUriAnchor::parse(token).expect("fixture anchor parses");
    IdentityEnvelope::anchored(path, format!("sha256:{sha_hex}"), bytes, anchor).render_jsonl_line()
}

fn receipt_line(path: &str, sha_hex: &str) -> String {
    format!(
        "{{\"schema\":\"m223-s07-consumer-receipt/v1\",\"relative_path\":\"{path}\",\
         \"counts\":{{\"identity\":{{\"document_version_ref\":\"m223-s07-corpus/v1\",\
         \"source_revision\":\"{sha_hex}\",\"decoder_profile\":\"source_package_decoded_text/v1\",\
         \"source_sha256\":\"{sha_hex}\",\"parent_schema\":\"law-nexus/cleaned-projection/v1\"}}}}}}\n"
    )
}

fn timeline_json(points: &[(i64, i64)]) -> String {
    let items: Vec<String> = points
        .iter()
        .map(|(number, day)| format!("{{\"edition_number\":{number},\"effect_day\":{day}}}"))
        .collect();
    format!(
        "{{\"schema\":\"m224-s06-edition-timeline/v1\",\"per_edition\":[{}]}}\n",
        items.join(",")
    )
}

/// A hermetic two-edition fixture: tracked-shape inputs on disk, a seeded
/// read-only catalog, and pin-source files for the ontology/registry/binary.
struct Fixture {
    envelope: PathBuf,
    receipts: PathBuf,
    catalog: PathBuf,
    timeline: PathBuf,
    ontology: PathBuf,
    registry: PathBuf,
    binary: PathBuf,
}

fn seed_catalog(path: &Path, anchor_override: Option<&str>, drop_number: Option<i64>) {
    let connection = Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE,
    )
    .expect("writable fixture connection");
    connection
        .execute_batch(
            "CREATE TABLE editions (
                edition_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                document_id TEXT,
                document_type TEXT,
                document_date TEXT,
                number TEXT,
                revision_date TEXT,
                edition_number INTEGER,
                relative_path TEXT
            );",
        )
        .expect("create observed catalog schema");
    for (number, rev) in [(1_i64, "initial"), (2, "2013-04-05")] {
        if drop_number == Some(number) {
            continue;
        }
        let path = edition_path(number as u32, rev);
        let anchor = match (number, anchor_override) {
            (2, Some(override_token)) => override_token.to_owned(),
            _ => token(number as u32),
        };
        connection
            .execute(
                "INSERT INTO editions (
                    edition_id, source_id, document_id, document_type, document_date, number,
                    revision_date, edition_number, relative_path
                 ) VALUES (?1, ?2, ?3, 'zakon', '2013-04-05', 'NUM', '2013-04-05', ?4, ?5)",
                rusqlite::params![
                    format!("edition-fixture-{number:04}"),
                    anchor,
                    format!("doc-fixture-{number:04}"),
                    number,
                    exports_path(&path)
                ],
            )
            .expect("insert edition row");
    }
    drop(connection);
}

fn write_fixture(dir: &Path, anchor_override: Option<&str>, drop_number: Option<i64>) -> Fixture {
    let p1 = edition_path(1, "initial");
    let p2 = edition_path(2, "2013-04-05");

    let mut envelope = envelope_header(2, 2);
    envelope.push_str(&envelope_line(&p1, SHA_A, 100, &token(1)));
    envelope.push_str(&envelope_line(&p2, SHA_B, 200, &token(2)));

    let mut receipts = String::new();
    receipts.push_str(&receipt_line(&p1, SHA_A));
    receipts.push_str(&receipt_line(&p2, SHA_B));

    let timeline = timeline_json(&[(1, 77891), (2, 77892)]);

    let envelope_path = dir.join("envelope.jsonl");
    let receipts_path = dir.join("receipts.jsonl");
    let timeline_path = dir.join("timeline.json");
    let catalog_path = dir.join("catalog.sqlite");
    let ontology_path = dir.join("kb-ontology.yaml");
    let registry_path = dir.join("kb-hierarchy-registry.yaml");
    let binary_path = dir.join("frbr-bridge.bin");

    fs::write(&envelope_path, envelope).unwrap();
    fs::write(&receipts_path, receipts).unwrap();
    fs::write(&timeline_path, timeline).unwrap();
    fs::write(&ontology_path, "ontology: fixture\n").unwrap();
    fs::write(&registry_path, "works: fixture\n").unwrap();
    fs::write(&binary_path, b"fixture-binary-bytes\n").unwrap();
    seed_catalog(&catalog_path, anchor_override, drop_number);

    Fixture {
        envelope: envelope_path,
        receipts: receipts_path,
        catalog: catalog_path,
        timeline: timeline_path,
        ontology: ontology_path,
        registry: registry_path,
        binary: binary_path,
    }
}

fn cli_args(fixture: &Fixture, out: &Path) -> Vec<String> {
    vec![
        "--envelope".to_owned(),
        fixture.envelope.display().to_string(),
        "--receipts".to_owned(),
        fixture.receipts.display().to_string(),
        "--catalog".to_owned(),
        fixture.catalog.display().to_string(),
        "--timeline".to_owned(),
        fixture.timeline.display().to_string(),
        "--ontology".to_owned(),
        fixture.ontology.display().to_string(),
        "--registry".to_owned(),
        fixture.registry.display().to_string(),
        "--binary".to_owned(),
        fixture.binary.display().to_string(),
        "--out".to_owned(),
        out.display().to_string(),
    ]
}

fn run(args: &[String]) -> Output {
    Command::new(BIN)
        .args(args)
        .output()
        .expect("run the frbr-bridge bin")
}

fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

// ---------------------------------------------------------------------------
// Library-level: deterministic, ASCII, closed-vocabulary render.
// ---------------------------------------------------------------------------

fn in_memory_catalog() -> BTreeMap<String, EditionJoinRow> {
    let mut map = BTreeMap::new();
    for (number, rev) in [(1_i64, "initial"), (2, "2013-04-05")] {
        let path = edition_path(number as u32, rev);
        map.insert(
            path.clone(),
            EditionJoinRow {
                relative_path: exports_path(&path),
                source_id: token(number as u32),
                edition_id: Some(format!("edition-fixture-{number:04}")),
                document_id: Some("doc-fixture-000000000000000000".to_owned()),
                edition_number: Some(number),
                revision_date: None,
            },
        );
    }
    map
}

fn fixture_pins() -> FrbrBridgePins {
    FrbrBridgePins {
        envelope_path: "envelope.jsonl".to_owned(),
        envelope_sha256: format!("sha256:{SHA_A}"),
        receipts_path: "receipts.jsonl".to_owned(),
        receipts_sha256: format!("sha256:{SHA_B}"),
        timeline_path: "timeline.json".to_owned(),
        timeline_sha256: format!("sha256:{SHA_A}"),
        ontology_path: "kb-ontology.yaml".to_owned(),
        ontology_sha256: format!("sha256:{SHA_A}"),
        registry_path: "kb-hierarchy-registry.yaml".to_owned(),
        registry_sha256: format!("sha256:{SHA_A}"),
        catalog_path: "catalog.sqlite".to_owned(),
        catalog_sha256: format!("sha256:{SHA_B}"),
        consumer_binary_path: "target/release/frbr-bridge".to_owned(),
        consumer_binary_sha256: format!("sha256:{SHA_B}"),
    }
}

#[test]
fn hermetic_render_is_deterministic_ascii_and_closed() {
    let p1 = edition_path(1, "initial");
    let p2 = edition_path(2, "2013-04-05");
    let mut envelope = envelope_header(2, 2);
    envelope.push_str(&envelope_line(&p1, SHA_A, 100, &token(1)));
    envelope.push_str(&envelope_line(&p2, SHA_B, 200, &token(2)));
    let receipts = format!("{}{}", receipt_line(&p1, SHA_A), receipt_line(&p2, SHA_B));
    let timeline = timeline_json(&[(1, 77891), (2, 77892)]);

    let build = || {
        build_frbr_bridge_join_from_bytes(
            DEFAULT_ACT_NUMBER,
            PREFIX,
            envelope.as_bytes(),
            receipts.as_bytes(),
            timeline.as_bytes(),
            &in_memory_catalog(),
        )
        .expect("hermetic join succeeds")
    };
    let pins = fixture_pins();
    let first = render_frbr_bridge_json(&build(), &pins).expect("first render");
    let second = render_frbr_bridge_json(&build(), &pins).expect("second render");

    assert_eq!(first, second, "render must be deterministic");
    assert!(first.is_ascii(), "mapping artifact payload must be ASCII");
    for claim in FRBR_BRIDGE_NON_CLAIMS {
        assert!(
            first.contains(claim),
            "the render must carry non-claim {claim}"
        );
    }
    assert!(first.contains("\"schema\": \"m224-s07-frbr-bridge/v1\""));
    assert!(first.contains("\"expressions\": 2"));
    assert!(first.contains("\"distinct_effect_days\": 2"));
    assert!(first.contains("\"distinct_anchors\": 2"));
    assert!(first.contains("\"join_mismatches\": 0"));
    assert!(first.contains("urn:lex:ru:federal:zakon:2013-04-05;44-fz@2013-04-06"));
    assert!(first.contains("\"r1000_status\": \"active/unclosed\""));
    // The `per_expression` rows must not carry a per-row work id: one Work is
    // declared once at the top level.
    assert_eq!(first.matches("\"expression_eli_urn\"").count(), 2);
}

#[test]
fn parse_bridge_args_is_strict_and_defaults_are_tracked() {
    assert!(parse_bridge_args(Vec::<String>::new()).is_ok());
    let parsed = parse_bridge_args(vec!["--check".to_owned()]).expect("flag only");
    assert!(parsed.check);
    assert_eq!(
        parsed.out,
        ln_consultant_parser::DEFAULT_OUT_PATH,
        "the bare binary must target the tracked artifact"
    );

    assert!(parse_bridge_args(vec!["--bogus".to_owned()]).is_err());
    assert!(parse_bridge_args(vec!["--out".to_owned()]).is_err());
    assert!(parse_bridge_args(vec!["--out".to_owned(), String::new()]).is_err());
}

// ---------------------------------------------------------------------------
// CLI-level: fail-closed exit codes (2/3/4/5/6), executed for real.
// ---------------------------------------------------------------------------

#[test]
fn usage_errors_exit_2() {
    for args in [
        vec!["--bogus".to_owned()],
        vec!["--out".to_owned()],
        vec!["--envelope".to_owned(), String::new()],
    ] {
        let output = run(&args);
        assert_eq!(
            output.status.code(),
            Some(i32::from(EXIT_USAGE)),
            "argv {args:?} must be a usage error"
        );
    }
}

#[test]
fn missing_input_exits_3() {
    let dir = TempDir::new("missing-input");
    let out = dir.path().join("out.json");

    // A missing envelope is an unreadable input, not a join refusal.
    let mut args = cli_args(&write_fixture(dir.path(), None, None), &out);
    let envelope_index = args
        .iter()
        .position(|arg| arg == "--envelope")
        .expect("envelope flag")
        + 1;
    args[envelope_index] = dir
        .path()
        .join("absent-envelope.jsonl")
        .display()
        .to_string();
    assert_eq!(
        run(&args).status.code(),
        Some(i32::from(EXIT_INPUT)),
        "a missing input is the input exit class"
    );

    // A missing pin source (the ontology) is the same class.
    let dir2 = TempDir::new("missing-pin");
    let fixture = write_fixture(dir2.path(), None, None);
    let mut args = cli_args(&fixture, &out);
    let ontology_index = args
        .iter()
        .position(|arg| arg == "--ontology")
        .expect("ontology flag")
        + 1;
    args[ontology_index] = dir2
        .path()
        .join("absent-ontology.yaml")
        .display()
        .to_string();
    assert_eq!(run(&args).status.code(), Some(i32::from(EXIT_INPUT)));

    // `--check` against a missing artifact is an unreadable artifact.
    let dir3 = TempDir::new("missing-check");
    let fixture = write_fixture(dir3.path(), None, None);
    let mut args = cli_args(&fixture, &dir3.path().join("absent-out.json"));
    args.push("--check".to_owned());
    assert_eq!(run(&args).status.code(), Some(i32::from(EXIT_INPUT)));
}

#[test]
fn out_unwritable_exits_4() {
    let dir = TempDir::new("out-unwritable");
    let fixture = write_fixture(dir.path(), None, None);
    // The parent directory does not exist, so the write fails closed.
    let out = dir.path().join("no-such-subdir").join("out.json");
    let args = cli_args(&fixture, &out);
    assert_eq!(
        run(&args).status.code(),
        Some(i32::from(EXIT_OUT_UNWRITABLE)),
        "an unwritable --out is the output exit class"
    );
    assert!(!out.exists());
}

#[test]
fn join_refusal_exits_5() {
    // Catalog miss: the second edition has no catalog row.
    let dir = TempDir::new("catalog-miss");
    let fixture = write_fixture(dir.path(), None, Some(2));
    let out = dir.path().join("out.json");
    assert_eq!(
        run(&cli_args(&fixture, &out)).status.code(),
        Some(i32::from(EXIT_JOIN_REFUSED)),
        "a catalog miss must refuse, not publish a partial mapping"
    );

    // Anchor byte mismatch: the catalog source_id differs from the envelope.
    let dir = TempDir::new("anchor-mismatch");
    let fixture = write_fixture(dir.path(), Some(&token(999)), None);
    let out = dir.path().join("out.json");
    assert_eq!(
        run(&cli_args(&fixture, &out)).status.code(),
        Some(i32::from(EXIT_JOIN_REFUSED))
    );
    assert!(!out.exists(), "a refusal never publishes an artifact");
}

#[test]
fn write_then_check_is_byte_identical_and_drift_exits_6() {
    let dir = TempDir::new("check");
    let fixture = write_fixture(dir.path(), None, None);
    let out = dir.path().join("out.json");

    let write = run(&cli_args(&fixture, &out));
    assert_eq!(write.status.code(), Some(0), "write mode exits clean");
    assert!(out.exists());
    let clean = fs::read(&out).unwrap();
    assert!(clean.is_ascii());

    let mut check_args = cli_args(&fixture, &out);
    check_args.push("--check".to_owned());
    let check = run(&check_args);
    assert_eq!(check.status.code(), Some(0), "check mode byte-identity");
    let stdout = String::from_utf8_lossy(&check.stdout);
    assert!(
        stdout.contains("check=ok expressions=2 distinct_effect_days=2 divergence=1"),
        "unexpected check message: {stdout}"
    );

    // Re-render from scratch into a second path: byte-identical (idempotent).
    let out2 = dir.path().join("out2.json");
    assert_eq!(run(&cli_args(&fixture, &out2)).status.code(), Some(0));
    assert_eq!(
        fs::read(&out2).unwrap(),
        clean,
        "re-render is byte-identical"
    );

    // Plant one byte: the check must fail closed and never rewrite.
    let mut drifted = clean.clone();
    drifted.push(b'x');
    fs::write(&out, &drifted).unwrap();
    let drift = run(&check_args);
    assert_eq!(drift.status.code(), Some(i32::from(EXIT_DRIFT)));
    assert_eq!(fs::read(&out).unwrap(), drifted, "check never writes");
}

// ---------------------------------------------------------------------------
// Corpus-gated: the tracked artifact re-renders byte-identical.
// ---------------------------------------------------------------------------

#[test]
fn tracked_artifact_re_renders_byte_identical() {
    let root = workspace_root();
    let out = root.join("prd/migration/rust-evidence/m224-s07-frbr-bridge.json");
    let catalog = root.join("consru_export/consru_export/catalog.sqlite");
    let binary = root.join("target/release/frbr-bridge");
    if !out.exists() || !catalog.exists() || !binary.exists() {
        eprintln!("SKIP: tracked artifact, catalog or release binary not available");
        return;
    }

    // Defaults are repo-relative, so run from the workspace root; this is
    // exactly the published `--check` surface.
    let check = Command::new(BIN)
        .current_dir(&root)
        .arg("--check")
        .output()
        .expect("run the tracked-artifact check");
    assert_eq!(
        check.status.code(),
        Some(0),
        "the tracked artifact must re-render byte-identical: {}",
        String::from_utf8_lossy(&check.stderr)
    );
    let stdout = String::from_utf8_lossy(&check.stdout);
    assert!(
        stdout.contains("check=ok expressions=118 distinct_effect_days=118 divergence=46"),
        "unexpected check message: {stdout}"
    );
}
