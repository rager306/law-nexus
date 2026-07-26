use std::fs;
use std::path::PathBuf;

use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{
        fingerprint_bytes, BlockDecodeErrorKind, DecodePhase, DecodeRequest, FamilyFormat,
        PayloadRef,
    },
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
};

const FIXTURE: &str = "law-source/consultant/federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023-o-publichno-pravovoi-kompanii-edinyi-zakazchik-v-sfere-stroitelstva-i-o-vnese--d71bf702.xml";
const EXPECTED_SOURCE_FINGERPRINT: &str = "fnv1a64:d7697a0ea8cc3970";
const EXPECTED_BLOCK_COUNT: usize = 167;
const EXPECTED_HIERARCHY_COUNT: usize = 22;

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(FIXTURE)
}

fn request(bytes: &[u8]) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:m132-consultant-real-tracer").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        bytes,
    )
}

#[test]
fn tracked_real_consultant_act_is_deterministic_and_bounded() {
    let bytes = fs::read(fixture_path()).expect("tracked Consultant fixture");
    let first = ConsultantWordMlBlockDecoder
        .decode_blocks(&request(&bytes))
        .expect("real Consultant fixture must decode");
    let second = ConsultantWordMlBlockDecoder
        .decode_blocks(&request(&bytes))
        .expect("repeat decode must succeed");
    let hierarchy = first
        .iter()
        .filter_map(extract_hierarchy)
        .collect::<Vec<_>>();
    let source_fingerprint = fingerprint_bytes(&bytes);

    eprintln!(
        "fixture={FIXTURE} bytes={} fingerprint={} blocks={} hierarchy={}",
        bytes.len(),
        source_fingerprint,
        first.len(),
        hierarchy.len()
    );

    assert_eq!(first, second, "repeat decode must be byte-deterministic");
    assert!(!first.is_empty(), "real act must emit blocks");
    for block in &first {
        assert_eq!(block.source_location().stream().as_str(), "artifact:whole");
        let span = block.source_location().span();
        let artifact = &bytes[span.start()..span.end()];
        assert!(artifact.starts_with(b"<w:p"));
        assert!(artifact.ends_with(b"</w:p>"));
        if let Some(node) = extract_hierarchy(block) {
            assert!(node.marker_span().end() <= block.text().len());
        }
    }
    assert_eq!(source_fingerprint, EXPECTED_SOURCE_FINGERPRINT);
    assert_eq!(first.len(), EXPECTED_BLOCK_COUNT);
    assert_eq!(hierarchy.len(), EXPECTED_HIERARCHY_COUNT);
}

#[test]
fn truncated_real_fixture_fails_atomically_without_raw_text() {
    let mut bytes = fs::read(fixture_path()).expect("tracked Consultant fixture");
    bytes.truncate(bytes.len().saturating_sub(64));

    let error = ConsultantWordMlBlockDecoder
        .decode_blocks(&request(&bytes))
        .expect_err("truncated real XML must fail atomically");

    assert_eq!(error.phase(), DecodePhase::Parse);
    assert_eq!(error.kind(), BlockDecodeErrorKind::MalformedInput);
    assert!(!error.to_string().contains("Постановление"));
    assert!(error.byte_offset().is_some());
}
