//! Catalog port: resolve consid tokens to document metadata.
//! Hexagonal: trait defined here, SQLite adapter provided by caller.
//! ADR-0025/0026.

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

/// Port for resolving consids to document metadata.
/// Implementations: SQLite catalog (consru_export), in-memory (tests).
pub trait CatalogPort {
    fn lookup(&self, consid: &str) -> Option<CatalogRecord>;
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
        self.records.insert(
            consid.to_owned(),
            CatalogRecord {
                consid: consid.to_owned(),
                title: Some(title.to_owned()),
                kind: Some("zakon".to_owned()),
                number: Some(number.to_owned()),
                document_date: None,
                in_catalog: true,
            },
        );
    }
}

impl CatalogPort for InMemoryCatalog {
    fn lookup(&self, consid: &str) -> Option<CatalogRecord> {
        self.records.get(consid).cloned()
    }
}

/// Resolve a list of consids against a catalog port.
/// Returns records for all consids (in_catalog=false if not found).
pub fn resolve_consids(port: &dyn CatalogPort, consids: &[String]) -> Vec<CatalogRecord> {
    consids
        .iter()
        .map(|c| {
            port.lookup(c).unwrap_or(CatalogRecord {
                consid: c.clone(),
                title: None,
                kind: None,
                number: None,
                document_date: None,
                in_catalog: false,
            })
        })
        .collect()
}

/// Count how many consids are resolved (in_catalog=true).
pub fn coverage_summary(records: &[CatalogRecord]) -> (usize, usize) {
    let resolved = records.iter().filter(|r| r.in_catalog).count();
    let total = records.len();
    (resolved, total)
}
