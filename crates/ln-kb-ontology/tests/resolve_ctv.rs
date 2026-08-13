//! resolve_CTV: deterministic point-in-time text reconstruction.
//! This is the main capability gap vs de Martim v5 (KBO-R046).
//! Text is synthetic in tests; no raw legal text is persisted.

use ln_kb_ontology::domain::{resolve_ctv, CtvResolution, TextVersionEvent, TextVersionLog};
use ln_temporal::domain::ComponentConceptId;

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn text_event(component: &str, text: &str, day: i64, prov: &str) -> TextVersionEvent {
    TextVersionEvent::try_new(cc(component), text, day, prov).expect("event")
}

#[test]
fn resolve_returns_latest_text_at_or_before_day() {
    let mut log = TextVersionLog::empty();
    log.append(text_event("cc:art-1", "Original wording", 100, "prov-a"))
        .expect("append");
    log.append(text_event("cc:art-1", "Amended wording", 200, "prov-b"))
        .expect("append");

    match resolve_ctv(&log, &cc("cc:art-1"), 100) {
        CtvResolution::Resolved { text } => assert_eq!(text, "Original wording"),
        other => panic!("expected Resolved, got {other:?}"),
    }
    match resolve_ctv(&log, &cc("cc:art-1"), 200) {
        CtvResolution::Resolved { text } => assert_eq!(text, "Amended wording"),
        other => panic!("expected Resolved, got {other:?}"),
    }
    // At day 150, the original is still in effect
    match resolve_ctv(&log, &cc("cc:art-1"), 150) {
        CtvResolution::Resolved { text } => assert_eq!(text, "Original wording"),
        other => panic!("expected Resolved, got {other:?}"),
    }
}

#[test]
fn resolve_unknown_before_first_event() {
    let mut log = TextVersionLog::empty();
    log.append(text_event("cc:art-1", "Text", 100, "prov"))
        .expect("append");
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:art-1"), 99),
        CtvResolution::Unknown
    ));
}

#[test]
fn resolve_unknown_for_untracked_cc() {
    let log = TextVersionLog::empty();
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:art-1"), 100),
        CtvResolution::Unknown
    ));
}

#[test]
fn resolve_conflict_same_day_different_text() {
    let mut log = TextVersionLog::empty();
    log.append(text_event("cc:art-1", "Version A", 100, "prov-a"))
        .expect("append");
    log.append(text_event("cc:art-1", "Version B", 100, "prov-b"))
        .expect("append");
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:art-1"), 100),
        CtvResolution::Conflict { .. }
    ));
}

#[test]
fn resolve_multiple_ccs_independent() {
    let mut log = TextVersionLog::empty();
    log.append(text_event("cc:art-1", "Art 1 text", 100, "prov"))
        .expect("append");
    log.append(text_event("cc:art-2", "Art 2 text", 100, "prov"))
        .expect("append");

    match resolve_ctv(&log, &cc("cc:art-1"), 100) {
        CtvResolution::Resolved { text } => assert_eq!(text, "Art 1 text"),
        other => panic!("got {other:?}"),
    }
    match resolve_ctv(&log, &cc("cc:art-2"), 100) {
        CtvResolution::Resolved { text } => assert_eq!(text, "Art 2 text"),
        other => panic!("got {other:?}"),
    }
    assert!(matches!(
        resolve_ctv(&log, &cc("cc:art-3"), 100),
        CtvResolution::Unknown
    ));
}

#[test]
fn resolve_empty_provenance_rejected() {
    assert!(TextVersionEvent::try_new(cc("cc:art-1"), "Text", 100, "").is_err());
}
