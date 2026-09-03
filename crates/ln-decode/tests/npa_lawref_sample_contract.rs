//! Contract tests for the `npa-lawref-sample/v1` Layer-2 gold-sample schema
//! (M199 S01 T01).
//!
//! T01 pins the SCHEMA, not the fill: a minimal inline 1-doc/1-fragment
//! manifest loads, and every hostile mutation fails the loader closed. The
//! 40-document stratified fill is T02; the seed spans are T03. No
//! `tests/fixtures/npa-lawref/` tree exists in T01 (an empty tree would break
//! the future bijection) — every fixture here is inline, and the corpus
//! (`consru_export`) is never opened.
//!
//! Protocol authority: `prd/migration/rust-evidence/m199-s01-annotation-protocol.md`.
//! The loader lives in `tests/npa_lawref_support/mod.rs` (D328 hand-rolled
//! JSON pattern; deliberately not a `#[path]` include of `npa_support`, and
//! `npa_golden_fixtures.rs` is never compiled twice from here — D335).

mod npa_lawref_support;

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use npa_lawref_support::*;

// ---------------------------------------------------------------------------
// Inline minimal sample (1 document / 1 fragment) — no fixtures tree in T01.
// ---------------------------------------------------------------------------

const DOC_ID: &str = "npa-doc-001";
const FRAGMENT_ID: &str = "npa-frag-001";
const FRAGMENT_FILE: &str = "npa-law-001.txt";
/// Synthetic reference shape, not a corpus sentence (Q3 hygiene).
const FRAGMENT_TEXT: &str = "ст. 15.1";
const SOURCE_PATH: &str = "consru_export/consru_export/exports/npa/npa-law-001.xml";
const DOC_SHA256: &str = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef";
const DEFAULT_NON_CLAIMS: [&str; 4] = [
    "not official-publication provenance (R070 open)",
    "not LawRef / act-tree / clause segmentation",
    "not the N2-gate acceptance decision",
    "not legal interpretation",
];

const MANIFEST_TEMPLATE: &str = r#"{
  "schema": "npa-lawref-sample/v1",
  "schema_version": 1,
  "lifecycle": "[bounded]",
  "draw_seed": 20260903,
  "strata": [
@STRATA@
  ],
  "documents": [
@DOC@
  ],
  "fragments": [
@FRAGMENTS@
  ]
}"#;

const DOC_TEMPLATE: &str = r#"    {
      "doc_id": "@DOC_ID@",
      "source_path": "@SOURCE_PATH@",
      "source_sha256": "@SHA256@",
      "byte_count": 2048,
      "family": "@FAMILY@",
      "doc_type": "@DOC_TYPE@",
      "decoder": "@DECODER@",
      "fragment_ids": [
@FRAGMENT_IDS@
      ],
      "non_claims": [
@NON_CLAIMS@
      ]
    }"#;

const FRAGMENT_TEMPLATE: &str = r#"    {
      "id": "@ID@",
      "file": "@FILE@",
      "doc_id": "@DOC_ID@",
      "source_block_index": 877,
      "note_kind": "enacting",
      "byte_len": @BYTE_LEN@,
      "status": "seed"@TAIL@
    }"#;

fn quoted_list(items: &[&str]) -> String {
    items
        .iter()
        .map(|item| format!("        \"{item}\""))
        .collect::<Vec<_>>()
        .join(",\n")
}

/// The strata rows are derived from the frozen constant so the inline
/// manifest and the loader can never drift apart.
fn strata_json() -> String {
    D367_QUOTA_TABLE
        .iter()
        .map(|(family, doc_type, quota)| {
            format!("    {{ \"family\": \"{family}\", \"doc_type\": \"{doc_type}\", \"quota\": {quota} }}")
        })
        .collect::<Vec<_>>()
        .join(",\n")
}

// Template renderer: the 8 args mirror the 8 template placeholders 1:1
// (DOC_ID…NON_CLAIMS) — grouping them into a struct would only rename the
// same positional contract for 8+ call sites.
#[allow(clippy::too_many_arguments)]
fn doc_json_custom(
    doc_id: &str,
    source_path: &str,
    sha256: &str,
    family: &str,
    doc_type: &str,
    decoder: &str,
    fragment_ids: &[&str],
    non_claims: &[&str],
) -> String {
    DOC_TEMPLATE
        .replace("@DOC_ID@", doc_id)
        .replace("@SOURCE_PATH@", source_path)
        .replace("@SHA256@", sha256)
        .replace("@FAMILY@", family)
        .replace("@DOC_TYPE@", doc_type)
        .replace("@DECODER@", decoder)
        .replace("@FRAGMENT_IDS@", &quoted_list(fragment_ids))
        .replace("@NON_CLAIMS@", &quoted_list(non_claims))
}

fn doc_json() -> String {
    doc_json_custom(
        DOC_ID,
        SOURCE_PATH,
        DOC_SHA256,
        "npa",
        "law",
        SAMPLE_DECODER,
        &[FRAGMENT_ID],
        &DEFAULT_NON_CLAIMS,
    )
}

fn fragment_json_custom(id: &str, file: &str, doc_id: &str, byte_len: usize, tail: &str) -> String {
    FRAGMENT_TEMPLATE
        .replace("@ID@", id)
        .replace("@FILE@", file)
        .replace("@DOC_ID@", doc_id)
        .replace("@BYTE_LEN@", &byte_len.to_string())
        .replace("@TAIL@", tail)
}

/// Valid fragment with an optional JSON tail (seed span or hostile extra key).
fn fragment_json(tail: &str) -> String {
    fragment_json_custom(
        FRAGMENT_ID,
        FRAGMENT_FILE,
        DOC_ID,
        FRAGMENT_TEXT.len(),
        tail,
    )
}

fn seed_span_json(kind: &str, start: usize, end: usize) -> String {
    format!(r#", "seed_span": {{ "kind": "{kind}", "start": {start}, "end": {end} }}"#)
}

fn manifest_with_strata(strata: &str, doc: &str, fragments: &str) -> String {
    MANIFEST_TEMPLATE
        .replace("@STRATA@", strata)
        .replace("@DOC@", doc)
        .replace("@FRAGMENTS@", fragments)
}

fn manifest_json(doc: &str, fragments: &str) -> String {
    manifest_with_strata(&strata_json(), doc, fragments)
}

fn sample_files() -> BTreeMap<String, String> {
    let mut files = BTreeMap::new();
    files.insert(FRAGMENT_FILE.to_string(), FRAGMENT_TEXT.to_string());
    files
}

fn run_valid(manifest: &str) -> SampleManifest {
    validate_sample_set(manifest, &sample_files()).expect("valid sample manifest must load")
}

fn run_hostile(manifest: &str) -> String {
    validate_sample_set(manifest, &sample_files())
        .expect_err("hostile sample manifest must fail the loader closed")
}

// ---------------------------------------------------------------------------
// Green path: the schema loads; the fill is T02's business.
// ---------------------------------------------------------------------------

#[test]
fn minimal_inline_one_doc_one_fragment_manifest_loads() {
    let loaded = run_valid(&manifest_json(&doc_json(), &fragment_json("")));
    assert_eq!(loaded.draw_seed, 20260903);
    assert_eq!(loaded.strata.len(), 9, "D367 declares nine strata");
    assert_eq!(loaded.documents.len(), 1);
    assert_eq!(loaded.fragments.len(), 1);

    let document = &loaded.documents[0];
    assert_eq!(document.doc_id, DOC_ID);
    assert_eq!(document.source_sha256, DOC_SHA256);
    assert_eq!(document.family, "npa");
    assert_eq!(document.doc_type, "law");
    assert_eq!(document.fragment_ids, [FRAGMENT_ID.to_string()]);

    let fragment = &loaded.fragments[0];
    assert_eq!(fragment.id, FRAGMENT_ID);
    assert_eq!(fragment.file, FRAGMENT_FILE);
    assert_eq!(fragment.doc_id, DOC_ID);
    assert_eq!(fragment.status, "seed");
    assert_eq!(fragment.note_kind, "enacting");
    assert_eq!(fragment.byte_len, FRAGMENT_TEXT.len());
    assert!(fragment.seed_span.is_none());
}

#[test]
fn optional_seed_span_loads_on_char_boundaries() {
    // "ст. 15.1": `ст.` is bytes [0,5) — Abbrev(lexeme) + its trailing dot.
    let loaded = run_valid(&manifest_json(
        &doc_json(),
        &fragment_json(&seed_span_json("Abbrev", 0, 5)),
    ));
    let span = loaded.fragments[0]
        .seed_span
        .as_ref()
        .expect("seed span must load");
    assert_eq!((span.kind, span.start, span.end), ("Abbrev", 0, 5));
}

#[test]
fn d367_quota_and_closed_vocab_constants_exist() {
    assert_eq!(SAMPLE_SCHEMA, "npa-lawref-sample/v1");
    assert_eq!(SAMPLE_SCHEMA_VERSION, 1);
    assert_eq!(SAMPLE_LIFECYCLE, "[bounded]");
    assert_eq!(SAMPLE_DECODER, "ConsultantWordMlBlockDecoder");

    assert_eq!(
        D367_QUOTA_TABLE.len(),
        9,
        "9 strata: 6 npa + courts + fas + xml"
    );
    let total: usize = D367_QUOTA_TABLE.iter().map(|(_, _, quota)| quota).sum();
    assert_eq!(total, 40, "D367 total: 8+4+6+4+3+1+5+5+4 = 40");
    for (family, doc_type, quota) in D367_QUOTA_TABLE {
        assert!(
            SAMPLE_FAMILIES.contains(&family),
            "stratum family '{family}'"
        );
        assert!(!doc_type.is_empty());
        assert!(quota >= 1);
    }

    assert_eq!(
        SAMPLE_NOTE_KINDS,
        [
            "enacting",
            "provider_note",
            "hostile-control",
            "pattern-boost"
        ]
    );
    assert!(
        !SAMPLE_NOTE_KINDS.contains(&"Editorial"),
        "Editorial stays absent"
    );
    assert_eq!(SAMPLE_FRAGMENT_STATUSES, ["seed"]);

    assert_eq!(SAMPLE_TOKEN_KINDS.len(), 9, "the closed C2 kind set");
    assert!(!SAMPLE_TOKEN_KINDS.contains(&"Editorial"));
    assert!(!SAMPLE_TOKEN_KINDS.contains(&"LawRef"));

    assert_eq!(
        SAMPLE_REQUIRED_NON_CLAIMS,
        [
            "official-publication",
            "R070",
            "LawRef",
            "N2-gate",
            "legal interpretation"
        ]
    );
}

// ---------------------------------------------------------------------------
// Hostile: the schema fails closed (goldens stay untouched; all inline).
// ---------------------------------------------------------------------------

#[test]
fn hostile_root_extra_key_fails_closed() {
    let manifest = manifest_json(&doc_json(), &fragment_json("")).replace(
        "\"draw_seed\": 20260903,",
        "\"draw_seed\": 20260903, \"helpful_comment\": \"why this draw\",",
    );
    let error = run_hostile(&manifest);
    assert!(
        error.contains("unexpected JSON key 'helpful_comment'"),
        "expected closed-root rejection, got: {error}"
    );
}

#[test]
fn hostile_fragment_extra_key_fails_closed() {
    // TokenKind-sidecar fields are a different schema (D335): they must not
    // leak into the Layer-2 manifest.
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json(", \"tokens\": []"),
    ));
    assert!(
        error.contains("unexpected JSON key 'tokens'"),
        "expected closed-fragment rejection, got: {error}"
    );
}

#[test]
fn hostile_unknown_family_and_garant_odt_fail_closed() {
    let fragments = fragment_json("");
    let error = run_hostile(&manifest_json(
        &doc_json_custom(
            DOC_ID,
            SOURCE_PATH,
            DOC_SHA256,
            "other",
            "law",
            SAMPLE_DECODER,
            &[FRAGMENT_ID],
            &DEFAULT_NON_CLAIMS,
        ),
        &fragments,
    ));
    assert!(
        error.contains("unknown family 'other'"),
        "expected unknown-family rejection, got: {error}"
    );

    let error = run_hostile(&manifest_json(
        &doc_json_custom(
            DOC_ID,
            SOURCE_PATH,
            DOC_SHA256,
            "garant-odt",
            "law",
            SAMPLE_DECODER,
            &[FRAGMENT_ID],
            &DEFAULT_NON_CLAIMS,
        ),
        &fragments,
    ));
    assert!(
        error.contains("unknown family 'garant-odt'"),
        "expected garant-odt family rejection, got: {error}"
    );
}

#[test]
fn hostile_garant_decoder_fails_closed() {
    let error = run_hostile(&manifest_json(
        &doc_json_custom(
            DOC_ID,
            SOURCE_PATH,
            DOC_SHA256,
            "npa",
            "law",
            "GarantOdtBlockDecoder",
            &[FRAGMENT_ID],
            &DEFAULT_NON_CLAIMS,
        ),
        &fragment_json(""),
    ));
    assert!(
        error.contains("Garant"),
        "expected Garant-decoder rejection, got: {error}"
    );
}

#[test]
fn hostile_strata_drift_from_d367_fails_closed() {
    let drifted = strata_json().replacen("\"quota\": 8", "\"quota\": 7", 1);
    let error = run_hostile(&manifest_with_strata(
        &drifted,
        &doc_json(),
        &fragment_json(""),
    ));
    assert!(
        error.contains("D367"),
        "expected frozen-strata rejection, got: {error}"
    );
}

#[test]
fn hostile_empty_non_claims_fail_closed() {
    let doc = doc_json_custom(
        DOC_ID,
        SOURCE_PATH,
        DOC_SHA256,
        "npa",
        "law",
        SAMPLE_DECODER,
        &[FRAGMENT_ID],
        &[],
    );
    let error = run_hostile(&manifest_json(&doc, &fragment_json("")));
    assert!(
        error.contains("non_claims must not be empty"),
        "expected empty-non_claims rejection, got: {error}"
    );
}

#[test]
fn hostile_non_claims_missing_required_substring_fails_closed() {
    // `official-publication` stays present — only `R070` goes missing, so the
    // loader must name exactly that substring.
    let reduced: Vec<&str> = vec![
        "not official-publication provenance",
        "not LawRef / act-tree / clause segmentation",
        "not the N2-gate acceptance decision",
        "not legal interpretation",
    ];
    let doc = doc_json_custom(
        DOC_ID,
        SOURCE_PATH,
        DOC_SHA256,
        "npa",
        "law",
        SAMPLE_DECODER,
        &[FRAGMENT_ID],
        &reduced,
    );
    let error = run_hostile(&manifest_json(&doc, &fragment_json("")));
    assert!(
        error.contains("non_claims is missing 'R070'"),
        "expected missing-non_claim rejection, got: {error}"
    );
}

#[test]
fn hostile_missing_or_short_sha256_fails_closed() {
    let missing = doc_json().replacen(
        &format!("      \"source_sha256\": \"{DOC_SHA256}\",\n"),
        "",
        1,
    );
    let error = run_hostile(&manifest_json(&missing, &fragment_json("")));
    assert!(
        error.contains("missing JSON field 'source_sha256'"),
        "expected missing-sha rejection, got: {error}"
    );

    let error = run_hostile(&manifest_json(
        &doc_json_custom(
            DOC_ID,
            SOURCE_PATH,
            "deadbeef",
            "npa",
            "law",
            SAMPLE_DECODER,
            &[FRAGMENT_ID],
            &DEFAULT_NON_CLAIMS,
        ),
        &fragment_json(""),
    ));
    assert!(
        error.contains("64-char hex digest"),
        "expected short-sha rejection, got: {error}"
    );
}

#[test]
fn hostile_wrong_lifecycle_fails_closed() {
    let manifest = manifest_json(&doc_json(), &fragment_json("")).replace(
        "\"lifecycle\": \"[bounded]\"",
        "\"lifecycle\": \"[validated]\"",
    );
    let error = run_hostile(&manifest);
    assert!(
        error.contains("lifecycle"),
        "expected lifecycle rejection, got: {error}"
    );
}

#[test]
fn hostile_editorial_kind_fails_closed() {
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json(&seed_span_json("Editorial", 0, 5)),
    ));
    assert!(
        error.contains("token kind 'Editorial'"),
        "expected Editorial span rejection, got: {error}"
    );

    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json("").replace(
            "\"note_kind\": \"enacting\"",
            "\"note_kind\": \"Editorial\"",
        ),
    ));
    assert!(
        error.contains("unknown note_kind 'Editorial'"),
        "expected Editorial note_kind rejection, got: {error}"
    );
}

#[test]
fn hostile_lawref_as_token_kind_fails_closed() {
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json(&seed_span_json("LawRef", 0, 5)),
    ));
    assert!(
        error.contains("'LawRef' is a product type"),
        "expected LawRef-kind rejection, got: {error}"
    );
    assert!(
        error.contains("no LawRef type may exist in src/"),
        "the rejection must name the S01 boundary, got: {error}"
    );
}

#[test]
fn hostile_span_violations_fail_closed() {
    // Past EOF.
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json(&seed_span_json("Abbrev", 0, 999)),
    ));
    assert!(
        error.contains("exceeds fragment text length"),
        "expected past-EOF rejection, got: {error}"
    );

    // Inside a multi-byte char (`с` starts at 0 and is two bytes long).
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json(&seed_span_json("HierNum", 1, 5)),
    ));
    assert!(
        error.contains("is not on char boundaries"),
        "expected char-boundary rejection, got: {error}"
    );

    // Empty span.
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json(&seed_span_json("HierNum", 5, 5)),
    ));
    assert!(
        error.contains(">= end"),
        "expected empty-span rejection, got: {error}"
    );
}

#[test]
fn hostile_non_seed_status_fails_closed() {
    // The seed is not gold: no status other than `seed` may be declared.
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json("").replacen("\"status\": \"seed\"", "\"status\": \"gold\"", 1),
    ));
    assert!(
        error.contains("unknown fragment status 'gold'"),
        "expected non-seed status rejection, got: {error}"
    );
}

#[test]
fn hostile_bijection_violations_fail_closed() {
    let manifest = manifest_json(&doc_json(), &fragment_json(""));

    // Extra .txt on disk without a manifest entry.
    let mut files = sample_files();
    files.insert("orphan-001.txt".to_string(), "orphan text".to_string());
    let error = validate_sample_set(&manifest, &files)
        .expect_err("extra txt without a manifest entry must fail closed");
    assert!(
        error.contains("extra fragment file"),
        "expected extra-file rejection, got: {error}"
    );

    // Manifest entry whose .txt is missing.
    let empty: BTreeMap<String, String> = BTreeMap::new();
    let error = validate_sample_set(&manifest, &empty)
        .expect_err("manifest entry without its txt must fail closed");
    assert!(
        error.contains("no .txt fragment on disk"),
        "expected missing-file rejection, got: {error}"
    );
}

#[test]
fn hostile_document_fragment_reference_drift_fails_closed() {
    // Fragment points at an undeclared document.
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json_custom(
            FRAGMENT_ID,
            FRAGMENT_FILE,
            "ghost-doc",
            FRAGMENT_TEXT.len(),
            "",
        ),
    ));
    assert!(
        error.contains("unknown document id 'ghost-doc'"),
        "expected ghost-doc rejection, got: {error}"
    );

    // Document lists a fragment that does not exist.
    let doc = doc_json_custom(
        DOC_ID,
        SOURCE_PATH,
        DOC_SHA256,
        "npa",
        "law",
        SAMPLE_DECODER,
        &["npa-frag-999"],
        &DEFAULT_NON_CLAIMS,
    );
    let error = run_hostile(&manifest_json(&doc, &fragment_json("")));
    assert!(
        error.contains("fragment_ids entry 'npa-frag-999' has no matching fragment"),
        "expected ghost-fragment rejection, got: {error}"
    );

    // Document lists no fragments at all.
    let doc = doc_json_custom(
        DOC_ID,
        SOURCE_PATH,
        DOC_SHA256,
        "npa",
        "law",
        SAMPLE_DECODER,
        &[],
        &DEFAULT_NON_CLAIMS,
    );
    let error = run_hostile(&manifest_json(&doc, &fragment_json("")));
    assert!(
        error.contains("fragment_ids must not be empty"),
        "expected empty-fragment_ids rejection, got: {error}"
    );
}

#[test]
fn hostile_byte_len_drift_fails_closed() {
    let error = run_hostile(&manifest_json(
        &doc_json(),
        &fragment_json_custom(FRAGMENT_ID, FRAGMENT_FILE, DOC_ID, 999, ""),
    ));
    assert!(
        error.contains("byte_len 999 does not equal the fragment file byte length"),
        "expected byte_len drift rejection, got: {error}"
    );
}

#[test]
fn on_disk_loader_fails_closed_while_fixtures_are_absent() {
    // T01 deliberately creates no tests/fixtures/npa-lawref/ tree (an empty
    // tree would break the future bijection); the on-disk loader must fail
    // closed until T02 lands the manifest + fragments. When T02 fills the
    // tree, this test is replaced by the real load + bijection contract.
    let manifest_path = fixture_dir().join("lawref_sample_manifest.json");
    let error = load_sample_manifest(&manifest_path, &fixture_dir())
        .expect_err("absent fixtures must fail closed");
    assert!(
        error.contains("read "),
        "expected read failure, got: {error}"
    );
}

// ---------------------------------------------------------------------------
// S01 boundary: no LawRef product type in src/ (scanner lives in tests/).
// ---------------------------------------------------------------------------

fn fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

fn collect_rs_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let entries = fs::read_dir(dir)
        .unwrap_or_else(|err| panic!("src dir {} must be readable: {err}", dir.display()));
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_rs_files(&path, out);
        } else if path.extension().and_then(|ext| ext.to_str()) == Some("rs") {
            out.push(path);
        }
    }
}

#[test]
fn src_has_no_lawref_product_type() {
    let src_dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut files = Vec::new();
    collect_rs_files(&src_dir, &mut files);
    assert!(
        files.len() >= 10,
        "the ln-decode src tree must be walked (got {} rs files)",
        files.len()
    );

    let mut violations = Vec::new();
    for path in &files {
        let text =
            fs::read_to_string(path).unwrap_or_else(|err| panic!("read {}: {err}", path.display()));
        for pattern in ["struct LawRef", "enum LawRef", "type LawRef"] {
            if text.contains(pattern) {
                violations.push(format!("{} contains '{pattern}'", path.display()));
            }
        }
    }
    assert!(
        violations.is_empty(),
        "no LawRef product type may exist in src/ during S01 (D363: Layer-2 sample before any FSM):\n{}",
        violations.join("\n")
    );
}
