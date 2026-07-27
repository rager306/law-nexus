use ln_decode::{
    deontic::DeonticLexemeKind,
    domain::{HierarchyLevel, SourceFormatId, TextSpan},
    golden::{GoldenAnnotation, GoldenError, GoldenFixture, GoldenSource},
    references::ReferenceMentionKind,
    temporal::TemporalPhraseKind,
};

fn consultant_source() -> GoldenSource {
    GoldenSource::try_new(
        "law-source/consultant/synthetic-fixture.xml",
        "0000000000000000000000000000000000000000000000000000000000000000",
        1024,
        "fnv1a64:0000000000000000",
    )
    .unwrap()
}

fn garant_source() -> GoldenSource {
    GoldenSource::try_new(
        "law-source/garant/synthetic-fixture.odt",
        "1111111111111111111111111111111111111111111111111111111111111111",
        2048,
        "fnv1a64:1111111111111111",
    )
    .unwrap()
}

fn span(start: usize, end: usize) -> TextSpan {
    TextSpan::try_new(start, end).unwrap()
}

#[test]
fn rejects_empty_or_malformed_source_identity() {
    assert!(matches!(
        GoldenSource::try_new("", "hash", 1, "fp"),
        Err(GoldenError::EmptySourcePath)
    ));
    assert!(matches!(
        GoldenSource::try_new("path", "", 1, "fp"),
        Err(GoldenError::EmptySourceHash)
    ));
    assert!(matches!(
        GoldenSource::try_new("path", "hash", 0, "fp"),
        Err(GoldenError::ZeroByteCount)
    ));
    assert!(matches!(
        GoldenSource::try_new("path", "hash", 1, ""),
        Err(GoldenError::EmptyFingerprint)
    ));
}

#[test]
fn rejects_empty_annotations() {
    let result = GoldenFixture::try_new(
        consultant_source(),
        SourceFormatId::ConsultantWordMl,
        Vec::new(),
        Vec::new(),
    );
    assert!(matches!(result, Err(GoldenError::EmptyAnnotations)));
}

#[test]
fn rejects_duplicate_annotation_within_same_block_and_layer() {
    let duplicate = GoldenAnnotation::Hierarchy {
        block_index: 0,
        level: HierarchyLevel::Statya,
        span: span(0, 10),
    };
    let result = GoldenFixture::try_new(
        consultant_source(),
        SourceFormatId::ConsultantWordMl,
        vec![duplicate.clone(), duplicate],
        Vec::new(),
    );
    assert!(matches!(
        result,
        Err(GoldenError::DuplicateAnnotation { .. })
    ));
}

#[test]
fn rejects_invalid_reference_number_grammar() {
    let annotation = GoldenAnnotation::Reference {
        block_index: 0,
        kind: ReferenceMentionKind::Article,
        number: "5а".to_owned(),
        span: span(0, 10),
    };
    let result = GoldenFixture::try_new(
        consultant_source(),
        SourceFormatId::ConsultantWordMl,
        vec![annotation],
        Vec::new(),
    );
    assert!(matches!(
        result,
        Err(GoldenError::InvalidReferenceNumber { .. })
    ));
}

#[test]
fn synthetic_consultant_fixture_round_trips_deterministically() {
    let annotations = vec![
        GoldenAnnotation::Hierarchy {
            block_index: 0,
            level: HierarchyLevel::Statya,
            span: span(0, 7),
        },
        GoldenAnnotation::Reference {
            block_index: 1,
            kind: ReferenceMentionKind::Article,
            number: "5.1".to_owned(),
            span: span(4, 12),
        },
    ];
    let fixture = GoldenFixture::try_new(
        consultant_source(),
        SourceFormatId::ConsultantWordMl,
        annotations.clone(),
        vec!["no legal correctness claim".to_owned()],
    )
    .unwrap();

    assert_eq!(fixture.annotations().len(), 2);
    assert_eq!(fixture.provider(), SourceFormatId::ConsultantWordMl);
    assert_eq!(
        fixture.source().path(),
        "law-source/consultant/synthetic-fixture.xml"
    );
    assert_eq!(fixture.source().byte_count(), 1024);
    assert_eq!(fixture.non_claims().len(), 1);

    let reconstructed = GoldenFixture::try_new(
        consultant_source(),
        SourceFormatId::ConsultantWordMl,
        annotations,
        vec!["no legal correctness claim".to_owned()],
    )
    .unwrap();
    assert_eq!(fixture, reconstructed);
}

#[test]
fn synthetic_garant_fixture_round_trips_all_four_layers() {
    let annotations = vec![
        GoldenAnnotation::Temporal {
            block_index: 0,
            kind: TemporalPhraseKind::EntersIntoForce,
            span: span(10, 30),
        },
        GoldenAnnotation::Deontic {
            block_index: 1,
            kind: DeonticLexemeKind::Permission,
            span: span(5, 10),
            negated: false,
        },
        GoldenAnnotation::Reference {
            block_index: 1,
            kind: ReferenceMentionKind::Point,
            number: "2".to_owned(),
            span: span(15, 17),
        },
        GoldenAnnotation::Hierarchy {
            block_index: 2,
            level: HierarchyLevel::Glava,
            span: span(0, 8),
        },
    ];
    let fixture = GoldenFixture::try_new(
        garant_source(),
        SourceFormatId::GarantOdt,
        annotations,
        Vec::new(),
    )
    .unwrap();

    assert_eq!(fixture.annotations().len(), 4);
    assert_eq!(fixture.provider(), SourceFormatId::GarantOdt);
}
