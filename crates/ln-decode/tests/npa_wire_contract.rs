//! M211 S02/T03 contract tests for the `m207-hybrid-records/v1` Rust
//! emitter (`ln_decode::npa_wire`). Pure library tests: no filesystem
//! writes, no corpus access, no Python subprocess. The end-to-end
//! validator handshake is exercised separately against the frozen
//! `scripts/m207_hybrid_eval_experiment.py --validate-records`.
//!
//! The absence check reads `npa_wire.rs` at compile time and asserts the
//! module stays free of an external serialization crate (D602/D328).

use ln_decode::npa_anchor;
use ln_decode::npa_wire::WireDocument;
use ln_decode::npa_wire::{self, RECORDS_ORIGIN_RUST};

fn sample_document() -> WireDocument {
    let blocks = vec![
        "Федеральный закон от 01.01.2020 N 1-ФЗ".to_string(),
        "Действующей лицензии от 24.02.2021 N 0001976".to_string(),
    ];
    npa_wire::wire_document_from_blocks("doc-1", &blocks).expect("non-empty blocks")
}

/// Key names of the top-level object: lines that start with exactly two
/// spaces followed by a quote. Deeper levels are indented by four or more.
fn top_level_keys(json: &str) -> Vec<String> {
    json.lines()
        .filter_map(|line| {
            let rest = line.strip_prefix("  ")?;
            let rest = rest.strip_prefix('"')?;
            let end = rest.find('"')?;
            Some(rest[..end].to_string())
        })
        .collect()
}

#[test]
fn render_is_byte_deterministic() {
    let docs = vec![sample_document()];
    let first = npa_wire::render_records(&docs, RECORDS_ORIGIN_RUST);
    let second = npa_wire::render_records(&docs, RECORDS_ORIGIN_RUST);
    assert_eq!(first, second, "two renders must be byte-identical");
}

#[test]
fn envelope_carries_required_and_honesty_keys() {
    let body = npa_wire::render_records(&[sample_document()], RECORDS_ORIGIN_RUST);
    for needle in [
        "\"schema\": \"m207-hybrid-records/v1\"",
        "\"schema_version\": 1",
        "\"provenance_origin\": \"rust-runtime\"",
        "\"lifecycle\": [",
        "\"authoritative\": false",
        "\"is_gold\": false",
        "\"not_human\": true",
        "\"not_s03_metrics\": true",
        "\"source_validation\": \"bytes-present\"",
        "\"alignment_policy\": \"local-anchor-identity-v1\"",
    ] {
        assert!(body.contains(needle), "missing envelope fragment {needle}");
    }
    assert!(!body.starts_with('\u{feff}'), "no UTF-8 BOM");
    assert!(body.ends_with('\n'), "canonical bytes end with newline");
}

#[test]
fn top_level_keys_are_closed_and_sorted() {
    let body = npa_wire::render_records(&[sample_document()], RECORDS_ORIGIN_RUST);
    let keys = top_level_keys(&body);
    let mut expected = vec![
        "alignment_policy",
        "authoritative",
        "bundles",
        "documents",
        "is_gold",
        "lifecycle",
        "limits",
        "non_claims",
        "not_human",
        "not_s03_metrics",
        "provenance_origin",
        "schema",
        "schema_version",
        "source_validation",
    ];
    expected.sort_unstable();
    assert_eq!(
        keys, expected,
        "envelope must expose exactly the closed keys"
    );

    let mut sorted = keys.clone();
    sorted.sort_unstable();
    assert_eq!(keys, sorted, "top-level keys must be sorted");
    assert!(
        body.lines().nth(1).is_some_and(|l| l.starts_with("  \"")),
        "object entries are indented by two spaces"
    );
}

#[test]
fn forbidden_keys_never_appear() {
    let body = npa_wire::render_records(&[sample_document()], RECORDS_ORIGIN_RUST);
    for key in [
        "false_authority",
        "span_rate",
        "slot_rate",
        "scope_rate",
        "binding_rate",
        "abstention_rate",
        "aspect_rates",
        "submissions",
        "coder_id",
        "coder",
        "adjudication",
        "adjudications",
        "corpus_excerpt",
        "raw_text",
        "legal_text",
        "source_text",
        "corpus_text",
        "raw_legal_text",
    ] {
        let needle = format!("\"{key}\"");
        assert!(!body.contains(&needle), "forbidden key {key} leaked");
    }
}

#[test]
fn bundle_shape_and_fragment_ids() {
    let body = npa_wire::render_records(&[sample_document()], RECORDS_ORIGIN_RUST);
    for needle in [
        "\"bundle_id\": \"doc-1\"",
        "\"construction\": \"act-requisites\"",
        "\"context_status\": \"available\"",
        "\"focus_id\": \"occ-0-0\"",
        "\"fragment_id\": \"doc-1#0\"",
        "\"fragment_id\": \"doc-1#1\"",
        "\"context_only\": []",
        "\"relations\": []",
    ] {
        assert!(body.contains(needle), "missing bundle fragment {needle}");
    }
}

#[test]
fn byte_length_and_spans_are_valid() {
    let doc = sample_document();
    let mut occurrences = 0usize;
    for fragment in &doc.fragments {
        assert_eq!(
            fragment.byte_length,
            fragment.source_utf8.len(),
            "byte_length must equal source_utf8 byte length"
        );
        for occ in &fragment.occurrences {
            occurrences += 1;
            assert!(
                npa_anchor::check_span(&fragment.source_utf8, occ.span).is_ok(),
                "occurrence span must be a valid UTF-8 byte span"
            );
            if let Some(evidence) = occ.type_evidence {
                assert!(
                    npa_anchor::check_span(&fragment.source_utf8, evidence).is_ok(),
                    "type_evidence must be a valid UTF-8 byte span"
                );
            }
        }
    }
    assert!(occurrences >= 2, "sample must yield typed occurrences");
    let body = npa_wire::render_records(&[doc], RECORDS_ORIGIN_RUST);
    assert!(
        body.contains("\"byte_length\": "),
        "byte_length is rendered"
    );
}

#[test]
fn unresolved_occurrence_nulls_kind_source() {
    let blocks = vec!["от 01.01.2020 N 1-ФЗ".to_string()];
    let doc = npa_wire::wire_document_from_blocks("doc-u", &blocks).expect("non-empty blocks");
    assert!(
        doc.fragments[0]
            .occurrences
            .iter()
            .all(|o| o.unresolved && o.type_name.is_empty()),
        "no TYPE head means every occurrence is unresolved"
    );
    let body = npa_wire::render_records(&[doc], RECORDS_ORIGIN_RUST);
    assert!(body.contains("\"unresolved\": true"));
    assert!(body.contains("\"unresolved_reason\": \"type_unresolved\""));
    assert!(
        body.contains("\"source\": null"),
        "unresolved kind must have a null source"
    );
}

#[test]
fn empty_blocks_are_rejected_not_emitted() {
    assert!(npa_wire::wire_document_from_blocks("doc-0", &[]).is_none());
}

#[test]
fn argv_parser_is_strict() {
    assert!(npa_wire::parse_records_args(vec!["--bogus".to_string()]).is_err());
    assert!(npa_wire::parse_records_args(vec!["--root".to_string()]).is_err());
    assert!(npa_wire::parse_records_args(vec!["--limit".to_string(), "x".to_string()]).is_err());
    let cli = npa_wire::parse_records_args(vec![
        "--root".to_string(),
        "somewhere".to_string(),
        "--limit".to_string(),
        "3".to_string(),
    ])
    .expect("valid argv");
    assert_eq!(cli.limit, Some(3));
    assert_eq!(cli.root.as_deref(), Some("somewhere"));
}

#[test]
fn missing_root_is_a_nonzero_exit_without_output() {
    let cli = npa_wire::RecordsCli {
        root: Some("/nonexistent-law-nexus-m211-wire".to_string()),
        out: None,
        limit: None,
    };
    let run = npa_wire::run_records(&cli, std::path::Path::new("."));
    assert_eq!(run.exit_code, ln_decode::npa_sweep::EXIT_ROOT_MISSING);
    assert!(run.json.is_none(), "fatal run must not print records");
}

#[test]
fn wire_emitter_is_free_of_external_serialization_crate() {
    const WIRE_SRC: &str = include_str!("../src/npa_wire.rs");
    for needle in ["serde", "Deserialize", "serde_json"] {
        assert!(
            !WIRE_SRC.contains(needle),
            "npa_wire.rs must not reference the external crate marker {needle}"
        );
    }
}
