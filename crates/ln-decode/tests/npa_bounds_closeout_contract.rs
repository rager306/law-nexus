//! M200 S04/T01 closeout contract suite.
//!
//! Pins the tracked closeout artifact
//! `prd/migration/rust-evidence/m200-s04-contract-reconciliation.json`
//! against the frozen S02/S03 evidence bytes and the accepted S03 gate
//! review (D400/D402): closed top-level schema, pure ASCII count-only
//! bytes, exactly 16 gate actions in G01..G16 document order mirroring the
//! S03 verdicts, and a live sha256 recompute over the three frozen
//! artifacts. Everything fails closed: unknown keys, non-ASCII bytes,
//! lifecycle drift, gate count/order drift, or sha256 drift.
//!
//! JSON parsing reuses the single shared D328 parser (`npa_support::parse_json`;
//! M200 S03/T01 rework F1 — no second JSON implementation, no crate
//! dependencies). The only local crypto is a tiny stdlib sha256 used for
//! live recompute; it self-validates in `t01` against the pinned scan digest
//! produced by sha256sum. YAML mutation assertions intentionally do not
//! exist yet: they land in T02/T03 on top of this suite.

#[allow(dead_code)]
mod npa_support;

use std::fs;

use npa_support::{repo_root, Json};

const CLOSEOUT_REL: &str = "prd/migration/rust-evidence/m200-s04-contract-reconciliation.json";
const SCAN_REL: &str = "prd/migration/rust-evidence/m200-s02-npa-bounds-scan.jsonl";
const ACCEPTANCE_REL: &str = "prd/migration/rust-evidence/m200-s02-corpus-acceptance.json";
const REVIEW_REL: &str = "prd/migration/rust-evidence/m200-s03-outlier-review.json";

const CLOSEOUT_SCHEMA: &str = "m200-s04-contract-reconciliation/v1";
const CLOSEOUT_LIFECYCLE: &str = "[proposed]";
const MILESTONE: &str = "M200-8s4kwq";
const SLICE: &str = "S04";
const TASK: &str = "T01";
const OWNER_DECISION: &str = "D402";

const SCAN_SHA256_PIN: &str = "3c76b3feb610adc5169d67aeb43a77dbecbd30fb1cac118918eff2a7f1863f6c";
const SCAN_LINE_COUNT_PIN: u64 = 15;
const SCAN_LIFECYCLE_PIN: &str = "[diagnostic]";
const ACCEPTANCE_SHA256_PIN: &str =
    "028335b6b3b8b50b5941fae7258408827ed44356bbbaee4eff060a12456a268f";
const REVIEW_SCHEMA_PIN: &str = "m200-s03-outlier-review/v1";
const REVIEW_LIFECYCLE_PIN: &str = "[proposed]";
const PROFILE_SCHEMA_PIN: &str = "law-nexus-npa-bounds-scanner-profile/v1";
const PROFILE_HASH_AT_SCAN_PIN: &str = "fnv1a64:bcf61bc0940f3cb9";
const MEASUREMENT_DEFS_HASH_PIN: &str = "fnv1a64:6fa01374f8c3ad65";
const SCANNER_SOURCE_HASH_PIN: &str = "fnv1a64:ee015b5f2f79c4e3";

const G02_CEILING_PIN: u64 = 1024;
const G02_OBSERVED_MAX_PIN: u64 = 504;
const G02_P999_EDGE_PIN: u64 = 14;
const G02_REFUSAL_DIAGNOSTIC_PIN: &str = "candidate_limit_reached";
const G02_BLOCK_HASH_PIN: &str = "fnv1a64:fec98440b4f3ae75";
const G14_PARTIAL_OVERLAP_PIN: &str = "539";
const G14_DISJOINT_PIN: &str = "10962245";

/// Closed top-level key set: unknown keys fail, missing keys fail.
const CLOSEOUT_TOP_LEVEL_KEYS: [&str; 17] = [
    "schema",
    "schema_version",
    "lifecycle",
    "milestone",
    "slice",
    "task",
    "owner_decision",
    "generated_utc",
    "count_only",
    "ascii_only",
    "non_claims",
    "source_binding",
    "order_agreed",
    "gate_actions",
    "yaml_mutations",
    "runtime_stop",
    "non_closures",
];

/// Closed per-row key set for every gate_actions entry.
const GATE_ACTION_KEYS: [&str; 9] = [
    "gate_id",
    "gate",
    "review_verdict",
    "selection_kind",
    "action",
    "yaml_path",
    "proposed_value",
    "refusal_diagnostic",
    "citation",
];

/// Every gate row must cite one of the six real tracked architecture files.
const ARCHITECTURE_YAML_PATHS: [&str; 6] = [
    "prd/architecture/current-document-requisites.yaml",
    "prd/architecture/npa-bounds-scanner-profile.yaml",
    "prd/architecture/npa-capture-arbitration.yaml",
    "prd/architecture/npa-document-context.yaml",
    "prd/architecture/npa-identifying-cycle.yaml",
    "prd/architecture/npa-semantic-process.yaml",
];

/// D402 mapping: write-proposed only G02; keep-categorical G01/G14; the
/// remaining 13 rows keep their gates deferred-undefined.
fn expected_action(gate_id: &str) -> &'static str {
    match gate_id {
        "G01" | "G14" => "keep-categorical",
        "G02" => "write-proposed",
        "G03" | "G04" | "G05" | "G06" | "G07" | "G08" | "G09" | "G10" | "G11" | "G12" | "G13"
        | "G15" | "G16" => "keep-deferred",
        other => panic!("unexpected gate id '{other}' outside the closed G01..G16 set"),
    }
}

fn read_repo_bytes(relative: &str) -> Vec<u8> {
    let path = repo_root().join(relative);
    fs::read(&path).unwrap_or_else(|err| panic!("read {}: {err}", path.display()))
}

fn parse_repo_json(relative: &str) -> Json {
    let bytes = read_repo_bytes(relative);
    let text = String::from_utf8(bytes).unwrap_or_else(|_| panic!("{relative} is not valid UTF-8"));
    npa_support::parse_json(&text).unwrap_or_else(|err| panic!("parse {relative}: {err}"))
}

fn field<'a>(value: &'a Json, key: &str, context: &str) -> &'a Json {
    value
        .get(key)
        .unwrap_or_else(|err| panic!("{context}: {err}"))
}

fn expect_str<'a>(value: &'a Json, key: &str, context: &str) -> &'a str {
    field(value, key, context)
        .as_str()
        .unwrap_or_else(|err| panic!("{context}.{key}: {err}"))
}

fn expect_num(value: &Json, key: &str, context: &str) -> u64 {
    match field(value, key, context) {
        Json::Num(raw) => raw
            .parse::<u64>()
            .unwrap_or_else(|_| panic!("{context}.{key}: '{raw}' is not a u64")),
        other => panic!("{context}.{key}: expected a number, found {other:?}"),
    }
}

/// String-or-null mirror of an S03 review field.
fn str_or_null(value: &Json, key: &str, context: &str) -> Option<String> {
    match field(value, key, context) {
        Json::Null => None,
        Json::Str(text) => Some(text.clone()),
        other => panic!("{context}.{key}: expected string or null, found {other:?}"),
    }
}

/// Number-or-null mirror of an S03 review field.
fn num_or_null(value: &Json, key: &str, context: &str) -> Option<u64> {
    match field(value, key, context) {
        Json::Null => None,
        Json::Num(raw) => Some(
            raw.parse::<u64>()
                .unwrap_or_else(|_| panic!("{context}.{key}: '{raw}' is not a u64")),
        ),
        other => panic!("{context}.{key}: expected number or null, found {other:?}"),
    }
}

fn first_non_ascii_offset(bytes: &[u8]) -> Option<usize> {
    bytes.iter().position(|&byte| byte >= 0x80)
}

fn assert_ascii(bytes: &[u8], label: &str) {
    if let Some(offset) = first_non_ascii_offset(bytes) {
        panic!("{label} carries a non-ASCII byte at offset {offset}");
    }
}

/// `Json::Bool` is unit-valued (D328), so exact booleans are asserted with
/// narrow raw-text markers after the structured parse.
fn assert_raw_marker(raw: &str, marker: &str) {
    assert!(
        raw.contains(marker),
        "raw closeout text must contain `{marker}`"
    );
}

// ---------------------------------------------------------------------------
// Tiny stdlib sha256 (live recompute only; self-checked in t01 against the
// sha256sum pin of the frozen scan bytes).
// ---------------------------------------------------------------------------

#[allow(clippy::chunks_exact_to_as_chunks)]
fn sha256_hex(data: &[u8]) -> String {
    const K: [u32; 64] = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
        0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
        0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
        0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
        0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
        0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
        0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
        0xc67178f2,
    ];
    let mut state: [u32; 8] = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab,
        0x5be0cd19,
    ];
    let bit_len = (data.len() as u64).wrapping_mul(8);
    let mut message = data.to_vec();
    message.push(0x80);
    while message.len() % 64 != 56 {
        message.push(0);
    }
    message.extend_from_slice(&bit_len.to_be_bytes());
    for chunk in message.chunks_exact(64) {
        let mut schedule = [0u32; 64];
        for (index, word) in chunk.chunks_exact(4).enumerate() {
            schedule[index] = u32::from_be_bytes([word[0], word[1], word[2], word[3]]);
        }
        for index in 16..64 {
            let s0 = schedule[index - 15].rotate_right(7)
                ^ schedule[index - 15].rotate_right(18)
                ^ (schedule[index - 15] >> 3);
            let s1 = schedule[index - 2].rotate_right(17)
                ^ schedule[index - 2].rotate_right(19)
                ^ (schedule[index - 2] >> 10);
            schedule[index] = schedule[index - 16]
                .wrapping_add(s0)
                .wrapping_add(schedule[index - 7])
                .wrapping_add(s1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h) = (
            state[0], state[1], state[2], state[3], state[4], state[5], state[6], state[7],
        );
        for index in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[index])
                .wrapping_add(schedule[index]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        state[0] = state[0].wrapping_add(a);
        state[1] = state[1].wrapping_add(b);
        state[2] = state[2].wrapping_add(c);
        state[3] = state[3].wrapping_add(d);
        state[4] = state[4].wrapping_add(e);
        state[5] = state[5].wrapping_add(f);
        state[6] = state[6].wrapping_add(g);
        state[7] = state[7].wrapping_add(h);
    }
    state.iter().map(|word| format!("{word:08x}")).collect()
}

// ---------------------------------------------------------------------------
// T01 tests. t01: source binding matches the frozen bytes. t02: closed
// schema, ASCII-only, count-only. t03: 16 gate actions mirror the S03
// verdicts under the D402 action mapping.
// ---------------------------------------------------------------------------

#[test]
fn t01_closeout_source_binding_matches_frozen_bytes() {
    let closeout = parse_repo_json(CLOSEOUT_REL);
    closeout
        .require_keys(&CLOSEOUT_TOP_LEVEL_KEYS, "closeout")
        .expect("closed top-level schema");
    let binding = field(&closeout, "source_binding", "closeout");
    binding
        .require_keys(
            &[
                "scan_artifact",
                "acceptance_artifact",
                "review_artifact",
                "profile_schema",
                "profile_hash_at_scan",
                "measurement_definitions_hash",
                "scanner_source_hash",
                "corpus_opened_by_this_closeout",
            ],
            "source_binding",
        )
        .expect("closed source_binding schema");

    // Frozen scan bytes: the local sha256_hex is self-validated here against
    // the sha256sum pin; any drift in either fails closed.
    let scan_bytes = read_repo_bytes(SCAN_REL);
    let scan_hash = sha256_hex(&scan_bytes);
    assert_eq!(
        scan_hash, SCAN_SHA256_PIN,
        "live scan JSONL bytes drifted vs the S03 pin (or the local sha256_hex is wrong)"
    );
    let scan_entry = field(binding, "scan_artifact", "source_binding");
    scan_entry
        .require_keys(
            &["path", "sha256", "line_count", "lifecycle"],
            "scan_artifact",
        )
        .expect("closed scan_artifact schema");
    assert_eq!(expect_str(scan_entry, "path", "scan_artifact"), SCAN_REL);
    assert_eq!(
        expect_str(scan_entry, "sha256", "scan_artifact"),
        SCAN_SHA256_PIN
    );
    assert_eq!(
        expect_num(scan_entry, "line_count", "scan_artifact"),
        SCAN_LINE_COUNT_PIN
    );
    assert_eq!(
        expect_str(scan_entry, "lifecycle", "scan_artifact"),
        SCAN_LIFECYCLE_PIN
    );
    let scan_text = String::from_utf8(scan_bytes).expect("scan JSONL is UTF-8");
    let scan_lines: Vec<&str> = scan_text
        .lines()
        .filter(|line| !line.trim().is_empty())
        .collect();
    assert_eq!(
        scan_lines.len() as u64,
        SCAN_LINE_COUNT_PIN,
        "live scan JSONL line count drifted"
    );
    let scan_header = npa_support::parse_json(scan_lines[0]).expect("scan header record parses");
    assert_eq!(
        expect_str(&scan_header, "record_kind", "scan header"),
        "header"
    );
    assert_eq!(
        expect_str(&scan_header, "lifecycle", "scan header"),
        SCAN_LIFECYCLE_PIN
    );
    assert_eq!(
        expect_str(&scan_header, "profile_hash", "scan header"),
        PROFILE_HASH_AT_SCAN_PIN
    );
    let scan_manifest = npa_support::parse_json(scan_lines[scan_lines.len() - 1])
        .expect("scan run_manifest record parses");
    assert_eq!(
        expect_str(&scan_manifest, "record_kind", "scan manifest"),
        "run_manifest"
    );
    assert_eq!(
        expect_str(&scan_manifest, "lifecycle", "scan manifest"),
        SCAN_LIFECYCLE_PIN
    );
    assert_eq!(
        expect_str(&scan_manifest, "scanner_source_hash", "scan manifest"),
        SCANNER_SOURCE_HASH_PIN
    );
    assert_eq!(
        expect_str(
            &scan_manifest,
            "measurement_definitions_hash",
            "scan manifest"
        ),
        MEASUREMENT_DEFS_HASH_PIN
    );

    // Frozen acceptance bytes and their own binding to the scan bytes.
    let acceptance_bytes = read_repo_bytes(ACCEPTANCE_REL);
    let acceptance_hash = sha256_hex(&acceptance_bytes);
    assert_eq!(
        acceptance_hash, ACCEPTANCE_SHA256_PIN,
        "live acceptance bytes drifted vs the S03 pin"
    );
    let acceptance_entry = field(binding, "acceptance_artifact", "source_binding");
    acceptance_entry
        .require_keys(&["path", "sha256"], "acceptance_artifact")
        .expect("closed acceptance_artifact schema");
    assert_eq!(
        expect_str(acceptance_entry, "path", "acceptance_artifact"),
        ACCEPTANCE_REL
    );
    assert_eq!(
        expect_str(acceptance_entry, "sha256", "acceptance_artifact"),
        ACCEPTANCE_SHA256_PIN
    );
    let acceptance_text =
        String::from_utf8(acceptance_bytes).expect("acceptance artifact is UTF-8");
    let acceptance = npa_support::parse_json(&acceptance_text).expect("acceptance parses");
    assert_eq!(
        expect_str(
            field(&acceptance, "artifact_under_acceptance", "acceptance"),
            "sha256",
            "acceptance.artifact_under_acceptance"
        ),
        SCAN_SHA256_PIN,
        "the acceptance artifact must keep binding the same frozen scan bytes"
    );

    // Frozen review bytes: schema/lifecycle pins, recorded digest, and the
    // scan-time hashes copied from the review source_binding.
    let review_bytes = read_repo_bytes(REVIEW_REL);
    let review_hash = sha256_hex(&review_bytes);
    let review = parse_repo_json(REVIEW_REL);
    assert_eq!(expect_str(&review, "schema", "review"), REVIEW_SCHEMA_PIN);
    assert_eq!(
        expect_str(&review, "lifecycle", "review"),
        REVIEW_LIFECYCLE_PIN
    );
    let review_entry = field(binding, "review_artifact", "source_binding");
    review_entry
        .require_keys(
            &["path", "schema", "lifecycle", "sha256"],
            "review_artifact",
        )
        .expect("closed review_artifact schema");
    assert_eq!(
        expect_str(review_entry, "path", "review_artifact"),
        REVIEW_REL
    );
    assert_eq!(
        expect_str(review_entry, "schema", "review_artifact"),
        REVIEW_SCHEMA_PIN
    );
    assert_eq!(
        expect_str(review_entry, "lifecycle", "review_artifact"),
        REVIEW_LIFECYCLE_PIN
    );
    assert_eq!(
        expect_str(review_entry, "sha256", "review_artifact"),
        review_hash,
        "review artifact bytes drifted since the closeout was written"
    );
    let review_binding = field(&review, "source_binding", "review");
    assert_eq!(
        expect_str(binding, "profile_schema", "source_binding"),
        PROFILE_SCHEMA_PIN
    );
    assert_eq!(
        expect_str(binding, "profile_schema", "source_binding"),
        expect_str(review_binding, "profile_schema", "review.source_binding")
    );
    assert_eq!(
        expect_str(binding, "profile_hash_at_scan", "source_binding"),
        PROFILE_HASH_AT_SCAN_PIN
    );
    assert_eq!(
        expect_str(binding, "profile_hash_at_scan", "source_binding"),
        expect_str(
            review_binding,
            "profile_hash_at_scan",
            "review.source_binding"
        )
    );
    assert_eq!(
        expect_str(binding, "measurement_definitions_hash", "source_binding"),
        MEASUREMENT_DEFS_HASH_PIN
    );
    assert_eq!(
        expect_str(binding, "measurement_definitions_hash", "source_binding"),
        expect_str(
            review_binding,
            "measurement_definitions_hash",
            "review.source_binding"
        )
    );
    // scanner_source_hash has no review-side copy: it is pinned from the
    // scan run_manifest above.
    assert_eq!(
        expect_str(binding, "scanner_source_hash", "source_binding"),
        SCANNER_SOURCE_HASH_PIN
    );

    // The closeout itself opened no corpus.
    let closeout_raw = String::from_utf8(read_repo_bytes(CLOSEOUT_REL)).expect("closeout is UTF-8");
    assert_raw_marker(&closeout_raw, "\"corpus_opened_by_this_closeout\": false");
}

#[test]
fn t02_closeout_closed_schema_ascii_count_only() {
    let bytes = read_repo_bytes(CLOSEOUT_REL);
    assert_ascii(&bytes, CLOSEOUT_REL);
    let raw = String::from_utf8(bytes).expect("closeout is UTF-8");

    // count-only: no corpus tree, no host paths, no Windows paths.
    for forbidden in ["consru_export", "/root/", "law-source/", "C:\\"] {
        assert!(
            !raw.contains(forbidden),
            "closeout must not contain the forbidden substring '{forbidden}'"
        );
    }

    let closeout = npa_support::parse_json(&raw).expect("closeout parses");
    closeout
        .require_keys(&CLOSEOUT_TOP_LEVEL_KEYS, "closeout")
        .expect("closed top-level schema");
    for key in CLOSEOUT_TOP_LEVEL_KEYS {
        assert!(
            closeout
                .get_opt(key)
                .expect("closeout is an object")
                .is_some(),
            "closeout is missing the required key '{key}'"
        );
    }

    // Fixed scalars (D402).
    assert_eq!(expect_str(&closeout, "schema", "closeout"), CLOSEOUT_SCHEMA);
    assert_eq!(expect_num(&closeout, "schema_version", "closeout"), 1);
    assert_eq!(
        expect_str(&closeout, "lifecycle", "closeout"),
        CLOSEOUT_LIFECYCLE,
        "closeout lifecycle must stay [proposed]"
    );
    assert_eq!(expect_str(&closeout, "milestone", "closeout"), MILESTONE);
    assert_eq!(expect_str(&closeout, "slice", "closeout"), SLICE);
    assert_eq!(expect_str(&closeout, "task", "closeout"), TASK);
    assert_eq!(
        expect_str(&closeout, "owner_decision", "closeout"),
        OWNER_DECISION
    );
    let generated = expect_str(&closeout, "generated_utc", "closeout");
    assert!(
        generated.starts_with("2026-") && generated.ends_with('Z'),
        "generated_utc '{generated}' must be a UTC timestamp"
    );

    // Json::Bool is unit-valued: exact booleans via raw markers.
    assert_raw_marker(&raw, "\"count_only\": true");
    assert_raw_marker(&raw, "\"ascii_only\": true");
    assert_raw_marker(&raw, "\"order_agreed\": true");

    // The five required honesty claims.
    let claims = field(&closeout, "non_claims", "closeout")
        .as_arr()
        .expect("non_claims array");
    assert!(
        claims.len() >= 5,
        "non_claims must carry at least the five required claims"
    );
    const REQUIRED_NON_CLAIMS: [&str; 5] = [
        "stays [diagnostic]",
        "stay [proposed]",
        "not a product-path bound",
        "step 7",
        "no R035, R070 or N2",
    ];
    for required in REQUIRED_NON_CLAIMS {
        assert!(
            claims
                .iter()
                .filter_map(|claim| claim.as_str().ok())
                .any(|claim| claim.contains(required)),
            "non_claims is missing '{required}'"
        );
    }

    // Fail-closed gate count.
    let actions = field(&closeout, "gate_actions", "closeout")
        .as_arr()
        .expect("gate_actions array");
    assert_eq!(
        actions.len(),
        16,
        "gate_actions must hold exactly the 16 rows G01..G16"
    );

    // yaml_mutations rows stay inside the closed schema and cite real
    // architecture files (content assertions are T02/T03 scope).
    let mutations = field(&closeout, "yaml_mutations", "closeout")
        .as_arr()
        .expect("yaml_mutations array");
    assert_eq!(
        mutations.len(),
        5,
        "yaml_mutations holds the G02 cardinality record plus the four stale runtime_stop reasons"
    );
    for (index, row) in mutations.iter().enumerate() {
        let context = format!("yaml_mutations[{index}]");
        row.require_keys(
            &["yaml_path", "mutation_kind", "stale_reason", "note"],
            &context,
        )
        .expect("closed yaml_mutations row schema");
        let yaml_path = expect_str(row, "yaml_path", &context);
        assert!(
            ARCHITECTURE_YAML_PATHS.contains(&yaml_path),
            "{context}: unknown architecture yaml_path '{yaml_path}'"
        );
        assert!(
            repo_root().join(yaml_path).is_file(),
            "{context}: yaml_path '{yaml_path}' is missing on disk"
        );
    }

    // runtime_stop and non_closures keep their closed schemas; the S03-true
    // remaining_reasons list has exactly six entries.
    let stop = field(&closeout, "runtime_stop", "closeout");
    stop.require_keys(&["active", "remaining_reasons"], "runtime_stop")
        .expect("closed runtime_stop schema");
    let stop_reasons = field(stop, "remaining_reasons", "runtime_stop")
        .as_arr()
        .expect("remaining_reasons array");
    assert_eq!(
        stop_reasons.len(),
        6,
        "the S03-true remaining_reasons list has exactly six entries"
    );
    let closures = field(&closeout, "non_closures", "closeout");
    closures
        .require_keys(&["requirements", "gates", "note"], "non_closures")
        .expect("closed non_closures schema");
}

#[test]
fn t03_sixteen_gate_actions_match_s03_verdicts() {
    let closeout = parse_repo_json(CLOSEOUT_REL);
    let review = parse_repo_json(REVIEW_REL);
    let actions = field(&closeout, "gate_actions", "closeout")
        .as_arr()
        .expect("gate_actions array");
    let decisions = field(&review, "gate_decisions", "review")
        .as_arr()
        .expect("gate_decisions array");
    assert_eq!(actions.len(), 16);
    assert_eq!(decisions.len(), 16);

    for index in 0..16 {
        let row = &actions[index];
        let decision = &decisions[index];
        let context = format!("gate_actions[{index}]");
        row.require_keys(&GATE_ACTION_KEYS, &context)
            .expect("closed gate row schema");
        for key in GATE_ACTION_KEYS {
            assert!(
                row.get_opt(key).expect("gate row is an object").is_some(),
                "{context}: missing key '{key}'"
            );
        }
        let gate_id = format!("G{:02}", index + 1);
        assert_eq!(
            expect_str(row, "gate_id", &context),
            gate_id,
            "gate rows must stay in G01..G16 document order"
        );
        assert_eq!(expect_str(decision, "gate_id", "review"), gate_id);
        // The S03 verdict, gate name, selection kind, proposed value and
        // refusal diagnostic are mirrored from the accepted review, never
        // reinvented.
        assert_eq!(
            expect_str(row, "gate", &context),
            expect_str(decision, "gate", "review")
        );
        assert_eq!(
            expect_str(row, "review_verdict", &context),
            expect_str(decision, "verdict", "review")
        );
        assert_eq!(
            str_or_null(row, "selection_kind", &context),
            str_or_null(decision, "selection_kind", "review")
        );
        assert_eq!(
            num_or_null(row, "proposed_value", &context),
            num_or_null(decision, "proposed_value", "review")
        );
        assert_eq!(
            str_or_null(row, "refusal_diagnostic", &context),
            str_or_null(decision, "refusal_diagnostic", "review")
        );
        // The D402 action mapping.
        assert_eq!(
            expect_str(row, "action", &context),
            expected_action(&gate_id)
        );
        // The cited YAML is a real tracked architecture file.
        let yaml_path = expect_str(row, "yaml_path", &context);
        assert!(
            ARCHITECTURE_YAML_PATHS.contains(&yaml_path),
            "{context}: unknown architecture yaml_path '{yaml_path}'"
        );
        assert!(
            repo_root().join(yaml_path).is_file(),
            "{context}: yaml_path '{yaml_path}' is missing on disk"
        );
        assert!(
            !expect_str(row, "citation", &context).is_empty(),
            "{context}: citation must be non-empty"
        );
    }

    // G01: categorical invariants stay test-enforced across three contracts.
    let g01 = &actions[0];
    assert_eq!(
        expect_str(g01, "yaml_path", "G01"),
        "prd/architecture/npa-document-context.yaml"
    );
    let g01_citation = expect_str(g01, "citation", "G01");
    for required in [
        "expansion_policy=endpoint_pair",
        "covering-span",
        "no numeric runtime bound",
    ] {
        assert!(
            g01_citation.contains(required),
            "G01 citation is missing '{required}'"
        );
    }

    // G02: the single write-proposed row pins the safety ceiling, never the
    // observed max nor the p999 bucket edge.
    let g02 = &actions[1];
    assert_eq!(
        expect_str(g02, "yaml_path", "G02"),
        "prd/architecture/npa-capture-arbitration.yaml"
    );
    let ceiling = expect_num(g02, "proposed_value", "G02");
    assert_eq!(ceiling, G02_CEILING_PIN);
    assert_ne!(
        ceiling, G02_OBSERVED_MAX_PIN,
        "the ceiling must never be lowered to the observed max"
    );
    assert_ne!(
        ceiling, G02_P999_EDGE_PIN,
        "the ceiling must never be lowered to the p999 bucket edge"
    );
    assert_eq!(
        expect_str(g02, "refusal_diagnostic", "G02"),
        G02_REFUSAL_DIAGNOSTIC_PIN
    );
    let g02_citation = expect_str(g02, "citation", "G02");
    for required in ["504", G02_BLOCK_HASH_PIN, "headroom", "p999", "[proposed]"] {
        assert!(
            g02_citation.contains(required),
            "G02 citation is missing '{required}'"
        );
    }

    // G14: categorical arbitration defaults cite the S02 span_relations counts.
    let g14 = &actions[13];
    assert_eq!(
        expect_str(g14, "yaml_path", "G14"),
        "prd/architecture/npa-capture-arbitration.yaml"
    );
    let g14_citation = expect_str(g14, "citation", "G14");
    for required in [G14_PARTIAL_OVERLAP_PIN, G14_DISJOINT_PIN] {
        assert!(
            g14_citation.contains(required),
            "G14 citation is missing '{required}'"
        );
    }

    // G15/G16 yaml targets.
    assert_eq!(
        expect_str(&actions[14], "yaml_path", "G15"),
        "prd/architecture/current-document-requisites.yaml"
    );
    assert_eq!(
        expect_str(&actions[15], "yaml_path", "G16"),
        "prd/architecture/npa-bounds-scanner-profile.yaml"
    );
}

// ---------------------------------------------------------------------------
// T03 transition pins (t04..t11). Everything here is read-only over tracked
// bytes: all 16 gate rows bound to the six YAML contracts, runtime_stop kept
// active with the stale reasons gone, the unwired product path, the
// diagnostic/proposed lifecycles, the R035/R070/N2 non-closures, the
// load-bearing deferred literals, the P0..P9 pipeline order, and fail-closed
// tampering of the closeout bytes.
// ---------------------------------------------------------------------------

/// Loads a tracked repo file as UTF-8 text, failing closed with its path.
fn repo_text(relative: &str) -> String {
    String::from_utf8(read_repo_bytes(relative))
        .unwrap_or_else(|_| panic!("{relative} is not valid UTF-8"))
}

/// The architecture YAML each gate row must cite (the D402 closeout table).
fn gate_yaml_path(gate_id: &str) -> &'static str {
    match gate_id {
        "G01" | "G08" | "G09" | "G10" | "G11" => "prd/architecture/npa-document-context.yaml",
        "G02" | "G12" | "G13" | "G14" => "prd/architecture/npa-capture-arbitration.yaml",
        "G03" | "G04" | "G05" | "G16" => "prd/architecture/npa-bounds-scanner-profile.yaml",
        "G06" | "G07" => "prd/architecture/npa-identifying-cycle.yaml",
        "G15" => "prd/architecture/current-document-requisites.yaml",
        other => panic!("unexpected gate id '{other}' outside G01..G16"),
    }
}

/// Load-bearing literals each gate row must still find in its cited YAML
/// (the T02 evidence-linked edits; every needle was grep-verified).
fn gate_yaml_needles(gate_id: &str) -> Vec<&'static str> {
    match gate_id {
        "G01" => vec![
            "request_kinds: [ancestor_path, adjacent_blocks, open_series_head, scoped_alias,",
            "current_document_requisites, explicit_anchor_lookup]",
        ],
        "G02" => vec![
            "G02 safety ceiling is [proposed] at 1024 candidates per block",
            G02_REFUSAL_DIAGNOSTIC_PIN,
            "observed max 504",
            G02_BLOCK_HASH_PIN,
            "never lowered to the observed max or the p999 bucket edge 14",
            "product path unwired in capture_lawrefs",
        ],
        "G03" | "G04" | "G05" => vec!["G03-G05, G16"],
        "G06" => vec![
            "G06 (max-members-coordinating-frame)",
            "not a members bound",
        ],
        "G07" => vec!["G07 (max-expanded-candidates)", "0/1 bit"],
        "G08" => vec!["adjacent_block_radius: deferred-undefined"],
        "G09" => vec!["max_series_hops: deferred-undefined"],
        "G10" => vec!["max_alias_candidates: deferred-undefined"],
        "G11" => vec!["max_context_claims_per_field: deferred-undefined"],
        "G12" | "G13" => vec!["pair_policies:\n  status: deferred-undefined"],
        "G14" => vec![
            "- when: partial_overlap\n    action: retain_conflict_set",
            "- when: disjoint\n    action: retain_both",
        ],
        "G15" => vec![
            "source_authority_policy:\n  status: deferred-undefined",
            "default: no winner; expose conflict",
        ],
        "G16" => vec!["top_k: deferred-undefined"],
        other => panic!("unexpected gate id '{other}' outside G01..G16"),
    }
}

#[test]
fn t04_sixteen_gate_actions_bind_yaml_literals() {
    let closeout = parse_repo_json(CLOSEOUT_REL);
    let actions = field(&closeout, "gate_actions", "closeout")
        .as_arr()
        .expect("gate_actions array");
    assert_eq!(actions.len(), 16, "the closeout table must keep 16 rows");

    let mut yaml_cache: std::collections::BTreeMap<String, String> = Default::default();
    for (index, row) in actions.iter().enumerate() {
        let gate_id = expect_str(row, "gate_id", "gate row");
        let context = format!("gate_actions[{index}] ({gate_id})");
        let cited = expect_str(row, "yaml_path", &context);
        assert_eq!(
            cited,
            gate_yaml_path(gate_id),
            "{context}: cited yaml_path drifted from the D402 table"
        );
        let text = yaml_cache
            .entry(cited.to_owned())
            .or_insert_with(|| repo_text(cited));
        for needle in gate_yaml_needles(gate_id) {
            assert!(
                text.contains(needle),
                "{context}: the cited YAML lost the load-bearing literal '{needle}'"
            );
        }
    }

    // G01's citation spans three contracts: endpoint-pair expansion lives in
    // the cycle contract, the closed covering-span relations in arbitration.
    let cycle = repo_text("prd/architecture/npa-identifying-cycle.yaml");
    assert!(
        cycle.contains("expansion_policy: endpoint_pair"),
        "G01 sibling invariant 'expansion_policy: endpoint_pair' is missing"
    );
    let arbitration = repo_text("prd/architecture/npa-capture-arbitration.yaml");
    for needle in [
        "same_span:",
        "strictly_contains:",
        "strictly_contained_by:",
        "partial_overlap:",
        "disjoint:",
    ] {
        assert!(
            arbitration.contains(needle),
            "G01 sibling covering-span relation '{needle}' is missing"
        );
    }
}

#[test]
fn t05_runtime_stop_stays_active_and_stale_reasons_are_absent() {
    for path in [
        "prd/architecture/npa-capture-arbitration.yaml",
        "prd/architecture/npa-semantic-process.yaml",
        "prd/architecture/npa-bounds-scanner-profile.yaml",
        "prd/architecture/current-document-requisites.yaml",
    ] {
        let text = repo_text(path);
        assert!(
            text.contains("runtime_stop:\n  active: true"),
            "{path}: runtime_stop must stay active for open runtime work"
        );
    }
    let closeout_raw = repo_text(CLOSEOUT_REL);
    assert!(
        closeout_raw.contains("\"active\": true"),
        "closeout runtime_stop.active must stay true (D403)"
    );

    // The four pre-S03 stale phrases recorded in the T01 yaml_mutations table
    // must be gone from every architecture contract (T02 replacements).
    const STALE: [&str; 5] = [
        "candidate cardinality bound is deferred-undefined",
        "hostile/pin tests are not implemented or accepted",
        "hostile contracts and full-corpus measurement are not yet accepted",
        "outlier review of maxima/top-K anchors is S03 scope and numeric bound selection stays deferred-undefined",
        "hostile contracts are not implemented or accepted",
    ];
    for path in ARCHITECTURE_YAML_PATHS {
        let text = repo_text(path);
        for stale in STALE {
            assert!(
                !text.contains(stale),
                "{path}: stale runtime_stop reason is still present: '{stale}'"
            );
        }
    }

    // The replacements are evidence-linked, not silent deletions.
    let arbitration = repo_text("prd/architecture/npa-capture-arbitration.yaml");
    assert!(
        arbitration.contains("hostile/pin contracts are accepted"),
        "arbitration must cite the accepted S03 hostile suite"
    );
    let process = repo_text("prd/architecture/npa-semantic-process.yaml");
    assert!(
        process.contains("hostile contracts are accepted (S03 suite 16/16)"),
        "semantic-process must cite the accepted S03 hostile suite"
    );
    let requisites = repo_text("prd/architecture/current-document-requisites.yaml");
    assert!(
        requisites.contains("S03 test-contract seeds exist"),
        "requisites must cite the S03 test-contract seeds"
    );
}

#[test]
fn t06_lawref_capture_path_stays_unwired() {
    // D403: the G02 [proposed] ceiling and the pair-policy helpers stay out
    // of the product path until the runtime stop clears (assessment/29 step
    // 8+); the ceiling number must not appear in capture_lawrefs.
    let lawref = repo_text("crates/ln-decode/src/lawref.rs");
    assert!(
        lawref.contains("pub fn capture_lawrefs"),
        "expected the capture_lawrefs surface to still exist"
    );
    for forbidden in [
        "PROPOSED_CANDIDATE_CEILING",
        "on_candidate_limit",
        "arbitrate_pair",
        "candidate_limit_reached",
    ] {
        assert!(
            !lawref.contains(forbidden),
            "lawref.rs must not reference '{forbidden}' (G02 ceiling stays unwired)"
        );
    }
    // The reviewed helpers now live in capture_bounds.rs and are explicitly
    // re-exported from npa_bounds.rs (hostile t15 pins their values); they
    // are simply never called from the product path.
    let bounds = repo_text("crates/ln-decode/src/npa_bounds.rs");
    assert!(
        bounds.contains("PROPOSED_CANDIDATE_CEILING"),
        "the reviewed ceiling helper must stay defined in npa_bounds.rs"
    );
}

#[test]
fn t07_lifecycles_stay_diagnostic_and_proposed() {
    // S02 JSONL stays [diagnostic]: measurement evidence, never a bound proof.
    let scan_header_line = repo_text(SCAN_REL)
        .lines()
        .next()
        .expect("scan JSONL header line")
        .to_owned();
    let scan_header = npa_support::parse_json(&scan_header_line).expect("scan header parses");
    assert_eq!(
        expect_str(&scan_header, "lifecycle", "scan header"),
        SCAN_LIFECYCLE_PIN
    );

    // The review and the closeout stay [proposed].
    assert_eq!(
        expect_str(&parse_repo_json(REVIEW_REL), "lifecycle", "review"),
        REVIEW_LIFECYCLE_PIN
    );
    assert_eq!(
        expect_str(&parse_repo_json(CLOSEOUT_REL), "lifecycle", "closeout"),
        CLOSEOUT_LIFECYCLE
    );

    // No architecture contract was promoted past [proposed].
    for path in ARCHITECTURE_YAML_PATHS {
        let text = repo_text(path);
        assert!(
            text.contains("lifecycle: \"[proposed]\""),
            "{path}: lifecycle must stay [proposed]"
        );
    }
}

#[test]
fn t08_non_closures_r035_r070_n2_stay_open() {
    let closeout = parse_repo_json(CLOSEOUT_REL);
    let non_closures = field(&closeout, "non_closures", "closeout");
    let requirements = field(non_closures, "requirements", "non_closures")
        .as_arr()
        .expect("requirements array");
    let ids: Vec<&str> = requirements
        .iter()
        .filter_map(|value| value.as_str().ok())
        .collect();
    assert_eq!(
        ids,
        vec!["R035", "R070"],
        "only R035 and R070 are non-closed requirements"
    );
    let gates = field(non_closures, "gates", "non_closures")
        .as_arr()
        .expect("gates array");
    let gate_ids: Vec<&str> = gates
        .iter()
        .filter_map(|value| value.as_str().ok())
        .collect();
    assert_eq!(
        gate_ids,
        vec!["N2-gate"],
        "only N2-gate is a non-closed gate"
    );
    let note = expect_str(non_closures, "note", "non_closures");
    assert!(
        note.contains("R038"),
        "the R038 standing-gate note (executed in S03) must survive"
    );

    // The runtime contracts still name the open items.
    let process = repo_text("prd/architecture/npa-semantic-process.yaml");
    assert!(
        process.contains("R035 and R070 remain active"),
        "semantic-process runtime_stop must keep R035/R070 open"
    );
    assert!(
        process.contains("N2 human dual coding remains incomplete"),
        "semantic-process runtime_stop must keep N2 open"
    );
    let profile = repo_text("prd/architecture/npa-bounds-scanner-profile.yaml");
    assert!(
        profile.contains("related: [D383, D384, D385, D387, ADR-0028, R035, R070]"),
        "profile must still list R035/R070 as related-open"
    );
}

#[test]
fn t09_load_bearing_deferred_literals_stay_byte_exact() {
    let pins: [(&str, &[&str]); 5] = [
        (
            "prd/architecture/npa-capture-arbitration.yaml",
            &[
                "pair_policies:\n  status: deferred-undefined",
                "default: retain candidates with ambiguous/conflict diagnostic; never silently suppress",
                "# Pair policy is data. Source function order is never precedence.",
                "- candidate_limit_reached",
            ],
        ),
        (
            "prd/architecture/current-document-requisites.yaml",
            &[
                "source_authority_policy:\n  status: deferred-undefined",
                "default: no winner; expose conflict",
            ],
        ),
        (
            "prd/architecture/npa-bounds-scanner-profile.yaml",
            &[
                "top_k: deferred-undefined",
                "- true CoordinatingFrame member count",
                "- true Cartesian frame expansion cardinality",
            ],
        ),
        (
            "prd/architecture/npa-document-context.yaml",
            &[
                "adjacent_block_radius: deferred-undefined",
                "max_series_hops: deferred-undefined",
                "max_alias_candidates: deferred-undefined",
                "max_context_claims_per_field: deferred-undefined",
                "max_linking_passes: 1",
            ],
        ),
        (
            "prd/architecture/npa-identifying-cycle.yaml",
            &[
                "max_members: deferred-undefined",
                "max_expanded_candidates: deferred-undefined",
                "continuation_hops: one unless a block coordinator materializes a proven longer chain",
            ],
        ),
    ];
    for (path, needles) in pins {
        let text = repo_text(path);
        for needle in needles.iter() {
            assert!(
                text.contains(needle),
                "{path}: load-bearing deferred literal drifted: '{needle}'"
            );
        }
    }
}

#[test]
fn t10_p0_p9_pipeline_order_stays_agreed() {
    let process = repo_text("prd/architecture/npa-semantic-process.yaml");
    const PHASES: [&str; 10] = [
        "id: P0_decode_complete_document",
        "id: P1_build_base_context",
        "id: P2_local_analysis",
        "id: P3_literal_projection",
        "id: P4_build_analysis_overlay",
        "id: P5_close_document_context",
        "id: P6_semantic_projection",
        "id: P7_identity_claim_projection",
        "id: P8_resolve_bindings",
        "id: P9_emit_proposed_evidence",
    ];
    let mut cursor = 0usize;
    for phase in PHASES {
        let at = process[cursor..]
            .find(phase)
            .unwrap_or_else(|| panic!("pipeline phase '{phase}' missing or out of order"));
        cursor += at + phase.len();
    }
    assert!(
        process.contains("P3_literal_projection precedes P5_close_document_context"),
        "order_invariants must keep P3 before P5"
    );
    let closeout_raw = repo_text(CLOSEOUT_REL);
    assert_raw_marker(&closeout_raw, "\"order_agreed\": true");
}

#[test]
fn t11_closeout_tampering_fails_closed() {
    let raw = repo_text(CLOSEOUT_REL);

    // An unknown top-level key must fail the closed-schema check.
    let brace = raw.find('{').expect("closeout is a JSON object");
    let mut injected = String::with_capacity(raw.len() + 40);
    injected.push_str(&raw[..=brace]);
    injected.push_str("\n  \"injected_key\": 1,");
    injected.push_str(&raw[brace + 1..]);
    let injected_json = npa_support::parse_json(&injected)
        .expect("injected copy must still be valid JSON before the schema check");
    let schema_err = injected_json
        .require_keys(&CLOSEOUT_TOP_LEVEL_KEYS, "closeout")
        .expect_err("an unknown top-level key must fail the closed schema");
    assert!(
        schema_err.contains("unexpected JSON key"),
        "closed-schema rejection must name the unknown key, got: {schema_err}"
    );

    // A duplicated key must be refused by the D328 parser, not last-wins.
    let duplicated = raw.replace(
        "\"order_agreed\": true",
        "\"order_agreed\": true, \"order_agreed\": true",
    );
    assert_ne!(
        duplicated, raw,
        "duplicate-key tamper must change the bytes"
    );
    let duplicate_err = npa_support::parse_json(&duplicated)
        .expect_err("a duplicated JSON key must fail closed at parse time");
    assert!(
        duplicate_err.contains("duplicate JSON object key"),
        "parser must reject duplicate keys, got: {duplicate_err}"
    );

    // One non-ASCII byte must be localized by the ASCII gate.
    let mut bytes = read_repo_bytes(CLOSEOUT_REL);
    let clean_len = bytes.len();
    bytes.push(0xD0);
    assert_eq!(
        first_non_ascii_offset(&bytes),
        Some(clean_len),
        "appended high byte must be localized"
    );
    assert_eq!(
        first_non_ascii_offset(&read_repo_bytes(CLOSEOUT_REL)),
        None,
        "the tracked closeout must stay pure ASCII"
    );

    // A lowered ceiling (the forbidden observed max) must miss the pin.
    let lowered = raw.replace("\"proposed_value\": 1024", "\"proposed_value\": 504");
    assert_ne!(lowered, raw, "ceiling tamper must change the bytes");
    let lowered_json = npa_support::parse_json(&lowered).expect("lowered copy parses");
    let lowered_actions = field(&lowered_json, "gate_actions", "lowered")
        .as_arr()
        .expect("gate_actions array");
    let tampered = expect_num(&lowered_actions[1], "proposed_value", "G02");
    assert_ne!(
        tampered, G02_CEILING_PIN,
        "the pin must reject the lowered ceiling"
    );
    assert_eq!(
        tampered, G02_OBSERVED_MAX_PIN,
        "the tamper must land exactly on the forbidden observed max"
    );
}
