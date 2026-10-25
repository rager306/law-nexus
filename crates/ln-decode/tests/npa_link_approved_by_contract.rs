//! M211 S03 T03: approved_by linking + head-family carry contract.
//!
//! Hand-rolled fixture reader (D602): the frozen 40-doc seed is read from
//! `tests/fixtures/npa-members/typed-parity-fixture.tsv` (doc -> frag) and the
//! fragment texts from `tests/fixtures/npa-lawref/`. A missing source fails
//! closed instead of silently skipping.
//!
//! Covers: named annex -> approving act on three frozen fragments
//! (doc-013/frag-051 «Методические рекомендации»; doc-030/frag-135 «Правила,
//! утв. Постановлением … N 1416»; doc-030/frag-132 «Правила … утвержденных
//! Постановлением … N 145»); the Work != approver invariant; the synthetic
//! «вместе с …» list fallback; a synthetic corporate regulation refused without
//! a normative citation; the narrow context-carry cliché; the lowercase-annex
//! gate; determinism / immutability; and serde/fs/env-free sources.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;
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
                if let Some(cur) = current.as_deref()
                    && let Some(frags) = docs.get_mut(cur)
                {
                    frags.push(cols[1].to_string());
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

/// doc-013/frag-051: the approving Приказ precedes its «Методические
/// рекомендации» annex inside the same paragraph. The annex has no requisites
/// of its own and quotes the approver.
#[test]
fn frozen_doc013_annex_quotes_the_approving_prikaz() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-013");
    let (annexes, relations, _) = npa_link::link_approved_by(&paras);
    let annex = annexes
        .iter()
        .find(|m| m.type_name == "Методические рекомендации" && m.approved_by.is_some())
        .unwrap_or_else(|| panic!("no linked annex in doc-013: {annexes:?}"));
    assert_eq!(
        annex.approved_by.as_deref(),
        Some("Приказ Минэкономразвития России от 02.10.2013 N 567")
    );
    assert_eq!(annex.derivation, LinkDerivation::ApprovedByQuote);
    assert!(
        relations
            .iter()
            .any(|r| r.from_id == annex.id && r.kind == LinkedRelationKind::ApprovedBy),
        "the annex must carry an ApprovedBy relation: {relations:?}"
    );
}

/// doc-030/frag-135: «Правила …, утвержденных Постановлением … N 1416».
#[test]
fn frozen_doc030_medical_rules_quote_the_postanovlenie() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-030");
    let (annexes, relations, _) = npa_link::link_approved_by(&paras);
    let annex = annexes
        .iter()
        .find(|m| {
            m.type_name == "Правила"
                && m.approved_by.as_deref()
                    == Some("Постановление Правительства РФ от 27.12.2012 N 1416")
        })
        .unwrap_or_else(|| panic!("no linked Правила annex for N 1416: {annexes:?}"));
    assert!(
        relations
            .iter()
            .any(|r| r.from_id == annex.id && r.kind == LinkedRelationKind::ApprovedBy),
        "{relations:?}"
    );
}

/// doc-030/frag-132: «Правил …, утвержденных Постановлением Правительства РФ
/// от 08.02.2017 N 145».
#[test]
fn frozen_doc030_catalog_rules_quote_the_postanovlenie() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-030");
    let (annexes, _, _) = npa_link::link_approved_by(&paras);
    assert!(
        annexes.iter().any(|m| {
            m.type_name == "Правила"
                && m.approved_by.as_deref()
                    == Some("Постановление Правительства РФ от 08.02.2017 N 145")
        }),
        "no linked Правила annex for N 145: {annexes:?}"
    );
}

/// ADR-0016: a named annex never absorbs the approving act's Work. Its
/// `date`/`number` stay empty and the citation is composed from the related
/// typed approver.
#[test]
fn named_annex_work_is_never_merged_with_the_approver() {
    let docs = read_fixture();
    for doc in ["npa-doc-013", "npa-doc-030"] {
        let paras = load_doc(&docs, doc);
        let members = npa_link::anchored_members(&paras);
        let (annexes, relations, _) = npa_link::link_approved_by(&paras);
        for annex in annexes
            .iter()
            .filter(|m| m.derivation == LinkDerivation::ApprovedByQuote)
        {
            assert!(
                annex.date.is_empty() && annex.number.is_empty(),
                "{doc}: annex stole the approver's requisites: {annex:?}"
            );
            let relation = relations
                .iter()
                .find(|r| r.from_id == annex.id && r.kind == LinkedRelationKind::ApprovedBy)
                .unwrap_or_else(|| panic!("{doc}: no ApprovedBy relation for {annex:?}"));
            let approver = &members[relation.to_id];
            let citation = format!(
                "{} от {} N {}",
                approver.type_name, approver.date, approver.number
            );
            assert_eq!(
                annex.approved_by.as_deref(),
                Some(citation.as_str()),
                "{doc}: citation must come from the related approver"
            );
            assert_ne!(
                annex.type_name, approver.type_name,
                "{doc}: annex Work must differ from the approving Work"
            );
        }
    }
}

/// The «вместе с …» list fallback: the annex sits after the first `вместе с`
/// token and more than 700 characters after the last act, so only the list
/// fallback can bind it.
#[test]
fn together_with_list_binds_annexes_to_the_last_act_before_it() {
    let filler = "нейтральный текст описания без дат и номеров. ".repeat(30);
    let paras = vec![format!(
        "Постановление Правительства РФ от 01.01.2020 N 1 {filler} (вместе с \"Правилами оценки заявок\", \"Требованиями к заявке\")"
    )];
    let (annexes, relations, _) = npa_link::link_approved_by(&paras);
    let linked: Vec<_> = annexes
        .iter()
        .filter(|m| {
            m.approved_by.as_deref() == Some("Постановление Правительства РФ от 01.01.2020 N 1")
        })
        .collect();
    assert!(
        !linked.is_empty(),
        "«вместе с …» list must bind an annex: {annexes:?}"
    );
    assert!(
        relations
            .iter()
            .any(|r| r.kind == LinkedRelationKind::ApprovedBy
                && linked.iter().any(|m| m.id == r.from_id)),
        "{relations:?}"
    );
}

/// A corporate regulation is refused: the corporate body is recorded, but no
/// normative citation and no relation are minted (`do_not_project`).
#[test]
fn corporate_regulation_is_refused_without_a_normative_citation() {
    let paras = vec![
        "Регламент работы электронной площадки".to_string(),
        "утвержден генеральным директором ООО \"РТС-тендер\" 01.01.2020".to_string(),
    ];
    let (annexes, relations, diagnostics) = npa_link::link_approved_by(&paras);
    assert!(
        diagnostics.contains(&LinkDiagnostic::HeadFamilyCarryRefused),
        "{diagnostics:?}"
    );
    let regulation = annexes
        .iter()
        .find(|m| m.type_name == "Регламент")
        .unwrap_or_else(|| panic!("regulation annex: {annexes:?}"));
    assert_eq!(regulation.derivation, LinkDerivation::Refused);
    let citation = regulation
        .approved_by
        .as_deref()
        .expect("corporate approver");
    assert!(citation.contains("генеральный директор"), "{citation}");
    assert!(
        !citation.contains("Постановление")
            && !citation.contains("Приказ")
            && !citation.contains("Правительства"),
        "no normative citation may be fabricated: {citation}"
    );
    assert!(
        !relations.iter().any(|r| r.from_id == regulation.id),
        "a refused annex must mint no relation: {relations:?}"
    );
}

/// The narrow context-carry cliché assigns the head family; outside it there is
/// no carry (proximity is never evidence).
#[test]
fn context_carry_assigns_the_head_family_only_inside_the_cliche() {
    let paras = vec![
        "В соответствии с правовой позицией Конституционного Суда Российской Федерации, изложенной в Постановлении от 23.12.2019 N 44-П, суды должны учитывать".to_string(),
    ];
    let carries = npa_link::carry_head_family(&paras);
    assert_eq!(carries.len(), 1, "{carries:?}");
    assert_eq!(carries[0].family, "Постановление КС РФ");
    assert_eq!(carries[0].date, "23.12.2019");
    assert_eq!(carries[0].number, "44-П");
    assert_eq!(carries[0].evidence.len(), 2, "two local anchors");
    for span in &carries[0].evidence {
        npa_anchor::check_span(&paras[span.block], *span).expect("valid evidence span");
    }

    let plain = vec!["Постановление Правительства РФ от 01.01.2020 N 1".to_string()];
    assert!(
        npa_link::carry_head_family(&plain).is_empty(),
        "outside the cliché there is no head-family carry"
    );
}

/// ADR-0029 §5: an uncited lowercase annex mention is not a named annex; a
/// cited one is admitted.
#[test]
fn uncited_lowercase_annex_is_dropped_but_a_cited_one_is_admitted() {
    let uncited = vec!["положением о закупках акционерного общества установлено".to_string()];
    let (annexes, _, _) = npa_link::link_approved_by(&uncited);
    assert!(
        !annexes.iter().any(|m| m.type_name == "Положение"),
        "uncited lowercase mention must be dropped: {annexes:?}"
    );

    let cited = vec![
        "положением о закупках, утвержденным Постановлением Правительства РФ от 01.01.2020 N 1"
            .to_string(),
    ];
    let (annexes, relations, _) = npa_link::link_approved_by(&cited);
    let annex = annexes
        .iter()
        .find(|m| m.type_name == "Положение")
        .unwrap_or_else(|| panic!("cited lowercase annex must be admitted: {annexes:?}"));
    assert_eq!(
        annex.approved_by.as_deref(),
        Some("Постановление Правительства РФ от 01.01.2020 N 1")
    );
    assert!(
        relations
            .iter()
            .any(|r| r.from_id == annex.id && r.kind == LinkedRelationKind::ApprovedBy),
        "{relations:?}"
    );
}

/// Every ApprovedBy relation carries two valid source-local anchors.
#[test]
fn every_approved_by_relation_carries_valid_local_anchors() {
    let docs = read_fixture();
    for doc in ["npa-doc-013", "npa-doc-030"] {
        let paras = load_doc(&docs, doc);
        let (_, relations, _) = npa_link::link_approved_by(&paras);
        for relation in &relations {
            assert_eq!(relation.evidence.len(), 2, "{doc}: two local anchors");
            for span in &relation.evidence {
                let source = paras
                    .get(span.block)
                    .unwrap_or_else(|| panic!("{doc}: evidence block out of range"));
                npa_anchor::check_span(source, *span)
                    .unwrap_or_else(|e| panic!("{doc}: invalid anchor {span:?}: {e:?}"));
            }
        }
    }
}

/// Deterministic replay and input immutability (`TypedMember` never mutated).
#[test]
fn approved_by_linking_is_deterministic_and_leaves_input_untouched() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-030");
    let before = paras.clone();
    let first = npa_link::link_approved_by(&paras);
    let second = npa_link::link_approved_by(&paras);
    assert_eq!(first, second, "replay must be stable");
    assert_eq!(paras, before, "linking must not mutate its input");
}

/// The linked module stays free of the external (de)serializer and of
/// filesystem / environment access (D602).
#[test]
fn linked_module_stays_serde_fs_env_free() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/npa_link.rs");
    let source = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read npa_link.rs: {e}"));
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
            "npa_link.rs must stay serde/fs/env-free (D602): found {forbidden}"
        );
    }
}
