//! S07/T02 contract suite for the corpus FRBR bridge join.
//!
//! Two halves:
//!
//! - a hermetic half driven entirely by inline fixtures (canonical S02
//!   envelope lines, receipt lines, a timeline object and an in-memory
//!   `EditionJoinRow` map). Every negative asserts the refusal is real (not an
//!   "empty success") and carries the expected stable operation tag;
//! - a corpus-gated half that runs only when the tracked S02/m223/S06 inputs
//!   and the `consru_export` catalog are present. It skips (never false-passes)
//!   when the gitignored corpus is absent.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_consultant_parser::{
    DEFAULT_ACT_NUMBER, DEFAULT_EDITION_PREFIX, EditionJoinRow, FrbrBridgeError, FrbrBridgeJoin,
    SqliteCatalog, build_frbr_bridge_join, build_frbr_bridge_join_from_bytes, exports_path,
};
use ln_decode::consultant_uri_anchor::ConsultantUriAnchor;
use ln_decode::identity_envelope::IdentityEnvelope;

const PREFIX: &str = DEFAULT_EDITION_PREFIX;
const SHA_A: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
const SHA_B: &str = "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210";

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

fn catalog_row(path: &str, token: &str, number: i64) -> (String, EditionJoinRow) {
    (
        path.to_owned(),
        EditionJoinRow {
            relative_path: exports_path(path),
            source_id: token.to_owned(),
            edition_id: Some(format!("edition-fixture-{number:04}")),
            document_id: Some("doc-fixture-000000000000000000".to_owned()),
            edition_number: Some(number),
            revision_date: None,
        },
    )
}

struct Fixture {
    envelope: String,
    receipts: String,
    timeline: String,
    catalog: BTreeMap<String, EditionJoinRow>,
}

/// Two editions: ed1 rev-initial effect 77891 (2013-04-05), ed2 rev-2013-04-05
/// timed to effect 77892 (2013-04-06). The rev-only registry id for ed2 is the
/// 2013-04-05 expression, so exactly one divergence is expected — the counter
/// is exercised non-vacuously.
fn fixture() -> Fixture {
    let p1 = edition_path(1, "initial");
    let p2 = edition_path(2, "2013-04-05");

    let mut envelope = envelope_header(2, 2);
    envelope.push_str(&envelope_line(&p1, SHA_A, 100, &token(1)));
    envelope.push_str(&envelope_line(&p2, SHA_B, 200, &token(2)));

    let mut receipts = String::new();
    receipts.push_str(&receipt_line(&p1, SHA_A));
    receipts.push_str(&receipt_line(&p2, SHA_B));

    let timeline = timeline_json(&[(1, 77891), (2, 77892)]);

    let mut catalog = BTreeMap::new();
    let (k1, v1) = catalog_row(&p1, &token(1), 1);
    let (k2, v2) = catalog_row(&p2, &token(2), 2);
    catalog.insert(k1, v1);
    catalog.insert(k2, v2);

    Fixture {
        envelope,
        receipts,
        timeline,
        catalog,
    }
}

fn run_with(fixture: &Fixture, act: &str) -> Result<FrbrBridgeJoin, FrbrBridgeError> {
    build_frbr_bridge_join_from_bytes(
        act,
        PREFIX,
        fixture.envelope.as_bytes(),
        fixture.receipts.as_bytes(),
        fixture.timeline.as_bytes(),
        &fixture.catalog,
    )
}

fn expect_refusal(result: Result<FrbrBridgeJoin, FrbrBridgeError>, operation: &str) {
    let error = result.expect_err("the join must refuse, not succeed by default");
    assert_eq!(error.operation(), operation, "unexpected operation tag");
    assert!(
        !error.detail().is_empty(),
        "refusal detail must not be empty"
    );
}

#[test]
fn hermetic_join_binds_two_editions_and_counts_divergence() {
    let fixture = fixture();
    let join = run_with(&fixture, DEFAULT_ACT_NUMBER).expect("hermetic join succeeds");

    assert_eq!(join.act_number, "44-fz");
    assert_eq!(join.authority, "federal");
    assert_eq!(join.enactment_date, "2013-04-05");
    assert_eq!(join.work_id, "work:ru:federal:zakon:2013-04-05:44-fz");
    assert_eq!(
        join.work_eli_urn,
        "urn:lex:ru:federal:zakon:2013-04-05;44-fz"
    );
    assert_eq!(join.rows.len(), 2);
    assert_eq!(join.distinct_effect_days, 2);
    assert_eq!(join.registry_expression_id_divergence, 1);
    assert_eq!(join.totals, Default::default());

    let first = &join.rows[0];
    assert_eq!(first.edition_number, 1);
    assert_eq!(first.effect_day, 77891);
    assert_eq!(first.effect_iso, "2013-04-05");
    assert_eq!(
        first.expression_eli_urn,
        "urn:lex:ru:federal:zakon:2013-04-05;44-fz@2013-04-05"
    );
    assert_eq!(first.uri_anchor, token(1));
    assert_eq!(first.source_sha256, format!("sha256:{SHA_A}"));
    assert_eq!(first.source_revision, SHA_A);
    assert_eq!(first.document_version_ref, "m223-s07-corpus/v1");
    assert_eq!(first.decoder_profile, "source_package_decoded_text/v1");
    assert_eq!(first.catalog_edition_number, Some(1));
    assert!(first.catalog_edition_id.is_some());
    assert!(first.catalog_document_id.is_some());

    let second = &join.rows[1];
    assert_eq!(second.edition_number, 2);
    assert_eq!(second.effect_iso, "2013-04-06");
    assert_eq!(
        second.expression_eli_urn,
        "urn:lex:ru:federal:zakon:2013-04-05;44-fz@2013-04-06"
    );

    assert!(join.envelope_sha256.starts_with("sha256:"));
    assert!(join.receipts_sha256.starts_with("sha256:"));
    assert!(join.timeline_sha256.starts_with("sha256:"));
}

#[test]
fn hermetic_catalog_miss_is_refused() {
    let mut fixture = fixture();
    fixture.catalog.remove(&edition_path(2, "2013-04-05"));
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "catalog-miss");
}

#[test]
fn hermetic_anchor_byte_mismatch_is_refused() {
    let mut fixture = fixture();
    let key = edition_path(2, "2013-04-05");
    if let Some(row) = fixture.catalog.get_mut(&key) {
        row.source_id = token(999);
    }
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "anchor-mismatch");
}

#[test]
fn hermetic_receipt_sha_mismatch_is_refused() {
    let mut fixture = fixture();
    // Rewrite ed2's receipt identity to SHA_A while the envelope still pins
    // SHA_B, so the per-row receipt sha cross-check refuses.
    fixture.receipts = fixture.receipts.replace(SHA_B, SHA_A);
    expect_refusal(
        run_with(&fixture, DEFAULT_ACT_NUMBER),
        "receipt-sha-mismatch",
    );
}

#[test]
fn hermetic_receipt_set_drift_is_refused() {
    let mut fixture = fixture();
    fixture.receipts = receipt_line(&edition_path(1, "initial"), SHA_A);
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "set-mismatch");
}

#[test]
fn hermetic_unknown_act_is_refused() {
    let fixture = fixture();
    expect_refusal(run_with(&fixture, "999-fz"), "unknown-act");
}

#[test]
fn hermetic_bad_ordinal_is_refused() {
    let mut fixture = fixture();
    fixture.timeline = timeline_json(&[(1, 77891), (2, 999_999)]);
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "bad-ordinal");
}

#[test]
fn hermetic_non_ascii_payload_is_refused() {
    let mut fixture = fixture();
    fixture.receipts = fixture
        .receipts
        .replace("m223-s07-corpus/v1", "m223-s07-corpus/тест");
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "non-ascii");
}

#[test]
fn hermetic_envelope_schema_drift_is_refused() {
    let mut fixture = fixture();
    fixture.envelope = fixture.envelope.replacen(
        "m224-s02-identity-envelope/v1",
        "m224-s02-identity-envelope/v2",
        1,
    );
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "envelope-schema");
}

#[test]
fn hermetic_receipts_schema_drift_is_refused() {
    let mut fixture = fixture();
    fixture.receipts = fixture.receipts.replace(
        "m223-s07-consumer-receipt/v1",
        "m223-s07-consumer-receipt/v2",
    );
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "receipts-schema");
}

#[test]
fn hermetic_timeline_schema_drift_is_refused() {
    let mut fixture = fixture();
    fixture.timeline = fixture.timeline.replace(
        "m224-s06-edition-timeline/v1",
        "m224-s06-edition-timeline/v2",
    );
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "timeline-schema");
}

#[test]
fn hermetic_envelope_counts_drift_is_refused() {
    let mut fixture = fixture();
    // Header claims three entries while only two entity lines exist.
    fixture.envelope = fixture
        .envelope
        .replacen("\"entries\":2", "\"entries\":3", 1);
    expect_refusal(run_with(&fixture, DEFAULT_ACT_NUMBER), "envelope-counts");
}

fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

#[test]
fn corpus_44fz_join_is_complete_and_zero_mismatch() {
    let root = workspace_root();
    let catalog_path = root.join("consru_export/consru_export/catalog.sqlite");
    let envelope = root.join("prd/migration/rust-evidence/m224-s02-identity-envelope.jsonl");
    let receipts = root.join("prd/migration/rust-evidence/m223-s07-corpus-receipts.jsonl");
    let timeline = root.join("prd/migration/rust-evidence/m224-s06-edition-timeline.json");

    if !catalog_path.exists() || !envelope.exists() || !receipts.exists() || !timeline.exists() {
        eprintln!("SKIP: consru_export catalog or tracked S02/m223-S07/S06 inputs not available");
        return;
    }

    let catalog = SqliteCatalog::open_read_only(&catalog_path).expect("open the read-only catalog");
    let map = catalog
        .load_edition_join_map()
        .expect("load the edition join map");
    let join = build_frbr_bridge_join(&envelope, &receipts, &timeline, &map)
        .expect("the bounded 44-FZ join must succeed");

    assert_eq!(join.rows.len(), 118, "expected the 118 bounded editions");
    assert_eq!(join.act_number, "44-fz");
    assert_eq!(join.work_id, "work:ru:federal:zakon:2013-04-05:44-fz");
    assert_eq!(
        join.work_eli_urn,
        "urn:lex:ru:federal:zakon:2013-04-05;44-fz"
    );
    assert_eq!(join.distinct_effect_days, 118);
    assert_eq!(join.registry_expression_id_divergence, 46);
    assert_eq!(join.totals.catalog_misses, 0);
    assert_eq!(join.totals.anchor_mismatches, 0);
    assert_eq!(join.totals.join_mismatches, 0);

    let first = &join.rows[0];
    assert_eq!(first.edition_number, 1);
    assert_eq!(first.effect_iso, "2013-04-05");
    assert_eq!(
        first.expression_eli_urn,
        "urn:lex:ru:federal:zakon:2013-04-05;44-fz@2013-04-05"
    );

    let last = &join.rows[117];
    assert_eq!(last.edition_number, 118);
    assert_eq!(last.effect_iso, "2026-07-01");

    for row in &join.rows {
        assert_eq!(
            row.expression_eli_urn,
            format!("{}@{}", join.work_eli_urn, row.effect_iso)
        );
        // Re-assert the anchor byte-exact against the catalog source_id that
        // the join keyed on (catches any transport normalization).
        assert_eq!(row.uri_anchor, map[&row.relative_path].source_id);
        assert!(row.uri_anchor.starts_with("consultantplus://offline/ref="));
    }
}
