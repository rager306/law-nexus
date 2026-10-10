//! M211 S04 T02: NPA form classification (axis A) contract and differential
//! consumer over the tracked Python reference fixture.
//!
//! The form plane is std-only and body-independent: frozen reference rows
//! carry an empty body and synthetic rows a single-line snippet, both ignored
//! here (the form does not depend on body). The Python fixture stores the
//! *layer-final* `graph` for every row, while this test compares only the
//! form-plane graph: for `unknown_kind` the final graph is re-decided by axes
//! B..H (overlay for ГОСТ/ТР/решение), so those rows are counted separately
//! and not treated as a form mismatch.

use std::collections::BTreeSet;
use std::path::PathBuf;

use ln_decode::npa_classify::{
    FormBucket, FormGraph, FormVerdict, classify_form, lemma_match, stem_kind,
};

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/npa-members/classification-parity-fixture.tsv")
}

/// Number of tab-separated columns in `m211-classification-parity-fixture/v1`.
const COLUMNS: usize = 10;

struct ReferenceRow {
    kind: String,
    doc: String,
    canon: String,
    body: String,
    lemma: String,
    bucket: String,
    verdict: String,
    graph: String,
}

fn read_reference() -> Vec<ReferenceRow> {
    let text = std::fs::read_to_string(fixture_path())
        .expect("MISSING SOURCE: classification parity fixture is mandatory");
    let mut rows = Vec::new();
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        assert_eq!(
            cols.len(),
            COLUMNS,
            "MISSING SOURCE: malformed fixture row with {} columns: {line:?}",
            cols.len()
        );
        rows.push(ReferenceRow {
            kind: cols[0].to_string(),
            doc: cols[1].to_string(),
            canon: cols[2].to_string(),
            body: cols[3].to_string(),
            lemma: cols[4].to_string(),
            bucket: cols[5].to_string(),
            verdict: cols[6].to_string(),
            graph: cols[7].to_string(),
        });
    }
    assert!(!rows.is_empty(), "MISSING SOURCE: fixture has no data rows");
    rows
}

fn assert_form(canon: &str, lemma: &str, bucket: &str, verdict: &str, graph: &str) {
    let form = classify_form(canon);
    assert_eq!(form.lemma, lemma, "lemma for {canon:?}");
    assert_eq!(form.bucket.as_str(), bucket, "bucket for {canon:?}");
    assert_eq!(form.verdict.as_str(), verdict, "verdict for {canon:?}");
    assert_eq!(form.graph.as_str(), graph, "graph for {canon:?}");
}

#[test]
fn type_missing_is_empty_and_refuses() {
    assert_form("", "", "", "type_missing", "refuse");
    // Whiteness-only canon is fail-closed too (Python would raise here; the
    // port stays total on the untrusted input boundary).
    assert_form("   ", "", "", "type_missing", "refuse");
    assert_form("\t\n", "", "", "type_missing", "refuse");
}

#[test]
fn homograph_tk_is_not_a_codex() {
    assert_form("ТК", "тк", "unknown", "unknown_kind", "refuse");
    assert_form("ТК РФ", "тк", "unknown", "unknown_kind", "refuse");
    assert_form("ВК", "тк", "unknown", "unknown_kind", "refuse");
    assert_form("ВК РФ", "тк", "unknown", "unknown_kind", "refuse");
    assert_eq!(stem_kind("ТК"), "тк");
    assert_eq!(stem_kind("ВК РФ"), "тк");
}

#[test]
fn unknown_kind_cases_refuse() {
    assert_form(
        "ГОСТ 1234-2020",
        "гост",
        "unknown",
        "unknown_kind",
        "refuse",
    );
    assert_form("ТР ТС 005/2011", "тр", "unknown", "unknown_kind", "refuse");
    assert_form(
        "Решение УФАС по Челябинской области",
        "решение",
        "unknown",
        "unknown_kind",
        "refuse",
    );
}

#[test]
fn skip_as_type_cases_refuse() {
    assert_form(
        "Извещение",
        "извещение",
        "skip_as_type",
        "not_an_act",
        "refuse",
    );
    assert_form("Лот", "лот", "skip_as_type", "not_an_act", "refuse");
    assert_form("Заявка", "заявка", "skip_as_type", "not_an_act", "refuse");
}

#[test]
fn instrument_cases_refuse() {
    for canon in [
        "доверенность",
        "Лицензия",
        "Лицензии",
        "протокол",
        "Протоколом",
        "жалоба",
        "Жалобу",
        "соглашение",
        "контракт",
        "Контракту",
    ] {
        let form = classify_form(canon);
        assert_eq!(form.bucket.as_str(), "instrument", "bucket for {canon:?}");
        assert_eq!(
            form.verdict.as_str(),
            "instrument_not_npa",
            "verdict for {canon:?}"
        );
        assert_eq!(form.graph.as_str(), "refuse", "graph for {canon:?}");
    }
    assert_form(
        "Жалобу",
        "жалобу",
        "instrument",
        "instrument_not_npa",
        "refuse",
    );
    assert_form(
        "Контракту",
        "контракт",
        "instrument",
        "instrument_not_npa",
        "refuse",
    );
    assert_form(
        "Протоколом",
        "протокол",
        "instrument",
        "instrument_not_npa",
        "refuse",
    );
}

#[test]
fn named_bucket_cases_hold() {
    assert_form("положение", "положение", "named", "named_annex", "hold");
    assert_form("Положением", "положением", "named", "named_annex", "hold");
    assert_form("Правил", "правил", "named", "named_annex", "hold");
    assert_form("Правилами", "правилами", "named", "named_annex", "hold");
}

#[test]
fn hardcoded_named_annex_branches_hold() {
    assert_form(
        "Конкурсная документация",
        "документация",
        "named",
        "named_annex",
        "hold",
    );
    assert_form(
        "Методические рекомендации",
        "рекомендации",
        "named",
        "named_annex",
        "hold",
    );
    assert_form(
        "Регламент торговой площадки",
        "регламент",
        "named",
        "named_annex",
        "hold",
    );
    assert_form(
        "Перечень объектов",
        "перечень",
        "named",
        "named_annex",
        "hold",
    );
    assert_form(
        "Порядок формирования",
        "порядок",
        "named",
        "named_annex",
        "hold",
    );
}

#[test]
fn dictionary_forms_are_undecided_with_family_bucket() {
    assert_form(
        "Федеральный закон",
        "закон",
        "federal",
        "form_in_dictionary",
        "undecided",
    );
    assert_form(
        "Закон РФ",
        "закон",
        "federal",
        "form_in_dictionary",
        "undecided",
    );
    assert_form(
        "Указ Президента РФ",
        "указ",
        "presidential",
        "form_in_dictionary",
        "undecided",
    );
    assert_form(
        "Постановление Правительства РФ",
        "постановление",
        "government",
        "form_in_dictionary",
        "undecided",
    );
    assert_form(
        "Приказ Минэкономразвития России",
        "приказ",
        "agency",
        "form_in_dictionary",
        "undecided",
    );
    assert_form(
        "КоАП РФ",
        "кодекс",
        "federal",
        "form_in_dictionary",
        "undecided",
    );
}

#[test]
fn lemma_match_is_exact_or_inflected_never_substring() {
    assert!(lemma_match("доверенность", "доверенность"));
    assert!(lemma_match("закона", "закон"));
    assert!(lemma_match("закон", "закона"));
    assert!(lemma_match("доверенностью", "доверенность"));
    assert!(
        !lemma_match("указ", "указание"),
        "указ must not match указание"
    );
    assert!(!lemma_match("приказ", "приказание"));
}

#[test]
fn stem_kind_normalizes_codex_and_alias() {
    assert_eq!(stem_kind("Гражданский кодекс"), "кодекс");
    assert_eq!(stem_kind("Трудовой кодекс"), "кодекс");
    assert_eq!(stem_kind("Уголовно-процессуальный кодекс"), "кодекс");
    assert_eq!(stem_kind("КоАП РФ"), "кодекс");
    assert_eq!(stem_kind("АПК"), "кодекс");
    assert_eq!(stem_kind("ГПК РФ"), "кодекс");
    assert_eq!(stem_kind("Федеральный закон"), "закон");
    assert_eq!(stem_kind("Постановление Правительства РФ"), "постановление");
    assert_eq!(stem_kind(""), "");
}

#[test]
fn enum_strings_are_stable() {
    assert_eq!(FormVerdict::TypeMissing.as_str(), "type_missing");
    assert_eq!(FormVerdict::UnknownKind.as_str(), "unknown_kind");
    assert_eq!(FormVerdict::NotAnAct.as_str(), "not_an_act");
    assert_eq!(FormVerdict::InstrumentNotNpa.as_str(), "instrument_not_npa");
    assert_eq!(FormVerdict::NamedAnnex.as_str(), "named_annex");
    assert_eq!(FormVerdict::FormInDictionary.as_str(), "form_in_dictionary");
    assert_eq!(FormBucket::SkipAsType.as_str(), "skip_as_type");
    assert_eq!(FormBucket::Instrument.as_str(), "instrument");
    assert_eq!(FormBucket::Named.as_str(), "named");
    assert_eq!(FormBucket::Identifying("agency").as_str(), "agency");
    assert_eq!(FormBucket::Unknown.as_str(), "unknown");
    assert_eq!(FormBucket::Empty.as_str(), "");
    assert_eq!(FormGraph::Refuse.as_str(), "refuse");
    assert_eq!(FormGraph::Hold.as_str(), "hold");
    assert_eq!(FormGraph::Undecided.as_str(), "undecided");
}

/// Python verdicts that are fully decided by the form plane.
const FORM_DECIDABLE: &[&str] = &[
    "type_missing",
    "unknown_kind",
    "not_an_act",
    "instrument_not_npa",
    "named_annex",
];

/// The form-plane graph implied by a verdict (Python `classify_type`).
fn form_graph_for(verdict: &str) -> &'static str {
    match verdict {
        "named_annex" => "hold",
        "form_in_dictionary" => "undecided",
        _ => "refuse",
    }
}

#[test]
fn fixture_form_plane_differential() {
    let rows = read_reference();

    let mut reference_keys: BTreeSet<(String, String, String)> = BTreeSet::new();
    let mut predicted_keys: BTreeSet<(String, String, String)> = BTreeSet::new();
    let mut reference_rows = 0usize;
    let mut matching = 0usize;
    let mut wrong = 0usize;
    let mut graph_compared = 0usize;
    let mut graph_deferred_to_layers = 0usize;

    for row in &rows {
        if !FORM_DECIDABLE.contains(&row.verdict.as_str()) {
            // `form_in_dictionary` is not decided by form; T03 checks it.
            continue;
        }
        reference_rows += 1;
        let key = (row.doc.clone(), row.canon.clone(), row.body.clone());
        reference_keys.insert(key.clone());

        let form = classify_form(&row.canon);
        predicted_keys.insert(key);

        let mut outcome_ok = form.lemma == row.lemma
            && form.bucket.as_str() == row.bucket
            && form.verdict.as_str() == row.verdict
            && form.graph.as_str() == form_graph_for(&row.verdict);

        if row.verdict == "unknown_kind" {
            // The frozen fixture stores the layer-final graph: axes B..H may
            // re-decide `unknown_kind` (ГОСТ/ТР/решение -> overlay). The form
            // plane owns only the hint, so this is not a mismatch here.
            graph_deferred_to_layers += 1;
        } else {
            graph_compared += 1;
            if form.graph.as_str() != row.graph {
                outcome_ok = false;
            }
        }

        if outcome_ok {
            matching += 1;
        } else {
            wrong += 1;
            eprintln!(
                "form mismatch: kind={} doc={} canon={:?} body={:?} \
                 rust=(lemma={:?},bucket={},verdict={},graph={}) \
                 ref=(lemma={:?},bucket={},verdict={},graph={})",
                row.kind,
                row.doc,
                row.canon,
                row.body,
                form.lemma,
                form.bucket.as_str(),
                form.verdict.as_str(),
                form.graph.as_str(),
                row.lemma,
                row.bucket,
                row.verdict,
                row.graph,
            );
        }
    }

    let missing = reference_keys.difference(&predicted_keys).count();
    let extra = predicted_keys.difference(&reference_keys).count();

    assert!(
        reference_rows >= 19,
        "expected at least 19 form-decidable reference rows, saw {reference_rows}"
    );
    assert_eq!(
        missing, 0,
        "missing reference rows (unmatched, not dropped)"
    );
    assert_eq!(extra, 0, "extra predictions absent from reference");
    assert_eq!(wrong, 0, "wrong form-plane rows");
    assert_eq!(matching, reference_rows);
    assert!(
        graph_compared > 0,
        "expected some verdicts where form owns the final graph"
    );
    assert!(
        graph_deferred_to_layers > 0,
        "expected layer-owned unknown_kind rows in the fixture"
    );
}
