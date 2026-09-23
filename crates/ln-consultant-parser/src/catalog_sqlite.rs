//! Read-only SQLite adapter for [`crate::catalog::CatalogPort`].
//! Opens with `SQLITE_OPEN_READ_ONLY` and maps a genuine miss to `Ok(None)`.

use std::path::Path;

use rusqlite::{Connection, OpenFlags, OptionalExtension};

use crate::catalog::{CatalogError, CatalogPort, CatalogRecord};

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
