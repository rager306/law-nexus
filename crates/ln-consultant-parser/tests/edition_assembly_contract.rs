//! Contract test: corpus single-edition assembly consumer over the materialized
//! cleaned-wire JSONL layer (M224/S06/T01).
//!
//! Exercises the library surface and the `edition-timeline` bin on real
//! cleaned-projection exports of self-authored inline WordML fixtures and on
//! the tracked 402-FZ fixture: the counts-only `edition-assembly/v1` payload,
//! the assembly FSM over a synthetic registry map, drift detection, the
//! accounting identity, determinism, the ASCII redaction posture, the absence
//! of any XML re-parse surface (negative grep self-check) and the fail-closed
//! CLI refusals (usage / unreadable input / refused wire / unimplemented mode).
//!
//! Non-claims: `[bounded]` to the self-authored non-legal synthetic fixtures and
//! the tracked fixture in this file; never corpus coverage, never source
//! authenticity, never a legal-completeness claim. R1000 stays active.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::edition_timeline::{
    ASSEMBLY_NON_CLAIMS, ASSEMBLY_SCHEMA, AssemblyMode, EXIT_INPUT_UNREADABLE, EXIT_USAGE,
    EXIT_WIRE_REFUSED, EditionTimelineCli, assemble_edition, markers_from_cleaned_wire,
    parse_edition_timeline_args, run_edition_timeline,
};
use ln_decode::cleaned_wire::{WireCompletion, WireLimits, render_cleaned_projection};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};
use ln_kb_ontology::domain::{HierarchyBinding, HierarchyMap};
use ln_temporal::domain::ComponentConceptId;

const BIN: &str = env!("CARGO_BIN_EXE_edition-timeline");

/// Corpus-relative path of the 44-FZ edition-0118 export (gitignored [smoke]).
const CORPUS_44FZ_REL: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml";

/// Tracked 402-FZ Consultant WordML fixture (repository-relative).
const TRACKED_402: &str = "law-source/consultant/federalnyi-zakon-ot-06-12-2011-n-402-fz-red-ot-15-12-2025-o-bukhgalterskom-uchete--fcc0b660.xml";

/// Two declared levels: a `glava` container and a `statya` unit. Written on one
/// line so no inter-element whitespace creates residual text.
const GLANVA_STATYA_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 4. Требования к участникам</w:t></w:r></w:p></w:body></w:wordDocument>"#;

/// A single undeclared-number `statya` marker (four) for the drift negative.
const STATYA_FOUR_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Статья 4. Требования к участникам</w:t></w:r></w:p></w:body></w:wordDocument>"#;

/// The negative-grep corpus: the assembly consumer path must contain no XML
/// re-parse surface. Token list is anchored to concrete decoder entry points.
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
            "ln-edition-timeline-{}-{}-{}-{label}",
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

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Run the real producer pipeline (`capture` → `build_projection` →
/// `render_cleaned_projection`) and return the materialized JSONL string.
fn build_wire(xml: &[u8]) -> String {
    let package = capture(xml, &Limits::default()).expect("fixture must capture");
    let projection = build_projection(package.records()).expect("fixture must project");
    render_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("fixture must export")
}

/// Build the wire layer from inline XML and materialize it under `dir`.
fn export_wire(dir: &Path, name: &str, xml: &str) -> PathBuf {
    let artifact = build_wire(xml.as_bytes());
    let path = dir.join(name);
    fs::write(&path, artifact).expect("write cleaned wire fixture");
    path
}

fn cli(tsv: &Path) -> EditionTimelineCli {
    EditionTimelineCli {
        editions: tsv.display().to_string(),
        mode: AssemblyMode::Assembly,
        ctv: false,
        out: None,
    }
}

/// Write a one-row TSV pointing at a materialized wire artifact.
fn write_assembly_tsv(dir: &Path, edition_number: u32, corpus_path: &str, wire: &Path) -> PathBuf {
    let tsv = dir.join("editions.tsv");
    fs::write(
        &tsv,
        format!("{edition_number}\t{corpus_path}\t{}\n", wire.display()),
    )
    .expect("write tsv");
    tsv
}

fn binding(level: &str, number: &str, cc: &str) -> HierarchyBinding {
    HierarchyBinding::try_new(
        None,
        level,
        number,
        ComponentConceptId::parse(cc).expect("cc"),
    )
    .expect("binding")
}

fn run_bin(args: &[&str]) -> std::process::Output {
    Command::new(BIN)
        .args(args)
        .output()
        .expect("bin must launch")
}

// --------------------------------------------------------- the FSM oracle #

#[test]
fn synthetic_single_assembly_reconstructs_oracle_with_zero_drift() {
    let dir = TempDir::new("assembly-ok");
    let wire = export_wire(dir.path(), "federal.jsonl", GLANVA_STATYA_FIXTURE);
    let bytes = fs::read(&wire).expect("read wire");
    let extracted = markers_from_cleaned_wire(&bytes).expect("markers");
    assert!(
        extracted.markers.len() >= 2,
        "glava+statya must extract from the wire layer"
    );

    let mut map = HierarchyMap::empty();
    map.register(binding("glava", "1", "cc:test:glava-1"))
        .expect("register glava");
    map.register(binding("statya", "4", "cc:test:statya-4"))
        .expect("register statya");

    let counts = assemble_edition(&extracted.markers, &map, 100, "amendingact:test-oracle")
        .expect("assembly must succeed");
    assert_eq!(counts.drift, 0, "synthetic oracle must reconstruct exactly");
    assert_eq!(counts.missing, 0);
    assert_eq!(counts.phantom, 0);
    assert_eq!(counts.roots, 1, "one glava forest root");
    assert_eq!(counts.nodes, 2, "glava + statya");
    assert_eq!(counts.proposals, 1, "glava -> statya attach draft");
    assert_eq!(counts.admitted, 1);
    assert_eq!(counts.committed, 1);
}

#[test]
fn mismatched_registry_number_is_detected_as_drift_not_masked() {
    let dir = TempDir::new("assembly-drift");
    let wire = export_wire(dir.path(), "statya.jsonl", STATYA_FOUR_FIXTURE);
    let bytes = fs::read(&wire).expect("read wire");
    let extracted = markers_from_cleaned_wire(&bytes).expect("markers");
    assert_eq!(extracted.markers.len(), 1);

    // One binding for a *different* article number: the fixture's statya 4 stays
    // Unknown, so the oracle (statya 5) is never reconstructed.
    let mut map = HierarchyMap::empty();
    map.register(binding("statya", "5", "cc:test:statya-5"))
        .expect("register");

    let counts = assemble_edition(&extracted.markers, &map, 100, "amendingact:test-drift")
        .expect("assembly must still report its drift");
    assert!(counts.drift > 0, "drift must be detected, not masked");
    assert_eq!(counts.admitted, 0, "no marker binds the registry");
    assert_eq!(counts.missing, 1, "oracle statya 5 is missing from the AST");
    assert_eq!(counts.phantom, 0);
}

#[test]
fn assembly_payload_is_deterministic_and_ascii() {
    let dir = TempDir::new("assembly-det");
    let wire = export_wire(dir.path(), "federal.jsonl", GLANVA_STATYA_FIXTURE);
    let tsv = write_assembly_tsv(dir.path(), 7, CORPUS_44FZ_REL, &wire);
    let (first_code, first) = run_edition_timeline(&cli(&tsv));
    assert_eq!(first_code, 0, "{first}");
    let (second_code, second) = run_edition_timeline(&cli(&tsv));
    assert_eq!(second_code, 0);
    assert_eq!(first, second, "render must be deterministic");
    assert!(first.is_ascii(), "payload must be ASCII");

    let payload: serde_json::Value = serde_json::from_str(&first).expect("payload is JSON");
    assert_eq!(payload["schema"], ASSEMBLY_SCHEMA);
    assert_eq!(payload["edition_number"], 7);
    assert_eq!(payload["r1000_status"], "active/unclosed");
    // The corpus path mints a real 44-FZ expression id.
    assert_eq!(payload["expression_id_present"], true);
    let source_sha = payload["wire_source"]["sha256"].as_str().unwrap();
    assert_eq!(source_sha.len(), 64, "wire source pin is 64 hex chars");
    assert!(
        payload["cleaned_wire_sha256"]
            .as_str()
            .unwrap()
            .starts_with("sha256:")
    );
}

// ------------------------------------------------------- fail-closed CLI #

#[test]
fn bin_unknown_flag_is_usage_error() {
    let output = run_bin(&["--bogus"]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_USAGE)));
}

#[test]
fn bin_missing_cleaned_wire_is_unreadable() {
    let dir = TempDir::new("missing-wire");
    let tsv = dir.path().join("editions.tsv");
    fs::write(
        &tsv,
        format!("118\t{CORPUS_44FZ_REL}\t/nonexistent/m224-s06/0118.jsonl\n"),
    )
    .expect("write tsv");
    let output = run_bin(&["--editions", &tsv.display().to_string()]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_INPUT_UNREADABLE)));
}

#[test]
fn bin_missing_tsv_is_unreadable() {
    let output = run_bin(&["--editions", "/nonexistent/m224-s06/editions.tsv"]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_INPUT_UNREADABLE)));
}

#[test]
fn bin_broken_wire_is_refused() {
    let dir = TempDir::new("broken");
    let wire = dir.path().join("broken.jsonl");
    fs::write(&wire, "not a cleaned projection\n").expect("write broken wire");
    let tsv = write_assembly_tsv(dir.path(), 118, CORPUS_44FZ_REL, &wire);
    let output = run_bin(&["--editions", &tsv.display().to_string()]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_WIRE_REFUSED)));
}

#[test]
fn bin_unimplemented_modes_fail_closed() {
    let dir = TempDir::new("modes");
    let wire = export_wire(dir.path(), "federal.jsonl", GLANVA_STATYA_FIXTURE);
    let tsv = write_assembly_tsv(dir.path(), 118, CORPUS_44FZ_REL, &wire);
    for mode in ["chain", "timeline"] {
        let output = run_bin(&["--editions", &tsv.display().to_string(), "--mode", mode]);
        assert_eq!(
            output.status.code(),
            Some(i32::from(EXIT_USAGE)),
            "mode {mode} must fail closed until implemented"
        );
    }
    let output = run_bin(&["--editions", &tsv.display().to_string(), "--ctv"]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_USAGE)));
}

#[test]
fn bin_two_rows_in_assembly_mode_is_usage_error() {
    let dir = TempDir::new("two-rows");
    let wire = export_wire(dir.path(), "federal.jsonl", GLANVA_STATYA_FIXTURE);
    let tsv = dir.path().join("editions.tsv");
    fs::write(
        &tsv,
        format!(
            "118\t{CORPUS_44FZ_REL}\t{}\n117\t{CORPUS_44FZ_REL}\t{}\n",
            wire.display(),
            wire.display()
        ),
    )
    .expect("write tsv");
    let output = run_bin(&["--editions", &tsv.display().to_string()]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_USAGE)));
}

#[test]
fn malformed_tsv_row_is_usage_error() {
    let dir = TempDir::new("malformed");
    let tsv = dir.path().join("editions.tsv");
    fs::write(&tsv, "not-a-number\tpath\tonly\n").expect("write tsv");
    let output = run_bin(&["--editions", &tsv.display().to_string()]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_USAGE)));
}

#[test]
fn arg_parser_rejects_from_xml_and_requires_editions() {
    assert!(parse_edition_timeline_args(Vec::<String>::new().into_iter()).is_err());
    assert!(
        parse_edition_timeline_args(
            ["--editions".to_owned(), "editions.tsv".to_owned()].into_iter()
        )
        .is_ok()
    );
    assert!(
        parse_edition_timeline_args(
            [
                "--editions".to_owned(),
                "editions.tsv".to_owned(),
                "--from-xml".to_owned(),
                "source.xml".to_owned(),
            ]
            .into_iter()
        )
        .is_err(),
        "--from-xml must never be accepted"
    );
    assert!(
        parse_edition_timeline_args(
            [
                "--editions".to_owned(),
                "editions.tsv".to_owned(),
                "--mode".to_owned(),
                "pdf".to_owned(),
            ]
            .into_iter()
        )
        .is_err(),
        "unknown mode is refused"
    );
}

// -------------------------------------------------- corpus-gated oracles #

#[test]
fn corpus_44fz_edition_0118_assembly_zero_drift() {
    let xml_path = repo_root().join(CORPUS_44FZ_REL);
    let Ok(xml) = fs::read(&xml_path) else {
        eprintln!("SKIP: consru_export edition-0118 not available");
        return;
    };
    let dir = TempDir::new("44fz-0118");
    let artifact = build_wire(&xml);
    let wire = dir.path().join("0118.jsonl");
    fs::write(&wire, artifact).expect("write wire");
    let tsv = write_assembly_tsv(dir.path(), 118, CORPUS_44FZ_REL, &wire);

    let (code, message) = run_edition_timeline(&cli(&tsv));
    assert_eq!(code, 0, "assembly must succeed: {message}");
    let payload: serde_json::Value = serde_json::from_str(&message).expect("payload is JSON");
    assert_eq!(payload["schema"], ASSEMBLY_SCHEMA);
    assert_eq!(payload["registry_bindings"], 102, "8 glava + 94 statya");
    assert!(
        payload["markers"].as_u64().unwrap() > 1500,
        "the full marker set must extract from the wire layer: {payload}"
    );
    assert_eq!(payload["proposals"], 94, "94 statya attach drafts");
    assert_eq!(payload["admitted"], 94);
    assert_eq!(payload["roots"], 8, "8 glava roots");
    assert_eq!(payload["nodes"], 102, "8 glava + 94 statya nodes");
    assert_eq!(payload["drift"], 0, "zero oracle drift");
    assert_eq!(payload["missing"], 0);
    assert_eq!(payload["phantom"], 0);
    assert_eq!(payload["expression_id_present"], true);
}

#[test]
fn tracked_402fz_fixture_assembly_zero_drift() {
    let xml_path = repo_root().join(TRACKED_402);
    let Ok(xml) = fs::read(&xml_path) else {
        eprintln!("SKIP: tracked 402-FZ fixture not available");
        return;
    };
    let dir = TempDir::new("tracked-402");
    let artifact = build_wire(&xml);
    let wire = dir.path().join("402fz.jsonl");
    fs::write(&wire, artifact).expect("write wire");
    let tsv = write_assembly_tsv(dir.path(), 70, TRACKED_402, &wire);

    let (code, message) = run_edition_timeline(&cli(&tsv));
    assert_eq!(code, 0, "assembly must succeed: {message}");
    let payload: serde_json::Value = serde_json::from_str(&message).expect("payload is JSON");
    assert_eq!(payload["registry_bindings"], 37, "4 glava + 33 statya");
    assert_eq!(payload["roots"], 4, "4 glava roots");
    assert_eq!(payload["nodes"], 37, "all bound markers fold");
    assert_eq!(payload["drift"], 0, "tracked 402-FZ must reconstruct");
    assert!(payload["proposals"].as_u64().unwrap() > 0);
}

// ------------------------------------------------- negative self-checks #

#[test]
fn source_contains_no_xml_reparse_surface() {
    let sources = [
        ("module", include_str!("../src/edition_timeline.rs")),
        ("bin", include_str!("../src/bin/edition-timeline.rs")),
    ];
    for (label, source) in sources {
        for token in FORBIDDEN_TOKENS {
            assert!(
                !source.contains(token),
                "{label} source must not contain the XML re-parse token {token:?}"
            );
        }
    }
    // Non-vacuity: the wire layer really is reconstructed, not hand-waved.
    let module = include_str!("../src/edition_timeline.rs");
    assert!(module.contains("read_cleaned_wire"));
    assert!(module.contains("blocks_from_cleaned_projection"));
}

#[test]
fn forbidden_token_probe_is_non_vacuous() {
    // Every token the grep forbids is a real, present symbol on the XML decode
    // path. If the XML path lost these tokens the grep above would silently
    // become vacuous.
    let xml_path_sources = [
        include_str!("../../ln-decode/src/adapters.rs"),
        include_str!("../../ln-decode/src/bin/reader-nav.rs"),
        include_str!("../../ln-decode/src/adapters/garant_odt.rs"),
    ];
    for token in FORBIDDEN_TOKENS {
        assert!(
            xml_path_sources.iter().any(|source| source.contains(token)),
            "forbidden token {token:?} must exist on the XML path, else the convention grep is vacuous"
        );
    }
}

#[test]
fn non_claims_are_declared() {
    assert!(
        ASSEMBLY_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("cleaned_wire_jsonl"))
    );
    assert!(
        ASSEMBLY_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("integrity_is_not_semantic_completeness"))
    );
}
