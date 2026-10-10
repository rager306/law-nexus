//! M211 S01: паритет якорей (дата, номер) с Python-прототипом
//! `scripts/m207_context_graph_demo.py` (executable spec, ADR-0029), плюс
//! строгие обязательные fixtures и контракт локальных UTF-8 byte spans.
//!
//! Фикстура `anchor-parity-fixture.tsv` [bounded] экспортирована из
//! прототипа. Universe = тексты seed-фрагментов (без головы XML, хвостов
//! и линкеров — это слои S02+). D602: serde только для `source_package`,
//! здесь reader hand-rolled. Корпус отсутствует -> **fail closed**, не skip
//! (D282 empty-as-unset касается `CONSULTANT_EXPORT_DIR`, а не обязательной
//! tracked-фикстуры).

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;

struct DocFixture {
    fragments: Vec<String>,
    anchors: Vec<(String, String)>,
}

/// Hand-rolled reader TSV-фикстуры (D602: без serde).
fn read_fixture(path: &PathBuf) -> BTreeMap<String, DocFixture> {
    let text = std::fs::read_to_string(path).expect("parity fixture must exist (tracked)");
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
                docs.insert(
                    cols[1].to_string(),
                    DocFixture {
                        fragments: Vec::new(),
                        anchors: Vec::new(),
                    },
                );
            }
            "frag" => {
                if cols.len() >= 2
                    && let Some(cur) = current.as_deref()
                    && let Some(d) = docs.get_mut(cur)
                {
                    d.fragments.push(cols[1].to_string());
                }
            }
            "anchor" => {
                if cols.len() < 3 {
                    continue;
                }
                let Some(cur) = current.as_deref() else {
                    continue;
                };
                if let Some(d) = docs.get_mut(cur) {
                    d.anchors.push((cols[1].to_string(), cols[2].to_string()));
                }
            }
            _ => {}
        }
    }
    docs
}

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("crates/ln-decode/tests/fixtures/npa-members/anchor-parity-fixture.tsv")
}

fn fixture_source_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("crates/ln-decode/tests/fixtures/npa-lawref")
}

/// Обязательный паритет + строгие fixtures + локальные byte spans.
///
/// Fail closed: отсутствие любого seed-фрагмента — провал с диагностикой
/// `MISSING SOURCE`, не молчаливый skip. Каждый принятый якорь обязан лежать
/// в корректном полуоткрытом UTF-8 byte-диапазоне своего источника.
#[test]
fn gold_anchor_parity_40_docs() {
    let docs = read_fixture(&fixture_path());
    assert!(
        !docs.is_empty(),
        "MISSING SOURCE: anchor parity fixture is mandatory and must be non-empty"
    );
    let root = fixture_source_root();

    let mut mismatches: Vec<String> = Vec::new();
    let mut missing_sources: Vec<String> = Vec::new();
    let mut invalid_spans: Vec<String> = Vec::new();
    let mut checked = 0usize;
    let mut got_total = 0usize;
    let mut want_total = 0usize;
    let mut rejected_total = 0usize;
    let mut duplicate_total = 0usize;

    for (doc, fixture) in &docs {
        assert!(
            !fixture.fragments.is_empty(),
            "MISSING SOURCE: {doc} has an empty fragment list"
        );
        let mut paras: Vec<String> = Vec::new();
        let mut doc_missing: Vec<String> = Vec::new();
        for fname in &fixture.fragments {
            match std::fs::read_to_string(root.join(fname)) {
                Ok(text) => paras.push(text),
                Err(e) => doc_missing.push(format!("{doc}: {fname}: {e}")),
            }
        }
        if !doc_missing.is_empty() {
            // Обязательные fixtures fail closed: missing source — провал, не skip.
            missing_sources.extend(doc_missing);
            continue;
        }

        let (got, diagnostics) = npa_anchor::scan_anchors_diagnosed(&paras);
        got_total += got.len();
        want_total += fixture.anchors.len();
        checked += 1;
        rejected_total += diagnostics
            .iter()
            .filter(|d| matches!(d, npa_anchor::AnchorDiagnostic::RejectedAnchor { .. }))
            .count();
        duplicate_total += diagnostics
            .iter()
            .filter(|d| matches!(d, npa_anchor::AnchorDiagnostic::DuplicateOccurrence { .. }))
            .count();

        // Byte spans must be valid and must locate the requisite in its source.
        for a in &got {
            let Some(src) = paras.get(a.span.block) else {
                invalid_spans.push(format!("{doc}: span block {} out of range", a.span.block));
                continue;
            };
            if npa_anchor::check_span(src, a.span).is_err() {
                invalid_spans.push(format!(
                    "{doc}: invalid span {:?} in block {}",
                    a.span, a.span.block
                ));
                continue;
            }
            let slice = &src[a.span.start..a.span.end];
            let slice_l = slice.to_lowercase();
            let located = if a.number == "б/н" {
                slice_l.contains("б/н")
            } else {
                slice_l.contains(&a.number.to_lowercase())
            };
            if !slice_l.starts_with("от") || !located {
                invalid_spans.push(format!(
                    "{doc}: span {:?} does not locate anchor ({} {}): slice={slice:?}",
                    a.span, a.date, a.number
                ));
            }
        }

        let want_set: std::collections::BTreeSet<(String, String)> =
            fixture.anchors.iter().cloned().collect();
        let got_set: std::collections::BTreeSet<(String, String)> = got
            .iter()
            .map(|a| (a.date.clone(), a.number.clone()))
            .collect();

        let missing: Vec<_> = want_set.difference(&got_set).collect();
        let extra: Vec<_> = got_set.difference(&want_set).collect();
        if !missing.is_empty() || !extra.is_empty() {
            mismatches.push(format!(
                "{doc}: missing={missing:?} extra={extra:?} (got={} want={})",
                got_set.len(),
                want_set.len()
            ));
        }
    }

    eprintln!(
        "anchor parity: checked={checked} missing={} rejected={rejected_total} duplicates={duplicate_total} got_total={got_total} want_total={want_total}",
        missing_sources.len()
    );

    assert!(
        missing_sources.is_empty(),
        "MISSING SOURCE (mandatory fixtures fail closed; no silent skip):\n{}",
        missing_sources.join("\n")
    );
    assert!(
        invalid_spans.is_empty(),
        "invalid/non-locating spans:\n{}",
        invalid_spans.join("\n")
    );
    assert!(
        mismatches.is_empty(),
        "anchor parity mismatches ({} docs checked):\n{}",
        checked,
        mismatches.join("\n")
    );
    assert_eq!(checked, 40, "gold corpus must contain 40 docs");
}

/// Обязательные inline-фикстуры guard'ов — tracked, не пропускаются:
/// inbound (обе формы), Минюст-регистрация, б/н, NBSP, регистр месяца.
#[test]
fn guard_cases_are_mandatory() {
    use npa_anchor::RejectReason;

    // (para, ожидаемые (date, number), ожидаемые причины отказов)
    type GuardCase = (
        &'static str,
        Vec<(&'static str, &'static str)>,
        Vec<RejectReason>,
    );
    let cases: Vec<GuardCase> = vec![
        // INBOUND форма 1: «(вх. от DD.MM.YYYY N NUM» — якорь не строится
        // (его отсекает lookbehind «вх.»), поэтому отказов-диагностик нет.
        ("(вх. от 12.03.2019 N 1456)", vec![], vec![]),
        // INBOUND форма 2: «(вх. N NUM от DD.MM.YYYY N NUM» — кандидат возникает
        // (lookbehind не срабатывает), но зона INBOUND его отвергает.
        (
            "(вх. N 1456 от 12.03.2019 N 999)",
            vec![],
            vec![RejectReason::Inbound],
        ),
        // Минюст-регистрация — не реквизит документа: «от»-якоря нет.
        (
            "Зарегистрировано в Минюсте России 12.03.2019 N 1456",
            vec![],
            vec![],
        ),
        // б/н: номер как написан.
        (
            "Приказ принят от 02.07.2021 б/н",
            vec![("02.07.2021", "б/н")],
            vec![],
        ),
        // NBSP как whitespace между «от», датой, «N» и номером.
        (
            "Приказ от\u{a0}02.07.2021\u{a0}N\u{a0}337-ФЗ",
            vec![("02.07.2021", "337-ФЗ")],
            vec![],
        ),
        // Регистр месяца (OT_DUMA) нормализуется без учёта регистра.
        (
            "Принят от 29 ИЮЛЯ 2017 года N 218-ФЗ",
            vec![("29.07.2017", "218-ФЗ")],
            vec![],
        ),
        // Контроль OT_DATE.
        (
            "Федеральный закон от 02.07.2021 N 337-ФЗ",
            vec![("02.07.2021", "337-ФЗ")],
            vec![],
        ),
    ];

    for (para, want, want_rejects) in cases {
        let paras = vec![para.to_string()];
        let (got, diagnostics) = npa_anchor::scan_anchors_diagnosed(&paras);
        let got_keys: Vec<(String, String)> = got
            .iter()
            .map(|a| (a.date.clone(), a.number.clone()))
            .collect();
        let want_keys: Vec<(String, String)> = want
            .iter()
            .map(|(d, n)| (d.to_string(), n.to_string()))
            .collect();
        assert_eq!(got_keys, want_keys, "guard case {para:?}");

        let rejects: Vec<RejectReason> = diagnostics
            .iter()
            .filter_map(|d| match d {
                npa_anchor::AnchorDiagnostic::RejectedAnchor { reason, .. } => Some(*reason),
                _ => None,
            })
            .collect();
        assert_eq!(rejects, want_rejects, "guard rejections for {para:?}");

        for a in &got {
            assert!(
                npa_anchor::check_span(para, a.span).is_ok(),
                "span must be valid UTF-8 byte bounds: {a:?}"
            );
        }
    }
}

/// Byte spans локальны источнику и измеряются в UTF-8 байтах (не char).
#[test]
fn spans_are_local_utf8_byte_bounds() {
    let para = "Преамбула «ёж»: Приказ от 05.03.2019 N 12-ФЗ принят.".to_string();
    let (anchors, diagnostics) = npa_anchor::scan_anchors_diagnosed(std::slice::from_ref(&para));
    assert!(
        diagnostics.is_empty(),
        "unexpected diagnostics: {diagnostics:?}"
    );
    assert_eq!(anchors.len(), 1);

    let a = &anchors[0];
    assert_eq!(a.span.block, 0);
    assert!(a.span.start < a.span.end);
    assert!(a.span.end <= para.len());
    assert!(para.is_char_boundary(a.span.start));
    assert!(para.is_char_boundary(a.span.end));
    assert_eq!(a.span.start, para.find("от").expect("от present"));
    assert_eq!(&para[a.span.start..a.span.end], "от 05.03.2019 N 12-ФЗ");

    // Префикс с multibyte-символами: byte-смещение строго больше char-индекса.
    let char_index = para.chars().position(|c| c == 'о').expect("char о");
    assert!(
        a.span.start > char_index,
        "span must be byte-based (byte {} > char {})",
        a.span.start,
        char_index
    );
    let expected_byte: usize = para.chars().take(char_index).map(|c| c.len_utf8()).sum();
    assert_eq!(
        a.span.start, expected_byte,
        "byte offset must equal the UTF-8 prefix length"
    );
}

/// `check_span` отклоняет полуоткрыто-невалидные и UTF-8-разрывающие спаны.
#[test]
fn invalid_span_is_reported() {
    let para = "Приказ от 05.03.2019 N 12";
    // ASCII-источник — положительный контроль.
    let ascii = "abcdef";
    assert!(
        npa_anchor::check_span(
            ascii,
            npa_anchor::LocalSpan {
                block: 0,
                start: 0,
                end: 3
            }
        )
        .is_ok()
    );
    assert_eq!(
        npa_anchor::check_span(
            para,
            npa_anchor::LocalSpan {
                block: 0,
                start: 5,
                end: 5
            }
        ),
        Err(npa_anchor::SpanError::EmptyOrInverted)
    );
    assert_eq!(
        npa_anchor::check_span(
            para,
            npa_anchor::LocalSpan {
                block: 0,
                start: 0,
                end: 9999
            }
        ),
        Err(npa_anchor::SpanError::OutOfBounds)
    );
    // 1 разрывает двухбайтовую '«'.
    let nb = "«ёж»";
    assert_eq!(
        npa_anchor::check_span(
            nb,
            npa_anchor::LocalSpan {
                block: 0,
                start: 1,
                end: 2
            }
        ),
        Err(npa_anchor::SpanError::NotCharBoundary)
    );
    assert!(
        npa_anchor::check_span(
            nb,
            npa_anchor::LocalSpan {
                block: 0,
                start: 0,
                end: 8
            }
        )
        .is_ok()
    );
}

/// Повтор реквизита в другом span — отдельный occurrence + диагностика.
#[test]
fn duplicate_occurrence_is_diagnosed() {
    let para = "Первый: Приказ от 05.03.2019 N 12. Второй: Приказ от 05.03.2019 N 12.".to_string();
    let (anchors, diagnostics) = npa_anchor::scan_anchors_diagnosed(&[para]);
    assert_eq!(
        anchors.len(),
        2,
        "occurrences must not merge by (date, number)"
    );
    assert_ne!(anchors[0].span, anchors[1].span);
    let dups = diagnostics
        .iter()
        .filter(|d| matches!(d, npa_anchor::AnchorDiagnostic::DuplicateOccurrence { .. }))
        .count();
    assert_eq!(dups, 1, "duplicate occurrence must be diagnosed");
}
