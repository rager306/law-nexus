use std::io::{Cursor, Write};

use ln_decode::adapters::garant_odt::GarantOdtBlockDecoder;
use ln_decode::adapters::ConsultantWordMlBlockDecoder;
use ln_testkit::assert_block_decoder_port_contract;
use zip::{write::SimpleFileOptions, CompressionMethod, ZipWriter};

const OFFICE_NS: &str = "urn:oasis:names:tc:opendocument:xmlns:office:1.0";
const TEXT_NS: &str = "urn:oasis:names:tc:opendocument:xmlns:text:1.0";

fn consultant_wordml_fixture() -> Vec<u8> {
    r#"<w:wordDocument xmlns:w="urn:word"><w:body><w:p><w:pPr><w:pStyle w:val="2"/></w:pPr><w:r><w:t>Статья 1.</w:t></w:r></w:p><w:p><w:r><w:t>Текст.</w:t></w:r></w:p></w:body></w:wordDocument>"#
        .as_bytes()
        .to_vec()
}

fn garant_odt_package() -> Vec<u8> {
    let content_xml = format!(
        r#"<office:document-content xmlns:office="{OFFICE_NS}" xmlns:text="{TEXT_NS}"><office:body><office:text><text:h text:style-name="Heading_20_1">Статья 1.</text:h><text:p text:style-name="Standard">Текст абзаца.</text:p></office:text></office:body></office:document-content>"#
    );
    let mut writer = ZipWriter::new(Cursor::new(Vec::new()));
    let options = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);
    writer
        .start_file("content.xml", options)
        .expect("test content.xml entry");
    writer
        .write_all(content_xml.as_bytes())
        .expect("test content.xml bytes");
    writer.finish().expect("finish test ZIP").into_inner()
}

#[test]
fn consultant_wordml_block_decoder_satisfies_shared_port_contract() {
    let fixture = consultant_wordml_fixture();
    assert_block_decoder_port_contract(
        &ConsultantWordMlBlockDecoder,
        "family:consultant-wordml",
        &fixture,
        "family:garant-odt",
    );
}

#[test]
fn garant_odt_block_decoder_satisfies_shared_port_contract() {
    let package = garant_odt_package();
    assert_block_decoder_port_contract(
        &GarantOdtBlockDecoder,
        "family:garant-odt",
        &package,
        "family:consultant-wordml",
    );
}
