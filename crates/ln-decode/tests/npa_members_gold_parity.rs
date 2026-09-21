//! M211 S01: паритет якорей (дата, номер) с Python-прототипом
//! `scripts/m207_context_graph_demo.py` (executable spec, ADR-0029).
//!
//! Фикстура `anchor-parity-fixture.tsv` [bounded] экспортирована из
//! прототипа. Universe = тексты seed-фрагментов (без головы XML, хвостов
//! и линкеров — это слои S02+). D328: читатель фикстуры hand-rolled,
//! без serde. Корпус отсутствует -> skip (D282, CONSULTANT_EXPORT_DIR
//! empty-as-unset); skip не является проходом-доказательством.

use std::collections::BTreeMap;
use std::path::PathBuf;

use ln_decode::npa_anchor;

struct DocFixture {
    fragments: Vec<String>,
    anchors: Vec<(String, String)>,
}

/// Hand-rolled reader TSV-фикстуры (D328: без serde).
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
                if cols.len() >= 2 {
                    if let Some(cur) = current.as_deref() {
                        if let Some(d) = docs.get_mut(cur) {
                            d.fragments.push(cols[1].to_string());
                        }
                    }
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

#[test]
fn gold_anchor_parity_40_docs() {
    let docs = read_fixture(&fixture_path());
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("crates/ln-decode/tests/fixtures/npa-lawref");

    let mut mismatches: Vec<String> = Vec::new();
    let mut checked = 0usize;
    let mut skipped = 0usize;
    let mut got_total = 0usize;
    let mut want_total = 0usize;

    for (doc, fixture) in &docs {
        let mut paras: Vec<String> = Vec::new();
        let mut missing_files = 0usize;
        for fname in &fixture.fragments {
            match std::fs::read_to_string(root.join(fname)) {
                Ok(text) => paras.push(text),
                Err(_) => missing_files += 1,
            }
        }
        if missing_files == fixture.fragments.len() && !fixture.fragments.is_empty() {
            skipped += 1;
            mismatches.push(format!("{doc}: SKIP (seed-фрагменты недоступны)"));
            continue;
        }
        let got = npa_anchor::scan_anchors(&paras);
        got_total += got.len();
        want_total += fixture.anchors.len();
        checked += 1;

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
        "anchor parity: checked={checked} skipped={skipped} got_total={got_total} want_total={want_total}"
    );

    if checked == 0 {
        eprintln!("SKIP: seed-фрагменты недоступны — паритет не проверялся (D282)");
        return;
    }

    assert!(
        mismatches.is_empty(),
        "anchor parity mismatches ({} docs checked):\n{}",
        checked,
        mismatches.join("\n")
    );
    assert_eq!(checked, 40, "gold corpus must contain 40 docs");
}
