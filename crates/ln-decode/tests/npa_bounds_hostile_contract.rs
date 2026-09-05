//! S03 T01+T02+T03 hostile contracts (M200-8s4kwq): tracked review `m200-s03-outlier-review/v1`
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

use ln_decode::lawref::{capture_lawrefs, LawRef};
use ln_decode::lexer::lex;
use ln_decode::npa_bounds::{
    arbitrate_pair, span_relation, validate_bounds_jsonl, PairDiagnostic, PairOutcome,
    SpanRelation, UNAVAILABLE_METRICS,
};
use ln_decode::unknown_forms::collect_unknown_forms_from_text;
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

// T02: tracked design sources + observed S02 pair-class distribution (G14).
const ASSESSMENT_RELATIVE_PATH: &str = "assessment/29-npa-bounds-hostile-plan.md";
const ARBITRATION_RELATIVE_PATH: &str = "prd/architecture/npa-capture-arbitration.yaml";
const OBSERVED_PARTIAL_OVERLAP_PAIRS: u64 = 539;
const OBSERVED_DISJOINT_PAIRS: u64 = 10_962_245;

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

// ==== T02: grammar-hard invariants + arbitration defaults (no numeric bound) ====

/// Section between two markdown headers (both headers exclusive; the end
/// header is searched after the start header).
fn section_between<'a>(text: &'a str, start: &str, end: &str) -> &'a str {
    let from = must_find(text, start, "section header missing").expect("section header");
    let to = must_find(&text[from..], end, "section end missing").expect("section end") + from;
    &text[from + start.len()..to]
}

/// Assessment §2 grammar-hard invariants stay categorical: each bound cell is
/// digit-free (a number would be a measured maximum, deferred to G02+), every
/// invariant is echoed in the review G01 rationale, §2 closes without minting
/// ceilings, and surfaces with no scanner form stay deferred-unavailable.
#[test]
fn t09_grammar_hard_invariants_categorical() {
    let assessment = read_text(ASSESSMENT_RELATIVE_PATH);
    let review = read_text(REVIEW_RELATIVE_PATH);
    let section = section_between(&assessment, "## 2. Grammar-hard invariants", "## 3.");
    assert!(
        section.contains("categorical constraints rather than measured maxima"),
        "§2 must state its categorical basis"
    );
    // (invariant, assessment §2 phrase, review G01 rationale echo)
    #[rustfmt::skip]
    let rows: [(&str, &str, &str); 8] = [
        ("covering span", "one fragment-local TextAnchor; never cross-block", "span never crosses blocks"),
        ("endpoint pair", "exactly two endpoint candidates under `endpoint_pair`", "endpoint_pair=2 exactly"),
        ("range semantics", "no arithmetic enumeration of intermediate decimal designations", "no arithmetic range enumeration"),
        ("request vocabulary", "closed to the contract's named ContextRequest kinds", "ContextRequest kinds closed"),
        ("context closure", "one deterministic worklist-to-fixpoint run per document version", "one worklist run"),
        ("source mutation", "zero mutation of covering tokens, mentions, or base index", "zero source mutation"),
        ("prompt dependency", "zero product dependencies", "zero prompt"),
        ("provenance", "every derived field retains every authorized hop", "provenance hops recorded"),
    ];
    let g01 = gate_row_slice(&review, "grammar-hard-invariants").unwrap();
    for (name, in_assessment, in_review) in rows {
        assert!(
            section.contains(in_assessment),
            "{name}: §2 phrase drifted: {in_assessment}"
        );
        assert!(
            g01.contains(in_review),
            "{name}: review G01 echo drifted: {in_review}"
        );
    }
    assert!(
        section.contains("These do not determine safe memory/time/cardinality ceilings."),
        "§2 must close without minting ceilings"
    );
    // Hostile: a digit inside a §2 bound cell would mint a measured maximum.
    for line in section.lines().filter(|l| l.starts_with('|')) {
        if line.contains("---") {
            continue;
        }
        let cells: Vec<&str> = line.split('|').collect();
        assert!(cells.len() >= 4, "malformed §2 row: {line}");
        if cells[1].trim() == "Invariant" {
            continue;
        }
        assert!(
            !cells[2].bytes().any(|byte| byte.is_ascii_digit()),
            "§2 bound carries a digit (measured maxima are deferred): {line}"
        );
    }
    // Surfaces with no scanner form stay deferred-unavailable, never invented.
    for deferred in [
        "ContextRequest count and fan-out",
        "accepted continues_series hop count",
    ] {
        assert!(
            UNAVAILABLE_METRICS.contains(&deferred),
            "grammar surface must stay unavailable-until-runtime: {deferred}"
        );
    }
    assert!(g01.contains("no numeric runtime bound is introduced"));
}

/// Executable categorical arbitration defaults (G14): the production
/// classifier and the pure pair reducer refuse to invent winners. Tables pin
/// half-open classification, one default per pair class, swap symmetry, and
/// diagnostics equal to the arbitration contract's ids verbatim.
type SpanCase = (&'static str, (usize, usize), (usize, usize), SpanRelation);
type ArbitrationCase = (
    &'static str,
    (usize, usize),
    (usize, usize),
    bool,
    PairOutcome,
);

#[test]
fn t10_arbitration_defaults_table_driven() {
    // (name, a, b, relation) — half-open byte-span classification.
    #[rustfmt::skip]
    let spans: [SpanCase; 6] = [
        ("exact", (5, 25), (5, 25), SpanRelation::Exact),
        ("containment wider first", (0, 100), (10, 20), SpanRelation::Containment),
        ("containment narrower first", (10, 20), (0, 100), SpanRelation::Containment),
        ("partial overlap", (0, 15), (10, 25), SpanRelation::PartialOverlap),
        ("half-open adjacency is disjoint", (0, 10), (10, 20), SpanRelation::Disjoint),
        ("degenerate empty span stays total", (5, 5), (5, 10), SpanRelation::Containment),
    ];
    for (name, a, b, want) in spans {
        assert_eq!(span_relation(a, b), want, "{name}");
        assert_eq!(
            span_relation(b, a),
            want,
            "{name}: classifier is order-independent"
        );
    }
    // (name, a, b, slots_equal, outcome) — one categorical default per class.
    #[rustfmt::skip]
    let rows: [ArbitrationCase; 7] = [
        ("disjoint retains both without invented ambiguity", (0, 10), (20, 30), true, PairOutcome::RetainBoth(None)),
        ("half-open adjacency retains both", (0, 10), (10, 20), false, PairOutcome::RetainBoth(None)),
        ("partial overlap becomes a conflict set", (0, 15), (10, 25), true, PairOutcome::ConflictSet(PairDiagnostic::PartialOverlapConflict)),
        ("same span + incompatible slots is a conflict set", (5, 25), (5, 25), false, PairOutcome::ConflictSet(PairDiagnostic::ExactSpanSlotConflict)),
        ("same span + identical slots merges evidence", (5, 25), (5, 25), true, PairOutcome::MergeEvidence(PairDiagnostic::DuplicateMatcherEvidenceMerged)),
        ("containment stays ambiguous (no pair policy)", (0, 100), (10, 20), true, PairOutcome::RetainBoth(Some(PairDiagnostic::ContainmentWithoutPairPolicy))),
        ("containment reversed stays ambiguous", (10, 20), (0, 100), false, PairOutcome::RetainBoth(Some(PairDiagnostic::ContainmentWithoutPairPolicy))),
    ];
    for (name, a, b, slots_equal, want) in rows {
        assert_eq!(arbitrate_pair(a, b, slots_equal), want, "{name}");
        assert_eq!(
            arbitrate_pair(b, a, slots_equal),
            want,
            "{name}: swapped order must not invent a winner"
        );
    }
    // No silent winner invention: merging needs identical slots; containment
    // never subsumes while every pair policy is deferred-undefined.
    assert!(matches!(
        arbitrate_pair((5, 25), (5, 25), false),
        PairOutcome::ConflictSet(_)
    ));
    assert!(!matches!(
        arbitrate_pair((0, 100), (10, 20), true),
        PairOutcome::MergeEvidence(_)
    ));
    // Diagnostics are the contract's ids verbatim; exactly four are reachable
    // from pure pair facts and none of the unreachable ones is minted.
    let yaml = read_text(ARBITRATION_RELATIVE_PATH);
    let reached = [
        PairDiagnostic::DuplicateMatcherEvidenceMerged,
        PairDiagnostic::ExactSpanSlotConflict,
        PairDiagnostic::ContainmentWithoutPairPolicy,
        PairDiagnostic::PartialOverlapConflict,
    ];
    let mut seen: Vec<&str> = Vec::new();
    for diagnostic in reached {
        let id = diagnostic.as_str();
        assert!(
            yaml.contains(&format!("- {id}")),
            "reducer diagnostic absent from the contract: {id}"
        );
        assert!(!seen.contains(&id), "duplicate diagnostic id: {id}");
        seen.push(id);
    }
    for unminted in [
        "compatible_explicit_slots_merged",
        "frame_direct_disagreement",
        "candidate_limit_reached",
    ] {
        assert!(
            !seen.contains(&unminted),
            "pair reducer must not mint '{unminted}'"
        );
    }
    // Structural contract pins: policies deferred, defaults never suppress.
    #[rustfmt::skip]
    let pins = [
        "pair_policies:\n  status: deferred-undefined",
        "default: retain candidates with ambiguous/conflict diagnostic; never silently suppress",
        "# Pair policy is data. Source function order is never precedence.",
        "note: ordering is deterministic presentation, not semantic winner selection",
        "- when: same_span + incompatible\n    action: retain_conflict_set",
        "- when: containment + no_pair_policy\n    action: retain_both_as_ambiguous",
        "- when: partial_overlap\n    action: retain_conflict_set",
        "- when: disjoint\n    action: retain_both",
        "- same span + incompatible doc_no remains a conflict set",
        "- partial overlap never resolves by pattern execution order",
        "- disjoint candidates retain stable source order",
        "- start_byte/end_byte are fragment-local half-open byte offsets",
    ];
    for pin in pins {
        assert!(yaml.contains(pin), "arbitration contract drifted: {pin:?}");
    }
}

/// Arbitration defaults bind to the observed S02 distribution: the scan's
/// closed `span_relations` record (exact 0 / containment 0 / partial 539 /
/// disjoint 10,962,245) matches the review G14 rationale citations — the
/// categorical defaults stay anchored to count-only corpus evidence.
#[test]
fn t11_arbitration_defaults_bind_observed_distribution() {
    let scan = read_text(SCAN_RELATIVE_PATH);
    let line = scan
        .lines()
        .find(|l| l.contains("\"record_kind\":\"span_relations\""))
        .expect("S02 span_relations record present");
    let read = |marker: &str| leading_uint(line, marker, "span_relations").unwrap();
    assert_eq!(read("\"exact_span_pairs\":"), 0);
    assert_eq!(read("\"containment_pairs\":"), 0);
    assert_eq!(
        read("\"partial_overlap_pairs\":"),
        OBSERVED_PARTIAL_OVERLAP_PAIRS
    );
    assert_eq!(read("\"disjoint_pairs\":"), OBSERVED_DISJOINT_PAIRS);
    let review = read_text(REVIEW_RELATIVE_PATH);
    let g14 = gate_row_slice(&review, "arbitration-default-actions").unwrap();
    assert!(
        g14.contains("(10,962,245 observed)"),
        "G14 disjoint citation drifted"
    );
    assert!(
        g14.contains("(539 observed)"),
        "G14 partial-overlap citation drifted"
    );
    for required in [
        "same-span incompatible slots stay a conflict set",
        "no source-function-order winner",
        "no silent truncation",
        "Categorical defaults only; no numeric bound",
        "production span_relation classifier",
    ] {
        assert!(g14.contains(required), "G14 rationale drifted: {required}");
    }
}

// ═══ T03: construction-family hostile synthetics (fixture-driven, test-only) ═══
//
// Blocking rework F1 (M200 S03): the hostile seed vocabulary is test data. The
// closed fixture reader, the family/seed/status tables and the refusal
// contract live here in the integration test - `npa_bounds.rs` stays
// untouched and no product enum/const/dictionary is minted to mirror the
// fixture. Executable families run existing production surfaces (`lex`,
// `capture_lawrefs`, `collect_unknown_forms_from_text`); deferred families
// record explicit refusal categories only - never a unique answer, never an
// overlaid runtime. The fixture stays synthetic, count-only and
// source-independent; unknown family/seed labels fail the reader closed.

const FIXTURE_RELATIVE_PATH: &str = "crates/ln-decode/tests/fixtures/npa/hostile-bounds.txt";
const CONTEXT_YAML_RELATIVE_PATH: &str = "prd/architecture/npa-document-context.yaml";
const REQUISITES_YAML_RELATIVE_PATH: &str = "prd/architecture/current-document-requisites.yaml";
const CYCLE_YAML_RELATIVE_PATH: &str = "prd/architecture/npa-identifying-cycle.yaml";

/// Closed construction families. Executable ones have a production surface to
/// exercise; deferred ones have none, so only refusal categories are recorded.
const EXECUTABLE_FAMILIES: [&str; 2] = ["coordinating-list", "structural-range"];
const DEFERRED_FAMILIES: [&str; 3] = [
    "cross-block-continuation",
    "alias-recursion",
    "requisites-conflict",
];

/// Closed fixture grammar: family -> expected seed labels (set equality both
/// ways; an unknown or missing label fails closed).
#[rustfmt::skip]
const EXPECTED_FAMILIES: [&str; 5] = [
    "coordinating-list", "structural-range", "cross-block-continuation",
    "alias-recursion", "requisites-conflict",
];
#[rustfmt::skip]
const EXPECTED_SEEDS: [&[&str]; 5] = [
    &["comma-heading-interrupt", "mixed-type-chain", "unclosed-parenthesis",
      "repeated-comma-empty-member", "case-address-metadata"],
    &["descending-range", "non-comparable-paths", "linguistic-hyphen",
      "quoted-digit-near-chast"],
    &["unrelated-ot-date-n", "heading-terminates-series", "two-heads",
      "continuation-cycle", "corrupt-block-order"],
    &["alias-cycle", "alias-out-of-scope", "sibling-same-word",
      "forward-keyed-lookup", "context-path-budget"],
    &["head-filename-conflict", "head-catalog-conflict", "filename-catalog-conflict",
      "geo-org-collapse", "missing-temporal-provenance", "single-source-visible"],
];
/// The 25 synthetic seeds carry exactly 42 block lines (count-only scale pin).
const EXPECTED_SEED_COUNT: usize = 25;
const EXPECTED_BLOCK_LINE_COUNT: usize = 42;

/// Deferred contract row: (family, seed, recorded status, required diagnostic
/// or ""). Status vocabulary: `context_result` statuses for context families,
/// CurrentDocumentRequisites statuses for the requisites family. The settling
/// statuses (`resolved`, `agreed`) are deliberately unreachable - recording
/// one would invent a unique answer for a family whose runtime does not exist.
#[rustfmt::skip]
const DEFERRED_REFUSALS: [(&str, &str, &str, &str); 16] = [
    ("cross-block-continuation", "unrelated-ot-date-n", "unavailable", "open_series_without_head"),
    ("cross-block-continuation", "heading-terminates-series", "conflicting", "cross_block_continuation_ambiguous"),
    ("cross-block-continuation", "two-heads", "conflicting", "incompatible_series_head"),
    ("cross-block-continuation", "continuation-cycle", "cycle", ""),
    ("cross-block-continuation", "corrupt-block-order", "unavailable", "missing_document_structure"),
    ("alias-recursion", "alias-cycle", "cycle", ""),
    ("alias-recursion", "alias-out-of-scope", "conflicting", "scoped_alias_ambiguous"),
    ("alias-recursion", "sibling-same-word", "conflicting", "scoped_alias_ambiguous"),
    ("alias-recursion", "forward-keyed-lookup", "unavailable", "unresolved_after_document_pass"),
    ("alias-recursion", "context-path-budget", "limit", "context_query_limit_reached"),
    ("requisites-conflict", "head-filename-conflict", "conflicting", "head_filename_conflict"),
    ("requisites-conflict", "head-catalog-conflict", "conflicting", "head_catalog_conflict"),
    ("requisites-conflict", "filename-catalog-conflict", "conflicting", "filename_catalog_conflict"),
    ("requisites-conflict", "geo-org-collapse", "conflicting", "org_geo_role_collapse"),
    ("requisites-conflict", "missing-temporal-provenance", "missing", "required_field_missing"),
    ("requisites-conflict", "single-source-visible", "single_source", "required_field_missing"),
];

/// Every deferred family maps to the D388 review gates that must stay
/// `deferred-undefined` (null proposed value, blocking rationale).
#[rustfmt::skip]
const DEFERRED_FAMILY_GATES: [(&str, &str); 5] = [
    ("cross-block-continuation", "adjacent-block-radius"),
    ("cross-block-continuation", "max-series-hops"),
    ("alias-recursion", "max-alias-candidates"),
    ("alias-recursion", "context-claims-fanout-memo-depth"),
    ("requisites-conflict", "source-authority-policy"),
];

/// Raw YAML pins: deferred-undefined bounds stay literals in the tracked
/// architecture sources, not parsed enums.
#[rustfmt::skip]
const CONTEXT_DEFERRED_BOUNDS: [&str; 6] = [
    "adjacent_block_radius: deferred-undefined",
    "max_series_hops: deferred-undefined",
    "max_alias_candidates: deferred-undefined",
    "max_context_claims_per_field: deferred-undefined",
    "max_linking_passes: 1",
    "on_limit: return partial/conflicting with diagnostic; never truncate into a false unique answer",
];
#[rustfmt::skip]
const CONTEXT_REQUIRED_DIAGNOSTICS: [&str; 9] = [
    "missing_document_structure", "missing_current_requisites", "open_series_without_head",
    "incompatible_series_head", "cross_block_continuation_ambiguous", "scoped_alias_ambiguous",
    "inherited_field_conflict", "context_query_limit_reached", "unresolved_after_document_pass",
];
#[rustfmt::skip]
const CONTEXT_NO_WINNER_PINS: [&str; 3] = [
    "request_kinds: [ancestor_path, adjacent_blocks, open_series_head, scoped_alias, current_document_requisites, explicit_anchor_lookup]",
    "conflict_rule: retain alternatives; never choose by distance alone",
    "no_source_rule: unresolved with missing-context diagnostic",
];
#[rustfmt::skip]
const CYCLE_DEFERRED_BOUNDS: [&str; 3] = [
    "max_members: deferred-undefined",
    "max_expanded_candidates: deferred-undefined",
    "on_limit: reject expansion with diagnostic; never truncate silently",
];
#[rustfmt::skip]
const REQUISITES_DIAGNOSTICS: [&str; 10] = [
    "head_filename_conflict", "head_catalog_conflict", "filename_catalog_conflict",
    "regional_geo_conflict", "org_geo_role_collapse", "number_normalization_ambiguous",
    "title_alias_only", "wrong_document_association", "required_field_missing",
    "source_authority_policy_missing",
];

/// Corpus-shaped tokens that must never appear in a synthetic fixture line.
#[rustfmt::skip]
const CORPUS_MARKERS: [&str; 10] = [
    ".xml", "xml/", "npa/", "courts/", "fas/", "consru", "edition-", "fnv1a64:",
    "/root/", "sha256",
];

/// One parsed fixture seed: family/seed labels plus its synthetic block lines.
struct FixtureSeed {
    family: String,
    seed: String,
    lines: Vec<String>,
}

/// Lowercase kebab label (closed fixture label grammar).
fn is_kebab_label(label: &str) -> bool {
    !label.is_empty()
        && !label.starts_with('-')
        && !label.ends_with('-')
        && label
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-')
}

/// Closed fixture reader: strict `# family=F seed=S` grammar, count-only body
/// hygiene, fail-closed errors naming family/seed/line. Test-only: the product
/// never sees this grammar (blocking rework F1).
fn parse_hostile_fixture(text: &str) -> Result<Vec<FixtureSeed>, String> {
    const HEADER: &str = "# family=";
    let mut seeds: Vec<FixtureSeed> = Vec::new();
    let mut seen_header = false;
    for (index, raw) in text.lines().enumerate() {
        let line_no = index + 1;
        if let Some(rest) = raw.strip_prefix(HEADER) {
            seen_header = true;
            let Some((family, seed)) = rest.split_once(" seed=") else {
                return Err(format!("fixture line {line_no}: header without ' seed='"));
            };
            if !is_kebab_label(family) || !is_kebab_label(seed) {
                return Err(format!(
                    "fixture line {line_no}: labels must be lowercase kebab: '{family}'/'{seed}'"
                ));
            }
            seeds.push(FixtureSeed {
                family: family.to_owned(),
                seed: seed.to_owned(),
                lines: Vec::new(),
            });
        } else if raw.starts_with('#') {
            if seen_header {
                return Err(format!(
                    "fixture line {line_no}: comment after the first seed header"
                ));
            }
        } else if raw.trim().is_empty() {
            continue; // blank line: seed separator only
        } else {
            let Some(last) = seeds.last_mut() else {
                return Err(format!(
                    "fixture line {line_no}: body before any seed header"
                ));
            };
            if raw.len() > 240 {
                return Err(format!(
                    "{}/{} line {line_no}: body line is not synthetic-scale",
                    last.family, last.seed
                ));
            }
            for marker in CORPUS_MARKERS {
                if raw.contains(marker) {
                    return Err(format!(
                        "{}/{} line {line_no}: corpus marker '{marker}' in a synthetic fixture",
                        last.family, last.seed
                    ));
                }
            }
            last.lines.push(raw.to_owned());
        }
    }
    let empty: Vec<&str> = seeds
        .iter()
        .filter(|seed| seed.lines.is_empty())
        .map(|seed| seed.seed.as_str())
        .collect();
    if !empty.is_empty() {
        return Err(format!("seeds without body lines: {empty:?}"));
    }
    Ok(seeds)
}

/// Fail-closed closed-set equality: every parsed (family, seed) is expected,
/// every expected (family, seed) is present, labels appear exactly once.
fn require_closed_sets(seeds: &[FixtureSeed]) -> Result<(), String> {
    for seed in seeds {
        let Some(family_index) = EXPECTED_FAMILIES
            .iter()
            .position(|family| *family == seed.family)
        else {
            return Err(format!("unknown family: '{}'", seed.family));
        };
        if !EXPECTED_SEEDS[family_index].contains(&seed.seed.as_str()) {
            return Err(format!("unknown seed: '{}/{}'", seed.family, seed.seed));
        }
        let duplicates = seeds
            .iter()
            .filter(|other| other.family == seed.family && other.seed == seed.seed)
            .count();
        if duplicates != 1 {
            return Err(format!(
                "seed must appear exactly once: '{}/{}' ({duplicates})",
                seed.family, seed.seed
            ));
        }
    }
    for (family_index, family) in EXPECTED_FAMILIES.iter().enumerate() {
        let present: Vec<&str> = seeds
            .iter()
            .filter(|seed| &seed.family == family)
            .map(|seed| seed.seed.as_str())
            .collect();
        for seed in EXPECTED_SEEDS[family_index] {
            if !present.contains(seed) {
                return Err(format!("missing seed: '{family}/{seed}'"));
            }
        }
        if present.len() != EXPECTED_SEEDS[family_index].len() {
            return Err(format!("family '{family}' seed count drifted"));
        }
    }
    Ok(())
}

/// Load pipeline: parse + closed-set equality (the surface tampered fixtures hit).
fn load_hostile_fixture(text: &str) -> Result<Vec<FixtureSeed>, String> {
    let seeds = parse_hostile_fixture(text)?;
    require_closed_sets(&seeds)?;
    Ok(seeds)
}

/// Distinct ASCII digit runs inside captured spans (count-only enumeration probe).
fn digit_groups<'s>(line: &'s str, captures: &[LawRef]) -> std::collections::BTreeSet<&'s str> {
    let mut groups = std::collections::BTreeSet::new();
    for capture in captures {
        let text = capture.user_text(line);
        let bytes = text.as_bytes();
        let mut index = 0;
        while index < bytes.len() {
            if bytes[index].is_ascii_digit() {
                let start = index;
                while index < bytes.len() && bytes[index].is_ascii_digit() {
                    index += 1;
                }
                groups.insert(&text[start..index]);
            } else {
                index += 1;
            }
        }
    }
    groups
}

/// T03: the fixture itself stays a preserved, synthetic, closed vocabulary and
/// the reader fails closed on every unknown label, tampering and corpus marker.
#[test]
fn t12_hostile_fixture_closed_reader() {
    let text = read_text(FIXTURE_RELATIVE_PATH);
    assert_eq!(
        text.lines().count(),
        98,
        "the 98-line synthetic fixture is preserved verbatim"
    );
    assert!(
        text.contains("# npa-hostile-bounds/v1"),
        "fixture header marker drifted"
    );
    assert!(
        text.contains("invented test vocabulary"),
        "fixture must declare its synthetic vocabulary (no corpus excerpt)"
    );
    for marker in [".xml", "/root/", "consru"] {
        assert!(
            !text.contains(marker),
            "path-like marker '{marker}' must not appear anywhere in the fixture"
        );
    }

    let seeds = load_hostile_fixture(&text).expect("closed fixture reader");
    assert_eq!(seeds.len(), EXPECTED_SEED_COUNT);
    assert_eq!(
        seeds.iter().map(|seed| seed.lines.len()).sum::<usize>(),
        EXPECTED_BLOCK_LINE_COUNT,
        "count-only scale drifted"
    );
    for seed in &seeds {
        assert!(
            EXECUTABLE_FAMILIES.contains(&seed.family.as_str())
                || DEFERRED_FAMILIES.contains(&seed.family.as_str()),
            "family is neither executable nor deferred: {}",
            seed.family
        );
    }

    // Fail-closed tampering table: (name, mutated fixture, error fragment).
    let drop_seed = |text: &str, dropped: &str| -> String {
        let mut out = String::new();
        let mut skipping = false;
        for line in text.lines() {
            if line.starts_with("# family=") {
                skipping = line.contains(&format!(" seed={dropped}"));
            }
            if !skipping {
                out.push_str(line);
                out.push('\n');
            }
        }
        out
    };
    #[rustfmt::skip]
    let tampered: [(&str, String, &str); 7] = [
        ("unknown family", text.replace("family=alias-recursion", "family=alias-bogus"), "unknown family"),
        ("unknown seed", text.replace("seed=alias-cycle", "seed=alias-bogus"), "unknown seed"),
        ("missing seed", drop_seed(&text, "two-heads"), "missing seed"),
        ("corpus marker", format!("{text}файл: npa/document_2001-12-30_195-fz.xml\n"), "corpus marker"),
        ("uppercase label", text.replace("seed=alias-cycle", "seed=Alias-Cycle"), "lowercase kebab"),
        ("header without seed", text.replace("# family=alias-recursion seed=alias-cycle", "# family=alias-recursion"), "header without ' seed='"),
        ("body without header", format!("статьи 3 настоящего Кодекса\n{text}"), "body before any seed header"),
    ];
    for (name, mutated, expected) in tampered {
        let error = load_hostile_fixture(&mutated).err().unwrap_or_else(|| {
            panic!("{name}: tampered fixture must fail closed");
        });
        assert!(
            error.contains(expected),
            "{name}: error must name the failure: {error}"
        );
    }
}

/// T03: executable construction families run the real production surfaces over
/// hostile synthetic lines; ranges never enumerate; blocks are never joined.
#[test]
fn t13_executable_families_exercise_production_surfaces() {
    let text = read_text(FIXTURE_RELATIVE_PATH);
    let seeds = load_hostile_fixture(&text).expect("closed fixture reader");
    let mut executable_seeds = 0usize;
    for seed in &seeds {
        if !EXECUTABLE_FAMILIES.contains(&seed.family.as_str()) {
            continue;
        }
        executable_seeds += 1;
        for line in &seed.lines {
            let ctx = format!("{}/{}", seed.family, seed.seed);
            // Covering lexer on hostile synthetic text: full coverage, no gaps,
            // boundary-safe, deterministic (fragment-local by construction).
            let tokens = lex(line);
            assert!(!tokens.is_empty(), "{ctx}: lexer returned no tokens");
            assert_eq!(
                tokens[0].span.start(),
                0,
                "{ctx}: lexer does not start at 0"
            );
            assert_eq!(
                tokens.last().expect("non-empty").span.end(),
                line.len(),
                "{ctx}: lexer does not cover the line end"
            );
            for pair in tokens.windows(2) {
                assert_eq!(
                    pair[0].span.end(),
                    pair[1].span.start(),
                    "{ctx}: covering lexer has a gap"
                );
            }
            assert_eq!(tokens, lex(line), "{ctx}: lexer is not deterministic");

            // Fragment-local captures: spans bounded by the line itself; the
            // suite never concatenates blocks, so no capture can cross blocks.
            let captures = capture_lawrefs(line);
            assert_eq!(
                captures,
                capture_lawrefs(line),
                "{ctx}: capture is not deterministic"
            );
            for capture in &captures {
                assert!(
                    capture.span.start() < capture.span.end(),
                    "{ctx}: empty capture span"
                );
                assert!(
                    capture.span.end() <= line.len(),
                    "{ctx}: capture exceeds the line"
                );
                assert!(
                    !capture.user_text(line).is_empty(),
                    "{ctx}: empty capture text"
                );
            }

            // Unsupported-form census stays count-only: kind/span/fingerprint
            // identity, stable 16-hex fingerprints, bounded spans.
            let forms = collect_unknown_forms_from_text(line);
            assert_eq!(
                forms,
                collect_unknown_forms_from_text(line),
                "{ctx}: census is not deterministic"
            );
            for form in &forms {
                assert!(
                    form.span().start() < form.span().end() && form.span().end() <= line.len(),
                    "{ctx}: census span out of bounds"
                );
                assert_eq!(
                    form.fingerprint().len(),
                    16,
                    "{ctx}: fingerprint is not 16 hex chars"
                );
                assert!(
                    form.fingerprint()
                        .bytes()
                        .all(|byte| byte.is_ascii_hexdigit()),
                    "{ctx}: fingerprint is not hex"
                );
            }

            // Construction-family pins (categorical; no numeric bound minted).
            match seed.seed.as_str() {
                "comma-heading-interrupt" => {
                    if line.starts_with("принимая") || line.starts_with("Раздел") {
                        assert!(
                            captures.is_empty(),
                            "{ctx}: heading/introductory line must capture nothing"
                        );
                    }
                    if line.starts_with("статьи 3") {
                        let ids: Vec<&str> = captures
                            .iter()
                            .map(|capture| capture.pattern_id.as_str())
                            .collect();
                        assert_eq!(
                            captures.len(),
                            2,
                            "{ctx}: post-heading member keeps exactly its two candidates"
                        );
                        assert!(
                            ids.contains(&"fullword-ref"),
                            "{ctx}: fullword member candidate drifted"
                        );
                        assert!(
                            ids.contains(&"anaphora_candidate"),
                            "{ctx}: anaphora candidate drifted"
                        );
                    }
                }
                "mixed-type-chain" => {
                    let date_docno = captures
                        .iter()
                        .filter(|capture| capture.pattern_id == "date-docno-window")
                        .count();
                    assert_eq!(
                        date_docno,
                        1,
                        "{ctx}: only the fully shaped doc-no window binds; lone dates and N-only tails invent nothing"
                    );
                }
                "repeated-comma-empty-member" => {
                    let fullword = captures
                        .iter()
                        .filter(|capture| capture.pattern_id == "fullword-ref")
                        .count();
                    assert_eq!(
                        fullword, 2,
                        "{ctx}: both real members captured; the empty member invents nothing"
                    );
                }
                "descending-range" => {
                    let ranges: Vec<_> = captures
                        .iter()
                        .filter(|capture| capture.pattern_id == "range_candidate")
                        .collect();
                    assert_eq!(
                        ranges.len(),
                        1,
                        "{ctx}: exactly one endpoint-pair range candidate"
                    );
                    assert_eq!(
                        ranges[0]
                            .slots
                            .range
                            .as_ref()
                            .map(|(a, b)| (a.as_str(), b.as_str())),
                        Some(("7.32", "7.29")),
                        "{ctx}: endpoints must stay as written (descending stays descending)"
                    );
                    let joined: String = captures
                        .iter()
                        .map(|capture| capture.user_text(line))
                        .collect();
                    assert!(
                        !joined.contains("7.30") && !joined.contains("7.31"),
                        "{ctx}: range capture enumerated intermediate designations"
                    );
                }
                "non-comparable-paths" => {
                    assert!(
                        !captures
                            .iter()
                            .any(|capture| capture.pattern_id == "range_candidate"),
                        "{ctx}: cross-level path must not become a range"
                    );
                    assert_eq!(
                        digit_groups(line, &captures),
                        std::collections::BTreeSet::from(["3", "5"]),
                        "{ctx}: captured numbers drifted beyond the written endpoints"
                    );
                }
                "linguistic-hyphen" => {
                    assert!(
                        !line.bytes().any(|byte| byte.is_ascii_digit()),
                        "{ctx}: precondition drifted (seed line has no digits)"
                    );
                    assert!(
                        captures.is_empty(),
                        "{ctx}: linguistic hyphen must not mint a capture"
                    );
                }
                "quoted-digit-near-chast" => {
                    assert!(
                        !captures
                            .iter()
                            .any(|capture| capture.pattern_id == "range_candidate"),
                        "{ctx}: quoted digits must not become a HierNum range"
                    );
                    assert!(
                        !digit_groups(line, &captures).contains("3"),
                        "{ctx}: quoted range enumerated an intermediate value"
                    );
                }
                _ => {}
            }
        }
    }
    assert_eq!(executable_seeds, 9, "executable fixture seeds drifted");
}

/// T03: deferred construction families record explicit refusal categories from
/// the closed YAML vocabularies - never a unique answer, never overlaid
/// runtime; the D388 review gates for them stay deferred-undefined.
#[test]
fn t14_deferred_families_record_refusal_contract() {
    let text = read_text(FIXTURE_RELATIVE_PATH);
    let seeds = load_hostile_fixture(&text).expect("closed fixture reader");
    let context_yaml = read_text(CONTEXT_YAML_RELATIVE_PATH);
    let requisites_yaml = read_text(REQUISITES_YAML_RELATIVE_PATH);
    let cycle_yaml = read_text(CYCLE_YAML_RELATIVE_PATH);

    assert!(
        context_yaml
            .contains("statuses: [resolved, partial, conflicting, unavailable, cycle, limit]"),
        "context_result status vocabulary drifted"
    );
    assert!(
        requisites_yaml.contains(
            "statuses: [agreed, single_source, conflicting, missing, invalid, association_failed]"
        ),
        "requisites status vocabulary drifted"
    );
    for pin in CONTEXT_DEFERRED_BOUNDS {
        assert!(
            context_yaml.contains(pin),
            "context bounds pin drifted: {pin}"
        );
    }
    for pin in CONTEXT_NO_WINNER_PINS {
        assert!(
            context_yaml.contains(pin),
            "context no-winner pin drifted: {pin}"
        );
    }
    for diagnostic in CONTEXT_REQUIRED_DIAGNOSTICS {
        assert!(
            context_yaml.contains(&format!("- {diagnostic}")),
            "context diagnostic drifted: {diagnostic}"
        );
    }
    for pin in CYCLE_DEFERRED_BOUNDS {
        assert!(
            cycle_yaml.contains(pin),
            "coordinating-frame bounds pin drifted: {pin}"
        );
    }
    for diagnostic in REQUISITES_DIAGNOSTICS {
        assert!(
            requisites_yaml.contains(&format!("- {diagnostic}")),
            "requisites diagnostic drifted: {diagnostic}"
        );
    }
    assert!(
        requisites_yaml.contains("status: deferred-undefined"),
        "source authority policy must stay deferred-undefined"
    );
    assert!(
        requisites_yaml.contains("default: no winner; expose conflict"),
        "requisites no-winner default drifted"
    );
    assert!(
        requisites_yaml.contains(
            "conflicting has no selected value without a tracked field/source authority policy"
        ),
        "requisites conflicting-value rule drifted"
    );

    // Set equality both ways between deferred fixture seeds and refusal rows.
    let mut deferred_seeds = 0usize;
    for seed in &seeds {
        if !DEFERRED_FAMILIES.contains(&seed.family.as_str()) {
            continue;
        }
        deferred_seeds += 1;
        let row = DEFERRED_REFUSALS
            .iter()
            .find(|(family, label, _, _)| *family == seed.family && *label == seed.seed)
            .unwrap_or_else(|| {
                panic!(
                    "deferred seed without a refusal row: {}/{}",
                    seed.family, seed.seed
                )
            });
        let (family, _, status, diagnostic) = *row;
        match family {
            "requisites-conflict" => {
                const STATUSES: [&str; 6] = [
                    "agreed",
                    "single_source",
                    "conflicting",
                    "missing",
                    "invalid",
                    "association_failed",
                ];
                assert!(
                    STATUSES.contains(&status),
                    "{family}/{}: status '{status}' is outside the requisites vocabulary",
                    seed.seed
                );
                assert_ne!(
                    status, "agreed",
                    "{family}/{}: a settled answer must not be invented",
                    seed.seed
                );
                assert!(
                    REQUISITES_DIAGNOSTICS.contains(&diagnostic),
                    "{family}/{}: diagnostic '{diagnostic}' is outside the closed set",
                    seed.seed
                );
            }
            _ => {
                const STATUSES: [&str; 6] = [
                    "resolved",
                    "partial",
                    "conflicting",
                    "unavailable",
                    "cycle",
                    "limit",
                ];
                assert!(
                    STATUSES.contains(&status),
                    "{family}/{}: status '{status}' is outside the context_result vocabulary",
                    seed.seed
                );
                assert_ne!(
                    status, "resolved",
                    "{family}/{}: recording 'resolved' invents a unique answer",
                    seed.seed
                );
                if !diagnostic.is_empty() {
                    assert!(
                        CONTEXT_REQUIRED_DIAGNOSTICS.contains(&diagnostic),
                        "{family}/{}: diagnostic '{diagnostic}' is outside the required set",
                        seed.seed
                    );
                }
            }
        }
    }
    assert_eq!(deferred_seeds, 16, "deferred fixture seeds drifted");
    for (family, label, _, _) in DEFERRED_REFUSALS {
        assert!(
            DEFERRED_FAMILIES.contains(&family),
            "refusal row family is not deferred: {family}"
        );
        assert!(
            seeds
                .iter()
                .any(|seed| seed.family == family && seed.seed == label),
            "refusal row without a fixture seed: {family}/{label}"
        );
    }

    // D388 reviewability: every deferred-family gate stays deferred-undefined
    // with a null proposed value and a blocking rationale.
    let review_text = read_text(REVIEW_RELATIVE_PATH);
    validate_review(&review_text).expect("closed review schema re-validates");
    let root = parse_json(&review_text).expect("review parses via the closed parser");
    let gates = root
        .get("gate_decisions")
        .expect("gate_decisions present")
        .as_arr()
        .expect("gate rows array");
    for (family, gate) in DEFERRED_FAMILY_GATES {
        let row_text = gate_row_slice(&review_text, gate).expect("gate row slice exists");
        assert!(
            row_text.contains("\"verdict\": \"deferred-undefined\""),
            "{family}: gate '{gate}' must stay deferred-undefined"
        );
        assert!(
            row_text.contains("blocking reason"),
            "{family}: gate '{gate}' rationale must name its blocking reason"
        );
        let structured =
            find_row(gates, "gate_decisions", "gate", gate).expect("structured gate row");
        assert!(
            int_or_null(structured, "proposed_value", gate)
                .expect("proposed_value parses")
                .is_none(),
            "{family}: gate '{gate}' must not carry a proposed value"
        );
    }

    // The surfaces these families would need stay explicitly unavailable.
    for metric in [
        "accepted continues_series hop count",
        "scoped alias candidate count",
        "ContextRequest count and fan-out",
        "memo hit rate and derivation depth",
        "SemanticFieldClaim count per field",
        "context sufficient/partial/conflicting/cycle/limit distributions",
    ] {
        assert!(
            UNAVAILABLE_METRICS.contains(&metric),
            "deferred family surface must stay unavailable-until-runtime: {metric}"
        );
    }
}
