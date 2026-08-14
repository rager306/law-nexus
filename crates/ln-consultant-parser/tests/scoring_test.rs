//! Scoring engine tests: multi-signal templates with AND/OR logic (ADR-0027).

use ln_consultant_parser::{
    classify_all_scored, classify_all_scored_for_path, classify_link_scored, extract_hyperlinks,
    load_templates, score_template, RawLink, Template,
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
        morph_needles: Vec::new(),
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
        morph_needles: Vec::new(),
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
            morph_needles: Vec::new(),
        },
        Template {
            name: "cites_or".to_owned(),
            kind: "cites".to_owned(),
            confidence: 0.7,
            match_all: false,
            needles: vec!["согласно".to_owned(), "в соответствии".to_owned()],
            morph_needles: Vec::new(),
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
    assert!(amends.needles.contains(&"ФЗ".to_owned()));
    assert!(
        amends.morph_needles.iter().any(|n| n == "в ред."),
        "amends_v_red morph_needles must include «в ред.»"
    );
    assert!(
        amends.morph_needles.iter().any(|n| n == "в редакции"),
        "amends_v_red morph_needles must include «в редакции»"
    );
    assert!(
        amends.morph_needles.iter().any(|n| n == "редакции"),
        "amends_v_red morph_needles must include «редакции»"
    );
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

#[test]
fn compatibility_wrapper_matches_empty_path_kinds() {
    let links = vec![
        link("в ред. ФЗ N 360"),
        link("в соответствии с и согласно норме"),
        link("какой-то текст без сигнала"),
    ];
    let wrapped = classify_all_scored(&links);
    let empty_path = classify_all_scored_for_path(&links, "");
    assert_eq!(wrapped.len(), empty_path.len());
    for (left, right) in wrapped.iter().zip(empty_path.iter()) {
        assert_eq!(left.kind, right.kind);
        assert!((left.confidence - right.confidence).abs() < 1e-9);
    }
    assert_eq!(wrapped[0].kind, "amends");
    assert_eq!(wrapped[1].kind, "cites");
    assert_eq!(wrapped[2].kind, "unknown");
    assert!((wrapped[2].confidence - 0.1).abs() < 1e-9);
}

#[test]
fn path_aware_federal_law_boosts_winning_confidence_only() {
    let links = vec![link("в ред. ФЗ N 360"), link("какой-то текст без сигнала")];
    let defaulted = classify_all_scored(&links);
    let boosted = classify_all_scored_for_path(
        &links,
        "exports/npa/federalnyi-zakon-ot-05-04-2013-n-44-fz.xml",
    );
    assert_eq!(defaulted[0].kind, boosted[0].kind);
    assert_eq!(defaulted[0].kind, "amends");
    assert!(
        boosted[0].confidence > defaulted[0].confidence,
        "federal_law boost 1.0 must raise default-profile 0.7 score; got {} vs {}",
        boosted[0].confidence,
        defaulted[0].confidence
    );
    assert!((boosted[0].confidence - defaulted[0].confidence / 0.7).abs() < 1e-9);
    assert_eq!(boosted[1].kind, "unknown");
    assert!((boosted[1].confidence - 0.1).abs() < 1e-9);
    assert!((defaulted[1].confidence - 0.1).abs() < 1e-9);
}

#[test]
fn tie_order_follows_yaml_even_after_profile_boost() {
    let templates = vec![
        Template {
            name: "first".to_owned(),
            kind: "amends".to_owned(),
            confidence: 0.6,
            match_all: false,
            needles: vec!["сигнал".to_owned()],
            morph_needles: Vec::new(),
        },
        Template {
            name: "second".to_owned(),
            kind: "cites".to_owned(),
            confidence: 0.6,
            match_all: false,
            needles: vec!["сигнал".to_owned()],
            morph_needles: Vec::new(),
        },
    ];
    let result = classify_link_scored(&link("сигнал присутствует"), &templates);
    assert_eq!(
        result.kind, "amends",
        "equal scores keep earlier YAML order"
    );
    assert!((result.confidence - 0.6).abs() < 1e-9);
}

#[test]
fn morph_variant_classifies_v_redaktsii_as_amends() {
    let templates = load_templates();
    let amends = templates
        .iter()
        .find(|t| t.name == "amends_v_red")
        .expect("amends_v_red template");
    assert!(
        amends.morph_needles.iter().any(|n| n == "в редакции"),
        "YAML morph_needles must include «в редакции»"
    );
    let scored = classify_all_scored(&[link("в редакции ФЗ N 360")]);
    assert_eq!(scored[0].kind, "amends");
    assert!(scored[0].confidence > 0.1);
}

#[test]
fn hostile_substring_noise_stays_unknown() {
    // Bounded substring semantics: a morph variant matches only when the exact
    // configured token is contained. «в редколлегии» contains neither «в ред.»
    // (period required) nor «в редакции», so the amendment morph signal fails.
    let scored = classify_all_scored(&[link("в редколлегии ФЗ N 360")]);
    assert_eq!(scored[0].kind, "unknown");
    assert!((scored[0].confidence - 0.1).abs() < 1e-9);
}
