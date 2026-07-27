use std::{fs, path::PathBuf};

use ln_decode::{
    adapters::{garant_odt::GarantOdtBlockDecoder, garant_odt_package::read_odt_content_xml},
    domain::{fingerprint_bytes, DecodeRequest, FamilyFormat, PayloadRef},
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
};

const EXPECTED_SOURCE_FINGERPRINT: &str = "fnv1a64:d4143a172688f8c3";
const EXPECTED_BLOCK_COUNT: usize = 5_124;
const EXPECTED_HIERARCHY_COUNT: usize = 140;

fn fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("law-source/garant/44-fz.odt")
}

fn request(bytes: &[u8]) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:garant-real-44-fz").unwrap(),
        FamilyFormat::parse("family:garant-odt").unwrap(),
        bytes,
    )
}

#[test]
fn tracked_real_garant_act_is_deterministic_and_bounded() {
    let bytes = fs::read(fixture_path()).expect("tracked Garant ODT fixture");
    let source_fingerprint = fingerprint_bytes(&bytes);
    let decode_request = request(&bytes);
    let content = read_odt_content_xml(&decode_request).expect("bounded tracked ODT package");
    let decoder = GarantOdtBlockDecoder;

    let first = decoder
        .decode_blocks(&decode_request)
        .unwrap_or_else(|error| {
            panic!(
                "current real ODT result: phase={:?} kind={:?} byte_offset={:?}",
                error.phase(),
                error.kind(),
                error.byte_offset()
            )
        });
    let second = decoder
        .decode_blocks(&decode_request)
        .expect("repeat tracked Garant ODT decode");
    let hierarchy = first
        .iter()
        .filter_map(extract_hierarchy)
        .collect::<Vec<_>>();

    assert_eq!(first, second, "repeat decode must be deterministic");
    assert!(!first.is_empty(), "tracked ODT must emit blocks");
    for block in &first {
        assert_eq!(
            block.source_location().stream().as_str(),
            "package-member:content.xml"
        );
        let span = block.source_location().span();
        assert!(span.start() < span.end());
        let source = &content.bytes()[span.start()..span.end()];
        assert!(source.starts_with(b"<text:p") || source.starts_with(b"<text:h"));
        assert!(source.ends_with(b"</text:p>") || source.ends_with(b"</text:h>"));
        if let Some(node) = extract_hierarchy(block) {
            assert!(node.marker_span().end() <= block.text().len());
        }
    }

    eprintln!(
        "source_fingerprint={source_fingerprint} blocks={} hierarchy={}",
        first.len(),
        hierarchy.len()
    );
    assert_eq!(source_fingerprint, EXPECTED_SOURCE_FINGERPRINT);
    assert_eq!(first.len(), EXPECTED_BLOCK_COUNT);
    assert_eq!(hierarchy.len(), EXPECTED_HIERARCHY_COUNT);
}
