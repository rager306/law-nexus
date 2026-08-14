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
