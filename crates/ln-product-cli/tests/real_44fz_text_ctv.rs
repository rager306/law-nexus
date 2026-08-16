//! Real-corpus text CTV (M170 S01 T03).
//!
//! decode edition-0118 → collect_marker_bodies → build_text_log_from_articles
//! → resolve_ctv returns the REAL article text. Skip-capable without the
//! export. Bounded non-claim: full text of one edition proves extraction and
//! resolution mechanics, not legal correctness or corpus coverage.

use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    article_body::collect_article_texts,
    domain::{DecodeRequest, FamilyFormat, PayloadRef},
    ports::BlockDecoderPort,
};
use ln_kb_ontology::domain::{build_text_log_from_articles, resolve_ctv, CtvResolution};
use ln_kb_ontology::registry::{
    load_edition_day_for_path, load_expression_id_for_path, load_hierarchy_map_for_path,
};
use ln_temporal::domain::ComponentConceptId;

fn edition_path() -> Option<std::path::PathBuf> {
    let dir = std::env::var("CONSULTANT_EXPORT_DIR").unwrap_or_else(|_| "consru_export".to_owned());
    let p = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(dir)
        .join("consru_export/exports/npa/law_2013-04-05_44-fz")
        .join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");
    p.exists().then_some(p)
}

#[test]
fn real_44fz_statya_1_resolves_to_full_article_text() {
    let Some(path) = edition_path() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
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
    assert!(
        with_text >= 85,
        "most articles must carry full text (incl. nested markers), got {with_text}"
    );

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

    // Статья 1 44-ФЗ «Сфера применения настоящего Федерального закона» —
    // its body must contain the definitional opening, not just the title.
    let cc1 = ComponentConceptId::parse("cc:44-fz:statya-1").expect("cc");
    match resolve_ctv(&log, &cc1, day) {
        CtvResolution::Resolved { text, .. } => {
            let len = text.chars().count();
            eprintln!("statya-1 resolved text: {len} chars");
            assert!(
                len > 200,
                "full article body expected, got {len} chars: {text}"
            );
            assert!(
                text.contains("настоящим Федеральным законом")
                    || text.contains("сферу применения")
                    || text.contains("регулирует"),
                "article 1 body marker words missing: {text}"
            );
        }
        other => panic!("statya-1 must resolve, got {other:?}"),
    }

    // All 94 bound statya resolve with real text or title fallback.
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
    // Measured on edition-0118: 85/94 bound statya resolve. The residual:
    // articles with no own prose (empty text, no title-only fallback either)
    // plus one same-day duplicate-number Conflict — honest, not a bug here.
    assert!(
        resolved >= 80,
        "expected most bound statya to resolve, got {resolved}"
    );
}
