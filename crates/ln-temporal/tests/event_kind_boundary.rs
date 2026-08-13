//! Design-boundary contracts: TextChangeEvent ≠ NormativeEffectEvent
//! (RC11-F07 / TSG-002 / ADR-0017 non-claims).

use ln_temporal::domain::{
    classify_legislative_event_kind, reject_text_change_as_normative_effect, LegislativeEventKind,
    LegislativeEventKindClass,
};

#[test]
fn text_change_and_normative_effect_are_distinct_kinds() {
    assert_ne!(
        LegislativeEventKind::TextChange.as_str(),
        LegislativeEventKind::NormativeEffect.as_str()
    );
    assert_eq!(LegislativeEventKind::all().len(), 2);
}

#[test]
fn both_kinds_are_design_only_not_runtime() {
    for kind in LegislativeEventKind::all() {
        let boundary = classify_legislative_event_kind(kind);
        assert_eq!(boundary.class, LegislativeEventKindClass::DesignOnly);
        assert_eq!(boundary.kind, kind);
        assert!(
            boundary
                .non_claims
                .iter()
                .any(|c| c.contains("not separated") || c.contains("not implemented")),
            "boundary must restate F07 non-claim for {:?}",
            kind
        );
    }
}

#[test]
fn text_change_cannot_prove_normative_effect() {
    let boundary = reject_text_change_as_normative_effect();
    assert_eq!(boundary.kind, LegislativeEventKind::TextChange);
    assert_eq!(boundary.class, LegislativeEventKindClass::DesignOnly);
    assert!(
        boundary
            .non_claims
            .iter()
            .any(|c| c.contains("does not prove") || c.contains("not prove")),
        "must forbid lexical→legal effect promotion"
    );
}

#[test]
fn design_class_is_not_executable_runtime() {
    let boundary = classify_legislative_event_kind(LegislativeEventKind::NormativeEffect);
    assert_ne!(boundary.class, LegislativeEventKindClass::ExecutableRuntime);
    assert_eq!(boundary.class.as_str(), "design_only");
}
