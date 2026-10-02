//! M211 S01/S02: паритет типизированных членов (дата, номер, TYPE) с
//! Python-прототипом. Фикстура TSV [bounded], reader hand-rolled (D602).
//!
//! Fixtures обязательные — отсутствие seed-фрагмента даёт провал
//! `MISSING SOURCE`, а не молчаливый skip.
//!
//! T02: `scan_typed` сведён на единый поток якорей S01
//! (`npa_anchor::scan_anchors_diagnosed`) с общими guards и локальными
//! byte spans; occurrences не сливаются по `(date, number)`.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;
use ln_decode::npa_typed;

struct DocFixture {
    fragments: Vec<String>,
    typed: Vec<(String, String, String)>,
}

fn read_typed_fixture(path: &PathBuf) -> BTreeMap<String, DocFixture> {
    let text = std::fs::read_to_string(path).expect("typed fixture must exist");
    let mut docs: BTreeMap<String, DocFixture> = BTreeMap::new();
    let mut current: Option<String> = None;
    for line in text.lines() {
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let cols: Vec<&str> = line.split('\t').collect();
        match cols[0] {
            "doc" => {
                current = Some(cols[1].to_string());
                docs.entry(cols[1].to_string()).or_insert(DocFixture {
                    fragments: Vec::new(),
                    typed: Vec::new(),
                });
            }
            "frag" if cols.len() >= 2 => {
                if let Some(cur) = current.as_deref() {
                    if let Some(d) = docs.get_mut(cur) {
                        d.fragments.push(cols[1].to_string());
                    }
                }
            }
            "typed" if cols.len() >= 4 => {
                if let Some(cur) = current.as_deref() {
                    if let Some(d) = docs.get_mut(cur) {
                        d.typed.push((
                            cols[1].to_string(),
                            cols[2].to_string(),
                            cols[3].to_string(),
                        ));
                    }
                }
            }
            _ => {}
        }
    }
    docs
}

fn fixture_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("crates/ln-decode/tests/fixtures/npa-lawref")
}

#[test]
fn gold_typed_parity_40_docs() {
    let docs = read_typed_fixture(
        &PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("tests/fixtures/npa-members/typed-parity-fixture.tsv"),
    );
    assert!(
        !docs.is_empty(),
        "MISSING SOURCE: typed parity fixture is mandatory and must be non-empty"
    );
    let mut mismatches: Vec<String> = Vec::new();
    let mut missing_sources: Vec<String> = Vec::new();
    let mut checked = 0usize;
    let mut got_total = 0usize;
    let mut want_total = 0usize;
    let mut type_match = 0usize;

    for (doc, fixture) in &docs {
        assert!(
            !fixture.fragments.is_empty(),
            "MISSING SOURCE: {doc} has an empty fragment list"
        );
        let mut paras: Vec<String> = Vec::new();
        let mut doc_missing: Vec<String> = Vec::new();
        for fname in &fixture.fragments {
            match std::fs::read_to_string(fixture_dir().join(fname)) {
                Ok(text) => paras.push(text),
                Err(e) => doc_missing.push(format!("{doc}: {fname}: {e}")),
            }
        }
        if !doc_missing.is_empty() {
            // Обязательные fixtures fail closed: missing source — провал, не skip.
            missing_sources.extend(doc_missing);
            continue;
        }

        let got = npa_typed::scan_typed(&paras);
        got_total += got.len();
        want_total += fixture.typed.len();
        checked += 1;

        let want_set: std::collections::BTreeMap<(String, String), String> = fixture
            .typed
            .iter()
            .map(|(d, n, t)| ((d.clone(), n.clone()), t.clone()))
            .collect();
        // Occurrences не сливаются: агрегируем по ключу, предпочитая первый
        // непустой TYPE (стабильная семантика dedup, D518 / M207).
        let mut got_set: std::collections::BTreeMap<(String, String), String> =
            std::collections::BTreeMap::new();
        for t in got.iter().filter(|t| !t.type_name.is_empty()) {
            got_set
                .entry((t.date.clone(), t.number.clone()))
                .or_insert_with(|| t.type_name.clone());
        }

        let mut doc_miss: Vec<String> = Vec::new();
        for (k, want_type) in &want_set {
            match got_set.get(k) {
                Some(got_type) if got_type == want_type => {
                    type_match += 1;
                }
                Some(got_type) => {
                    doc_miss.push(format!(
                        "  type_drift {k:?}: want={want_type:?} got={got_type:?}"
                    ));
                }
                None => {
                    doc_miss.push(format!("  missing {k:?} (want={want_type:?})"));
                }
            }
        }
        for (k, got_type) in &got_set {
            if !want_set.contains_key(k) {
                doc_miss.push(format!("  extra {k:?} (got={got_type:?})"));
            }
        }
        if !doc_miss.is_empty() {
            mismatches.push(format!("{doc}: {} diffs", doc_miss.len()));
            mismatches.extend(doc_miss);
        }
    }

    eprintln!(
        "typed parity: checked={checked} missing={} got_total={got_total} want_total={want_total} type_match={type_match}",
        missing_sources.len()
    );

    assert!(
        missing_sources.is_empty(),
        "MISSING SOURCE (mandatory fixtures fail closed; no silent skip):\n{}",
        missing_sources.join("\n")
    );

    // S02 — строгий гейт: typed-parity обязан быть нулевым. Дифференциальный
    // эталон — scripts/m207_context_graph_demo.py (D519), не независимый gold.
    assert_eq!(checked, 40, "gold corpus must contain 40 docs");
    assert_eq!(
        want_total, 112,
        "gold corpus must carry 112 typed want-members"
    );
    assert!(
        mismatches.is_empty(),
        "typed parity residuals must be empty (strict gate; {} diffs):\n{}",
        mismatches.len(),
        mismatches.join("\n")
    );
    assert_eq!(
        type_match, want_total,
        "every want-member must have a matching TYPE ({type_match}/{want_total})"
    );
    eprintln!("S02 typed parity strict: {type_match}/{want_total} — zero residual diffs");
}

// ---------------------------------------------------------------------------
// T01: поимённые named-тесты по каждой первопричине residual diffs.
// ---------------------------------------------------------------------------

fn fragment(name: &str) -> String {
    let path = fixture_dir().join(name);
    std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("MISSING SOURCE: {}: {e}", path.display()))
}

fn member<'a>(
    members: &'a [npa_typed::TypedMember],
    date: &str,
    number: &str,
) -> &'a npa_typed::TypedMember {
    members
        .iter()
        .find(|m| m.date == date && m.number == number)
        .unwrap_or_else(|| panic!("member ({date}, {number}) not found: {members:?}"))
}

/// doc-031: «дополнительного соглашения к контракту от 23.03.2023 N 2/4/5»:
/// char-инкремент перескакивал через «контракт» после «соглашени», победитель
/// выбирал более ранний `соглашение`. Эталон — контракт.
#[test]
fn doc031_contract_after_agreement_wins() {
    for (frag, number) in [
        ("npa-frag-136.txt", "2"),
        ("npa-frag-137.txt", "4"),
        ("npa-frag-138.txt", "5"),
    ] {
        let para = fragment(frag);
        let members = npa_typed::scan_typed(std::slice::from_ref(&para));
        let m = member(&members, "23.03.2023", number);
        assert_eq!(m.type_name, "контракт", "{frag} (N {number})");
    }
}

/// char-инкремент не перескакивает «контракт» и не порождает extras: скан
/// frag-136 даёт ровно два кандидата — соглашение, затем контракт.
#[test]
fn doc031_char_scan_reaches_contract_without_false_extras() {
    let para = fragment("npa-frag-136.txt");
    let chars: Vec<char> = para.chars().collect();
    let cands = npa_typed::scan_types(&chars);
    let canons: Vec<&str> = cands.iter().map(|c| c.canon.as_str()).collect();
    assert_eq!(
        canons,
        vec!["соглашение", "контракт"],
        "char-increment must reach «контракт» with no extras: {canons:?}"
    );
    assert!(
        cands[1].start > cands[0].start,
        "контракт candidate must follow соглашение: {cands:?}"
    );
}

/// doc-007: аббревиатура «Постановление КС РФ от 21.07.2022 N 34-П».
#[test]
fn doc007_constitutional_court_abbreviation() {
    let para = fragment("npa-frag-027.txt");
    let members = npa_typed::scan_typed(std::slice::from_ref(&para));
    assert_eq!(
        member(&members, "21.07.2022", "34-П").type_name,
        "Постановление КС РФ"
    );
}

/// doc-029: вынесенный эмитент «Конституционным Судом РФ в Постановлении
/// от 17.02.2022 N 7-П».
#[test]
fn doc029_constitutional_court_carried_emitter() {
    let para = fragment("npa-frag-129.txt");
    let members = npa_typed::scan_typed(std::slice::from_ref(&para));
    assert_eq!(
        member(&members, "17.02.2022", "7-П").type_name,
        "Постановление КС РФ"
    );
}

/// doc-027: стем «лицензи…» («действующей лицензии … от 24.02.2021 N 0001976»).
#[test]
fn doc027_license_stem() {
    let para = fragment("npa-frag-120.txt");
    let members = npa_typed::scan_typed(std::slice::from_ref(&para));
    assert_eq!(
        member(&members, "24.02.2021", "0001976").type_name,
        "лицензия"
    );
}

/// doc-032/033: generic «распоряжен… <issuer>» → «Распоряжение <issuer>»;
/// чужое «постановление Правительства» — самостоятельный член другого TYPE.
#[test]
fn doc032_generic_rasporyazhenie_with_issuer() {
    for frag in ["npa-frag-143.txt", "npa-frag-147.txt"] {
        let para = fragment(frag);
        let members = npa_typed::scan_typed(std::slice::from_ref(&para));
        assert_eq!(
            member(&members, "15.08.2024", "74-480-р").type_name,
            "Распоряжение МТУ Росимущества в Челябинской и Курганской областях",
            "{frag}: generic распоряжение must win over earlier ПП РФ"
        );
        assert_eq!(
            member(&members, "27.08.2012", "860").type_name,
            "Постановление Правительства РФ",
            "{frag}: чужое Правительство сохраняет свой TYPE"
        );
    }
}

/// Demo-инвариант: чужое «постановление Правительства» ПОСЛЕ реквизита не
/// меняет TYPE распоряжения (локализованная ветка Правительства, не
/// block-wide forward search).
#[test]
fn foreign_government_after_requisites_does_not_change_type() {
    let para = "распоряжением МТУ Росимущества в Челябинской и Курганской областях \
                от 15.08.2024 N 74-480-р, а также постановлением Правительства РФ \
                от 27.08.2012 N 860."
        .to_string();
    let members = npa_typed::scan_typed(std::slice::from_ref(&para));
    assert_eq!(
        member(&members, "15.08.2024", "74-480-р").type_name,
        "Распоряжение МТУ Росимущества в Челябинской и Курганской областях"
    );
    assert_eq!(
        member(&members, "27.08.2012", "860").type_name,
        "Постановление Правительства РФ"
    );
}

/// Единый producer: typed pipeline применяет те же guards, что S01, и несёт
/// диагностики отвергнутых якорей (INBOUND), а не свой scanner дат.
#[test]
fn typed_consumes_canonical_anchors_with_guards() {
    let paras = vec![
        "Федеральный закон от 02.07.2021 N 337-ФЗ".to_string(),
        "(вх. N 1456 от 12.03.2019 N 999)".to_string(),
        "Зарегистрировано в Минюсте России 05.03.2019 N 12".to_string(),
    ];
    let (members, diagnostics) = npa_typed::scan_typed_diagnosed(&paras);

    // Единственный принятый якорь — вне guarded-зон (S01 и typed совпадают).
    assert_eq!(
        members.len(),
        1,
        "guards must filter typed pipeline: {members:?}"
    );
    assert_eq!(members[0].date, "02.07.2021");
    assert_eq!(members[0].number, "337-ФЗ");
    assert_eq!(members[0].type_name, "Федеральный закон");
    assert_eq!(members[0].span.block, 0);

    // Отвергнутый INBOUND-якорь виден в диагностиках единого потока.
    assert!(
        diagnostics.iter().any(|d| matches!(
            d,
            npa_anchor::AnchorDiagnostic::RejectedAnchor {
                reason: npa_anchor::RejectReason::Inbound,
                ..
            }
        )),
        "rejected inbound anchor must surface as diagnostic: {diagnostics:?}"
    );

    // Спаны — валидные локальные UTF-8 byte bounds своего источника.
    for m in &members {
        let src = &paras[m.span.block];
        assert!(
            npa_anchor::check_span(src, m.span).is_ok(),
            "typed span must be valid UTF-8 byte bounds: {:?}",
            m.span
        );
    }
}

/// Повтор реквизита в другом span — отдельные occurrences, identity по
/// `(date, number)` не сливается (M207 AMBIGUOUS_DUPLICATE, D518).
#[test]
fn typed_preserves_source_occurrences() {
    let para = "Федеральный закон от 02.07.2021 N 337-ФЗ, а также \
                тот же Федеральный закон от 02.07.2021 N 337-ФЗ."
        .to_string();
    let members = npa_typed::scan_typed(std::slice::from_ref(&para));

    assert_eq!(
        members.len(),
        2,
        "occurrences must not merge by (date, number): {members:?}"
    );
    assert_eq!(members[0].date, members[1].date);
    assert_eq!(members[0].number, members[1].number);
    assert_ne!(
        members[0].span, members[1].span,
        "distinct occurrences must keep distinct spans"
    );
    assert_eq!(members[0].span.block, 0);
    assert_eq!(members[1].span.block, 0);
    assert!(members[0].span.start < members[1].span.start);
    for m in &members {
        assert!(npa_anchor::check_span(&para, m.span).is_ok());
    }
}

/// Span типизированного члена локален источнику и измеряется в UTF-8 байтах
/// (не char-индексах): многобайтовый префикс сдвигает byte-смещение.
#[test]
fn typed_span_is_source_local_byte_bounds() {
    let para = "Преамбула «ёж»: Указ Президента РФ от 05.03.2019 N 12-ФЗ принят.".to_string();
    let members = npa_typed::scan_typed(std::slice::from_ref(&para));

    assert_eq!(members.len(), 1, "members={members:?}");
    let m = &members[0];
    assert_eq!(m.date, "05.03.2019");
    assert_eq!(m.number, "12-ФЗ");
    assert_eq!(m.type_name, "Указ Президента РФ");
    assert_eq!(m.span.block, 0);
    assert!(m.span.start < m.span.end);
    assert!(m.span.end <= para.len());
    assert!(para.is_char_boundary(m.span.start));
    assert!(para.is_char_boundary(m.span.end));
    assert_eq!(&para[m.span.start..m.span.end], "от 05.03.2019 N 12-ФЗ");

    let ot_byte = para.find("от ").expect("от present");
    assert_eq!(m.span.start, ot_byte);
    let char_index = para[..ot_byte].chars().count();
    let expected_byte: usize = para.chars().take(char_index).map(|c| c.len_utf8()).sum();
    assert_eq!(
        m.span.start, expected_byte,
        "byte offset must equal the UTF-8 prefix length"
    );
    assert!(m.span.start > char_index, "span must be byte-based");
}
