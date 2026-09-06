//! TDD red contract for the closed hierarchy candidate artifact boundary
//! (M202-9qf3ta S02): count-only ASCII artifact + fail-closed CLI.
//!
//! Pins against `ln_decode::hierarchy_artifact` (implemented in T02):
//! - fixed `law-nexus-hierarchy-candidate-artifact/v1` key order and bytes;
//! - ASCII-only, count-only, `authoritative: false` candidate identities;
//! - source and identity FNV-1a digests via `domain::fingerprint_bytes`;
//! - raw hit-stream duplicate indices (first=2 / later=4);
//! - typed `SchemaDrift` / `PathDrift` / `HashDrift` / `NonAscii` / `Usage`
//!   failures and pinned CLI exit codes;
//! - `--check` stale rejection (exit 6) without mutating the stale file,
//!   subprocess coverage via `CARGO_BIN_EXE_hierarchy-candidate-artifact`.
//!
//! Git-tracked fixture only: no consru_export corpus walk, no registry YAML
//! writes, no ontology/admission imports (D185 / D417 / D418).

use std::fs;
use std::path::PathBuf;
use std::process::Command;

use ln_decode::adapters::ConsultantWordMlBlockDecoder;
use ln_decode::domain::{fingerprint_bytes, DecodeRequest, FamilyFormat, ParsedBlock, PayloadRef};
use ln_decode::hierarchy::{
    catalog_token, extract_hierarchy_candidates, HierarchyCandidateReport,
    HierarchyExtractDiagnostic,
};
use ln_decode::hierarchy_artifact::{
    check_hierarchy_candidate_artifact, parse_artifact_args, render_hierarchy_candidate_artifact,
    run_hierarchy_candidate_artifact, validate_hierarchy_candidate_artifact, ArtifactCli,
    ArtifactError, ArtifactMode, ArtifactRenderInput, ArtifactSourceKind,
    HIERARCHY_CANDIDATE_ARTIFACT_SCHEMA,
};
use ln_decode::ports::BlockDecoderPort;

/// Same document bytes as the S01 inline fixture, tracked as a file so the
/// CLI can take it via explicit `--source` (no implicit corpus walk).
const FIXTURE_XML: &[u8] = include_bytes!("fixtures/hierarchy_candidates.xml");
const FIXTURE_REPO_PATH: &str = "crates/ln-decode/tests/fixtures/hierarchy_candidates.xml";
const PAYLOAD_REF: &str = "payload:m202-hierarchy-candidates";
const EXPECTED_HEARTBEAT: &str = "extracted=7 unique=6 drift=0";
const REGISTRY_YAML_REL: &str = "prd/architecture/kb-hierarchy-registry.yaml";
const IDENTITY_DIGEST_MARKER: &str = "\"identity_digest\": \"fnv1a64:";

const DUPLICATE_ROW_LINE: &str = concat!(
    "      {\"catalog_token\": \"punkt\", \"key_path\": \"statya-4/punkt-1\", ",
    "\"first_index\": 2, \"later_index\": 4}"
);

/// Fixed-order hand-rendered schema v1 for the tracked fixture. Digests are
/// substituted from `domain::fingerprint_bytes` so this stays a byte pin, not
/// a hash hardcode. Any renderer drift (spacing, ordering, wording) fails.
const GOLDEN_TEMPLATE: &str = r#"{
  "schema": "law-nexus-hierarchy-candidate-artifact/v1",
  "schema_version": 1,
  "lifecycle": "[proposed]",
  "count_only": true,
  "ascii_only": true,
  "authoritative": false,
  "crate": "ln-decode",
  "decoder": "ConsultantWordMlBlockDecoder",
  "extractor": "ln_decode::hierarchy::extract_hierarchy_candidates",
  "non_claims": [
    "Candidates are not ComponentConcept and never mint ComponentConcept identifiers (Review 4).",
    "Candidates are not kb-hierarchy-registry.yaml and are never auto-applied as YAML (D185).",
    "Candidates are never admitted to the registry: admission is a separate human-gated step.",
    "Candidates are not legal hierarchy truth: not InForce, not Applicable, not authority.",
    "Artifact is not kb-hierarchy-registry.yaml.",
    "Not R035 validation; corpus 8/94 is SKIP-capable sanity."
  ],
  "source_binding": {
    "kind": "file",
    "path": "crates/ln-decode/tests/fixtures/hierarchy_candidates.xml",
    "payload_ref": "payload:m202-hierarchy-candidates",
    "source_digest": "SOURCE_DIGEST"
  },
  "counts": {
    "extracted": 7,
    "unique": 6,
    "duplicate": 1,
    "nested": 3,
    "by_level": {
      "razdel": 0,
      "glava": 1,
      "paragraph": 0,
      "statya": 2,
      "chast": 0,
      "punkt": 3,
      "podpunkt": 0
    }
  },
  "diagnostics": {
    "duplicate_key_count": 1,
    "duplicate_keys": [
      {"catalog_token": "punkt", "key_path": "statya-4/punkt-1", "first_index": 2, "later_index": 4}
    ]
  },
  "identity_digest": "IDENTITY_DIGEST",
  "candidates": [
    {"catalog_token": "glava", "number": "1", "path": null, "key_path": "1", "depth": 1, "marker_span": {"start": 0, "end": 13}},
    {"catalog_token": "statya", "number": "4", "path": null, "key_path": "4", "depth": 1, "marker_span": {"start": 0, "end": 15}},
    {"catalog_token": "punkt", "number": "1", "path": "statya-4/punkt-1", "key_path": "statya-4/punkt-1", "depth": 2, "marker_span": {"start": 0, "end": 2}},
    {"catalog_token": "punkt", "number": "4.1", "path": "statya-4/punkt-4.1", "key_path": "statya-4/punkt-4.1", "depth": 2, "marker_span": {"start": 0, "end": 4}},
    {"catalog_token": "statya", "number": "5", "path": null, "key_path": "5", "depth": 1, "marker_span": {"start": 0, "end": 15}},
    {"catalog_token": "punkt", "number": "1", "path": "statya-5/punkt-1", "key_path": "statya-5/punkt-1", "depth": 2, "marker_span": {"start": 0, "end": 2}}
  ]
}
"#;

fn decode_fixture() -> Vec<ParsedBlock> {
    let request = DecodeRequest::new(
        PayloadRef::parse(PAYLOAD_REF).expect("fixture payload ref parses"),
        FamilyFormat::parse("family:consultant-wordml").expect("wordml family parses"),
        FIXTURE_XML,
    );
    ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("tracked fixture must decode")
}

fn fixture_report() -> HierarchyCandidateReport {
    extract_hierarchy_candidates(&decode_fixture())
}

fn render_input<'a>(report: &'a HierarchyCandidateReport) -> ArtifactRenderInput<'a> {
    ArtifactRenderInput {
        source_kind: ArtifactSourceKind::File,
        source_path: FIXTURE_REPO_PATH,
        payload_ref: PAYLOAD_REF,
        source_bytes: FIXTURE_XML,
        report,
        include_identities: true,
    }
}

fn golden_string() -> String {
    let report = fixture_report();
    render_hierarchy_candidate_artifact(&render_input(&report))
}

/// Independent reconstruction of the canonical identity stream (research
/// canon): unique candidates in extraction order, then duplicate rows.
fn canonical_identity_stream(report: &HierarchyCandidateReport) -> String {
    let mut stream = String::new();
    for candidate in report.candidates() {
        stream.push_str(candidate.catalog_token());
        stream.push('\0');
        stream.push_str(candidate.number());
        stream.push('\0');
        stream.push_str(candidate.path().unwrap_or(""));
        stream.push('\0');
        stream.push_str(candidate.key_path());
        stream.push('\0');
        stream.push_str(&candidate.depth().to_string());
        stream.push('\n');
    }
    for diagnostic in report.diagnostics() {
        if let HierarchyExtractDiagnostic::DuplicateKey {
            level,
            key_path,
            first_index,
            later_index,
        } = diagnostic
        {
            stream.push_str("dup\0");
            stream.push_str(catalog_token(*level));
            stream.push('\0');
            stream.push_str(key_path);
            stream.push('\0');
            stream.push_str(&first_index.to_string());
            stream.push('\0');
            stream.push_str(&later_index.to_string());
            stream.push('\n');
        }
    }
    stream
}

fn expected_artifact_bytes() -> String {
    let report = fixture_report();
    let source_digest = fingerprint_bytes(FIXTURE_XML);
    let identity_digest = fingerprint_bytes(canonical_identity_stream(&report).as_bytes());
    GOLDEN_TEMPLATE
        .replace("SOURCE_DIGEST", &source_digest)
        .replace("IDENTITY_DIGEST", &identity_digest)
}

fn replace_first(artifact: &str, from: &str, to: &str) -> String {
    assert!(artifact.contains(from), "mutation target missing: {from}");
    artifact.replacen(from, to, 1)
}

fn remove_line_containing(artifact: &str, needle: &str) -> String {
    let mut out = String::new();
    let mut removed = false;
    for line in artifact.lines() {
        if !removed && line.contains(needle) {
            removed = true;
            continue;
        }
        out.push_str(line);
        out.push('\n');
    }
    assert!(removed, "line to remove not found: {needle}");
    out
}

fn flip_first_hex_after(artifact: &str, marker: &str) -> String {
    let start = artifact.find(marker).expect("marker missing") + marker.len();
    let mut bytes = artifact.as_bytes().to_vec();
    let byte = bytes[start];
    assert!(byte.is_ascii_hexdigit(), "expected hex digit after marker");
    bytes[start] = if byte == b'0' { b'1' } else { b'0' };
    String::from_utf8(bytes).expect("artifact is ascii")
}

fn position_of(artifact: &str, needle: &str) -> usize {
    artifact
        .find(needle)
        .unwrap_or_else(|| panic!("needle missing: {needle}"))
}

fn assert_ascending(artifact: &str, keys: &[&str]) {
    for pair in keys.windows(2) {
        assert!(
            position_of(artifact, pair[0]) < position_of(artifact, pair[1]),
            "key order violated: {} must precede {}",
            pair[0],
            pair[1]
        );
    }
}

fn args(items: &[&str]) -> Vec<String> {
    items.iter().map(|item| (*item).to_string()).collect()
}

fn temp_dir(label: &str) -> PathBuf {
    let base = std::env::var_os("CARGO_TARGET_TMPDIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("target/tmp"));
    let dir = base.join(format!("hierarchy-artifact-{label}-{}", std::process::id()));
    fs::create_dir_all(&dir).expect("create temp dir under cargo target tmpdir");
    dir
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repo root resolves")
}

fn cargo_bin() -> PathBuf {
    std::env::var_os("CARGO_BIN_EXE_hierarchy-candidate-artifact")
        .map(PathBuf::from)
        .expect("hierarchy-candidate-artifact bin is built by cargo test")
}

// ---------------------------------------------------------------------------
// Renderer: fixed schema v1 bytes, digests, determinism
// ---------------------------------------------------------------------------

#[test]
fn artifact_schema_constant_is_v1() {
    assert_eq!(
        HIERARCHY_CANDIDATE_ARTIFACT_SCHEMA,
        "law-nexus-hierarchy-candidate-artifact/v1"
    );
}

#[test]
fn rendered_artifact_bytes_are_pinned() {
    assert_eq!(golden_string(), expected_artifact_bytes());
    let golden = golden_string();
    assert!(
        golden.starts_with("{\n  \"schema\": \"law-nexus-hierarchy-candidate-artifact/v1\",\n"),
        "artifact must open with the fixed schema line"
    );
    assert!(
        golden.ends_with("}\n"),
        "artifact must end with a single newline"
    );
}

#[test]
fn rendered_artifact_key_order_is_fixed() {
    let golden = golden_string();
    assert_ascending(
        &golden,
        &[
            "\"schema\"",
            "\"schema_version\"",
            "\"lifecycle\"",
            "\"count_only\"",
            "\"ascii_only\"",
            "\"authoritative\"",
            "\"crate\"",
            "\"decoder\"",
            "\"extractor\"",
            "\"non_claims\"",
            "\"source_binding\"",
            "\"counts\"",
            "\"diagnostics\"",
            "\"identity_digest\"",
            "\"candidates\"",
        ],
    );
    assert_ascending(
        &golden,
        &[
            "\"kind\"",
            "\"path\"",
            "\"payload_ref\"",
            "\"source_digest\"",
        ],
    );
    assert_ascending(
        &golden,
        &[
            "\"extracted\"",
            "\"unique\"",
            "\"duplicate\"",
            "\"nested\"",
            "\"by_level\"",
        ],
    );
    assert_ascending(&golden, &["\"duplicate_key_count\"", "\"duplicate_keys\""]);
    let candidates = &golden[position_of(&golden, "\"candidates\": [")..];
    assert_ascending(
        candidates,
        &[
            "\"catalog_token\"",
            "\"number\"",
            "\"path\"",
            "\"key_path\"",
            "\"depth\"",
            "\"marker_span\"",
        ],
    );
}

#[test]
fn rendered_artifact_is_ascii_count_only_and_claim_free() {
    let golden = golden_string();
    assert!(
        golden.bytes().all(|byte| byte < 0x80),
        "artifact must be ASCII-only"
    );
    assert!(golden.contains("\"count_only\": true"));
    assert!(golden.contains("\"ascii_only\": true"));
    assert!(golden.contains("\"authoritative\": false"));
    assert!(!golden.contains("\"authoritative\": true"));
    // No titles, no raw legal text, no ComponentConcept claims (Review 4).
    assert!(!golden.contains("\"title\""));
    assert!(!golden.contains("cc:"));
    assert!(!golden.contains("\"cc\""));
    for needle in ["Общие", "Требования", "Сфера", "положения", "пункт первый"]
    {
        assert!(!golden.contains(needle), "raw legal text leaked: {needle}");
    }
}

#[test]
fn source_digest_is_fnv1a_of_fixture_bytes() {
    let golden = golden_string();
    let expected = fingerprint_bytes(FIXTURE_XML);
    assert!(expected.starts_with("fnv1a64:"));
    assert!(
        golden.contains(&format!("\"source_digest\": \"{expected}\"")),
        "source_digest must be fingerprint_bytes of the exact fixture bytes"
    );
}

#[test]
fn identity_digest_is_fnv1a_of_canonical_stream() {
    let golden = golden_string();
    let expected = fingerprint_bytes(canonical_identity_stream(&fixture_report()).as_bytes());
    assert!(
        golden.contains(&format!("\"identity_digest\": \"{expected}\"")),
        "identity_digest must be fingerprint_bytes of the canonical stream"
    );
}

#[test]
fn render_is_deterministic() {
    assert_eq!(golden_string(), golden_string());
    let report = fixture_report();
    let a = render_hierarchy_candidate_artifact(&render_input(&report));
    let b = render_hierarchy_candidate_artifact(&render_input(&report));
    assert_eq!(a, b);
}

#[test]
fn duplicate_row_addresses_raw_hit_indices() {
    let golden = golden_string();
    assert!(
        golden.contains(DUPLICATE_ROW_LINE),
        "diagnostics must carry raw hit-stream indices first=2 / later=4"
    );
    assert!(
        !golden.contains("\"first_index\": 4"),
        "first_index must not be the later hit"
    );
}

#[test]
fn counts_block_pins_s01_fixture_shape() {
    let golden = golden_string();
    assert!(golden.contains("\"extracted\": 7"));
    assert!(golden.contains("\"unique\": 6"));
    assert!(golden.contains("\"duplicate\": 1"));
    assert!(golden.contains("\"nested\": 3"));
    assert!(golden.contains("\"glava\": 1"));
    assert!(golden.contains("\"statya\": 2"));
    assert!(golden.contains("\"punkt\": 3"));
    assert!(golden.contains("\"razdel\": 0"));
    assert!(golden.contains("\"chast\": 0"));
}

#[test]
fn inline_fixture_source_kind_is_declared() {
    let report = fixture_report();
    let mut input = render_input(&report);
    input.source_kind = ArtifactSourceKind::InlineFixture;
    let rendered = render_hierarchy_candidate_artifact(&input);
    assert!(rendered.contains("\"kind\": \"inline-fixture\""));
}

#[test]
fn counts_only_render_omits_identity_rows_but_keeps_digest() {
    let report = fixture_report();
    let mut input = render_input(&report);
    input.include_identities = false;
    let rendered = render_hierarchy_candidate_artifact(&input);
    assert!(!rendered.contains("\"candidates\""), "rows must be omitted");
    assert!(rendered.contains("\"identity_digest\""), "digest must stay");
    assert!(rendered.contains("\"unique\": 6"));
    assert_eq!(
        validate_hierarchy_candidate_artifact(&rendered),
        Ok(()),
        "counts-only artifact is a valid closed artifact"
    );
}

// ---------------------------------------------------------------------------
// Validator: closed keys, constants, ASCII, drift classes
// ---------------------------------------------------------------------------

#[test]
fn validate_accepts_rendered_artifact() {
    assert_eq!(
        validate_hierarchy_candidate_artifact(&golden_string()),
        Ok(())
    );
}

#[test]
fn validate_pins_closed_keys_and_constants() {
    let golden = golden_string();
    let unknown_key = golden.replacen("{\n", "{\n  \"extra_unpinned_key\": 1,\n", 1);
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&unknown_key),
        Err(ArtifactError::SchemaDrift { .. })
    ));
    let missing_key = remove_line_containing(&golden, "\"lifecycle\"");
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&missing_key),
        Err(ArtifactError::SchemaDrift { .. })
    ));
    let wrong_tag = replace_first(
        &golden,
        "law-nexus-hierarchy-candidate-artifact/v1",
        "law-nexus-hierarchy-candidate-artifact/v2",
    );
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&wrong_tag),
        Err(ArtifactError::SchemaDrift { .. })
    ));
}

#[test]
fn validate_pins_count_only_ascii_and_authoritative() {
    let golden = golden_string();
    let count_only_false = replace_first(&golden, "\"count_only\": true", "\"count_only\": false");
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&count_only_false),
        Err(ArtifactError::SchemaDrift { .. })
    ));
    let ascii_only_false = replace_first(&golden, "\"ascii_only\": true", "\"ascii_only\": false");
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&ascii_only_false),
        Err(ArtifactError::SchemaDrift { .. })
    ));
    let authoritative_true = replace_first(
        &golden,
        "\"authoritative\": false",
        "\"authoritative\": true",
    );
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&authoritative_true),
        Err(ArtifactError::SchemaDrift { .. })
    ));
}

#[test]
fn validate_rejects_non_ascii_payload() {
    let golden = golden_string();
    let poisoned = replace_first(
        &golden,
        "\"lifecycle\": \"[proposed]\"",
        "\"lifecycle\": \"[proposed] Общие\"",
    );
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&poisoned),
        Err(ArtifactError::NonAscii { .. })
    ));
}

#[test]
fn validate_detects_identity_digest_flip_as_hash_drift() {
    let stale = flip_first_hex_after(&golden_string(), IDENTITY_DIGEST_MARKER);
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&stale),
        Err(ArtifactError::HashDrift { .. })
    ));
}

#[test]
fn validate_detects_tampered_duplicate_index_as_hash_drift() {
    let tampered = replace_first(&golden_string(), "\"first_index\": 2", "\"first_index\": 3");
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&tampered),
        Err(ArtifactError::HashDrift { .. })
    ));
}

#[test]
fn validate_pins_count_consistency() {
    let golden = golden_string();
    let extracted = replace_first(&golden, "\"extracted\": 7", "\"extracted\": 8");
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&extracted),
        Err(ArtifactError::SchemaDrift { .. })
    ));
    let nested = replace_first(&golden, "\"nested\": 3", "\"nested\": 4");
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&nested),
        Err(ArtifactError::SchemaDrift { .. })
    ));
    let by_level = replace_first(&golden, "\"punkt\": 3", "\"punkt\": 2");
    assert!(matches!(
        validate_hierarchy_candidate_artifact(&by_level),
        Err(ArtifactError::SchemaDrift { .. })
    ));
}

// ---------------------------------------------------------------------------
// Check: whole-file byte comparison, typed drift, never writes
// ---------------------------------------------------------------------------

#[test]
fn check_accepts_matching_bytes() {
    let golden = golden_string();
    assert_eq!(check_hierarchy_candidate_artifact(&golden, &golden), Ok(()));
}

#[test]
fn check_maps_byte_difference_to_hash_drift() {
    let golden = golden_string();
    let stale = flip_first_hex_after(&golden, IDENTITY_DIGEST_MARKER);
    let error = check_hierarchy_candidate_artifact(&stale, &golden)
        .expect_err("stale expected must be hash drift");
    assert!(matches!(error, ArtifactError::HashDrift { .. }));
    assert_eq!(error.exit_code(), 6);
}

#[test]
fn check_surfaces_expected_side_schema_and_ascii_drift() {
    let golden = golden_string();
    let schema_stale = golden.replacen("{\n", "{\n  \"extra_unpinned_key\": 1,\n", 1);
    assert!(matches!(
        check_hierarchy_candidate_artifact(&schema_stale, &golden),
        Err(ArtifactError::SchemaDrift { .. })
    ));
    let ascii_stale = replace_first(
        &golden,
        "\"lifecycle\": \"[proposed]\"",
        "\"lifecycle\": \"[proposed] Общие\"",
    );
    assert!(matches!(
        check_hierarchy_candidate_artifact(&ascii_stale, &golden),
        Err(ArtifactError::NonAscii { .. })
    ));
}

// ---------------------------------------------------------------------------
// Argument parser: modes, label, mutual exclusion, path refusal
// ---------------------------------------------------------------------------

#[test]
fn parse_args_happy_paths_pin_mode_and_label() {
    let check_cli = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--check",
        "--out",
        "target/hierarchy-artifact-scratch/check.json",
    ]))
    .expect("check args parse");
    assert_eq!(check_cli.source, PathBuf::from(FIXTURE_REPO_PATH));
    assert!(matches!(check_cli.mode, ArtifactMode::Check { .. }));
    assert_eq!(check_cli.label, PAYLOAD_REF);

    let write_cli = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--write",
        "--out",
        "target/hierarchy-artifact-scratch/write.json",
    ]))
    .expect("write args parse");
    assert!(matches!(write_cli.mode, ArtifactMode::Write { .. }));

    let stdout_cli =
        parse_artifact_args(args(&["--source", FIXTURE_REPO_PATH])).expect("stdout args parse");
    assert!(matches!(stdout_cli.mode, ArtifactMode::RenderStdout));

    let labeled = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--check",
        "--out",
        "target/hierarchy-artifact-scratch/labeled.json",
        "--label",
        "payload:m202-s02-scratch",
    ]))
    .expect("label args parse");
    assert_eq!(labeled.label, "payload:m202-s02-scratch");
}

#[test]
fn parse_args_rejects_mutually_exclusive_check_write() {
    let parsed = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--check",
        "--write",
        "--out",
        "target/hierarchy-artifact-scratch/both.json",
    ]));
    assert!(matches!(parsed, Err(ArtifactError::Usage { .. })));
}

#[test]
fn parse_args_rejects_bad_flag_shapes() {
    let unknown_flag = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--corpus",
        "consru_export",
    ]));
    assert!(matches!(unknown_flag, Err(ArtifactError::Usage { .. })));

    let missing_source = parse_artifact_args(args(&["--check", "--out", "a.json"]));
    assert!(matches!(missing_source, Err(ArtifactError::Usage { .. })));

    let write_without_out = parse_artifact_args(args(&["--source", FIXTURE_REPO_PATH, "--write"]));
    assert!(matches!(
        write_without_out,
        Err(ArtifactError::Usage { .. })
    ));

    let out_without_mode = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--out",
        "target/hierarchy-artifact-scratch/idle.json",
    ]));
    assert!(matches!(out_without_mode, Err(ArtifactError::Usage { .. })));
}

#[test]
fn parse_args_refuses_registry_yaml_and_repo_escapes() {
    let yaml_out = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--write",
        "--out",
        REGISTRY_YAML_REL,
    ]));
    assert!(matches!(yaml_out, Err(ArtifactError::PathDrift { .. })));

    let parent_escape = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--write",
        "--out",
        "../hierarchy-artifact-escape.json",
    ]));
    assert!(matches!(
        parent_escape,
        Err(ArtifactError::PathDrift { .. })
    ));

    let absolute_escape = parse_artifact_args(args(&[
        "--source",
        FIXTURE_REPO_PATH,
        "--write",
        "--out",
        "/tmp/hierarchy-artifact-escape.json",
    ]));
    assert!(matches!(
        absolute_escape,
        Err(ArtifactError::PathDrift { .. })
    ));

    let source_escape = parse_artifact_args(args(&[
        "--source",
        "/tmp/hierarchy-artifact-source-escape.xml",
        "--check",
        "--out",
        "target/hierarchy-artifact-scratch/ok.json",
    ]));
    assert!(matches!(
        source_escape,
        Err(ArtifactError::PathDrift { .. })
    ));
}

#[test]
fn exit_codes_are_pinned_per_error_class() {
    assert_eq!(ArtifactError::Usage { detail: "x".into() }.exit_code(), 2);
    assert_eq!(ArtifactError::PathDrift { path: "p".into() }.exit_code(), 2);
    assert_eq!(
        ArtifactError::OutUnwritable { path: "p".into() }.exit_code(),
        3
    );
    assert_eq!(
        ArtifactError::SourceMissing { path: "p".into() }.exit_code(),
        4
    );
    assert_eq!(
        ArtifactError::SchemaDrift { detail: "x".into() }.exit_code(),
        6
    );
    assert_eq!(
        ArtifactError::NonAscii { detail: "x".into() }.exit_code(),
        6
    );
    assert_eq!(
        ArtifactError::HashDrift { detail: "x".into() }.exit_code(),
        6
    );
}

// ---------------------------------------------------------------------------
// Runner (library level): write/check/stdout, fail-closed drift paths
// ---------------------------------------------------------------------------

fn write_cli_to(out: PathBuf) -> ArtifactCli {
    ArtifactCli {
        source: PathBuf::from(FIXTURE_REPO_PATH),
        mode: ArtifactMode::Write { out },
        label: PAYLOAD_REF.to_string(),
    }
}

fn check_cli_of(out: PathBuf) -> ArtifactCli {
    ArtifactCli {
        source: PathBuf::from(FIXTURE_REPO_PATH),
        mode: ArtifactMode::Check { out },
        label: PAYLOAD_REF.to_string(),
    }
}

#[test]
fn run_write_then_check_roundtrip_is_green() {
    let dir = temp_dir("lib-roundtrip");
    let out = dir.join("artifact.json");

    let written = run_hierarchy_candidate_artifact(&write_cli_to(out.clone()))
        .expect("write run must succeed");
    assert_eq!(written.heartbeat, EXPECTED_HEARTBEAT);
    assert!(written.stdout.is_none());
    assert_eq!(
        fs::read(&out).expect("artifact written"),
        golden_string().as_bytes(),
        "written bytes must equal the pinned render"
    );

    let checked =
        run_hierarchy_candidate_artifact(&check_cli_of(out)).expect("check run must succeed");
    assert_eq!(checked.heartbeat, EXPECTED_HEARTBEAT);
    assert!(checked.stdout.is_none());

    fs::remove_dir_all(&dir).ok();
}

#[test]
fn run_check_against_stale_expected_fails_without_mutating() {
    let dir = temp_dir("lib-stale");
    let out = dir.join("expected.json");
    let stale = flip_first_hex_after(&golden_string(), IDENTITY_DIGEST_MARKER);
    fs::write(&out, &stale).expect("write stale expected");
    let before = fs::read(&out).expect("stale bytes");

    let error = run_hierarchy_candidate_artifact(&check_cli_of(out.clone()))
        .expect_err("stale expected must be hash drift");
    assert!(matches!(error, ArtifactError::HashDrift { .. }));
    assert_eq!(error.exit_code(), 6);
    assert_eq!(
        fs::read(&out).expect("stale bytes after"),
        before,
        "--check must never rewrite the expected file"
    );

    fs::remove_dir_all(&dir).ok();
}

#[test]
fn run_check_missing_expected_fails_closed_without_creating() {
    let dir = temp_dir("lib-missing-expected");
    let out = dir.join("absent.json");
    let error = run_hierarchy_candidate_artifact(&check_cli_of(out.clone()))
        .expect_err("missing expected must fail closed");
    assert!(matches!(error, ArtifactError::HashDrift { .. }));
    assert!(!out.exists(), "--check must never create the expected file");
    fs::remove_dir_all(&dir).ok();
}

#[test]
fn run_missing_source_is_typed_source_missing() {
    let cli = ArtifactCli {
        source: PathBuf::from("crates/ln-decode/tests/fixtures/does-not-exist.xml"),
        mode: ArtifactMode::RenderStdout,
        label: PAYLOAD_REF.to_string(),
    };
    let error = run_hierarchy_candidate_artifact(&cli).expect_err("missing source must fail");
    assert!(matches!(error, ArtifactError::SourceMissing { .. }));
    assert_eq!(error.exit_code(), 4);
}

#[test]
fn run_refuses_registry_yaml_out_for_hand_built_cli() {
    let error = run_hierarchy_candidate_artifact(&write_cli_to(PathBuf::from(REGISTRY_YAML_REL)))
        .expect_err("registry yaml out must be refused");
    assert!(matches!(error, ArtifactError::PathDrift { .. }));
}

#[test]
fn run_stdout_mode_returns_artifact_and_heartbeat() {
    let cli =
        parse_artifact_args(args(&["--source", FIXTURE_REPO_PATH])).expect("stdout args parse");
    let outcome = run_hierarchy_candidate_artifact(&cli).expect("stdout run");
    assert_eq!(outcome.heartbeat, EXPECTED_HEARTBEAT);
    assert_eq!(outcome.stdout.as_deref(), Some(golden_string().as_str()));
}

// ---------------------------------------------------------------------------
// Subprocess: CARGO_BIN_EXE_hierarchy-candidate-artifact, stale exit 6
// ---------------------------------------------------------------------------

#[test]
fn cli_check_stale_expected_exits_six_and_leaves_bytes_unchanged() {
    let dir = temp_dir("cli-stale");
    let out = dir.join("expected.json");
    let stale = flip_first_hex_after(&golden_string(), IDENTITY_DIGEST_MARKER);
    fs::write(&out, &stale).expect("write stale expected");
    let before = fs::read(&out).expect("stale bytes");

    let output = Command::new(cargo_bin())
        .current_dir(repo_root())
        .args(["--source", FIXTURE_REPO_PATH, "--check", "--out"])
        .arg(&out)
        .output()
        .expect("spawn hierarchy-candidate-artifact");

    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    assert_eq!(
        output.status.code(),
        Some(6),
        "stale expected must exit 6, stderr: {stderr}"
    );
    assert!(
        stderr.contains("drift=hash"),
        "stderr must be drift line: {stderr}"
    );
    assert_eq!(
        fs::read(&out).expect("stale bytes after"),
        before,
        "stale file bytes must be unchanged"
    );

    fs::remove_dir_all(&dir).ok();
}

#[test]
fn cli_check_matching_expected_exits_zero_and_leaves_bytes_unchanged() {
    let dir = temp_dir("cli-green");
    let out = dir.join("expected.json");
    fs::write(&out, golden_string()).expect("write matching expected");
    let before = fs::read(&out).expect("expected bytes");

    let output = Command::new(cargo_bin())
        .current_dir(repo_root())
        .args(["--source", FIXTURE_REPO_PATH, "--check", "--out"])
        .arg(&out)
        .output()
        .expect("spawn hierarchy-candidate-artifact");

    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    assert_eq!(output.status.code(), Some(0), "stderr: {stderr}");
    assert!(stderr.contains(EXPECTED_HEARTBEAT), "stderr: {stderr}");
    assert!(
        output.stdout.is_empty(),
        "check mode must not print the artifact"
    );
    assert_eq!(fs::read(&out).expect("expected bytes after"), before);

    fs::remove_dir_all(&dir).ok();
}

#[test]
fn cli_write_then_check_roundtrip_exits_zero_with_pinned_bytes() {
    let dir = temp_dir("cli-roundtrip");
    let out = dir.join("artifact.json");

    let write_output = Command::new(cargo_bin())
        .current_dir(repo_root())
        .args(["--source", FIXTURE_REPO_PATH, "--write", "--out"])
        .arg(&out)
        .output()
        .expect("spawn hierarchy-candidate-artifact");
    assert_eq!(write_output.status.code(), Some(0));
    assert_eq!(
        fs::read(&out).expect("artifact written"),
        golden_string().as_bytes(),
        "CLI write bytes must equal the pinned render"
    );

    let check_output = Command::new(cargo_bin())
        .current_dir(repo_root())
        .args(["--source", FIXTURE_REPO_PATH, "--check", "--out"])
        .arg(&out)
        .output()
        .expect("spawn hierarchy-candidate-artifact");
    assert_eq!(
        check_output.status.code(),
        Some(0),
        "fresh artifact must pass --check"
    );

    fs::remove_dir_all(&dir).ok();
}

#[test]
fn cli_refuses_registry_yaml_out_with_exit_two() {
    let yaml_path = repo_root().join(REGISTRY_YAML_REL);
    let before = fs::read(&yaml_path).expect("registry yaml exists");

    let output = Command::new(cargo_bin())
        .current_dir(repo_root())
        .args([
            "--source",
            FIXTURE_REPO_PATH,
            "--write",
            "--out",
            REGISTRY_YAML_REL,
        ])
        .output()
        .expect("spawn hierarchy-candidate-artifact");

    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    assert_eq!(output.status.code(), Some(2), "stderr: {stderr}");
    assert!(stderr.contains("drift=path"), "stderr: {stderr}");
    assert_eq!(fs::read(&yaml_path).expect("registry yaml after"), before);
}

#[test]
fn cli_rejects_check_and_write_together_with_exit_two() {
    let dir = temp_dir("cli-mutex");
    let out = dir.join("both.json");

    let output = Command::new(cargo_bin())
        .current_dir(repo_root())
        .args(["--source", FIXTURE_REPO_PATH, "--check", "--write", "--out"])
        .arg(&out)
        .output()
        .expect("spawn hierarchy-candidate-artifact");

    assert_eq!(
        output.status.code(),
        Some(2),
        "mutually exclusive flags are usage"
    );
    assert!(!out.exists(), "nothing may be written on usage error");
    fs::remove_dir_all(&dir).ok();
}
