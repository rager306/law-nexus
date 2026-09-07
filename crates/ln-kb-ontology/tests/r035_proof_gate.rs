//! R035 proof-gate pins (M202 S04, T01).
//!
//! Count-only honesty gate over frozen S02/S03 evidence. The S04 JSON must
//! keep R035 `active` (D430, HOLD pattern after M201 S04/D416 for R070),
//! lifecycle `[bounded]`, `authoritative: false`, name all four coverage
//! legs as bounded-supporting or unsatisfied (never validated/complete),
//! name all seven promotion gates as unsatisfied, and carry the mandatory
//! non-claims. This suite refuses `validated`/`complete`/`satisfied`
//! upgrades, refuses absolute/`.gsd` paths and timestamps, and pins the
//! frozen S02/S03 byte counts and sha256 source bindings.
//!
//! No product code is exercised here: this is the evidence/lifecycle
//! honesty contour of the ADR-0015 verification matrix. Compile-red until
//! `prd/migration/rust-evidence/m202-s04-r035-proof-gate.json` exists is
//! the intended TDD red state of T01; T02 creates that JSON to go green.
//!
//! Contract for T02 (field names the pins below require in the JSON):
//! - `"requirement_id": "R035"`, `"disposition": "active"`,
//!   `"disposition_decision": "D430"`, `"lifecycle": "[bounded]"`,
//!   `"authoritative": false`,
//!   `"coverage_verdict": "incomplete-because-promotion-gates-unsatisfied"`
//! - `"coverage_legs": [` with exactly four `"leg_id":` entries:
//!   `extractor-integration`, `closed-candidate-artifact`,
//!   `registry-source-mappings`, `named-promotion-gates`; every
//!   `"leg_verdict":` is bounded-supporting or unsatisfied, never
//!   validated/complete/proven.
//! - `"promotion_gates": [` with exactly seven `"gate_id":` entries (the
//!   README R035 table names) and exactly seven
//!   `"gate_verdict": "unsatisfied"` entries.
//! - `mapping_counts` carrying `"candidates_extracted": 7`,
//!   `"candidates_unique": 6`, `"candidates_duplicate": 1`,
//!   `"admitted_candidate_backed": 3`, `"punkt_admitted": 0`,
//!   `"legacy_human": 163`, `"registry_rows": 166`.
//! - `source_binding` citing all four frozen inputs by repo-relative path,
//!   byte count (2443, 3210, 19982, 16699), and sha256 hex below.
//! - `"non_claims": [` naming Akoma/FRBR/LKIF/RusLegalCore/BFO/GOST/OWL/
//!   Common Logic/graph-vector/pilot-scale as NOT validated, punkt
//!   unadmitted (D426), no CC minted, registry `[proposed]` +
//!   authoritative false (D185), 8/94 SKIP-capable sanity is not
//!   validation (D418), two registries / no architecture-JSONL mint, and
//!   `R035 stays active`.
//! - ASCII only, no absolute paths, no `.gsd` paths, no timestamps, no
//!   `"validated"` string value anywhere.

const PROOF_GATE_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m202-s04-r035-proof-gate.json");
const S02_CANDIDATES_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json");
const S03_REGENERATION_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m202-s03-registry-regeneration.json");
const ADMISSIONS_YAML: &str =
    include_str!("../../../prd/architecture/kb-hierarchy-registry-admissions.yaml");
const REGISTRY_YAML: &str = include_str!("../../../prd/architecture/kb-hierarchy-registry.yaml");

/// sha256 + bytes of the frozen S02 candidate artifact (2443 bytes).
const S02_JSON_SHA256: &str = "50946d813412315632214bdfe6f6300e5d5fa8372ab14900002ade2ded5adef6";
const S02_JSON_BYTES: usize = 2443;

/// sha256 + bytes of the frozen S03 regeneration evidence (3210 bytes).
const S03_JSON_SHA256: &str = "7d27652eafb410cab1b394830a2458aaa10815236e090e45badd8058e6049b0e";
const S03_JSON_BYTES: usize = 3210;

/// sha256 + bytes of the frozen admissions source (19982 bytes).
const ADMISSIONS_YAML_SHA256: &str =
    "1707330b202d336046deaf4e94c3836bf8194d16b0f8b9e2fea3bd317ab94b19";
const ADMISSIONS_YAML_BYTES: usize = 19982;

/// sha256 + bytes of the frozen regenerated registry (16699 bytes).
const REGISTRY_YAML_SHA256: &str =
    "6d7952b716b60d3b15ce302833323375e4964b70bb36b20a608331cfa3193c38";
const REGISTRY_YAML_BYTES: usize = 16699;

fn assert_contains(haystack: &str, needle: &str, what: &str) {
    assert!(
        haystack.contains(needle),
        "{what} must contain {needle} (fail-closed honesty pin)"
    );
}

fn assert_count(haystack: &str, needle: &str, expected: usize, what: &str) {
    assert_eq!(
        haystack.matches(needle).count(),
        expected,
        "{what}: expected exactly {expected} occurrence(s) of {needle}"
    );
}

#[test]
fn proof_gate_json_pins_active_r035_bounded_non_authoritative() {
    for expected in [
        "\"requirement_id\": \"R035\"",
        "\"disposition\": \"active\"",
        "\"disposition_decision\": \"D430\"",
        "\"lifecycle\": \"[bounded]\"",
        "\"authoritative\": false",
        "\"coverage_verdict\": \"incomplete-because-promotion-gates-unsatisfied\"",
        "\"milestone\": \"M202-9qf3ta\"",
        "\"slice\": \"S04\"",
        S02_JSON_SHA256,
        S03_JSON_SHA256,
        ADMISSIONS_YAML_SHA256,
        REGISTRY_YAML_SHA256,
    ] {
        assert_contains(PROOF_GATE_JSON, expected, "R035 proof-gate JSON");
    }
    assert!(
        !PROOF_GATE_JSON.contains("\"authoritative\": true"),
        "proof-gate JSON stays non-authoritative"
    );
    for banned in [
        "\"coverage_verdict\": \"complete",
        "\"coverage_verdict\": \"validated",
        "\"disposition\": \"validated\"",
        "\"disposition\": \"complete",
        "\"status\": \"validated\"",
        // the bare JSON string value anywhere: prose may warn against it,
        // a value may never carry it (D430)
        "\"validated\"",
    ] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "R035 proof gate must never carry {banned}: active until promotion gates are proven"
        );
    }
}

#[test]
fn four_coverage_legs_are_named_and_not_validated_or_complete() {
    assert_contains(
        PROOF_GATE_JSON,
        "\"coverage_legs\": [",
        "R035 proof-gate JSON",
    );
    for leg_id in [
        "\"leg_id\": \"extractor-integration\"",
        "\"leg_id\": \"closed-candidate-artifact\"",
        "\"leg_id\": \"registry-source-mappings\"",
        "\"leg_id\": \"named-promotion-gates\"",
    ] {
        assert_contains(PROOF_GATE_JSON, leg_id, "coverage inventory");
    }
    // Exactly four legs.
    assert_count(PROOF_GATE_JSON, "\"leg_id\":", 4, "coverage inventory");
    for banned in [
        "\"leg_verdict\": \"validated\"",
        "\"leg_verdict\": \"complete",
        "\"leg_verdict\": \"proven",
    ] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "no coverage leg may be upgraded: {banned}"
        );
    }
}

#[test]
fn seven_named_promotion_gates_are_unsatisfied() {
    assert_contains(
        PROOF_GATE_JSON,
        "\"promotion_gates\": [",
        "R035 proof-gate JSON",
    );
    for gate_id in [
        "\"gate_id\": \"GATE-AKOMA-FRBR-NORMALIZATION\"",
        "\"gate_id\": \"GATE-LKIF-DEONTIC-BENCHMARK\"",
        "\"gate_id\": \"GATE-RUSLEGALCORE-SCOPE\"",
        "\"gate_id\": \"GATE-BFO-GOST-ALIGNMENT\"",
        "\"gate_id\": \"GATE-ONTOLOGY-GRAPHRAG-INTEGRATION\"",
        "\"gate_id\": \"GATE-G015\"",
        "\"gate_id\": \"GATE-PILOT-SCALE-READINESS\"",
    ] {
        assert_contains(PROOF_GATE_JSON, gate_id, "promotion-gate inventory");
    }
    // Exactly seven gates, all unsatisfied, none promoted.
    assert_count(
        PROOF_GATE_JSON,
        "\"gate_id\":",
        7,
        "promotion-gate inventory",
    );
    assert_count(
        PROOF_GATE_JSON,
        "\"gate_verdict\": \"unsatisfied\"",
        7,
        "promotion-gate verdicts",
    );
    for banned in [
        "\"gate_verdict\": \"validated\"",
        "\"gate_verdict\": \"complete",
        "\"gate_verdict\": \"satisfied\"",
        "\"gate_verdict\": \"checked\"",
        "\"gate_verdict\": \"proven",
    ] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "no promotion gate may be promoted: {banned}"
        );
    }
}

#[test]
fn mapping_counts_pin_unique_admitted_and_punkt_unadmitted() {
    // Proof-gate JSON cites the frozen counts (count-only, no raw text).
    for expected in [
        "\"candidates_extracted\": 7",
        "\"candidates_unique\": 6",
        "\"candidates_duplicate\": 1",
        "\"admitted_candidate_backed\": 3",
        "\"punkt_admitted\": 0",
        "\"legacy_human\": 163",
        "\"registry_rows\": 166",
        "cc:44-fz:glava-1",
        "cc:44-fz:statya-4",
        "cc:44-fz:statya-5",
    ] {
        assert_contains(PROOF_GATE_JSON, expected, "mapping counts");
    }
    // Cross-pin against the frozen artifacts themselves.
    for expected in ["\"extracted\": 7", "\"unique\": 6", "\"duplicate\": 1"] {
        assert_contains(S02_CANDIDATES_JSON, expected, "frozen S02 counts");
    }
    assert_contains(
        S03_REGENERATION_JSON,
        "\"punkt_rows_admitted\": 0",
        "frozen S03 punkt pin",
    );
    for cc in ["cc:44-fz:glava-1", "cc:44-fz:statya-4", "cc:44-fz:statya-5"] {
        assert_contains(S03_REGENERATION_JSON, cc, "frozen S03 admitted CC");
    }
    assert_count(
        S03_REGENERATION_JSON,
        "cc:44-fz:",
        3,
        "frozen S03 admits exactly three CC",
    );
}

#[test]
fn source_binding_pins_frozen_hashes_and_byte_counts() {
    // Frozen inputs are byte-identical to research time: any drift is red.
    assert_eq!(
        S02_CANDIDATES_JSON.len(),
        S02_JSON_BYTES,
        "frozen S02 bytes must stay {S02_JSON_BYTES}"
    );
    assert_eq!(
        S03_REGENERATION_JSON.len(),
        S03_JSON_BYTES,
        "frozen S03 bytes must stay {S03_JSON_BYTES}"
    );
    assert_eq!(
        ADMISSIONS_YAML.len(),
        ADMISSIONS_YAML_BYTES,
        "frozen admissions bytes must stay {ADMISSIONS_YAML_BYTES}"
    );
    assert_eq!(
        REGISTRY_YAML.len(),
        REGISTRY_YAML_BYTES,
        "frozen registry bytes must stay {REGISTRY_YAML_BYTES}"
    );
    // The proof gate cites every hash exactly once (recomputed binding).
    for (hex, what) in [
        (S02_JSON_SHA256, "S02 source binding"),
        (S03_JSON_SHA256, "S03 source binding"),
        (ADMISSIONS_YAML_SHA256, "admissions source binding"),
        (REGISTRY_YAML_SHA256, "registry source binding"),
    ] {
        assert_count(PROOF_GATE_JSON, hex, 1, what);
    }
    // The proof gate cites every byte count (count-only inventory).
    for (bytes, what) in [
        ("2443", "S02 byte count"),
        ("3210", "S03 byte count"),
        ("19982", "admissions byte count"),
        ("16699", "registry byte count"),
    ] {
        assert_contains(PROOF_GATE_JSON, bytes, what);
    }
    // Repo-relative durable anchors only (KNOWLEDGE rule 6).
    for path in [
        "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json",
        "prd/migration/rust-evidence/m202-s03-registry-regeneration.json",
        "prd/architecture/kb-hierarchy-registry-admissions.yaml",
        "prd/architecture/kb-hierarchy-registry.yaml",
    ] {
        assert_contains(PROOF_GATE_JSON, path, "source binding path");
    }
}

#[test]
fn non_claims_name_promotion_boundaries_and_keep_r035_active() {
    assert_contains(PROOF_GATE_JSON, "\"non_claims\": [", "R035 proof-gate JSON");
    for mandatory in [
        // external-standard promotion is not proven by hierarchy mapping
        "Akoma",
        "FRBR",
        "LKIF",
        "RusLegalCore",
        "BFO",
        "GOST",
        "OWL",
        "Common Logic",
        "graph-vector",
        "pilot-scale",
        // punkt stays unadmitted, no CC minted (D426)
        "punkt",
        "unadmitted",
        "D426",
        // never auto-apply decoder output (D185)
        "D185",
        // registry stays proposed and non-authoritative
        "[proposed]",
        // corpus sanity is never R035 validation (D418)
        "D418",
        // two registries: no architecture-JSONL mint in this slice
        "architecture-JSONL",
        // the disposition itself
        "R035 stays active",
    ] {
        assert_contains(PROOF_GATE_JSON, mandatory, "mandatory non-claim");
    }
}

#[test]
fn proof_gate_rejects_overclaims_paths_and_timestamps() {
    // ASCII/count-only: rejects raw legal text (Cyrillic) outright.
    assert!(
        PROOF_GATE_JSON.is_ascii(),
        "proof-gate JSON must stay ASCII-only (R022)"
    );
    // No local-only or absolute anchors (KNOWLEDGE rule 6).
    for banned in ["/root/", "/home/", "/tmp/", ".gsd", "C:\\", ".gsd/exec"] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "proof gate must not anchor: {banned}"
        );
    }
    // No timestamps: the gate is a closed snapshot, not a log line.
    for banned in ["\"timestamp\"", "\"created_at\"", "\"generated_at\""] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "proof gate must not carry: {banned}"
        );
    }
    // No authority/validation upgrades smuggled into any field.
    for banned in [
        "\"authoritative\": true",
        "\"validated\"",
        "\"status\": \"validated\"",
        "\"disposition\": \"validated\"",
    ] {
        assert!(
            !PROOF_GATE_JSON.contains(banned),
            "proof gate must never carry {banned}: R035 stays active"
        );
    }
}

#[test]
fn frozen_s02_s03_artifacts_still_carry_bounded_non_authoritative_counts() {
    for expected in [
        "\"authoritative\": false",
        "\"candidates_extracted\": 7",
        "\"candidates_unique\": 6",
        "\"candidates_duplicate\": 1",
    ] {
        // S03 regeneration JSON nests the S02 input pins verbatim.
        assert_contains(S03_REGENERATION_JSON, expected, "frozen S03 input pins");
    }
    assert_contains(
        S03_REGENERATION_JSON,
        "R035 stays active",
        "frozen S03 non-claim",
    );
    assert_contains(
        S03_REGENERATION_JSON,
        S02_JSON_SHA256,
        "frozen S03 cites S02 sha256",
    );
    assert_contains(
        S03_REGENERATION_JSON,
        ADMISSIONS_YAML_SHA256,
        "frozen S03 cites admissions sha256",
    );
    assert_contains(
        ADMISSIONS_YAML,
        "authoritative: false",
        "frozen admissions pin",
    );
    assert_contains(REGISTRY_YAML, "authoritative: false", "frozen registry pin");
}
