//! Read-only SQLite adapter for [`crate::catalog::CatalogPort`].
//! Opens with `SQLITE_OPEN_READ_ONLY` and maps a genuine miss to `Ok(None)`.

use std::collections::BTreeMap;
use std::path::Path;

use rusqlite::{Connection, OpenFlags, OptionalExtension};

use crate::catalog::{CatalogError, CatalogPort, CatalogRecord};
use crate::catalog_anchor::{CatalogAnchorPort, CatalogAnchorRecord, EXPORTS_PREFIX};
use crate::page_index_catalog::{CatalogPageIndexRecord, PageIndexCatalogPort};

/// Anchor lookup by manifest path. The `exports/` prefix is a bound `?1`
/// parameter (never interpolated user data) and the manifest path is `?2`, so
/// `editions.relative_path = EXPORTS_PREFIX || <manifest_relative_path>`.
const LOOKUP_BY_RELATIVE_PATH_SQL: &str = "
SELECT
    e.relative_path AS relative_path,
    e.source_id AS source_id,
    e.edition_id AS edition_id
FROM editions AS e
WHERE e.relative_path = ?1 || ?2
ORDER BY
    COALESCE(e.edition_number, 0) DESC,
    e.revision_date DESC,
    e.edition_id DESC
LIMIT 1
";

/// Anchor lookup by catalog `source_id` (exact-token join; no decoding). Same
/// latest-edition tie-break as the locator lookup.
const LOOKUP_BY_SOURCE_ID_SQL: &str = "
SELECT
    e.relative_path AS relative_path,
    e.source_id AS source_id,
    e.edition_id AS edition_id
FROM editions AS e
WHERE e.source_id = ?1
ORDER BY
    COALESCE(e.edition_number, 0) DESC,
    e.revision_date DESC,
    e.edition_id DESC
LIMIT 1
";

/// Page-index catalog join: an offline token to its catalog `(bank,
/// document_key)` legal identities across both observed surfaces. The join is
/// byte-exact (`?1` is a bound parameter, never interpolated and never
/// decoded). `UNION` de-duplicates rows shared by both surfaces; `ORDER BY`
/// fixes the ascending `(bank, document_key)` order. `document_key` is an
/// `INTEGER` in the schema and is cast to `TEXT` so it maps into the pageindex
/// key space. A genuine miss yields zero rows (an empty result), not an error.
const LOOKUP_PAGE_INDEX_BY_OFFLINE_TOKEN_SQL: &str = "
SELECT bank, CAST(document_key AS TEXT) AS document_key
FROM court_items
WHERE offline_uri = ?1
UNION
SELECT r.bank AS bank, CAST(r.document_key AS TEXT) AS document_key
FROM consultant_source_locators AS loc
JOIN consultant_source_records AS r ON r.source_record_id = loc.source_record_id
WHERE loc.offline_uri = ?1
ORDER BY bank ASC, document_key ASC
";

/// Bulk page-index token map: one pass over both observed surfaces returning
/// the same `offline_uri → [(bank, document_key)]` join that
/// [`PageIndexCatalogPort::lookup_by_offline_token`] produces per token. The
/// corpus producer calls this once instead of issuing ~36k full scans of the
/// unindexed `court_items.offline_uri`; the exact-token join, the `CAST`, and
/// the read-only posture are identical. `offline_uri` NULL/empty rows are
/// skipped because an empty token is rejected before any lookup.
const LOAD_PAGE_INDEX_TOKEN_MAP_SQL: &str = "
SELECT
    offline_uri AS offline_uri,
    bank AS bank,
    CAST(document_key AS TEXT) AS document_key
FROM court_items
WHERE offline_uri IS NOT NULL AND offline_uri <> ''
UNION
SELECT
    loc.offline_uri AS offline_uri,
    r.bank AS bank,
    CAST(r.document_key AS TEXT) AS document_key
FROM consultant_source_locators AS loc
JOIN consultant_source_records AS r ON r.source_record_id = loc.source_record_id
WHERE loc.offline_uri IS NOT NULL AND loc.offline_uri <> ''
";

/// Bulk edition join map: one read-only pass over `editions` returning the
/// catalog identity of every corpus document keyed by its manifest
/// `relative_path` (the `exports/` prefix is stripped in Rust, never in SQL).
/// Unlike [`LOOKUP_BY_RELATIVE_PATH_SQL`] this is not a latest-edition
/// tie-break probe: it returns the `document_id` and `edition_number` that the
/// FRBR-bridge join needs, one row per path (`editions.relative_path` is
/// `UNIQUE`), byte-exact and never decoded or normalized. NULL/empty paths are
/// skipped (they cannot key a manifest row).
const LOAD_EDITION_JOIN_MAP_SQL: &str = "
SELECT
    relative_path AS relative_path,
    source_id AS source_id,
    edition_id AS edition_id,
    document_id AS document_id,
    edition_number AS edition_number,
    revision_date AS revision_date
FROM editions
WHERE relative_path IS NOT NULL AND relative_path <> ''
";

const LOOKUP_SQL: &str = "
SELECT
    d.title AS title,
    d.kind AS kind,
    e.number AS number,
    e.document_date AS document_date
FROM consultant_source_locators AS loc
LEFT JOIN documents AS d
    ON d.source_id = loc.catalog_source_id
LEFT JOIN editions AS e
    ON e.source_id = d.source_id
WHERE loc.offline_uri = ?1
ORDER BY
    COALESCE(e.edition_number, 0) DESC,
    e.revision_date DESC,
    e.edition_id DESC
LIMIT 1
";

/// Read-only Consultant catalog backed by the observed locator/document/edition schema.
#[derive(Debug)]
pub struct SqliteCatalog {
    conn: Connection,
}

impl SqliteCatalog {
    /// Open an existing catalog file read-only. Fails if the path is absent.
    pub fn open_read_only(path: impl AsRef<Path>) -> Result<Self, CatalogError> {
        let flags = OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_FULL_MUTEX;
        let conn = Connection::open_with_flags(path.as_ref(), flags)
            .map_err(|err| map_sqlite("open", err))?;
        Ok(Self { conn })
    }

    /// Report whether SQLite opened the main database read-only.
    pub fn is_read_only(&self) -> Result<bool, CatalogError> {
        self.conn
            .is_readonly("main")
            .map_err(|err| map_sqlite("read-only-check", err))
    }

    /// One golden relation row for classifier P/R measurement (M169 S04 T02).
    /// Returns `(item_id, relation_type, raw_tooltip)` for the golden set:
    /// explicit `amends` edges only. Carries no raw text beyond the catalog's
    /// own title strings; item ids let the recall report name misses without
    /// echoing tooltip text.
    pub fn golden_relation_rows(&self) -> Result<Vec<(i64, String, String)>, CatalogError> {
        let mut stmt = self
            .conn
            .prepare(
                "SELECT item_id, relation_type, raw_tooltip FROM legal_relation_items
                 WHERE relation_type = 'amends'
                   AND normalization_status = 'explicit'
                   AND raw_tooltip IS NOT NULL AND length(raw_tooltip) > 0",
            )
            .map_err(|err| map_sqlite("prepare", err))?;
        let rows = stmt
            .query_map([], |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                ))
            })
            .map_err(|err| map_sqlite("query", err))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|err| map_sqlite("rows", err))
    }

    /// Read-only, bounded read of the relation run that roots an edge set plus
    /// its explicit `amends` edge rows (M209/S03 T02, R070).
    ///
    /// Mirrors [`Self::golden_relation_rows`] SQL discipline: constant
    /// statements with the `relation_type` / `normalization_status` predicates
    /// inline and the row bound passed as a *bound* `?2` parameter, never
    /// interpolated. No prose column is selected (`raw_tooltip` and
    /// `visible_text` are absent from the projection), so licensed provider
    /// text cannot leave the catalog through this method. The connection stays
    /// on `SQLITE_OPEN_READ_ONLY`; nothing here writes or mutates schema, and a
    /// missing table or run maps to `Ok(None)` / a typed `CatalogError` rather
    /// than to an empty success.
    pub fn amends_edge_set(&self, limit: u32) -> Result<Option<AmendsEdgeSet>, CatalogError> {
        let runs_total: i64 = self
            .conn
            .query_row("SELECT COUNT(*) FROM legal_relation_runs", [], |row| {
                row.get(0)
            })
            .map_err(|err| map_sqlite("count-relation-runs", err))?;
        let run = self
            .conn
            .query_row(
                "SELECT run_id, profile, root_source_id, status,
                        source_artifact_sha256, table_artifact_sha256
                 FROM legal_relation_runs
                 ORDER BY run_id LIMIT 1",
                [],
                |row| {
                    Ok((
                        row.get::<_, i64>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, String>(3)?,
                        row.get::<_, String>(4)?,
                        row.get::<_, String>(5)?,
                    ))
                },
            )
            .optional()
            .map_err(|err| map_sqlite("query-relation-run", err))?;
        let Some((run_id, profile, root_source_id, status, source_sha, table_sha)) = run else {
            return Ok(None);
        };

        let mut stmt = self
            .conn
            .prepare(
                "SELECT item_id, relation_type, normalization_status, export_status, bank,
                        document_key, field, destination_json, edition_id
                 FROM legal_relation_items
                 WHERE run_id = ?1
                   AND relation_type = 'amends'
                   AND normalization_status = 'explicit'
                 ORDER BY item_id
                 LIMIT ?2",
            )
            .map_err(|err| map_sqlite("prepare-amends", err))?;
        let rows = stmt
            .query_map(rusqlite::params![run_id, i64::from(limit)], |row| {
                Ok(AmendsEdgeRow {
                    item_id: row.get(0)?,
                    relation_type: row.get(1)?,
                    normalization_status: row.get(2)?,
                    export_status: row.get(3)?,
                    bank: row.get(4)?,
                    document_key: row.get(5)?,
                    field: row.get(6)?,
                    destination_json: row.get(7)?,
                    edition_id: row.get(8)?,
                })
            })
            .map_err(|err| map_sqlite("query-amends", err))?;
        let edges = rows
            .collect::<Result<Vec<_>, _>>()
            .map_err(|err| map_sqlite("amends-rows", err))?;

        Ok(Some(AmendsEdgeSet {
            runs_total,
            run_id,
            profile,
            root_source_id,
            status,
            source_artifact_sha256: source_sha,
            table_artifact_sha256: table_sha,
            edges,
        }))
    }

    /// Negative titles for precision measurement: normative documents whose
    /// titles are not amending acts. Bounded by `limit`. Excludes both the
    /// plural (`внесении изменений`) and singular (`внесении изменения`)
    /// amending phrasings so the negative sample is honest.
    pub fn non_amending_titles(&self, limit: u32) -> Result<Vec<String>, CatalogError> {
        let mut stmt = self
            .conn
            .prepare(
                "SELECT title FROM documents
                 WHERE kind = 'normative' AND title IS NOT NULL
                   AND title NOT LIKE '%внесении изменений%'
                   AND title NOT LIKE '%внесении изменения%'
                   AND title NOT LIKE '%внести изменения%'
                   AND title NOT LIKE '%внести изменение%'
                 ORDER BY source_id LIMIT ?1",
            )
            .map_err(|err| map_sqlite("prepare", err))?;
        let rows = stmt
            .query_map([limit], |row| row.get::<_, String>(0))
            .map_err(|err| map_sqlite("query", err))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|err| map_sqlite("rows", err))
    }
}

impl CatalogPort for SqliteCatalog {
    fn lookup(&self, consid: &str) -> Result<Option<CatalogRecord>, CatalogError> {
        if consid.is_empty() {
            return Err(CatalogError::new("lookup", "empty consid"));
        }

        let row = self
            .conn
            .query_row(LOOKUP_SQL, [consid], |row| {
                Ok(RawLookup {
                    title: row.get("title")?,
                    kind: row.get("kind")?,
                    number: row.get("number")?,
                    document_date: row.get("document_date")?,
                })
            })
            .optional()
            .map_err(|err| map_sqlite("query", err))?;

        match row {
            None => Ok(None),
            Some(raw) => match raw.title {
                Some(title) => Ok(Some(CatalogRecord {
                    consid: consid.to_owned(),
                    title: Some(title),
                    kind: raw.kind,
                    number: raw.number,
                    document_date: raw.document_date,
                    in_catalog: true,
                })),
                None => Err(CatalogError::new(
                    "decode",
                    "locator without document title",
                )),
            },
        }
    }
}

impl CatalogAnchorPort for SqliteCatalog {
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
        let row = self
            .conn
            .query_row(
                LOOKUP_BY_RELATIVE_PATH_SQL,
                rusqlite::params![EXPORTS_PREFIX, manifest_relative_path],
                map_anchor_row,
            )
            .optional()
            .map_err(|err| map_sqlite("lookup-by-relative-path", err))?;
        Ok(row)
    }

    fn lookup_by_source_id(
        &self,
        source_id: &str,
    ) -> Result<Option<CatalogAnchorRecord>, CatalogError> {
        if source_id.is_empty() {
            return Err(CatalogError::new("lookup-by-source-id", "empty source id"));
        }
        let row = self
            .conn
            .query_row(LOOKUP_BY_SOURCE_ID_SQL, [source_id], map_anchor_row)
            .optional()
            .map_err(|err| map_sqlite("lookup-by-source-id", err))?;
        Ok(row)
    }
}

impl PageIndexCatalogPort for SqliteCatalog {
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
        let mut stmt = self
            .conn
            .prepare(LOOKUP_PAGE_INDEX_BY_OFFLINE_TOKEN_SQL)
            .map_err(|err| map_sqlite("lookup-by-offline-token", err))?;
        let rows = stmt
            .query_map([offline_token], |row| {
                Ok(CatalogPageIndexRecord {
                    bank: row.get(0)?,
                    document_key: row.get(1)?,
                })
            })
            .map_err(|err| map_sqlite("lookup-by-offline-token", err))?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|err| map_sqlite("lookup-by-offline-token", err))
    }
}

impl SqliteCatalog {
    /// Bulk-load the page-index token map (one catalog pass).
    ///
    /// Returns the same per-token `(bank, document_key)` rows — sorted and
    /// de-duplicated — that [`PageIndexCatalogPort::lookup_by_offline_token`]
    /// yields, keyed by the byte-exact `offline_uri`. This is a read-only
    /// producer optimization: the corpus pageindex builder uses it to avoid a
    /// full-table scan per token, then serves lookups through the
    /// [`PageIndexCatalogPort`] interface (an in-memory adapter). No token is
    /// decoded or normalized.
    pub fn load_page_index_token_map(
        &self,
    ) -> Result<BTreeMap<String, Vec<CatalogPageIndexRecord>>, CatalogError> {
        let mut stmt = self
            .conn
            .prepare(LOAD_PAGE_INDEX_TOKEN_MAP_SQL)
            .map_err(|err| map_sqlite("load-page-index-token-map", err))?;
        let rows = stmt
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    CatalogPageIndexRecord {
                        bank: row.get(1)?,
                        document_key: row.get(2)?,
                    },
                ))
            })
            .map_err(|err| map_sqlite("load-page-index-token-map", err))?;
        let mut map: BTreeMap<String, Vec<CatalogPageIndexRecord>> = BTreeMap::new();
        for row in rows {
            let (token, record) =
                row.map_err(|err| map_sqlite("load-page-index-token-map", err))?;
            map.entry(token).or_default().push(record);
        }
        for records in map.values_mut() {
            records.sort();
            records.dedup();
        }
        Ok(map)
    }

    /// Bulk-load the edition join map (one catalog pass).
    ///
    /// Keyed by the manifest `relative_path` (the `exports/` prefix is
    /// stripped); the value carries the catalog `source_id` anchor plus the
    /// `edition_id`, `document_id` and `edition_number` that FRBR-bridge
    /// records need (the [`CatalogAnchorPort`] record has only the first
    /// three). Read-only, one pass, no decoding — the same posture as
    /// [`Self::load_page_index_token_map`]. A NULL/empty `relative_path` row is
    /// skipped; a path that does not carry the `exports/` prefix keys on its
    /// raw path.
    pub fn load_edition_join_map(&self) -> Result<BTreeMap<String, EditionJoinRow>, CatalogError> {
        let mut stmt = self
            .conn
            .prepare(LOAD_EDITION_JOIN_MAP_SQL)
            .map_err(|err| map_sqlite("load-edition-join-map", err))?;
        let rows = stmt
            .query_map([], |row| {
                Ok(EditionJoinRow {
                    relative_path: row.get("relative_path")?,
                    source_id: row.get("source_id")?,
                    edition_id: row.get("edition_id")?,
                    document_id: row.get("document_id")?,
                    edition_number: row.get("edition_number")?,
                    revision_date: row.get("revision_date")?,
                })
            })
            .map_err(|err| map_sqlite("load-edition-join-map", err))?;
        let mut map: BTreeMap<String, EditionJoinRow> = BTreeMap::new();
        for row in rows {
            let row = row.map_err(|err| map_sqlite("load-edition-join-map", err))?;
            let key = row
                .relative_path
                .strip_prefix(EXPORTS_PREFIX)
                .unwrap_or(&row.relative_path)
                .to_owned();
            map.insert(key, row);
        }
        Ok(map)
    }
}

/// One `editions` row for the FRBR-bridge join (M224/S07/T02).
///
/// Unlike [`CatalogAnchorRecord`] this carries the catalog `document_id` and
/// `edition_number`; the map that [`SqliteCatalog::load_edition_join_map`]
/// returns is keyed by the manifest `relative_path` (the catalog form is
/// stored here in `relative_path`, `exports/`-prefixed). `source_id` is the
/// anchor token, byte-exact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionJoinRow {
    /// Catalog `editions.relative_path` (the `exports/…` form).
    pub relative_path: String,
    /// Catalog `editions.source_id` (the offline token for corpus rows).
    pub source_id: String,
    /// Catalog `editions.edition_id`, if present.
    pub edition_id: Option<String>,
    /// Catalog `editions.document_id`, if present.
    pub document_id: Option<String>,
    /// Catalog `editions.edition_number`, if present.
    pub edition_number: Option<i64>,
    /// Catalog `editions.revision_date`, if present.
    pub revision_date: Option<String>,
}

fn map_anchor_row(row: &rusqlite::Row<'_>) -> rusqlite::Result<CatalogAnchorRecord> {
    Ok(CatalogAnchorRecord {
        relative_path: row.get("relative_path")?,
        source_id: row.get("source_id")?,
        edition_id: row.get("edition_id")?,
    })
}

/// One explicit `amends` edge row of a catalog relation run.
///
/// Catalog identifiers and status columns only: the projection this struct is
/// built from never selects `raw_tooltip` or `visible_text`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AmendsEdgeRow {
    pub item_id: i64,
    pub relation_type: String,
    pub normalization_status: String,
    pub export_status: String,
    pub bank: String,
    pub document_key: i64,
    pub field: Option<i64>,
    pub destination_json: Option<String>,
    pub edition_id: Option<String>,
}

/// The relation run that roots an edge set, plus its explicit `amends` edges.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AmendsEdgeSet {
    /// How many `legal_relation_runs` rows the catalog carries.
    pub runs_total: i64,
    pub run_id: i64,
    pub profile: String,
    pub root_source_id: String,
    pub status: String,
    pub source_artifact_sha256: String,
    pub table_artifact_sha256: String,
    pub edges: Vec<AmendsEdgeRow>,
}

struct RawLookup {
    title: Option<String>,
    kind: Option<String>,
    number: Option<String>,
    document_date: Option<String>,
}

fn map_sqlite(operation: &'static str, err: rusqlite::Error) -> CatalogError {
    let detail = match &err {
        rusqlite::Error::QueryReturnedNoRows => "no rows".to_owned(),
        rusqlite::Error::InvalidQuery => "invalid query".to_owned(),
        rusqlite::Error::InvalidColumnName(_) => "invalid column".to_owned(),
        rusqlite::Error::InvalidColumnType(_, _, _) => "invalid column type".to_owned(),
        rusqlite::Error::InvalidColumnIndex(_) => "invalid column index".to_owned(),
        rusqlite::Error::FromSqlConversionFailure(_, _, _) => "value decode".to_owned(),
        rusqlite::Error::InvalidParameterCount(_, _) => "parameter count".to_owned(),
        rusqlite::Error::InvalidPath(_) => "invalid path".to_owned(),
        rusqlite::Error::SqliteFailure(code, _) => {
            format!("sqlite {}", code.extended_code)
        }
        _ => "sqlite error".to_owned(),
    };
    CatalogError::new(operation, detail)
}
