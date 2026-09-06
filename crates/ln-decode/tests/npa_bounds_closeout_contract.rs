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

fn assert_ascii(bytes: &[u8], label: &str) {
    if let Some(offset) = bytes.iter().position(|&byte| byte >= 0x80) {
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
