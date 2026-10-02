//! M211 S03 T05: executable linked pipeline integration proof (ADR-0029).
//!
//! The frozen 40-doc seed is read from
//! `tests/fixtures/npa-members/typed-parity-fixture.tsv` (doc -> frag) and the
//! fragment texts from `tests/fixtures/npa-lawref/` with a hand-rolled reader
//! (D602; no serde / external JSON dependency). A missing source fails closed
//! instead of silently skipping.
//!
//! Covers the single assembly point `npa_link::build_linked_document` on the
//! real fixture: input immutability, deterministic replay, cross-block series
//! edges with two valid local anchors, letterhead positives / court negatives,
//! annex `approved_by` with the Work != approver invariant, scoped aliases and
//! this-document references failing closed, and the D602 serde/fs/env absence
//! check.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;
use ln_decode::npa_link::{self, LinkDerivation, LinkDiagnostic, LinkedRelationKind};
use ln_decode::npa_typed;

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

/// Frozen-seed cross-block candidate pairs (head block -> tail block), matching
/// `npa_link_series_contract`. Each `head` block ends open (`(в ред. … N …,`);
/// each `tail` block is a bare `от ДАТА N` list.
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

/// The pipeline is run for every frozen document: the canonical typed stream is
/// untouched, the input paragraphs are untouched, and two runs are structurally
/// equal (deterministic replay).
#[test]
fn every_frozen_document_builds_deterministically_and_immutably() {
    let docs = read_fixture();
    assert_eq!(docs.len(), 40, "the frozen seed is exactly 40 documents");
    for doc in docs.keys() {
        let paras = load_doc(&docs, doc);
        let before = paras.clone();
        let typed_before = npa_typed::scan_typed_diagnosed(&paras).0;

        let first = npa_link::build_linked_document(&paras);
        let typed_after = npa_typed::scan_typed_diagnosed(&paras).0;
        let second = npa_link::build_linked_document(&paras);

        assert_eq!(
            typed_before, typed_after,
            "{doc}: the pipeline mutated the canonical TypedMember stream"
        );
        assert_eq!(paras, before, "{doc}: the pipeline mutated its input");
        assert_eq!(first, second, "{doc}: replay must be structurally stable");
    }
}

/// Member ids are contiguous and every relation endpoint resolves to a member;
/// every member / series evidence span is a valid source-local anchor.
#[test]
fn pipeline_members_are_consistent_and_evidence_is_source_local() {
    let docs = read_fixture();
    for doc in docs.keys() {
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);
        for (index, member) in linked.members.iter().enumerate() {
            assert_eq!(
                member.id, index,
                "{doc}: member ids must stay index-aligned"
            );
            let source = paras
                .get(member.evidence.block)
                .unwrap_or_else(|| panic!("{doc}: member evidence block out of range"));
            npa_anchor::check_span(source, member.evidence).unwrap_or_else(|e| {
                panic!("{doc}: member {} has an invalid span: {e:?}", member.id)
            });
        }
        for relation in &linked.relations {
            assert!(
                relation.from_id < linked.members.len(),
                "{doc}: from_id out of range"
            );
            assert!(
                relation.to_id < linked.members.len(),
                "{doc}: to_id out of range"
            );
            for span in &relation.evidence {
                let source = paras
                    .get(span.block)
                    .unwrap_or_else(|| panic!("{doc}: relation evidence block out of range"));
                npa_anchor::check_span(source, *span)
                    .unwrap_or_else(|e| panic!("{doc}: relation has an invalid span: {e:?}"));
            }
        }
    }
}

/// The named frozen cross-block continuations survive the full pipeline.
#[test]
fn frozen_seed_positive_series_edges_are_present() {
    let docs = read_fixture();
    for (doc, head_block, tail_block) in SERIES_PAIRS {
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);
        let hit = linked.relations.iter().any(|relation| {
            relation.kind == LinkedRelationKind::ContinuesSeries
                && relation.evidence.len() == 2
                && relation.evidence[0].block == *head_block
                && relation.evidence[1].block == *tail_block
        });
        assert!(
            hit,
            "{doc}: expected ContinuesSeries {head_block}->{tail_block}; got {:?}",
            linked
                .relations
                .iter()
                .filter(|r| r.kind == LinkedRelationKind::ContinuesSeries)
                .map(|r| r.evidence.clone())
                .collect::<Vec<_>>()
        );
    }
}

/// The roadmap-named edges (`doc-015 frag-061->062`, `doc-021 frag-091->092`)
/// map to their fragment positions and are emitted by the pipeline.
#[test]
fn named_frozen_series_edges_map_to_their_fragments() {
    let docs = read_fixture();
    for (doc, head_frag, tail_frag) in [
        ("npa-doc-015", "npa-frag-061.txt", "npa-frag-062.txt"),
        ("npa-doc-021", "npa-frag-091.txt", "npa-frag-092.txt"),
    ] {
        let frags = docs
            .get(doc)
            .unwrap_or_else(|| panic!("MISSING SOURCE: {doc}"));
        let head_block = frags
            .iter()
            .position(|frag| frag == head_frag)
            .unwrap_or_else(|| panic!("MISSING SOURCE: {doc}/{head_frag}"));
        let tail_block = frags
            .iter()
            .position(|frag| frag == tail_frag)
            .unwrap_or_else(|| panic!("MISSING SOURCE: {doc}/{tail_frag}"));
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);
        assert!(
            linked.relations.iter().any(|relation| {
                relation.kind == LinkedRelationKind::ContinuesSeries
                    && relation.evidence.len() == 2
                    && relation.evidence[0].block == head_block
                    && relation.evidence[1].block == tail_block
            }),
            "{doc}: {head_frag} -> {tail_frag} must continue"
        );
    }
}

/// Unrelated complete citations never form a series, and the orphan tail of
/// doc-012 has no eligible head (fail-closed).
#[test]
fn unrelated_completed_citations_and_orphan_tail_have_no_series_edge() {
    let unrelated = vec![
        "Федеральный закон от 01.01.2020 N 1-ФЗ".to_string(),
        "Федеральный кодекс от 02.02.2021 N 2-ФЗ".to_string(),
        "Федеральный закон от 03.03.2022 N 3-ФЗ".to_string(),
    ];
    let linked = npa_link::build_linked_document(&unrelated);
    assert!(
        !linked
            .relations
            .iter()
            .any(|r| r.kind == LinkedRelationKind::ContinuesSeries),
        "complete citations must not continue: {:?}",
        linked.relations
    );

    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-012");
    let linked = npa_link::build_linked_document(&paras);
    assert!(
        !linked
            .relations
            .iter()
            .any(|r| r.kind == LinkedRelationKind::ContinuesSeries),
        "doc-012 frag-046 has no eligible head: {:?}",
        linked.relations
    );
    assert!(
        linked
            .diagnostics
            .contains(&LinkDiagnostic::OpenSeriesWithoutHead),
        "{:?}",
        linked.diagnostics
    );
}

/// Every pipeline series edge carries exactly two separate local anchors, each
/// valid in its own block.
#[test]
fn every_pipeline_series_edge_carries_two_valid_local_anchors() {
    let docs = read_fixture();
    for doc in docs.keys() {
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);
        for relation in linked
            .relations
            .iter()
            .filter(|r| r.kind == LinkedRelationKind::ContinuesSeries)
        {
            assert_eq!(relation.evidence.len(), 2, "{doc}: two local anchors");
            assert_ne!(
                relation.evidence[0].block, relation.evidence[1].block,
                "{doc}: a continuation is never one cross-block span"
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

/// Inline `Приказ` letterheads (doc-013..018) are recognized with source
/// requisites; court documents (doc-009/010/011/029/031) fail closed.
#[test]
fn frozen_letterhead_positives_and_court_negatives() {
    let docs = read_fixture();
    for doc in [
        "npa-doc-013",
        "npa-doc-014",
        "npa-doc-015",
        "npa-doc-016",
        "npa-doc-017",
        "npa-doc-018",
    ] {
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);
        let head = linked
            .letterhead
            .unwrap_or_else(|| panic!("{doc}: expected an inline letterhead"));
        assert!(head.kind.contains("Приказ"), "{doc}: kind={}", head.kind);
        assert!(!head.issuer.is_empty(), "{doc}: issuer must be captured");
        assert!(
            !head.date.is_empty() && !head.number.is_empty(),
            "{doc}: requisites must come from the source"
        );
        npa_anchor::check_span(&paras[head.evidence.block], head.evidence)
            .unwrap_or_else(|e| panic!("{doc}: invalid head evidence: {e:?}"));
    }

    for doc in [
        "npa-doc-009",
        "npa-doc-010",
        "npa-doc-011",
        "npa-doc-029",
        "npa-doc-031",
    ] {
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);
        assert!(
            linked.letterhead.is_none(),
            "{doc}: court documents must fail closed"
        );
    }
}

/// doc-013: the «Методические рекомендации» annex quotes the approving
/// Приказ and never absorbs its requisites (Work != approver, ADR-0016).
#[test]
fn frozen_doc013_annex_quotes_the_approver_and_does_not_merge_work() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-013");
    let linked = npa_link::build_linked_document(&paras);
    let annex = linked
        .members
        .iter()
        .find(|m| m.type_name == "Методические рекомендации" && m.approved_by.is_some())
        .unwrap_or_else(|| panic!("no linked annex in doc-013: {:?}", linked.members));
    assert_eq!(
        annex.approved_by.as_deref(),
        Some("Приказ Минэкономразвития России от 02.10.2013 N 567")
    );
    assert_eq!(annex.derivation, LinkDerivation::ApprovedByQuote);
    assert!(
        annex.date.is_empty() && annex.number.is_empty(),
        "the annex must not merge the approver's Work: {annex:?}"
    );
    assert!(
        linked
            .relations
            .iter()
            .any(|r| { r.from_id == annex.id && r.kind == LinkedRelationKind::ApprovedBy }),
        "missing ApprovedBy relation: {:?}",
        linked.relations
    );
}

/// doc-027 / doc-035 declarations resolve; the doc-032 party alias
/// `(далее - Заявитель)` never binds.
#[test]
fn frozen_alias_declarations_resolve_and_party_aliases_do_not() {
    let docs = read_fixture();

    let paras = load_doc(&docs, "npa-doc-027");
    assert!(
        !npa_link::collect_aliases(&paras).is_empty(),
        "doc-027 declarations must resolve"
    );
    let linked = npa_link::build_linked_document(&paras);
    assert!(
        linked
            .members
            .iter()
            .any(|m| { m.derivation == LinkDerivation::ScopedAlias && m.number == "44-ФЗ" }),
        "the «Закона N 44-ФЗ» short reference must resolve in the pipeline: {:?}",
        linked.members
    );

    let paras = load_doc(&docs, "npa-doc-035");
    assert!(
        npa_link::collect_aliases(&paras)
            .iter()
            .any(|b| b.alias.to_lowercase() == "протокол"),
        "doc-035 «(далее - Протокол)» must resolve"
    );

    let paras = load_doc(&docs, "npa-doc-032");
    let linked = npa_link::build_linked_document(&paras);
    for party in [
        "заявитель",
        "организатор",
        "оператор",
        "продажа",
        "конкурсный отбор",
    ] {
        assert!(
            !linked.members.iter().any(|m| {
                m.alias
                    .as_deref()
                    .map(|a| a.to_lowercase().contains(party))
                    .unwrap_or(false)
            }),
            "party alias {party} leaked into the pipeline"
        );
    }
}

/// doc-002/007/009/010 this-references stay requisites-free and report
/// `HeadUnavailable`; a foreign act is never borrowed (fail-closed).
#[test]
fn frozen_this_refs_never_borrow_foreign_requisites_in_the_pipeline() {
    let docs = read_fixture();
    for doc in ["npa-doc-002", "npa-doc-007", "npa-doc-009", "npa-doc-010"] {
        let paras = load_doc(&docs, doc);
        let linked = npa_link::build_linked_document(&paras);
        let refs: Vec<_> = linked
            .members
            .iter()
            .filter(|m| m.derivation == LinkDerivation::ThisDocumentRef)
            .collect();
        assert!(!refs.is_empty(), "{doc}: expected a this-ref member");
        for reference in refs {
            assert_eq!(reference.date, "—", "{doc}: leaked a date");
            assert_eq!(reference.number, "—", "{doc}: leaked a number");
        }
        assert!(
            linked
                .diagnostics
                .contains(&LinkDiagnostic::HeadUnavailable),
            "{doc}: {:?}",
            linked.diagnostics
        );
    }
}

/// The linked sources stay free of the external (de)serializer and of
/// filesystem / environment access (D602).
#[test]
fn linked_sources_stay_serde_fs_env_free() {
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
