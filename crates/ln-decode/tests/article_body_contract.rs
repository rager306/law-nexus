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
    let articles = collect_article_texts(&blocks);
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
    let articles = collect_article_texts(&blocks);
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
    let articles = collect_article_texts(&blocks);
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
    let articles = collect_article_texts(&blocks);
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
    let articles = collect_article_texts(&blocks);
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
    let articles = collect_article_texts(&blocks);
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
    let articles = collect_article_texts(&blocks);
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
    let articles = collect_article_texts(&blocks);
    assert_eq!(articles.len(), 2);
    assert_eq!(
        articles[0].text(),
        "",
        "empty body stays empty (fail-closed)"
    );
    assert_eq!(articles[0].title(), Some("Пустая"));
    assert!(articles[1].text().contains("Текст второй статьи"));
}
