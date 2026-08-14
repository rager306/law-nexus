//! Catalog port: resolve consid tokens to document metadata.
//! Hexagonal: trait defined here; InMemory for tests; SQLite adapter in
//! [`crate::catalog_sqlite`]. ADR-0025/0026, R085, ADR-0015.

use std::error::Error;
use std::fmt;

/// Maximum characters retained in a [`CatalogError`] detail.
const MAX_DETAIL_CHARS: usize = 240;

/// Document metadata resolved from a consid token.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CatalogRecord {
    pub consid: String,
    pub title: Option<String>,
    pub kind: Option<String>,
    pub number: Option<String>,
    pub document_date: Option<String>,
    pub in_catalog: bool,
}

/// Contextual catalog failure. Detail is bounded and must not carry raw
/// legal text or a row payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CatalogError {
    operation: &'static str,
    detail: String,
}

impl CatalogError {
    pub fn new(operation: &'static str, detail: impl Into<String>) -> Self {
        Self {
            operation,
            detail: bound_detail(detail.into()),
        }
    }

    pub fn operation(&self) -> &'static str {
        self.operation
    }

    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for CatalogError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "catalog {} failed: {}",
            self.operation, self.detail
        )
    }
}

impl Error for CatalogError {}

fn bound_detail(raw: String) -> String {
    let mut out = String::new();
    for ch in raw.chars() {
        if ch.is_control() {
            continue;
        }
        if out.chars().count() >= MAX_DETAIL_CHARS {
            break;
        }
        out.push(ch);
    }
    out
}

/// Port for resolving consids to document metadata.
/// Implementations: [`crate::SqliteCatalog`], [`InMemoryCatalog`].
pub trait CatalogPort {
    fn lookup(&self, consid: &str) -> Result<Option<CatalogRecord>, CatalogError>;
}

/// In-memory catalog for testing. Maps consid → CatalogRecord.
#[derive(Debug, Clone, Default)]
pub struct InMemoryCatalog {
    records: std::collections::HashMap<String, CatalogRecord>,
}

impl InMemoryCatalog {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, consid: &str, title: &str, number: &str) {
        self.insert_record(CatalogRecord {
            consid: consid.to_owned(),
            title: Some(title.to_owned()),
            kind: Some("zakon".to_owned()),
            number: Some(number.to_owned()),
            document_date: None,
            in_catalog: true,
        });
    }

    pub fn insert_record(&mut self, record: CatalogRecord) {
        self.records.insert(record.consid.clone(), record);
    }
}

impl CatalogPort for InMemoryCatalog {
    fn lookup(&self, consid: &str) -> Result<Option<CatalogRecord>, CatalogError> {
        if consid.is_empty() {
            return Err(CatalogError::new("lookup", "empty consid"));
        }
        Ok(self.records.get(consid).cloned())
    }
}

/// Resolve a list of consids against a catalog port.
/// Genuine misses become `in_catalog=false`. Adapter/schema failures propagate.
pub fn resolve_consids(
    port: &dyn CatalogPort,
    consids: &[String],
) -> Result<Vec<CatalogRecord>, CatalogError> {
    consids
        .iter()
        .map(|consid| {
            Ok(port.lookup(consid)?.unwrap_or_else(|| CatalogRecord {
                consid: consid.clone(),
                title: None,
                kind: None,
                number: None,
                document_date: None,
                in_catalog: false,
            }))
        })
        .collect()
}

/// Count how many consids are resolved (`in_catalog=true`).
pub fn coverage_summary(records: &[CatalogRecord]) -> (usize, usize) {
    let resolved = records.iter().filter(|record| record.in_catalog).count();
    let total = records.len();
    (resolved, total)
}

/// Shared CatalogPort contract helpers (ADR-0015). Exercised against InMemory
/// and the read-only SQLite adapter.
pub mod contract {
    use super::{resolve_consids, CatalogPort, CatalogRecord};

    pub fn lookup_found_exact(port: &dyn CatalogPort, expected: &CatalogRecord) {
        let got = port
            .lookup(&expected.consid)
            .expect("catalog lookup should succeed");
        assert_eq!(got.as_ref(), Some(expected));
    }

    pub fn lookup_missing_is_none(port: &dyn CatalogPort, consid: &str) {
        let got = port
            .lookup(consid)
            .expect("catalog lookup should succeed for a genuine miss");
        assert_eq!(got, None);
    }

    pub fn resolve_missing_is_not_in_catalog(port: &dyn CatalogPort, consid: &str) {
        let records = resolve_consids(port, &[consid.to_owned()])
            .expect("resolve_consids should succeed for a genuine miss");
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].consid, consid);
        assert!(!records[0].in_catalog);
        assert!(records[0].title.is_none());
        assert!(records[0].kind.is_none());
        assert!(records[0].number.is_none());
        assert!(records[0].document_date.is_none());
    }

    pub fn lookup_metadata_exact(
        port: &dyn CatalogPort,
        consid: &str,
        number: &str,
        document_date: &str,
    ) {
        let record = port
            .lookup(consid)
            .expect("catalog lookup should succeed")
            .expect("catalog metadata should be present");
        assert!(record.in_catalog);
        assert_eq!(record.consid, consid);
        assert_eq!(record.number.as_deref(), Some(number));
        assert_eq!(record.document_date.as_deref(), Some(document_date));
    }

    pub fn lookup_empty_consid_rejected(port: &dyn CatalogPort) {
        let err = port
            .lookup("")
            .expect_err("empty consid must be rejected before a catalog probe");
        assert_eq!(err.operation(), "lookup");
        assert!(!err.detail().is_empty());
        assert!(!err.to_string().is_empty());
    }
}
