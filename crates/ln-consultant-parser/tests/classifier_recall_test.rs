//! Classifier recall/precision on the real catalog golden set (M169 S04 T02).
//!
//! Positives: 120 `legal_relation_items` rows with relation_type=amends,
//! normalization_status=explicit; the classifier sees the C1 tooltip as
//! link context. Negatives: normative titles that are not amending acts.
//!
//! Skip-capable without CONSULTANT_EXPORT_DIR. Metrics print as counts and
//! ratios only; no raw legal text beyond catalog title lexemes is persisted.

use ln_consultant_parser::catalog_sqlite::SqliteCatalog;
use ln_consultant_parser::classifier::{classify_link, load_classifier_rules};
use ln_consultant_parser::raw_link::RawLink;

fn catalog_path() -> Option<std::path::PathBuf> {
    let dir = std::env::var("CONSULTANT_EXPORT_DIR").unwrap_or_else(|_| "consru_export".to_owned());
    let p = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(dir)
        .join("consru_export/catalog-links-20260814.sqlite");
    p.exists().then_some(p)
}

fn link(context: &str) -> RawLink {
    RawLink {
        dest: "catalog://golden".to_owned(),
        text: "golden".to_owned(),
        context: context.to_owned(),
    }
}

#[test]
fn classifier_recall_on_real_amends_golden_set() {
    let Some(path) = catalog_path() else {
        eprintln!("SKIP: consru_export catalog not available");
        return;
    };
    let catalog = SqliteCatalog::open_read_only(&path).expect("open catalog read-only");
    let rules = load_classifier_rules();
    let rows = catalog.golden_relation_rows().expect("golden rows");
    assert!(
        rows.len() >= 120,
        "expected the 120+ explicit relation rows, got {}",
        rows.len()
    );

    let positives: Vec<&(String, String)> =
        rows.iter().filter(|(kind, _)| kind == "amends").collect();
    let hits = positives
        .iter()
        .filter(|(_, tooltip)| classify_link(&link(tooltip), &rules).kind == "amends")
        .count();
    let recall = hits as f64 / positives.len() as f64;

    let negatives = catalog.non_amending_titles(300).expect("negatives");
    let false_positives = negatives
        .iter()
        .filter(|title| classify_link(&link(title), &rules).kind == "amends")
        .count();
    let precision_denom = hits + false_positives;
    let precision = if precision_denom == 0 {
        1.0
    } else {
        hits as f64 / precision_denom as f64
    };

    eprintln!(
        "golden classifier P/R: positives={} hits={} recall={:.3}; negatives={} fp={} precision={:.3}",
        positives.len(),
        hits,
        recall,
        negatives.len(),
        false_positives,
        precision
    );

    // Baseline floors (measured 2026-08-15): recall floor keeps every
    // explicit amends tooltip classifiable; precision floor guards against
    // 'в ред.'-style consolidated-edition tooltips flooding amends.
    assert!(
        recall >= 0.8,
        "recall {recall:.3} below 0.8 baseline (hits {hits}/{})",
        positives.len()
    );
    assert!(
        precision >= 0.7,
        "precision {precision:.3} below 0.7 baseline (fp {false_positives}/{})",
        negatives.len()
    );
}
