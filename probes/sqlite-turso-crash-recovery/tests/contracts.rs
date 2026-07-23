use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn binary() -> PathBuf {
    PathBuf::from(env!("CARGO_BIN_EXE_sqlite-turso-crash-recovery"))
}

fn temp_case(name: &str) -> PathBuf {
    let path = std::env::temp_dir().join(format!(
        "law-nexus-sqlite-turso-{name}-{}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&path);
    fs::create_dir_all(&path).expect("create temp case");
    path
}

#[test]
fn sqlite_clean_commit_and_reopen_pass() {
    let work = temp_case("sqlite-clean");
    let output = Command::new(binary())
        .args(["parent", "sqlite", "S01_clean_commit"])
        .arg(&work)
        .output()
        .expect("run probe");
    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: serde_json::Value = serde_json::from_slice(&output.stdout).expect("JSON report");
    assert_eq!(report["status"], "pass");
    assert_eq!(report["observed_rows"], 40);
    assert_eq!(report["checksum_mismatches"], 0);
    let _ = fs::remove_dir_all(work);
}

#[test]
fn turso_file_is_independently_verified_by_stock_sqlite() {
    let work = temp_case("turso-stock-exit");
    let output = Command::new(binary())
        .args(["parent", "turso", "S07_exit_to_stock_sqlite"])
        .arg(&work)
        .output()
        .expect("run probe");
    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    let report: serde_json::Value = serde_json::from_slice(&output.stdout).expect("JSON report");
    assert_eq!(report["status"], "pass");
    assert_eq!(report["observed_rows"], 40);
    assert_eq!(report["checksum_mismatches"], 0);
    assert_eq!(report["integrity"], "ok");
    assert!(report["note"]
        .as_str()
        .expect("note")
        .contains("independently verified 40/40"));
    let _ = fs::remove_dir_all(work);
}

#[test]
fn checkpoint_and_enospc_are_honestly_unsupported() {
    for scenario in ["S04_kill_during_checkpoint", "S05_disk_full"] {
        let work = temp_case(scenario);
        let output = Command::new(binary())
            .args(["parent", "sqlite", scenario])
            .arg(&work)
            .output()
            .expect("run probe");
        assert!(output.status.success());
        let report: serde_json::Value =
            serde_json::from_slice(&output.stdout).expect("JSON report");
        assert_eq!(report["status"], "unsupported");
        let _ = fs::remove_dir_all(work);
    }
}

#[test]
fn source_contract_forbids_non_authoritative_features() {
    let source = fs::read_to_string(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/main.rs"))
        .expect("read source");
    for token in [
        "mvcc",
        "encryption",
        "multiprocess-wal",
        "fts",
        "cdc",
        "sync",
        "mcp",
    ] {
        assert!(
            source.contains(token),
            "missing forbidden-feature declaration: {token}"
        );
    }
    assert!(source.contains("synthetic_only"));
    assert!(source.contains("adoption: \"none\""));
}
