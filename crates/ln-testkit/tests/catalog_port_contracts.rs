//! Shared CatalogPort contract suite (ADR-0015).
//!
//! Exercises the read-only SQLite adapter and the in-memory adapter against
//! the same `ln_consultant_parser::catalog::contract` helpers so the
//! multi-adapter catalog port stays covered by one shared surface. Lifecycle
//! `[bounded]`: the SQLite fixture uses the observed locator/document/edition
//! schema; it is not real-infrastructure validation.

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
const FOUND_NUMBER: &str = "NUM-1";
const FOUND_DATE: &str = "2024-01-23";

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
            "ln-testkit-catalog-{}-{}-{}-{}.sqlite",
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

fn seed_found_document(path: &Path) {
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
         ) VALUES (1, 'src-a', 'zakon', '2024-01-23', 'NUM-1', '2024-01-23', 1)",
        [],
    )
    .expect("insert edition");
}

fn expected_found() -> CatalogRecord {
    CatalogRecord {
        consid: FOUND_CONSID.to_owned(),
        title: Some("DOC-TITLE-A".to_owned()),
        kind: Some("KIND-A".to_owned()),
        number: Some(FOUND_NUMBER.to_owned()),
        document_date: Some(FOUND_DATE.to_owned()),
        in_catalog: true,
    }
}

#[test]
fn in_memory_and_sqlite_catalog_share_the_port_contract() {
    let temp = TempDb::new("shared");
    seed_found_document(temp.path());

    let sqlite = SqliteCatalog::open_read_only(temp.path()).expect("open seeded catalog");
    assert!(sqlite.is_read_only().expect("read-only check"));

    let mut memory = InMemoryCatalog::new();
    memory.insert_record(expected_found());

    for port in [&sqlite as &dyn CatalogPort, &memory as &dyn CatalogPort] {
        contract::lookup_found_exact(port, &expected_found());
        contract::lookup_missing_is_none(port, MISSING_CONSID);
        contract::resolve_missing_is_not_in_catalog(port, MISSING_CONSID);
        contract::lookup_metadata_exact(port, FOUND_CONSID, FOUND_NUMBER, FOUND_DATE);
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
