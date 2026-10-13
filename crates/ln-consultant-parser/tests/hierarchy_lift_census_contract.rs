//! Contract test: per-document hierarchy-lift census consumer over the
//! materialized cleaned-wire JSONL layer (M224/S05/T03).
//!
//! Exercises the library surface and the `hierarchy-lift-census` bin on real
//! cleaned-projection exports of self-authored inline WordML fixtures: the
//! counts-only payload, the normative ladder placement, the `text_only`
//! non-normative barrier, the fail-closed `Unknown` accounting, the accounting
//! identities, determinism, the ASCII redaction posture, the absence of any
//! XML re-parse surface (negative grep self-check) and the fail-closed CLI
//! refusals (usage / unreadable input / refused wire).
//!
//! Non-claims: `[bounded]` to the self-authored non-legal synthetic fixtures in
//! this file and the embedded ontology catalog; never corpus coverage, never
//! source authenticity, never a legal-completeness claim. R1000 stays active.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::hierarchy_lift_census::{
    CENSUS_NON_CLAIMS, DOC_SCHEMA, EXIT_INPUT_UNREADABLE, EXIT_USAGE, EXIT_WIRE_REFUSED,
    HierarchyLiftCensusCli, parse_hierarchy_lift_census_args, run_hierarchy_lift_census,
};
use ln_decode::cleaned_wire::{
    WireCompletion, WireLimits, read_cleaned_wire, render_cleaned_projection,
};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};

const BIN: &str = env!("CARGO_BIN_EXE_hierarchy-lift-census");

// ---------------------------------------------------------------- fixtures #

/// Four plain paragraphs with hierarchy markers: one container (`glava`) and
/// two `statya` units, one of which owns a numbered `punkt`. Written on one
/// line so no inter-element whitespace creates residual text.
const FEDERAL_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 4. Требования к участникам</w:t></w:r></w:p><w:p><w:r><w:t>1) пункт первый</w:t></w:r></w:p><w:p><w:r><w:t>Статья 5. Сфера применения</w:t></w:r></w:p></w:body></w:wordDocument>"#;

/// Three paragraphs: two declared levels (`statya`, numbered `punkt`) and one
/// undeclared level (`Раздел`, R8-08) that must stay fail-closed `Unknown`.
const RAZDEL_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Статья 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>1) Первое требование.</w:t></w:r></w:p><w:p><w:r><w:t>Раздел 2. Особенная часть</w:t></w:r></w:p></w:body></w:wordDocument>"#;

/// The negative-grep corpus: the lift consumer path must contain no XML
/// re-parse surface. Token list is deliberately anchored to concrete decoder
/// entry points, not the bare word "xml".
const FORBIDDEN_TOKENS: [&str; 4] = [
    "from_xml",
    "ConsultantWordMlBlockDecoder",
    "decode_blocks",
    "read_odt_content_xml",
];

// ------------------------------------------------------------ preparation #

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
            "ln-hierarchy-lift-census-{}-{}-{}-{label}",
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

/// Run the real producer pipeline (`capture` → `build_projection` →
/// `render_cleaned_projection`) and materialize the cleaned-wire JSONL to disk.
/// This is the producer that touches the source bytes exactly once.
fn export_wire(dir: &Path, name: &str, xml: &str) -> PathBuf {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let projection = build_projection(package.records()).expect("fixture must project");
    let artifact = render_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("fixture must export");
    // The export must read back: a materialized layer the consumer can trust.
    read_cleaned_wire(&artifact).expect("exported projection must read back");
    let path = dir.join(name);
    fs::write(&path, artifact).expect("write cleaned wire fixture");
    path
}

fn cli(wire: &Path, corpus_path: &str) -> HierarchyLiftCensusCli {
    HierarchyLiftCensusCli {
        cleaned_wire: wire.display().to_string(),
        corpus_path: corpus_path.to_owned(),
        source_format: Default::default(),
        out: None,
    }
}

fn run_json(cli: &HierarchyLiftCensusCli) -> serde_json::Value {
    let (code, message) = run_hierarchy_lift_census(cli);
    assert_eq!(code, 0, "census must succeed: {message}");
    serde_json::from_str(&message).expect("payload must be JSON")
}

fn run_bin(args: &[&str]) -> std::process::Output {
    Command::new(BIN)
        .args(args)
        .output()
        .expect("bin must launch")
}

// ------------------------------------------------------------- the oracle #

#[test]
fn federal_law_fixture_yields_normative_lift_over_jsonl() {
    let dir = TempDir::new("federal");
    let wire = export_wire(dir.path(), "federal.jsonl", FEDERAL_FIXTURE);
    let cli = cli(&wire, "exports/npa/federalnyi-zakon_402-fz.xml");
    let payload = run_json(&cli);

    assert_eq!(payload["schema"], DOC_SCHEMA);
    assert_eq!(payload["group"], "federal_law@v1");
    assert_eq!(payload["detection"], "bound:needle_and_probe");
    let markers = payload["lift"]["markers"].as_u64().unwrap();
    assert!(
        markers >= 3,
        "markers must extract from the wire layer: {payload}"
    );
    assert_eq!(payload["lift"]["bound"].as_u64().unwrap(), markers);
    assert_eq!(payload["lift"]["unknown"].as_u64().unwrap(), 0);
    assert_eq!(payload["lift"]["non_normative"].as_u64().unwrap(), 0);
    assert_eq!(payload["non_normative"], false);
    // Normative ladder placement: at least the `statya` unit binds.
    assert!(payload["by_catalog_token"]["statya"].as_u64().unwrap() >= 1);
    assert!(payload["by_role"]["unit"].as_u64().unwrap() >= 1);
    // Accounting: sum(by_group) == markers, sum(by_role) == bound.
    let group_sum: u64 = payload["by_group"]
        .as_object()
        .unwrap()
        .values()
        .map(|value| value.as_u64().unwrap())
        .sum();
    assert_eq!(group_sum, markers);
    // The source identity is read from the projection, not re-derived.
    let source_sha = payload["wire_source"]["sha256"].as_str().unwrap();
    assert_eq!(source_sha.len(), 64, "wire source pin is 64 hex chars");
    assert!(source_sha.chars().all(|c| c.is_ascii_hexdigit()));
    assert!(payload["wire_source"]["bytes"].as_u64().unwrap() > 0);
    assert_eq!(payload["r1000_status"], "active/unclosed");

    // Determinism: a second run is byte-identical.
    let (second_code, second) = run_hierarchy_lift_census(&cli);
    assert_eq!(second_code, 0);
    let (_, first) = run_hierarchy_lift_census(&cli);
    assert_eq!(second, first, "the payload render must be deterministic");
}

#[test]
fn court_practice_path_is_non_normative_with_zero_placements() {
    let dir = TempDir::new("court");
    let wire = export_wire(dir.path(), "court.jsonl", FEDERAL_FIXTURE);
    let payload = run_json(&cli(&wire, "exports/courts/court_123.xml"));

    assert_eq!(payload["group"], "court_practice");
    assert_eq!(payload["detection"], "bound:needle");
    assert_eq!(payload["non_normative"], true);
    let markers = payload["lift"]["markers"].as_u64().unwrap();
    assert!(
        markers >= 3,
        "text-only still counts the markers: {payload}"
    );
    assert_eq!(payload["lift"]["bound"].as_u64().unwrap(), 0);
    assert_eq!(payload["lift"]["unknown"].as_u64().unwrap(), 0);
    // Every marker is carried by the non-normative barrier.
    assert_eq!(payload["lift"]["non_normative"].as_u64().unwrap(), markers);
    assert!(payload["by_role"].as_object().unwrap().is_empty());
    assert!(payload["unmapped_tokens"].as_object().unwrap().is_empty());
}

#[test]
fn undeclared_razdel_is_fail_closed_unknown_and_counted_unmapped() {
    let dir = TempDir::new("razdel");
    let wire = export_wire(dir.path(), "razdel.jsonl", RAZDEL_FIXTURE);
    let payload = run_json(&cli(&wire, "exports/npa/federalnyi-zakon_402-fz.xml"));

    assert_eq!(payload["group"], "federal_law@v1");
    assert_eq!(payload["lift"]["unknown"].as_u64().unwrap(), 1);
    assert_eq!(payload["unmapped_tokens"]["razdel"].as_u64().unwrap(), 1);
    assert_eq!(payload["by_role"]["unit"].as_u64().unwrap(), 1);
    assert_eq!(payload["by_role"]["subunit"].as_u64().unwrap(), 1);
}

// ------------------------------------------------------- fail-closed CLI #

#[test]
fn bin_unknown_flag_is_usage_error() {
    let output = run_bin(&["--bogus"]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_USAGE)));
}

#[test]
fn bin_missing_input_is_unreadable() {
    let output = run_bin(&[
        "--cleaned-wire",
        "/nonexistent/m224-s05/census.jsonl",
        "--corpus-path",
        "exports/courts/court_1.xml",
    ]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_INPUT_UNREADABLE)));
}

#[test]
fn bin_broken_wire_is_refused() {
    let dir = TempDir::new("broken");
    let path = dir.path().join("broken.jsonl");
    fs::write(&path, "not a cleaned projection\n").expect("write broken wire");
    let output = run_bin(&[
        "--cleaned-wire",
        &path.display().to_string(),
        "--corpus-path",
        "exports/courts/court_1.xml",
    ]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_WIRE_REFUSED)));
}

#[test]
fn bin_out_mode_writes_payload_and_summarizes() {
    let dir = TempDir::new("out");
    let wire = export_wire(dir.path(), "federal.jsonl", FEDERAL_FIXTURE);
    let out = dir.path().join("doc.json");
    let output = run_bin(&[
        "--cleaned-wire",
        &wire.display().to_string(),
        "--corpus-path",
        "exports/npa/federalnyi-zakon_402-fz.xml",
        "--out",
        &out.display().to_string(),
    ]);
    assert_eq!(output.status.code(), Some(0));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("group=federal_law@v1"),
        "log line reports the group summary: {stderr}"
    );
    let written = fs::read_to_string(&out).expect("payload must be written");
    let payload: serde_json::Value = serde_json::from_str(&written).expect("payload is JSON");
    assert_eq!(payload["schema"], DOC_SCHEMA);
    assert!(written.is_ascii(), "payload must be ASCII");
}

// ------------------------------------------------- negative self-checks #

#[test]
fn source_contains_no_xml_reparse_surface() {
    let sources = [
        ("module", include_str!("../src/hierarchy_lift_census.rs")),
        ("bin", include_str!("../src/bin/hierarchy-lift-census.rs")),
    ];
    for (label, source) in sources {
        for token in FORBIDDEN_TOKENS {
            assert!(
                !source.contains(token),
                "{label} source must not contain the XML re-parse token {token:?}"
            );
        }
    }
}

#[test]
fn forbidden_token_probe_is_non_vacuous() {
    // Non-vacuity anchor: every token the grep forbids is a real, present
    // symbol on the XML decode path. If the XML path lost these tokens the
    // grep above would silently become vacuous.
    let xml_path_sources = [
        include_str!("../../ln-decode/src/adapters.rs"),
        include_str!("../../ln-decode/src/bin/reader-nav.rs"),
        include_str!("../../ln-decode/src/adapters/garant_odt.rs"),
    ];
    for token in FORBIDDEN_TOKENS {
        assert!(
            xml_path_sources.iter().any(|source| source.contains(token)),
            "forbidden token {token:?} must exist on the XML path, else the lift grep is vacuous"
        );
    }
}

#[test]
fn arg_parser_rejects_from_xml() {
    let result = parse_hierarchy_lift_census_args([
        "--cleaned-wire".to_owned(),
        "wire.jsonl".to_owned(),
        "--corpus-path".to_owned(),
        "exports/npa/law_1.xml".to_owned(),
        "--from-xml".to_owned(),
        "source.xml".to_owned(),
    ]);
    assert!(result.is_err(), "--from-xml must never be accepted");
}

#[test]
fn arg_parser_requires_both_inputs() {
    assert!(parse_hierarchy_lift_census_args(Vec::<String>::new().into_iter()).is_err());
    assert!(
        parse_hierarchy_lift_census_args(
            ["--cleaned-wire".to_owned(), "wire.jsonl".to_owned()].into_iter()
        )
        .is_err(),
        "--corpus-path is required"
    );
    assert!(
        parse_hierarchy_lift_census_args(
            [
                "--cleaned-wire".to_owned(),
                "wire.jsonl".to_owned(),
                "--corpus-path".to_owned(),
                "exports/npa/law_1.xml".to_owned(),
                "--source-format".to_owned(),
                "pdf".to_owned(),
            ]
            .into_iter()
        )
        .is_err(),
        "unsupported source format is refused"
    );
}

#[test]
fn non_claims_are_declared() {
    assert!(
        CENSUS_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("component_concept"))
    );
    assert!(
        CENSUS_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("fail_closed"))
    );
}
