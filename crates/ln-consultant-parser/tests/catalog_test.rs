//! Catalog port tests: consid resolution, coverage, in-memory catalog.

use ln_consultant_parser::catalog::{
    coverage_summary, resolve_consids, CatalogPort, InMemoryCatalog,
};

#[test]
fn in_memory_catalog_lookup() {
    let mut cat = InMemoryCatalog::new();
    cat.insert(
        "consultantplus://offline/ref=TOKEN1",
        "ФЗ о контрактной системе",
        "44-ФЗ",
    );
    let rec = cat.lookup("consultantplus://offline/ref=TOKEN1");
    assert!(rec.is_some());
    let rec = rec.unwrap();
    assert_eq!(rec.number.as_deref(), Some("44-ФЗ"));
    assert!(rec.in_catalog);
}

#[test]
fn unknown_consid_returns_none() {
    let cat = InMemoryCatalog::new();
    assert!(cat.lookup("unknown").is_none());
}

#[test]
fn resolve_mixed_consids() {
    let mut cat = InMemoryCatalog::new();
    cat.insert("ref1", "Закон N 1", "1-ФЗ");
    cat.insert("ref3", "Закон N 3", "3-ФЗ");

    let consids = vec!["ref1".to_owned(), "ref2".to_owned(), "ref3".to_owned()];
    let records = resolve_consids(&cat, &consids);

    assert_eq!(records.len(), 3);
    assert!(records[0].in_catalog);
    assert!(!records[1].in_catalog);
    assert!(records[2].in_catalog);
}

#[test]
fn coverage_summary_counts() {
    let mut cat = InMemoryCatalog::new();
    cat.insert("ref1", "A", "1-ФЗ");
    cat.insert("ref2", "B", "2-ФЗ");

    let consids = vec![
        "ref1".to_owned(),
        "ref2".to_owned(),
        "ref3".to_owned(),
        "ref4".to_owned(),
    ];
    let records = resolve_consids(&cat, &consids);
    let (resolved, total) = coverage_summary(&records);

    assert_eq!(resolved, 2);
    assert_eq!(total, 4);
}
