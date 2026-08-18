//! Article body extraction: text between a hierarchy marker and the next
//! marker (M170 S01 T01). Bounded: structural observation only — no legal
//! interpretation, no citation authority. `ProviderComment` blocks never
//! contribute; empty bodies are skipped, not invented.

use ln_decode::article_body::{collect_marker_bodies, MarkerBody};
use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};
use ln_decode::hierarchy::extract_hierarchy;

fn block(style: ParagraphStyle, text: &str, _offset: usize) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:article-body").unwrap(),
            SourceSpan::try_new(10, 900).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("block")
}

/// Build blocks with running offsets so spans stay valid.
struct BlockBuilder {
    offset: usize,
}

impl BlockBuilder {
    fn new() -> Self {
        Self { offset: 0 }
    }
    fn push(&mut self, style: ParagraphStyle, text: &str) -> ParsedBlock {
        let b = block(style, text, self.offset);
        self.offset += text.len() + 1;
        b
    }
}

#[test]
fn body_collects_text_until_next_marker() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Глава 1. Общие положения"),
        bb.push(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        bb.push(
            ParagraphStyle::BodyText,
            "Настоящий Федеральный закон регулирует отношения,",
        ),
        bb.push(
            ParagraphStyle::BodyText,
            "возникающие в сфере закупок товаров, работ, услуг.",
        ),
        bb.push(
            ParagraphStyle::Heading,
            "Статья 2. Определение законодательства",
        ),
        bb.push(
            ParagraphStyle::BodyText,
            "Законодательство о контрактной системе основано на положениях Конституции.",
        ),
    ];
    let bodies = collect_marker_bodies(&blocks);
    let statya_1 = bodies
        .iter()
        .find(|b: &&MarkerBody| b.level() == "Statya" && b.number() == "1")
        .expect("statya 1 body");
    let text = statya_1.body();
    assert!(text.contains("регулирует отношения"), "{text}");
    assert!(text.contains("возникающие в сфере закупок"), "{text}");
    assert!(!text.contains("Статья 2"), "body stops before next marker");
    assert!(!text.contains("Конституции"), "no leakage from statya 2");
}

#[test]
fn provider_comments_never_contribute() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Сфера"),
        bb.push(ParagraphStyle::ProviderComment, "ГАРАНТ: примечание"),
        bb.push(ParagraphStyle::BodyText, "Реальный текст статьи."),
    ];
    let bodies = collect_marker_bodies(&blocks);
    let body = bodies.first().expect("one body");
    assert!(body.body().contains("Реальный текст"));
    assert!(!body.body().contains("ГАРАНТ"), "provider comment excluded");
}

#[test]
fn empty_body_is_skipped_not_invented() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Заголовок"),
        bb.push(ParagraphStyle::Heading, "Статья 2. Заголовок"),
        bb.push(ParagraphStyle::BodyText, "Текст второй статьи."),
    ];
    let bodies = collect_marker_bodies(&blocks);
    // Contract: markers with no body block before the next marker are still
    // emitted with an empty body — the consumer (build_text_log_from_articles)
    // falls back to the title; nothing is invented here.
    assert_eq!(bodies.len(), 2);
    let s1 = bodies.iter().find(|b| b.number() == "1").expect("statya 1");
    assert_eq!(s1.body(), "", "empty body stays empty");
    let s2 = bodies.iter().find(|b| b.number() == "2").expect("statya 2");
    assert!(s2.body().contains("Текст второй статьи"));
}

#[test]
fn glava_and_statya_bodies_are_separate_entries() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Глава 1. Общие"),
        bb.push(ParagraphStyle::BodyText, "Текст главы перед статьёй."),
        bb.push(ParagraphStyle::Heading, "Статья 1. Первая"),
        bb.push(ParagraphStyle::BodyText, "Текст статьи."),
    ];
    let bodies = collect_marker_bodies(&blocks);
    let glava = bodies.iter().find(|b| b.level() == "Glava").expect("glava");
    assert!(glava.body().contains("Текст главы"), "{}", glava.body());
}

#[test]
fn title_is_preserved_for_events() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        bb.push(ParagraphStyle::BodyText, "Текст."),
    ];
    let bodies = collect_marker_bodies(&blocks);
    assert_eq!(bodies[0].title(), Some("Сфера применения"));
}

#[test]
fn extract_hierarchy_still_recognizes_builder_blocks() {
    // sanity: the synthetic blocks produce markers through the real extractor
    let mut bb = BlockBuilder::new();
    let blocks = [
        bb.push(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        bb.push(ParagraphStyle::BodyText, "Текст."),
    ];
    assert!(extract_hierarchy(&blocks[0]).is_some());
    assert!(extract_hierarchy(&blocks[1]).is_none());
}

// ─── M170 S01 T01: full article texts with nested sub-markers (contract) ────

use ln_decode::article_body::collect_article_texts;
use ln_decode::structural_profile::{GroupProfile, StructuralProfile};

/// Embedded federal_law@v1 profile (M171 S01 T03: profile-driven bounds).
fn federal_law() -> GroupProfile {
    let profile = StructuralProfile::embedded().expect("embedded kb-ontology.yaml");
    profile
        .group("federal_law@v1")
        .expect("federal_law@v1 group")
        .clone()
}

/// Embedded departmental_order profile: unit=punkt, subunit-text=primechanie.
fn departmental_order() -> GroupProfile {
    let profile = StructuralProfile::embedded().expect("embedded kb-ontology.yaml");
    profile
        .group("departmental_order")
        .expect("departmental_order group")
        .clone()
}

/// Embedded government_resolution profile: unit=punkt (dot style "."),
/// container=prilozhenie (surface).
fn government_resolution() -> GroupProfile {
    let profile = StructuralProfile::embedded().expect("embedded kb-ontology.yaml");
    profile
        .group("government_resolution")
        .expect("government_resolution group")
        .clone()
}

/// Embedded court_practice profile: text-only, no structure.
fn court_practice() -> GroupProfile {
    let profile = StructuralProfile::embedded().expect("embedded kb-ontology.yaml");
    profile
        .group("court_practice")
        .expect("court_practice group")
        .clone()
}

#[test]
fn article_text_accumulates_nested_markers() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        bb.push(ParagraphStyle::BodyText, "Общая часть статьи."),
        bb.push(ParagraphStyle::BodyText, "1) подпункт первый;"),
        bb.push(ParagraphStyle::BodyText, "2) подпункт второй;"),
        bb.push(ParagraphStyle::Heading, "Статья 2. Другая"),
        bb.push(ParagraphStyle::BodyText, "Текст второй."),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(articles.len(), 2);
    let a1 = &articles[0];
    assert!(a1.text().contains("Общая часть"), "{}", a1.text());
    assert!(a1.text().contains("подпункт первый"), "{}", a1.text());
    assert!(a1.text().contains("подпункт второй"), "{}", a1.text());
    assert!(!a1.text().contains("Текст второй"), "stops at next statya");
}

#[test]
fn glava_boundary_ends_article_accumulation() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Первая"),
        bb.push(ParagraphStyle::BodyText, "Текст первой."),
        bb.push(ParagraphStyle::Heading, "Глава 2. Новая"),
        bb.push(ParagraphStyle::BodyText, "Текст главы не входит в статью."),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(articles.len(), 1);
    assert!(!articles[0].text().contains("Текст главы"));
}

#[test]
fn provider_comment_excluded_from_article_text() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Первая"),
        bb.push(ParagraphStyle::ProviderComment, "ГАРАНТ: комментарий"),
        bb.push(ParagraphStyle::BodyText, "Текст."),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert!(articles[0].text().contains("Текст."));
    assert!(!articles[0].text().contains("ГАРАНТ"));
}

#[test]
fn statya_marker_line_not_in_article_text() {
    // Contract: the marker line "Статья N. …" never enters ArticleText::text;
    // the marker title is stored separately.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        bb.push(
            ParagraphStyle::BodyText,
            "Настоящий закон регулирует отношения.",
        ),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(articles.len(), 1);
    let a1 = &articles[0];
    assert_eq!(a1.number(), "1");
    assert_eq!(a1.title(), Some("Сфера применения"));
    assert!(a1.text().contains("Настоящий закон"), "{}", a1.text());
    assert!(
        !a1.text().contains("Статья"),
        "marker line must not leak into text: {}",
        a1.text()
    );
    assert!(
        !a1.text().contains("Сфера применения"),
        "title lives separately: {}",
        a1.text()
    );
}

#[test]
fn razdel_boundary_ends_article_accumulation() {
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Первая"),
        bb.push(ParagraphStyle::BodyText, "Текст первой статьи."),
        bb.push(ParagraphStyle::Heading, "Раздел II. Особенная часть"),
        bb.push(
            ParagraphStyle::BodyText,
            "Текст раздела не входит в статью.",
        ),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(articles.len(), 1);
    assert!(articles[0].text().contains("Текст первой статьи"));
    assert!(
        !articles[0].text().contains("Текст раздела"),
        "Razdel breaks accumulation"
    );
    assert!(
        !articles[0].text().contains("Особенная часть"),
        "Razdel marker line excluded"
    );
}

#[test]
fn paragraph_section_boundary_ends_article_accumulation() {
    // "§" markers (Paragraph level) also break accumulation.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Первая"),
        bb.push(ParagraphStyle::BodyText, "Текст первой статьи."),
        bb.push(ParagraphStyle::Heading, "§ 1. Применение к отношениям"),
        bb.push(
            ParagraphStyle::BodyText,
            "Текст параграфа не входит в статью.",
        ),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(articles.len(), 1);
    assert!(articles[0].text().contains("Текст первой статьи"));
    assert!(
        !articles[0].text().contains("Текст параграфа"),
        "Paragraph (§) breaks accumulation"
    );
    assert!(
        !articles[0].text().contains("Применение к отношениям"),
        "Paragraph marker line excluded"
    );
}

#[test]
fn chast_marker_line_belongs_to_article_text() {
    // Nested sub-markers (chast/punkt/podpunkt) ARE part of the article text.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Первая"),
        bb.push(ParagraphStyle::BodyText, "1. Часть первая"),
        bb.push(ParagraphStyle::BodyText, "Текст части."),
        bb.push(ParagraphStyle::BodyText, "1) пункт первый;"),
        bb.push(ParagraphStyle::BodyText, "Текст пункта."),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(articles.len(), 1);
    let text = articles[0].text();
    assert!(text.contains("Часть первая"), "{text}");
    assert!(text.contains("Текст части"), "{text}");
    assert!(text.contains("пункт первый"), "{text}");
    assert!(text.contains("Текст пункта"), "{text}");
}

#[test]
fn empty_statya_emitted_with_empty_text_fail_closed() {
    // Contract: no title-fallback masquerade — a statya with no body blocks
    // before the next marker keeps an empty text; the caller decides.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 1. Пустая"),
        bb.push(ParagraphStyle::Heading, "Статья 2. Содержательная"),
        bb.push(ParagraphStyle::BodyText, "Текст второй статьи."),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(articles.len(), 2);
    assert_eq!(
        articles[0].text(),
        "",
        "empty body stays empty (fail-closed)"
    );
    assert_eq!(articles[0].title(), Some("Пустая"));
    assert!(articles[1].text().contains("Текст второй статьи"));
}

// ─── M171 S01 T03: profile-driven boundaries (TDD contract) ───────────────

/// M170 legacy behavior as reference: statya starts an article; Glava/Razdel/
/// Paragraph reset accumulation; nested sub-markers (chast/punkt/podpunkt)
/// belong to the owning article; ProviderComment never contributes.
fn legacy_collect_article_texts(blocks: &[ParsedBlock]) -> Vec<(String, Option<String>, String)> {
    fn is_boundary(level: &str) -> bool {
        matches!(level, "Glava" | "Razdel" | "Paragraph")
    }
    fn is_statya(level: &str) -> bool {
        level == "Statya"
    }
    fn append(target: &mut String, line: &str) {
        if target.is_empty() {
            target.push_str(line);
        } else {
            target.push('\n');
            target.push_str(line);
        }
    }
    let mut out: Vec<(String, Option<String>, String)> = Vec::new();
    let mut current: Option<usize> = None;
    for block in blocks {
        if block.style() == ParagraphStyle::ProviderComment {
            continue;
        }
        if let Some(node) = extract_hierarchy(block) {
            let level = node.level().as_str();
            if is_statya(level) {
                out.push((
                    node.number().to_owned(),
                    node.title().map(str::to_owned),
                    String::new(),
                ));
                current = Some(out.len() - 1);
                continue;
            }
            if is_boundary(level) {
                current = None;
                continue;
            }
            if let Some(idx) = current {
                let line = block.text().trim();
                if !line.is_empty() {
                    append(&mut out[idx].2, line);
                }
            }
            continue;
        }
        let text = block.text().trim();
        if text.is_empty() {
            continue;
        }
        if let Some(idx) = current {
            append(&mut out[idx].2, text);
        }
    }
    out
}

#[test]
fn federal_law_profile_is_bitwise_equivalent_to_legacy_collector() {
    // R8-14 regression anchor: the profile-driven collector must reproduce
    // the M170 hardcoded is_statya/is_boundary behavior bit-for-bit for
    // federal_law@v1 — articles own nested sub-marker lines, boundaries
    // (Glava/Razdel/Paragraph) reset, ProviderComment is excluded.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Глава 1. Общие положения"),
        bb.push(ParagraphStyle::BodyText, "Текст главы."),
        bb.push(ParagraphStyle::Heading, "Статья 1. Сфера применения"),
        bb.push(
            ParagraphStyle::BodyText,
            "Настоящий закон регулирует отношения,",
        ),
        bb.push(ParagraphStyle::BodyText, "возникающие в сфере закупок."),
        bb.push(ParagraphStyle::BodyText, "1. Часть первая"),
        bb.push(ParagraphStyle::BodyText, "Текст части."),
        bb.push(ParagraphStyle::BodyText, "1) пункт первый;"),
        bb.push(ParagraphStyle::BodyText, "2) пункт второй;"),
        bb.push(ParagraphStyle::ProviderComment, "ГАРАНТ: комментарий"),
        bb.push(ParagraphStyle::Heading, "Статья 2. Другая"),
        bb.push(ParagraphStyle::BodyText, "Текст второй."),
        bb.push(ParagraphStyle::Heading, "Раздел II. Особенная часть"),
        bb.push(ParagraphStyle::BodyText, "Текст раздела."),
        bb.push(ParagraphStyle::Heading, "§ 1. Параграф"),
        bb.push(ParagraphStyle::BodyText, "Текст параграфа."),
    ];

    let legacy_out = legacy_collect_article_texts(&blocks);
    let profile_out = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(
        legacy_out.len(),
        profile_out.len(),
        "article count must match legacy"
    );
    for (l, p) in legacy_out.iter().zip(profile_out.iter()) {
        assert_eq!(l.0, p.number(), "number mismatch");
        assert_eq!(l.1.as_deref(), p.title(), "title mismatch");
        assert_eq!(l.2, p.text(), "text must be bitwise identical");
    }
}

#[test]
fn departmental_order_punkt_bodies_collect_until_next_unit() {
    // unit=punkt: punkt bodies run until the next unit (or container);
    // podpunkt prose belongs to the owning punkt body.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::BodyText, "1) пункт первый"),
        bb.push(ParagraphStyle::BodyText, "Текст первого пункта."),
        bb.push(ParagraphStyle::BodyText, "а) подпункт первого;"),
        bb.push(ParagraphStyle::BodyText, "Текст подпункта."),
        bb.push(ParagraphStyle::BodyText, "2) пункт второй"),
        bb.push(ParagraphStyle::BodyText, "Текст второго пункта."),
    ];
    let bodies = collect_article_texts(&departmental_order(), &blocks);
    assert_eq!(bodies.len(), 2);
    let p1 = &bodies[0];
    assert_eq!(p1.number(), "1");
    assert!(p1.text().contains("Текст первого пункта"), "{}", p1.text());
    assert!(p1.text().contains("подпункт первого"), "{}", p1.text());
    assert!(p1.text().contains("Текст подпункта"), "{}", p1.text());
    assert!(
        !p1.text().contains("Текст второго пункта"),
        "body stops at next punkt: {}",
        p1.text()
    );
    let p2 = &bodies[1];
    assert_eq!(p2.number(), "2");
    assert!(p2.text().contains("Текст второго пункта"), "{}", p2.text());
}

#[test]
fn note_not_in_punkt_body_subunit_text() {
    // primechanie is subunit-text: the note marker line and its text never
    // join the owning punkt body ("Примечание" is a structural-only surface
    // marker, R8-09; extract_hierarchy has no level for it).
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::BodyText, "1) пункт первый"),
        bb.push(ParagraphStyle::BodyText, "Текст пункта."),
        bb.push(ParagraphStyle::BodyText, "Примечание. Сноска к приказу."),
        bb.push(ParagraphStyle::BodyText, "2) пункт второй"),
        bb.push(ParagraphStyle::BodyText, "Текст второго пункта."),
    ];
    let bodies = collect_article_texts(&departmental_order(), &blocks);
    assert_eq!(bodies.len(), 2);
    let p1 = &bodies[0];
    assert!(p1.text().contains("Текст пункта"), "{}", p1.text());
    assert!(
        !p1.text().contains("Примечание"),
        "note must not enter the punkt body: {}",
        p1.text()
    );
    assert!(
        !p1.text().contains("Сноска"),
        "note text must not enter the punkt body: {}",
        p1.text()
    );
    let p2 = &bodies[1];
    assert!(p2.text().contains("Текст второго пункта"), "{}", p2.text());
    assert!(
        !p2.text().contains("Примечание"),
        "note must not leak into the next punkt: {}",
        p2.text()
    );
}

#[test]
fn prilozhenie_container_resets_accumulation() {
    // prilozhenie is a container recognized by its surface marker: the annex
    // region is not part of any punkt body.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::BodyText, "1) пункт первый"),
        bb.push(ParagraphStyle::BodyText, "Текст пункта."),
        bb.push(ParagraphStyle::BodyText, "Приложение N 1"),
        bb.push(ParagraphStyle::BodyText, "Форма заявки."),
    ];
    let bodies = collect_article_texts(&departmental_order(), &blocks);
    assert_eq!(bodies.len(), 1);
    assert!(bodies[0].text().contains("Текст пункта"));
    assert!(
        !bodies[0].text().contains("Приложение"),
        "{}",
        bodies[0].text()
    );
    assert!(
        !bodies[0].text().contains("Форма заявки"),
        "{}",
        bodies[0].text()
    );
}

#[test]
fn text_only_profile_collects_nothing() {
    // court_practice is text-only: numbered lists are never structure
    // (R8-05 hostile case) — the collector emits no unit bodies at all.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::BodyText, "1. Комиссия решила"),
        bb.push(ParagraphStyle::BodyText, "1.1. Рекомендовать заказчику"),
        bb.push(ParagraphStyle::BodyText, "1.1.1. Принять меры"),
        bb.push(ParagraphStyle::BodyText, "1.1.1.1. Уведомить стороны"),
    ];
    let bodies = collect_article_texts(&court_practice(), &blocks);
    assert!(bodies.is_empty(), "text-only profile collects nothing");
}

#[test]
fn undeclared_marker_level_fails_closed_to_boundary() {
    // A marker level not declared in the profile's ladder is a fail-closed
    // boundary: accumulation stops and the region never joins a unit body.
    // departmental_order declares punkt/podpunkt but no chast — a "1. Часть"
    // block (Chast level) must reset, not leak into the preceding punkt.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::BodyText, "1) пункт первый"),
        bb.push(ParagraphStyle::BodyText, "Текст пункта."),
        bb.push(ParagraphStyle::BodyText, "1. Часть вне лестницы"),
        bb.push(ParagraphStyle::BodyText, "Текст части."),
    ];
    let bodies = collect_article_texts(&departmental_order(), &blocks);
    assert_eq!(bodies.len(), 1);
    assert!(bodies[0].text().contains("Текст пункта"));
    assert!(
        !bodies[0].text().contains("Часть вне лестницы"),
        "{}",
        bodies[0].text()
    );
    assert!(
        !bodies[0].text().contains("Текст части"),
        "{}",
        bodies[0].text()
    );
}

#[test]
fn government_resolution_dot_style_punkt_units_via_group_style() {
    // PP "1." points decode as Chast (global decode catalog), which the
    // government_resolution ladder does not declare — the group's own dot
    // style reclassifies them as punkt units (R8-04: group number styles
    // are authoritative). federal_law@v1 declares all seven decode levels,
    // so this fallback never fires for it (bitwise anchor preserved).
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::BodyText, "1. Утвердить прилагаемые:"),
        bb.push(ParagraphStyle::BodyText, "Положение о системе."),
        bb.push(ParagraphStyle::BodyText, "2. Установить, что:"),
        bb.push(ParagraphStyle::BodyText, "Требование действует."),
    ];
    let bodies = collect_article_texts(&government_resolution(), &blocks);
    assert_eq!(bodies.len(), 2, "dot-style points must be punkt units");
    assert_eq!(bodies[0].number(), "1");
    assert_eq!(bodies[0].title(), Some("Утвердить прилагаемые:"));
    assert!(
        bodies[0].text().contains("Положение о системе"),
        "{}",
        bodies[0].text()
    );
    assert_eq!(bodies[1].number(), "2");
    assert!(
        bodies[1].text().contains("Требование действует"),
        "{}",
        bodies[1].text()
    );
}
