//! Hyperlink extraction from Consultant WordML XML.

use ln_consultant_parser::extract_hyperlinks;

fn xml_with_link(dest: &str, text: &str) -> Vec<u8> {
    format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<w:wordDocument xmlns:w="urn:word">
<w:p><w:pPr><w:pStyle w:val="0"/></w:pPr>
  <w:r><w:t>Текст до ссылки </w:t></w:r>
  <w:hlink w:dest="{dest}">
    <w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>
      <w:t>{text}</w:t>
    </w:r>
  </w:hlink>
  <w:r><w:t> текст после</w:t></w:r>
</w:p>
</w:wordDocument>"#
    )
    .into_bytes()
}

#[test]
fn extracts_single_internal_link() {
    let xml = xml_with_link(
        "consultantplus://offline/ref=E0A05835A65D4DCC29CAA6ED3C5F3C",
        "N 396-ФЗ",
    );
    let links = extract_hyperlinks(&xml);
    assert_eq!(links.len(), 1);
    assert!(links[0].is_internal());
    assert_eq!(links[0].text, "N 396-ФЗ");
    assert!(links[0].consid().is_some());
    assert!(links[0].consid().unwrap().starts_with("E0A0"));
}

#[test]
fn extracts_multiple_links_in_sequence() {
    let xml = r#"<w:wordDocument xmlns:w="urn:word">
<w:p><w:hlink w:dest="consultantplus://offline/ref=TOKEN1"><w:r><w:t>N 188-ФЗ</w:t></w:r></w:hlink></w:p>
<w:p><w:hlink w:dest="consultantplus://offline/ref=TOKEN2"><w:r><w:t>N 396-ФЗ</w:t></w:r></w:hlink></w:p>
<w:p><w:hlink w:dest="consultantplus://offline/ref=TOKEN3"><w:r><w:t>N 140-ФЗ</w:t></w:r></w:hlink></w:p>
</w:wordDocument>"#
        .to_string();
    let links = extract_hyperlinks(xml.as_bytes());
    assert_eq!(links.len(), 3);
    assert_eq!(links[0].text, "N 188-ФЗ");
    assert_eq!(links[1].text, "N 396-ФЗ");
    assert_eq!(links[2].text, "N 140-ФЗ");
}

#[test]
fn extracts_external_link() {
    let xml = xml_with_link("https://www.consultant.ru/document/", "КонсультантПлюс");
    let links = extract_hyperlinks(&xml);
    assert_eq!(links.len(), 1);
    assert!(links[0].is_external());
    assert!(!links[0].is_internal());
}

#[test]
fn empty_xml_returns_empty() {
    let links = extract_hyperlinks(b"<?xml version=\"1.0\"?>");
    assert!(links.is_empty());
}

#[test]
fn link_with_multiple_text_runs() {
    let xml = r#"<w:wordDocument xmlns:w="urn:word">
<w:hlink w:dest="consultantplus://offline/ref=ABC">
  <w:r><w:t>Федеральный </w:t></w:r>
  <w:r><w:t>закон </w:t></w:r>
  <w:r><w:t>N 360-ФЗ</w:t></w:r>
</w:hlink>
</w:wordDocument>"#
        .as_bytes();
    let links = extract_hyperlinks(xml);
    assert_eq!(links.len(), 1);
    assert_eq!(links[0].text, "Федеральный закон N 360-ФЗ");
}

#[test]
fn real_44fz_hyperlinks() {
    let path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../")
        .join("consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");
    let xml = std::fs::read(&path);
    if xml.is_err() {
        eprintln!("SKIP: consru_export not available");
        return;
    }
    let links = extract_hyperlinks(&xml.unwrap());
    let internal = links.iter().filter(|l| l.is_internal()).count();
    let external = links.iter().filter(|l| l.is_external()).count();
    println!(
        "44-ФЗ: total={}, internal={}, external={}",
        links.len(),
        internal,
        external
    );
    assert!(
        links.len() > 1000,
        "44-ФЗ must have 1000+ hyperlinks; got {}",
        links.len()
    );
    assert!(internal > external, "internal links must dominate");
}
