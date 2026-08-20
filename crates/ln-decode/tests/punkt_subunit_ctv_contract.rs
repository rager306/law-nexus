//! KBO-R067 decode layer: the two senses of «punkt» and the unit-mint
//! source (M172-tsa1j7 S01 T02 — locking tests, no behavior change).
//!
//! Contract:
//! - `federal_law@v1`: punkt is a SUBUNIT (D190/D192). Nested chast /
//!   punkt / podpunkt marker lines fold into the owning statya body; a
//!   federal law never emits a separate `ArticleText` per punkt.
//! - `government_resolution` / `departmental_order`: punkt is a UNIT
//!   (M171). Each punkt gets its own `ArticleText`; the marker heading
//!   stays in `title`, never in `text`; podpunkt folds into the owning
//!   punkt; primechanie (subunit-text) is surface-excluded.
//! - The unit role comes from the group profile (YAML `granularity`),
//!   never from a hardcoded level token: the same physical blocks mint
//!   statya units under one profile and punkt units under another
//!   (R8-04: the group's number styles are authoritative).
//! - `collect_marker_bodies` is NOT a CTV source: it cuts a title-sized
//!   fragment at every marker, so a unit body can never be reconstructed
//!   from it.
//!
//! Non-claims: no nested 44-FZ punkt CC (D192), no InForce/Applicable, no
//! lifecycle promotion (ADR-0017 stays [proposed]), no inspect wiring
//! (that composition gap is S02, not decode).

use ln_decode::article_body::{collect_article_texts, collect_marker_bodies};
use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};
use ln_decode::structural_profile::{GroupProfile, StructuralProfile};

fn group(id: &str) -> GroupProfile {
    let profile = StructuralProfile::embedded().expect("embedded kb-ontology.yaml");
    profile
        .group(id)
        .unwrap_or_else(|| panic!("{id} group"))
        .clone()
}

/// Embedded federal_law@v1 profile: granularity statya, punkt = subunit.
fn federal_law() -> GroupProfile {
    group("federal_law@v1")
}

/// Embedded government_resolution profile: granularity punkt (dot style).
fn government_resolution() -> GroupProfile {
    group("government_resolution")
}

/// Embedded departmental_order profile: granularity punkt, subunit-text
/// primechanie.
fn departmental_order() -> GroupProfile {
    group("departmental_order")
}

fn block(style: ParagraphStyle, text: &str, _offset: usize) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:punkt-subunit-ctv").unwrap(),
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

// ─── punkt-as-subunit: federal_law@v1 ──────────────────────────────────────

#[test]
fn federal_law_punkt_is_subunit_and_never_mints_an_article_text() {
    // KBO-R067 layer 1 (article CTV, M170): the emitted unit count equals
    // the statya count even when nested chast/punkt/podpunkt markers are
    // present — a federal law mints ZERO punkt ArticleTexts, and every
    // nested marker line lives inside the owning statya body.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 8. Порядок"),
        bb.push(ParagraphStyle::BodyText, "Вводная часть статьи."),
        bb.push(ParagraphStyle::BodyText, "1. Часть статьи."),
        bb.push(ParagraphStyle::BodyText, "1) пункт части;"),
        bb.push(ParagraphStyle::BodyText, "а) подпункт пункта;"),
        bb.push(ParagraphStyle::Heading, "Статья 9. Контроль"),
        bb.push(ParagraphStyle::BodyText, "1) пункт другой статьи."),
    ];
    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(
        articles.len(),
        2,
        "one ArticleText per statya: chast/punkt/podpunkt markers never mint a unit under federal_law@v1"
    );
    let numbers: Vec<&str> = articles.iter().map(|a| a.number()).collect();
    assert_eq!(numbers, ["8", "9"]);

    let a8 = &articles[0];
    for needle in [
        "Вводная часть статьи.",
        "1. Часть статьи.",
        "1) пункт части;",
        "а) подпункт пункта;",
    ] {
        assert!(
            a8.text().contains(needle),
            "subunit marker must fold into the owning statya body: {}",
            a8.text()
        );
    }
    let a9 = &articles[1];
    assert!(
        a9.text().contains("1) пункт другой статьи."),
        "{}",
        a9.text()
    );
    assert!(
        !a9.text().contains("пункт части"),
        "no leakage across statya bodies: {}",
        a9.text()
    );
}

// ─── punkt-as-unit: government_resolution / departmental_order ─────────────

#[test]
fn government_resolution_punkt_is_unit_with_own_article_text() {
    // KBO-R067 layer 2 (punkt-unit CTV, M171): each dot-style punkt is its
    // own unit; the heading never enters `text`; podpunkt folds into the
    // owning punkt body.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Вводное постановление"),
        bb.push(ParagraphStyle::BodyText, "1. Утвердить правила:"),
        bb.push(ParagraphStyle::BodyText, "Текст первого пункта."),
        bb.push(ParagraphStyle::BodyText, "а) подпункт пункта;"),
        bb.push(ParagraphStyle::BodyText, "2. Вступление в силу:"),
        bb.push(ParagraphStyle::BodyText, "Текст второго пункта."),
    ];
    let articles = collect_article_texts(&government_resolution(), &blocks);
    assert_eq!(articles.len(), 2, "one ArticleText per punkt unit");
    let p1 = &articles[0];
    assert_eq!(p1.number(), "1");
    assert_eq!(p1.title(), Some("Утвердить правила:"));
    assert!(p1.text().contains("Текст первого пункта."), "{}", p1.text());
    assert!(
        p1.text().contains("а) подпункт пункта;"),
        "podpunkt folds into the owning punkt body: {}",
        p1.text()
    );
    assert!(
        !p1.text().contains("Утвердить правила"),
        "marker heading never enters the punkt text: {}",
        p1.text()
    );
    assert!(
        !p1.text().contains("Вводное постановление"),
        "pre-unit prose is not part of any punkt: {}",
        p1.text()
    );
    let p2 = &articles[1];
    assert_eq!(p2.number(), "2");
    assert!(p2.text().contains("Текст второго пункта."), "{}", p2.text());
}

#[test]
fn departmental_order_punkt_is_unit_primechanie_excluded() {
    // KBO-R067 layer 2 for departmental_order: "1)" decodes as Punkt and
    // IS the unit token here; primechanie is subunit-text and its region
    // never joins a punkt body.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::BodyText, "1) пункт первый"),
        bb.push(ParagraphStyle::BodyText, "Текст первого пункта."),
        bb.push(ParagraphStyle::BodyText, "Примечание. Сноска к приказу."),
        bb.push(ParagraphStyle::BodyText, "2) пункт второй"),
        bb.push(ParagraphStyle::BodyText, "Текст второго пункта."),
    ];
    let articles = collect_article_texts(&departmental_order(), &blocks);
    assert_eq!(articles.len(), 2);
    let p1 = &articles[0];
    assert_eq!(p1.number(), "1");
    assert!(p1.text().contains("Текст первого пункта."), "{}", p1.text());
    assert!(
        !p1.text().contains("Примечание") && !p1.text().contains("Сноска"),
        "subunit-text region excluded from the punkt body: {}",
        p1.text()
    );
    let p2 = &articles[1];
    assert_eq!(p2.number(), "2");
    assert!(p2.text().contains("Текст второго пункта."), "{}", p2.text());
}

// ─── mint level comes from the profile, not a hardcoded level ──────────────

#[test]
fn same_blocks_mint_different_units_per_profile() {
    // The same physical blocks: under federal_law@v1 the "1."/"2." lines
    // are chast SUBUNITS folded into statya 7; under government_resolution
    // the same lines are punkt UNITS (the "Статья 7." heading is an
    // undeclared level there and fails closed as a boundary). S02 wiring
    // must take the mint level from the group's YAML granularity — a
    // hardcoded "statya" would silently mint the wrong layer.
    let build = |mut bb: BlockBuilder| {
        vec![
            bb.push(ParagraphStyle::Heading, "Статья 7. Порядок"),
            bb.push(ParagraphStyle::BodyText, "Общее положение."),
            bb.push(ParagraphStyle::BodyText, "1. Первый уровень."),
            bb.push(ParagraphStyle::BodyText, "2. Второй уровень."),
        ]
    };
    let fl_blocks = build(BlockBuilder::new());
    let pp_blocks = build(BlockBuilder::new());

    let fl = collect_article_texts(&federal_law(), &fl_blocks);
    assert_eq!(fl.len(), 1, "federal_law@v1: one statya unit");
    assert_eq!(fl[0].number(), "7");
    for needle in [
        "Общее положение.",
        "1. Первый уровень.",
        "2. Второй уровень.",
    ] {
        assert!(
            fl[0].text().contains(needle),
            "chast lines fold into the owning statya: {}",
            fl[0].text()
        );
    }

    let pp = collect_article_texts(&government_resolution(), &pp_blocks);
    assert_eq!(
        pp.len(),
        2,
        "government_resolution: the same lines are punkt units"
    );
    let numbers: Vec<&str> = pp.iter().map(|a| a.number()).collect();
    assert_eq!(numbers, ["1", "2"]);
    // Under PP the "Статья 7." heading is an undeclared level and fails
    // closed: the pre-unit prose belongs to no punkt, so the first punkt
    // body stays empty until its own marker title is used as fallback.
    assert_eq!(pp[0].title(), Some("Первый уровень."));
    assert_eq!(pp[0].text(), "", "pre-unit prose belongs to no punkt");
}

// ─── collect_marker_bodies is not a CTV source ─────────────────────────────

#[test]
fn collect_marker_bodies_fragments_units_and_is_not_a_ctv_source() {
    // collect_marker_bodies cuts at EVERY marker: nested "1)" lines become
    // separate title-sized fragments and the statya entry loses the punkt
    // prose. A unit body cannot be reconstructed from marker bodies —
    // text-CTV feeds on collect_article_texts unit bodies only.
    let mut bb = BlockBuilder::new();
    let blocks = vec![
        bb.push(ParagraphStyle::Heading, "Статья 8. Порядок"),
        bb.push(ParagraphStyle::BodyText, "Вводная часть."),
        bb.push(ParagraphStyle::BodyText, "1) пункт статьи;"),
        bb.push(ParagraphStyle::BodyText, "Продолжение пункта."),
    ];

    let articles = collect_article_texts(&federal_law(), &blocks);
    assert_eq!(articles.len(), 1);
    let unit_text = articles[0].text();
    for needle in ["Вводная часть.", "1) пункт статьи;", "Продолжение пункта."]
    {
        assert!(unit_text.contains(needle), "unit body: {unit_text}");
    }

    let marker_bodies = collect_marker_bodies(&blocks);
    let statya = marker_bodies
        .iter()
        .find(|m| m.level() == "Statya")
        .expect("statya marker body");
    assert!(
        !statya.body().contains("пункт статьи;"),
        "marker body stops at the first nested marker: {}",
        statya.body()
    );
    assert!(
        marker_bodies
            .iter()
            .any(|m| m.level() == "Punkt" && m.number() == "1"),
        "the nested marker becomes its own fragment entry"
    );
    assert!(
        !marker_bodies.iter().any(|m| m.body() == unit_text),
        "no marker body equals the unit body — marker bodies are fragments, not CTV text"
    );
}
