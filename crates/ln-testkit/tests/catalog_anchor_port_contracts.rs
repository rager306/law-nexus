//! Shared CatalogAnchorPort contract suite (ADR-0015).
//!
//! Exercises the read-only SQLite adapter and the in-memory adapter against the
//! same `ln_consultant_parser::catalog_anchor::contract` helpers so the anchor
//! port stays covered by one shared surface. Lifecycle `[bounded]`: the SQLite
//! fixture uses the observed document/edition schema; it is synthetic, not
//! real-infrastructure validation.
//!
//! Two catalogs exist in the corpus. This suite binds `catalog.sqlite`
//! explicitly: its `editions.source_id` is the anchor of a corpus document
//! itself. Reference tokens found *inside* document bodies are resolved against
//! the separate links database, not this one — a reference token is only an
//! anchor here when it is the document's own edition `source_id`.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::catalog_anchor::contract;
use ln_consultant_parser::{
    CatalogAnchorPort, CatalogAnchorRecord, InMemoryCatalogAnchor, SqliteCatalog,
};
use rusqlite::{Connection, OpenFlags};

/// A real-form offline token (mixed-case tail preserved verbatim).
const TOKEN_OWN: &str = "consultantplus://offline/ref=9E3314DB7361376719B3ADCEA898430BE476990BC9F6D0C1BD194E8D474CA6B73B5B623A5CF89E2A75B80C3814bD31I";
const MANIFEST_OWN: &str = "npa/document_own.xml";
const RELATIVE_OWN: &str = "exports/npa/document_own.xml";
const RELATIVE_MID: &str = "exports/npa/document_own_rev-2023.xml";
const RELATIVE_HIGH: &str = "exports/npa/document_own_rev-2024.xml";
const MISSING_MANIFEST: &str = "npa/absent.xml";
const MISSING_SOURCE: &str = "consultantplus://offline/ref=no-such-token";

/// Extracted act numbers must NOT join by exact token (they are not tokens):
/// the number is encrypted inside the offline token (MEM1781).
const EXTRACTED_NUMBERS: [&str; 3] = ["44-ФЗ", "402-ФЗ", "5-фкз"];

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
            "ln-testkit-anchor-{}-{}-{}-{}.sqlite",
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
            document_id TEXT NOT NULL,
            document_type TEXT NOT NULL DEFAULT 'document',
            document_date TEXT,
            number TEXT,
            revision_date TEXT,
            edition_number INTEGER,
            relative_path TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL,
            exported_at TEXT NOT NULL
        );
        CREATE TABLE consultant_source_locators (
            offline_uri TEXT UNIQUE,
            catalog_source_id TEXT REFERENCES documents(source_id)
        );
        ",
    )
    .expect("create observed catalog schema");
}

fn insert_edition(
    conn: &Connection,
    edition_id: &str,
    relative_path: &str,
    number: &str,
    date: &str,
    edition_number: i64,
) {
    conn.execute(
        "INSERT INTO editions (
            edition_id, source_id, document_id, document_date, number,
            revision_date, edition_number, relative_path, sha256, exported_at
         ) VALUES (?1, ?2, 'doc-own', ?3, ?4, ?3, ?5, ?6, 'sha-own', '2025-12-28')",
        rusqlite::params![
            edition_id,
            TOKEN_OWN,
            date,
            number,
            edition_number,
            relative_path
        ],
    )
    .expect("insert edition");
}

fn seed_fixture(path: &Path) {
    let conn = writable(path);
    create_schema(&conn);
    conn.execute(
        "INSERT INTO documents (source_id, title, kind)
         VALUES (?1, 'DOC-OWN', 'normative')",
        [TOKEN_OWN],
    )
    .expect("insert document");
    // Three editions of the same document; relative_path is UNIQUE so only the
    // source_id lookup can pick the latest (edition_number wins, then
    // revision_date, then edition_id).
    insert_edition(&conn, "edition-own", RELATIVE_OWN, "NUM-1", "2020-01-01", 1);
    insert_edition(
        &conn,
        "edition-mid",
        RELATIVE_MID,
        "NUM-MID",
        "2023-06-01",
        2,
    );
    insert_edition(
        &conn,
        "edition-high",
        RELATIVE_HIGH,
        "NUM-HIGH",
        "2024-01-23",
        3,
    );
    conn.execute(
        "INSERT INTO consultant_source_locators (offline_uri, catalog_source_id)
         VALUES ('offline://token-own', ?1)",
        [TOKEN_OWN],
    )
    .expect("insert locator");
}

fn own_record() -> CatalogAnchorRecord {
    CatalogAnchorRecord {
        relative_path: Some(RELATIVE_OWN.to_owned()),
        source_id: TOKEN_OWN.to_owned(),
        edition_id: Some("edition-own".to_owned()),
    }
}

fn latest_record() -> CatalogAnchorRecord {
    CatalogAnchorRecord {
        relative_path: Some(RELATIVE_HIGH.to_owned()),
        source_id: TOKEN_OWN.to_owned(),
        edition_id: Some("edition-high".to_owned()),
    }
}

fn memory_port() -> InMemoryCatalogAnchor {
    let mut memory = InMemoryCatalogAnchor::new();
    memory.insert_by_relative_path(MANIFEST_OWN, own_record());
    memory.insert_by_source_id(TOKEN_OWN, latest_record());
    memory
}

#[test]
fn in_memory_and_sqlite_anchor_share_the_port_contract() {
    let temp = TempDb::new("shared");
    seed_fixture(temp.path());

    let sqlite = SqliteCatalog::open_read_only(temp.path()).expect("open seeded catalog");
    let memory = memory_port();

    for port in [
        &sqlite as &dyn CatalogAnchorPort,
        &memory as &dyn CatalogAnchorPort,
    ] {
        contract::lookup_by_path_found_exact(port, &own_record());
        contract::lookup_by_path_missing_is_none(port, MISSING_MANIFEST);
        contract::lookup_by_source_id_found_exact(port, &latest_record());
        contract::lookup_by_source_id_missing_is_none(port, MISSING_SOURCE);
        contract::empty_input_rejected(port);
        contract::latest_edition_tie_break(port, TOKEN_OWN, &latest_record());
    }
}

#[test]
fn sqlite_lookup_returns_full_token_verbatim() {
    let temp = TempDb::new("verbatim");
    seed_fixture(temp.path());
    let sqlite = SqliteCatalog::open_read_only(temp.path()).expect("open seeded catalog");

    let by_path = sqlite
        .lookup_by_relative_path(MANIFEST_OWN)
        .expect("path lookup")
        .expect("own anchor present");
    assert_eq!(by_path.source_id, TOKEN_OWN, "source_id must be byte-exact");

    let by_source = sqlite
        .lookup_by_source_id(TOKEN_OWN)
        .expect("source lookup")
        .expect("own anchor present");
    assert_eq!(by_source.source_id.as_bytes(), TOKEN_OWN.as_bytes());
}

#[test]
fn extracted_numbers_are_a_zero_match_negative() {
    let temp = TempDb::new("negative");
    seed_fixture(temp.path());
    let sqlite = SqliteCatalog::open_read_only(temp.path()).expect("open seeded catalog");
    let memory = memory_port();

    for port in [
        &sqlite as &dyn CatalogAnchorPort,
        &memory as &dyn CatalogAnchorPort,
    ] {
        for number in EXTRACTED_NUMBERS {
            let hit = port
                .lookup_by_source_id(number)
                .expect("negative probe must not fail");
            assert_eq!(
                hit, None,
                "extracted number {number} must not join by exact token"
            );
        }
    }
}

#[test]
fn missing_file_open_fails_and_connection_is_read_only() {
    let absent = TempDb::new("absent");
    let err = SqliteCatalog::open_read_only(absent.path()).expect_err("absent file must fail");
    assert_eq!(err.operation(), "open");
    assert!(!err.detail().is_empty());

    let temp = TempDb::new("readonly");
    seed_fixture(temp.path());
    let catalog = SqliteCatalog::open_read_only(temp.path()).expect("open read-only catalog");
    assert!(
        catalog.is_read_only().expect("inspect connection mode"),
        "SqliteCatalog must keep a read-only main connection"
    );
}
