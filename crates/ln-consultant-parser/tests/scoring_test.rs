//! Scoring engine tests: multi-signal templates with AND/OR logic (ADR-0027).

use ln_consultant_parser::{
    classify_all_scored, classify_link_scored, extract_hyperlinks, load_templates, score_template,
    RawLink, Template,
};

fn link(context: &str) -> RawLink {
    RawLink {
        dest: "consultantplus://offline/ref=TOKEN".to_owned(),
        text: "N 360-ФЗ".to_owned(),
        context: context.to_owned(),
    }
}

#[test]
fn and_mode_requires_all_needles() {
    let t = Template {
        name: "test_and".to_owned(),
        kind: "amends".to_owned(),
        confidence: 0.9,
        match_all: true,
        needles: vec!["в ред.".to_owned(), "ФЗ".to_owned()],
    };
    // Both present → full confidence
    assert_eq!(score_template(&t, &link("в ред. ФЗ от 2024 N 360")), 0.9);
    // Only one → zero
    assert_eq!(score_template(&t, &link("закон N 360 от 2024")), 0.0);
    assert_eq!(score_template(&t, &link("в ред. постановления")), 0.0);
}

#[test]
fn or_mode_proportional_score() {
    let t = Template {
        name: "test_or".to_owned(),
        kind: "cites".to_owned(),
        confidence: 0.7,
        match_all: false,
        needles: vec![
            "согласно".to_owned(),
            "в соответствии с".to_owned(),
            "предусмотренном".to_owned(),
        ],
    };
    // All 3 match → full confidence
    let full = score_template(&t, &link("согласно и в соответствии с и предусмотренном"));
    assert!((full - 0.7).abs() < 0.01);
    // 1 of 3 → 0.7 × (1/3) ≈ 0.233
    let partial = score_template(&t, &link("только согласно закону"));
    assert!((partial - 0.233).abs() < 0.01);
    // 0 → zero
    assert_eq!(score_template(&t, &link("нет совпадений")), 0.0);
}

#[test]
fn best_score_wins() {
    let templates = vec![
        Template {
            name: "amends_and".to_owned(),
            kind: "amends".to_owned(),
            confidence: 0.9,
            match_all: true,
            needles: vec!["в ред.".to_owned(), "ФЗ".to_owned()],
        },
        Template {
            name: "cites_or".to_owned(),
            kind: "cites".to_owned(),
            confidence: 0.7,
            match_all: false,
            needles: vec!["согласно".to_owned(), "в соответствии".to_owned()],
        },
    ];
    // Context matches amends (both needles) → score 0.9 > cites 0.0
    let result = classify_link_scored(&link("в ред. ФЗ N 360-ФЗ"), &templates);
    assert_eq!(result.kind, "amends");
    assert!((result.confidence - 0.9).abs() < 0.01);
}

#[test]
fn templates_loaded_from_yaml() {
    let templates = load_templates();
    assert!(!templates.is_empty(), "YAML must have classifier_templates");
    // Check amends_v_red template exists with AND mode
    let amends = templates.iter().find(|t| t.name == "amends_v_red");
    assert!(amends.is_some());
    let amends = amends.unwrap();
    assert!(amends.match_all);
    assert!(amends.needles.contains(&"в ред.".to_owned()));
    assert!(amends.needles.contains(&"ФЗ".to_owned()));
}

#[test]
fn real_44fz_scored_vs_single() {
    let path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../")
        .join("consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");
    let xml = std::fs::read(&path);
    if xml.is_err() {
        eprintln!("SKIP: consru_export not available");
        return;
    }
    let links = extract_hyperlinks(&xml.unwrap());

    // Scored classification
    let scored = classify_all_scored(&links);
    let mut counts = std::collections::HashMap::new();
    let mut conf_sum = 0.0;
    for c in &scored {
        *counts.entry(c.kind.as_str()).or_insert(0usize) += 1;
        conf_sum += c.confidence;
    }
    let avg_conf = conf_sum / scored.len() as f64;

    println!("44-ФЗ scored classification:");
    let mut sorted: Vec<_> = counts.iter().collect();
    sorted.sort_by(|a, b| b.1.cmp(a.1));
    for (kind, count) in &sorted {
        println!("  {kind}: {count}");
    }
    println!("  avg confidence: {avg_conf:.3}");

    assert!(scored.len() > 1000);
    let amends = counts.get("amends").copied().unwrap_or(0);
    assert!(amends > 100, "must have 100+ amends; got {amends}");
}
