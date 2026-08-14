//! Edge deriver tests: ClassifiedLink → DerivedEdge with correct direction.

use ln_consultant_parser::{classify_all_scored, derive_edges, extract_hyperlinks, ClassifiedLink};

fn cl(kind: &str, dest: &str, text: &str, conf: f64) -> ClassifiedLink {
    ClassifiedLink {
        dest: dest.to_owned(),
        text: text.to_owned(),
        kind: kind.to_owned(),
        confidence: conf,
    }
}

const SOURCE: &str = "consultantplus://offline/ref=SOURCE_44_FZ";

#[test]
fn amends_edge_direction_reversed() {
    let links = vec![cl(
        "amends",
        "consultantplus://offline/ref=360_FZ",
        "N 360-ФЗ",
        0.9,
    )];
    let edges = derive_edges(&links, SOURCE);
    assert_eq!(edges.len(), 1);
    // amends: from amending act (360-FZ) → to amended act (44-FZ source)
    assert_eq!(
        edges[0].from_consider,
        "consultantplus://offline/ref=360_FZ"
    );
    assert_eq!(edges[0].to_consider, SOURCE);
    assert_eq!(edges[0].kind, "amends");
}

#[test]
fn cites_edge_direction_forward() {
    let links = vec![cl(
        "cites",
        "consultantplus://offline/ref=GK_RF",
        "статья 421",
        0.7,
    )];
    let edges = derive_edges(&links, SOURCE);
    assert_eq!(edges.len(), 1);
    // cites: from source (44-FZ) → to target (GK RF)
    assert_eq!(edges[0].from_consider, SOURCE);
    assert_eq!(edges[0].to_consider, "consultantplus://offline/ref=GK_RF");
}

#[test]
fn unknown_links_skipped() {
    let links = vec![
        cl("amends", "ref1", "N 360", 0.9),
        cl("unknown", "ref2", "что-то", 0.1),
        cl("cites", "ref3", "статья", 0.6),
    ];
    let edges = derive_edges(&links, SOURCE);
    assert_eq!(edges.len(), 2); // unknown filtered out
}

#[test]
fn real_44fz_edge_derivation() {
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
    let edges = derive_edges(&classified, "consultantplus://offline/ref=44_FZ");

    let mut counts = std::collections::HashMap::new();
    for e in &edges {
        *counts.entry(e.kind.as_str()).or_insert(0usize) += 1;
    }
    println!("44-ФЗ derived edges: total={}", edges.len());
    let mut sorted: Vec<_> = counts.iter().collect();
    sorted.sort_by(|a, b| b.1.cmp(a.1));
    for (kind, count) in &sorted {
        println!("  {kind}: {count}");
    }

    assert!(!edges.is_empty(), "must derive edges from 44-ФЗ");
    let amends = counts.get("amends").copied().unwrap_or(0);
    assert!(amends > 100, "must have 100+ amends edges; got {amends}");
}
