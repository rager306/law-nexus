//! Catalog page-index port: join an offline token to the legal-identity keys
//! `(bank, document_key)` that the corpus pageindex is addressed by.
//!
//! This is a separate port from [`crate::catalog::CatalogPort`] (resolves a
//! consid via `consultant_source_locators.offline_uri`) and from
//! [`crate::catalog_anchor::CatalogAnchorPort`] (resolves a document's own
//! self-URI via `editions.relative_path` / `editions.source_id`). Per ADR-0015
//! it gets its own shared contract suite.
//!
//! Hexagonal: trait defined here; [`InMemoryPageIndexCatalog`] for tests; the
//! read-only SQLite adapter lives in [`crate::catalog_sqlite`]. ADR-0030
//! D1/D6, R1000 (supporting-only), ADR-0015.

use std::collections::BTreeMap;

use crate::catalog::CatalogError;

/// One catalog legal-identity row: the `(bank, document_key)` address that the
/// corpus pageindex joins against.
///
/// `document_key` is the catalog `INTEGER` rendered as text, matching the
/// `(bank, document_key)` key space of the pageindex; it is never decoded or
/// derived from a file path.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct CatalogPageIndexRecord {
    pub bank: String,
    pub document_key: String,
}

/// Port for joining an offline token to its catalog `(bank, document_key)`
/// identities.
///
/// Implementations: [`crate::SqliteCatalog`], [`InMemoryPageIndexCatalog`].
/// The join is byte-exact against the stored `offline_uri`: the token is never
/// decoded. A genuine miss is `Ok(vec![])`, never an error — a token absent
/// from the catalog is an honest "unresolved" outcome, not a failure. An empty
/// input is rejected before any query. Results are deterministically sorted and
/// de-duplicated by `(bank, document_key)`.
pub trait PageIndexCatalogPort {
    fn lookup_by_offline_token(
        &self,
        offline_token: &str,
    ) -> Result<Vec<CatalogPageIndexRecord>, CatalogError>;
}

/// Normalize a raw record list into the contract result: deduplicated by
/// `(bank, document_key)` and sorted ascending.
fn normalize(mut records: Vec<CatalogPageIndexRecord>) -> Vec<CatalogPageIndexRecord> {
    records.sort();
    records.dedup();
    records
}

/// In-memory page-index catalog for testing. Maps an offline token to the raw
/// `(bank, document_key)` rows the adapter would observe; lookup applies the
/// same normalization (sort + dedup) as the SQLite adapter.
#[derive(Debug, Clone, Default)]
pub struct InMemoryPageIndexCatalog {
    rows: BTreeMap<String, Vec<CatalogPageIndexRecord>>,
}

impl InMemoryPageIndexCatalog {
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert one raw `(bank, document_key)` row returned for a token lookup.
    /// Duplicates are tolerated and collapsed at lookup time.
    pub fn insert(&mut self, offline_token: &str, bank: &str, document_key: &str) {
        self.rows
            .entry(offline_token.to_owned())
            .or_default()
            .push(CatalogPageIndexRecord {
                bank: bank.to_owned(),
                document_key: document_key.to_owned(),
            });
    }
}

impl PageIndexCatalogPort for InMemoryPageIndexCatalog {
    fn lookup_by_offline_token(
        &self,
        offline_token: &str,
    ) -> Result<Vec<CatalogPageIndexRecord>, CatalogError> {
        if offline_token.is_empty() {
            return Err(CatalogError::new(
                "lookup-by-offline-token",
                "empty offline token",
            ));
        }
        Ok(normalize(
            self.rows.get(offline_token).cloned().unwrap_or_default(),
        ))
    }
}

/// Shared [`PageIndexCatalogPort`] contract helpers (ADR-0015). Exercised
/// against [`InMemoryPageIndexCatalog`] and the read-only SQLite adapter.
pub mod contract {
    use super::{CatalogPageIndexRecord, PageIndexCatalogPort};

    /// A hit returns exactly the expected rows, in ascending `(bank,
    /// document_key)` order (deterministic order is part of the contract).
    pub fn lookup_found_exact(
        port: &dyn PageIndexCatalogPort,
        offline_token: &str,
        expected: &[CatalogPageIndexRecord],
    ) {
        let got = port
            .lookup_by_offline_token(offline_token)
            .expect("page-index catalog lookup should succeed");
        assert_eq!(got, expected, "lookup must return the exact expected rows");
    }

    /// A genuine miss is `Ok(vec![])`, never an error.
    pub fn lookup_missing_is_empty(port: &dyn PageIndexCatalogPort, offline_token: &str) {
        let got = port
            .lookup_by_offline_token(offline_token)
            .expect("page-index catalog miss must be Ok(vec![]), not a failure");
        assert!(got.is_empty(), "a miss must yield an empty result");
    }

    /// An extracted act number is not a token: it must not join by exact token
    /// (the number is encrypted inside the offline token). Zero match.
    pub fn extracted_number_zero_match(port: &dyn PageIndexCatalogPort, number: &str) {
        let got = port
            .lookup_by_offline_token(number)
            .expect("negative probe must not fail");
        assert!(
            got.is_empty(),
            "extracted number {number} must not join by exact token"
        );
    }

    /// Ordering is deterministic: the same lookup twice yields identical
    /// ascending order.
    pub fn deterministic_sorted_dedup(
        port: &dyn PageIndexCatalogPort,
        offline_token: &str,
        expected: &[CatalogPageIndexRecord],
    ) {
        let first = port
            .lookup_by_offline_token(offline_token)
            .expect("lookup should succeed");
        let second = port
            .lookup_by_offline_token(offline_token)
            .expect("lookup should succeed");
        assert_eq!(first, second, "repeated lookups must be identical");
        assert_eq!(first, expected, "rows must be sorted and deduplicated");
        let mut sorted = first.clone();
        sorted.sort();
        sorted.dedup();
        assert_eq!(
            first, sorted,
            "rows must already be sorted and deduplicated"
        );
    }

    pub fn empty_input_rejected(port: &dyn PageIndexCatalogPort) {
        let err = port
            .lookup_by_offline_token("")
            .expect_err("empty offline token must be rejected before a catalog probe");
        assert_eq!(err.operation(), "lookup-by-offline-token");
        assert!(!err.detail().is_empty());
        assert!(!err.to_string().is_empty());
    }
}
