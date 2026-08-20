//! KBO-R067 ontology layer: punkt/subunit text-CTV mint contract vs the
//! M170 article-only CTV (M172-tsa1j7 S01 T02 — locking tests, no
//! resolver change).
//!
//! Contract:
//! - "punkt/subunit Resolved" = a unique Bound CC for which
//!   `resolve_ctv(log, cc, t) == CtvResolution::Resolved { text }` where
//!   `text` is the UNIT body (empty body falls back to the marker title;
//!   unbound markers mint nothing).
//! - The mint level is the group's YAML `granularity` — `statya` for
//!   federal_law@v1 / code, `punkt` for government_resolution /
//!   departmental_order. It is data the wiring (S02 inspect) must read,
//!   never a hardcoded "statya" token.
//! - Fail-closed: units minted at the wrong level bind nothing and
//!   resolve Unknown — never a silent article-CTV.
//! - D192: the 44-FZ fixture registry stays flat (8 glava + 94 statya,
//!   0 punkt). Number+level never mints a nested CC outside the registry;
//!   a nested 44-FZ punkt-CC is a separate bounded wave, not M172.
//! - D187: the Resolved count is the number of unique Resolved CCs —
//!   never `events().len()`; same-day different-text duplicates for one
//!   flat number are Conflict.
//!
//! Non-claims: resolve_ctv is text witnessing, not InForce, not
//! Applicable (`CTV_NON_CLAIMS`); no lifecycle promotion (ADR-0017 stays
//! [proposed]); no inspect/replay wiring (S02/S4).

use std::collections::HashSet;

use ln_kb_ontology::catalog::OntologyCatalog;
use ln_kb_ontology::domain::{
    build_text_log_from_articles, resolve_ctv, CtvResolution, HierarchyBinding, HierarchyMap,
};
use ln_temporal::domain::ComponentConceptId;

/// Tracked fixture registry (kb-hierarchy-registry.yaml): the D192 flat
/// 44-FZ cardinality anchor lives here, not in test data.
const REGISTRY: &str = include_str!("../../../prd/architecture/kb-hierarchy-registry.yaml");
const DAY: i64 = 80_000;
const PROV: &str = "amendingact:m172-contract";

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn bind(map: &mut HierarchyMap, level: &str, number: &str, id: &str) {
    map.register(HierarchyBinding::try_new(None, level, number, cc(id)).expect("bind"))
        .expect("reg");
}

/// (level, number, title, body) — the plain-tuple surface the ontology
/// consumes; it never depends on ln-decode (KBO-R030).
type Unit<'a> = (&'a str, &'a str, Option<&'a str>, &'a str);

// ─── mint level is YAML granularity data ───────────────────────────────────

#[test]
fn mint_level_is_group_granularity_data_not_a_hardcoded_statya() {
    // The level token handed to build_text_log_from_articles must come
    // from the group's YAML `granularity`. Pinning the catalog data here
    // is the decode x ontology lock: S02 inspect wiring reads this field;
    // a hardcoded "statya" on government_resolution would mint the wrong
    // layer (the named composition gap this contract freezes).
    let catalog = OntologyCatalog::embedded().expect("yaml");
    let granularity = |id: &str| {
        catalog
            .document_group(id)
            .expect("group")
            .granularity
            .clone()
    };
    assert_eq!(granularity("federal_law@v1").as_deref(), Some("statya"));
    assert_eq!(granularity("code").as_deref(), Some("statya"));
    assert_eq!(
        granularity("government_resolution").as_deref(),
        Some("punkt")
    );
    assert_eq!(granularity("departmental_order").as_deref(), Some("punkt"));
    assert!(
        granularity("court_practice").is_none(),
        "text-only group has no granularity"
    );
}

// ─── punkt-as-unit Resolved definition ─────────────────────────────────────

#[test]
fn punkt_unit_body_resolves_as_unit_text_not_title() {
    // "punkt/subunit Resolved": the witnessed text is the punkt unit body,
    // not the marker heading (PP_60 shape: fixture CC per punkt, unit
    // body text, edition day).
    let mut map = HierarchyMap::empty();
    bind(&mut map, "punkt", "1", "cc:pp-60:punkt-1");
    bind(&mut map, "punkt", "2", "cc:pp-60:punkt-2");
    let units: [Unit; 2] = [
        (
            "punkt",
            "1",
            Some("Утвердить правила"),
            "Текст первого пункта целиком.",
        ),
        (
            "punkt",
            "2",
            Some("Вступление в силу"),
            "Текст второго пункта целиком.",
        ),
    ];
    let log = build_text_log_from_articles(&map, units, DAY, PROV);
    for (id, expected) in [
        ("cc:pp-60:punkt-1", "Текст первого пункта целиком."),
        ("cc:pp-60:punkt-2", "Текст второго пункта целиком."),
    ] {
        match resolve_ctv(&log, &cc(id), DAY) {
            CtvResolution::Resolved { text } => {
                assert_eq!(text, expected, "resolved text is the unit body");
                assert_ne!(text, "Утвердить правила", "never the heading");
            }
            other => panic!("expected Resolved for {id}, got {other:?}"),
        }
    }
}

#[test]
fn empty_punkt_body_falls_back_to_title() {
    let mut map = HierarchyMap::empty();
    bind(&mut map, "punkt", "3", "cc:pp-60:punkt-3");
    let units: [Unit; 1] = [("punkt", "3", Some("Заголовок пустого пункта"), "")];
    let log = build_text_log_from_articles(&map, units, DAY, PROV);
    match resolve_ctv(&log, &cc("cc:pp-60:punkt-3"), DAY) {
        CtvResolution::Resolved { text } => {
            assert_eq!(text, "Заголовок пустого пункта", "title fallback");
        }
        other => panic!("expected Resolved, got {other:?}"),
    }
}

#[test]
fn unbound_punkt_mints_nothing() {
    // Unbound = no event, Unknown downstream — never an invented CC.
    let mut map = HierarchyMap::empty();
    bind(&mut map, "punkt", "1", "cc:pp-60:punkt-1");
    let units: [Unit; 2] = [
        ("punkt", "1", Some("Первый"), "Текст первого пункта."),
        (
            "punkt",
            "99",
            Some("Нет в реестре"),
            "Текст несуществующего пункта.",
        ),
    ];
    let log = build_text_log_from_articles(&map, units, DAY, PROV);
    assert_eq!(log.events().len(), 1, "only the Bound punkt mints an event");
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:pp-60:punkt-1"), DAY),
        CtvResolution::Resolved { .. }
    ));
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:pp-60:punkt-99"), DAY),
        CtvResolution::Unknown
    ));
}

// ─── fail-closed wrong-level mint (Q5/Q7 hostile) ──────────────────────────

#[test]
fn wrong_level_statya_labels_against_punkt_map_fail_closed() {
    // Anti-regression for the S02 wiring gap: the SAME punkt unit bodies
    // signed "statya" (the current inspect hardcode) against a punkt-only
    // map bind NOTHING — 0 events, Unknown downstream. Fail-closed, not a
    // silent article-CTV on the wrong layer.
    let mut map = HierarchyMap::empty();
    bind(&mut map, "punkt", "1", "cc:pp-60:punkt-1");
    bind(&mut map, "punkt", "2", "cc:pp-60:punkt-2");
    let mislabeled: [Unit; 2] = [
        ("statya", "1", Some("Первый"), "Текст первого пункта."),
        ("statya", "2", Some("Второй"), "Текст второго пункта."),
    ];
    let log = build_text_log_from_articles(&map, mislabeled, DAY, PROV);
    assert_eq!(log.events().len(), 0, "wrong-level mint binds nothing");
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:pp-60:punkt-1"), DAY),
        CtvResolution::Unknown
    ));
}

// ─── D192: federal_law punkt is a subunit, never a nested CC ───────────────

#[test]
fn federal_law_punkt_subunit_never_mints_a_nested_cc() {
    // 44-FZ registry shape: statya-only bindings. Punkt-level tuples for
    // the same numbers mint NOTHING — number+level is not a CC outside
    // the registry (D192), while the statya-level M170 path stays alive.
    let mut map = HierarchyMap::empty();
    bind(&mut map, "statya", "1", "cc:44-fz:statya-1");
    bind(&mut map, "statya", "2", "cc:44-fz:statya-2");

    let nested: [Unit; 2] = [
        (
            "punkt",
            "1",
            Some("Пункт статьи 1"),
            "Пункт внутри статьи 1.",
        ),
        (
            "punkt",
            "2",
            Some("Пункт статьи 2"),
            "Пункт внутри статьи 2.",
        ),
    ];
    let nested_log = build_text_log_from_articles(&map, nested, DAY, PROV);
    assert_eq!(
        nested_log.events().len(),
        0,
        "nested punkt-CC is a non-claim: the flat key never binds to a statya CC"
    );

    let articles: [Unit; 2] = [
        ("statya", "1", Some("Сфера"), "Полный текст статьи 1."),
        ("statya", "2", Some("Определения"), "Полный текст статьи 2."),
    ];
    let log = build_text_log_from_articles(&map, articles, DAY, PROV);
    assert!(
        matches!(
            resolve_ctv(&log, &cc("cc:44-fz:statya-1"), DAY),
            CtvResolution::Resolved { .. }
        ),
        "M170 article CTV stays alive"
    );
}

#[test]
fn registry_44fz_stays_flat_8_glava_94_statya_0_punkt() {
    // Tracked-registry lock: the 44-FZ section holds 8 glava + 94 statya
    // and zero punkt bindings. Changing this cardinality is a deliberate
    // D192 wave, not quiet drift this contract may absorb.
    let (mut glava, mut statya, mut punkt) = (0usize, 0usize, 0usize);
    for line in REGISTRY.lines() {
        if !line.contains("law_2013-04-05_44-fz") {
            continue;
        }
        if line.contains("level: glava") {
            glava += 1;
        } else if line.contains("level: statya") {
            statya += 1;
        } else if line.contains("level: punkt") {
            punkt += 1;
        }
    }
    assert_eq!(
        (glava, statya, punkt),
        (8, 94, 0),
        "D192 registry anchor: flat 44-FZ, no nested punkt bindings"
    );
}

// ─── D187: unique Resolved count, never events().len() ─────────────────────

#[test]
fn resolved_count_is_unique_ccs_not_events_len() {
    // Flat duplicate numbers on one resolution day (a punkt "1" and a
    // Положение "1" both minting through flat key punkt-1) produce two
    // same-day events with different text for ONE CC: Conflict. The
    // Resolved count is the number of unique Resolved CCs (1), never
    // events().len() (3).
    let mut map = HierarchyMap::empty();
    bind(&mut map, "punkt", "1", "cc:pp-60:punkt-1");
    bind(&mut map, "punkt", "2", "cc:pp-60:punkt-2");
    let units: [Unit; 3] = [
        ("punkt", "1", Some("Первый"), "Текст первого пункта."),
        (
            "punkt",
            "1",
            Some("Первый"),
            "Другой текст с тем же номером.",
        ),
        ("punkt", "2", Some("Второй"), "Текст второго пункта."),
    ];
    let log = build_text_log_from_articles(&map, units, DAY, PROV);
    assert_eq!(log.events().len(), 3, "all three tuples mint events");

    assert!(matches!(
        resolve_ctv(&log, &cc("cc:pp-60:punkt-1"), DAY),
        CtvResolution::Conflict { .. }
    ));
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:pp-60:punkt-2"), DAY),
        CtvResolution::Resolved { .. }
    ));

    // D187 pattern: HashSet of CC ids whose resolution is Resolved.
    let ids = [cc("cc:pp-60:punkt-1"), cc("cc:pp-60:punkt-2")];
    let unique_resolved: HashSet<&ComponentConceptId> = ids
        .iter()
        .filter(|id| matches!(resolve_ctv(&log, id, DAY), CtvResolution::Resolved { .. }))
        .collect();
    assert_eq!(unique_resolved.len(), 1);
    assert_ne!(
        unique_resolved.len(),
        log.events().len(),
        "resolved count is never events().len()"
    );
}
