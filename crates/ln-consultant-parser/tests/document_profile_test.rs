//! Document profile detection tests (ADR-0027 Layer 1).

use ln_consultant_parser::document_profile::{apply_boost, detect_profile, load_profiles};

#[test]
fn profiles_loaded_from_yaml() {
    let profiles = load_profiles();
    assert!(!profiles.is_empty());
    assert!(profiles.iter().any(|p| p.name == "federal_law"));
    assert!(profiles.iter().any(|p| p.name == "court_decision"));
    assert!(profiles.iter().any(|p| p.name == "default"));
}

#[test]
fn federal_law_detected() {
    let profiles = load_profiles();
    let d = detect_profile(
        &profiles,
        "exports/npa/federalnyi-zakon-ot-05-04-2013-n-44-fz.xml",
    );
    assert_eq!(d.name, "federal_law");
    assert!((d.boost - 1.0).abs() < 0.01);
}

#[test]
fn court_decision_detected() {
    let profiles = load_profiles();
    let d = detect_profile(
        &profiles,
        "exports/courts/postanovlenie-arbitrazhnogo-suda.xml",
    );
    assert_eq!(d.name, "court_decision");
    assert!((d.boost - 0.8).abs() < 0.01);
}

#[test]
fn default_when_no_match() {
    let profiles = load_profiles();
    let d = detect_profile(&profiles, "exports/fas/unknown-document.xml");
    assert_eq!(d.name, "default");
    assert!((d.boost - 0.7).abs() < 0.01);
}

#[test]
fn boost_applied() {
    let profiles = load_profiles();
    let d = detect_profile(&profiles, "federalnyi-zakon.xml");
    let boosted = apply_boost(0.9, &d);
    assert!((boosted - 0.9).abs() < 0.01); // 1.0 boost
}
