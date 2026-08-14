//! Read-only SQLite CatalogPort adapter: shared contract + hostile open/query.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::catalog::{
    contract, resolve_consids, CatalogPort, CatalogRecord, InMemoryCatalog,
};
use ln_consultant_parser::SqliteCatalog;
use rusqlite::{Connection, OpenFlags};

const FOUND_CONSID: &str = "offline://token-found";
const MISSING_CONSID: &str = "offline://token-missing";
const LATEST_NUMBER: &str = "NUM-LATEST";
const LATEST_DATE: &str = "2024-01-23";

static TEMP_SEQ: AtomicU64 = AtomicU64::new(0);

struct TempDb {
    path: PathBuf,
}

impl TempDb {
    fn new(label: &str) -> Self {
        let seq = TEMP_SEQ.fetch_add(1, Ordering::Relaxed);
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        let path = std::env::temp_dir().join(format!(
            "ln-consultant-catalog-{}-{}-{}-{}.sqlite",
            std::process::id(),
            nanos,
            seq,
            label
        ));
        Self { path }
    }

    fn path(&self) -> &Path {
        &self.path
    }
}

impl Drop for TempDb {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.path);
        let _ = std::fs::remove_file(sidecar(&self.path, "-wal"));
        let _ = std::fs::remove_file(sidecar(&self.path, "-shm"));
        let _ = std::fs::remove_file(sidecar(&self.path, "-journal"));
    }
}

fn sidecar(path: &Path, suffix: &str) -> PathBuf {
    let mut name = path.as_os_str().to_os_string();
    name.push(suffix);
    PathBuf::from(name)
}

fn writable(path: &Path) -> Connection {
    Connection::open_with_flags(
        path,
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE,
    )
    .expect("writable fixture connection")
}

fn create_schema(conn: &Connection) {
    conn.execute_batch(
        "
        CREATE TABLE documents (
            source_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            offline_uri TEXT,
            kind TEXT
        );
        CREATE TABLE editions (
            edition_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES documents(source_id),
            document_type TEXT,
            document_date TEXT,
            number TEXT,
            revision_date TEXT,
            edition_number INTEGER
        );
        CREATE TABLE consultant_source_locators (
            offline_uri TEXT UNIQUE,
            catalog_source_id TEXT REFERENCES documents(source_id)
        );
        ",
    )
    .expect("create observed catalog schema");
}

fn seed_latest_edition_fixture(path: &Path) {
    let conn = writable(path);
    create_schema(&conn);
    conn.execute(
        "INSERT INTO documents (source_id, title, offline_uri, kind)
         VALUES ('src-a', 'DOC-TITLE-A', 'offline://token-found', 'KIND-A')",
        [],
    )
    .expect("insert document");
    conn.execute(
        "INSERT INTO consultant_source_locators (offline_uri, catalog_source_id)
         VALUES ('offline://token-found', 'src-a')",
        [],
    )
    .expect("insert locator");
    conn.execute(
        "INSERT INTO editions (
            edition_id, source_id, document_type, document_date, number,
            revision_date, edition_number
         ) VALUES (1, 'src-a', 'zakon', '2020-01-01', 'NUM-OLD', '2020-01-01', 1)",
        [],
    )
    .expect("insert older edition");
    conn.execute(
        "INSERT INTO editions (
            edition_id, source_id, document_type, document_date, number,
            revision_date, edition_number
         ) VALUES (3, 'src-a', 'zakon', '2023-12-01', 'NUM-MID', '2023-12-01', 2)",
        [],
    )
    .expect("insert mid edition");
    conn.execute(
        "INSERT INTO editions (
            edition_id, source_id, document_type, document_date, number,
            revision_date, edition_number
         ) VALUES (2, 'src-a', 'zakon', '2024-01-23', 'NUM-LATEST', '2024-01-23', 3)",
        [],
    )
    .expect("insert latest edition");
}

fn expected_found() -> CatalogRecord {
    CatalogRecord {
        consid: FOUND_CONSID.to_owned(),
        title: Some("DOC-TITLE-A".to_owned()),
        kind: Some("KIND-A".to_owned()),
        number: Some(LATEST_NUMBER.to_owned()),
        document_date: Some(LATEST_DATE.to_owned()),
        in_catalog: true,
    }
}

#[test]
fn sqlite_and_in_memory_share_found_missing_and_latest_contract() {
    let temp = TempDb::new("shared");
    seed_latest_edition_fixture(temp.path());

    let sqlite = SqliteCatalog::open_read_only(temp.path()).expect("open seeded catalog");
    let mut memory = InMemoryCatalog::new();
    memory.insert_record(expected_found());

    for port in [&sqlite as &dyn CatalogPort, &memory as &dyn CatalogPort] {
        contract::lookup_found_exact(port, &expected_found());
        contract::lookup_missing_is_none(port, MISSING_CONSID);
        contract::resolve_missing_is_not_in_catalog(port, MISSING_CONSID);
        contract::lookup_metadata_exact(port, FOUND_CONSID, LATEST_NUMBER, LATEST_DATE);
        contract::lookup_empty_consid_rejected(port);
    }

    let records = resolve_consids(
        &sqlite,
        &[FOUND_CONSID.to_owned(), MISSING_CONSID.to_owned()],
    )
    .expect("mixed sqlite resolve");
    assert!(records[0].in_catalog);
    assert!(!records[1].in_catalog);
}

#[test]
fn latest_edition_uses_edition_number_then_revision_then_id() {
    let temp = TempDb::new("tiebreak");
    let conn = writable(temp.path());
    create_schema(&conn);
    conn.execute(
        "INSERT INTO documents (source_id, title, kind)
         VALUES ('src-b', 'DOC-TITLE-B', 'KIND-B')",
        [],
    )
    .expect("insert document");
    conn.execute(
        "INSERT INTO consultant_source_locators (offline_uri, catalog_source_id)
         VALUES ('offline://token-tie', 'src-b')",
        [],
    )
    .expect("insert locator");
    conn.execute(
        "INSERT INTO editions (
            edition_id, source_id, document_date, number, revision_date, edition_number
         ) VALUES (10, 'src-b', '2024-01-01', 'NUM-LOW-ID', '2024-06-01', 5)",
        [],
    )
    .expect("insert lower id same rank");
    conn.execute(
        "INSERT INTO editions (
            edition_id, source_id, document_date, number, revision_date, edition_number
         ) VALUES (11, 'src-b', '2024-02-02', 'NUM-HIGH-ID', '2024-06-01', 5)",
        [],
    )
    .expect("insert higher id same rank");
    drop(conn);

    let catalog = SqliteCatalog::open_read_only(temp.path()).expect("open tie-break catalog");
    contract::lookup_metadata_exact(&catalog, "offline://token-tie", "NUM-HIGH-ID", "2024-02-02");
}

#[test]
fn null_edition_rank_falls_back_to_text_edition_id() {
    let temp = TempDb::new("null-rank");
    let conn = writable(temp.path());
    create_schema(&conn);
    conn.execute(
        "INSERT INTO documents (source_id, title, kind)
         VALUES ('src-null', 'DOC-TITLE-NULL', 'KIND-NULL')",
        [],
    )
    .expect("insert document");
    conn.execute(
        "INSERT INTO consultant_source_locators (offline_uri, catalog_source_id)
         VALUES ('offline://token-null', 'src-null')",
        [],
    )
    .expect("insert locator");
    conn.execute(
        "INSERT INTO editions (
            edition_id, source_id, document_date, number, revision_date, edition_number
         ) VALUES ('edition-a', 'src-null', '2020-01-01', 'NUM-A', NULL, NULL)",
        [],
    )
    .expect("insert lower text id");
    conn.execute(
        "INSERT INTO editions (
            edition_id, source_id, document_date, number, revision_date, edition_number
         ) VALUES ('edition-b', 'src-null', '2021-01-01', 'NUM-B', NULL, NULL)",
        [],
    )
    .expect("insert higher text id");
    drop(conn);

    let catalog = SqliteCatalog::open_read_only(temp.path()).expect("open null-rank catalog");
    // This is a deterministic projection order, not a wall-clock latest claim.
    contract::lookup_metadata_exact(&catalog, "offline://token-null", "NUM-B", "2021-01-01");
}

#[test]
fn missing_file_open_fails() {
    let temp = TempDb::new("absent");
    let err = SqliteCatalog::open_read_only(temp.path()).expect_err("absent file must fail");
    assert_eq!(err.operation(), "open");
    assert!(!err.detail().is_empty());
}

#[test]
fn invalid_database_open_or_query_fails() {
    let temp = TempDb::new("garbage");
    std::fs::write(temp.path(), b"not-a-sqlite-database").expect("write garbage file");
    match SqliteCatalog::open_read_only(temp.path()) {
        Err(err) => {
            assert!(err.operation() == "open" || err.operation() == "query");
            assert!(!err.detail().is_empty());
        }
        Ok(catalog) => {
            let err = catalog
                .lookup(FOUND_CONSID)
                .expect_err("garbage database lookup must fail");
            assert!(err.operation() == "query" || err.operation() == "decode");
            assert!(!err.detail().is_empty());
        }
    }
}

#[test]
fn malformed_schema_lookup_fails() {
    let temp = TempDb::new("malformed");
    let conn = writable(temp.path());
    conn.execute_batch("CREATE TABLE documents (source_id TEXT);")
        .expect("create incomplete schema");
    drop(conn);

    let catalog = SqliteCatalog::open_read_only(temp.path()).expect("open malformed catalog");
    let err = catalog
        .lookup(FOUND_CONSID)
        .expect_err("malformed schema must not look like a miss");
    assert!(err.operation() == "query" || err.operation() == "decode");
    assert!(!err.detail().is_empty());
}

#[test]
fn locator_without_document_is_decode_failure() {
    let temp = TempDb::new("orphan");
    let conn = writable(temp.path());
    create_schema(&conn);
    conn.execute_batch(
        "PRAGMA foreign_keys = OFF;
         INSERT INTO consultant_source_locators (offline_uri, catalog_source_id)
         VALUES ('offline://token-orphan', 'missing-src');",
    )
    .expect("insert orphan locator");
    drop(conn);

    let catalog = SqliteCatalog::open_read_only(temp.path()).expect("open orphan catalog");
    let err = catalog
        .lookup("offline://token-orphan")
        .expect_err("orphan locator is schema/decode failure");
    assert_eq!(err.operation(), "decode");
}

#[test]
fn adapter_connection_reports_read_only() {
    let temp = TempDb::new("readonly");
    seed_latest_edition_fixture(temp.path());
    let catalog = SqliteCatalog::open_read_only(temp.path()).expect("open read-only catalog");

    assert!(
        catalog
            .is_read_only()
            .expect("inspect adapter connection mode"),
        "SqliteCatalog main connection must be read-only"
    );
}
