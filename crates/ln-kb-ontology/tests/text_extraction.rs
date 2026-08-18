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
// M171 S02 T03: diff identity is (level, key_path) — statya-4 and punkt-4
// with the same number never collide, and punkt-4 under different statya
// ladders stay distinct (R8-11 / D192). Tuples are (level, number, path, text).

use ln_kb_ontology::domain::{changed_article_texts, AmendmentDraftOp};

#[test]
fn changed_text_becomes_text_facet_draft() {
    let before = [("statya", "3", None, "Старый текст статьи.")];
    let after = [("statya", "3", None, "Новый текст статьи после правки.")];
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
    assert_eq!(drafts[0].path, None);
    assert_eq!(drafts[0].evidence_class, "hypothesized_from_oracle_diff");
    assert!(drafts[0].provenance.contains("2013-07-02"));
}

#[test]
fn unchanged_text_yields_no_draft() {
    let same = [("statya", "1", None, "Одинаковый текст.")];
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
    let before = [("statya", "2", None, "текст два")];
    let after = [("statya", "5", None, "новая статья")];
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

// ─── M171 S02 T03: (level, key_path) diff identity ────────────────────────────

#[test]
fn same_number_different_levels_do_not_collide() {
    // statya-4 and punkt-4 share the number "4" — the old number-only key
    // would pair punkt-4's text against statya-4's text (R8-11). The
    // (level, key_path) key keeps them apart.
    let before = [
        ("statya", "4", None, "текст статьи 4 (старая)"),
        ("punkt", "4", None, "текст пункта 4 (старая)"),
    ];
    let after = [
        ("statya", "4", None, "текст статьи 4 (НОВАЯ)"),
        ("punkt", "4", None, "текст пункта 4 (старая)"),
    ];
    let drafts = changed_article_texts(
        before.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        after.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "expr:test:1",
    )
    .expect("drafts");
    assert_eq!(drafts.len(), 1, "only statya-4 changed: {drafts:?}");
    assert_eq!(drafts[0].level, "statya");
    assert_eq!(drafts[0].number, "4");
    assert_eq!(drafts[0].op, AmendmentDraftOp::Attach);
}

#[test]
fn same_number_different_paths_do_not_collide() {
    // punkt-4 under statya-93 vs punkt-4 under statya-94: same level and
    // number, different ladder paths — only the statya-93 one changes.
    let before = [
        (
            "punkt",
            "4",
            Some("statya-93/punkt-4"),
            "текст п.4 ст.93 (старая)",
        ),
        (
            "punkt",
            "4",
            Some("statya-94/punkt-4"),
            "текст п.4 ст.94 (старая)",
        ),
    ];
    let after = [
        (
            "punkt",
            "4",
            Some("statya-93/punkt-4"),
            "текст п.4 ст.93 (НОВАЯ)",
        ),
        (
            "punkt",
            "4",
            Some("statya-94/punkt-4"),
            "текст п.4 ст.94 (старая)",
        ),
    ];
    let drafts = changed_article_texts(
        before.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        after.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "expr:test:1",
    )
    .expect("drafts");
    assert_eq!(
        drafts.len(),
        1,
        "only statya-93 punkt-4 changed: {drafts:?}"
    );
    assert_eq!(drafts[0].path.as_deref(), Some("statya-93/punkt-4"));
    assert_eq!(drafts[0].op, AmendmentDraftOp::Attach);
}

#[test]
fn nested_path_carried_into_text_draft() {
    // A nested unit removed between editions keeps its ladder identity.
    let before = [(
        "punkt",
        "4.2",
        Some("statya-93/punkt-4/punkt-4.2"),
        "текст 4.2",
    )];
    let after: [(&str, &str, Option<&str>, &str); 0] = [];
    let drafts = changed_article_texts(
        before.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        after.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "expr:test:1",
    )
    .expect("drafts");
    assert_eq!(drafts.len(), 1);
    assert_eq!(drafts[0].op, AmendmentDraftOp::Detach);
    assert_eq!(drafts[0].level, "punkt");
    assert_eq!(drafts[0].number, "4.2");
    assert_eq!(
        drafts[0].path.as_deref(),
        Some("statya-93/punkt-4/punkt-4.2")
    );
}

#[test]
fn flat_number_matches_flat_path_identity() {
    // Flat marker without a path keys on its number (D192); a flat before
    // item is found by a flat after item with the same number.
    let before = [("statya", "1", None, "текст один")];
    let after = [("statya", "1", None, "текст один")];
    let drafts = changed_article_texts(
        before.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        after.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "expr:test:1",
    )
    .expect("drafts");
    assert!(
        drafts.is_empty(),
        "identical flat texts stay unchanged: {drafts:?}"
    );
}

#[test]
fn flat_does_not_match_path_bound_item() {
    // A flat `punkt 4` (key_path "4") and a ladder `punkt 4`
    // (key_path "statya-93/punkt-4") are different identities — one side
    // changed alone must not leak into the other (fail-closed, no invented
    // pairing across key_path boundaries).
    let before = [("punkt", "4", None, "плоский пункт 4")];
    let after = [("punkt", "4", Some("statya-93/punkt-4"), "вложенный пункт 4")];
    let drafts = changed_article_texts(
        before.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        after.into_iter().map(|(a, b, c, d)| (a, b, c, d as &str)),
        "expr:test:1",
    )
    .expect("drafts");
    // Two separate identities: flat removed (Detach), ladder added (Attach).
    assert_eq!(
        drafts.len(),
        2,
        "flat and ladder identities stay apart: {drafts:?}"
    );
}
