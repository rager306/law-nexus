//! build_text_log_from_markers: extract titles from markers → TextVersionLog.
//! Wires resolve_ctv into the real assembly pipeline (KBO-R051).

use ln_kb_ontology::domain::{
    build_text_log_from_markers, resolve_ctv, CtvResolution, HierarchyBinding, HierarchyMap,
    HierarchyMarker,
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
