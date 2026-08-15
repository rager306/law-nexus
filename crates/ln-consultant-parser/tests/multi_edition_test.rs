//! Multi-edition pipeline tests: temporal edge evolution across 44-ФЗ editions.

use ln_consultant_parser::multi_edition::{
    delta, parse_edition_filename, process_edition, process_edition_for_path,
    process_editions_directory,
};

fn editions_dir() -> std::path::PathBuf {
    let root =
        std::env::var("CONSULTANT_EXPORT_DIR").unwrap_or_else(|_| "consru_export".to_owned());
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(root)
        .join("consru_export/exports/npa/law_2013-04-05_44-fz")
}

#[test]
fn parse_filename_extracts_number_and_date() {
    let (num, rev) =
        parse_edition_filename("edition-0042_rev-2017-01-01_from-2017-07-01_abc123.xml")
            .expect("parse");
    assert_eq!(num, 42);
    assert_eq!(rev, "2017-01-01");
}

#[test]
fn parse_filename_initial() {
    let (num, rev) = parse_edition_filename("edition-0001_rev-initial_from-unknown_19d3c051.xml")
        .expect("parse initial");
    assert_eq!(num, 1);
    assert_eq!(rev, "initial");
}

#[test]
fn real_44fz_first_vs_last_edition() {
    let dir = editions_dir();
    if !dir.exists() {
        eprintln!("SKIP: consru_export not available");
        return;
    }

    // Process first edition (2013 initial) and last edition (2025 latest)
    let first_file = dir.join("edition-0001_rev-initial_from-unknown_19d3c051.xml");
    let last_file = dir.join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");

    let first_xml = std::fs::read(&first_file).expect("read first edition");
    let last_xml = std::fs::read(&last_file).expect("read last edition");

    let first = process_edition(&first_xml, 1, "initial");
    let last = process_edition(&last_xml, 118, "2025-12-28");

    println!("=== 44-ФЗ temporal edge evolution ===");
    println!(
        "Edition 1 (2013 initial): {} links, {} amends, {} cites",
        first.hyperlink_count, first.amends_count, first.cites_count
    );
    println!(
        "Edition 118 (2025-12-28): {} links, {} amends, {} cites",
        last.hyperlink_count, last.amends_count, last.cites_count
    );

    let d = delta(&first, &last);
    println!(
        "Delta: amends {:+}, cites {:+}, implements {:+}",
        d.amends_change, d.cites_change, d.implements_change
    );

    // The 2013 edition should have FEWER links than 2025 (law grew)
    assert!(
        last.hyperlink_count > first.hyperlink_count,
        "2025 edition should have more hyperlinks than 2013; got {} vs {}",
        last.hyperlink_count,
        first.hyperlink_count
    );
    // The 2025 edition should have MORE amends references (accumulated amendments)
    assert!(
        last.amends_count > first.amends_count,
        "2025 edition should have more amends; got {} vs {}",
        last.amends_count,
        first.amends_count
    );
}

fn amendment_xml() -> Vec<u8> {
    r#"<?xml version="1.0" encoding="UTF-8"?>
<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml">
<w:body>
<w:p><w:r><w:t>(в ред. </w:t></w:r>
  <w:hlink w:dest="consultantplus://offline/ref=TOKEN360">
    <w:r><w:t>N 360-ФЗ</w:t></w:r>
  </w:hlink>
<w:r><w:t>)</w:t></w:r></w:p>
</w:body>
</w:wordDocument>"#
        .as_bytes()
        .to_vec()
}

#[test]
fn process_edition_wrapper_uses_default_profile_path() {
    let xml = amendment_xml();
    let wrapped = process_edition(&xml, 1, "2024-01-01");
    let empty_path = process_edition_for_path(&xml, 1, "2024-01-01", "");
    assert_eq!(wrapped.hyperlink_count, 1);
    assert_eq!(wrapped.amends_count, empty_path.amends_count);
    assert_eq!(wrapped.amends_count, 1);
    assert_eq!(wrapped.unknown_count, empty_path.unknown_count);
}

#[test]
fn process_edition_for_path_classifies_federal_law_source() {
    let xml = amendment_xml();
    let summary = process_edition_for_path(
        &xml,
        5,
        "2024-01-01",
        "exports/npa/federalnyi-zakon-ot-05-04-2013-n-44-fz/edition-0005.xml",
    );
    assert_eq!(summary.edition_number, 5);
    assert_eq!(summary.hyperlink_count, 1);
    assert_eq!(summary.amends_count, 1);
    assert_eq!(summary.unknown_count, 0);
}

#[test]
fn process_editions_directory_passes_source_path() {
    let dir = std::env::temp_dir().join(format!("ln-s03-editions-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).expect("temp editions dir");
    let file = dir.join("edition-0007_rev-2024-01-01_from-2024-01-01_deadbeef.xml");
    std::fs::write(&file, amendment_xml()).expect("write edition xml");
    let summaries = process_editions_directory(&dir);
    let _ = std::fs::remove_dir_all(&dir);
    assert_eq!(summaries.len(), 1);
    assert_eq!(summaries[0].edition_number, 7);
    assert_eq!(summaries[0].amends_count, 1);
}
