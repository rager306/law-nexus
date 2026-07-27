use std::{fs, path::PathBuf};

use ln_decode::{
    adapters::{garant_odt::GarantOdtBlockDecoder, ConsultantWordMlBlockDecoder},
    deontic::extract_deontic_lexemes,
    domain::{fingerprint_bytes, DecodeRequest, FamilyFormat, PayloadRef, SourceFormatId},
    evaluator::evaluate,
    golden::{GoldenAnnotation, GoldenFixture, GoldenLayer, GoldenSource},
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
    references::extract_reference_mentions,
    temporal::extract_temporal_phrases,
};

const CONSULTANT_FIXTURE: &str = "law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";
const GARANT_FIXTURE: &str = "law-source/garant/44-fz.odt";

const CONSULTANT_FP: &str = "fnv1a64:d7697a0ea8cc3970";
const GARANT_FP: &str = "fnv1a64:d4143a172688f8c3";

fn fixture_path(relative: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(relative)
}

fn request(payload: &str, family: &str, bytes: &[u8]) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse(payload).unwrap(),
        FamilyFormat::parse(family).unwrap(),
        bytes,
    )
}

fn build_annotations(blocks: &[ln_decode::domain::ParsedBlock]) -> Vec<GoldenAnnotation> {
    let mut annotations = Vec::new();
    for (index, block) in blocks.iter().enumerate() {
        if let Some(node) = extract_hierarchy(block) {
            annotations.push(GoldenAnnotation::Hierarchy {
                block_index: index,
                level: node.level(),
                span: node.marker_span(),
            });
        }
        for mention in extract_reference_mentions(block) {
            annotations.push(GoldenAnnotation::Reference {
                block_index: index,
                kind: mention.kind(),
                number: mention.number().to_owned(),
                span: mention.text_span(),
            });
        }
        for phrase in extract_temporal_phrases(block) {
            annotations.push(GoldenAnnotation::Temporal {
                block_index: index,
                kind: phrase.kind(),
                span: phrase.text_span(),
            });
        }
        for lexeme in extract_deontic_lexemes(block) {
            annotations.push(GoldenAnnotation::Deontic {
                block_index: index,
                kind: lexeme.kind(),
                span: lexeme.text_span(),
                negated: lexeme.negated(),
            });
        }
    }
    annotations
}

fn assert_self_consistent(metrics: &[ln_decode::evaluator::LayerMetrics]) {
    for metric in metrics {
        assert_eq!(
            metric.false_positives(),
            0,
            "FP must be zero for {:?}",
            metric.layer()
        );
        assert_eq!(
            metric.false_negatives(),
            0,
            "FN must be zero for {:?}",
            metric.layer()
        );
    }
}

#[test]
fn tracked_real_consultant_enrichment_is_self_consistent_and_deterministic() {
    let bytes = fs::read(fixture_path(CONSULTANT_FIXTURE)).expect("tracked Consultant fixture");
    let fp = fingerprint_bytes(&bytes);
    assert_eq!(fp, CONSULTANT_FP);

    let req = request(
        "payload:m135-consultant-golden",
        "family:consultant-wordml",
        &bytes,
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&req)
        .expect("decode");

    let annotations = build_annotations(&blocks);
    assert!(!annotations.is_empty(), "must have annotations");

    let source = GoldenSource::try_new(
        CONSULTANT_FIXTURE,
        "sha256:verified-by-script",
        bytes.len(),
        &fp,
    )
    .unwrap();
    let fixture = GoldenFixture::try_new(
        source,
        SourceFormatId::ConsultantWordMl,
        annotations,
        Vec::new(),
    )
    .unwrap();

    let first = evaluate(&fixture, &blocks).expect("evaluate");
    let second = evaluate(&fixture, &blocks).expect("repeat evaluate");
    assert_eq!(first, second, "must be deterministic");
    assert_self_consistent(&first);

    let mut layer_counts: Vec<(&str, usize, usize, usize)> = first
        .iter()
        .map(|m| {
            let name = match m.layer() {
                GoldenLayer::Hierarchy => "hierarchy",
                GoldenLayer::Reference => "reference",
                GoldenLayer::Temporal => "temporal",
                GoldenLayer::Deontic => "deontic",
            };
            (
                name,
                m.true_positives(),
                m.false_positives(),
                m.false_negatives(),
            )
        })
        .collect();
    layer_counts.sort_by_key(|(name, _, _, _)| name.to_string());

    eprintln!(
        "M135_CONSULTANT_GOLDEN blocks={} annotations={} layers={}",
        blocks.len(),
        fixture.annotations().len(),
        first.len()
    );
    for (name, tp, fp, fn_) in &layer_counts {
        eprintln!("  {name}: TP={tp} FP={fp} FN={fn_}");
    }
}

#[test]
fn tracked_real_garant_enrichment_is_self_consistent_and_deterministic() {
    let bytes = fs::read(fixture_path(GARANT_FIXTURE)).expect("tracked Garant fixture");
    let fp = fingerprint_bytes(&bytes);
    assert_eq!(fp, GARANT_FP);

    let req = request("payload:m135-garant-golden", "family:garant-odt", &bytes);
    let blocks = GarantOdtBlockDecoder.decode_blocks(&req).expect("decode");

    let annotations = build_annotations(&blocks);
    assert!(!annotations.is_empty(), "must have annotations");

    let source = GoldenSource::try_new(
        GARANT_FIXTURE,
        "sha256:verified-by-script",
        bytes.len(),
        &fp,
    )
    .unwrap();
    let fixture =
        GoldenFixture::try_new(source, SourceFormatId::GarantOdt, annotations, Vec::new()).unwrap();

    let first = evaluate(&fixture, &blocks).expect("evaluate");
    let second = evaluate(&fixture, &blocks).expect("repeat evaluate");
    assert_eq!(first, second, "must be deterministic");
    assert_self_consistent(&first);

    let mut layer_counts: Vec<(&str, usize, usize, usize)> = first
        .iter()
        .map(|m| {
            let name = match m.layer() {
                GoldenLayer::Hierarchy => "hierarchy",
                GoldenLayer::Reference => "reference",
                GoldenLayer::Temporal => "temporal",
                GoldenLayer::Deontic => "deontic",
            };
            (
                name,
                m.true_positives(),
                m.false_positives(),
                m.false_negatives(),
            )
        })
        .collect();
    layer_counts.sort_by_key(|(name, _, _, _)| name.to_string());

    eprintln!(
        "M135_GARANT_GOLDEN blocks={} annotations={} layers={}",
        blocks.len(),
        fixture.annotations().len(),
        first.len()
    );
    for (name, tp, fp, fn_) in &layer_counts {
        eprintln!("  {name}: TP={tp} FP={fp} FN={fn_}");
    }
}
