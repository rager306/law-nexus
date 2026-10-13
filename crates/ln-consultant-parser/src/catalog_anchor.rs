//! Catalog anchor port: resolve a corpus document to its own Consultant URI
//! anchor by manifest-relative path or by catalog `source_id`.
//!
//! The self-URI of a corpus document is absent from its own XML; it only comes
//! from the catalog where `editions.relative_path = "exports/" + <manifest
//! relative_path>` and `editions.source_id` is the full offline token. This is
//! a separate port from [`crate::catalog::CatalogPort`] (which resolves consids
//! via `consultant_source_locators.offline_uri`), so it gets its own shared
//! contract suite per ADR-0015.
//!
//! Hexagonal: trait defined here; [`InMemoryCatalogAnchor`] for tests; the
//! read-only SQLite adapter lives in [`crate::catalog_sqlite`]. ADR-0030 D1,
//! R1000 (supporting-only), ADR-0015.

use std::collections::HashMap;

use crate::catalog::CatalogError;

/// Corpus path prefix in the catalog. `editions.relative_path` stores
/// `"exports/" + <manifest relative_path>`; the port accepts the bare manifest
/// path and the adapter binds the prefix.
pub const EXPORTS_PREFIX: &str = "exports/";

/// Build the catalog `editions.relative_path` value for a manifest path.
pub fn exports_path(manifest_relative_path: &str) -> String {
    format!("{EXPORTS_PREFIX}{manifest_relative_path}")
}

/// One anchor resolution row: the catalog identity of a corpus document.
///
/// `source_id` is the catalog identifier verbatim — for the corpus this is the
/// full `consultantplus://offline/ref=…` offline token, never decoded or
/// normalized.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CatalogAnchorRecord {
    /// Catalog `editions.relative_path` (the `exports/…` form), if present.
    pub relative_path: Option<String>,
    /// Catalog `editions.source_id` (the offline token for corpus rows).
    pub source_id: String,
    /// Catalog `editions.edition_id`, if present.
    pub edition_id: Option<String>,
}

/// Port for resolving a corpus document to its consultant URI anchor.
///
/// Implementations: [`crate::SqliteCatalog`], [`InMemoryCatalogAnchor`].
/// A genuine miss is `Ok(None)`, never an error — a document absent from the
/// catalog is an honest "unresolved" outcome, not a failure. An empty input is
/// rejected before any query.
pub trait CatalogAnchorPort {
    /// Resolve by manifest-relative path (`npa/x.xml`). The adapter matches
    /// `editions.relative_path = EXPORTS_PREFIX || <manifest_relative_path>`.
    fn lookup_by_relative_path(
        &self,
        manifest_relative_path: &str,
    ) -> Result<Option<CatalogAnchorRecord>, CatalogError>;

    /// Resolve by catalog `source_id` (exact-token join; no decoding).
    fn lookup_by_source_id(
        &self,
        source_id: &str,
    ) -> Result<Option<CatalogAnchorRecord>, CatalogError>;
}

/// In-memory anchor catalog for testing. Keeps separate maps for the two lookup
/// keys so a double can model SQLite's latest-edition tie-break by keying the
/// winner per lookup surface.
#[derive(Debug, Clone, Default)]
pub struct InMemoryCatalogAnchor {
    by_path: HashMap<String, CatalogAnchorRecord>,
    by_source_id: HashMap<String, CatalogAnchorRecord>,
}

impl InMemoryCatalogAnchor {
    pub fn new() -> Self {
        Self::default()
    }

    /// Insert the record returned for a manifest-relative path lookup.
    pub fn insert_by_relative_path(
        &mut self,
        manifest_relative_path: &str,
        record: CatalogAnchorRecord,
    ) {
        self.by_path
            .insert(manifest_relative_path.to_owned(), record);
    }

    /// Insert the record returned for a `source_id` lookup.
    pub fn insert_by_source_id(&mut self, source_id: &str, record: CatalogAnchorRecord) {
        self.by_source_id.insert(source_id.to_owned(), record);
    }
}

impl CatalogAnchorPort for InMemoryCatalogAnchor {
    fn lookup_by_relative_path(
        &self,
        manifest_relative_path: &str,
    ) -> Result<Option<CatalogAnchorRecord>, CatalogError> {
        if manifest_relative_path.is_empty() {
            return Err(CatalogError::new(
                "lookup-by-relative-path",
                "empty relative path",
            ));
        }
        Ok(self.by_path.get(manifest_relative_path).cloned())
    }

    fn lookup_by_source_id(
        &self,
        source_id: &str,
    ) -> Result<Option<CatalogAnchorRecord>, CatalogError> {
        if source_id.is_empty() {
            return Err(CatalogError::new("lookup-by-source-id", "empty source id"));
        }
        Ok(self.by_source_id.get(source_id).cloned())
    }
}

/// Shared [`CatalogAnchorPort`] contract helpers (ADR-0015). Exercised against
/// [`InMemoryCatalogAnchor`] and the read-only SQLite adapter.
pub mod contract {
    use super::{CatalogAnchorPort, CatalogAnchorRecord, EXPORTS_PREFIX};

    /// The manifest-relative path implied by a catalog `relative_path`.
    fn manifest_of(record: &CatalogAnchorRecord) -> &str {
        record
            .relative_path
            .as_deref()
            .expect("expected anchor record must carry a relative_path")
            .strip_prefix(EXPORTS_PREFIX)
            .expect("anchor record relative_path must start with the exports prefix")
    }

    pub fn lookup_by_path_found_exact(
        port: &dyn CatalogAnchorPort,
        expected: &CatalogAnchorRecord,
    ) {
        let got = port
            .lookup_by_relative_path(manifest_of(expected))
            .expect("anchor path lookup should succeed");
        assert_eq!(got.as_ref(), Some(expected));
    }

    pub fn lookup_by_path_missing_is_none(
        port: &dyn CatalogAnchorPort,
        manifest_relative_path: &str,
    ) {
        let got = port
            .lookup_by_relative_path(manifest_relative_path)
            .expect("anchor path miss should be Ok(None), not a failure");
        assert_eq!(got, None);
    }

    pub fn lookup_by_source_id_found_exact(
        port: &dyn CatalogAnchorPort,
        expected: &CatalogAnchorRecord,
    ) {
        let got = port
            .lookup_by_source_id(&expected.source_id)
            .expect("anchor source-id lookup should succeed");
        assert_eq!(got.as_ref(), Some(expected));
    }

    pub fn lookup_by_source_id_missing_is_none(port: &dyn CatalogAnchorPort, source_id: &str) {
        let got = port
            .lookup_by_source_id(source_id)
            .expect("anchor source-id miss should be Ok(None), not a failure");
        assert_eq!(got, None);
    }

    pub fn empty_input_rejected(port: &dyn CatalogAnchorPort) {
        let path_err = port
            .lookup_by_relative_path("")
            .expect_err("empty relative path must be rejected before a catalog probe");
        assert_eq!(path_err.operation(), "lookup-by-relative-path");
        assert!(!path_err.detail().is_empty());

        let source_err = port
            .lookup_by_source_id("")
            .expect_err("empty source id must be rejected before a catalog probe");
        assert_eq!(source_err.operation(), "lookup-by-source-id");
        assert!(!source_err.detail().is_empty());
    }

    pub fn latest_edition_tie_break(
        port: &dyn CatalogAnchorPort,
        source_id: &str,
        expected: &CatalogAnchorRecord,
    ) {
        let got = port
            .lookup_by_source_id(source_id)
            .expect("anchor tie-break lookup should succeed");
        assert_eq!(got.as_ref(), Some(expected));
    }
}
