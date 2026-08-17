//! Text-facet CTV between real editions (M170 S02 T01).
//!
//! edition-0001 (rev-initial, in force 2013-04-05) vs edition-0002
//! (rev-2013-07-02): structurally identical at marker level (M169 finding),
//! article TEXT changed. resolve_ctv at the two days must return different
//! real texts for the changed article. Skip-capable without the export.

use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    article_body::collect_article_texts,
    domain::{DecodeRequest, FamilyFormat, PayloadRef},
    ports::BlockDecoderPort,
};
use ln_kb_ontology::domain::{
    build_text_log_from_articles, changed_article_texts, resolve_ctv, CtvResolution,
};
use ln_kb_ontology::registry::{
    load_edition_day_for_path, load_expression_id_for_path, load_hierarchy_map_for_path,
};
use ln_temporal::domain::ComponentConceptId;

#[test]
fn real_44fz_statya_1_resolves_to_full_article_text() {
    let Some(dir) = editions_dir() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let path = dir.join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");
    let path_str = path.to_string_lossy().to_string();
    let bytes = std::fs::read(&path).expect("read edition-0118");
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m170-text-ctv").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        &bytes,
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("decode");
    let bodies = collect_article_texts(&blocks);
    let with_text = bodies
        .iter()
        .filter(|b| !b.text().trim().is_empty())
        .count();
    eprintln!("statya articles with non-empty full text: {with_text}");
    assert!(with_text >= 85);

    let map = load_hierarchy_map_for_path(&path_str).expect("registry map");
    let day = load_edition_day_for_path(&path_str).expect("edition day");
    let provenance = load_expression_id_for_path(&path_str).expect("expression id");
    let log = build_text_log_from_articles(
        &map,
        bodies
            .iter()
            .map(|b| ("statya", b.number(), b.title(), b.text() as &str)),
        day,
        &provenance,
    );
    let cc1 = ComponentConceptId::parse("cc:44-fz:statya-1").expect("cc");
    match resolve_ctv(&log, &cc1, day) {
        CtvResolution::Resolved { text, .. } => {
            let len = text.chars().count();
            eprintln!("statya-1 resolved text: {len} chars");
            assert!(len > 200, "full article body expected, got {len} chars");
        }
        other => panic!("statya-1 must resolve, got {other:?}"),
    }
    let mut resolved = 0usize;
    for n in 1..=114 {
        let Ok(ccn) = ComponentConceptId::parse(&format!("cc:44-fz:statya-{n}")) else {
            continue;
        };
        if matches!(resolve_ctv(&log, &ccn, day), CtvResolution::Resolved { .. }) {
            resolved += 1;
        }
    }
    eprintln!("statya resolved with text: {resolved}");
    // Measured on edition-0118: 85/94 (no-prose articles + one Conflict).
    assert!(
        resolved >= 80,
        "expected most bound statya to resolve, got {resolved}"
    );
}

fn editions_dir() -> Option<std::path::PathBuf> {
    let dir = std::env::var("CONSULTANT_EXPORT_DIR").unwrap_or_else(|_| "consru_export".to_owned());
    let root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(dir)
        .join("consru_export/exports/npa/law_2013-04-05_44-fz");
    root.join("edition-0001_rev-initial_from-unknown_19d3c051.xml")
        .exists()
        .then_some(root)
}

fn read_edition(path: &std::path::Path) -> Vec<ln_decode::article_body::ArticleText> {
    let bytes = std::fs::read(path).expect("read edition");
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m170-text-facet").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        &bytes,
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("decode");
    collect_article_texts(&blocks)
}

#[test]
fn text_changed_between_editions_resolves_differently() {
    let Some(dir) = editions_dir() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let seed_path = dir.join("edition-0001_rev-initial_from-unknown_19d3c051.xml");
    let target_path = dir.join("edition-0002_rev-2013-07-02_from-unknown_f4bfa020.xml");
    let seed_str = seed_path.to_string_lossy().to_string();
    let target_str = target_path.to_string_lossy().to_string();

    let seed_articles = read_edition(&seed_path);
    let target_articles = read_edition(&target_path);
    assert!(seed_articles.len() >= 80 && target_articles.len() >= 80);

    // Find articles present in both with identical number and different text.
    let mut changed: Vec<&str> = Vec::new();
    for s in &seed_articles {
        if let Some(t) = target_articles
            .iter()
            .find(|t| t.number() == s.number())
            .filter(|t| !t.text().trim().is_empty() && !s.text().trim().is_empty())
        {
            if s.text() != t.text() {
                changed.push(s.number());
            }
        }
    }
    eprintln!("articles with changed text 0001->0002: {}", changed.len());
    assert!(
        !changed.is_empty(),
        "the 2013-07-02 revision must change article text"
    );

    // The registry map is edition-agnostic for needle law_2013-04-05_44-fz.
    let map = load_hierarchy_map_for_path(&target_str).expect("registry map");
    let seed_day = load_edition_day_for_path(&seed_str).expect("seed day");
    let target_day = load_edition_day_for_path(&target_str).expect("target day");
    assert!(target_day > seed_day);
    let seed_prov = load_expression_id_for_path(&seed_str).expect("seed expression");
    let target_prov = load_expression_id_for_path(&target_str).expect("target expression");

    // Text-facet lock (M170 S02 T01): the same pair must draft exactly 3
    // text-facet events via changed_article_texts — observed on 7a3592f,
    // now asserted so the measurement cannot drift back into prose.
    // Drafts are observations, never membership writes (KBO-R061).
    let drafts = changed_article_texts(
        seed_articles
            .iter()
            .map(|a| ("statya", a.number(), a.title(), a.text())),
        target_articles
            .iter()
            .map(|a| ("statya", a.number(), a.title(), a.text())),
        &target_prov,
    )
    .expect("changed_article_texts must succeed on 0001->0002");
    eprintln!(
        "text facet drafts 0001->0002: {} (facet=text)",
        drafts.len()
    );
    assert_eq!(
        drafts.len(),
        3,
        "0001->0002 must draft exactly 3 text-facet events, got {}",
        drafts.len()
    );
    for d in &drafts {
        assert_eq!(d.facet, "text", "draft {d:?} must be text-facet");
        assert_eq!(d.evidence_class, "hypothesized_from_oracle_diff");
        assert_eq!(
            d.provenance, target_prov,
            "provenance must be the target Expression ID"
        );
    }

    let seed_log = build_text_log_from_articles(
        &map,
        seed_articles
            .iter()
            .map(|a| ("statya", a.number(), a.title(), a.text())),
        seed_day,
        &seed_prov,
    );
    let target_log = build_text_log_from_articles(
        &map,
        target_articles
            .iter()
            .map(|a| ("statya", a.number(), a.title(), a.text())),
        target_day,
        &target_prov,
    );

    // One combined log models the timeline: seed events then target events.
    let merged = merge_logs(&seed_log, &target_log);
    let sample = changed[0];
    let cc = ComponentConceptId::parse(&format!("cc:44-fz:statya-{sample}")).expect("cc");

    let before = resolve_ctv(&merged, &cc, seed_day);
    let after = resolve_ctv(&merged, &cc, target_day);
    match (before, after) {
        (CtvResolution::Resolved { text: old, .. }, CtvResolution::Resolved { text: new, .. }) => {
            assert_ne!(
                old, new,
                "statya {sample} text must change between editions"
            );
            eprintln!(
                "statya {sample}: seed {} chars, target {} chars",
                old.chars().count(),
                new.chars().count()
            );
        }
        (b, a) => panic!("both days must resolve for statya {sample}: {b:?} -> {a:?}"),
    }
    // At the seed day the later event must not leak backwards.
    if let CtvResolution::Resolved { text, .. } = resolve_ctv(&merged, &cc, seed_day) {
        let target_text = target_articles
            .iter()
            .find(|t| t.number() == sample)
            .unwrap()
            .text();
        assert_ne!(text, target_text, "no future leakage at seed day");
    }
}

/// Merge two TextVersionLogs (re-exported events) into one timeline.
fn merge_logs(
    a: &ln_kb_ontology::domain::TextVersionLog,
    b: &ln_kb_ontology::domain::TextVersionLog,
) -> ln_kb_ontology::domain::TextVersionLog {
    let mut out = ln_kb_ontology::domain::TextVersionLog::empty();
    for e in a.events() {
        let _ = out.append(e.clone());
    }
    for e in b.events() {
        let _ = out.append(e.clone());
    }
    out
}
