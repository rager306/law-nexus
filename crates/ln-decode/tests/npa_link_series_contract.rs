//! M211 S03 T01: cross-block series continuation contract (RC28-F07).
//!
//! Hand-rolled fixture reader (D602): the frozen 40-doc seed is read from
//! `tests/fixtures/npa-members/typed-parity-fixture.tsv` (doc -> frag) and the
//! fragment texts from `tests/fixtures/npa-lawref/`. A missing source fails
//! closed instead of silently skipping.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;
use ln_decode::npa_continuation::{eligible_continuation_head_for, ContinuationEligibility};
use ln_decode::npa_link::{self, LinkDerivation, LinkDiagnostic, LinkedRelationKind};

fn fixture_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

fn fixture_tsv() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/npa-members/typed-parity-fixture.tsv")
}

fn read_fixture() -> BTreeMap<String, Vec<String>> {
    let text = std::fs::read_to_string(fixture_tsv()).expect("typed parity fixture must exist");
    let mut docs: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut current: Option<String> = None;
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        match cols.first().copied() {
            Some("doc") => {
                current = Some(cols[1].to_string());
                docs.entry(cols[1].to_string()).or_default();
            }
            Some("frag") if cols.len() >= 2 => {
                if let Some(cur) = current.as_deref() {
                    if let Some(frags) = docs.get_mut(cur) {
                        frags.push(cols[1].to_string());
                    }
                }
            }
            _ => {}
        }
    }
    assert!(!docs.is_empty(), "MISSING SOURCE: fixture is mandatory");
    docs
}

fn load_doc(docs: &BTreeMap<String, Vec<String>>, doc: &str) -> Vec<String> {
    let frags = docs
        .get(doc)
        .unwrap_or_else(|| panic!("MISSING SOURCE: {doc} absent from fixture"));
    assert!(!frags.is_empty(), "MISSING SOURCE: {doc} has no fragments");
    frags
        .iter()
        .map(|frag| {
            let path = fixture_dir().join(frag);
            std::fs::read_to_string(&path)
                .unwrap_or_else(|e| panic!("MISSING SOURCE: {}: {e}", path.display()))
        })
        .collect()
}

/// Frozen-seed cross-block candidate pairs (head block -> tail block), from
/// the research anchor list in `211-03-RESEARCH.md`. Each `head` block ends
/// open (`(в ред. … N …,`) and each `tail` block is a bare `от ДАТА N` list.
const SERIES_PAIRS: &[(&str, usize, usize)] = &[
    ("npa-doc-015", 1, 2),
    ("npa-doc-016", 1, 2),
    ("npa-doc-017", 1, 2),
    ("npa-doc-019", 1, 2),
    ("npa-doc-020", 1, 2),
    ("npa-doc-021", 1, 2),
    ("npa-doc-021", 3, 4),
    ("npa-doc-022", 1, 2),
    ("npa-doc-025", 1, 2),
    ("npa-doc-026", 1, 2),
];

#[test]
fn frozen_seed_cross_block_series_pairs_are_linked() {
    let docs = read_fixture();
    let mut found = 0usize;
    for (doc, head_block, tail_block) in SERIES_PAIRS {
        let paras = load_doc(&docs, doc);
        let (relations, _) = npa_link::link_series(&paras);
        let hit = relations.iter().any(|relation| {
            relation.kind == LinkedRelationKind::ContinuesSeries
                && relation.evidence.len() == 2
                && relation.evidence[0].block == *head_block
                && relation.evidence[1].block == *tail_block
        });
        assert!(
            hit,
            "{doc}: expected ContinuesSeries {head_block}->{tail_block}; got {:?}",
            relations
                .iter()
                .map(|r| (r.kind, r.evidence.clone()))
                .collect::<Vec<_>>()
        );
        found += 1;
    }
    assert!(
        found >= 10,
        "at least 10 named positive pairs must be covered (found {found})"
    );
}

#[test]
fn every_series_edge_carries_two_valid_local_anchors() {
    let docs = read_fixture();
    for doc in [
        "npa-doc-012",
        "npa-doc-015",
        "npa-doc-016",
        "npa-doc-017",
        "npa-doc-019",
        "npa-doc-020",
        "npa-doc-021",
        "npa-doc-022",
        "npa-doc-025",
        "npa-doc-026",
    ] {
        let paras = load_doc(&docs, doc);
        let (relations, _) = npa_link::link_series(&paras);
        for relation in &relations {
            assert_eq!(
                relation.evidence.len(),
                2,
                "{doc}: a continuation carries exactly two local anchors"
            );
            assert_ne!(
                relation.evidence[0].block, relation.evidence[1].block,
                "{doc}: never one cross-block span"
            );
            for span in &relation.evidence {
                let source = paras
                    .get(span.block)
                    .expect("evidence block must be in range");
                npa_anchor::check_span(source, *span)
                    .unwrap_or_else(|e| panic!("{doc}: invalid local anchor {span:?}: {e:?}"));
            }
        }
    }
}

#[test]
fn three_unrelated_complete_citations_do_not_continue() {
    let paras = vec![
        "Федеральный закон от 01.01.2020 N 1-ФЗ".to_string(),
        "Федеральный кодекс от 02.02.2021 N 2-ФЗ".to_string(),
        "Федеральный закон от 03.03.2022 N 3-ФЗ".to_string(),
    ];
    let (relations, _) = npa_link::link_series(&paras);
    assert!(
        relations.is_empty(),
        "complete citations must not form a series: {relations:?}"
    );
}

#[test]
fn open_tail_after_unrelated_complete_citations_has_no_head() {
    // No preceding block ends open, so the bare tail cannot continue an
    // unrelated completed citation (fail-closed).
    let paras = vec![
        "Федеральный закон от 01.01.2020 N 1-ФЗ".to_string(),
        "Федеральный кодекс от 02.02.2021 N 2-ФЗ".to_string(),
        "Федеральный закон от 03.03.2022 N 3-ФЗ".to_string(),
        "от 04.04.2023 N 4-ФЗ".to_string(),
    ];
    let (relations, diagnostics) = npa_link::link_series(&paras);
    assert!(
        relations.is_empty(),
        "no open head => no continuation: {relations:?}"
    );
    assert!(diagnostics.contains(&LinkDiagnostic::OpenSeriesWithoutHead));
}

#[test]
fn orphan_tail_without_preceding_block_is_not_linked() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-012");
    // frag-046 (`от 09.04.2020 N 16-П)`) is the first block: no head exists.
    let (relations, diagnostics) = npa_link::link_series(&paras);
    assert!(
        relations.is_empty(),
        "doc-012 frag-046 has no eligible head: {relations:?}"
    );
    assert!(diagnostics.contains(&LinkDiagnostic::OpenSeriesWithoutHead));
}

#[test]
fn cross_block_series_does_not_inherit_type_into_tail_member() {
    // Head block stops mid-list; the next block has only its own anchor.
    let paras = vec![
        "Федерального закона от 01.01.2020 N 1-ФЗ,".to_string(),
        "от 02.02.2021 N 2-ФЗ".to_string(),
    ];
    let (relations, diagnostics) = npa_link::link_series(&paras);
    assert_eq!(
        relations.len(),
        1,
        "open head + bare tail => one continuation: {relations:?}"
    );
    assert_eq!(relations[0].kind, LinkedRelationKind::ContinuesSeries);
    assert_eq!(relations[0].evidence[0].block, 0);
    assert_eq!(relations[0].evidence[1].block, 1);
    assert!(diagnostics.is_empty(), "{diagnostics:?}");

    let members = npa_link::anchored_members(&paras);
    assert_eq!(members.len(), 2, "{members:?}");
    assert!(
        !members[0].type_name.is_empty(),
        "head member keeps its locally written TYPE: {}",
        members[0].type_name
    );
    assert_eq!(
        members[1].type_name, "",
        "cross-block TYPE must not be inherited into the tail member"
    );
    assert_eq!(members[1].derivation, LinkDerivation::TypedAnchor);
}

#[test]
fn continuation_predicate_is_the_single_source_of_truth() {
    let all_true = ContinuationEligibility {
        head_status_proposed: true,
        tail_status_not_rejected: true,
        distinct_frames: true,
        distinct_blocks: true,
        head_admits_act_type: true,
        head_order_before_tail: true,
        same_scope: true,
        head_retains_derivation: true,
        tail_retains_derivation: true,
    };
    assert!(eligible_continuation_head_for(&all_true));
    for clause in 0..9 {
        let mut e = all_true;
        match clause {
            0 => e.head_status_proposed = false,
            1 => e.tail_status_not_rejected = false,
            2 => e.distinct_frames = false,
            3 => e.distinct_blocks = false,
            4 => e.head_admits_act_type = false,
            5 => e.head_order_before_tail = false,
            6 => e.same_scope = false,
            7 => e.head_retains_derivation = false,
            _ => e.tail_retains_derivation = false,
        }
        assert!(
            !eligible_continuation_head_for(&e),
            "clause {clause} must be load-bearing"
        );
    }
}

#[test]
fn link_modules_stay_serde_fs_env_free() {
    for file in ["src/npa_link.rs", "src/npa_continuation.rs"] {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(file);
        let source = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {file}: {e}"));
        for forbidden in [
            "serde",
            "Deserialize",
            "Serialize",
            "serde_json",
            "std::fs",
            "std::env",
        ] {
            assert!(
                !source.contains(forbidden),
                "{file} must stay serde/fs/env-free (D602): found {forbidden}"
            );
        }
    }
}
