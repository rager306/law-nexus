//! M211 S03 T02: letterhead recognizer contract.
//!
//! Hand-rolled fixture reader (D602): the frozen 40-doc seed is read from
//! `tests/fixtures/npa-members/typed-parity-fixture.tsv` (doc -> frag) and the
//! fragment texts from `tests/fixtures/npa-lawref/`. A missing source fails
//! closed instead of silently skipping.
//!
//! Covers: synthetic uppercase ministry / inline `Приказ` / ПП / распоряжение
//! / Указ / ФАС(U/FAS); court and unknown heads fail closed; fixture positive
//! inline `Приказ` heads (doc-013..018) and fixture court documents
//! (doc-009/010/011/029/031) -> None; every evidence span is a valid
//! source-local `LocalSpan`.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;
use ln_decode::npa_link::{self, LetterheadStatus};

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

/// Synthetic uppercase ministry head + standalone `ПРИКАЗ` + requisites.
#[test]
fn synthetic_uppercase_ministry_head_is_recognized_from_the_table() {
    let paras = vec![
        "МИНИСТЕРСТВО ВНУТРЕННИХ ДЕЛ РОССИЙСКОЙ ФЕДЕРАЦИИ".to_string(),
        "ПРИКАЗ".to_string(),
        "от 12.03.2020 N 123".to_string(),
    ];
    let letterhead = npa_link::recognize_letterhead(&paras).expect("ministry letterhead");
    assert_eq!(letterhead.status, LetterheadStatus::Recognized);
    assert_eq!(letterhead.kind, "Приказ МВД России");
    assert_eq!(letterhead.issuer, "МВД России");
    assert_eq!(letterhead.date, "12.03.2020");
    assert_eq!(letterhead.number, "123");
    assert_eq!(letterhead.head_type(), "Приказ МВД России");
    npa_anchor::check_span(&paras[letterhead.evidence.block], letterhead.evidence)
        .expect("evidence must be a valid local span");
}

/// The data table covers several agencies, not only the special-cased ones.
#[test]
fn issuer_table_covers_multiple_ministries() {
    let cases: &[(&str, &str)] = &[
        (
            "МИНИСТЕРСТВО ЮСТИЦИИ РОССИЙСКОЙ ФЕДЕРАЦИИ",
            "Минюста России",
        ),
        ("ФЕДЕРАЛЬНАЯ АНТИМОНОПОЛЬНАЯ СЛУЖБА", "ФАС России"),
        ("ФЕДЕРАЛЬНОЕ КАЗНАЧЕЙСТВО", "Федерального казначейства"),
        (
            "ФЕДЕРАЛЬНАЯ ПРОБИРНАЯ ПАЛАТА",
            "Федеральной пробирной палаты",
        ),
    ];
    for (head, expected_issuer) in cases {
        let paras = vec![
            head.to_string(),
            "ПРИКАЗ".to_string(),
            "от 01.02.2021 N 7".to_string(),
        ];
        let letterhead =
            npa_link::recognize_letterhead(&paras).unwrap_or_else(|| panic!("{head}: letterhead"));
        assert_eq!(letterhead.issuer, *expected_issuer, "{head}");
        assert_eq!(
            letterhead.kind,
            format!("Приказ {expected_issuer}"),
            "{head}"
        );
        assert_eq!(letterhead.date, "01.02.2021", "{head}");
        assert_eq!(letterhead.number, "7", "{head}");
    }
}

/// Inline `Приказ <issuer> от DD.MM.YYYY N …`: the issuer phrase is captured
/// after the keyword (including agencies absent from the table).
#[test]
fn synthetic_inline_prikaz_captures_the_issuer_phrase() {
    let paras = vec![
        "Приказ Минэкономразвития России от 02.10.2013 N 567\"Об утверждении Методических рекомендаций\"".to_string(),
    ];
    let letterhead = npa_link::recognize_letterhead(&paras).expect("inline prikaz");
    assert_eq!(letterhead.kind, "Приказ Минэкономразвития России");
    assert_eq!(letterhead.issuer, "Минэкономразвития России");
    assert_eq!(letterhead.date, "02.10.2013");
    assert_eq!(letterhead.number, "567");
}

/// Government / presidential act kinds.
#[test]
fn synthetic_government_and_president_acts_are_recognized() {
    let pp = vec![
        "ПОСТАНОВЛЕНИЕ ПРАВИТЕЛЬСТВА РОССИЙСКОЙ ФЕДЕРАЦИИ".to_string(),
        "от 01.12.2020 N 1234".to_string(),
    ];
    let letterhead = npa_link::recognize_letterhead(&pp).expect("postanovlenie");
    assert_eq!(letterhead.kind, "Постановление Правительства РФ");
    assert_eq!(letterhead.issuer, "Правительство РФ");
    assert_eq!(letterhead.date, "01.12.2020");
    assert_eq!(letterhead.number, "1234");

    let rasporyazhenie = vec![
        "РАСПОРЯЖЕНИЕ ПРАВИТЕЛЬСТВА РОССИЙСКОЙ ФЕДЕРАЦИИ".to_string(),
        "от 02.02.2021 N 55-р".to_string(),
    ];
    let letterhead = npa_link::recognize_letterhead(&rasporyazhenie).expect("rasporyazhenie");
    assert_eq!(letterhead.kind, "распоряжение Правительства РФ");
    assert_eq!(letterhead.number, "55-р");

    let ukaz = vec![
        "УКАЗ ПРЕЗИДЕНТА РОССИЙСКОЙ ФЕДЕРАЦИИ".to_string(),
        "от 03.03.2022 N 100".to_string(),
    ];
    let letterhead = npa_link::recognize_letterhead(&ukaz).expect("ukaz");
    assert_eq!(letterhead.kind, "Указ Президента РФ");
    assert_eq!(letterhead.issuer, "Президент РФ");
    assert_eq!(letterhead.number, "100");
}

/// Antitrust decision letterhead: the case number comes from `по делу N`.
#[test]
fn synthetic_fas_decision_uses_the_case_number() {
    let paras = vec![
        "ФЕДЕРАЛЬНАЯ АНТИМОНОПОЛЬНАЯ СЛУЖБА".to_string(),
        "РЕШЕНИЕ".to_string(),
        "по делу N А40-12345/2020".to_string(),
    ];
    let letterhead = npa_link::recognize_letterhead(&paras).expect("fas decision");
    assert_eq!(letterhead.kind, "Решение ФАС России");
    assert_eq!(letterhead.issuer, "ФАС России");
    assert_eq!(letterhead.date, "—");
    assert_eq!(letterhead.number, "А40-12345/2020");
    npa_anchor::check_span(&paras[letterhead.evidence.block], letterhead.evidence)
        .expect("case-number evidence must be a valid local span");
}

/// A regional antitrust directorate is recognized as УФАС.
#[test]
fn synthetic_ufas_decision_uses_the_ufas_issuer() {
    let paras = vec![
        "УПРАВЛЕНИЕ ФЕДЕРАЛЬНОЙ АНТИМОНОПОЛЬНОЙ СЛУЖБЫ ПО МОСКОВСКОЙ ОБЛАСТИ".to_string(),
        "ПРЕДПИСАНИЕ".to_string(),
        "по делу N 12/2021".to_string(),
    ];
    let letterhead = npa_link::recognize_letterhead(&paras).expect("ufas decision");
    assert_eq!(letterhead.kind, "Предписание УФАС России");
    assert_eq!(letterhead.issuer, "УФАС России");
    assert_eq!(letterhead.number, "12/2021");
}

/// Court letterheads are refused outright (ADR-0029 §5 fail-closed).
#[test]
fn court_letterheads_are_fail_closed() {
    let heads = [
        vec![
            "ВЕРХОВНЫЙ СУД РОССИЙСКОЙ ФЕДЕРАЦИИ",
            "РЕШЕНИЕ",
            "от 01.01.2020 N 1",
        ],
        vec![
            "АРБИТРАЖНЫЙ СУД МОСКОВСКОЙ ОБЛАСТИ",
            "РЕШЕНИЕ",
            "от 02.02.2020 N 2",
        ],
        vec!["МИРОВОЙ СУДЬЯ СУДЕБНОГО УЧАСТКА N 1", "от 03.03.2020 N 3"],
    ];
    for head in heads {
        let paras: Vec<String> = head.iter().map(|s| s.to_string()).collect();
        assert_eq!(
            npa_link::recognize_letterhead(&paras),
            None,
            "{head:?} must fail closed"
        );
    }
}

/// A head with no recognized kind is refused, even when it carries an anchor.
#[test]
fn unknown_head_is_fail_closed() {
    let without_anchor = vec![
        "1. Общие положения".to_string(),
        "Настоящие Правила определяют порядок применения.".to_string(),
    ];
    assert_eq!(npa_link::recognize_letterhead(&without_anchor), None);

    let with_anchor = vec![
        "ДОГОВОР О ПРИСОЕДИНЕНИИ".to_string(),
        "от 01.01.2020 N 1".to_string(),
    ];
    assert_eq!(npa_link::recognize_letterhead(&with_anchor), None);
}

/// Frozen-seed inline `Приказ` heads: kind / issuer / date / number.
#[test]
fn fixture_inline_prikaz_positives_are_recognized() {
    let docs = read_fixture();
    let cases: &[(&str, &str, &str, &str, &str)] = &[
        (
            "npa-doc-013",
            "Приказ Минэкономразвития России",
            "Минэкономразвития России",
            "02.10.2013",
            "567",
        ),
        (
            "npa-doc-014",
            "Приказ ФАНО России",
            "ФАНО России",
            "09.01.2014",
            "1",
        ),
        (
            "npa-doc-015",
            "Приказ Росгидромета",
            "Росгидромета",
            "14.02.2014",
            "55",
        ),
        (
            "npa-doc-016",
            "Приказ Роструда",
            "Роструда",
            "06.03.2014",
            "80",
        ),
        (
            "npa-doc-017",
            "Приказ Минэкономразвития России",
            "Минэкономразвития России",
            "26.03.2014",
            "161",
        ),
        (
            "npa-doc-018",
            "Приказ Минобрнауки России",
            "Минобрнауки России",
            "23.04.2014",
            "398",
        ),
    ];
    for (doc, kind, issuer, date, number) in cases {
        let paras = load_doc(&docs, doc);
        let letterhead = npa_link::recognize_letterhead(&paras)
            .unwrap_or_else(|| panic!("{doc}: inline prikaz letterhead expected"));
        assert_eq!(letterhead.kind, *kind, "{doc}");
        assert_eq!(letterhead.issuer, *issuer, "{doc}");
        assert_eq!(letterhead.date, *date, "{doc}");
        assert_eq!(letterhead.number, *number, "{doc}");
        npa_anchor::check_span(&paras[letterhead.evidence.block], letterhead.evidence)
            .unwrap_or_else(|e| panic!("{doc}: invalid evidence {e:?}"));
    }
}

/// Frozen-seed court documents are refused outright.
#[test]
fn fixture_court_documents_are_fail_closed() {
    let docs = read_fixture();
    for doc in [
        "npa-doc-009",
        "npa-doc-010",
        "npa-doc-011",
        "npa-doc-029",
        "npa-doc-031",
    ] {
        let paras = load_doc(&docs, doc);
        assert_eq!(
            npa_link::recognize_letterhead(&paras),
            None,
            "{doc}: court document must fail closed"
        );
    }
}

/// ADR-0029 §5 priority: a body kind mention outside the head zone never
/// overrides the letterhead kind.
#[test]
fn letterhead_outranks_body_kind_mentions() {
    let paras = vec![
        "МИНИСТЕРСТВО ВНУТРЕННИХ ДЕЛ РОССИЙСКОЙ ФЕДЕРАЦИИ".to_string(),
        "ПРИКАЗ".to_string(),
        "от 12.03.2020 N 123".to_string(),
        "Текст цитирует Постановление Правительства РФ от 01.01.2019 N 9".to_string(),
    ];
    let letterhead = npa_link::recognize_letterhead(&paras).expect("ministry letterhead");
    assert_eq!(letterhead.head_type(), "Приказ МВД России");
    assert!(
        !letterhead.kind.contains("Постановление"),
        "body mention leaked into the head kind: {}",
        letterhead.kind
    );
}

/// The letterhead test must not weaken the frozen-fixture contract: the same
/// source files used by `npa_link_series_contract` remain unmodified.
#[test]
fn fixture_sources_are_not_mutated_by_recognition() {
    let docs = read_fixture();
    let paras = load_doc(&docs, "npa-doc-013");
    let before = paras.clone();
    let _ = npa_link::recognize_letterhead(&paras);
    assert_eq!(paras, before, "recognizer must not mutate its input");
}
