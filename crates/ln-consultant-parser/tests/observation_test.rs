//! Observation store tests: unknown links → learning backlog.

use ln_consultant_parser::{
    classify_all_scored, collect_observations, extract_hyperlinks, format_observations_yaml,
    ClassifiedLink,
};

fn cl(kind: &str, dest: &str, text: &str) -> ClassifiedLink {
    ClassifiedLink {
        dest: dest.to_owned(),
        text: text.to_owned(),
        kind: kind.to_owned(),
        confidence: 0.5,
        context: String::new(),
    }
}

#[test]
fn unknown_links_collected() {
    let links = vec![
        cl("amends", "ref1", "N 360"),
        cl("unknown", "ref2", "закон"),
        cl("unknown", "ref3", "закон"),
        cl("unknown", "ref4", "перечень документов"),
    ];
    let obs = collect_observations(&links);
    assert_eq!(obs.len(), 2); // "закон" (2 occurrences) + "перечень документов" (1)
    assert_eq!(obs[0].link_text, "закон");
    assert_eq!(obs[0].occurrences, 2);
}

#[test]
fn known_links_not_collected() {
    let links = vec![cl("amends", "ref1", "N 360"), cl("cites", "ref2", "статья")];
    let obs = collect_observations(&links);
    assert!(obs.is_empty());
}

#[test]
fn sorted_by_frequency() {
    let links = vec![
        cl("unknown", "r1", "редко"),
        cl("unknown", "r2", "часто"),
        cl("unknown", "r3", "часто"),
        cl("unknown", "r4", "часто"),
    ];
    let obs = collect_observations(&links);
    assert_eq!(obs[0].link_text, "часто");
    assert_eq!(obs[0].occurrences, 3);
    assert_eq!(obs[1].link_text, "редко");
}

#[test]
fn yaml_output_contains_observations() {
    let links = vec![cl("unknown", "r1", "закон"), cl("unknown", "r2", "закон")];
    let obs = collect_observations(&links);
    let yaml = format_observations_yaml(&obs);
    assert!(yaml.contains("link_text"));
    assert!(yaml.contains("occurrences: 2"));
    assert!(yaml.contains("candidate"));
}

#[test]
fn real_44fz_observations() {
    let path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../")
        .join("consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");
    let xml = std::fs::read(&path);
    if xml.is_err() {
        eprintln!("SKIP: consru_export not available");
        return;
    }
    let links = extract_hyperlinks(&xml.unwrap());
    let classified = classify_all_scored(&links);
    let obs = collect_observations(&classified);

    println!("44-ФЗ observations: {} unique unknown patterns", obs.len());
    println!("Top 10:");
    for o in obs.iter().take(10) {
        println!(
            "  [{}] {} ({} dests)",
            o.occurrences, o.link_text, o.unique_dests
        );
    }

    assert!(!obs.is_empty(), "must have unknown observations");
    // "закон" should be a common unknown pattern
    assert!(obs.iter().any(|o| o.link_text.contains("закон")));
}
