//! Link classifier tests: RawLink → ClassifiedLink based on context.

use ln_consultant_parser::{
    classify_all, classify_link, extract_hyperlinks, load_classifier_rules, RawLink,
};

fn link(dest: &str, text: &str, context: &str) -> RawLink {
    RawLink {
        dest: dest.to_owned(),
        text: text.to_owned(),
        context: context.to_owned(),
    }
}

#[test]
fn amendment_context_classified_as_amends() {
    let l = link(
        "consultantplus://offline/ref=TOKEN",
        "N 360-ФЗ",
        "(в ред. Федерального закона от 24.11.2014 N 356-ФЗ)",
    );
    let rules = load_classifier_rules();
    assert!(!rules.is_empty());
    let result = classify_link(&l, &rules);
    assert_eq!(result.kind, "amends");
    assert!(result.confidence >= 0.8);
}

#[test]
fn citation_context_classified_as_cites() {
    let l = link(
        "consultantplus://offline/ref=TOKEN",
        "статья 421",
        "в соответствии с Гражданским кодексом",
    );
    let rules = load_classifier_rules();
    let result = classify_link(&l, &rules);
    assert_eq!(result.kind, "cites");
}

#[test]
fn implements_context_classified() {
    let l = link(
        "consultantplus://offline/ref=TOKEN",
        "порядок",
        "в порядке, установленном Правительством",
    );
    let rules = load_classifier_rules();
    let result = classify_link(&l, &rules);
    assert_eq!(result.kind, "implements");
}

#[test]
fn unknown_context_low_confidence() {
    let l = link(
        "consultantplus://offline/ref=TOKEN",
        "закон",
        "некоторый контекст без ключевых слов",
    );
    let rules = load_classifier_rules();
    let result = classify_link(&l, &rules);
    assert_eq!(result.kind, "unknown");
    assert!(result.confidence < 0.2);
}

#[test]
fn classify_multiple_links() {
    let links = vec![
        link("ref1", "N 360-ФЗ", "в ред. N 360-ФЗ от 2024"),
        link("ref2", "статья 421", "согласно ГК РФ"),
        link("ref3", "закон", "какой-то текст"),
    ];
    let results = classify_all(&links);
    assert_eq!(results.len(), 3);
    assert_eq!(results[0].kind, "amends");
    assert_eq!(results[1].kind, "cites");
    assert_eq!(results[2].kind, "unknown");
}

#[test]
fn real_44fz_classification_distribution() {
    let path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../")
        .join("consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");
    let xml = std::fs::read(&path);
    if xml.is_err() {
        eprintln!("SKIP: consru_export not available");
        return;
    }
    let links = extract_hyperlinks(&xml.unwrap());
    let classified = classify_all(&links);

    let mut counts = std::collections::HashMap::new();
    for c in &classified {
        *counts.entry(c.kind.as_str()).or_insert(0usize) += 1;
    }

    println!("44-ФЗ link classification:");
    let mut sorted: Vec<_> = counts.iter().collect();
    sorted.sort_by(|a, b| b.1.cmp(a.1));
    for (kind, count) in sorted {
        println!("  {kind}: {count}");
    }

    assert!(classified.len() > 1000, "must have 1000+ classified links");
    let amends = counts.get("amends").copied().unwrap_or(0);
    assert!(amends > 100, "must have 100+ amends; got {amends}");
}
