//! Classifier recall/precision on the real catalog golden set (M169 S04 T02).
//!
//! Golden set: 120 explicit `amends` rows of `legal_relation_items` (121 rows
//! total in the 2026-08-14 export; the extra row is `affects_legal_state`
//! / review and is not part of the amends golden set). The classifier sees
//! the C1 tooltip (`raw_tooltip`) as link context.
//!
//! Both engines are measured:
//! - single-signal rules (`link_classifiers` via `classify_link`)
//! - multi-signal templates (`classifier_templates` via `classify_link_scored`)
//!
//! Baseline floors per the slice plan: P >= 0.8, R >= 0.5. Below that the
//! test fails honestly with a task to extend templates in kb-ontology.yaml.
//!
//! Skip-capable without CONSULTANT_EXPORT_DIR. Metrics print as counts,
//! ratios and catalog item ids only; raw legal text is never echoed.

use ln_consultant_parser::catalog_sqlite::SqliteCatalog;
use ln_consultant_parser::classifier::{
    classify_link, classify_link_scored, load_classifier_rules, load_templates,
};
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

/// One golden row: (catalog item_id, relation_type, raw_tooltip).
type GoldenRow = (i64, String, String);

struct Measured {
    name: String,
    hits: usize,
    miss_item_ids: Vec<i64>,
    false_positives: usize,
    recall: f64,
    precision: f64,
}

fn measure(
    name: &str,
    golden: &[GoldenRow],
    negatives: &[String],
    is_amends: impl Fn(&str) -> bool,
) -> Measured {
    let hits = golden
        .iter()
        .filter(|(_, _, tooltip)| is_amends(tooltip))
        .count();
    let miss_item_ids: Vec<i64> = golden
        .iter()
        .filter(|(_, _, tooltip)| !is_amends(tooltip))
        .map(|(item_id, _, _)| *item_id)
        .collect();
    let false_positives = negatives.iter().filter(|t| is_amends(t)).count();
    let recall = hits as f64 / golden.len() as f64;
    let precision = if hits + false_positives == 0 {
        1.0
    } else {
        hits as f64 / (hits + false_positives) as f64
    };
    Measured {
        name: name.to_owned(),
        hits,
        miss_item_ids,
        false_positives,
        recall,
        precision,
    }
}

#[test]
fn classifier_recall_on_real_amends_golden_set() {
    let Some(path) = catalog_path() else {
        eprintln!("SKIP: consru_export catalog not available");
        return;
    };
    let catalog = SqliteCatalog::open_read_only(&path).expect("open catalog read-only");
    let golden = catalog.golden_relation_rows().expect("golden rows");
    assert!(
        golden.len() >= 120,
        "expected the 120 explicit amends rows, got {}",
        golden.len()
    );
    assert!(
        golden.iter().all(|(_, kind, _)| kind == "amends"),
        "golden set must contain amends edges only"
    );
    let negatives = catalog.non_amending_titles(300).expect("negatives");

    let rules = load_classifier_rules();
    let templates = load_templates();
    assert!(!rules.is_empty(), "link_classifiers must not be empty");
    assert!(
        !templates.is_empty(),
        "classifier_templates must not be empty"
    );

    let rules_m = measure("rules", &golden, &negatives, |ctx| {
        classify_link(&link(ctx), &rules).kind == "amends"
    });
    let templates_m = measure("templates", &golden, &negatives, |ctx| {
        classify_link_scored(&link(ctx), &templates).kind == "amends"
    });

    for m in [&rules_m, &templates_m] {
        eprintln!(
            "[{}] positives={} hits={} recall={:.3}; negatives={} fp={} precision={:.3}",
            m.name,
            golden.len(),
            m.hits,
            m.recall,
            negatives.len(),
            m.false_positives,
            m.precision
        );
        eprintln!(
            "[{}] miss_item_ids={:?} (counts and catalog ids only, no raw text)",
            m.name, m.miss_item_ids
        );
    }
    // Baseline floors (slice plan): P >= 0.8, R >= 0.5. Honest FAIL below
    // with a task to extend classifier_templates / link_classifiers.
    for m in [&rules_m, &templates_m] {
        assert!(
            m.recall >= 0.5,
            "[{}] recall {:.3} < 0.5 (hits {}/{}) — extend templates, misses item_ids {:?}",
            m.name,
            m.recall,
            m.hits,
            golden.len(),
            m.miss_item_ids
        );
        assert!(
            m.precision >= 0.8,
            "[{}] precision {:.3} < 0.8 (fp {}/{}) — extend templates, tighten amends needles",
            m.name,
            m.precision,
            m.false_positives,
            negatives.len()
        );
    }
}
