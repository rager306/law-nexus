use std::fs;
use std::io::{Cursor, Write};
use std::path::PathBuf;

use ln_decode::{
    adapters::garant_odt_package::{
        read_odt_content_xml, MAX_CONTENT_XML_BYTES, MAX_ODT_ENTRIES, MAX_ODT_PACKAGE_BYTES,
    },
    domain::{BlockDecodeErrorKind, DecodePhase, DecodeRequest, FamilyFormat, PayloadRef},
};
use zip::{write::SimpleFileOptions, CompressionMethod, ZipWriter};

fn package(entries: Vec<(String, Vec<u8>)>) -> Vec<u8> {
    let mut writer = ZipWriter::new(Cursor::new(Vec::new()));
    let options = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);
    for (name, bytes) in entries {
        writer.start_file(name, options).expect("test ZIP entry");
        writer.write_all(&bytes).expect("test ZIP bytes");
    }
    writer.finish().expect("finish test ZIP").into_inner()
}

fn package_with_comment(entries: Vec<(String, Vec<u8>)>, comment: &[u8]) -> Vec<u8> {
    let mut writer = ZipWriter::new(Cursor::new(Vec::new()));
    let options = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);
    for (name, bytes) in entries {
        writer.start_file(name, options).expect("test ZIP entry");
        writer.write_all(&bytes).expect("test ZIP bytes");
    }
    writer
        .set_raw_comment(comment.to_vec().into_boxed_slice())
        .expect("test ZIP comment");
    writer.finish().expect("finish test ZIP").into_inner()
}

fn duplicate_content_package() -> Vec<u8> {
    let mut bytes = package(vec![
        ("content.xml".to_owned(), b"<one/>".to_vec()),
        ("xontent.xml".to_owned(), b"<two/>".to_vec()),
    ]);
    for index in 0..=bytes.len() - b"xontent.xml".len() {
        if &bytes[index..index + b"xontent.xml".len()] == b"xontent.xml" {
            bytes[index..index + b"content.xml".len()].copy_from_slice(b"content.xml");
        }
    }
    bytes
}

fn request(bytes: &[u8], family: &str) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:odt-package-test").unwrap(),
        FamilyFormat::parse(family).unwrap(),
        bytes,
    )
}

fn assert_package_error(
    result: Result<
        ln_decode::adapters::garant_odt_package::OdtPackageContent,
        ln_decode::domain::BlockDecodeError,
    >,
    kind: BlockDecodeErrorKind,
) {
    let error = result.expect_err("hostile package must fail");
    assert_eq!(error.phase(), DecodePhase::Package);
    assert_eq!(error.kind(), kind);
    assert!(!error.to_string().contains("CANARY"));
    assert!(!format!("{error:?}").contains("CANARY"));
}

#[test]
fn valid_deflated_package_returns_exact_bounded_content_in_memory() {
    let content = b"<office:document-content>bounded</office:document-content>";
    let bytes = package(vec![
        (
            "mimetype".to_owned(),
            b"application/vnd.oasis.opendocument.text".to_vec(),
        ),
        ("content.xml".to_owned(), content.to_vec()),
    ]);

    let result = read_odt_content_xml(&request(&bytes, "family:garant-odt"))
        .expect("valid bounded ODT package");

    assert_eq!(result.bytes(), content);
    assert_eq!(result.entry_count(), 2);
}

#[test]
fn eocd_signature_inside_valid_comment_does_not_hide_real_record() {
    let bytes = package_with_comment(
        vec![("content.xml".to_owned(), b"<root/>".to_vec())],
        b"comment-PK\x05\x06-tail",
    );

    let result = read_odt_content_xml(&request(&bytes, "family:garant-odt"))
        .expect("valid comment must not confuse EOCD scan");
    assert_eq!(result.bytes(), b"<root/>");
}

#[test]
fn tracked_44_fz_package_fits_bounded_intake_without_parsing_xml() {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("law-source/garant/44-fz.odt");
    let bytes = fs::read(path).expect("tracked canonical ODT package");

    let result = read_odt_content_xml(&request(&bytes, "family:garant-odt"))
        .expect("tracked package must fit bounded intake");

    assert_eq!(result.entry_count(), 8);
    assert_eq!(result.bytes().len(), 2_387_452);
}

#[test]
fn wrong_family_and_invalid_zip_fail_with_safe_typed_errors() {
    let valid = package(vec![("content.xml".to_owned(), b"<root/>".to_vec())]);
    let wrong_family = read_odt_content_xml(&request(&valid, "family:consultant-wordml"))
        .expect_err("wrong provider family must fail before package parsing");
    assert_eq!(wrong_family.phase(), DecodePhase::Input);
    assert_eq!(wrong_family.kind(), BlockDecodeErrorKind::UnsupportedFormat);
    assert_package_error(
        read_odt_content_xml(&request(b"CANARY::NOT-A-ZIP", "family:garant-odt")),
        BlockDecodeErrorKind::InvalidPackage,
    );
}

#[test]
fn missing_duplicate_and_unsafe_content_entries_fail_closed() {
    assert_package_error(
        read_odt_content_xml(&request(
            &package(vec![("styles.xml".to_owned(), b"CANARY".to_vec())]),
            "family:garant-odt",
        )),
        BlockDecodeErrorKind::MissingContentXml,
    );
    assert_package_error(
        read_odt_content_xml(&request(&duplicate_content_package(), "family:garant-odt")),
        BlockDecodeErrorKind::DuplicatePackageEntry,
    );
    assert_package_error(
        read_odt_content_xml(&request(
            &package(vec![("../content.xml".to_owned(), b"CANARY".to_vec())]),
            "family:garant-odt",
        )),
        BlockDecodeErrorKind::UnsafePackageEntry,
    );
}

#[test]
fn entry_and_content_limits_are_enforced_before_unbounded_use() {
    let mut oversized_package = package(vec![("content.xml".to_owned(), b"<root/>".to_vec())]);
    oversized_package.resize(MAX_ODT_PACKAGE_BYTES + 1, 0);
    assert_package_error(
        read_odt_content_xml(&request(&oversized_package, "family:garant-odt")),
        BlockDecodeErrorKind::PackageLimitExceeded,
    );

    let too_many = (0..=MAX_ODT_ENTRIES)
        .map(|index| (format!("entry-{index}.txt"), Vec::new()))
        .collect();
    assert_package_error(
        read_odt_content_xml(&request(&package(too_many), "family:garant-odt")),
        BlockDecodeErrorKind::PackageLimitExceeded,
    );

    let oversized = vec![b'x'; MAX_CONTENT_XML_BYTES + 1];
    assert_package_error(
        read_odt_content_xml(&request(
            &package(vec![("content.xml".to_owned(), oversized)]),
            "family:garant-odt",
        )),
        BlockDecodeErrorKind::PackageLimitExceeded,
    );
}
