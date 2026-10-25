//! Shared PageIndexCatalogPort contract suite (ADR-0015).
//!
//! Exercises the read-only SQLite adapter and the in-memory adapter against the
//! same `ln_consultant_parser::page_index_catalog::contract` helpers so the
//! page-index catalog port stays covered by one shared surface. Lifecycle
//! `[bounded]`: the SQLite fixture uses the observed `court_items` /
//! `consultant_source_records` / `consultant_source_locators` column shapes; it
//! is synthetic, not real-infrastructure validation.
//!
//! The port joins an offline token to the legal-identity keys
//! `(bank, document_key)` across *both* catalog surfaces. It never decodes the
//! token and never derives a key from a file path, so an extracted act number
//! is a guaranteed zero match.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::page_index_catalog::contract;
use ln_consultant_parser::{
    CatalogPageIndexRecord, InMemoryPageIndexCatalog, PageIndexCatalogPort, SqliteCatalog,
};
use rusqlite::{Connection, OpenFlags};

/// Real-form offline tokens (mixed-case tails preserved verbatim).
const TOKEN_COURT: &str = "consultantplus://offline/ref=9E3314DB7361376719B3ADCEA898430BE476990BC9F6D0C1BD194E8D474CA6B73B5B623A5CF89E2A75B80C3814bD31I";
const TOKEN_LOCATOR: &str =
    "consultantplus://offline/ref=0F1A2B3C4D5E6F778899AABBCCDDEEFF00112233445566778899aAbBcC";
const TOKEN_BOTH: &str =
    "consultantplus://offline/ref=DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEeFdEaD";
const TOKEN_MISSING: &str = "consultantplus://offline/ref=no-such-token";

/// Extracted act numbers must NOT join by exact token (they are not tokens):
/// the number is encrypted inside the offline token (MEM1781). A numeric
/// document_key ("402") is likewise not a token.
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
            "ln-testkit-pageindex-{}-{}-{}-{}.sqlite",
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
        CREATE TABLE court_items (
            item_id INTEGER PRIMARY KEY,
            bank TEXT,
            document_key INTEGER,
            offline_uri TEXT
        );
        CREATE TABLE consultant_source_records (
            source_record_id TEXT PRIMARY KEY,
            bank TEXT NOT NULL,
            document_key INTEGER NOT NULL CHECK (document_key > 0)
        );
        CREATE TABLE consultant_source_locators (
            locator_id TEXT PRIMARY KEY,
            source_record_id TEXT NOT NULL
                REFERENCES consultant_source_records(source_record_id),
            offline_uri TEXT NOT NULL UNIQUE
        );
        ",
    )
    .expect("create observed catalog schema subset");
}

fn insert_court_item(conn: &Connection, bank: &str, document_key: i64, offline_uri: &str) {
    conn.execute(
        "INSERT INTO court_items (bank, document_key, offline_uri) VALUES (?1, ?2, ?3)",
        rusqlite::params![bank, document_key, offline_uri],
    )
    .expect("insert court item");
}

fn insert_source_record(conn: &Connection, source_record_id: &str, bank: &str, key: i64) {
    conn.execute(
        "INSERT INTO consultant_source_records (source_record_id, bank, document_key)
         VALUES (?1, ?2, ?3)",
        rusqlite::params![source_record_id, bank, key],
    )
    .expect("insert source record");
}

fn insert_locator(conn: &Connection, locator_id: &str, source_record_id: &str, offline_uri: &str) {
    conn.execute(
        "INSERT INTO consultant_source_locators (locator_id, source_record_id, offline_uri)
         VALUES (?1, ?2, ?3)",
        rusqlite::params![locator_id, source_record_id, offline_uri],
    )
    .expect("insert locator");
}

fn seed_fixture(path: &Path) {
    let conn = writable(path);
    create_schema(&conn);

    // court_items surface: TOKEN_COURT carries two identities (sorted ACN then
    // ARB) plus a duplicate (ARB, 155320) that must collapse. TOKEN_BOTH is
    // shared with the locator surface to exercise cross-surface de-duplication.
    insert_court_item(&conn, "ARB", 155320, TOKEN_COURT);
    insert_court_item(&conn, "ARB", 155320, TOKEN_COURT);
    insert_court_item(&conn, "ACN", 42, TOKEN_COURT);
    insert_court_item(&conn, "LAW", 5, TOKEN_BOTH);

    // locator surface: locator -> source_record -> (bank, document_key).
    insert_source_record(&conn, "cp:LAW:402", "LAW", 402);
    insert_source_record(&conn, "cp:LAW:5", "LAW", 5);
    insert_locator(&conn, "loc-402", "cp:LAW:402", TOKEN_LOCATOR);
    insert_locator(&conn, "loc-both", "cp:LAW:5", TOKEN_BOTH);

    conn.execute(
        "INSERT INTO court_items (bank, document_key, offline_uri) VALUES ('LAW', 5, ?1)",
        [TOKEN_BOTH],
    )
    .expect("insert cross-surface duplicate court row");
}

fn record(bank: &str, document_key: &str) -> CatalogPageIndexRecord {
    CatalogPageIndexRecord {
        bank: bank.to_owned(),
        document_key: document_key.to_owned(),
    }
}

fn court_expected() -> Vec<CatalogPageIndexRecord> {
    vec![record("ACN", "42"), record("ARB", "155320")]
}

fn locator_expected() -> Vec<CatalogPageIndexRecord> {
    vec![record("LAW", "402")]
}

fn both_expected() -> Vec<CatalogPageIndexRecord> {
    vec![record("LAW", "5")]
}

fn memory_port() -> InMemoryPageIndexCatalog {
    let mut memory = InMemoryPageIndexCatalog::new();
    // Raw rows as observed, duplicates included; the port normalizes.
    memory.insert(TOKEN_COURT, "ARB", "155320");
    memory.insert(TOKEN_COURT, "ARB", "155320");
    memory.insert(TOKEN_COURT, "ACN", "42");
    memory.insert(TOKEN_LOCATOR, "LAW", "402");
    memory.insert(TOKEN_BOTH, "LAW", "5");
    memory.insert(TOKEN_BOTH, "LAW", "5");
    memory
}

#[test]
fn in_memory_and_sqlite_page_index_catalog_share_the_port_contract() {
    let temp = TempDb::new("shared");
    seed_fixture(temp.path());

    let sqlite = SqliteCatalog::open_read_only(temp.path()).expect("open seeded catalog");
    let memory = memory_port();

    for port in [
        &sqlite as &dyn PageIndexCatalogPort,
        &memory as &dyn PageIndexCatalogPort,
    ] {
        contract::lookup_found_exact(port, TOKEN_COURT, &court_expected());
        contract::lookup_found_exact(port, TOKEN_LOCATOR, &locator_expected());
        contract::lookup_found_exact(port, TOKEN_BOTH, &both_expected());
        contract::lookup_missing_is_empty(port, TOKEN_MISSING);
        contract::deterministic_sorted_dedup(port, TOKEN_COURT, &court_expected());
        contract::deterministic_sorted_dedup(port, TOKEN_BOTH, &both_expected());
        contract::empty_input_rejected(port);
    }
}

#[test]
fn extracted_numbers_are_a_zero_match_negative() {
    let temp = TempDb::new("negative");
    seed_fixture(temp.path());
    let sqlite = SqliteCatalog::open_read_only(temp.path()).expect("open seeded catalog");
    let memory = memory_port();

    for port in [
        &sqlite as &dyn PageIndexCatalogPort,
        &memory as &dyn PageIndexCatalogPort,
    ] {
        for number in EXTRACTED_NUMBERS {
            contract::extracted_number_zero_match(port, number);
        }
    }
}

#[test]
fn sqlite_document_key_is_rendered_as_text_not_integer() {
    let temp = TempDb::new("textkey");
    seed_fixture(temp.path());
    let sqlite = SqliteCatalog::open_read_only(temp.path()).expect("open seeded catalog");

    let rows = sqlite
        .lookup_by_offline_token(TOKEN_LOCATOR)
        .expect("locator lookup");
    assert_eq!(
        rows,
        vec![record("LAW", "402")],
        "catalog INTEGER document_key must map to the TEXT pageindex key space"
    );
    assert_eq!(rows[0].document_key, "402");
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
