//! Bounded SQLite-vs-Turso crash/recovery evidence probe.
//!
//! Synthetic data only. This executable does not select a product database.

use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitCode, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use anyhow::{anyhow, bail, Context, Result};
use rusqlite::{params, Connection as SqliteConnection, OpenFlags};
use serde::Serialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use turso::Builder;

const JOBS: usize = 40;
const PAYLOAD_BYTES: usize = 4096;
const BASE_ROWS: usize = 10;
const MARKER_TIMEOUT: Duration = Duration::from_secs(30);
const SCENARIOS: &[&str] = &[
    "S01_clean_commit",
    "S02_kill_mid_txn",
    "S03_kill_after_commit_before_checkpoint",
    "S04_kill_during_checkpoint",
    "S05_disk_full",
    "S06_reopen_integrity",
    "S07_exit_to_stock_sqlite",
];

#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "lowercase")]
enum Backend {
    Sqlite,
    Turso,
}

impl Backend {
    fn parse(raw: &str) -> Result<Self> {
        match raw {
            "sqlite" => Ok(Self::Sqlite),
            "turso" => Ok(Self::Turso),
            _ => bail!("unknown backend: {raw}"),
        }
    }

    fn as_str(self) -> &'static str {
        match self {
            Self::Sqlite => "sqlite",
            Self::Turso => "turso",
        }
    }
}

#[derive(Debug, Serialize)]
struct ScenarioResult {
    scenario: String,
    backend: Backend,
    status: &'static str,
    note: String,
    expected_rows: Option<usize>,
    observed_rows: Option<usize>,
    checksum_mismatches: Option<usize>,
    integrity: String,
    wall_ms: u128,
    db_bytes: u64,
    wal_bytes: u64,
}

#[derive(Debug, Serialize)]
struct Report {
    schema: &'static str,
    lifecycle: &'static str,
    adoption: &'static str,
    versions: serde_json::Value,
    config: serde_json::Value,
    results: Vec<ScenarioResult>,
    non_claims: Vec<&'static str>,
}

fn usage() -> &'static str {
    "usage:\n  sqlite-turso-crash-recovery matrix <work-dir>\n  sqlite-turso-crash-recovery parent <sqlite|turso> <scenario> <work-dir>\n  sqlite-turso-crash-recovery worker <sqlite|turso> <scenario> <db-path> <marker-dir>"
}

#[tokio::main(flavor = "current_thread")]
async fn main() -> ExitCode {
    match run().await {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("probe_error: {error:#}");
            ExitCode::from(20)
        }
    }
}

async fn run() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("matrix") if args.len() == 3 => run_matrix(Path::new(&args[2])).await,
        Some("parent") if args.len() == 5 => {
            let backend = Backend::parse(&args[2])?;
            let result = run_parent(backend, &args[3], Path::new(&args[4])).await?;
            println!("{}", serde_json::to_string_pretty(&result)?);
            if result.status == "fail" {
                bail!("scenario assertion failed")
            }
            Ok(())
        }
        Some("worker") if args.len() == 6 => {
            let backend = Backend::parse(&args[2])?;
            run_worker(backend, &args[3], Path::new(&args[4]), Path::new(&args[5])).await
        }
        _ => bail!(usage()),
    }
}

async fn run_matrix(work_dir: &Path) -> Result<()> {
    fs::create_dir_all(work_dir)?;
    let mut results = Vec::new();
    for backend in [Backend::Sqlite, Backend::Turso] {
        for scenario in SCENARIOS {
            results.push(run_parent(backend, scenario, work_dir).await?);
        }
    }
    let report = Report {
        schema: "lnx.probe.sqlite-turso.report/v1",
        lifecycle: "[bounded]",
        adoption: "none",
        versions: json!({"rusqlite":"0.39.0","turso":"0.7.1"}),
        config: json!({
            "synthetic_only": true,
            "jobs": JOBS,
            "payload_bytes": PAYLOAD_BYTES,
            "journal_mode": "WAL",
            "synchronous": "FULL",
            "forbidden_features": ["mvcc","encryption","multiprocess-wal","fts","cdc","sync","mcp"]
        }),
        results,
        non_claims: vec![
            "This probe does not select or adopt a product database.",
            "This probe does not prove production durability, legal correctness, E1-E3 capacity, encryption, MVCC, cloud sync, FTS, CDC or MCP behavior.",
            "Unsupported checkpoint-window and true ENOSPC cases are not simulated as durability proof.",
            "All records are deterministic synthetic payloads; no legal text, vectors, credentials or secrets are used.",
        ],
    };
    println!("{}", serde_json::to_string_pretty(&report)?);
    if report.results.iter().any(|r| r.status == "fail") {
        bail!("one or more scenario assertions failed")
    }
    Ok(())
}

async fn run_parent(backend: Backend, scenario: &str, root: &Path) -> Result<ScenarioResult> {
    if !SCENARIOS.contains(&scenario) {
        bail!("unknown scenario: {scenario}");
    }
    let started = Instant::now();
    let case_dir = root.join(format!("{}-{scenario}", backend.as_str()));
    if case_dir.exists() {
        fs::remove_dir_all(&case_dir).context("remove prior synthetic case directory")?;
    }
    let marker_dir = case_dir.join("markers");
    fs::create_dir_all(&marker_dir)?;
    let db_path = case_dir.join("probe.db");

    if scenario == "S04_kill_during_checkpoint" {
        return Ok(unsupported(
            backend,
            scenario,
            started,
            &db_path,
            "checkpoint window is not controllable through a shared safe API",
        ));
    }
    if scenario == "S05_disk_full" {
        return Ok(unsupported(backend, scenario, started, &db_path, "true ENOSPC is not safe to induce on the host; no simulation is promoted as durability proof"));
    }
    if scenario == "S07_exit_to_stock_sqlite" && matches!(backend, Backend::Sqlite) {
        return Ok(unsupported(
            backend,
            scenario,
            started,
            &db_path,
            "stock reopen is a Turso compatibility check",
        ));
    }

    let mut child = spawn_worker(backend, scenario, &db_path, &marker_dir)?;
    match scenario {
        "S02_kill_mid_txn" => kill_at_marker(&mut child, &marker_dir.join("txn_mid"))?,
        "S03_kill_after_commit_before_checkpoint" => {
            kill_at_marker(&mut child, &marker_dir.join("txn_committed"))?
        }
        _ => {
            let status = child.wait().context("wait for worker")?;
            if !status.success() {
                bail!("worker exited with {status}");
            }
        }
    }

    let expected = match scenario {
        "S02_kill_mid_txn" => BASE_ROWS,
        _ => JOBS,
    };
    let (backend_observed, backend_mismatches, backend_integrity) =
        verify_with_backend(backend, &db_path).await?;
    let backend_pass =
        backend_observed == expected && backend_mismatches == 0 && backend_integrity == "ok";

    let (observed, mismatches, integrity, pass, note) = if scenario == "S07_exit_to_stock_sqlite" {
        let (stock_observed, stock_mismatches, stock_integrity) = verify_sqlite(&db_path)?;
        let stock_pass =
            stock_observed == expected && stock_mismatches == 0 && stock_integrity == "ok";
        (
                stock_observed,
                stock_mismatches,
                stock_integrity.clone(),
                backend_pass && stock_pass,
                format!(
                    "Turso and bundled stock SQLite independently verified {stock_observed}/{expected} rows, zero digest mismatches and integrity={stock_integrity}"
                ),
            )
    } else {
        (
            backend_observed,
            backend_mismatches,
            backend_integrity,
            backend_pass,
            "fresh connection verified deterministic row count, checksums and integrity surface"
                .to_string(),
        )
    };
    Ok(ScenarioResult {
        scenario: scenario.to_string(),
        backend,
        status: if pass { "pass" } else { "fail" },
        note,
        expected_rows: Some(expected),
        observed_rows: Some(observed),
        checksum_mismatches: Some(mismatches),
        integrity,
        wall_ms: started.elapsed().as_millis(),
        db_bytes: file_size(&db_path),
        wal_bytes: file_size(&PathBuf::from(format!("{}-wal", db_path.display()))),
    })
}

fn unsupported(
    backend: Backend,
    scenario: &str,
    started: Instant,
    db_path: &Path,
    note: &str,
) -> ScenarioResult {
    ScenarioResult {
        scenario: scenario.to_string(),
        backend,
        status: "unsupported",
        note: note.to_string(),
        expected_rows: None,
        observed_rows: None,
        checksum_mismatches: None,
        integrity: "unsupported".to_string(),
        wall_ms: started.elapsed().as_millis(),
        db_bytes: file_size(db_path),
        wal_bytes: 0,
    }
}

fn spawn_worker(
    backend: Backend,
    scenario: &str,
    db_path: &Path,
    marker_dir: &Path,
) -> Result<Child> {
    let exe = env::current_exe()?;
    Command::new(exe)
        .arg("worker")
        .arg(backend.as_str())
        .arg(scenario)
        .arg(db_path)
        .arg(marker_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::inherit())
        .spawn()
        .context("spawn worker")
}

fn kill_at_marker(child: &mut Child, marker: &Path) -> Result<()> {
    let deadline = Instant::now() + MARKER_TIMEOUT;
    while !marker.exists() {
        if let Some(status) = child.try_wait()? {
            bail!("worker exited before marker {}: {status}", marker.display());
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            bail!("marker timeout: {}", marker.display());
        }
        thread::sleep(Duration::from_millis(5));
    }
    child.kill().context("SIGKILL worker")?;
    child.wait().context("reap killed worker")?;
    Ok(())
}

async fn run_worker(
    backend: Backend,
    scenario: &str,
    db_path: &Path,
    markers: &Path,
) -> Result<()> {
    match backend {
        Backend::Sqlite => worker_sqlite(scenario, db_path, markers),
        Backend::Turso => worker_turso(scenario, db_path, markers).await,
    }
}

fn worker_sqlite(scenario: &str, db_path: &Path, markers: &Path) -> Result<()> {
    let mut conn = SqliteConnection::open(db_path)?;
    configure_sqlite(&conn)?;
    create_schema_sqlite(&conn)?;
    insert_sqlite(&mut conn, 0, BASE_ROWS)?;

    if scenario == "S02_kill_mid_txn" {
        let tx = conn.transaction()?;
        for idx in BASE_ROWS..JOBS {
            insert_sqlite_row(&tx, idx)?;
            if idx == BASE_ROWS + (JOBS - BASE_ROWS) / 2 {
                mark(markers, "txn_mid")?;
                park_forever();
            }
        }
        tx.commit()?;
    } else {
        insert_sqlite(&mut conn, BASE_ROWS, JOBS)?;
        if scenario == "S03_kill_after_commit_before_checkpoint" {
            mark(markers, "txn_committed")?;
            park_forever();
        }
    }
    Ok(())
}

async fn worker_turso(scenario: &str, db_path: &Path, markers: &Path) -> Result<()> {
    let db = Builder::new_local(db_path.to_string_lossy().as_ref())
        .build()
        .await?;
    let conn = db.connect()?;
    drain_turso_query(&conn, "PRAGMA journal_mode=WAL").await?;
    drain_turso_query(&conn, "PRAGMA synchronous=FULL").await?;
    create_schema_turso(&conn).await?;
    insert_turso_range(&conn, 0, BASE_ROWS).await?;

    if scenario == "S02_kill_mid_txn" {
        conn.execute("BEGIN IMMEDIATE", ()).await?;
        for idx in BASE_ROWS..JOBS {
            insert_turso_row(&conn, idx).await?;
            if idx == BASE_ROWS + (JOBS - BASE_ROWS) / 2 {
                mark(markers, "txn_mid")?;
                park_forever();
            }
        }
        conn.execute("COMMIT", ()).await?;
    } else {
        conn.execute("BEGIN IMMEDIATE", ()).await?;
        for idx in BASE_ROWS..JOBS {
            insert_turso_row(&conn, idx).await?;
        }
        conn.execute("COMMIT", ()).await?;
        if scenario == "S03_kill_after_commit_before_checkpoint" {
            mark(markers, "txn_committed")?;
            park_forever();
        }
    }
    Ok(())
}

fn create_schema_sqlite(conn: &SqliteConnection) -> Result<()> {
    conn.execute_batch("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE, source_scope TEXT NOT NULL, source_observed_at INTEGER NOT NULL, source_published_at INTEGER, legal_effective_from INTEGER, legal_effective_to INTEGER, system_recorded_at INTEGER NOT NULL, payload BLOB NOT NULL, payload_sha256 TEXT NOT NULL) STRICT;")?;
    Ok(())
}

async fn drain_turso_query(conn: &turso::Connection, sql: &str) -> Result<()> {
    let mut rows = conn.query(sql, ()).await?;
    while rows.next().await?.is_some() {}
    Ok(())
}

async fn create_schema_turso(conn: &turso::Connection) -> Result<()> {
    conn.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE, source_scope TEXT NOT NULL, source_observed_at INTEGER NOT NULL, source_published_at INTEGER, legal_effective_from INTEGER, legal_effective_to INTEGER, system_recorded_at INTEGER NOT NULL, payload BLOB NOT NULL, payload_sha256 TEXT NOT NULL) STRICT", ()).await?;
    Ok(())
}

fn insert_sqlite(conn: &mut SqliteConnection, start: usize, end: usize) -> Result<()> {
    let tx = conn.transaction()?;
    for idx in start..end {
        insert_sqlite_row(&tx, idx)?;
    }
    tx.commit()?;
    Ok(())
}

fn insert_sqlite_row(conn: &SqliteConnection, idx: usize) -> Result<()> {
    let payload = payload(idx);
    let hash = payload_hash(&payload);
    conn.execute(
        "INSERT INTO events VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10)",
        params![
            idx as i64,
            operation_id(idx),
            "synthetic-probe",
            1_700_000_000_i64 + idx as i64,
            Option::<i64>::None,
            Option::<i64>::None,
            Option::<i64>::None,
            1_700_100_000_i64 + idx as i64,
            payload,
            hash
        ],
    )?;
    Ok(())
}

async fn insert_turso_range(conn: &turso::Connection, start: usize, end: usize) -> Result<()> {
    conn.execute("BEGIN IMMEDIATE", ()).await?;
    for idx in start..end {
        insert_turso_row(conn, idx).await?;
    }
    conn.execute("COMMIT", ()).await?;
    Ok(())
}

async fn insert_turso_row(conn: &turso::Connection, idx: usize) -> Result<()> {
    let payload = payload(idx);
    let hash = payload_hash(&payload);
    conn.execute(
        "INSERT INTO events VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10)",
        (
            idx as i64,
            operation_id(idx),
            "synthetic-probe",
            1_700_000_000_i64 + idx as i64,
            turso::Value::Null,
            turso::Value::Null,
            turso::Value::Null,
            1_700_100_000_i64 + idx as i64,
            payload,
            hash,
        ),
    )
    .await?;
    Ok(())
}

fn configure_sqlite(conn: &SqliteConnection) -> Result<()> {
    conn.pragma_update(None, "journal_mode", "WAL")?;
    conn.pragma_update(None, "synchronous", "FULL")?;
    Ok(())
}

async fn verify_with_backend(backend: Backend, path: &Path) -> Result<(usize, usize, String)> {
    match backend {
        Backend::Sqlite => verify_sqlite(path),
        Backend::Turso => verify_turso(path).await,
    }
}

fn verify_sqlite(path: &Path) -> Result<(usize, usize, String)> {
    let conn = SqliteConnection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    let count: usize = conn
        .query_row("SELECT count(*) FROM events", [], |r| r.get::<_, i64>(0))?
        .try_into()
        .context("negative SQLite row count")?;
    let mut statement =
        conn.prepare("SELECT seq, payload, payload_sha256 FROM events ORDER BY seq")?;
    let mut rows = statement.query([])?;
    let mut mismatches = 0;
    while let Some(row) = rows.next()? {
        let idx: usize = row
            .get::<_, i64>(0)?
            .try_into()
            .context("negative SQLite sequence")?;
        let bytes: Vec<u8> = row.get(1)?;
        let hash: String = row.get(2)?;
        if bytes != payload(idx) || hash != payload_hash(&bytes) {
            mismatches += 1;
        }
    }
    let integrity: String = conn.query_row("PRAGMA integrity_check", [], |r| r.get(0))?;
    Ok((count, mismatches, integrity))
}

async fn verify_turso(path: &Path) -> Result<(usize, usize, String)> {
    let db = Builder::new_local(path.to_string_lossy().as_ref())
        .build()
        .await?;
    let conn = db.connect()?;
    let mut count_rows = conn.query("SELECT count(*) FROM events", ()).await?;
    let row = count_rows
        .next()
        .await?
        .ok_or_else(|| anyhow!("missing count row"))?;
    let count = *row
        .get_value(0)?
        .as_integer()
        .ok_or_else(|| anyhow!("count is not integer"))? as usize;
    let mut rows = conn
        .query(
            "SELECT seq, payload, payload_sha256 FROM events ORDER BY seq",
            (),
        )
        .await?;
    let mut mismatches = 0;
    while let Some(row) = rows.next().await? {
        let idx = *row
            .get_value(0)?
            .as_integer()
            .ok_or_else(|| anyhow!("seq is not integer"))? as usize;
        let payload_value = row.get_value(1)?;
        let bytes = payload_value
            .as_blob()
            .ok_or_else(|| anyhow!("payload is not blob"))?;
        let hash_value = row.get_value(2)?;
        let hash = hash_value
            .as_text()
            .ok_or_else(|| anyhow!("hash is not text"))?;
        if bytes != payload(idx).as_slice() || hash.as_str() != payload_hash(bytes) {
            mismatches += 1;
        }
    }
    let mut integrity_rows = conn.query("PRAGMA integrity_check", ()).await?;
    let integrity = match integrity_rows.next().await? {
        Some(row) => row
            .get_value(0)?
            .as_text()
            .cloned()
            .unwrap_or_else(|| "unsupported".to_string()),
        None => "unsupported".to_string(),
    };
    Ok((count, mismatches, integrity))
}

fn payload(idx: usize) -> Vec<u8> {
    (0..PAYLOAD_BYTES)
        .map(|offset| ((idx * 31 + offset * 17) % 251) as u8)
        .collect()
}

fn payload_hash(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn operation_id(idx: usize) -> String {
    format!("synthetic-operation-{idx:06}")
}

fn mark(dir: &Path, name: &str) -> Result<()> {
    fs::write(dir.join(name), b"armed\n")?;
    Ok(())
}

fn park_forever() -> ! {
    loop {
        thread::park_timeout(Duration::from_secs(60));
    }
}

fn file_size(path: &Path) -> u64 {
    fs::metadata(path).map(|m| m.len()).unwrap_or(0)
}
