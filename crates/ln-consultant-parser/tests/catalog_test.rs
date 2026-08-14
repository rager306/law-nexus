//! Catalog port tests: Result lookup, coverage, InMemory shared contract.

use ln_consultant_parser::catalog::{
    contract, coverage_summary, resolve_consids, CatalogError, CatalogPort, CatalogRecord,
    InMemoryCatalog,
};

#[test]
fn in_memory_catalog_lookup() {
    let mut cat = InMemoryCatalog::new();
    cat.insert(
        "consultantplus://offline/ref=TOKEN1",
        "ФЗ о контрактной системе",
        "44-ФЗ",
    );
    let rec = cat
        .lookup("consultantplus://offline/ref=TOKEN1")
        .expect("in-memory lookup is infallible for a present key");
    assert!(rec.is_some());
    let rec = rec.unwrap();
    assert_eq!(rec.number.as_deref(), Some("44-ФЗ"));
    assert!(rec.in_catalog);
}

#[test]
fn unknown_consid_returns_none() {
    let cat = InMemoryCatalog::new();
    assert!(cat
        .lookup("unknown")
        .expect("genuine miss is Ok(None)")
        .is_none());
}

#[test]
fn resolve_mixed_consids() {
    let mut cat = InMemoryCatalog::new();
    cat.insert("ref1", "Закон N 1", "1-ФЗ");
    cat.insert("ref3", "Закон N 3", "3-ФЗ");

    let consids = vec!["ref1".to_owned(), "ref2".to_owned(), "ref3".to_owned()];
    let records = resolve_consids(&cat, &consids).expect("mixed resolve stays Ok");

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
    let records = resolve_consids(&cat, &consids).expect("coverage resolve stays Ok");
    let (resolved, total) = coverage_summary(&records);

    assert_eq!(resolved, 2);
    assert_eq!(total, 4);
}

#[test]
fn in_memory_shared_contract_found_missing_and_latest() {
    let mut cat = InMemoryCatalog::new();
    let found = CatalogRecord {
        consid: "offline://token-found".to_owned(),
        title: Some("DOC-TITLE-A".to_owned()),
        kind: Some("KIND-A".to_owned()),
        number: Some("NUM-LATEST".to_owned()),
        document_date: Some("2024-01-23".to_owned()),
        in_catalog: true,
    };
    cat.insert_record(found.clone());

    contract::lookup_found_exact(&cat, &found);
    contract::lookup_missing_is_none(&cat, "offline://token-missing");
    contract::resolve_missing_is_not_in_catalog(&cat, "offline://token-missing");
    contract::lookup_metadata_exact(&cat, "offline://token-found", "NUM-LATEST", "2024-01-23");
    contract::lookup_empty_consid_rejected(&cat);
}

#[test]
fn resolve_consids_propagates_adapter_failure() {
    struct FailingPort;

    impl CatalogPort for FailingPort {
        fn lookup(&self, _consid: &str) -> Result<Option<CatalogRecord>, CatalogError> {
            Err(CatalogError::new("lookup", "forced adapter failure"))
        }
    }

    let err = resolve_consids(&FailingPort, &["token".to_owned()])
        .expect_err("adapter failure must not become in_catalog=false");
    assert_eq!(err.operation(), "lookup");
    assert_eq!(err.detail(), "forced adapter failure");
}

#[test]
fn catalog_error_is_bounded_and_displayable() {
    let err = CatalogError::new("lookup", "x".repeat(400));
    assert_eq!(err.operation(), "lookup");
    assert!(err.detail().chars().count() <= 240);
    assert!(err.to_string().starts_with("catalog lookup failed:"));
    let _: &dyn std::error::Error = &err;
}
