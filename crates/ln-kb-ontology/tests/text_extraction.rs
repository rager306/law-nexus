//! build_text_log_from_markers: extract titles from markers → TextVersionLog.
//! Wires resolve_ctv into the real assembly pipeline (KBO-R051).

use ln_kb_ontology::domain::{
    build_text_log_from_articles, build_text_log_from_markers, resolve_ctv, CtvResolution,
    HierarchyBinding, HierarchyMap, HierarchyMarker,
};
use ln_temporal::domain::ComponentConceptId;

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn marker(level: &str, number: &str, title: Option<&str>) -> HierarchyMarker {
    HierarchyMarker::try_new(None, level, number, title).expect("marker")
}

fn bind(map: &mut HierarchyMap, level: &str, number: &str, id: &str) {
    map.register(HierarchyBinding::try_new(None, level, number, cc(id)).expect("bind"))
        .expect("reg");
}

#[test]
fn text_log_from_titled_bound_markers() {
    let mut map = HierarchyMap::empty();
    bind(&mut map, "statya", "1", "cc:art-1");
    bind(&mut map, "statya", "2", "cc:art-2");

    let markers = vec![
        marker("statya", "1", Some("Общие положения")),
        marker("statya", "2", Some("Основные понятия")),
    ];

    let log = build_text_log_from_markers(&map, &markers, 80_000, "amendingact:c2-oracle-edition");

    assert_eq!(log.events().len(), 2);

    match resolve_ctv(&log, &cc("cc:art-1"), 80_000) {
        CtvResolution::Resolved { text } => assert_eq!(text, "Общие положения"),
        other => panic!("expected Resolved, got {other:?}"),
    }
    match resolve_ctv(&log, &cc("cc:art-2"), 80_000) {
        CtvResolution::Resolved { text } => assert_eq!(text, "Основные понятия"),
        other => panic!("expected Resolved, got {other:?}"),
    }
}

#[test]
fn untitled_markers_produce_no_text_events() {
    let mut map = HierarchyMap::empty();
    bind(&mut map, "statya", "1", "cc:art-1");

    let markers = vec![marker("statya", "1", None)];

    let log = build_text_log_from_markers(&map, &markers, 80_000, "amendingact:c2-oracle-edition");
    assert!(log.events().is_empty());
}

#[test]
fn unknown_markers_produce_no_text_events() {
    let map = HierarchyMap::empty();

    let markers = vec![marker("statya", "99", Some("Unknown article"))];

    let log = build_text_log_from_markers(&map, &markers, 80_000, "amendingact:c2-oracle-edition");
    assert!(log.events().is_empty());
}

#[test]
fn resolve_at_earlier_day_is_unknown() {
    let mut map = HierarchyMap::empty();
    bind(&mut map, "statya", "1", "cc:art-1");

    let markers = vec![marker("statya", "1", Some("Title at day 100"))];

    let log = build_text_log_from_markers(&map, &markers, 100, "amendingact:c2-oracle-edition");

    assert!(matches!(
        resolve_ctv(&log, &cc("cc:art-1"), 99),
        CtvResolution::Unknown
    ));
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:art-1"), 100),
        CtvResolution::Resolved { .. }
    ));
}

// ─── M170 S01 T02: TextVersionLog from full article bodies ──────────────────

// build_text_log_from_articles + resolve_ctv/CtvResolution/cc reuse the
// imports at the top of this file.

/// Mirror of ln-decode MarkerBody for the ontology boundary: the ontology
/// consumes plain data, it does not depend on ln-decode.
struct Article<'a> {
    level: &'a str,
    number: &'a str,
    title: Option<&'a str>,
    body: &'a str,
}

#[test]
fn full_body_becomes_text_event_and_resolves() {
    let mut map = ln_kb_ontology::domain::HierarchyMap::empty();
    map.register(
        ln_kb_ontology::domain::HierarchyBinding::try_new(None, "statya", "1", cc("cc:t:statya-1"))
            .expect("bind"),
    )
    .expect("reg");

    let articles = [Article {
        level: "statya",
        number: "1",
        title: Some("Сфера применения"),
        body: "Настоящий закон регулирует отношения в сфере закупок. Полный текст статьи.",
    }];
    let day = 80000i64;
    let log = build_text_log_from_articles(
        &map,
        articles
            .iter()
            .map(|a| (a.level, a.number, a.title, a.body)),
        day,
        "amendingact:c2-oracle-edition",
    );

    match resolve_ctv(&log, &cc("cc:t:statya-1"), day) {
        CtvResolution::Resolved { text, .. } => {
            assert!(text.contains("Настоящий закон регулирует"), "{text}");
            assert!(text.contains("Полный текст"), "{text}");
        }
        other => panic!("expected Resolved, got {other:?}"),
    }
}

#[test]
fn empty_body_falls_back_to_title() {
    let mut map = ln_kb_ontology::domain::HierarchyMap::empty();
    map.register(
        ln_kb_ontology::domain::HierarchyBinding::try_new(None, "statya", "2", cc("cc:t:statya-2"))
            .expect("bind"),
    )
    .expect("reg");

    let articles = [Article {
        level: "statya",
        number: "2",
        title: Some("Заголовок только"),
        body: "",
    }];
    let day = 80000i64;
    let log = build_text_log_from_articles(
        &map,
        articles
            .iter()
            .map(|a| (a.level, a.number, a.title, a.body)),
        day,
        "amendingact:c2-oracle-edition",
    );
    match resolve_ctv(&log, &cc("cc:t:statya-2"), day) {
        CtvResolution::Resolved { text, .. } => {
            assert!(text.contains("Заголовок только"), "{text}")
        }
        other => panic!("expected Resolved fallback, got {other:?}"),
    }
}

#[test]
fn unbound_article_mints_nothing() {
    let map = ln_kb_ontology::domain::HierarchyMap::empty();
    let articles = [Article {
        level: "statya",
        number: "99",
        title: None,
        body: "текст",
    }];
    let log = build_text_log_from_articles(
        &map,
        articles
            .iter()
            .map(|a| (a.level, a.number, a.title, a.body)),
        80000,
        "amendingact:c2-oracle-edition",
    );
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:t:statya-99"), 80000),
        CtvResolution::Unknown
    ));
}

// ─── M170 S02 T02: text-facet AmendmentEventDraft bridge ────────────────────

use ln_kb_ontology::domain::{changed_article_texts, AmendmentDraftOp};

#[test]
fn changed_text_becomes_text_facet_draft() {
    let before = [(
        "statya",
        "3",
        Some("Законодательство о контрактной системе"),
        "Старый текст статьи.",
    )];
    let after = [(
        "statya",
        "3",
        Some("Законодательство о контрактной системе"),
        "Новый текст статьи после правки.",
    )];
    let drafts = changed_article_texts(
        before.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        after.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "expr:ru:federal:zakon:2013-04-05:44-fz:2013-07-02",
    )
    .expect("drafts");
    assert_eq!(drafts.len(), 1);
    assert_eq!(drafts[0].op, AmendmentDraftOp::Attach);
    assert_eq!(drafts[0].facet, "text");
    assert_eq!(drafts[0].level, "statya");
    assert_eq!(drafts[0].number, "3");
    assert_eq!(drafts[0].evidence_class, "hypothesized_from_oracle_diff");
    assert!(drafts[0].provenance.contains("2013-07-02"));
}

#[test]
fn unchanged_text_yields_no_draft() {
    let same = [("statya", "1", Some("Сфера"), "Одинаковый текст.")];
    let drafts = changed_article_texts(
        same.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        same.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "expr:test:1",
    )
    .expect("drafts");
    assert!(drafts.is_empty());
}

#[test]
fn empty_provenance_fails_closed_text_facet() {
    let before = [("statya", "1", None, "текст")];
    let after = [("statya", "1", None, "другой текст")];
    let err = changed_article_texts(
        before.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        after.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "",
    )
    .expect_err("empty provenance");
    assert!(err.to_string().contains("provenance"));
}

#[test]
fn added_and_removed_articles_reported_as_text_drafts() {
    let before = [("statya", "2", Some("t"), "текст два")];
    let after = [("statya", "5", Some("t"), "новая статья")];
    let drafts = changed_article_texts(
        before.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        after.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "expr:test:1",
    )
    .expect("drafts");
    // removed statya-2 and added statya-5 are structural news surfaced here
    // as text-facet drafts too (facet=text covers presence+wording changes
    // of the same level in this bounded bridge)
    assert_eq!(drafts.len(), 2);
}
