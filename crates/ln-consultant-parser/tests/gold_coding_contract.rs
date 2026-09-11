use ln_consultant_parser::gold_coding::*;
use ln_decode::domain::TextSpan;

fn unit(label: &str, span: (usize, usize)) -> CodingUnit {
    CodingUnit::new(
        "consultant/doc.xml",
        "sha256:abc",
        2,
        TextSpan::try_new(span.0, span.1).unwrap(),
        "alpha бета",
        CodingLabel::new(CodingLayer::Semantic, label).unwrap(),
    )
    .unwrap()
}

fn passes(a: &str, b: &str) -> (CoderPass, CoderPass) {
    (
        CoderPass::new("coder-a", "evidence-forward", vec![unit(a, (0, 5))]).unwrap(),
        CoderPass::new("coder-b", "surface-forward", vec![unit(b, (0, 5))]).unwrap(),
    )
}

#[test]
fn alpha_pins_perfect_and_systematic_disagreement() {
    let perfect =
        krippendorff_nominal_alpha(&["obligation", "obligation"], &["obligation", "obligation"])
            .unwrap();
    assert_eq!((perfect.numerator, perfect.denominator), (1, 1));

    let disagree = krippendorff_nominal_alpha(
        &["Actor", "Action", "Actor", "Action"],
        &["Action", "Actor", "Action", "Actor"],
    )
    .unwrap();
    assert!(disagree.value() <= 0.0);
}

#[test]
fn duplicate_coder_and_empty_envelope_fail_closed() {
    let (first, _) = passes("Actor", "Action");
    let same_id = CoderPass::new("coder-a", "other", vec![unit("Actor", (0, 5))]).unwrap();
    assert!(matches!(
        CodingEnvelope::new(first.clone(), same_id),
        Err(CodingError::DuplicateCoderId)
    ));
    assert!(matches!(
        CoderPass::new("coder", "profile", vec![]),
        Err(CodingError::EmptyEnvelope)
    ));
    assert!(matches!(
        krippendorff_nominal_alpha(&[], &[]),
        Err(CodingError::EmptyEnvelope)
    ));
}

#[test]
fn span_boundaries_are_utf8_and_length_checked() {
    let label = CodingLabel::new(CodingLayer::Identity, "Geo").unwrap();
    assert!(matches!(
        CodingUnit::new(
            "doc",
            "hash",
            0,
            TextSpan::try_new(1, 2).unwrap(),
            "я",
            label.clone()
        ),
        Err(CodingError::InvalidSpan)
    ));
    assert!(matches!(
        CodingUnit::new(
            "doc",
            "hash",
            0,
            TextSpan::try_new(0, 5).unwrap(),
            "я",
            label
        ),
        Err(CodingError::InvalidSpan)
    ));
}

#[test]
fn envelope_requires_different_profiles_and_adjudication_is_append_only() {
    let (first, _) = passes("Actor", "Action");
    let second =
        CoderPass::new("coder-b", "surface-forward", vec![unit("Action", (0, 5))]).unwrap();
    let envelope = CodingEnvelope::new(first, second).unwrap();
    assert_eq!(envelope.classification(), AgreementClassification::Proxy);
    let key = ("consultant/doc.xml".into(), "sha256:abc".into(), 2, 0, 5);
    let label = CodingLabel::new(CodingLayer::Semantic, "Actor").unwrap();
    let adjudicated = envelope
        .adjudicate(key.clone(), label.clone(), "independent tie-break")
        .unwrap();
    assert_eq!(envelope.adjudications().len(), 0);
    assert_eq!(adjudicated.adjudications().len(), 1);
    assert!(matches!(
        adjudicated.adjudicate(key, label, "second decision"),
        Err(CodingError::DuplicateUnit)
    ));
}

#[test]
fn missing_coders_are_not_measurement_and_snapshot_is_required() {
    assert_eq!(
        publication_status(None, "sha256:snapshot").unwrap(),
        MeasurementStatus::NotMeasured
    );
    assert!(matches!(
        publication_status(None, "diagnostic-bound"),
        Err(CodingError::MissingSnapshotBinding)
    ));
}

#[test]
fn closed_label_sets_reject_unknown_values() {
    assert!(CodingLabel::new(CodingLayer::Semantic, "NormRule").is_err());
    assert!(CodingLabel::new(CodingLayer::Parsing, "Article").is_ok());
    assert!(CodingLabel::new(CodingLayer::Temporal, "AsOfPairing").is_ok());
}
