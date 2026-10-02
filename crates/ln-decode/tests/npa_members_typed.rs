//! M211 S02: паритет типизированных членов (дата, номер, TYPE) с
//! Python-прототипом. Фикстура TSV [bounded], reader hand-rolled (D602).
//!
//! M211 S01/T01: fixtures обязательные — отсутствие seed-фрагмента даёт
//! провал `MISSING SOURCE`, а не молчаливый skip.
//!
//! T02 (следующий task слайса) сведёт `scan_typed` на единый поток якорей
//! S01 с общими guards; здесь фиксируется только строгость фикстуры.

use std::collections::BTreeMap;
use std::path::PathBuf;

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
        let got_set: std::collections::BTreeMap<(String, String), String> = got
            .iter()
            .filter(|t| !t.type_name.is_empty())
            .map(|t| ((t.date.clone(), t.number.clone()), t.type_name.clone()))
            .collect();

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

    // S02 — измеритель: паритет TYPE растёт итерациями (не гейт).
    // Минимальный порог: >50% type_match на типизированных want-членах.
    let want_typed = want_total; // все want entries имеют тип
    let rate = if want_typed > 0 {
        (type_match * 100).checked_div(want_typed).unwrap_or(0)
    } else {
        0
    };
    eprintln!("S02 typed match rate: {rate}% ({type_match}/{want_typed}) — итерации продолжаются");
    assert!(
        rate > 50,
        "S02 typed match rate {rate}% below 50% threshold ({type_match}/{want_typed})"
    );
    assert_eq!(checked, 40, "gold corpus must contain 40 docs");
    // детали расхождений — для отладки следующей итерации
    if !mismatches.is_empty() {
        eprintln!(
            "S02 remaining diffs ({}):\n{}",
            mismatches.len(),
            mismatches.join("\n")
        );
    }
}
