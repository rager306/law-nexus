//! S03 T01 hostile contract (M200-8s4kwq): tracked review `m200-s03-outlier-review/v1`
//! over the accepted S02 `[diagnostic]` JSONL (D388 select-or-defer).
//! Reader: `npa_support`'s D328 closed parser (exact booleans via raw markers).
//! Source binding: structured pins + acceptance cross-chain (digests: S02 UAT).
//! Fail-closed (ADR-0015/R038): closed key allowlists; ASCII count-only redaction (R022);
//! only metric maxima reconstructed (first anchor, descending insertion; tails never rank);
//! `[proposed]` lifecycle, R035/R070/N2 open, 1024 ceiling only numeric select.

#[allow(dead_code)]
mod npa_support;

use std::fs;
use std::path::PathBuf;

use ln_decode::npa_bounds::validate_bounds_jsonl;
use npa_support::{parse_json, Json};

// Pinned values (accepted S02 evidence chain).

const REVIEW_RELATIVE_PATH: &str = "prd/migration/rust-evidence/m200-s03-outlier-review.json";
const SCAN_RELATIVE_PATH: &str = "prd/migration/rust-evidence/m200-s02-npa-bounds-scan.jsonl";
const ACCEPTANCE_RELATIVE_PATH: &str =
    "prd/migration/rust-evidence/m200-s02-corpus-acceptance.json";

const SCAN_SHA256: &str = "3c76b3feb610adc5169d67aeb43a77dbecbd30fb1cac118918eff2a7f1863f6c";
const ACCEPTANCE_SHA256: &str = "028335b6b3b8b50b5941fae7258408827ed44356bbbaee4eff060a12456a268f";

const REVIEW_SCHEMA: &str = "m200-s03-outlier-review/v1";
const REVIEW_LIFECYCLE: &str = "[proposed]";
const SCAN_LIFECYCLE: &str = "[diagnostic]";

/// Exact-once raw markers: every exact scalar the closed schema pins.
#[rustfmt::skip]
const MARKERS: [&str; 7] = [
    "\"schema_version\": 1", "\"lifecycle\": \"[proposed]\"", "\"count_only\": true",
    "\"line_count\": 15", "\"corpus_opened_by_this_review\": false",
    "\"anchors_store_values\": false", "\"active\": true",
];

const OBSERVED_CANDIDATES_PER_BLOCK_MAX: u64 = 504;
const PROPOSED_CANDIDATE_CEILING: u64 = 1024;
const P999_CANDIDATES_PER_BLOCK_BUCKET_EDGE: u64 = 14;

#[rustfmt::skip]
const DIRECT_KINDS: [&str; 4] = [
    "blocks_per_document", "tokens_per_block", "candidates_per_block", "candidates_per_document",
];

/// Proxy kind + whether its maximum identifies an outlier (binary/all-zero tails
/// never rank: retained anchors are walk-order first-seen).
#[rustfmt::skip]
const PROXY_ROWS: [(&str, bool); 4] = [
    ("proxy_date_docno_members_per_block", true),
    ("proxy_structural_range_blocks_per_block", false), ("proxy_alias_surfaces_per_document", true),
    ("proxy_cross_block_tails_per_document", false),
];

/// Closed D388 gate table (gate, verdict): select rows carry `select_kind`, the rest
/// are kind-less `deferred-undefined`. Ids assert sequential G01..G16 in document order.
#[rustfmt::skip]
const GATE_ROWS: [(&str, &str); 16] = [
    ("grammar-hard-invariants", "select"), ("contour-a-candidates-per-block-ceiling", "select"),
    ("candidates-per-document-bound", "deferred-undefined"),
    ("blocks-per-document-resource-budget", "deferred-undefined"),
    ("tokens-per-block-resource-budget", "deferred-undefined"),
    ("max-members-coordinating-frame", "deferred-undefined"),
    ("max-expanded-candidates", "deferred-undefined"),
    ("adjacent-block-radius", "deferred-undefined"), ("max-series-hops", "deferred-undefined"),
    ("max-alias-candidates", "deferred-undefined"),
    ("context-claims-fanout-memo-depth", "deferred-undefined"),
    ("pair-policies-frame-pairs", "deferred-undefined"),
    ("pair-policies-same-span-containment", "deferred-undefined"),
    ("arbitration-default-actions", "select"), ("source-authority-policy", "deferred-undefined"),
    ("top-k-aggregation-policy", "deferred-undefined"),
];

/// Selection kind for the three `select` rows, keyed by gate.
fn select_kind(gate: &str) -> &'static str {
    match gate {
        "grammar-hard-invariants" => "categorical-invariants",
        "contour-a-candidates-per-block-ceiling" => "numeric-safety-ceiling",
        "arbitration-default-actions" => "categorical-defaults",
        _ => "",
    }
}

fn tracked(rel: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(rel)
}

fn read_text(rel: &str) -> String {
    String::from_utf8(fs::read(tracked(rel)).expect("tracked artifact readable"))
        .expect("artifact is valid UTF-8")
}

// S02 JSONL helpers: pinned metric max + FIRST top-K anchor markers.
// Record schema is closed by `validate_bounds_jsonl` - not a second parser.

fn must_find(hay: &str, needle: &str, err: &str) -> Result<usize, String> {
    hay.find(needle).ok_or_else(|| err.to_owned())
}

fn scan_metric_record<'a>(scan: &'a str, metric_kind: &str) -> Result<&'a str, String> {
    let marker = format!("\"record_kind\":\"metric\",\"metric_kind\":\"{metric_kind}\"");
    scan.lines()
        .find(|line| line.contains(&marker))
        .ok_or_else(|| format!("no S02 metric '{metric_kind}'"))
}

/// Leading unsigned integer right after a marker; empty digit runs refuse.
fn leading_uint(record: &str, marker: &str, ctx: &str) -> Result<u64, String> {
    let start = must_find(record, marker, &format!("{ctx} without {marker}"))? + marker.len();
    let digits: String = record[start..]
        .chars()
        .take_while(|c| c.is_ascii_digit())
        .collect();
    digits
        .parse::<u64>()
        .map_err(|_| format!("{ctx} not an integer: '{digits}'"))
}

fn source_metric_max(record: &str) -> Result<u64, String> {
    leading_uint(record, "\"max\":", "metric record")
}

/// First top-K anchor object of a metric record (identity only).
fn source_first_anchor(record: &str) -> Result<&str, String> {
    let marker = "\"top_k_outlier_anchors\":[";
    let list = must_find(record, marker, "metric record without anchors")? + marker.len();
    let open = list + must_find(&record[list..], "{", "empty anchors list")?;
    let close = open + must_find(&record[open..], "}", "unterminated anchor")?;
    Ok(&record[open..=close])
}

fn anchor_string_field(anchor: &str, key: &str) -> Result<String, String> {
    let marker = format!("\"{key}\":\"");
    let start = must_find(anchor, &marker, &format!("anchor without '{key}'"))? + marker.len();
    let end = start + must_find(&anchor[start..], "\"", &format!("unterminated '{key}'"))?;
    Ok(anchor[start..end].to_owned())
}

fn anchor_block_index(anchor: &str) -> Result<Option<u64>, String> {
    let marker = "\"block_index\":";
    let start = must_find(anchor, marker, "anchor without 'block_index'")? + marker.len();
    if anchor[start..].starts_with("null") {
        return Ok(None);
    }
    leading_uint(&anchor[start..], "", "block_index").map(Some)
}

/// S02 source truth for one metric: (max, first-anchor path/hash/block).
/// The metric line's `"max"` binds to S02; the head-of-array check pins
/// that the first-anchor object sits exactly at the start of the S02
/// top-K anchors array (descending insertion, never reordered).
fn source_max_first(scan: &str, kind: &str) -> (u64, String, String, Option<u64>) {
    let record = scan_metric_record(scan, kind).expect("metric record exists");
    let max = source_metric_max(record).expect("source max parses");
    let marker = "\"top_k_outlier_anchors\":[";
    let anchors =
        must_find(record, marker, "metric record without anchors").unwrap() + marker.len();
    let first = source_first_anchor(record).expect("first anchor exists");
    assert_eq!(&record[anchors..anchors + first.len()], first);
    let path = anchor_string_field(first, "document_relative_path").expect("anchor path");
    let hash = anchor_string_field(first, "document_content_hash").expect("anchor hash");
    let block = anchor_block_index(first).expect("source block_index parses");
    (max, path, hash, block)
}

// Narrow raw check for exact booleans (opaque unit bools in D328 parser):
// structured parse guarantees shape; the raw marker pins the exact value.

/// Row slice for one metric or gate: from its unique marker to the next
/// same-level marker (or section end). Each marker occurs exactly once.
fn row_slice<'a>(text: &'a str, marker: &str, next: &str, end: &str) -> Result<&'a str, String> {
    if text.match_indices(marker).count() != 1 {
        return Err(format!("marker must appear exactly once: {marker}"));
    }
    let start = must_find(text, marker, "marker counted once")?;
    let after = start + marker.len();
    let next_pos = text[after..].find(next).map(|o| after + o);
    let end_pos = must_find(text, end, &format!("section '{end}' missing"))?;
    let stop = match next_pos {
        Some(n) if n < end_pos => n,
        _ => end_pos,
    };
    if stop <= start {
        return Err(format!("slice is empty for marker: {marker}"));
    }
    Ok(&text[start..stop])
}

fn metric_row_slice<'a>(text: &'a str, kind: &str) -> Result<&'a str, String> {
    let marker = format!("\"metric_kind\": \"{kind}\"");
    row_slice(text, &marker, "\"metric_kind\": \"", "\"gate_decisions\"")
}

/// Gate row slice: starts at its `gate_id` (precedes the `gate` marker),
/// runs to the next row's `gate_id` (or the drift section end).
fn gate_row_slice<'a>(text: &'a str, gate: &str) -> Result<&'a str, String> {
    let marker = format!("\"gate\": \"{gate}\"");
    if text.match_indices(&marker).count() != 1 {
        return Err(format!("gate '{gate}' must appear exactly once"));
    }
    let at = must_find(text, &marker, "marker counted once")?;
    let row_start = must_find(
        &text[..at],
        "\"gate_id\"",
        &format!("gate '{gate}' row has no id"),
    )?;
    let after = at + marker.len();
    let next_pos = text[after..].find("\"gate_id\": \"G").map(|o| after + o);
    let drift = must_find(text, "\"npa_family_drift\"", "drift section missing")?;
    let stop = match next_pos {
        Some(n) if n < drift => n,
        _ => drift,
    };
    if stop <= row_start {
        return Err(format!("gate '{gate}' slice is empty"));
    }
    Ok(&text[row_start..stop])
}

/// Exact boolean marker: expected form present, opposite form absent.
fn assert_raw_bool(section: &str, key: &str, expected: bool, ctx: &str) -> Result<(), String> {
    if !section.contains(&format!("\"{key}\": {expected}")) {
        return Err(format!("{ctx}: expected '\"{key}\": {expected}'"));
    }
    if section.contains(&format!("\"{key}\": {}", !expected)) {
        return Err(format!("{ctx}: unexpected opposite boolean for '{key}'"));
    }
    Ok(())
}

/// Integer-or-null scalar via the single D328 parser: `Num` parses through
/// `as_usize`, `Null` maps to `None`, anything else refuses.
fn int_or_null(value: &Json, key: &str, ctx: &str) -> Result<Option<u64>, String> {
    match value.get(key)? {
        Json::Null => Ok(None),
        num => match num.as_usize() {
            Ok(n) => u64::try_from(n)
                .map(Some)
                .map_err(|_| format!("{ctx}: '{key}' out of range")),
            Err(err) => Err(format!("{ctx}: '{key}': {err}")),
        },
    }
}

/// Every `reconstructed_value` in a metric's secondary-anchors section is
/// null (identity-only); an empty list is honest (nothing ranked).
fn check_secondary_identity_only(text: &str, kind: &str) -> Result<(), String> {
    let row = metric_row_slice(text, kind)?;
    let marker = "\"secondary_anchors\": [";
    let start = must_find(row, marker, &format!("{kind}: secondaries missing"))? + marker.len();
    let section = &row[start..];
    if section.trim_start().starts_with(']') {
        return Ok(());
    }
    let mut found = false;
    for chunk in section.split("\"reconstructed_value\":").skip(1) {
        found = true;
        if !chunk.trim_start().starts_with("null") {
            return Err(format!(
                "{kind}: secondaries are identity-only (values must be null)"
            ));
        }
    }
    if found {
        Ok(())
    } else {
        Err(format!("{kind}: no reconstructed_value markers found"))
    }
}

type RowResult<'a> = Result<&'a Json, String>;

fn find_row<'a>(rows: &'a [Json], section: &str, key: &str, kind: &str) -> RowResult<'a> {
    rows.iter()
        .find(|row| {
            row.get(key)
                .and_then(|v| v.as_str())
                .is_ok_and(|v| v == kind)
        })
        .ok_or_else(|| format!("{section} has no row for '{kind}'"))
}

// Closed-schema validation: fail-closed reader over the single D328 parser.

#[rustfmt::skip]
const TOP_KEYS: [&str; 18] = [
    "schema", "schema_version", "lifecycle", "milestone", "slice", "task", "owner_decision",
    "generated_utc", "count_only", "non_claims", "source_binding", "top_k_reconstruction",
    "direct_metric_review", "proxy_metric_review", "gate_decisions", "npa_family_drift",
    "runtime_stop", "non_closures",
];
#[rustfmt::skip]
const SOURCE_BINDING_KEYS: [&str; 6] = [
    "scan_artifact", "acceptance_artifact", "profile_schema", "profile_hash_at_scan",
    "measurement_definitions_hash", "corpus_opened_by_this_review",
];
#[rustfmt::skip]
const SCAN_ARTIFACT_KEYS: [&str; 4] = ["path", "sha256", "line_count", "lifecycle"];
const ACCEPTANCE_ARTIFACT_KEYS: [&str; 2] = ["path", "sha256"];
#[rustfmt::skip]
const TOP_K_RECONSTRUCTION_KEYS: [&str; 5] = [
    "anchors_store_values", "statement", "max_identification_rule",
    "binary_and_zero_tails", "non_claims",
];
#[rustfmt::skip]
const DIRECT_METRIC_ROW_KEYS: [&str; 9] = [
    "metric_kind", "namespace", "observed_max", "max_identifies_outlier", "max_anchor",
    "secondary_anchors", "reconstruction_basis", "compact_shape", "review_note",
];
/// Proxy rows are the direct closed set plus `proxy_honesty`; direct rows must not carry it.
const PROXY_HONESTY_EXTRA: &str = "proxy_honesty";
#[rustfmt::skip]
const MAX_ANCHOR_KEYS: [&str; 4] = [
    "document_relative_path", "document_content_hash", "block_index", "reconstructed_value",
];
#[rustfmt::skip]
const SECONDARY_ANCHOR_KEYS: [&str; 5] = [
    "document_relative_path", "document_content_hash", "block_index", "reconstructed_value", "note",
];
#[rustfmt::skip]
const GATE_ROW_KEYS: [&str; 10] = [
    "gate_id", "gate", "source", "evidence_basis", "observed_max", "verdict", "selection_kind",
    "proposed_value", "refusal_diagnostic", "rationale",
];
#[rustfmt::skip]
const NPA_FAMILY_DRIFT_KEYS: [&str; 4] = [
    "historical_top_level_dirents", "live_recursive_xml", "delta", "authority_note",
];
const RUNTIME_STOP_KEYS: [&str; 3] = ["active", "remaining_reasons", "note"];
const NON_CLOSURES_KEYS: [&str; 3] = ["requirements", "gates", "note"];
const EVIDENCE_BASES: [&str; 4] = ["categorical", "direct", "proxy", "unavailable"];

/// Closed-schema row check (direct/proxy): exact scalars pinned by raw markers;
/// the closed key set forces their presence.
fn non_empty_str(value: &Json, key: &str, ctx: &str) -> Result<(), String> {
    if value.get(key)?.as_str()?.is_empty() {
        return Err(format!("{ctx}: '{key}' must be non-empty"));
    }
    Ok(())
}

fn validate_metric_row(row: &Json, keys: &[&str], ns: &str, hon: bool) -> Result<(), String> {
    let ctx = ns;
    row.require_keys(keys, ctx)?;
    non_empty_str(row, "metric_kind", ctx)?;
    if row.get("namespace")?.as_str()? != ns {
        return Err(format!("{ctx}: namespace is not '{ns}'"));
    }
    let anchor = row.get("max_anchor")?;
    anchor.require_keys(&MAX_ANCHOR_KEYS, &format!("{ctx}: max_anchor"))?;
    let path = anchor.get("document_relative_path")?.as_str()?;
    if path.starts_with('/') || path.contains("..") {
        return Err(format!("{ctx}: max_anchor path is not repo-relative"));
    }
    let hash = anchor.get("document_content_hash")?.as_str()?;
    if !hash.starts_with("fnv1a64:") {
        return Err(format!("{ctx}: max_anchor hash is not an fnv1a64 pin"));
    }
    for secondary in row.get("secondary_anchors")?.as_arr()? {
        secondary.require_keys(&SECONDARY_ANCHOR_KEYS, &format!("{ctx}: secondary"))?;
        non_empty_str(secondary, "note", ctx)?;
    }
    non_empty_str(row, "reconstruction_basis", ctx)?;
    match (row.get_opt("proxy_honesty")?, hon) {
        (None, false) => Ok(()),
        (Some(honesty), true) if !honesty.as_str()?.is_empty() => Ok(()),
        _ => Err(format!("{ctx}: proxy_honesty must match the namespace")),
    }
}

/// Fail-closed D388 gate verdicts: one select-or-defer row per gate, sequential ids;
/// raw verdicts cross-checked against the structured row.
fn check_gate_row(
    text: &str,
    gates: &[Json],
    n: usize,
    gate: &str,
    verdict: &str,
) -> Result<(), String> {
    let row = gate_row_slice(text, gate)?;
    if !row.contains(&format!("\"gate_id\": \"G{:02}\"", n + 1)) {
        return Err(format!("gate '{gate}' row id is not sequential"));
    }
    let structured = find_row(gates, "gate_decisions", "gate", gate)?;
    structured.require_keys(&GATE_ROW_KEYS, "gate row")?;
    if !EVIDENCE_BASES.contains(&structured.get("evidence_basis")?.as_str()?) {
        return Err(format!("gate '{gate}' has an unknown evidence_basis"));
    }
    if structured.get("source")?.as_str()?.is_empty() {
        return Err(format!("gate '{gate}' source must be non-empty"));
    }
    let _ = int_or_null(structured, "observed_max", gate)?;
    let sv = structured.get("verdict")?.as_str()?;
    if sv != verdict || !row.contains(&format!("\"verdict\": \"{verdict}\"")) {
        return Err(format!(
            "gate '{gate}' verdict drifted (raw + structured must agree)"
        ));
    }
    let selection = select_kind(gate);
    let proposed = int_or_null(structured, "proposed_value", gate)?;
    if verdict == "select" {
        if !row.contains(&format!("\"selection_kind\": \"{selection}\"")) {
            return Err(format!("gate '{gate}': selection_kind drifted"));
        }
        if (selection == "numeric-safety-ceiling") != proposed.is_some() {
            return Err(format!("gate '{gate}': only the ceiling mints a value"));
        }
    } else {
        if !row.contains("\"selection_kind\": null") || proposed.is_some() {
            return Err(format!(
                "gate '{gate}': deferred selection_kind must be null"
            ));
        }
        if !row.contains("blocking reason") {
            return Err(format!("gate '{gate}': deferred rows state a reason"));
        }
    }
    if row.contains("\"rationale\": \"\"") {
        return Err(format!("gate '{gate}' rationale must be non-empty"));
    }
    match structured.get("refusal_diagnostic")? {
        Json::Null | Json::Str(_) => Ok(()),
        other => Err(format!("gate '{gate}': refusal not null/str: {other:?}")),
    }
}

/// Fail-closed reader over the single D328 parser.
fn validate_review(text: &str) -> Result<(), String> {
    let root = parse_json(text)?;
    root.require_keys(&TOP_KEYS, "review")?;
    for (key, expected) in [
        ("schema", REVIEW_SCHEMA),
        ("milestone", "M200-8s4kwq"),
        ("slice", "S03"),
        ("task", "T01"),
        ("owner_decision", "D388"),
    ] {
        if root.get(key)?.as_str()? != expected {
            return Err(format!("review {key} drifted"));
        }
    }
    for marker in MARKERS {
        if text.matches(marker).count() != 1 {
            return Err(format!("review marker must appear exactly once: {marker}"));
        }
    }
    if root.get("generated_utc")?.as_str()?.is_empty() {
        return Err("review generated_utc must be non-empty".to_string());
    }
    if root.get("non_claims")?.as_arr()?.len() < 8 {
        return Err("review non_claims set is too small to be honest".to_string());
    }
    for check in [
        check_source_binding,
        check_reconstruction,
        check_metric_sections,
    ] {
        check(&root)?;
    }
    let gates = root.get("gate_decisions")?.as_arr()?;
    if gates.len() != GATE_ROWS.len() {
        return Err("gate_decisions must carry exactly one row per D388 gate".to_string());
    }
    for (n, (gate, verdict)) in GATE_ROWS.iter().enumerate() {
        check_gate_row(text, gates, n, gate, verdict)?;
    }
    let drift = root.get("npa_family_drift")?;
    drift.require_keys(&NPA_FAMILY_DRIFT_KEYS, "npa_family_drift")?;
    if drift.get("authority_note")?.as_str()?.is_empty() {
        return Err("npa_family_drift authority_note must be non-empty".to_string());
    }
    let stop = root.get("runtime_stop")?;
    stop.require_keys(&RUNTIME_STOP_KEYS, "runtime_stop")?;
    if stop.get("remaining_reasons")?.as_arr()?.len() < 3 {
        return Err("runtime_stop must list its remaining reasons for S04".to_string());
    }
    root.get("non_closures")?
        .require_keys(&NON_CLOSURES_KEYS, "non_closures")?;
    Ok(())
}

/// Source binding: digest pins, scan lifecycle, fnv pins.
fn check_source_binding(root: &Json) -> Result<(), String> {
    let binding = root.get("source_binding")?;
    binding.require_keys(&SOURCE_BINDING_KEYS, "source_binding")?;
    let scan_artifact = binding.get("scan_artifact")?;
    scan_artifact.require_keys(&SCAN_ARTIFACT_KEYS, "scan_artifact")?;
    for (key, expected) in [
        ("path", SCAN_RELATIVE_PATH),
        ("sha256", SCAN_SHA256),
        ("lifecycle", SCAN_LIFECYCLE),
    ] {
        if scan_artifact.get(key)?.as_str()? != expected {
            return Err(format!("scan artifact '{key}' drifted"));
        }
    }
    let acceptance_artifact = binding.get("acceptance_artifact")?;
    acceptance_artifact.require_keys(&ACCEPTANCE_ARTIFACT_KEYS, "acceptance_artifact")?;
    if acceptance_artifact.get("path")?.as_str()? != ACCEPTANCE_RELATIVE_PATH {
        return Err("acceptance artifact path drifted".to_string());
    }
    if acceptance_artifact.get("sha256")?.as_str()? != ACCEPTANCE_SHA256 {
        return Err("acceptance artifact sha256 pin drifted".to_string());
    }
    if binding.get("profile_schema")?.as_str()? != "law-nexus-npa-bounds-scanner-profile/v1" {
        return Err("profile_schema drifted".to_string());
    }
    for key in ["profile_hash_at_scan", "measurement_definitions_hash"] {
        if !binding.get(key)?.as_str()?.starts_with("fnv1a64:") {
            return Err(format!("{key} must be an fnv1a64 pin"));
        }
    }
    Ok(())
}

/// Top-K reconstruction honesty: omit-values contract + tail policy stated.
fn check_reconstruction(root: &Json) -> Result<(), String> {
    let reconstruction = root.get("top_k_reconstruction")?;
    reconstruction.require_keys(&TOP_K_RECONSTRUCTION_KEYS, "top_k_reconstruction")?;
    let statement = reconstruction.get("statement")?.as_str()?;
    for required in ["omit", "first anchor", "descending insertion"] {
        if !statement.contains(required) {
            return Err(format!("reconstruction statement must state '{required}'"));
        }
    }
    if reconstruction
        .get("binary_and_zero_tails")?
        .as_str()?
        .is_empty()
    {
        return Err("binary/zero tail policy must be stated".to_string());
    }
    if reconstruction.get("non_claims")?.as_arr()?.len() < 3 {
        return Err("reconstruction non_claims set is too small".to_string());
    }
    Ok(())
}

/// Metric reviews: closed 4+4 rows, direct/proxy strictly separate.
fn check_metric_sections(root: &Json) -> Result<(), String> {
    let mut proxy_keys = DIRECT_METRIC_ROW_KEYS.to_vec();
    proxy_keys.push(PROXY_HONESTY_EXTRA);
    for (section, allowed, ns, hon, kinds) in [
        (
            "direct_metric_review",
            &DIRECT_METRIC_ROW_KEYS[..],
            "direct",
            false,
            DIRECT_KINDS.len(),
        ),
        (
            "proxy_metric_review",
            &proxy_keys[..],
            "proxy",
            true,
            PROXY_ROWS.len(),
        ),
    ] {
        let rows = root.get(section)?.as_arr()?;
        if rows.len() != kinds {
            return Err(format!(
                "{section} must carry exactly its closed metric set"
            ));
        }
        for row in rows {
            validate_metric_row(row, allowed, ns, hon)?;
        }
    }
    Ok(())
}

// T01 hostile contracts (table-driven; all load-bearing checks retained).

/// Source binding without digest recomputation: pins are well-formed hex, review fields
/// equal the pins, acceptance cross-pins the scan chain (file digests: S02 contracts/UAT).
#[test]
fn t01_source_pins_consistent() {
    for pin in [SCAN_SHA256, ACCEPTANCE_SHA256] {
        assert_eq!(pin.len(), 64);
        assert!(pin.bytes().all(|byte| byte.is_ascii_hexdigit()));
    }
    assert_ne!(SCAN_SHA256, ACCEPTANCE_SHA256);
    let review = read_text(REVIEW_RELATIVE_PATH);
    let root = parse_json(&review).expect("review parses");
    let binding = root.get("source_binding").unwrap();
    for (section, key, want) in [
        ("scan_artifact", "sha256", SCAN_SHA256),
        ("scan_artifact", "path", SCAN_RELATIVE_PATH),
        ("acceptance_artifact", "sha256", ACCEPTANCE_SHA256),
        ("acceptance_artifact", "path", ACCEPTANCE_RELATIVE_PATH),
    ] {
        let artifact = binding.get(section).unwrap();
        assert_eq!(artifact.get(key).unwrap().as_str().unwrap(), want);
    }
    let acceptance = read_text(ACCEPTANCE_RELATIVE_PATH);
    assert_eq!(acceptance.matches("\"gate_passed\": true").count(), 1);
    let acc_root = parse_json(&acceptance).expect("acceptance parses");
    let under = acc_root.get("artifact_under_acceptance").unwrap();
    assert_eq!(under.get("sha256").unwrap().as_str().unwrap(), SCAN_SHA256);
    assert_eq!(under.get("line_count").unwrap().as_usize().unwrap(), 15);
}

/// Artifact hygiene + lifecycle honesty: pure ASCII (R022), no corpus reference,
/// `...=false` once, no host paths, evidence on disk; `[proposed]` review without
/// `[bounded]` promotion while S02 `[diagnostic]` JSONL still validates untouched.
#[test]
fn t02_hygiene_and_lifecycle() {
    let bytes = fs::read(tracked(REVIEW_RELATIVE_PATH)).expect("review readable");
    assert!(bytes.iter().all(|byte| byte.is_ascii()));
    let review = String::from_utf8(bytes).expect("review is valid UTF-8");
    assert!(!review.contains("consru_export") && !review.contains("/root/"));
    let count = |marker: &str| review.matches(marker).count();
    assert_eq!(count("\"corpus_opened_by_this_review\": false"), 1);
    assert_eq!(count(&format!("\"lifecycle\": \"{REVIEW_LIFECYCLE}\"")), 1);
    assert!(!review.contains("[bounded]"));
    for rel in [
        REVIEW_RELATIVE_PATH,
        SCAN_RELATIVE_PATH,
        ACCEPTANCE_RELATIVE_PATH,
    ] {
        assert!(tracked(rel).is_file());
    }
    let scan = read_text(SCAN_RELATIVE_PATH);
    validate_bounds_jsonl(&scan).expect("S02 JSONL still validates");
    assert_eq!(scan.lines().count(), 15);
    assert_eq!(scan.matches("\"lifecycle\":\"[diagnostic]\"").count(), 2);
    assert!(!scan.contains("[bounded]") && scan.contains("\"bound-decision\""));
}

/// Closed schema: the tracked artifact passes the fail-closed reader.
#[test]
fn t03_review_artifact_closed_schema() {
    let review = read_text(REVIEW_RELATIVE_PATH);
    validate_review(&review).expect("closed-schema reader passes");
    assert!(review.contains("\"schema\": \"m200-s03-outlier-review/v1\""));
}

/// Direct rows carry no proxy_honesty; proxy rows follow the closed
/// identifies table (non-identifying tails rank nothing); secondaries are
/// identity-only with every cited anchor present in the S02 top-K list.
fn anchor_str<'a>(anchor: &'a Json, key: &str) -> &'a str {
    anchor.get(key).unwrap().as_str().unwrap()
}

/// One table-driven check per metric row: observed_max == S02 max, max_anchor is
/// exactly the FIRST top-K anchor (never invented).
fn check_metric_row(scan: &str, review: &str, rows: &[Json], kind: &str, ident: bool) {
    let section = if DIRECT_KINDS.contains(&kind) {
        "direct_metric_review"
    } else {
        "proxy_metric_review"
    };
    let (max, path, hash, block) = source_max_first(scan, kind);
    let metric = find_row(rows, section, "metric_kind", kind).unwrap();
    let row = metric_row_slice(review, kind).expect("review row exists");
    let observed = int_or_null(metric, "observed_max", kind).unwrap();
    assert_eq!(observed, Some(max));
    assert_raw_bool(row, "max_identifies_outlier", ident, kind).unwrap();
    let anchor = metric.get("max_anchor").unwrap();
    assert_eq!(anchor_str(anchor, "document_relative_path"), path);
    assert_eq!(anchor_str(anchor, "document_content_hash"), hash);
    assert_eq!(int_or_null(anchor, "block_index", kind).unwrap(), block);
    let value = int_or_null(anchor, "reconstructed_value", kind).unwrap();
    if ident {
        assert_eq!(value, Some(max));
    } else {
        assert_eq!(value, None);
        let secondaries = metric.get("secondary_anchors").unwrap().as_arr().unwrap();
        assert!(secondaries.is_empty());
    }
    check_secondary_identity_only(review, kind).expect("identity-only secondaries");
    let record = scan_metric_record(scan, kind).expect("metric record exists");
    for secondary in metric.get("secondary_anchors").unwrap().as_arr().unwrap() {
        let sub = anchor_str(secondary, "document_relative_path");
        assert!(record.contains(sub), "{kind}: '{sub}' must exist in S02");
    }
}

#[test]
fn t04_all_metric_rows_bind_to_s02() {
    let scan = read_text(SCAN_RELATIVE_PATH);
    let review = read_text(REVIEW_RELATIVE_PATH);
    let root = parse_json(&review).expect("review parses");
    let direct_rows = root.get("direct_metric_review").unwrap().as_arr().unwrap();
    let proxy_rows = root.get("proxy_metric_review").unwrap().as_arr().unwrap();
    assert_eq!(direct_rows.len(), DIRECT_KINDS.len());
    assert_eq!(proxy_rows.len(), PROXY_ROWS.len());
    for kind in DIRECT_KINDS {
        let row = metric_row_slice(&review, kind).expect("direct row exists");
        assert!(row.contains("\"namespace\": \"direct\"") && !row.contains("proxy_honesty"));
        check_metric_row(&scan, &review, direct_rows, kind, true);
    }
    for (kind, ident) in PROXY_ROWS {
        assert!(!DIRECT_KINDS.contains(&kind));
        let row = metric_row_slice(&review, kind).expect("proxy row exists");
        assert!(row.contains("\"namespace\": \"proxy\"") && row.contains("proxy_honesty"));
        check_metric_row(&scan, &review, proxy_rows, kind, ident);
    }
}

/// Closed D388 gate table (sequential ids, deferred rows state blocking reason);
/// only numeric select is the 1024 safety ceiling (>= 2x observed 504, not the max
/// nor the p999 edge 14, named diagnostic, explicit safety-ceiling sentence).
#[test]
fn t05_gate_table_and_ceiling() {
    let review = read_text(REVIEW_RELATIVE_PATH);
    let root = parse_json(&review).expect("review parses");
    validate_review(&review).expect("closed gate table validates");
    let count = |marker: &str| review.matches(marker).count();
    assert_eq!(count("\"verdict\": \"select\""), 3);
    assert_eq!(count("\"verdict\": \"deferred-undefined\""), 13);
    assert_eq!(count("\"refusal_diagnostic\": null"), 15);
    let gates = root.get("gate_decisions").unwrap().as_arr().unwrap();
    let mut numeric = Vec::new();
    for (gate, _) in GATE_ROWS {
        let row = find_row(gates, "gate_decisions", "gate", gate).unwrap();
        if let Some(value) = int_or_null(row, "proposed_value", gate).unwrap() {
            numeric.push((gate, value));
        }
    }
    let ceiling_gate = "contour-a-candidates-per-block-ceiling";
    assert_eq!(numeric, [(ceiling_gate, PROPOSED_CANDIDATE_CEILING)]);
    let ceiling = find_row(gates, "gate_decisions", "gate", ceiling_gate).unwrap();
    let refusal = anchor_str(ceiling, "refusal_diagnostic");
    assert_eq!(refusal, "candidate_limit_reached");
    let observed_max = int_or_null(ceiling, "observed_max", "ceiling")
        .unwrap()
        .expect("selected ceiling must cite an observed maximum");
    let proposed = int_or_null(ceiling, "proposed_value", "ceiling")
        .unwrap()
        .expect("selected ceiling must carry a proposed value");
    assert_eq!(observed_max, OBSERVED_CANDIDATES_PER_BLOCK_MAX);
    assert!(proposed >= 2 * observed_max);
    assert_ne!(proposed, observed_max);
    assert_ne!(proposed, P999_CANDIDATES_PER_BLOCK_BUCKET_EDGE);
    let rationale = anchor_str(ceiling, "rationale");
    for required in [
        "safety ceiling",
        "headroom",
        "not a claim that larger legal structures do not exist",
    ] {
        assert!(rationale.contains(required));
    }
}

/// Reconstruction honesty: anchors omit per-anchor values; only the metric maximum
/// is reconstructed; binary/all-zero tails never rank.
#[test]
fn t06_top_k_reconstruction_honesty_pinned() {
    let review = read_text(REVIEW_RELATIVE_PATH);
    let root = parse_json(&review).expect("review parses");
    let reconstruction = root.get("top_k_reconstruction").unwrap();
    assert_eq!(review.matches("\"anchors_store_values\": false").count(), 1);
    let statement = reconstruction.get("statement").unwrap().as_str().unwrap();
    for required in ["omit", "first anchor", "descending insertion"] {
        assert!(statement.contains(required));
    }
    let tails = anchor_str(reconstruction, "binary_and_zero_tails");
    for required in [
        "proxy_structural_range_blocks_per_block",
        "proxy_cross_block_tails_per_document",
        "never ranked",
    ] {
        assert!(tails.contains(required));
    }
    let claims = reconstruction.get("non_claims").unwrap().as_arr().unwrap();
    let joined: Vec<&str> = claims.iter().map(|c| c.as_str().unwrap()).collect();
    let has = |needle: &str| joined.iter().any(|c| c.contains(needle));
    assert!(has("no independently stored per-anchor values"));
    assert!(has("never numerically claimed"));
}

/// Non-closures + runtime stop + drift: R035/R070/N2-gate stay open; stop stays active
/// with S04 reasons; drift matches the acceptance record (recorded, never hardcoded).
#[test]
fn t07_non_closures_stop_and_drift() {
    let review = read_text(REVIEW_RELATIVE_PATH);
    let root = parse_json(&review).expect("review parses");
    let closures = root.get("non_closures").unwrap();
    let reqs = closures.get("requirements").unwrap().as_arr().unwrap();
    for want in ["R035", "R070"] {
        assert!(reqs.iter().any(|v| v.as_str().unwrap() == want));
    }
    let req_gates = closures.get("gates").unwrap().as_arr().unwrap();
    assert!(req_gates.iter().any(|v| v.as_str().unwrap() == "N2-gate"));
    let stop = root.get("runtime_stop").unwrap();
    assert_eq!(review.matches("\"active\": true").count(), 1);
    let reasons = stop.get("remaining_reasons").unwrap().as_arr().unwrap();
    assert!(reasons.len() >= 3);
    assert!(anchor_str(stop, "note").contains("S04"));
    assert!(review.contains("R035, R070 and the N2-gate stay open"));
    let acceptance = read_text(ACCEPTANCE_RELATIVE_PATH);
    let acc_root = parse_json(&acceptance).expect("acceptance parses");
    let accepted = acc_root.get("npa_family_drift").unwrap();
    let drift = root.get("npa_family_drift").unwrap();
    for key in ["historical_top_level_dirents", "live_recursive_xml"] {
        let want = accepted.get(key).unwrap().as_usize().unwrap();
        assert_eq!(drift.get(key).unwrap().as_usize().unwrap(), want);
    }
    let note = anchor_str(drift, "authority_note");
    for required in [
        "inventory authority",
        "neither is a bound",
        "hardcoded in the scanner",
    ] {
        assert!(note.contains(required));
    }
}

/// Hostile self-checks, table-driven: each tampered variant refused with its
/// fail-closed diagnostic (non-ASCII injection is byte-observable).
#[test]
fn t08_review_reader_refuses_tampering() {
    let review = read_text(REVIEW_RELATIVE_PATH);
    // (name, tampered text, expected diagnostic substring)
    let unknown_key = review.replacen('{', "{\n  \"bogus_top_level_key\": 1,", 1);
    let duplicate_key = review.replacen("\"schema\":", "\"schema_version\": 2, \"schema\":", 1);
    let trailing = format!("{review}{{}}");
    let bad_verdict = review.replace(
        "\"verdict\": \"deferred-undefined\"",
        "\"verdict\": \"bounded\"",
    );
    let minted_policy = review.replace(
        "\"verdict\": \"select\",\n      \"selection_kind\": \"numeric-safety-ceiling\",",
        "\"verdict\": \"select\",\n      \"selection_kind\": \"numeric-safety-ceiling\",\n      \"first_n\": 504,",);
    for (name, tampered, expected) in [
        ("unknown key", unknown_key, "bogus_top_level_key"),
        ("duplicate key", duplicate_key, "duplicate"),
        ("trailing garbage", trailing, "trailing"),
        ("invented verdict", bad_verdict, "verdict drifted"),
        ("minted policy key", minted_policy, "first_n"),
    ] {
        let err = validate_review(&tampered).unwrap_err();
        assert!(err.contains(expected), "{name} must fail closed: {err}");
    }
    let non_ascii = review
        .replace("resource tail", "resource DEAtail")
        .replacen("DEA", "х", 1);
    assert!(!non_ascii.as_bytes().iter().all(|byte| byte.is_ascii()));
    let invented_value = review.replace(
        "\"reconstructed_value\": null,\n          \"note\": \"identity-only second anchor",
        "\"reconstructed_value\": 40000,\n          \"note\": \"identity-only second anchor",
    );
    assert_ne!(invented_value, review, "tamper fixture must differ");
    let err = check_secondary_identity_only(&invented_value, "blocks_per_document").unwrap_err();
    assert!(err.contains("identity-only"), "names the rule: {err}");
}
